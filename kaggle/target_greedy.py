"""target_greedy.py — build the labeller one keyword at a time, and show what each one bought.

Every keyword below was proposed by hand, because a keyword the sky happens to like is worth nothing
if a reader cannot see why it belongs. Each is something a person would accept as evidence about a
marriage: a divorce, a described affair, a stated devotion, a shared body of work, a spouse nursed
through a last illness. Nothing about a profession, a nationality or a century, because those name
who somebody was and when, which is the confound this project spends its life removing.

The label is then as simple as a label can be:

    score = (positive keywords present) - (negative keywords present)

so a marriage with three negative markers and one positive scores -2, and a reader can check that by
eye. Selection is forward and greedy against the astrology model's cross-validated AUC: at each step
every unused keyword is tried in both signs, the best is kept, and the gain it brought is printed. A
keyword that buys nothing is never added, and the sign the search picks is shown against the sign I
proposed — where they disagree, that is worth knowing and is printed as a disagreement rather than
quietly accepted.

Search couples only. The confirm third stays untouched for target_confirm.py.
"""
import json, os, re, sys, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))

POOL = os.path.expanduser("~/.artamatch-dev/quality_pool")
OUT = os.path.expanduser(os.environ.get("AQ_RESULT", "~/.artamatch-dev/target_greedy.json"))
LAM = float(os.environ.get("AQ_LAM", "1000"))
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))
STEPS = int(os.environ.get("AQ_STEPS", "40"))
NFOLD, SEEDS = 5, (7, 23)

# ---- proposed keywords, with the sign I would defend in advance -------------------------------
# -1 : the record says something went wrong        +1 : the record says something went right
PROPOSED = {
 # the ending, and its manner
 "divorc": -1, "dissolved": -1, "annul": -1, "separated": -1, "separation": -1,
 "estranged": -1, "ex-husband": -1, "ex-wife": -1, "former husband": -1, "former wife": -1,
 "first husband": -1, "first wife": -1, "remarri": -1, "second marriage": -1,
 # trouble the record actually describes
 "affair": -1, "mistress": -1, "adulter": -1, "unfaithful": -1, "illegitimate": -1,
 "unhappy": -1, "miserable": -1, "loveless": -1, "of convenience": -1, "arranged marriage": -1,
 "quarrel": -1, "dispute": -1, "litigat": -1, "feud": -1, "acrimon": -1, "bitter": -1,
 "violen": -1, "abuse": -1, "cruel": -1, "assault": -1, "beat her": -1,
 "abandon": -1, "deserted": -1, "left him": -1, "left her": -1, "bigam": -1, "scandal": -1,
 "alcohol": -1, "drunken": -1, "gambling": -1, "custody": -1, "alimony": -1,
 "childless": -1, "no children": -1, "brief marriage": -1, "short-lived": -1,
 # a marriage that ran its course
 "his widow": 1, "her widower": 1, "was widowed": 1, "survived by": 1,
 "until his death": 1, "until her death": 1, "until he died": 1, "until she died": 1,
 "fifty years": 1, "forty years": 1, "golden wedding": 1, "lifelong": 1,
 # stated warmth
 "devot": 1, "beloved": 1, "adored": 1, "cherish": 1, "happily": 1, "happy marriage": 1,
 "inseparable": 1, "love letters": 1, "deeply in love": 1, "mourned": 1, "grief": 1,
 "nursed": 1, "supported him": 1, "supported her": 1, "encouraged": 1,
 # something built together
 "collaborat": 1, "co-wrote": 1, "co-author": 1, "co-founded": 1, "partnership": 1,
 "together they": 1, "worked together": 1, "jointly": 1, "his muse": 1, "her muse": 1,
 "model for": 1, "duet": 1, "co-starred": 1,
 # a household
 "children": 1, "sons": 1, "daughters": 1, "grandchildren": 1,
 # the same ideas in the other big Wikipedias
 "scheidung": -1, "geschieden": -1, "divorce en": -1, "divorciad": -1, "развод": -1,
 "離婚": -1, "affaire": -1, "amante": -1, "любовниц": -1,
 "witwe": 1, "veuve": 1, "viuda": 1, "вдов": 1,
 "zusammen": 1, "ensemble": 1, "juntos": 1, "вместе": 1,
 "kinder": 1, "enfants": 1, "hijos": 1, "дети": 1,
}


