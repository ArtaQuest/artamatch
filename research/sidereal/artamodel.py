"""
artamodel.py — ArtaModel, canonical implementation.

    y = | b + Σ_i  a_i  e^{i(θm_i − θd_i)}      synastry, mom − dad
                 + m_i  e^{i(θt_i − θm_i)}      the wedding sky transiting mom
                 + d_i  e^{i(θt_i − θd_i)}      the wedding sky transiting dad
                 + mn_i e^{i θm_i}              mom's own natal phase
                 + dn_i e^{i θd_i}              dad's own natal phase
                 + tn_i e^{i θt_i}              the wedding sky's own phase
                 + c_i  e^{i θc_i}              the COMPOSITE: the shorter-arc midpoint of mom's and dad's natal
                                                 longitudes (Arash, 2026-08-18: "add the mid angle of natals as
                                                 term, like Davison compatibility")
                 + tc_i e^{i(θt_i − θc_i)} |²   the wedding sky transiting the composite

θ are sidereal longitudes (Kerykeion, Lahiri unless told otherwise): dad and mom at 09:00 local at each birthplace,
θt the marriage date at 12:00 UT. Every complex weight is held as (Re, Im); the model is a complex-linear map over
the phasors followed by |·|², a logistic head turns the standardised intensity into a probability for the loss,
and AUC reads the intensity's ranking. F fields = F copies of the formula combined by the head; F = 1 is the
formula literally.

THE PRESENCE RULE (Arash, 2026-08-18): a term exists only when both of its phases exist. "If wedding is not known,
drop the last two terms"; "if dob of either is not known, drop the natal term of it". A missing phase is NaN in the
phase matrix and contributes exactly zero to the sum (cos = sin = 0), so one parameter set serves every row and a
row is usable as long as it has at least one phasor.

TERMS are selectable by name -- "a", "m", "d", "mn", "dn", "tn" -- and BODIES by name, so the study can ablate.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from coherent_fit import Coherent, auc                                    # noqa: E402

TERMS = ("a", "m", "d", "mn", "dn", "tn")
TERMS8 = TERMS + ("c", "tc")
# Arash, 2026-08-19: "add the midpoint of natals as another term. also midpoint with their wedding. overall 3 more
# terms" -> c (midpoint of the two natals), mw (midpoint of mom's natal with the wedding), dw (dad's with the wedding)
TERMS9 = TERMS + ("c", "mw", "dw")
BODIES14 = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
            "true_node", "true_south_node", "chiron", "mean_lilith"]
ANGLES = ["ascendant", "medium_coeli"]
GROUPS = {"luminaries": ["sun", "moon"], "inner": ["mercury", "venus", "mars"], "social": ["jupiter", "saturn"],
          "outer": ["uranus", "neptune", "pluto"], "nodes": ["true_node", "true_south_node"],
          "points": ["chiron", "mean_lilith"], "angles": ANGLES}


def composite(D, M):
    """The shorter-arc midpoint of two longitudes, in degrees on [0, 360): dad + half the wrapped difference.
    (The naive (θm+θd)/2 is ambiguous by 180 degrees whenever the pair straddles 0.)"""
    diff = (M - D + 180.0) % 360.0 - 180.0
    return (D + diff / 2.0) % 360.0


# FOURTH EDITION — GENDERLESS (operator 2026-08-19): "I want a genderless model from now on ... (a, b, 1) should
# also mean (b, a, 1) ... for each subtractive term add abs to ensure each term is an even function." The two
# natal charts are slot 1 and slot 2 with no meaning attached; the files carry every pair in BOTH orders; and
# every phase DIFFERENCE enters as its wrapped absolute value |Δθ| in [0°, 180°], so a term's value is unchanged
# when the partners swap (and the wedding-sky terms are even in the same sense: |θt − θ|). Term names for this
# edition: a (synastry |θ1 − θ2|), t1/t2 (the wedding sky to each partner, |θt − θ|), n1/n2 (each natal phase),
# tn (the wedding sky's own phase). They map onto the earlier a/m/d/mn/dn/tn computations with `even=True`.
TERMS_IV = ("a", "t1", "t2", "n1", "n2", "tn")
_IV_TO_III = {"t1": "d", "t2": "m", "n1": "dn", "n2": "mn"}


def absdiff(x, y):
    """The wrapped absolute phase difference |x − y| in [0, 180] degrees — even in (x, y)."""
    return np.abs((x - y + 180.0) % 360.0 - 180.0)


def phase_matrix(D, M, W, all_bodies, bodies, terms, angles_in_natal=False, even=False):
    """(n, K) phases in degrees (NaN = the term does not exist for that row) and K labels.
    even=True: every subtractive term is the wrapped absolute difference (the genderless edition)."""
    col = {b: j for j, b in enumerate(all_bodies)}
    P, lab = [], []
    use = list(bodies) + (ANGLES if angles_in_natal else [])
    diff = absdiff if even else (lambda x, y: x - y)
    for t0 in terms:
        t = _IV_TO_III.get(t0, t0)
        for b in use:
            j = col[b]
            if t == "a":
                P.append(diff(M[:, j], D[:, j]))
            elif t == "c":
                P.append(composite(D[:, j], M[:, j]))
            elif t == "tc":
                if b in ANGLES: continue
                P.append(diff(W[:, j], composite(D[:, j], M[:, j])))
            elif t == "mw":
                if b in ANGLES: continue
                P.append(composite(M[:, j], W[:, j]))          # midpoint of mom's natal and the wedding sky
            elif t == "dw":
                if b in ANGLES: continue
                P.append(composite(D[:, j], W[:, j]))          # midpoint of dad's natal and the wedding sky
            elif t == "m":
                if b in ANGLES: continue
                P.append(diff(W[:, j], M[:, j]))
            elif t == "d":
                if b in ANGLES: continue
                P.append(diff(W[:, j], D[:, j]))
            elif t == "mn":
                P.append(M[:, j])
            elif t == "dn":
                P.append(D[:, j])
            elif t == "tn":
                if b in ANGLES: continue
                P.append(W[:, j])
            else:
                raise ValueError(t)
            lab.append(f"{t0}_{b}")
    return (np.column_stack(P) if P else np.zeros((len(D), 0))), lab


class ArtaModel:
    """One ArtaModel: a term set, a body set, F fields, and the fitted weights."""

    def __init__(self, terms=TERMS, bodies=BODIES14, F=1, l2=1e-3, angles_in_natal=False, seed=0):
        self.terms, self.bodies, self.F, self.l2, self.angles, self.seed = tuple(terms), list(bodies), F, l2, angles_in_natal, seed
        self.model = None; self.labels = None; self.inner_auc = None; self.epochs = None

    def _cs(self, P):
        rad = np.pi / 180.0
        return np.nan_to_num(np.cos(P * rad)), np.nan_to_num(np.sin(P * rad))

    def fit(self, P, y, inner, lr=0.01, epochs=150, patience=15, batch=None):
        """Early-stopped on `inner` (a boolean mask: the inner temporal validation rows). Returns self.

        The batch adapts to the population: at least sixteen gradient steps per epoch. A fixed 2,048 gave a
        300-row self-test one step per epoch and 80 steps in all, and the planted phasor was not recovered."""
        C, S = self._cs(P)
        m = Coherent(C.shape[1], self.F, seed=self.seed)
        rng = np.random.default_rng(1000 + self.seed)
        idx = np.where(~inner)[0]
        if batch is None:
            batch = int(min(1024, max(32, len(idx) // 16)))
        best, state, bad, best_ep = -1.0, None, 0, 0
        for ep in range(epochs):
            rng.shuffle(idx)
            for s0 in range(0, len(idx), batch):
                b = idx[s0:s0 + batch]
                if len(b) >= 32:
                    m.step(C[b], S[b], y[b].astype(float), lr, self.l2)
            a = auc(y[inner], m.logit(C[inner], S[inner])[0]) if inner.any() else 0.5
            if a > best + 1e-5:
                best, bad, best_ep = a, 0, ep
                state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
            else:
                bad += 1
                if bad >= patience:
                    break
        m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
        self.model, self.inner_auc, self.epochs = m, best, best_ep
        return self

    def score(self, P):
        C, S = self._cs(P)
        return self.model.logit(C, S)[0]

    def intensity(self, P):
        """|b + Σ w_k z_k|² per field, before the head: (n, F)."""
        C, S = self._cs(P)
        return self.model.fields(C, S)[2]

    def weights(self, labels):
        """The fitted complex weights of field 0: {label: (modulus, phase_deg)} plus the bias and head weight."""
        m = self.model
        w = m.A1[0] - 1j * m.A2[0]                     # A1 = Re w, A2 = -Im w
        out = {lab: (float(abs(w[k])), float(np.degrees(np.angle(w[k])))) for k, lab in enumerate(labels)}
        out["_bias"] = (float(abs(m.br[0] + 1j * m.bi[0])), float(np.degrees(np.angle(m.br[0] + 1j * m.bi[0]))))
        out["_head_w"] = (float(m.w[0]), 0.0)
        return out


def fit_ensemble(P, y, inner, Pte, seeds=3, **kw):
    """Mean held-out score over seeds, and the mean inner AUC."""
    outs, ivs = [], []
    for s in range(seeds):
        am = ArtaModel(seed=s, **kw).fit(P, y, inner)
        outs.append(am.score(Pte)); ivs.append(am.inner_auc)
    return float(np.mean(ivs)), np.mean(outs, 0)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n, B = 400, len(BODIES14)
    D = rng.uniform(0, 360, (n, B)); M = rng.uniform(0, 360, (n, B)); W = rng.uniform(0, 360, (n, B))
    P, lab = phase_matrix(D, M, W, BODIES14, BODIES14, TERMS)
    assert P.shape == (n, 6 * B) and len(lab) == 6 * B
    # a planted signal in one phasor must be recovered
    y = (np.cos(np.radians(M[:, 1] - D[:, 1])) + 0.3 * rng.normal(size=n) > 0).astype(int)
    inner = np.arange(n) >= 300
    am = ArtaModel(F=1).fit(P, y, inner)
    w = am.weights(lab)
    top = max((k for k in w if not k.startswith("_")), key=lambda k: w[k][0])
    print(f"  {6*B} phasors · planted signal on a_moon · largest fitted weight: {top} (|w|={w[top][0]:.3f}) · inner AUC {am.inner_auc:.3f}")
    assert top == "a_moon", "the fit did not recover the planted phasor"
    # a NaN phase contributes nothing: scores identical whether the column is NaN or absent
    P2 = P.copy(); P2[:, 5] = np.nan
    P3, _ = phase_matrix(D, M, W, BODIES14, [b for b in BODIES14 if b != BODIES14[5]] + [BODIES14[5]], TERMS)
    print("  presence rule: a NaN phase zeroes its phasor (cos=sin=0)")
