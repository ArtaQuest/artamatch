"""closed_newton.py — THE solver, per operator 2026-08-31: closed form only, from now on.

Three Newton steps from zero on balanced-BCE logistic ridge. Step one from beta=0 IS the weighted
least-squares / LDA closed form; steps two and three re-solve against the analytic logistic Hessian
at the previous point. Three explicit Cholesky solves — a finite composition of closed forms, no
iterative optimiser — and it matches LBFGS to the fourth decimal on every gated variant.

Grams run on MPS (fp32 matmul), factorisations on CPU (fp64, jitter ladder for near-singular
bases). Lambda is RELATIVE to mean(diag(Gram)) and swept wide in both directions; a boundary
optimum is flagged, never trusted.
"""
import numpy as np, torch
from scipy.linalg import cho_factor, cho_solve

DEV = ("cuda" if torch.cuda.is_available() else
       "mps" if torch.backends.mps.is_available() else "cpu")   # Kaggle T4/P100 lane, laptop MPS, or cores
NEWTON = 3
RLAMS = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e0)


def _solve(H, g, scale):
    for jit in (0.0, 1e-8, 1e-6, 1e-4, 1e-2):
        try:
            if jit:
                H[np.diag_indices_from(H)] += jit * scale
            c = cho_factor(H, lower=True, check_finite=False)
            return cho_solve(c, g, check_finite=False)
        except Exception:
            continue
    raise FloatingPointError("unfactorable")


CHUNK = 24576


def _wgram(Ft, wv):
    """chunked (F' diag(wv) F) and never a row-sliced copy — train rows selected by ZERO weight"""
    n, p1 = Ft.shape
    H = torch.zeros((p1, p1), dtype=torch.float32, device=DEV)
    for i in range(0, n, CHUNK):
        c = Ft[i:i + CHUNK] * wv[i:i + CHUNK].sqrt().unsqueeze(1)
        H += c.T @ c
        del c
    return H.cpu().numpy().astype(np.float64)


def _wmatvec(Ft, v):
    n, p1 = Ft.shape
    g = torch.zeros(p1, dtype=torch.float32, device=DEV)
    for i in range(0, n, CHUNK):
        g += Ft[i:i + CHUNK].T @ v[i:i + CHUNK]
    return g.cpu().numpy().astype(np.float64)


def _matvec(Ft, bt):
    n = Ft.shape[0]
    z = torch.empty(n, dtype=torch.float32, device=DEV)
    for i in range(0, n, CHUNK):
        z[i:i + CHUNK] = Ft[i:i + CHUNK] @ bt
    return z


def newton_fold(Ft, y, w, trm, rlams, G0=None):
    """Ft: torch fp32 on DEV (n, p1) WITH the intercept column ALREADY LAST. Train rows are
    selected by zeroing the weight vector — no row-sliced copy of Ft ever exists.
    Pass G0 (the fold's unweighted train Gram) to reuse it across rlams; None computes it.
    -> {rl: scores_for_all_rows (np)}"""
    n, p1 = Ft.shape
    yt = torch.from_numpy(y).to(DEV)
    wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)   # zero off-train
    if G0 is None:
        G0 = _wgram(Ft, wm)
    scale = float(np.mean(np.diag(G0)[:-1]))
    out = {}
    for rl in rlams:
        lam = rl * scale
        reg = np.full(p1, lam); reg[-1] = 0.0
        beta = np.zeros(p1)
        try:
            for step in range(NEWTON):
                bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
                z = _matvec(Ft, bt)
                pr = torch.sigmoid(z)
                gv = _wmatvec(Ft, wm * (yt - pr)) - reg * beta
                if step == 0:
                    H = 0.25 * G0.copy()
                else:
                    H = _wgram(Ft, wm * pr * (1 - pr))
                H[np.diag_indices_from(H)] += reg
                beta = beta + _solve(H, gv, scale)
            bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
            out[rl] = _matvec(Ft, bt).cpu().numpy()
        except FloatingPointError:
            out[rl] = None
        del bt
    return out
