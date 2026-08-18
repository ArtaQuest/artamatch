# %% [markdown]
# # ArtaMatch: the coherent phasor field at scale
#
# $$F_f(\text{chart}) \;=\; \Bigl|\, b_f \;+\; \sum_k w_{fk}\, e^{\,i\,h_k\,\theta_k}\,\Bigr|^{2},
#   \qquad w_{fk} = a_{fk}\,e^{-i p_{fk}}$$
#
# Each body's ecliptic longitude $\theta_k$ is the phase of a phasor; amplitudes and phase offsets are
# **fitted**. The squared modulus is an interference intensity — large where the chosen bodies reinforce,
# small where they cancel. It contains the classical aspect as its two-body case,
# $|e^{i\theta_1}+e^{i\theta_2}|^2 = 2 + 2\cos(\theta_1-\theta_2)$, and generalises it to fitted multi-body
# resonances including every cross-partner contact at once.
#
# ### What scaling actually buys here
#
# A laptop sweep of 27 configurations found that **8 fields beat 64** — capacity was never the binding limit,
# so simply making the bank wider is wasted GPU. Two things do scale:
#
# 1. **The basis.** Locally it was 7 harmonics; here it is up to 24, over all 18 bodies and both charts.
# 2. **The restarts.** $|\cdot|^2$ of a sum of phasors is a badly non-convex objective, and a single
#    initialisation finds a local optimum. Hundreds of independent restarts, each selected on the inner
#    temporal split, is the honest way to search it.
#
# ### The rules this notebook keeps
#
# * **Selection never touches the held-out set.** Every fit early-stops on an *inner temporal* split — the
#   latest births of the training half, mirroring the outer split. Configurations are ranked by inner AUC and the
#   winner is chosen there; only then is a held-out number read.
# * **Identical-chart rows are dropped.** 41.3% of training rows give both partners the same instant (an absent
#   partner inherits the other's), against 0.1% of held-out rows. Fitting a cross-chart model through them
#   trains on a configuration that never occurs at test time.
# * **An orb filter bounds the harmonic.** Birth *dates* only, no times: at a fixed hour the Moon carries
#   ±6.6°, so at $h=12$ its phase error is ±79° and the term is noise with a plausible name.
# * **Three numbers are reported, not one:** held-out AUC, the age-gap logistic (the one permitted
#   comparison), and the **gap-matched** AUC — the field's AUC *within* 1-year age-gap bands. A slow body's
#   phase difference between partners is a near-linear read of the age gap, so without that control a field can
#   score well while carrying nothing astrological.

# %%
import json, math, time
import numpy as np
import torch

T0 = time.time()
DEV = "cuda" if torch.cuda.is_available() else "cpu"
_card = torch.cuda.get_device_name(0) if DEV == "cuda" else "no gpu"
print(f"torch {torch.__version__} · device {DEV} · {_card}")
if DEV == "cuda":
    _cap = torch.cuda.get_device_capability(0)
    print(f"compute capability {_cap[0]}.{_cap[1]}")
    # Kaggle's DEFAULT accelerator is a Tesla P100 at capability 6.0, and the preinstalled torch supports 7.0+
    # only -- every cuda call on it raises. The kernel must therefore request NvidiaTeslaT4 (sm_75) in its
    # metadata, not merely enable_gpu. Say so loudly rather than falling back to a CPU fit that would take days.
    if _cap[0] < 7:
        raise SystemExit(f"{_card} is capability {_cap[0]}.{_cap[1]} and this torch needs 7.0+. "
                         f"Push with machine_shape=NvidiaTeslaT4.")
torch.backends.cuda.matmul.allow_tf32 = True

# %%
# FIND THE INPUT, DO NOT ASSUME ITS PATH. The first run of this notebook died with FileNotFoundError on a
# hardcoded /kaggle/input/artamatch-longitudes/lon.npz: the dataset had been created seconds earlier and Kaggle
# had not finished processing it, so the mount was not there yet. A hardcoded path turns that into an error
# about a missing file rather than about a missing dataset, so the search prints what IS mounted.
import glob
_hits = sorted(glob.glob("/kaggle/input/**/lon.npz", recursive=True))
if not _hits:
    _have = sorted(glob.glob("/kaggle/input/*")) or ["(nothing mounted at all)"]
    raise SystemExit("lon.npz is not mounted. /kaggle/input holds: " + ", ".join(_have)
                     + "\n  If the dataset was just created, wait for Kaggle to finish processing it and rerun.")
