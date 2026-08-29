"""explain_rules.py — turn every surviving statement into a sentence a person can read.

A model is only explainable if the explanation reaches the reader, not just the analyst. Each rule
becomes four things: the TRADITION it comes from, a short TITLE, what it PLAINLY says about the two
dates, and the READING that tradition gives it. Nothing here is fitted — this is the doctrine's own
vocabulary, written out.

explain(name) -> {tradition, title, plain, reading}
Unknown patterns return a truthful fallback rather than an invented meaning.
"""
import os
import re
import sys

BODY = {
    "sun": ("Sun", "who someone is at the core — vitality, pride, the will to shine"),
    "moon": ("Moon", "feelings, instinct, what makes a person feel at home"),
    "mercury": ("Mercury", "talk, thought and the everyday exchange between two people"),
    "venus": ("Venus", "love, affection, beauty and what someone treasures"),
    "mars": ("Mars", "desire, drive and the way a person fights"),
    "jupiter": ("Jupiter", "generosity, faith, growth and good fortune"),
    "saturn": ("Saturn", "duty, endurance, patience and the weight of time"),
    "uranus": ("Uranus", "freedom, surprise and the urge to break the pattern"),
    "neptune": ("Neptune", "dreams, compassion and the blur between two souls"),
    "pluto": ("Pluto", "depth, power and the things that transform a person"),
    "true_node": ("North Node", "the direction a life is being pulled toward"),
    "true_south_node": ("South Node", "what a person already carries from before"),
    "chiron": ("Chiron", "the old wound and the gift of healing it"),
    "mean_lilith": ("Lilith", "the untamed part that refuses to be owned"),
}
ASPECT = {
    "conj": ("meets", "sit at the same degree — the two energies fuse and amplify each other"),
    "opp": ("faces", "sit directly opposite — a tension that can balance into partnership"),
    "trine": ("flows with", "sit 120° apart — the easiest angle in astrology, help given freely"),
    "square": ("challenges", "sit 90° apart — friction that forces both people to grow"),
    "sext": ("opens to", "sit 60° apart — an opportunity that has to be taken up"),
    "semisext": ("nudges", "sit 30° apart — a small, persistent adjustment"),
    "quinc": ("adjusts to", "sit 150° apart — two things that must keep re-fitting to each other"),
    "sesq": ("agitates", "sit 135° apart — a restless angle that keeps asking for change"),
    "quint": ("delights", "sit 72° apart — Kepler's creative angle, a private talent between two"),
    "bq": ("inspires", "sit 144° apart — the biquintile, a gift the pair discovers together"),
    "nov": ("ripens with", "sit 40° apart — the novile, the angle of things coming to term"),
}
SIGN = {"Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Leo": "Leo",
        "Vir": "Virgo", "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius", "Cap": "Capricorn",
        "Aqu": "Aquarius", "Pis": "Pisces"}
SIGN_READ = {
    "Ari": "beginnings and nerve", "Tau": "steadiness and the senses", "Gem": "curiosity and talk",
    "Can": "home and safekeeping", "Leo": "warmth and display", "Vir": "care and craft",
    "Lib": "balance and partnership", "Sco": "depth and devotion", "Sag": "faith and horizon",
    "Cap": "duty and building", "Aqu": "freedom and the collective", "Pis": "mercy and dissolving",
}
HARMONIC = {"5": ("the 5th harmonic", "the creative chart — what two people make together"),
            "7": ("the 7th harmonic", "the romantic chart — longing, glamour and inspiration"),
            "9": ("the 9th harmonic", "the marriage chart — in Vedic practice the ninth division "
                                      "is where a marriage is actually judged")}
NADI = {"Aadi": "Vata — air and movement", "Madhya": "Pitta — fire and drive",
        "Antya": "Kapha — water and endurance"}
GANA = {"Deva": "divine — gentle and idealistic", "Manushya": "human — practical and mixed",
        "Rakshasa": "fierce — wilful and intense"}
ANIMAL_READ = {
    "Rat": "quick and resourceful", "Ox": "patient and unmoveable", "Tiger": "bold and headstrong",
    "Rabbit": "gentle and diplomatic", "Dragon": "proud and lucky", "Snake": "wise and private",
    "Horse": "free and restless", "Goat": "tender and artistic", "Monkey": "clever and playful",
    "Rooster": "exacting and proud", "Dog": "loyal and just", "Pig": "generous and easy",
}
PHASE_READ = {
    "New": "beginning — acting on instinct, before the shape is clear",
    "Crescent": "pushing off from the past to make something new",
    "FirstQtr": "crisis of action — building against resistance",
    "Gibbous": "refining, questioning, perfecting before the reveal",
    "Full": "full illumination — seeing and being seen completely",
    "Disseminating": "sharing what has been learned",
    "LastQtr": "crisis of meaning — dismantling what no longer holds",
    "Balsamic": "the closing dark — release, and seeds for what comes next",
}


NEEDS_THE = {"Sun", "Moon", "North Node", "South Node"}


def _the(b, cap=False):
    """'the Moon' / 'Venus' — an article only for the bodies that take one"""
    t = ("the " + b) if b in NEEDS_THE else b
    return t[0].upper() + t[1:] if cap else t


def _pair(v):
    return v.split("x", 1) if "x" in v else (v, v)


NEG_TITLE = [
    ("Both born under ", "Not both born under "),
    ("One of the six ", "Not one of the six "),
    ("In the same ", "Not in the same "),
    ("The same ", "Not the same "),
    ("Born under the same ", "Not born under the same "),
]


def _negate_title(t):
    """say the ABSENCE of a statement in English, not as a logical operator"""
    for a, b in NEG_TITLE:
        if t.startswith(a):
            return b + t[len(a):]
    if t.startswith("His ") or t.startswith("Her "):
        return t[:4] + t[4:].replace(" meets ", " does not meet ", 1) \
                              .replace(" faces ", " does not face ", 1) \
                              .replace(" flows with ", " does not flow with ", 1) \
                              .replace(" challenges ", " does not challenge ", 1) \
                              .replace(" opens to ", " does not open to ", 1) \
            if any(k in t for k in (" meets ", " faces ", " flows with ", " challenges ", " opens to ")) \
            else "Not: " + t
    if " scores " in t:
        return t.replace(" scores ", " does not score ", 1)
    if t.startswith("Guna Milan score"):
        return t.replace("Guna Milan score", "Guna Milan is NOT", 1)
    if t.startswith("Guna Milan reaches"):
        return t.replace("reaches", "falls short of", 1)
    if t.startswith("Nadi dosha"):
        return "No nadi dosha — the two pulses differ"
    if t.startswith("Bhakoot dosha"):
        return "No bhakoot dosha — the moons sit at an easy distance"
    return "Not: " + t