def fast_auc(y, s):
    o = np.argsort(s, kind="stable")
    r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    ss = s[o]; i = 0
    while i < len(ss):
        j = i + 1
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if j > i + 1:
            r[o[i:j]] = (i + 1 + j) / 2.0
        i = j
    n1 = y.sum(); n0 = len(y) - n1
    return 0.5 if n1 == 0 or n0 == 0 else (r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


class Sky:
    """The astrology side, factorised once.

    MEMORY. An earlier version kept A = Xc[tr] for each of ten folds — ten copies of a 7,700 x 3,000
    matrix, about 1.9 GB, on top of everything else, and it was killed. It is also unnecessary: the
    ridge target is zero on every row outside the fold, so

        Aᵀ t  =  Xcᵀ t_full        with t_full zero off-fold

    and the design never needs slicing at all. One copy of Xc plus the Cholesky factors, and the
    prediction indexes rows of Xc rather than holding a second block."""

    def __init__(self, X, gid):
        from scipy.linalg import cho_factor
        self.Xc = np.ascontiguousarray(X - X.mean(0))
        self.folds = []
        for s in SEEDS:
            fold = np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid]
            for k in range(NFOLD):
                tr = fold != k
                A = self.Xc[tr]
                c = cho_factor(A.T @ A + LAM * np.eye(A.shape[1]), lower=True, check_finite=False)
                del A
                self.folds.append((tr, c, np.where(~tr)[0]))

    def auc(self, y, mask):
        from scipy.linalg import cho_solve
        n = len(y)
        preds = np.full((len(SEEDS), n), np.nan)
        t_full = np.zeros(n)
        for i, (tr, c, te) in enumerate(self.folds):
            trm = tr & mask
            if trm.sum() < 200 or len(np.unique(y[trm])) < 2:
                continue
            t_full[:] = 0.0
            t_full[trm] = y[trm] - y[trm].mean()
            beta = cho_solve(c, self.Xc.T @ t_full, check_finite=False)
            preds[i // NFOLD, te] = self.Xc[te] @ beta
        outs = []
        for p in preds:
            m = mask & np.isfinite(p)
            if m.sum() < 200 or len(np.unique(y[m])) < 2:
                return 0.5
            outs.append(fast_auc(y[m].astype(int), p[m]))
        return float(np.mean(outs))


def main():
    from target_fast import load
    sp, _H, gid, X, names = load()
    txt = sp.desc.fillna("").astype(str).str.lower()
    keys = list(PROPOSED)
    P = np.column_stack([txt.str.contains(re.escape(k) if " " not in k and not k.isascii()
                                          else k, regex=True).to_numpy(float) for k in keys])
    rate = P.mean(0)
    live = [i for i in range(len(keys)) if rate[i] >= float(os.environ.get("AQ_MINRATE","0.0025"))]
    print(f"  {len(sp):,} search couples · {len(keys)} proposed keywords, "
          f"{len(live)} fire in at least 0.4% of records")
    dropped = [keys[i] for i in range(len(keys)) if i not in live]
    if dropped:
        print(f"  too rare to use: {', '.join(dropped[:14])}"
              f"{' ...' if len(dropped) > 14 else ''}")
    t0 = time.time()
    S = Sky(X.astype(np.float64), gid)
    print(f"  sky factorised in {time.time()-t0:.0f}s · {X.shape[1]:,} statements\n")

    # Label by the SIGN of the integer score, not by a quantile band. With one keyword the score takes
    # two values and a 30/70 band collapses to a single point, so every candidate scored 0.5 and the
    # greedy stopped before it started. The sign rule is well defined from the first keyword and reads
    # the way a person would say it: more positive markers than negative means the record says it went
    # well, the reverse means it went badly, and a tie means the record does not say.
    MINCOV = float(os.environ.get("AQ_MINCOV", "0.30"))

    def ev(sel):
        if not sel:
            return 0.5, 0
        sc = sum(sg * P[:, i] for i, sg in sel)
        y = (sc > 0).astype(int)
        m = sc != 0
        if m.sum() < MINCOV * len(sc):
            return 0.5, int(m.sum())
        p1 = y[m].mean()
        if p1 < 0.1 or p1 > 0.9:            # a target that is 95% one class measures almost nothing
            return 0.5, int(m.sum())
        return S.auc(y, m), int(m.sum())

    # A single keyword cannot produce two classes — every row it fires on gets one label and the rest
    # get none — so the first move is a PAIR, searched exhaustively over the live keywords in both
    # sign assignments.
    print(f"  seeding with the best opposed pair ({len(live)*(len(live)-1)//2:,} pairs)...",
          flush=True)
    seed = None
    for ii in range(len(live)):
        for jj in range(ii + 1, len(live)):
            i, j = live[ii], live[jj]
            for sg in ((1.0, -1.0), (-1.0, 1.0)):
                a, nlab = ev([(i, sg[0]), (j, sg[1])])
                if seed is None or a > seed[0]:
                    seed = (a, [(i, sg[0]), (j, sg[1])], nlab)
    cur, sel, nlab = seed[0], list(seed[1]), seed[2]
    used = {i for i, _ in sel}
    path = []
    print(f"\n  {'step':>4}  {'keyword':<22}{'sign':>5}{'fires':>8}{'labelled':>10}"
          f"{'AUC':>9}{'gain':>9}")
    print("  " + "-" * 72)
    for (i, sg) in sel:
        flag = "" if sg == PROPOSED[keys[i]] else "   <- opposite to my proposal"
        print(f"  {'seed':>4}  {keys[i]:<22}{'+' if sg > 0 else '-':>5}{rate[i]*100:>7.1f}%"
              f"{nlab:>10,}{cur:>9.4f}{'':>9}{flag}")
        path.append({"step": 0, "keyword": keys[i], "sign": int(sg),
                     "proposed_sign": PROPOSED[keys[i]], "fires": float(rate[i]), "auc": cur})
    for step in range(1, STEPS + 1):
        best = None
        for i in live:
            if i in used:
                continue
            for sg in (1.0, -1.0):
                a, nl = ev(sel + [(i, sg)])
                if best is None or a > best[0]:
                    best = (a, i, sg, nl)
        if best is None or best[0] <= cur + 1e-5:
            print(f"  stopped after {len(sel)} keywords: nothing left improves it")
            break
        a, i, sg, nl = best
        sel.append((i, sg)); used.add(i)
        flag = "" if sg == PROPOSED[keys[i]] else "   <- opposite to my proposal"
        print(f"  {step:>4}  {keys[i]:<22}{'+' if sg > 0 else '-':>5}{rate[i]*100:>7.1f}%"
              f"{nl:>10,}{a:>9.4f}{a-cur:>+9.4f}{flag}")
        path.append({"step": step, "keyword": keys[i], "sign": int(sg),
                     "proposed_sign": PROPOSED[keys[i]], "fires": float(rate[i]), "auc": a})
        cur = a

    print(f"\n  final: {len(sel)} keywords · astrology CV AUC {cur:.4f} on the search half")
    agree = sum(1 for p in path if p["sign"] == p["proposed_sign"])
    print(f"  {agree}/{len(path)} keywords kept the sign I proposed in advance")
    json.dump({"lam": LAM, "keep": KEEP, "auc": cur,
               "selected": {keys[i]: int(sg) for i, sg in sel},
               "path": path, "proposed": PROPOSED},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