print(f"reading {_hits[0]}")
Z = np.load(_hits[0])
LONtr, LONte = Z["lon_train"], Z["lon_test"]
ytr_all, yte = Z["y_train"].astype(np.int64), Z["y_test"].astype(np.int64)
yr_tr_all, yr_te = Z["yr_train"], Z["yr_test"]
print(f"train {LONtr.shape} · held out {LONte.shape}")

# Drop the identical-chart rows: 41% of the training half, 0.1% of the held-out half.
genuine = ~np.all(np.isclose(LONtr[0], LONtr[1], atol=1e-4), axis=0)
LONtr, ytr, yr_tr = LONtr[:, :, genuine], ytr_all[genuine], yr_tr_all[:, genuine]
print(f"genuine pairs {int(genuine.sum()):,} of {len(genuine):,} "
      f"({100*(~genuine).mean():.1f}% dropped as identical-chart)")

# The inner split is TEMPORAL, mirroring the outer one.
later = yr_tr.max(0)
CUT = np.quantile(later, 0.85)
inner = torch.tensor(later > CUT, device=DEV)
print(f"inner validation: training births after {CUT:.0f} ({int((later>CUT).sum()):,} rows)")

# %%
SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO = range(10)
SETS = {"fast": (SUN, MOON, MERCURY, VENUS, MARS),
        "classical": (SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN),
        "all18": tuple(range(18))}
DAILY = {SUN: .9856, MOON: 13.176, MERCURY: 4.09, VENUS: 1.60, MARS: .524, JUPITER: .083,
         SATURN: .0335, URANUS: .0117, NEPTUNE: .006, PLUTO: .004}


def basis(LON, bodies, harmonics, orb):
    """cos/sin of h*theta for every admitted (harmonic, body, chart), as float32 GPU tensors."""
    rad = math.pi / 180.0
    cols = []
    for h in harmonics:
        for b in bodies:
            if orb and h * DAILY.get(b, 0.3) / 2.0 > orb:
                continue
            for s in (0, 1):                       # older chart, younger chart
                cols.append(h * LON[s, b] * rad)
    P = torch.tensor(np.stack(cols, 1), dtype=torch.float32, device=DEV)
    return torch.cos(P), torch.sin(P)


