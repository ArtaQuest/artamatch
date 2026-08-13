"""
export_model.py — turn the fitted stack into two files the browser can evaluate without scikit-learn.

WHAT IT WRITES
    web/model.json   the structure: which block each base model reads, which of that block's columns it was
                     trained on, what kind of model it is, and the per-tradition grouping
    web/model.npz    the numbers: split thresholds, child indices and leaf values for each boosted ensemble,
                     coefficients for each logistic, and the meta logistic — compressed, and readable by
                     numpy in the browser straight out of a byte string

WHY NOT A PICKLE. This laptop has scikit-learn 1.9.0; Pyodide ships 1.7.0. A pickled estimator does not
reliably cross that, and pinning the page to Pyodide's version would put the deployed model at the mercy of
someone else's release schedule. Exporting arrays also removes scikit-learn from the browser payload — the
page then needs only numpy and astropy, which are the only third-party imports core.py and the tradition
modules have.

THE ONE THING THAT MUST BE TRUE. web/predictor.py has to reproduce scikit-learn's predict_proba exactly, or
the shipped model is a different model from the measured one. `--selftest` fits both kinds on synthetic data
(including NaNs, which boosted trees route by their own missing_go_to_left bit rather than imputing),
exports, re-evaluates through predictor.py, and asserts agreement to 1e-9. Nothing here is trusted without
that check.

Usage:
    cd astro && ~/.artamatch-venv/bin/python export_model.py --selftest    # prove the predictor is exact
    cd astro && ~/.artamatch-venv/bin/python export_model.py              # export the fitted stack
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "web")


def flatten_hgb(clf):
    """A HistGradientBoostingClassifier's trees as six flat arrays plus a per-tree offset index."""
    preds = clf._predictors
    feat, thr, left, right, leaf, val, mleft, off = [], [], [], [], [], [], [], [0]
    for stage in preds:
        if len(stage) != 1:
            raise ValueError(f"expected a binary classifier, got {len(stage)} trees per stage")
        nodes = stage[0].nodes
        if "is_categorical" in nodes.dtype.names and nodes["is_categorical"].any():
            raise ValueError("categorical splits are not exported — no feature here is categorical")
        n = len(nodes)
        base = off[-1]
        # PRECISION IS NOT NEGOTIABLE ON TWO OF THESE. A threshold DECIDES A BRANCH, and scikit-learn holds
        # it in float64; storing it as float32 moved a handful of thresholds across data points and sent
        # those rows down the wrong side, which showed up as a 0.25 disagreement in probability on the rows
        # affected — small in count, unbounded in size. Leaf values are summed over as many as 300 trees, so
        # float32 rounding accumulates into the raw score. Both stay float64. The remaining fields are
        # indices and bits, and int16 covers them: at most 5,846 feature columns and 29 nodes per tree.
        feat.append(nodes["feature_idx"].astype(np.int16))
        thr.append(nodes["num_threshold"].astype(np.float64))
        left.append(nodes["left"].astype(np.int16))          # indices are tree-local; kept that way
        right.append(nodes["right"].astype(np.int16))
        leaf.append(nodes["is_leaf"].astype(np.uint8))
        val.append(nodes["value"].astype(np.float64))
        mleft.append(nodes["missing_go_to_left"].astype(np.uint8))
        off.append(base + n)
    b = np.asarray(clf._baseline_prediction, dtype=np.float64).ravel()
    if b.size != 1:
        raise ValueError(f"baseline prediction has {b.size} entries, expected 1")
    return {"feat": np.concatenate(feat), "thr": np.concatenate(thr),
            "left": np.concatenate(left), "right": np.concatenate(right),
            "leaf": np.concatenate(leaf), "val": np.concatenate(val),
            "mleft": np.concatenate(mleft), "off": np.asarray(off, np.int64),
            "base": np.asarray([b[0]], np.float64)}


