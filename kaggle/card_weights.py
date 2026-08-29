"""card_weights.py — group the shipped statements into the cards the page shows before a match.

Every statement in the model reads BOTH birth dates, so none of them can be displayed against one
person. What the page can honestly show, once you have entered your own date, is WHAT the comparison is
about to read and how much of the model each part carries. That is what these cards are.

Groups are by which bodies the statement is about, because that is what a reader can be told in one
line. Share is the summed absolute weight, which is the model's own answer to "how much of me is this".
"""
import json, os, re, sys

SRC = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_signal.json")
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/almanac/quality_card_weights.json")
SCORES = os.path.expanduser("~/.artamatch-dev/interaction_scores.json")

GROUPS = [
    ("feeling", "How your feelings meet theirs",
     "Moon and Venus contacts — the two bodies every tradition reads for affection.",
     lambda n: bool(re.match(r"^his_(moon|venus)_\w+_her_", n) or re.search(r"_her_(moon|venus)$", n))),
    ("daily", "How you meet day to day",
     "Sun, Mercury and Mars contacts — presence, talk and friction.",
     lambda n: bool(re.match(r"^his_(sun|mercury|mars)_\w+_her_", n) or re.search(r"_her_(sun|mercury|mars)$", n))),
    ("holding", "What holds you and what opens you",
     "Saturn and Jupiter contacts — the binding planet and the expanding one.",
     lambda n: bool(re.match(r"^his_(saturn|jupiter)_\w+_her_", n) or re.search(r"_her_(saturn|jupiter)$", n))),
    ("deep", "The contacts you do not choose",
     "Uranus, Neptune and Pluto contacts — the slow planets, read as what a couple is handed.",
     lambda n: bool(re.match(r"^his_(uranus|neptune|pluto)_\w+_her_", n) or re.search(r"_her_(uranus|neptune|pluto)$", n))),
    ("cycles", "The sky you were both born under",
     "Rudhyar's cycle phases — where a pair of slow planets stood in their own cycle at each birth.",
     lambda n: bool(re.match(r"^cycle", n))),
]


def main():
    M = json.load(open(SRC))
    W = M["weights"]
    sc = json.load(open(SCORES)) if os.path.exists(SCORES) else {}
    base = lambda k: k[4:-1] if k.startswith("NOT(") and k.endswith(")") else k

    assigned, cards = set(), []
    for key, label, blurb, test in GROUPS:
        mem = [k for k in W if k not in assigned and test(base(k))]
        assigned |= set(mem)
        if not mem:
            continue
        inter = [sc[base(k)] for k in mem if base(k) in sc]
        cards.append({"key": key, "label": label, "blurb": blurb, "statements": len(mem),
                      "weight": round(sum(abs(W[k]) for k in mem), 4),
                      "mean_interaction": round(sum(inter) / len(inter), 3) if inter else None})
    rest = [k for k in W if k not in assigned]
    if rest:
        cards.append({"key": "other", "label": "Everything else the model reads",
                      "blurb": "Statements that fall outside the four groups above.",
                      "statements": len(rest), "weight": round(sum(abs(W[k]) for k in rest), 4),
                      "mean_interaction": None})
    tot = sum(c["weight"] for c in cards) or 1.0
    for c in cards:
        c["share"] = round(c["weight"] / tot, 3)
    cards.sort(key=lambda c: -c["share"])

    out = {"ranked_by": "summed absolute weight of the statements in each group",
           "note": "every statement here reads both birth dates, and more than half of its variance "
                   "comes from how far apart the two births are rather than from when they happened",
           "n_statements": len(W), "cv_auc": M["cv_auc"], "test_auc": M["test_auc"], "cards": cards}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"  {len(W)} statements in {len(cards)} cards")
    for c in cards:
        print(f"    {c['share']*100:5.1f}%  {c['statements']:>3} stmts  {c['label']}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