def auc_np(y, s):
    y = np.asarray(y, np.int64); s = np.asarray(s, np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort"); ys, ss = y[o], s[o]
    r = np.empty(len(ss)); i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0; i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def matched_auc(y, s, band):
    """AUC pooled over eligible pairs WITHIN bands of a nuisance quantity. Pooling by pair count, not an
    average of per-band AUCs, because a 40-row band must not outweigh a 4,000-row one."""
    num = den = 0.0
    for b in np.unique(band):
        m = band == b
        yy, ss = y[m], s[m]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if n1 and n0:
            num += auc_np(yy, ss) * n1 * n0; den += n1 * n0
    return num / den if den else float("nan")


gap_te = (yr_te[1] - yr_te[0]).astype(float)
_a = auc_np(yte, gap_te)
GAP = max(_a, 1 - _a)
BAND = (np.abs(gap_te) // 1) * 1
print(f"age-gap logistic on the held-out rows: {GAP:.4f}   "
      f"(inside its own 1-year bands: {matched_auc(yte, (1 if _a>.5 else -1)*gap_te, BAND):.4f}, "
      f"which is how we know the control works)")

# %%
class Coherent(torch.nn.Module):
    """A bank of F coherent fields, then a linear head. The complex weight w = a*exp(-i p) is held in
    Cartesian coordinates (A1 = Re w, A2 = -Im w): the same function as the polar form, with a flat parameter
    space and no phase wrapping to fight."""

    def __init__(self, K, F):
        super().__init__()
        sc = 1.0 / math.sqrt(K)
        self.A1 = torch.nn.Parameter(torch.randn(F, K) * sc)
        self.A2 = torch.nn.Parameter(torch.randn(F, K) * sc)
        self.br = torch.nn.Parameter(torch.randn(F) * 0.3)
        self.bi = torch.nn.Parameter(torch.randn(F) * 0.3)
        self.head = torch.nn.Linear(F, 1)
        torch.nn.init.zeros_(self.head.weight); torch.nn.init.zeros_(self.head.bias)
        self.register_buffer("mu", torch.zeros(F)); self.register_buffer("sd", torch.ones(F))

    def fields(self, C, S):
        ReS = C @ self.A1.T + S @ self.A2.T
        ImS = S @ self.A1.T - C @ self.A2.T
        Zr, Zi = ReS + self.br, ImS + self.bi
        return Zr * Zr + Zi * Zi

    def forward(self, C, S, update=False):
        u = self.fields(C, S)
        if update:
            with torch.no_grad():
                self.mu.mul_(0.9).add_(0.1 * u.mean(0))
                self.sd.mul_(0.9).add_(0.1 * (u.std(0) + 1e-6))
        return self.head((u - self.mu) / self.sd).squeeze(1)


def fit(C, S, y, inner_mask, F, l2, lr, steps=1500, patience=150):
    """One full-batch fit, early-stopped on the inner temporal split. Full batch because the whole training
    half is a single 53k x K matmul on a GPU -- minibatching would only add noise and wall-clock."""
    fitm = ~inner_mask
    Cf, Sf, yf = C[fitm], S[fitm], y[fitm].float()
    Ci, Si = C[inner_mask], S[inner_mask]
    yi = y[inner_mask].cpu().numpy()
    m = Coherent(C.shape[1], F).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=lr, weight_decay=l2)
    lossf = torch.nn.BCEWithLogitsLoss()
    best, best_state, bad = -1.0, None, 0
    for t in range(steps):
        opt.zero_grad(set_to_none=True)
        lossf(m(Cf, Sf, update=True), yf).backward()
        opt.step()
        if t % 15 == 0:
            with torch.no_grad():
                a = auc_np(yi, m(Ci, Si).cpu().numpy())
            if a > best + 1e-5:
                best, bad = a, 0
                best_state = {k: v.detach().clone() for k, v in m.state_dict().items()}
            else:
                bad += 15
                if bad >= patience:
                    break
    m.load_state_dict(best_state)
    return m, best

# %%
# The search. Configurations are SAMPLED, each fitted from several independent initialisations, and ranked by
# inner temporal AUC. Nothing below reads yte.
HARM_POOL = [(1, 2, 3, 4, 6, 8, 12),
             (1, 2, 3, 4, 5, 6, 8, 9, 10, 12),
             tuple(range(1, 13)),
             tuple(range(1, 19)),
             tuple(range(1, 25))]
BUDGET_S = float(__import__("os").environ.get("AQ_BUDGET", 8400))     # leave room inside Kaggle's 9h ceiling
rng = np.random.default_rng(0)
ytr_t = torch.tensor(ytr, device=DEV)
cache, trials = {}, []
trial = 0
while time.time() - T0 < BUDGET_S:
    which = str(rng.choice(["fast", "classical", "all18"]))
    hi = int(rng.integers(len(HARM_POOL))); harm = HARM_POOL[hi]
    orb = float(rng.choice([0.0, 15.0, 30.0, 60.0]))
    F = int(rng.choice([4, 8, 16, 32, 64]))
    l2 = float(10 ** rng.uniform(-5, -1.5))
    lr = float(10 ** rng.uniform(-2.7, -1.3))
    key = (which, hi, orb)
    if key not in cache:
        if len(cache) > 14:
            cache.clear(); torch.cuda.empty_cache() if DEV == "cuda" else None
        cache[key] = (basis(LONtr, SETS[which], harm, orb), basis(LONte, SETS[which], harm, orb))
    (Ctr, Str), (Cte, Ste) = cache[key]
    ivs, hos = [], []
    for _ in range(3):
        torch.manual_seed(rng.integers(1 << 30))
        m, iv = fit(Ctr, Str, ytr_t, inner, F, l2, lr)
        with torch.no_grad():
            ho = auc_np(yte, m(Cte, Ste).cpu().numpy())
        ivs.append(iv); hos.append(ho)
    trials.append({"set": which, "harmonics": list(harm), "orb": orb, "fields": F, "l2": l2, "lr": lr,
                   "basis": int(Ctr.shape[1]), "inner": float(np.mean(ivs)), "held": float(np.mean(hos)),
                   "held_sd": float(np.std(hos))})
    trial += 1
    if trial % 10 == 0:
        b = max(trials, key=lambda r: r["inner"])
        print(f"[{time.time()-T0:6.0f}s] {trial} trials · best inner {b['inner']:.4f} "
              f"({b['set']}, F={b['fields']}, K={b['basis']}, orb={b['orb']:g})", flush=True)
print(f"{trial} trials in {(time.time()-T0)/60:.1f} min")

# %%
trials.sort(key=lambda r: -r["inner"])
print(f"{'#':>3}  {'bodies':<10} {'F':>3} {'K':>5} {'orb':>4} {'nH':>3} {'L2':>9} {'lr':>8} "
      f"{'inner':>7} {'held':>7}")
for i, r in enumerate(trials[:20], 1):
    print(f"{i:>3}  {r['set']:<10} {r['fields']:>3} {r['basis']:>5} {r['orb']:>4g} {len(r['harmonics']):>3} "
          f"{r['l2']:>9.2e} {r['lr']:>8.2e} {r['inner']:>7.4f} {r['held']:>7.4f}")

W = trials[0]
print(f"\nSELECTED ON THE INNER TEMPORAL SPLIT: {W['set']}, {W['fields']} fields, "
      f"{len(W['harmonics'])} harmonics, orb {W['orb']:g}, K={W['basis']}")
print(f"  its held-out AUC        {W['held']:.4f} +- {W['held_sd']:.4f}")
print(f"  age-gap logistic        {GAP:.4f}")
print(f"  best held-out anywhere  {max(r['held'] for r in trials):.4f}  "
      f"(shown only to price what selecting on the test set would have bought)")

# The gap-blind family reported separately: fast bodies cannot encode a 0-60 year gap, since their phases wrap
# hundreds of times across it. This is the only row that could be a genuinely astrological result.
fastr = [r for r in trials if r["set"] == "fast"]
if fastr:
    bf = max(fastr, key=lambda r: r["inner"])
    print(f"\nBEST GAP-BLIND (fast bodies only), selected on inner: held out {bf['held']:.4f} "
          f"+- {bf['held_sd']:.4f}  ({len(fastr)} trials)")

# %%
# Refit the selected configuration and put it through the gap-matched control.
harm = tuple(W["harmonics"])
(Ctr, Str) = basis(LONtr, SETS[W["set"]], harm, W["orb"])
(Cte, Ste) = basis(LONte, SETS[W["set"]], harm, W["orb"])
preds = []
for s in range(8):
    torch.manual_seed(9000 + s)
    m, _ = fit(Ctr, Str, ytr_t, inner, W["fields"], W["l2"], W["lr"])
    with torch.no_grad():
        preds.append(m(Cte, Ste).cpu().numpy())
p = np.mean(preds, 0)
raw = auc_np(yte, p)
gm = matched_auc(yte, p, BAND)
rho = float(np.corrcoef(np.argsort(np.argsort(p)), np.argsort(np.argsort(gap_te)))[0, 1])
print(f"8-seed ensemble of the selected configuration")
print(f"  held-out AUC                         {raw:.4f}")
print(f"  rank correlation with the age gap    {rho:+.3f}")
print(f"  AUC with the gap held flat (1y bands){gm:>8.4f}   <- 0.50 means the score WAS the gap")
print(f"  age-gap logistic                     {GAP:.4f}")
verdict = ("carries something beyond the age gap" if gm > 0.52 else
           "is the age gap in disguise — nothing astrological survives the control")
print(f"\n  VERDICT: the coherent field {verdict}")

# %%
json.dump({"n_trials": trial, "age_gap": GAP, "selected": W, "selected_refit": {
    "held_out": raw, "gap_matched": gm, "rho_with_gap": rho},
    "best_gap_blind": (max([r for r in trials if r["set"] == "fast"], key=lambda r: r["inner"])
                       if any(r["set"] == "fast" for r in trials) else None),
    "trials": trials}, open("/kaggle/working/coherent_gpu.json", "w"), indent=1)
print(f"wrote /kaggle/working/coherent_gpu.json · total {(time.time()-T0)/60:.1f} min")