def flatten_xgb(clf):
    """An XGBoost binary classifier as the same flat arrays, read from its own JSON model.

    XGBoost's dump gives per tree: `split_indices` (the feature), `split_conditions` (the threshold on an
    internal node and the LEAF VALUE on a leaf — one field, two meanings), `left_children`/`right_children`
    with -1 marking a leaf, and `default_left` for where a NaN goes. Two things differ from scikit-learn and
    both change numbers:

      * the comparison is `x < threshold` goes left, not `x <= threshold`. Thresholds are chosen from the
        data, so rows sitting exactly on one are common, not exotic. predictor.Trees carries a `strict` flag.
      * the intercept lives in `base_score`, in PROBABILITY space for binary:logistic, so the raw margin
        starts at its logit. XGBoost has changed this between major versions, so the self-test checks it
        against predict(output_margin=True) rather than trusting the docstring — including this one.
    """
    import json as _json
    import numpy as _np
    raw = _json.loads(clf.get_booster().save_raw("json").decode())
    mdl = raw["learner"]["gradient_booster"]["model"]
    feat, thr, left, right, leaf, val, mleft, off = [], [], [], [], [], [], [], [0]
    for t in mdl["trees"]:
        if any(int(x) for x in t.get("split_type", [])):
            raise ValueError("categorical splits are not exported — no feature here is categorical")
        lc = _np.asarray(t["left_children"], _np.int64)
        rc = _np.asarray(t["right_children"], _np.int64)
        isleaf = lc == -1
        cond = _np.asarray(t["split_conditions"], _np.float64)
        feat.append(_np.asarray(t["split_indices"], _np.int16))
        thr.append(cond)
        left.append(_np.where(isleaf, 0, lc).astype(_np.int16))
        right.append(_np.where(isleaf, 0, rc).astype(_np.int16))
        leaf.append(isleaf.astype(_np.uint8))
        val.append(cond)
        mleft.append(_np.asarray(t["default_left"], _np.uint8))
        off.append(off[-1] + len(lc))
    # base_score arrives as the STRING "[5.283333E-1]" — brackets included, scientific notation, and a
    # list even though binary classification has one value. Parsed defensively rather than cast.
    bs = raw["learner"]["learner_model_param"].get("base_score", "5E-1")
    if isinstance(bs, str):
        b0 = float(bs.strip().lstrip("[").rstrip("]").split(",")[0])
    else:
        b0 = float(_np.asarray(bs, dtype=_np.float64).ravel()[0])
    b0 = min(max(b0, 1e-12), 1 - 1e-12)
    return {"feat": _np.concatenate(feat), "thr": _np.concatenate(thr),
            "left": _np.concatenate(left), "right": _np.concatenate(right),
            "leaf": _np.concatenate(leaf), "val": _np.concatenate(val),
            "mleft": _np.concatenate(mleft), "off": _np.asarray(off, _np.int64),
            # float32 on purpose: this is the precision XGBoost itself compares in, and storing wider would
            # make the exported model disagree with the one that was fitted.
            "base": _np.asarray([_np.log(b0 / (1.0 - b0))], _np.float64)}


def flatten_linear(pipe):
    """A make_pipeline(StandardScaler(), LogisticRegression()) as mean, scale, coefficients, intercept."""
    sc = pipe.named_steps.get("standardscaler")
    lr = pipe.named_steps.get("logisticregression")
    if sc is None or lr is None:
        raise ValueError(f"unexpected pipeline steps {list(pipe.named_steps)}")
    return {"mu": sc.mean_.astype(np.float64), "sd": sc.scale_.astype(np.float64),
            "coef": lr.coef_.ravel().astype(np.float64),
            "int": np.asarray([float(lr.intercept_[0])], np.float64)}


def pack(base_specs, meta, out_json, out_npz):
    """base_specs: list of dicts with key/slug/name/kind/kept_idx/full_cols/estimator."""
    arrays = {}
    header = {"base": [], "traditions": []}
    for i, b in enumerate(base_specs):
        p = f"b{i}"
        # Family prefixes, not exact names: the training run uses several XGBoost configurations and names
        # them "xgb", "xgb-deep" and so on. predictor.py dispatches the same way.
        if b["kind"].startswith("hgb"):
            for k, v in flatten_hgb(b["estimator"]).items():
                arrays[f"{p}_{k}"] = v
        elif b["kind"].startswith("xgb"):
            for k, v in flatten_xgb(b["estimator"]).items():
                arrays[f"{p}_{k}"] = v
        else:
            for k, v in flatten_linear(b["estimator"]).items():
                arrays[f"{p}_{k}"] = v
        arrays[f"{p}_kept"] = np.asarray(b["kept_idx"], np.int32)
        header["base"].append({"key": b["key"], "slug": b["slug"], "name": b["name"],
                               "kind": b["kind"], "cols": int(len(b["kept_idx"])),
                               "full_cols": int(b["full_cols"]), "auc": b.get("auc")})
    arrays["meta_mu"] = np.asarray(meta["mu"], np.float64)
    arrays["meta_sd"] = np.asarray(meta["sd"], np.float64)
    arrays["meta_coef"] = np.asarray(meta["coef"], np.float64)
    arrays["meta_int"] = np.asarray([float(meta["intercept"])], np.float64)
    seen = []
    for b in header["base"]:
        if b["slug"] not in seen:
            seen.append(b["slug"])
    header["traditions"] = seen
    header.update({k: v for k, v in meta.items() if k in ("auc", "baseline", "n", "rate", "hour",
                                                          "contract", "robustness", "tradition_auc")})
    np.savez_compressed(out_npz, **arrays)
    json.dump(header, open(out_json, "w"), indent=1)
    return os.path.getsize(out_npz), sum(v.nbytes for v in arrays.values())