def explain(name):
    n = name
    # a statement used as its NEGATION: the same doctrine, stated the other way round, so that a
    # non-negative model can carry it. See v22_nnls.py for why this exists.
    if n.startswith("NOT(") and n.endswith(")"):
        inner = explain(n[4:-1])
        return {"tradition": inner["tradition"],
                "title": _negate_title(inner["title"]),
                "plain": "This condition does NOT hold. " + inner["plain"],
                "reading": inner["reading"] + " Here it is its ABSENCE that the model reads, which is "
                           "the same doctrine stated the other way round."}
    # --- conjunctions of two statements ---
    if " AND " in n:
        parts = [explain(p.strip()) for p in n.split(" AND ")]
        return {"tradition": " + ".join(dict.fromkeys(p["tradition"] for p in parts)),
                "title": " and ".join(p["title"] for p in parts),
                "plain": " AND ".join(p["plain"] for p in parts),
                "reading": "Both conditions hold at once, which the doctrine treats as one combined "
                           "statement: " + " ".join(p["reading"] for p in parts)}

    # ---------- v29: cycle phases, chart gestalts, reception, Tibetan four ----------
    m = re.match(r"^cycle(\d+)_(\w+?)_(\w+?)_same_part$", n)
    if m:
        div, p1, p2 = m.groups()
        n1 = BODY.get(p1, (p1, ""))[0]; n2 = BODY.get(p2, (p2, ""))[0]
        return {"tradition": "Mundane astrology — planetary cycles",
                "title": f"Both births fall in the same {div}th of the {n1}\u2013{n2} cycle",
                "plain": f"Cut the {n1}\u2013{n2} cycle into {div} parts. Both of you were born inside "
                         f"the same one.",
                "reading": "A cycle this slow moves through a part over years, so sharing one means the "
                           "two of you were born into the same narrow window of a very long rhythm."}
    m = re.match(r"^cyclesep(\d+)_(\w+?)_(\w+?)_same_band$", n)
    if m:
        step, p1, p2 = m.groups()
        n1 = BODY.get(p1, (p1, ""))[0]; n2 = BODY.get(p2, (p2, ""))[0]
        return {"tradition": "Mundane astrology — planetary cycles",
                "title": f"The {n1}\u2013{n2} angle was within the same {step}\u00b0 at both births",
                "plain": f"Measure the angle from {n2} to {n1} at each birth; both fall in the same "
                         f"{step}-degree band.",
                "reading": "The raw separation, read directly rather than through a phase name — the "
                           "two of you caught the same slow planets at the same distance apart."}
    m = re.match(r"^cyclephase_(\w+?)_(\w+?)(=(\S+)|_same|_opposed)$", n)
    if m:
        p1, p2 = m.group(1), m.group(2)
        n1 = BODY.get(p1, (p1, ""))[0]; n2 = BODY.get(p2, (p2, ""))[0]
        tail = m.group(3)
        if tail == "_same":
            t = f"Both born in the same phase of the {n1}\u2013{n2} cycle"
            pl = f"The {n1}\u2013{n2} cycle was in the same one of its eight phases at both births."
        elif tail == "_opposed":
            t = f"Born in opposite phases of the {n1}\u2013{n2} cycle"
            pl = f"The two births fall across the {n1}\u2013{n2} cycle from each other."
        else:
            a, b = _pair(m.group(4))
            t = (f"Both born in the {a} phase of {n1}\u2013{n2}" if a == b else
                 f"He in the {a} phase of {n1}\u2013{n2}, she in the {b}")
            pl = (f"Measure the angle from {n2} to {n1} and read it as a lunation: his birth falls in "
                  f"the {a} phase, hers in the {b}.")
        return {"tradition": "Mundane astrology — cycle phase (Rudhyar)", "title": t, "plain": pl,
                "reading": "Rudhyar read every planetary pair as a cycle with the same eight phases the "
                           "Moon has — new, crescent, first quarter, gibbous, full, disseminating, last "
                           "quarter, balsamic. The phase says where in a long story a birth falls: the "
                           "new phase begins something, the full illuminates it, the balsamic lets it go."}
    m = re.match(r"^(comp|dav)_(grand_trine|t_square|grand_cross|yod|stellium3|stellium4)$", n)
    if m:
        ch, sh = m.groups()
        W = "composite chart — the midpoint of the two charts, read as the relationship itself" \
            if ch == "comp" else "Davison chart — a real chart for the midpoint in time between the births"
        SH = {"grand_trine": ("A grand trine", "three bodies at 120\u00b0 to each other — a closed "
                              "circuit of ease, gift that can become complacency"),
              "t_square": ("A T-square", "an opposition with a third body square to both — the "
                           "engine-room of a chart, tension that produces work"),
              "grand_cross": ("A grand cross", "two oppositions squaring each other — four-way "
                              "pressure, and the hardest shape a chart can carry"),
              "yod": ("A yod", "two bodies sextile, both quincunx a third — the Finger of God, a "
                      "pointed and awkward calling"),
              "stellium3": ("A stellium of three", "three or more bodies crowded into one sign"),
              "stellium4": ("A stellium of four", "four or more bodies crowded into one sign")}[sh]
        return {"tradition": f"{'Composite' if ch=='comp' else 'Davison'} chart — aspect pattern",
                "title": f"{SH[0]} in the {'composite' if ch=='comp' else 'Davison'}",
                "plain": f"In the {W}, the bodies form {SH[0].lower()}.",
                "reading": f"{SH[0]} is {SH[1]}. A pattern is the first thing a chart reader names, "
                           f"before any single placement."}
    m = re.match(r"^(comp|dav)_(largest_sign_cluster|aspect_density)=(\d+)$", n)
    if m:
        ch, kind, v = m.groups()
        if kind == "largest_sign_cluster":
            return {"tradition": f"{'Composite' if ch=='comp' else 'Davison'} chart",
                    "title": f"{v} bodies gathered in one sign",
                    "plain": f"The fullest sign of the relationship chart holds {v} of the ten bodies.",
                    "reading": "A crowded sign concentrates a chart: much of the relationship's weight "
                               "falls in one department of life."}
        return {"tradition": f"{'Composite' if ch=='comp' else 'Davison'} chart",
                "title": "How tightly the relationship chart is wired",
                "plain": "The count of major aspects inside the chart, banded.",
                "reading": "A densely aspected chart has everything talking to everything; a sparse one "
                           "leaves its parts to run separately."}
    m = re.match(r"^(comp|dav)_d9_(\w+)_sign=(\w+)$", n)
    if m:
        ch, body, sg = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": f"{'Composite' if ch=='comp' else 'Davison'} chart — Navamsa",
                "title": f"{_the(bn, True)} in {SIGN.get(sg,sg)} in the relationship's D9",
                "plain": f"Take the ninth-part chart OF the relationship chart; {_the(bn)} falls in "
                         f"{SIGN.get(sg,sg)}.",
                "reading": f"The navamsa is where Vedic astrology judges a marriage. Applied to the "
                           f"composite it asks what the union itself becomes. {_the(bn, True)} is {bd}."}
    m = re.match(r"^reception_his_(\w+)_her_(\w+)$", n)
    if m:
        p1, p2 = m.groups()
        n1, d1 = BODY.get(p1, (p1, "")); n2, d2 = BODY.get(p2, (p2, ""))
        return {"tradition": "Classical synastry — mutual reception",
                "title": f"His {n1} and her {n2} are each other's guest",
                "plain": f"His {n1} sits in the sign her {n2} rules, and her {n2} sits in the sign his "
                         f"{n1} rules.",
                "reading": "Mutual reception is one of the oldest judgements in the craft: two planets "
                           "keeping each other's house, obliged to treat each other well. "
                           f"{_the(n1, True)} is {d1}; {_the(n2)} is {d2}."}
    m = re.match(r"^his_(\w+)_guest_of_(\w+)$", n)
    if m:
        p1, p2 = m.groups()
        n1, d1 = BODY.get(p1, (p1, "")); n2, _ = BODY.get(p2, (p2, ""))
        return {"tradition": "Classical astrology — dispositor",
                "title": f"His {n1} is a guest of {n2}",
                "plain": f"His {n1} sits in a sign ruled by {n2}, so {n2} is its host.",
                "reading": f"A planet in another's sign is that planet's guest, and takes some of its "
                           f"host's character. {_the(n1, True)} is {d1}."}
    m = re.match(r"^tib_(srog|lus|dbangthang|klungrta)(pair=(\S+)|_same|_he_feeds_her|_she_feeds_him|"
                 r"_he_harms_her|_she_harms_him)$", n)
    if m:
        q, tail = m.group(1), m.group(2)
        Q = {"srog": ("srog", "the life-force — the first and heaviest of the four"),
             "lus": ("lus", "the body — health and constitution"),
             "dbangthang": ("dbang-thang", "power — standing and capability"),
             "klungrta": ("klung-rta", "the wind-horse — luck and momentum")}[q]
        if tail == "_same":
            t, pl = f"The same {Q[0]} element", f"Both births carry the same {Q[0]} element."
        elif "feeds" in tail:
            who = "His" if "he_feeds" in tail else "Her"
            t = f"{who} {Q[0]} feeds the other's"
            pl = f"On the five-element cycle {who.lower()} {Q[0]} element produces the other's."
        elif "harms" in tail:
            who = "His" if "he_harms" in tail else "Her"
            t = f"{who} {Q[0]} harms the other's"
            pl = f"On the controlling cycle {who.lower()} {Q[0]} element overcomes the other's."
        else:
            a, b = _pair(m.group(3))
            t, pl = f"{Q[0]}: {a} and {b}", f"His {Q[0]} element is {a}, hers {b}."
        return {"tradition": "Tibetan astrology — the four qualities", "title": t, "plain": pl,
                "reading": f"Tibetan practice compares four quantities when matching a couple; {Q[0]} is "
                           f"{Q[1]}. Each is an element, and the elements feed or harm each other in a "
                           f"fixed cycle."}
    if n.startswith("ninestar_month") or n == "ninestar_year_meets_month":
        return {"tradition": "Nine Star Ki (Japanese)",
                "title": ("His yearly star is her monthly star, or the reverse"
                          if n.endswith("meets_month") else
                          "The same monthly star" if n.endswith("same") else "The pair of monthly stars"),
                "plain": "Beside the yearly star, Nine Star Ki gives each birth a monthly star from the "
                         "same nine.",
                "reading": "The year star is read as the outer character and the month star as the "
                           "inner one, so two people can meet on either."}
    m = re.match(r"^bridge_(lifepath|birthday)=(\d+)$", n)
    if m:
        kind, v = m.groups()
        return {"tradition": "Numerology — bridge number",
                "title": f"A {kind} bridge of {v}",
                "plain": f"The plain distance between the two {kind} numbers is {v}.",
                "reading": "The bridge number is read as the work of translation between two people — "
                           "zero means you speak the same language, a wide bridge means you must build "
                           "one."}
    if n.startswith("universalyearpair") or n.startswith("universaldaypair"):
        a, b = _pair(n.split("=", 1)[1])
        what = "year" if "year" in n else "day"
        return {"tradition": "Numerology — universal numbers",
                "title": f"Universal {what} {a} and {b}",
                "plain": f"The universal {what} number is the whole world's number for that date, "
                         f"before anything personal: his {a}, hers {b}.",
                "reading": "Numerology reads a personal number against the universal one — the season "
                           "the world was in when each of you arrived."}
    if n.startswith("chaldean_compound"):
        return {"tradition": "Numerology — Chaldean compound number",
                "title": ("The same compound number" if n.endswith("same")
                          else f"Compound number {n.split('=')[-1]}"),
                "plain": "Chaldean numerology keeps the two-digit compound before reducing it, and reads "
                         "each of the fifty-two as its own symbol.",
                "reading": "The compound is held to carry the finer meaning, the single digit only the "
                           "outline."}
    if n.startswith("digit_"):
        T = {"digit_palindrome_either": ("A birth date that reads the same backwards",
                                         "One of the two dates is a palindrome."),
             }.get(n)
        if T:
            return {"tradition": "Numerology — the shape of the date", "title": T[0], "plain": T[1],
                    "reading": "Numerology reads the written date as a figure, not only as a sum: "
                               "repetitions, mirrors and runs are held to mark it."}
        a, b = _pair(n.split("=", 1)[1]) if "=" in n else ("", "")
        kind = "repeated digits" if "repeat" in n else "consecutive runs"
        return {"tradition": "Numerology — the shape of the date",
                "title": f"{kind.capitalize()}: {a} and {b}",
                "plain": f"His date shows {a} and hers {b} by that measure.",
                "reading": "Numerology reads the written date as a figure as well as a sum."}

    # ---------- v26: lagna systems, compatibility systems, finer charts ----------
    m = re.match(r"^(his|her)_(\w+?)_in_(her|his)_(chandra|surya)_house=(\d+)$", n)
    if m:
        w1, body, w2, lag, h = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        L = "Moon" if lag == "chandra" else "Sun"
        return {"tradition": f"Vedic — {'Chandra' if lag=='chandra' else 'Surya'} lagna",
                "title": f"{'His' if w1=='his' else 'Her'} {bn} falls in the {h}th house of "
                         f"{'her' if w2=='her' else 'his'} chart",
                "plain": f"Reading {'her' if w2=='her' else 'his'} chart from the {L} as the ascendant — "
                         f"what a Vedic astrologer does when no birth time is known — "
                         f"{'his' if w1=='his' else 'her'} {bn} lands in the {h}th house.",
                "reading": f"{_the(bn, True)} is {bd}. The house says which part of life it touches; the "
                           f"7th is the house of marriage itself."}
    m = re.match(r"^(his|her)_(\w+?)_in_(her|his)_7th_(chandra|surya)$", n)
    if m:
        w1, body, w2, lag = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": f"Vedic — {'Chandra' if lag=='chandra' else 'Surya'} lagna",
                "title": f"{'His' if w1=='his' else 'Her'} {bn} sits in "
                         f"{'her' if w2=='her' else 'his'} house of marriage",
                "plain": f"Counting from the {'Moon' if lag=='chandra' else 'Sun'} as ascendant, "
                         f"{'his' if w1=='his' else 'her'} {bn} falls in the 7th house of "
                         f"{'her' if w2=='her' else 'his'} chart.",
                "reading": f"The 7th is the house of the spouse. {_the(bn, True)} is {bd}."}
    m = re.match(r"^(his|her)_(\w+?)_kendra_from_(her|his)_(chandra|surya)$", n)
    if m:
        w1, body, w2, lag = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": f"Vedic — {'Chandra' if lag=='chandra' else 'Surya'} lagna",
                "title": f"{'His' if w1=='his' else 'Her'} {bn} stands on an angle of "
                         f"{'her' if w2=='her' else 'his'} chart",
                "plain": f"{'His' if w1=='his' else 'Her'} {bn} falls in the 1st, 4th, 7th or 10th house "
                         f"of {'her' if w2=='her' else 'his'} {'Moon' if lag=='chandra' else 'Sun'} chart.",
                "reading": "The kendras are the four angles — the strongest, most visible houses in a "
                           f"chart. {_the(bn, True)} is {bd}."}
    # --- harmonic / draconic / antiscia synastry ---
    m = re.match(r"^h([579])_his_(\w+?)_(\w+?)_her_(\w+)$", n)
    if m:
        h, a, asp, b = m.groups()
        hn, hr = HARMONIC[h]
        an, ad = BODY.get(a, (a, "")); bn, bd = BODY.get(b, (b, ""))
        av, adesc = ASPECT.get(asp, (asp, "form an angle"))
        return {"tradition": f"Harmonic astrology — {hn}",
                "title": f"His {an} {av} her {bn}, in {hn}",
                "plain": f"Multiply every position in both charts by {h} and read the result. In that "
                         f"chart his {an} and her {bn} {adesc}.",
                "reading": f"{_the(hn, True)} is {hr}. His {an} is {ad}; her {bn} is {bd}."}
    m = re.match(r"^(draconic|antiscia)_his_(\w+?)_(\w+?)_her_(\w+)$", n)
    if m:
        kind, a, asp, b = m.groups()
        an, ad = BODY.get(a, (a, "")); bn, bd = BODY.get(b, (b, ""))
        av, adesc = ASPECT.get(asp, (asp, "form an angle"))
        if kind == "draconic":
            return {"tradition": "Draconic astrology",
                    "title": f"His {an} {av} her {bn}, in the draconic chart",
                    "plain": f"Re-measure both charts from the Moon's north node instead of the "
                             f"equinox. There, his {an} and her {bn} {adesc}.",
                    "reading": "The draconic chart is read as the soul's own chart, underneath the "
                               f"personality. His {an} is {ad}; her {bn} is {bd}."}
        return {"tradition": "Antiscia (classical)",
                "title": f"His {an} mirrors her {bn}",
                "plain": f"Reflect his chart across the solstice axis — the Cancer–Capricorn line. "
                         f"His {an}'s mirror point and her {bn} {adesc}.",
                "reading": "Antiscia are the hidden contacts of classical astrology: two points that "
                           "share the same daylight, linked without any visible aspect between them."}

    # --- ordinary synastry ---
    m = re.match(r"^his_(\w+?)_(\w+?)_her_(\w+)$", n)
    if m:
        a, asp, b = m.groups()
        an, ad = BODY.get(a, (a, "")); bn, bd = BODY.get(b, (b, ""))
        av, adesc = ASPECT.get(asp, (asp, "form an angle"))
        return {"tradition": "Western synastry",
                "title": f"His {an} {av} her {bn}",
                "plain": f"Laying his birth chart over hers, his {an} and her {bn} {adesc}.",
                "reading": (f"{an.capitalize()} is {ad} — and this angle links his to hers."
                            if a == b else f"His {an} is {ad}. Her {bn} is {bd}.") +
                           " Synastry reads this contact as one of the live wires between two people."}
    m = re.match(r"^(his|her)_(\w+?)_(his|her)_(\w+?)_house=(\d+)$", n)
    if m:
        w1, a, w2, b, h = m.groups()
        an, ad = BODY.get(a, (a, ""))
        return {"tradition": "Western synastry — houses",
                "title": f"{'His' if w1=='his' else 'Her'} {an} falls in {'his' if w2=='his' else 'her'} {h}th house",
                "plain": f"Placed in {'his' if w2=='his' else 'her'} chart, {'his' if w1=='his' else 'her'} "
                         f"{an} lands in the {h}th house.",
                "reading": f"The house says which room of life the contact happens in. "
                           f"{_the(an, True)} brings {ad} into it."}

    # --- composite / davison ---
    m = re.match(r"^(comp|dav)_(\w+?)_(sign|decan|tithi|nakshatra)=(\w+)$", n)
    if m:
        kind, body, what, val = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        where = ("the composite chart — the midpoint of the two birth charts, read as the chart of the "
                 "relationship itself" if kind == "comp" else
                 "the Davison chart — a real chart cast for the exact midpoint in time between the two "
                 "births, so the relationship gets a birthday of its own")
        val_h = SIGN.get(val, val)
        extra = f" {val_h} is {SIGN_READ[val]}." if val in SIGN_READ else ""
        return {"tradition": "Composite chart" if kind == "comp" else "Davison relationship chart",
                "title": f"{_the(bn, True)} in {val_h}, in the {'composite' if kind=='comp' else 'Davison'} chart",
                "plain": f"In {where}, {_the(bn)} sits in {val_h}.",
                "reading": f"{_the(bn, True)} is {bd}.{extra}"}
    m = re.match(r"^comp_(\w+?)_(\w+?)_(\w+)$", n)
    if m:
        a, asp, b = m.groups()
        an, ad = BODY.get(a, (a, "")); bn, bd = BODY.get(b, (b, ""))
        av, adesc = ASPECT.get(asp, (asp, "form an angle"))
        return {"tradition": "Composite chart",
                "title": f"{_the(an, True)} {av} {_the(bn)} in the composite",
                "plain": f"In the chart of the relationship itself, {_the(an)} and {_the(bn)} {adesc}.",
                "reading": f"{_the(an, True)} is {ad}; {_the(bn)} is {bd}."}

    # --- outer-planet cycles ---
    m = re.match(r"^cycle_(\w+?)_(\w+?)_phase=(\w+)$", n)
    if m:
        p1, p2, sg = m.groups()
        n1 = BODY.get(p1, (p1, ""))[0]; n2 = BODY.get(p2, (p2, ""))[0]
        return {"tradition": "Mundane astrology — planetary cycles",
                "title": f"Both born under {n1}–{n2} in {SIGN.get(sg, sg)}",
                "plain": f"The slow cycle between {n1} and {n2} was passing through "
                         f"{SIGN.get(sg, sg)} when both of you were born.",
                "reading": "These are generational rhythms — they change over decades, not days, so this "
                           "says the two of you belong to the same long season of history. It is the "
                           "part of the reading that is about your era as much as about you."}
    m = re.match(r"^cycle(\d+)?_(\w+?)_(\w+)=(\d+)$", n)
    if m:
        div, p1, p2, k = m.groups()
        n1 = BODY.get(p1, (p1, ""))[0]; n2 = BODY.get(p2, (p2, ""))[0]
        d = div or "the"
        return {"tradition": "Mundane astrology — planetary cycles",
                "title": f"Same phase {k} of the {n1}–{n2} cycle",
                "plain": f"Divide the {n1}–{n2} cycle into {d} parts; both births fall in part {k}.",
                "reading": "A generational marker: it moves over decades, so it speaks to the age you "
                           "were both born into."}

    # --- Vedic: kootas, nadi, tara, gana, yoni, navamsa ---
    if n.startswith("guna_total_band"):
        b = n.split("=")[-1]
        bands = {"0": "under 12", "1": "12–17", "2": "18–23", "3": "24–27", "4": "28–31", "5": "32–36"}
        return {"tradition": "Vedic — Ashtakoota (Guna Milan)",
                "title": f"Guna Milan score {bands.get(b, b)} out of 36",
                "plain": "The eight traditional compatibility tests, scored and added: Varna, Vashya, "
                         "Tara, Yoni, Graha Maitri, Gana, Bhakoot and Nadi.",
                "reading": "This is the number a Vedic astrologer actually gives a couple. Eighteen of "
                           "thirty-six is the classical threshold for a match; the high twenties is "
                           "considered a strong one."}
    if n in ("guna_total_ge18_traditional_pass", "guna_total_ge24_very_good"):
        thr = "18" if "18" in n else "24"
        return {"tradition": "Vedic — Ashtakoota (Guna Milan)",
                "title": f"Guna Milan reaches {thr} of 36",
                "plain": f"The eight kootas together score at least {thr}.",
                "reading": "Eighteen is the classical pass mark for a marriage; twenty-four and above is "
                           "read as a genuinely strong match."}
    if n in ("nadi_dosha", "koota_nadi=0"):
        return {"tradition": "Vedic — Nadi koota",
                "title": "Nadi dosha — the same pulse",
                "plain": "Both birth stars fall in the same nadi, so the koota scores zero of eight.",
                "reading": "Nadi is the constitutional pulse. Sharing it is the single heaviest caution "
                           "in Guna Milan — traditionally read as too much sameness rather than too "
                           "little. It is also the one most often waived when the rest of the chart is "
                           "strong."}
    if n == "bhakoot_dosha":
        return {"tradition": "Vedic — Bhakoot koota",
                "title": "Bhakoot dosha — an awkward distance between the moons",
                "plain": "The two Moon signs sit at a distance the tradition marks as difficult "
                         "(2/12, 5/9 or 6/8), scoring zero of seven.",
                "reading": "Bhakoot is about emotional footing — whether two people stand at an easy "
                           "angle to each other's feelings."}
    m = re.match(r"^koota_(\w+)=(\S+)$", n)
    if m:
        k, v = m.groups()
        KO = {"varna": ("Varna", 1, "the spiritual temperaments, and whether hers is met by his"),
              "vashya": ("Vashya", 2, "mutual influence — who naturally draws whom"),
              "tara": ("Tara", 3, "the star-count between the two birth stars, read for fortune"),
              "yoni": ("Yoni", 4, "the animal symbol of each birth star — instinctive and physical fit"),
              "grahamaitri": ("Graha Maitri", 5, "whether the two Moon-sign rulers are friends"),
              "gana": ("Gana", 6, "temperament class — divine, human or fierce"),
              "bhakoot": ("Bhakoot", 7, "the distance between the two Moon signs"),
              "nadi": ("Nadi", 8, "the constitutional pulse — health and lineage")}
        nm, mx, desc = KO.get(k, (k.title(), "?", ""))
        return {"tradition": f"Vedic — {nm} koota",
                "title": f"{nm} scores {v} of {mx}",
                "plain": f"The {nm} test scores {v} out of {mx} for this pair.",
                "reading": f"{nm} measures {desc}."}
    if n.startswith("nadipair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Vedic — Nadi koota",
                "title": f"His nadi {a}, hers {b}",
                "plain": f"His birth star falls in the {a} nadi, hers in the {b} nadi.",
                "reading": ("Nadi is the constitutional pulse. Both of you carry "
                            f"{NADI.get(a, a)}." if a == b else
                            f"Nadi is the constitutional pulse — his is {NADI.get(a, a)}, hers is "
                            f"{NADI.get(b, b)}.") +
                           " Different nadis score the full eight points; the same nadi scores nothing."}
    if n.startswith("ganapair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Vedic — Gana koota",
                "title": f"His gana {a}, hers {b}",
                "plain": f"His birth star is {a}, hers is {b}.",
                "reading": (f"Gana is temperament, and you share it: {GANA.get(a, a)}."
                            if a == b else
                            f"Gana is temperament — his {GANA.get(a, a)}, hers {GANA.get(b, b)}.")}
    if n.startswith("yonipair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Vedic — Yoni koota",
                "title": f"His yoni the {a}, hers the {b}",
                "plain": f"Each birth star carries an animal; his is the {a}, hers the {b}.",
                "reading": "Yoni is read for instinctive and physical fit. Matching animals score the "
                           "full four points; traditional enemies score nothing."}
    if n.startswith("tarapair=") or n.startswith("tara"):
        return {"tradition": "Vedic — Tara koota",
                "title": "The star-count between the two birth stars",
                "plain": "Counting from his birth star to hers and back again gives the Tara pair.",
                "reading": "Tara is read for fortune between the two — some counts are auspicious, and "
                           "the 3rd, 5th and 7th are the ones the tradition warns about."}
    if n.startswith("varnapair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Vedic — Varna koota",
                "title": f"His varna {a}, hers {b}",
                "plain": f"By Moon sign his varna is {a} and hers is {b}.",
                "reading": "Varna is the spiritual temperament — priestly, warrior, merchant or worker "
                           "in the classical scheme, read here for whether each meets the other's."}
    if n.startswith("moonlordpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Vedic — Graha Maitri",
                "title": f"His Moon ruled by {a}, hers by {b}",
                "plain": f"His Moon sign is ruled by {a}, hers by {b}.",
                "reading": "Graha Maitri asks whether those two rulers are friends, neutral or enemies "
                           "in the classical table — five points ride on it."}
    m = re.match(r"^d9_(\w+?)pair=(\w+)$", n)
    if m:
        body, val = m.groups()
        a, b = _pair(val)
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": "Vedic — Navamsa (D9)",
                "title": f"His {bn} in {SIGN.get(a,a)}, hers in {SIGN.get(b,b)} — in the D9",
                "plain": f"Divide each sign into nine and re-read the chart. In that ninth-part chart "
                         f"his {bn} is in {SIGN.get(a,a)} and hers is in {SIGN.get(b,b)}.",
                "reading": f"The Navamsa is the chart Vedic astrology judges a marriage in — the birth "
                           f"chart shows the promise, the D9 shows what it becomes. {bn.capitalize()} "
                           f"is {bd}."}
    m = re.match(r"^d9_(\w+)_(same_sign|opposite|trine)$", n)
    if m:
        body, rel = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        R = {"same_sign": "land in the same sign", "opposite": "land opposite each other",
             "trine": "land in the same element, 120° apart"}
        return {"tradition": "Vedic — Navamsa (D9)",
                "title": f"Both {bn}s {R[rel]} in the D9",
                "plain": f"In the ninth-part chart, his and her {bn} {R[rel]}.",
                "reading": f"The Navamsa is where a Vedic astrologer reads the marriage itself. "
                           f"{bn.capitalize()} is {bd}."}
    if n.startswith("nakpair=") or n.startswith("nakshatra"):
        return {"tradition": "Vedic — Nakshatra",
                "title": "The pair of birth stars",
                "plain": "Each Moon sits in one of the 27 nakshatras; this is the pair.",
                "reading": "The nakshatra is the lunar mansion — a finer division than the sign, and the "
                           "unit most Vedic marriage matching is actually built on."}
    if n.startswith("tithi") or n.startswith("comp_tithi"):
        return {"tradition": "Vedic — Tithi (lunar day)",
                "title": "The lunar day of the pairing",
                "plain": "The tithi is the Moon's distance from the Sun in 12° steps — the lunar day.",
                "reading": "Tithi carries the mood of the lunar month; it is chosen carefully for "
                           "weddings and read here for the pair."}
    if n.startswith("rajjupair="):
        return {"tradition": "Vedic — Rajju",
                "title": "The rajju (rope) group of the two birth stars",
                "plain": "The 27 stars divide into five rajju groups, from foot to head.",
                "reading": "Rajju is read for the durability of the marriage — sharing a rajju group is "
                           "the traditional caution."}

    # --- numerology ---
    if n.startswith("lifepathpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Numerology — Life Path",
                "title": f"Life Path {a} with Life Path {b}",
                "plain": f"Reduce each full birth date to a single digit (11, 22 and 33 stay whole): "
                         f"his is {a}, hers is {b}.",
                "reading": "The Life Path is the backbone of Pythagorean numerology — the number a whole "
                           "life is read from. This is the pairing of the two."}
    if n.startswith("chaldeanpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Numerology — Chaldean",
                "title": f"Chaldean {a} with Chaldean {b}",
                "plain": f"The older Chaldean reduction of each birth date: his {a}, hers {b}.",
                "reading": "Chaldean numerology predates the Pythagorean system and reduces differently; "
                           "it is kept separate here rather than merged."}
    if n.startswith("birthdaynumpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Numerology — Birthday number",
                "title": f"Born on a {a} day and a {b} day",
                "plain": f"The day of the month reduced: his {a}, hers {b}.",
                "reading": "The birthday number is read as the particular gift someone brings, sitting "
                           "on top of the Life Path."}
    if n.startswith("attitudepair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Numerology — Attitude number",
                "title": f"Attitude {a} with attitude {b}",
                "plain": f"Month plus day, reduced: his {a}, hers {b}.",
                "reading": "The attitude number is how a person comes across before you know them — the "
                           "first impression, in numerological terms."}
    if n.startswith("personalyearpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Numerology — Personal Year",
                "title": f"He was in a {a} year, she in a {b} year",
                "plain": f"The nine-year personal cycle, each measured at the other's birth: his {a}, "
                         f"hers {b}.",
                "reading": "Numerology reads life in nine-year seasons; this asks which season each of "
                           "you was living through when the other arrived."}
    if n.startswith("lifepath_sum"):
        return {"tradition": "Numerology — Life Path",
                "title": f"The two Life Paths add to {n.split('=')[-1]}",
                "plain": "Add both Life Path numbers and reduce.",
                "reading": "The sum is read as the number of the relationship itself, rather than of "
                           "either person."}
    if n.startswith("lifepath_gap"):
        return {"tradition": "Numerology — Life Path",
                "title": f"Life Paths {n.split('=')[-1]} apart",
                "plain": "The plain distance between the two Life Path numbers.",
                "reading": "Distance is read as how much translation the two of you have to do."}
    if n == "lifepath_same":
        return {"tradition": "Numerology — Life Path",
                "title": "The same Life Path number",
                "plain": "Both birth dates reduce to the same Life Path.",
                "reading": "Sharing a Life Path is read as walking the same road — recognition, and the "
                           "risk of sharing a blind spot."}
    if n == "lifepath_harmonious_set":
        return {"tradition": "Numerology — Life Path",
                "title": "Life Paths in the same harmonious family",
                "plain": "The two Life Paths fall in one of numerology's compatible sets — {1,5,7}, "
                         "{2,4,8} or {3,6,9}.",
                "reading": "These groupings are the classical compatibility families: the mental, the "
                           "material and the creative."}
    if n in ("lifepath_master_present", "lifepath_both_master"):
        both = n.endswith("both_master")
        return {"tradition": "Numerology — Master numbers",
                "title": "Both carry a master number" if both else "A master number is present",
                "plain": "A Life Path of 11, 22 or 33 is never reduced further.",
                "reading": "The master numbers are read as a heavier charge to carry — more potential "
                           "and more strain."}

    # --- moon phase ---
    if n.startswith("moonphasepair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Lunation cycle (Dane Rudhyar)",
                "title": f"He is a {a} Moon, she is a {b} Moon",
                "plain": f"The Moon's distance from the Sun at birth gives eight phase types: his is "
                         f"{a}, hers is {b}.",
                "reading": f"Rudhyar read the phase you are born under as the mood of a whole life. "
                           f"{a}: {PHASE_READ.get(a, '')}. {b}: {PHASE_READ.get(b, '')}."}
    if n.startswith("moonphase_sep"):
        return {"tradition": "Lunation cycle (Dane Rudhyar)",
                "title": f"{n.split('=')[-1]} phases apart on the lunar cycle",
                "plain": "How far apart the two birth phases sit on the eight-phase wheel.",
                "reading": "Adjacent phases are read as one person carrying forward what the other began."}
    if n == "moonphase_same":
        return {"tradition": "Lunation cycle (Dane Rudhyar)",
                "title": "Born under the same Moon phase",
                "plain": "Both births fall in the same one of the eight lunation types.",
                "reading": "Sharing a phase is read as sharing a tempo — the same instinct about when "
                           "to act and when to wait."}
    if n == "moonphase_opposite":
        return {"tradition": "Lunation cycle (Dane Rudhyar)",
                "title": "Opposite Moon phases",
                "plain": "The two birth phases sit across the wheel from each other.",
                "reading": "Opposite phases are read as complementary halves of one cycle — each holding "
                           "what the other is missing."}

    # --- Chinese ---
    if n.startswith("animalpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Chinese zodiac",
                "title": f"{a} and {b}",
                "plain": f"His birth year is the year of the {a}, hers the {b}.",
                "reading": f"The {a} is {ANIMAL_READ.get(a,'')}; the {b} is {ANIMAL_READ.get(b,'')}."}
    if n == "chinese_sanhe_trine":
        return {"tradition": "Chinese zodiac — San He",
                "title": "In the same triangle of affinity",
                "plain": "The two animals sit four apart, forming one of the four San He trines.",
                "reading": "San He is the strongest positive grouping in Chinese astrology — three signs "
                           "that reinforce each other's nature."}
    if n == "chinese_liuhe_harmony":
        return {"tradition": "Chinese zodiac — Liu He",
                "title": "One of the six harmonies",
                "plain": "The two animals form a Liu He pair — Rat with Ox, Tiger with Pig, and so on.",
                "reading": "Liu He is the classical secret-friend pairing, read as the most naturally "
                           "supportive match between two animals."}
    if n == "chinese_liuchong_clash":
        return {"tradition": "Chinese zodiac — Liu Chong",
                "title": "One of the six clashes",
                "plain": "The two animals sit directly opposite on the twelve-year wheel.",
                "reading": "Liu Chong is the classical clash — read as two natures that provoke each "
                           "other, for better and for worse."}
    if n == "chinese_xianghai_harm":
        return {"tradition": "Chinese zodiac — Xiang Hai",
                "title": "One of the six harms",
                "plain": "The two animals form a Xiang Hai pair.",
                "reading": "The harms are subtler than the clashes — read as quiet erosion rather than "
                           "open conflict."}
    if n == "chinese_same_animal":
        return {"tradition": "Chinese zodiac",
                "title": "The same animal",
                "plain": "Both born under the same zodiac animal, twelve years apart or the same year.",
                "reading": "Sharing an animal is read as deep recognition and shared blind spots."}
    if n.startswith("stemelempair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Chinese — Five Elements",
                "title": f"{a} and {b}",
                "plain": f"The heavenly stem of his birth year is {a}, hers {b}.",
                "reading": "Wu Xing reads the five elements as a cycle in which each produces one and "
                           "controls another."}
    m = re.match(r"^wuxing_(he|she)_(produces|controls)_(her|him)$", n)
    if m:
        who, verb, whom = m.groups()
        W = "His" if who == "he" else "Her"
        T = "her" if whom == "her" else "his"
        return {"tradition": "Chinese — Five Elements (Wu Xing)",
                "title": f"{W} element {verb} {T}",
                "plain": f"On the five-element wheel, {W.lower()} birth element {verb} {T} birth element.",
                "reading": ("The producing cycle — wood feeds fire, fire makes earth — is read as one "
                            "person nourishing the other." if verb == "produces" else
                            "The controlling cycle — water quenches fire, fire melts metal — is read as "
                            "one person checking or restraining the other.")}
    if n == "wuxing_same_element":
        return {"tradition": "Chinese — Five Elements (Wu Xing)",
                "title": "The same birth element",
                "plain": "Both birth years carry the same element.",
                "reading": "Shared element is read as easy understanding with little friction to grow on."}
    if n == "chinese_same_polarity":
        return {"tradition": "Chinese — Yin and Yang",
                "title": "The same polarity",
                "plain": "Both birth years are yin, or both are yang.",
                "reading": "Classical practice prefers one of each — yin and yang completing rather than "
                           "doubling."}
    if n.startswith("nayinpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Chinese — Na Yin",
                "title": f"Na Yin {a} with {b}",
                "plain": f"The sixty-year Na Yin cycle gives his year the {a} element and hers {b}.",
                "reading": "Na Yin is the subtler element system of the sixty-pillar cycle, used in "
                           "traditional Chinese marriage matching."}
    if n.startswith("kuapair="):
        return {"tradition": "Chinese — Kua number (Feng Shui)",
                "title": "The pair of Kua numbers",
                "plain": "Each birth year gives a Kua number, one to nine.",
                "reading": "Feng Shui divides Kua numbers into East and West groups; matching groups are "
                           "read as harmonious directions for a shared home."}

    # --- Mayan ---
    if n.startswith("tzolkin_signpair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Mayan — Tzolkin",
                "title": f"Day sign {a} with {b}",
                "plain": f"The 260-day sacred calendar gives his birth the day sign {a} and hers {b}.",
                "reading": "The Tzolkin's twenty day signs are the Mayan reading of character — the "
                           "closest equivalent to a sun sign in that tradition."}
    if n.startswith("tzolkin_tonepair="):
        a, b = _pair(n.split("=", 1)[1])
        return {"tradition": "Mayan — Tzolkin",
                "title": f"Galactic tone {a} with {b}",
                "plain": f"Each Tzolkin day also carries a tone from one to thirteen: his {a}, hers {b}.",
                "reading": "The tone is read as the pitch a life is played at, under the day sign."}
    if n in ("tzolkin_same_daysign", "tzolkin_same_tone", "tzolkin_antipode"):
        T = {"tzolkin_same_daysign": ("The same Tzolkin day sign",
                                      "Both births fall on the same one of the twenty day signs.",
                                      "Sharing a day sign is read as sharing a face in the calendar."),
             "tzolkin_same_tone": ("The same galactic tone",
                                   "Both births carry the same tone, one to thirteen.",
                                   "Sharing a tone is read as moving at the same pitch."),
             "tzolkin_antipode": ("Tzolkin antipodes",
                                  "The two day signs sit ten apart — opposite on the twenty-sign wheel.",
                                  "The antipode is the challenging partner in the Mayan cross — the one "
                                  "that tests and completes.")}[n]
        return {"tradition": "Mayan — Tzolkin", "title": T[0], "plain": T[1], "reading": T[2]}

    # --- element / mode / polarity pairings ---
    m = re.match(r"^(\w+?)_(elempair|modepair|polpair)=(\w+)$", n)
    if m:
        body, kind, val = m.groups()
        a, b = _pair(val)
        bn, bd = BODY.get(body, (body, ""))
        K = {"elempair": ("element", "fire, earth, air or water — the temperament of a sign"),
             "modepair": ("mode", "cardinal, fixed or mutable — whether a sign starts, holds or adapts"),
             "polpair": ("polarity", "yang and yin — outgoing and receptive")}[kind]
        return {"tradition": "Western astrology — elements and modes",
                "title": f"His {bn} {a}, hers {b} (by {K[0]})",
                "plain": f"By {K[0]}, his {bn} is {a} and hers is {b}.",
                "reading": f"{K[1].capitalize()}. {bn.capitalize()} is {bd}."}
    m = re.match(r"^(\w+?)pair=(\w+)$", n)
    if m and m.group(1) in BODY:
        body, val = m.groups()
        a, b = _pair(val)
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": "Western astrology — sign placement",
                "title": f"His {bn} in {SIGN.get(a,a)}, hers in {SIGN.get(b,b)}",
                "plain": f"His {bn} sits in {SIGN.get(a,a)}; hers in {SIGN.get(b,b)}.",
                "reading": f"{bn.capitalize()} is {bd}. "
                           f"{SIGN.get(a,a)} is {SIGN_READ.get(a,'')}; "
                           f"{SIGN.get(b,b)} is {SIGN_READ.get(b,'')}."}

    m = re.match(r"^(his|her)_(\w+)_(\w+)$", n)
    if m:
        w, body, rest = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        return {"tradition": "Western astrology",
                "title": f"{'His' if w=='his' else 'Her'} {bn}: {rest.replace('_',' ')}",
                "plain": f"{'His' if w=='his' else 'Her'} {bn} — {rest.replace('_',' ')}.",
                "reading": f"{bn.capitalize()} is {bd}."}

    if n.startswith("ninestar"):
        T = {"ninestar_same": ("The same nine-star number",
                               "Both birth years reduce to the same star, one to nine."),
             "ninestar_same_element": ("The same nine-star element", "Both stars share an element."),
             "ninestar_he_produces_her": ("His star feeds hers",
                                          "On the five-element cycle his star produces hers."),
             "ninestar_she_produces_him": ("Her star feeds his",
                                           "On the five-element cycle her star produces his."),
             "ninestar_he_controls_her": ("His star checks hers",
                                          "On the controlling cycle his star restrains hers."),
             "ninestar_she_controls_him": ("Her star checks his",
                                           "On the controlling cycle her star restrains his.")}
        if n in T:
            return {"tradition": "Nine Star Ki (Japanese)", "title": T[n][0], "plain": T[n][1],
                    "reading": "Nine Star Ki is used in Japan for compatibility specifically — the "
                               "birth year gives a star, and the stars stand in producing or "
                               "controlling relations to each other."}
        if "=" in n:
            a, b = _pair(n.split("=", 1)[1])
            kind = "elements" if "elem" in n else "numbers"
            return {"tradition": "Nine Star Ki (Japanese)",
                    "title": f"Nine-star {kind}: {a} and {b}",
                    "plain": f"His nine-star {kind[:-1]} is {a}, hers {b}.",
                    "reading": "The Japanese nine-star system, read for how two people's years meet."}
    if n.startswith("mewa"):
        return {"tradition": "Tibetan astrology — Mewa",
                "title": ("The same Mewa number" if n == "mewa_same"
                          else f"Mewa {n.split('=')[-1].replace('x', ' with ')}"),
                "plain": "The Mewa is one of nine numbers on the Tibetan magic square, taken from the "
                         "birth year.",
                "reading": "Tibetan practice reads the Mewa for the texture of a life, and compares two "
                           "of them when matching people."}
    if n.startswith("parkha"):
        return {"tradition": "Tibetan astrology — Parkha",
                "title": ("The same Parkha trigram" if n == "parkha_same"
                          else f"Parkha {n.split('=')[-1].replace('x', ' with ')}"),
                "plain": "The Parkha is one of the eight trigrams, taken from the birth year.",
                "reading": "The eight trigrams of the I Ching, used in Tibetan astrology to place a "
                           "person and to test a pairing."}
    if n.startswith("jieqi"):
        if n == "jieqi_same":
            t, pl = "Born in the same solar term", "Both births fall in the same one of the 24 jieqi."
        elif n == "jieqi_opposite":
            t, pl = "Born in opposite solar terms", "The two terms sit across the year from each other."
        else:
            a, b = _pair(n.split("=", 1)[1])
            t, pl = f"{a} and {b}", f"His birth falls in {a}, hers in {b}."
        return {"tradition": "Chinese solar calendar — the 24 jieqi", "title": t, "plain": pl,
                "reading": "The jieqi cut the solar year into twenty-four; they govern the Chinese "
                           "agricultural calendar and set when each zodiac year truly begins."}
    m = re.match(r"^d(3|7|12)_(\w+?)(pair=(\w+)|_same_sign|_opposite)$", n)
    if m:
        dv, body = m.group(1), m.group(2)
        DN = {"3": ("Drekkana (D3)", "the third-part chart, read for siblings, courage and the body"),
              "7": ("Saptamsa (D7)", "the seventh-part chart, the one read for children"),
              "12": ("Dwadasamsa (D12)", "the twelfth-part chart, read for what came from the parents")}[dv]
        bn, bd = BODY.get(body, (body, ""))
        if n.endswith("_same_sign"):
            t = f"Both {bn}s in the same sign of the {DN[0]}"
        elif n.endswith("_opposite"):
            t = f"The two {bn}s opposite in the {DN[0]}"
        else:
            a, b = _pair(m.group(4))
            t = f"His {bn} in {SIGN.get(a,a)}, hers in {SIGN.get(b,b)} — in the {DN[0]}"
        return {"tradition": f"Vedic — {DN[0]}", "title": t,
                "plain": f"Divide each sign into {dv} and re-read the chart; that is the {DN[0]}.",
                "reading": f"The {DN[0]} is {DN[1]}. {_the(bn, True)} is {bd}."}
    m = re.match(r"^(gajakesari|chandramangala|budhaaditya|kalasarpa)_(both|one|neither)$", n)
    if m:
        yg, who = m.groups()
        Y = {"gajakesari": ("Gaja Kesari yoga", "Jupiter standing on an angle from the Moon — the "
                            "elephant-and-lion yoga, read for standing and good judgement"),
             "chandramangala": ("Chandra Mangala yoga", "Moon and Mars together or facing — read for "
                                "drive, and for a temper that has to be spent somewhere"),
             "budhaaditya": ("Budha Aditya yoga", "Mercury with the Sun — read for a quick and "
                             "articulate mind"),
             "kalasarpa": ("Kala Sarpa yoga", "every planet penned between Rahu and Ketu — read as a "
                           "life under unusual pressure and unusual concentration")}[yg]
        W = {"both": "Both charts carry", "one": "One chart carries", "neither": "Neither chart carries"}
        return {"tradition": "Vedic — named yogas", "title": f"{W[who]} {Y[0]}",
                "plain": f"{W[who]} the classical configuration called {Y[0]}.",
                "reading": f"{Y[0]} is {Y[1]}."}
    m = re.match(r"^star_(\w+)_(\w+)_(both|one)$", n)
    if m:
        st, body, who = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        SR = {"Regulus": "the heart of the Lion — honour, and a fall if it is misused",
              "Spica": "the sheaf of wheat — the most fortunate star in the sky",
              "Aldebaran": "the Watcher of the East — success bought with integrity",
              "Antares": "the Watcher of the West — courage, obsession and risk",
              "Algol": "the Demon Star — the most feared fixed star of all",
              "Sirius": "the Dog Star — brilliance and heat",
              "Fomalhaut": "the Watcher of the South — vision, or delusion"}
        return {"tradition": "Fixed stars",
                "title": f"{'Both have' if who=='both' else 'One has'} {bn} on {st}",
                "plain": f"{'Both charts place' if who=='both' else 'One chart places'} {_the(bn)} within "
                         f"two degrees of the fixed star {st}.",
                "reading": f"{st} is {SR.get(st,'a named fixed star')}. {_the(bn, True)} is {bd}."}
    if n.startswith("manzil"):
        return {"tradition": "Arabic lunar mansions (manazil)",
                "title": ("The same lunar mansion" if n == "manzil_same" else "The pair of lunar mansions"),
                "plain": "The Moon's path divides into 28 mansions; this is where each Moon falls.",
                "reading": "The manazil are the Arabic counterpart of the nakshatras — twenty-eight "
                           "stations rather than twenty-seven, used for timing and for matching."}
    m = re.match(r"^sa_(his|her)_?(\w+?)_(conj|opp)_(\w+)$", n) or \
        re.match(r"^sa_(his|her)_(\w+?)_(conj|opp)_(\w+)$", n)
    if m:
        who, x, asp, y_ = m.groups()
        an, ad = BODY.get(x, (x, "")); bn, bd = BODY.get(y_, (y_, ""))
        av, adesc = ASPECT.get(asp, (asp, "form an angle"))
        return {"tradition": "Solar arc directions",
                "title": f"{'His' if who=='his' else 'Her'} directed {an} {av} "
                         f"{'her' if who=='his' else 'his'} {bn}",
                "plain": f"Advance the whole chart one degree for each year between the two births — a "
                         f"solar arc direction. The directed {an} and the natal {bn} {adesc}.",
                "reading": f"Solar arc asks what one chart had become by the time the other was born. "
                           f"{_the(an, True)} is {ad}; {_the(bn)} is {bd}."}
    m = re.match(r"^(critdeg|anaretic)_(\w+)_(both|one)$", n)
    if m:
        kind, body, who = m.groups()
        bn, bd = BODY.get(body, (body, ""))
        if kind == "critdeg":
            return {"tradition": "Critical degrees",
                    "title": f"{'Both have' if who=='both' else 'One has'} {bn} on a critical degree",
                    "plain": f"{_the(bn, True)} falls on one of the classical critical degrees — 0, 13 "
                             f"or 26 of a cardinal sign, 8-9 or 21-22 of a fixed one, 4 or 17 of a "
                             f"mutable one.",
                    "reading": f"A planet on a critical degree is read as emphasised, for good or ill. "
                               f"{_the(bn, True)} is {bd}."}
        return {"tradition": "The anaretic degree",
                "title": f"{'Both have' if who=='both' else 'One has'} {bn} at the 29th degree",
                "plain": f"{_the(bn, True)} sits in the last degree of its sign.",
                "reading": "The 29th is the degree of finishing — a matter at its last moment, urgent "
                           f"and unresolved. {_the(bn, True)} is {bd}."}
    m = re.match(r"^contrantiscia_his_(\w+?)_(\w+?)_her_(\w+)$", n)
    if m:
        x, asp, y_ = m.groups()
        an, ad = BODY.get(x, (x, "")); bn, bd = BODY.get(y_, (y_, ""))
        return {"tradition": "Contra-antiscia (classical)",
                "title": f"His {an} mirrors her {bn} across the equinox",
                "plain": f"Reflect his chart across the Aries-Libra axis; the mirror of his {an} meets "
                         f"her {bn}.",
                "reading": "The contra-antiscion is the second classical mirror — two points that share "
                           f"the same night rather than the same day. {_the(an, True)} is {ad}."}
    if n.startswith("composite_moonphase"):
        v = n.split("=")[-1]
        return {"tradition": "Composite chart — lunation",
                "title": f"The relationship's own Moon phase: {v}",
                "plain": "Take the midpoint Sun and midpoint Moon of the two charts and read the phase "
                         "between them.",
                "reading": f"The composite has a lunation of its own. {v}: {PHASE_READ.get(v, '')}"}
    if n.startswith("hijrimonth"):
        return {"tradition": "Islamic lunar calendar",
                "title": ("Born in the same Hijri month" if n == "hijrimonth_same"
                          else "The pair of Hijri months"),
                "plain": "The Islamic calendar is purely lunar, so its months drift against the seasons.",
                "reading": "A lunar-calendar reading of the two births, independent of the solar year."}

    return {"tradition": "Doctrine", "title": name.replace("_", " "),
            "plain": f"The statement `{name}`, computed from both birth dates.",
            "reading": "A named condition in the doctrine bank; see the model file for its definition."}


if __name__ == "__main__":
    import json
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.artamatch-dev/quality_v21.json")
    w = json.load(open(src))["weights"]
    out = []
    for k, v in sorted(w.items(), key=lambda kv: -kv[1]):
        e = explain(k); e["rule"] = k; e["weight"] = round(v, 4)
        out.append(e)
        print(f"\n[{e['tradition']}]  {e['title']}   (+{v:.4f})")
        print(f"   plain:   {e['plain']}")
        print(f"   reading: {e['reading']}")
    json.dump(out, open(os.path.expanduser("~/.artamatch-dev/quality_v21_explained.json"), "w"), indent=1)
    print(f"\n  {len(out)} rules explained -> ~/.artamatch-dev/quality_v21_explained.json")
