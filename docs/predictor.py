"""
predictor.py — evaluate the trained stack in the browser, in numpy, with no scikit-learn.

WHY NOT JUST SHIP THE PICKLE. This laptop trains on scikit-learn 1.9.0 and Pyodide carries 1.7.0; a pickled
estimator does not reliably cross that gap, and pinning the browser to whatever version Pyodide happens to
ship would make the deployed model hostage to someone else's release schedule. So the fitted models are
exported as plain arrays — split thresholds, child indices and leaf values — and evaluated here. The arrays
are what scikit-learn itself evaluates; only the loop is ours.

That also drops scikit-learn from the browser payload entirely. The only third-party packages the page needs
are numpy and astropy, because those are the only ones `core.py` and the tradition modules import.

WHAT IS EVALUATED

    A histogram gradient-boosting classifier is a sum over trees of the leaf each row falls into, plus a
    baseline, put through a logistic. Missing values are NOT imputed: every internal node carries its own
    `missing_go_to_left` bit, which is how scikit-learn routes a NaN, and this reproduces that rather than
    substituting a zero. That matters here — a row with one unknown birth date legitimately carries NaN
    through a good part of the feature vector.

    A logistic base model is a standardiser followed by a linear term, so the exported mean and scale are
    applied before the coefficients.

    The meta model is a logistic over the base models' probabilities, standardised by the mean and scale
    measured on the training set's out-of-fold predictions.

EXACTNESS IS TESTED, NOT ASSUMED. `astro/export_model.py --selftest` fits both model kinds on synthetic data,
exports them, evaluates them here, and asserts agreement with scikit-learn's own predict_proba to 1e-9. A
predictor that is nearly right is worse than useless, because nothing downstream would show it.
"""
import io
import json

import numpy as np


def _sigmoid(z):
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    e = np.exp(z[~pos])
    out[~pos] = e / (1.0 + e)
    return out


class Trees:
    """One histogram gradient-boosting ensemble, flattened into six parallel arrays.

    Nodes of every tree live in one array; `off[t]:off[t+1]` is tree t. Traversal is vectorised over ROWS
    rather than trees: all rows walk tree t together, which is the shape numpy is fast at and the reason a
    ten-thousand-candidate search is arithmetic rather than a Python loop over a million nodes.
    """

    __slots__ = ("feat", "thr", "left", "right", "leaf", "val", "off", "base", "mleft", "strict", "f32")

    def __init__(self, z, p, strict=False, f32=False):
        self.strict = strict
        self.f32 = f32
        self.feat = z[f"{p}_feat"]
        self.thr = z[f"{p}_thr"].astype(np.float32 if f32 else np.float64)
        self.left = z[f"{p}_left"]
        self.right = z[f"{p}_right"]
        self.leaf = z[f"{p}_leaf"].astype(bool)
        self.val = z[f"{p}_val"].astype(np.float32 if f32 else np.float64)
        self.off = z[f"{p}_off"]
        self.mleft = z[f"{p}_mleft"].astype(bool)
        self.base = float(z[f"{p}_base"][0])

    def raw(self, X):
        """Sum of leaf values over every tree, vectorised over ROWS.

        TWO THINGS ABOUT THE COMPARISON, and both were found by a test rather than by reading a document.

        `strict`: scikit-learn's histogram booster sends a row LEFT when `x <= threshold`, XGBoost when
        `x < threshold`. Thresholds are chosen from the data, so rows landing exactly on one are common.

        `f32`: XGBoost holds its features in a DMatrix of float32 and compares in float32. Comparing in
        float64 against a widened threshold is not the same predicate — a feature of 0.5667908633732233
        against a threshold of 0.5667909 is `<` in float64 and EQUAL in float32, so the two send that row
        down opposite branches. That single case put the exported model 0.87 out in raw margin.
        """
        n = X.shape[0]
        # The accumulator matches the library's own: XGBoost sums leaf values in float32, so summing in
        # float64 leaves a ~1e-7 residual that is arithmetic, not a defect.
        dt = np.float32 if self.f32 else np.float64
        total = np.full(n, self.base, dtype=dt)
        rows = np.arange(n)
        for t in range(len(self.off) - 1):
            lo, hi = int(self.off[t]), int(self.off[t + 1])
            feat = self.feat[lo:hi]; thr = self.thr[lo:hi]
            left = self.left[lo:hi]; right = self.right[lo:hi]
            leaf = self.leaf[lo:hi]; val = self.val[lo:hi]; mleft = self.mleft[lo:hi]
            cur = np.zeros(n, dtype=np.int64)
            alive = ~leaf[cur]
            # A tree of 15 leaves is at most 15 levels deep, so this terminates; the guard is a hard stop
            # against a malformed export rather than an expected exit.
            for _ in range(64):
                if not alive.any():
                    break
                idx = rows[alive]
                c = cur[idx]
                v = X[idx, feat[c]]
                nan = np.isnan(v)
                if self.f32:
                    v = v.astype(np.float32)
                go_left = np.where(nan, mleft[c], v < thr[c] if self.strict else v <= thr[c])
                cur[idx] = np.where(go_left, left[c], right[c])
                alive = ~leaf[cur]
            total += val[cur].astype(dt)
        return total.astype(np.float64)

    def proba(self, X):
        return _sigmoid(self.raw(X))


