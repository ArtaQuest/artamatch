"""The mortality-ceiling prior, from the competition's DEFINITION, with no parameter fitted to any label.

A held-out couple exists only if BOTH partners are dead by 2026, and the label is 'lasted >= 30 years'. So a
partner born in year b who is dead by 2026 died at age <= 2026-b, and for the bond to have lasted 30 years from
a start age s they must have died at age >= s+30. Under a Gompertz survival curve S(x) that gives, per partner,

    p_i = P(s+30 <= death age <= 2026-b_i) / P(death age <= 2026-b_i) = (S(s+30) - S(2026-b_i)) / (1 - S(2026-b_i))

and the couple's prior is p_older * p_younger. Standard human Gompertz: hazard B*exp(theta*x) with theta = 0.09
and B set so that S(80) = 0.5; start age s = 25. These are textbook values, stated before use, not tuned.

For a partner born 1910 the room is 116 years, S(116) ~ 0, so p ~ S(55): flat. For 1950 the room is 76 and the
condition 'died by 76' removes most of the long-lived, so p falls. For 1980 the room is 46 < 55: p = 0.
"""
import numpy as np
THETA, S80, START = 0.09, 0.5, 25
B = -np.log(S80) * THETA / (np.exp(THETA * 80) - 1)
def S(x):
    x = np.maximum(np.asarray(x, float), 0.0)
    return np.exp(-B / THETA * (np.exp(THETA * x) - 1.0))
def prior(b_older, b_younger, now=2026):
    def p(b):
        room = now - np.asarray(b, float)
        num = np.clip(S(START + 30) - S(room), 0, None)
        den = np.clip(1.0 - S(room), 1e-9, None)
        return np.where(room < START + 30, 0.0, num / den)
    return p(b_older) * p(b_younger)
if __name__ == "__main__":
    print(f"  Gompertz: theta={THETA}, S(80)={S80}, start age {START} -> B={B:.3e}; S(55)={S(55):.3f} S(76)={S(76):.3f} S(96)={S(96):.3f}")
    for L in (1905,1920,1930,1940,1950,1960,1970,1980,1990):
        print(f"    both born {L}: prior {float(prior(np.array([L]),np.array([L]))[0]):.3f}")