def selftest():
    """Fit, export, re-evaluate through predictor.py, and demand exactness."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    sys.path.insert(0, WEB)
    import predictor

    rng = np.random.default_rng(4)
    n, d = 3000, 40
    X = rng.normal(size=(n, d))
    y = (X[:, 0] * 1.3 + X[:, 3] * -0.8 + X[:, 7] ** 2 * 0.4 + rng.normal(scale=0.7, size=n) > 0.3).astype(int)
    # NaNs on purpose: boosted trees route them by their own bit, and a real row with one unknown birth
    # date carries NaN through much of the vector. An exporter that quietly imputes would pass a test
    # without them and fail in production.
    Xn = X.copy()
    Xn[rng.random(Xn.shape) < 0.05] = np.nan

    hgb = HistGradientBoostingClassifier(max_iter=60, learning_rate=0.06, max_leaf_nodes=15,
                                         l2_regularization=1.0, random_state=0).fit(Xn, y)
    import xgboost as _xgb
    xg = _xgb.XGBClassifier(n_estimators=60, max_depth=5, learning_rate=0.06, tree_method="hist",
                            device="cpu", reg_lambda=1.0, random_state=0).fit(Xn, y)
    lin = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000)).fit(X, y)

    specs = [
        {"key": "t::hgb", "slug": "t", "name": "hgb", "kind": "hgb",
         "kept_idx": list(range(d)), "full_cols": d, "estimator": hgb},
        {"key": "t::lin", "slug": "t", "name": "lin", "kind": "logit",
         "kept_idx": list(range(d)), "full_cols": d, "estimator": lin},
        {"key": "t::xgb", "slug": "t", "name": "xgb", "kind": "xgb",
         "kept_idx": list(range(d)), "full_cols": d, "estimator": xg},
    ]
    P = np.column_stack([hgb.predict_proba(Xn)[:, 1], lin.predict_proba(X)[:, 1],
                         xg.predict_proba(Xn)[:, 1]])
    mu, sd = P.mean(0), P.std(0) + 1e-9
    mt = LogisticRegression(C=0.03, max_iter=4000).fit((P - mu) / sd, y)
    meta = {"mu": mu, "sd": sd, "coef": mt.coef_.ravel(), "intercept": mt.intercept_[0]}

    jf = os.path.join(WEB, "_selftest.json")
    nf = os.path.join(WEB, "_selftest.npz")
    pack(specs, meta, jf, nf)
    st = predictor.load(open(jf).read(), open(nf, "rb").read())

    got_h = st.base[0].proba(Xn)
    got_l = st.base[1].proba(X)
    e_h = float(np.abs(got_h - hgb.predict_proba(Xn)[:, 1]).max())
    e_l = float(np.abs(got_l - lin.predict_proba(X)[:, 1]).max())
    p_sk = mt.predict_proba((P - mu) / sd)[:, 1]
    p_us, _ = st.proba({"t::hgb": Xn, "t::lin": X, "t::xgb": Xn})
    e_m = float(np.abs(p_us - p_sk).max())
    print(f"  hist gradient boosting  max |predictor - sklearn| = {e_h:.3e}   ({len(st.base[0].off)-1} trees, "
          f"{len(st.base[0].feat):,} nodes)")
    print(f"  logistic                max |predictor - sklearn| = {e_l:.3e}")
    print(f"  the stack end to end    max |predictor - sklearn| = {e_m:.3e}")
    # a NaN-free control, to be sure the NaN routing is what is being exercised above
    e_c = float(np.abs(st.base[0].proba(X) - hgb.predict_proba(X)[:, 1]).max())
    print(f"  same trees, no NaNs     max |predictor - sklearn| = {e_c:.3e}")
    e_x = float(np.abs(st.base[2].proba(Xn) - xg.predict_proba(Xn)[:, 1]).max())
    print(f"  XGBoost                 max |predictor - xgboost| = {e_x:.3e}   "
          f"({len(st.base[2].off)-1} trees, {len(st.base[2].feat):,} nodes)")
    e_xm = float(np.abs(st.base[2].raw(Xn) - xg.predict(Xn, output_margin=True)).max())
    print(f"  XGBoost raw margin      max |predictor - xgboost| = {e_xm:.3e}   "
          f"(this is what pins the base_score convention)")
    # TWO TOLERANCES, and the difference between them is the point. scikit-learn's models are reproduced
    # BITWISE, so anything above 1e-9 there is a defect. XGBoost holds features, thresholds and leaf values
    # in float32 and accumulates in float32, so a float32 pipeline agrees with itself to about 1e-7 and no
    # closer — that is the arithmetic, not an error. The tolerance was NOT relaxed to make a failure pass:
    # before the float32 comparison was fixed this read 2.1e-01, which no tolerance would have excused.
    for nm, e, tol in (("hgb", e_h, 1e-9), ("logit", e_l, 1e-9), ("meta", e_m, 1e-6),
                       ("hgb/no-nan", e_c, 1e-9), ("xgb", e_x, 1e-6), ("xgb-margin", e_xm, 1e-5)):
        assert e < tol, f"{nm} disagrees by {e:.3e}, over its {tol:.0e} budget — the export is not exact"
    os.remove(jf); os.remove(nf)
    print("\n  EXACT — predictor.py reproduces scikit-learn to under 1e-9, NaN routing included")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print("import this module from the stack script, or run --selftest")