class Linear:
    """Standardiser plus logistic — the other base-model kind."""

    __slots__ = ("mu", "sd", "coef", "intercept")

    def __init__(self, z, p):
        self.mu = z[f"{p}_mu"].astype(np.float64)
        self.sd = z[f"{p}_sd"].astype(np.float64)
        self.coef = z[f"{p}_coef"].astype(np.float64)
        self.intercept = float(z[f"{p}_int"][0])

    def proba(self, X):
        Z = (np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0) - self.mu) / self.sd
        return _sigmoid(Z @ self.coef + self.intercept)


class Stack:
    """The whole shipped model: the base models, the columns each one wants, and the meta logistic."""

    def __init__(self, header, z):
        self.h = header
        self.z = z
        self.base = []
        for i, b in enumerate(header["base"]):
            p = f"b{i}"
            # MATCH THE FAMILY, NOT ONE NAME. This read `b["kind"] in ("hgb", "xgb")`, and the training run
            # uses two XGBoost configurations named "xgb" and "xgb-deep" — so every "xgb-deep" block fell
            # through to the linear branch and asked for coefficients that do not exist in a tree export.
            # Any kind beginning "xgb" is an XGBoost ensemble, and both its quirks (a strict `<` comparison
            # and float32 arithmetic) come with it.
            kind = b["kind"]
            if kind.startswith("xgb"):
                self.base.append(Trees(z, p, strict=True, f32=True))
            elif kind.startswith("hgb"):
                self.base.append(Trees(z, p, strict=False, f32=False))
            else:
                self.base.append(Linear(z, p))
        self.kept = [np.asarray(z[f"b{i}_kept"], dtype=np.int64) for i in range(len(self.base))]
        self.meta_mu = z["meta_mu"].astype(np.float64)
        self.meta_sd = z["meta_sd"].astype(np.float64)
        self.meta_coef = z["meta_coef"].astype(np.float64)
        self.meta_int = float(z["meta_int"][0])

    @property
    def modules(self):
        """The tradition modules that must be built for this model — nothing else needs computing."""
        seen = []
        for b in self.h["base"]:
            if b["slug"] not in seen:
                seen.append(b["slug"])
        return seen

    def base_proba(self, blocks):
        """blocks: {block key -> the FULL built array}. Returns (n, n_base) base probabilities."""
        cols = []
        for i, b in enumerate(self.h["base"]):
            X = blocks.get(b["key"])
            if X is None:
                raise KeyError(f"block {b['key']!r} was not built")
            if X.shape[1] != b["full_cols"]:
                raise ValueError(
                    f"{b['key']}: built {X.shape[1]} columns, model was trained on {b['full_cols']}. "
                    f"A block's width must be a function of the code, never of the batch.")
            cols.append(self.base[i].proba(np.asarray(X, dtype=np.float64)[:, self.kept[i]]))
        return np.column_stack(cols)

    def proba(self, blocks):
        P = self.base_proba(blocks)
        Z = (P - self.meta_mu) / self.meta_sd
        return _sigmoid(Z @ self.meta_coef + self.meta_int), P

    def by_tradition(self, P):
        """Mean base probability per tradition — what the page shows as the per-tradition breakdown.

        It is a DESCRIPTION, not a decomposition: the meta logistic is not additive over traditions, so
        these do not sum to the final number and are not that number's parts.
        """
        out = {}
        for i, b in enumerate(self.h["base"]):
            out.setdefault(b["slug"], []).append(P[:, i])
        return {k: np.mean(v, axis=0) for k, v in out.items()}


def load(header_json, npz_bytes):
    header = json.loads(header_json) if isinstance(header_json, str) else header_json
    z = np.load(io.BytesIO(npz_bytes)) if isinstance(npz_bytes, (bytes, bytearray)) else np.load(npz_bytes)
    return Stack(header, z)
