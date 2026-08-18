"""
coherent_fit.py — FIT the coherent phasor field. Arash's form, with a, p and b learned rather than drawn.

    F_f(chart) = | b_f + SUM_k w_fk * exp( i * h_k * theta_k ) |^2 ,    w_fk = a_fk * exp(-i * p_fk)

THE REPARAMETERISATION, AND WHY IT MATTERS. Written in polar form the parameters are an amplitude a >= 0 and a
phase p on a circle, and a gradient step on p has to be wrapped. Folding them into ONE COMPLEX WEIGHT
w = a*exp(-i*p) removes both problems: the model becomes a complex linear map followed by a squared modulus, the
parameter space is flat R^2 per term, and every gradient is a matmul. With A1 = Re w and A2 = -Im w,

    Re S = C @ A1' + S_ @ A2'          Im S = S_ @ A1' - C @ A2'

where C = cos(h*theta) and S_ = sin(h*theta) are the batch's basis. Nothing is approximated -- this is the same
function, in coordinates that optimise cleanly.

WHAT IS ACTUALLY BEING LEARNED. |b + sum w_k z_k|^2 expands to |b|^2 + 2*Re(b_bar * sum w_k z_k) + sum_jk
w_j w_k_bar z_j z_k_bar. The last term is a QUADRATIC form in the chart's Fourier coefficients, so a bank of F
fields is a rank-F quadratic model over every pairwise product of body phases -- every classical aspect, every
harmonic of one, and every cross-partner contact, simultaneously, with the weights fitted. The bias term is what
makes the field's response asymmetric rather than a pure interference pattern.

The basis spans harmonics h in HARMONICS for every (partner-slot, body) pair, so a single field may mix
harmonics. That is strictly more general than one harmonic per field, and it is the fit's business which to use.

INNER VALIDATION IS TEMPORAL, NOT RANDOM. Early stopping on a random slice of the training half would select the
iteration that generalises best to CONTEMPORARIES of the training data, which is not the question -- the real
test is out of time. So the inner split holds out the LATEST births of the training half, mirroring the outer
split. A random inner split measurably overfits the epoch count here.

THE ONLY COMPARISON REPORTED is the two-parameter logistic on the age gap. Note a consequence of the dataset's
own column definition: with the OLDER partner always first, the gap is non-negative by construction, so the
signed form that distinguished man-older from woman-older is not expressible and is not claimed -- no sex is
read anywhere in this dataset.

Usage: AQ_LON=/tmp/aqcoh/lon.npz AQ_SET=fast AQ_FIELDS=64 python coherent_fit.py
"""
import json
import os
import sys
import time

import numpy as np

T0 = time.time()

