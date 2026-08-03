#!/usr/bin/env python3
"""Least-squares fit of the Lahiri ayanamsa to a quadratic in Julian centuries from J2000.

Reads tests/golden.json (Swiss Ephemeris SIDM_LAHIRI) and prints the coefficients that
src/engine/ephemeris.ts hard-codes, plus the residual it achieves.
"""
import json, os
here = os.path.dirname(__file__)
g = json.load(open(os.path.join(here, "..", "tests", "golden.json")))
T = [(r["jd"] - 2451545.0) / 36525 for r in g["rows"]]
A = [r["ayanamsa"] for r in g["rows"]]

n = len(T)
# Normal equations for a + b*T + c*T^2
S = [sum(t ** k for t in T) for k in range(5)]
R = [sum(a * (t ** k) for t, a in zip(T, A)) for k in range(3)]
M = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]

def solve(M, R):
    M = [row[:] + [r] for row, r in zip(M, R)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                for c in range(i, 4): M[r][c] -= f * M[i][c]
    return [M[i][3] / M[i][i] for i in range(3)]

c0, c1, c2 = solve(M, R)
res = [abs(c0 + c1 * t + c2 * t * t - a) for t, a in zip(T, A)]
print(f"AYANAMSA_C0 = {c0:.8f}")
print(f"AYANAMSA_C1 = {c1:.8f}")
print(f"AYANAMSA_C2 = {c2:.8f}")
print(f"\nresidual over {n} samples 1900-2100: mean {sum(res)/n:.6f}deg  max {max(res):.6f}deg")
