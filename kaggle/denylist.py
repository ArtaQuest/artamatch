"""denylist.py — operator 2026-08-26: only astrology/numerology doctrine may enter the bank.
Calendar demographics are OUT: weekday pairs, the bare age gap, same-birthday coincidences, and
biorhythms (a 20th-century pseudoscience but neither astrology nor numerology). A conjunction is
out if ANY clause is out."""
import re
NONDOCTRINE = re.compile(
    r"^(varapair|his_vara|her_vara|gap_years|gap_369_taboo|same_birthday|same_birth_month|"
    r"bio_physical|bio_emotional|bio_intellectual)")

def clause_ok(name):
    return not NONDOCTRINE.match(name)

def rule_ok(name):
    return all(clause_ok(p) for p in name.split(" AND "))