HARMONICS = (1, 2, 3, 4, 6, 8, 12)
SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO = range(10)
SETS = {
    "fast": (SUN, MOON, MERCURY, VENUS, MARS),
    "classical": (SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN),
    "all18": tuple(range(18)),
}
iO, iY = 0, 1


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc(y, s):
    y = np.asarray(y, np.int64)
    s = np.asarray(s, np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort")
    ys, ss = y[o], s[o]
    r = np.empty(len(ss))
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


# Mean daily motion in degrees, for the orb filter below. Only the ten classical/modern bodies are ever used
# with a harmonic filter; the asteroids and nodes are slow and unaffected.
DAILY = {SUN: 0.9856, MOON: 13.176, MERCURY: 4.09, VENUS: 1.60, MARS: 0.524, JUPITER: 0.083,
         SATURN: 0.0335, URANUS: 0.0117, NEPTUNE: 0.006, PLUTO: 0.004}


def basis(LON, bodies, orb=0.0):
    """cos and sin of h*theta for every (slot, body, harmonic), with an ORB FILTER on the harmonic.

    WHY A FILTER. This dataset has birth DATES and no birth TIMES, so every chart is cast for a fixed hour and
    each body carries an uncertainty of +-(daily motion)/2 degrees. A harmonic MULTIPLIES that error: the Moon
    moves 13.2 deg/day, so its phase is +-6.6 deg at h=1 and +-79 deg at h=12 -- at which point the term is not a
    weak feature, it is noise with a plausible name, and fitting it can only cost generalisation.

    `orb` is the largest phase error in degrees a term may carry. A term is admitted when
    h * (daily motion)/2 <= orb. orb=0 admits everything (the unfiltered basis); orb=30 drops the Moon above
    h=4 and Mercury above h=12 while keeping every slow body at every harmonic.
    """
    rad = np.pi / 180.0
    cols, kept = [], []
    for h in HARMONICS:
        for b in bodies:
            if orb and h * DAILY.get(b, 0.3) / 2.0 > orb:
                continue
            for s in (iO, iY):
                cols.append(h * LON[s, b] * rad)
                kept.append((h, b, s))
    P = np.stack(cols, axis=1)
    return np.cos(P), np.sin(P), kept


class Coherent:
    """A bank of F coherent fields plus a logistic head, fitted by Adam on the exact gradients."""

    def __init__(self, K, F=64, seed=0):
        g = np.random.default_rng(seed)
        # Small init so the initial |Z|^2 is O(1) and the head starts near chance.
        sc = 1.0 / np.sqrt(K)
        self.A1 = g.normal(0, sc, (F, K))
        self.A2 = g.normal(0, sc, (F, K))
        self.br = g.normal(0, 0.3, F)
        self.bi = g.normal(0, 0.3, F)
        self.w = np.zeros(F)
        self.c = 0.0
        self.mu = np.zeros(F)
        self.sd = np.ones(F)
        self.F, self.K = F, K
        self._m = {k: np.zeros_like(getattr(self, k)) for k in ("A1", "A2", "br", "bi", "w")}
        self._v = {k: np.zeros_like(getattr(self, k)) for k in ("A1", "A2", "br", "bi", "w")}
        self._mc = self._vc = 0.0
        self.t = 0

    def fields(self, C, S):
        ReS = C @ self.A1.T + S @ self.A2.T
        ImS = S @ self.A1.T - C @ self.A2.T
        Zr, Zi = ReS + self.br, ImS + self.bi
        return Zr, Zi, Zr * Zr + Zi * Zi

    def logit(self, C, S):
        Zr, Zi, u = self.fields(C, S)
        return ((u - self.mu) / self.sd) @ self.w + self.c, Zr, Zi, u

    def step(self, C, S, y, lr, l2, mom=0.99):
        B = len(y)
        Zr, Zi, u = self.fields(C, S)
        # Running standardisation of the fields. Treated as a constant in the gradient -- the standard
        # inference-time treatment, and the running stats are what the held-out pass will use.
        self.mu = mom * self.mu + (1 - mom) * u.mean(0)
        self.sd = mom * self.sd + (1 - mom) * (u.std(0) + 1e-6)
        un = (u - self.mu) / self.sd
        z = un @ self.w + self.c
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        d = (p - y) / B                                   # dL/dz
        gw = un.T @ d + l2 * self.w
        gc = d.sum()
        gu = np.outer(d, self.w) / self.sd                # dL/du   (B,F)
        gr, gi = 2.0 * gu * Zr, 2.0 * gu * Zi             # dL/dReZ, dL/dImZ
        gA1 = gr.T @ C + gi.T @ S + l2 * self.A1
        gA2 = gr.T @ S - gi.T @ C + l2 * self.A2
        gbr, gbi = gr.sum(0), gi.sum(0)
        self.t += 1
        for k, g in (("A1", gA1), ("A2", gA2), ("br", gbr), ("bi", gbi), ("w", gw)):
            self._m[k] = 0.9 * self._m[k] + 0.1 * g
            self._v[k] = 0.999 * self._v[k] + 0.001 * g * g
            mh = self._m[k] / (1 - 0.9 ** self.t)
            vh = self._v[k] / (1 - 0.999 ** self.t)
            setattr(self, k, getattr(self, k) - lr * mh / (np.sqrt(vh) + 1e-8))
        self.c -= lr * gc
        return float(-np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)))


