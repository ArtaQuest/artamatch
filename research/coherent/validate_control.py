"""
validate_control.py — prove the gap-matched estimator does what it claims, on cases with known answers.

WHY THIS EXISTS. Every negative conclusion in this investigation rests on one estimator: AUC pooled over
eligible pairs within 1-year age-gap bands. It has been shown to return 0.5000 for the age gap itself, which
proves it DESTROYS the thing it is meant to hold flat. That is only half of what it must do. If it also
destroyed genuine gap-independent signal, "nothing survives the control" would be a property of my arithmetic
rather than of the data, and the whole finding would be worthless.

So: four planted features on the REAL held-out labels and the REAL age gaps, each with a known answer.

  1. pure gap        -> raw high, matched 0.50      (the control must remove it)
  2. pure signal     -> raw == matched              (the control must PRESERVE it)
  3. half and half   -> both above 0.50, matched < raw
  4. pure noise      -> both 0.50
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coherent_fit import auc                                        # noqa: E402

Z = np.load("/tmp/aqcoh/lon.npz")
y = Z["y_test"].astype(np.int64)
yr = Z["yr_test"]
gap = np.abs(yr[1] - yr[0]).astype(float)
band = (gap // 1) * 1
rng = np.random.default_rng(11)


def matched(y, s, band):
    num = den = 0.0
    for b in np.unique(band):
        m = band == b
        yy, ss = y[m], s[m]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if n1 and n0:
            num += auc(yy, ss) * n1 * n0
            den += n1 * n0
    return num / den if den else float("nan")


# A gap-INDEPENDENT planted signal: a monotone function of the label plus noise, with no reference to the gap.
# Its strength is tuned so its raw AUC lands near the values actually observed on real blocks (~0.55-0.60),
# which is the regime the conclusion depends on.
def planted(strength):
    return y * strength + rng.normal(size=len(y))


cases = [
    ("pure age gap (must be removed)", -gap + 1e-9 * rng.normal(size=len(y))),
    ("pure planted signal, gap-independent (must SURVIVE)", planted(0.35)),
    ("planted signal, weaker (must survive)", planted(0.20)),
    ("half gap + half planted signal", -0.5 * (gap - gap.mean()) / gap.std() + 0.5 * planted(0.35)),
    ("pure noise (must be 0.50 both ways)", rng.normal(size=len(y))),
]
print(f"  held-out rows {len(y):,} · {len(np.unique(band))} one-year gap bands\n")
print(f"  {'planted feature':<52} {'raw':>7} {'matched':>8}  {'verdict'}")
ok = True
for name, s in cases:
    r, m = auc(y, s), matched(y, s, band)
    r, m = max(r, 1 - r), (m if abs(m - 0.5) >= abs((1 - m) - 0.5) else 1 - m)
    if "must be removed" in name:
        good = abs(m - 0.5) < 0.015
    elif "SURVIVE" in name or "must survive" in name:
        good = abs(m - r) < 0.02 and r > 0.53
    elif "half" in name:
        good = m > 0.52 and m < r
    else:
        good = abs(r - 0.5) < 0.02 and abs(m - 0.5) < 0.02
    ok &= good
    print(f"  {name:<52} {r:>7.4f} {m:>8.4f}  {'OK' if good else 'FAILED'}")
print()
if ok:
    print("  THE CONTROL IS SOUND: it removes the age gap to within 0.015 of chance AND preserves a")
    print("  gap-independent signal to within 0.02 of its raw AUC. So a real block scoring 0.49 gap-matched")
    print("  is a real absence of gap-independent signal, not an artefact of the estimator.")
else:
    raise SystemExit("  THE CONTROL IS NOT SOUND — every conclusion drawn from it must be withdrawn")
