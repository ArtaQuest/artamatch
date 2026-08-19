"""
publish_competition_v4.py — create the FOURTH-EDITION competition (genderless, every pair in both orders), and nothing else.

WHY A THIRD SCRIPT. v2 created `artamatch-astrology`, wrote its pages from copy in the same file, and retired the
edition before it, all in one run. Three jobs in one file meant its copy went stale the moment competition_pages.py
took over the pages, and its retirement step could not be run on its own. This one does exactly one thing per
flag, so each can be checked before the next:

    AQ_DO_CREATE=1  python publish_competition_v3.py            create the competition + deadline/title/brief
    python publish_competition_v3.py --retire-old               retitle the FIRST edition as superseded and
                                                                disable its submissions -- run LAST, after the new
                                                                one is launched, never before

The pages come from competition_pages.py (which reads the model's numbers), the data/solution/sample from
publish_competition.py, and the metric from the UI or the ArtaFocus browser -- CompetitionSettings still has no
metric field in kagglesdk 0.1.37 (only the read-side ApiCompetition carries evaluation_metric), and the solution
upload 500s until a metric exists.

Slugs come from the environment so the first edition can never be created over by accident:
    AQ_COMPETITION      default artamatch-marriage-year
    AQ_OLD_COMPETITION  default artamatch-astrology
"""
import json
import os
import sys
import time

import requests

SLUG = os.environ.get("AQ_COMPETITION", "artamatch-genderless")
OLD_SLUG = os.environ.get("AQ_OLD_COMPETITION", "artamatch-sidereal")   # the third edition, the one that is live
ORG_ID = 5418
DEADLINE = "2027-02-28T23:59:00Z"
B = "https://api.kaggle.com/v1/competitions.CompetitionApiService/"
CR = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
U, K = CR["username"], CR["key"]
if U != "artafather":
    raise SystemExit(f"the credential file names {U!r}, not artafather — refusing")

# LENGTH LIMITS THE API DOES NOT ENFORCE BUT THE LAUNCH CHECKLIST DOES: title <= 60 characters, brief <= 140.
# The first values here were 61 and 389 and the settings page showed both in red; the API had answered 200.
TITLE = os.environ.get("AQ_COMP_TITLE", "ArtaMatch Astrology IV: genderless, any relationship")
BRIEF = os.environ.get("AQ_COMP_BRIEF", ("Two births, two places, the start date, every pair in both orders: did the relationship "
                                         "last thirty years? Genderless; any long-term pair."))
assert len(TITLE) <= 60 and len(BRIEF) <= 140, (len(TITLE), len(BRIEF))


def call(ep, payload, tries=5):
    for i in range(tries):
        try:
            r = requests.post(B + ep, json=payload, auth=(U, K), timeout=300)
            try:
                body = r.json()
            except Exception:
                body = r.text[:300]
            if r.status_code >= 500 and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            return r.status_code, body
        except Exception as e:
            if i == tries - 1:
                return None, f"{type(e).__name__} {e}"
            time.sleep(3 * (i + 1))
    return None, "gave up"


def create():
    if SLUG == OLD_SLUG:
        raise SystemExit("AQ_COMPETITION equals AQ_OLD_COMPETITION — refusing to create over the first edition")
    st, b = call("CreateCompetition", {"slug": SLUG, "title": TITLE, "briefDescription": BRIEF,
                                       "organizationId": ORG_ID})
    already = isinstance(b, dict) and "already taken" in json.dumps(b)
    print(f"  CreateCompetition {SLUG} -> {st}  "
          f"{'already exists, continuing' if already else (json.dumps(b)[:200] if isinstance(b, dict) else b)}")
    if st and st >= 400 and not already:
        raise SystemExit("  create failed; not touching settings")
    st, b = call("UpdateCompetitionSettings", {
        "competitionName": SLUG, "updateMask": "deadline,title,briefDescription",
        "settings": {"competitionName": SLUG, "deadline": DEADLINE, "title": TITLE, "briefDescription": BRIEF}})
    print(f"  deadline + title + brief -> {st} {json.dumps(b)[:120] if st and st >= 400 else ''}")
    print(f"\n  created: https://www.kaggle.com/competitions/{SLUG}  (unlaunched, invisible)")
    print("  next: competition_pages.py (pages) · set the metric to ROC AUC · publish_competition.py --launch")


def retire_old():
    st, b = call("UpdateCompetitionSettings", {
        "competitionName": OLD_SLUG, "updateMask": "title,briefDescription,disableSubmissions",
        "settings": {"competitionName": OLD_SLUG,
                     "title": "[SUPERSEDED] ArtaMatch Astrology III: sidereal, place and date",
                     "briefDescription": f"Superseded by {SLUG}, the fourth edition: genderless, every long-term "
                                         f"relationship, every pair in both orders. Please enter that one.",
                     "disableSubmissions": True}})
    print(f"  {OLD_SLUG} retitled as superseded + submissions disabled -> {st} "
          f"{json.dumps(b)[:120] if st and st >= 400 else ''}")


if __name__ == "__main__":
    if "--retire-old" in sys.argv:
        retire_old()
    elif os.environ.get("AQ_DO_CREATE") == "1":
        create()
    else:
        print(f"  DRY RUN. AQ_DO_CREATE=1 creates {SLUG!r} for org {ORG_ID}; --retire-old retires {OLD_SLUG!r}.")
        print(f"  title: {TITLE}\n  brief: {BRIEF[:120]}…")