def _gradcheck():
    """The exact gradients against finite differences. If this is wrong every number below is noise."""
    g = np.random.default_rng(0)
    B, K, F = 24, 9, 4
    C, S = g.normal(size=(B, K)), g.normal(size=(B, K))
    y = (g.random(B) < 0.5).astype(float)
    m = Coherent(K, F, seed=1)
    m.w = g.normal(0, 0.5, F)
    m.mu, m.sd = np.zeros(F), np.ones(F)

    def loss():
        _, _, u = m.fields(C, S)
        z = ((u - m.mu) / m.sd) @ m.w + m.c
        p = 1 / (1 + np.exp(-z))
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    # analytic, with the running-stat update and the optimiser disabled
    B_ = len(y)
    Zr, Zi, u = m.fields(C, S)
    z = ((u - m.mu) / m.sd) @ m.w + m.c
    p = 1 / (1 + np.exp(-z))
    d = (p - y) / B_
    gu = np.outer(d, m.w) / m.sd
    gr, gi = 2 * gu * Zr, 2 * gu * Zi
    an = {"A1": gr.T @ C + gi.T @ S, "A2": gr.T @ S - gi.T @ C, "br": gr.sum(0), "bi": gi.sum(0)}
    worst = 0.0
    for name in an:
        P = getattr(m, name)
        num = np.zeros_like(P)
        it = np.nditer(P, flags=["multi_index"])
        for _ in it:
            ix = it.multi_index
            o = P[ix]
            P[ix] = o + 1e-6
            hi = loss()
            P[ix] = o - 1e-6
            lo = loss()
            P[ix] = o
            num[ix] = (hi - lo) / 2e-6
        rel = np.abs(num - an[name]).max() / max(1e-12, np.abs(num).max())
        worst = max(worst, rel)
        assert rel < 2e-4, (name, rel)
    print(f"  gradcheck: analytic == finite-difference for A1, A2, Re b, Im b (worst relative {worst:.2e})")


def main():
    Z = np.load(os.environ.get("AQ_LON", "/tmp/aqcoh/lon.npz"))
    LONtr, LONte = Z["lon_train"], Z["lon_test"]
    ytr, yte = Z["y_train"], Z["y_test"]
    yr_tr, yr_te = Z["yr_train"], Z["yr_test"]          # (2, n) the two birth years
    which = os.environ.get("AQ_SET", "fast")
    F = int(os.environ.get("AQ_FIELDS") or 64)
    EPOCHS = int(os.environ.get("AQ_EPOCHS") or 40)
    LR = float(os.environ.get("AQ_LR") or 0.01)
    L2 = float(os.environ.get("AQ_L2") or 1e-4)
    SEEDS = int(os.environ.get("AQ_SEEDS") or 3)
    TRACE = bool(os.environ.get("AQ_TRACE"))
    PATIENCE = int(os.environ.get("AQ_PATIENCE") or 12)
    bodies = SETS[which]
    TWO = os.environ.get("AQ_TWO_SIDED", "1") not in ("0", "")

    # DROP THE IDENTICAL-CHART ROWS FROM THE FIT, BY DEFAULT.
    #
    # dates.couple_record gives a partner with no known birth date the OTHER partner's instant, deliberately and
    # documented -- every chart needs some instant, and self-comparison is a defined value rather than a guess
    # about a stranger. For a one-sided feature that is harmless. For a COHERENT SUM OVER BOTH CHARTS it is not:
    # when theta_older == theta_younger the sum collapses from SUM_k (w_Ok e^{ih th_Ok} + w_Yk e^{ih th_Yk}) to
    # SUM_k (w_Ok + w_Yk) e^{ih th_k}, a different and smaller function class. Measured on this data that is
    # 41.3% of training rows and 0.1% of held-out rows -- so 41% of the fit's gradient comes from a configuration
    # that essentially never occurs at test time, and the fitted phases are pulled toward it.
    #
    # This is not specific to this module. Every cross-chart block in the stack -- ashtakoot, the Uranian dial
    # distances, the composite and Davison charts -- is degenerate on the same 41% and was fitted through it.
    if TWO:
        keep = ~np.all(np.isclose(LONtr[0], LONtr[1], atol=1e-4), axis=0)
        log(f"  genuine pairs only: {int(keep.sum()):,} of {len(ytr):,} training rows "
            f"({100*(~keep).mean():.1f}% dropped as identical-chart)")
        LONtr, ytr, yr_tr = LONtr[:, :, keep], ytr[keep], yr_tr[:, keep]

    ORB = float(os.environ.get('AQ_ORB') or 0)
    Ctr, Str, kept = basis(LONtr, bodies, ORB)
    Cte, Ste, _ = basis(LONte, bodies, ORB)
    K = Ctr.shape[1]
    log(f"set {which}: {len(bodies)} bodies, orb {ORB:g} deg -> {K} basis terms · "
        f"{F} fields · train {len(ytr):,} · held out {len(yte):,}")

    # TEMPORAL inner split: the latest births of the training half become the inner validation set.
    later = yr_tr.max(0)
    cutoff = np.quantile(later, 0.85)
    inner = later > cutoff
    log(f"  inner validation = training births after {cutoff:.0f} ({inner.sum():,} rows), a TEMPORAL split")

    best_te = None
    aucs = []
    for seed in range(SEEDS):
        m = Coherent(K, F, seed=seed)
        rng = np.random.default_rng(1000 + seed)
        fit = ~inner
        idx = np.where(fit)[0]
        best_iv, best_state, bad = -1, None, 0
        for ep in range(EPOCHS):
            rng.shuffle(idx)
            for s in range(0, len(idx), 4096):
                b = idx[s:s + 4096]
                if len(b) < 64:
                    continue
                m.step(Ctr[b], Str[b], ytr[b].astype(float), LR, L2)
            ziv, _, _, _ = m.logit(Ctr[inner], Str[inner])
            a = auc(ytr[inner], ziv)
            if TRACE:
                log(f"    seed {seed} epoch {ep:>3} inner {a:.4f}")
            if a > best_iv + 1e-5:
                best_iv, bad = a, 0
                best_state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(),
                              m.c, m.mu.copy(), m.sd.copy())
            else:
                bad += 1
                if bad >= PATIENCE:
                    break
        m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = best_state
        zte, _, _, ute = m.logit(Cte, Ste)
        a_te = auc(yte, zte)
        aucs.append(a_te)
        log(f"  seed {seed}: inner (temporal) {best_iv:.4f} -> HELD OUT {a_te:.4f}")
        if best_te is None or best_iv > best_te[0]:
            best_te = (best_iv, zte, ute, m)

    # THE ONE PERMITTED COMPARISON: the two-parameter logistic on the age gap.
    #
    # It needs no fitting. b0 + b1*gap is MONOTONE in gap, and AUC is invariant under any monotone transform of
    # the score, so the logistic's AUC is exactly max(AUC(gap), 1 - AUC(gap)) -- the sign of b1 being the only
    # thing the fit decides. The gradient-descent version of this overflowed np.exp and reported the same number
    # less reliably.
    #
    # Note what the dataset's own column definition does to this baseline: with the OLDER partner always first,
    # the gap is non-negative by construction, so the SIGNED form that once distinguished man-older from
    # woman-older is not expressible here. No sex is read anywhere in this dataset.
    gap_te = (yr_te[1] - yr_te[0]).astype(float)
    absent = (yr_te[0] == 0) | (yr_te[1] == 0)
    assert not absent.any(), "a held-out row with an absent partner has no age gap"
    g = auc(yte, gap_te)
    gap_auc = max(g, 1 - g)

    mean, sd = float(np.mean(aucs)), float(np.std(aucs))
    print(f"\n  COHERENT FIELD, set '{which}', {F} fields over {K} basis terms")
    print(f"    held-out AUC over {SEEDS} seeds: {mean:.4f} +- {sd:.4f}   (best-inner seed {auc(yte, best_te[1]):.4f})")
    print(f"    age-gap logistic (2 parameters), same rows: {gap_auc:.4f}")
    out = {"set": which, "fields": F, "basis": K, "held_out_mean": mean, "held_out_sd": sd,
           "seeds": [float(a) for a in aucs], "age_gap": gap_auc}
    d = os.environ.get("AQ_OUT", "/tmp/aqcoh")
    json.dump(out, open(os.path.join(d, f"coherent_{which}.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(d, f"coherent_{which}_fields.npz"),
                        test_fields=best_te[2].astype(np.float32))
    print(f"    wrote {d}/coherent_{which}.json")


if __name__ == "__main__":
    if os.environ.get("AQ_GRADCHECK") or "--gradcheck" in sys.argv:
        _gradcheck()
    else:
        _gradcheck()
        main()
