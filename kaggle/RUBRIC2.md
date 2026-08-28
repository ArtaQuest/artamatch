# Was this a good marriage? — the binary rubric (ArtaMatch, 2026-08-28)

You are reading what the historical record says about one marriage, assembled from both partners'
Wikipedia articles, plus two structured facts: how many children the couple had together, and how the
record says the marriage ended. **Decide one thing: did this marriage go well, yes or no.**

There is no neutral option. A previous pass allowed one and 69% of marriages landed there, which taught
nothing. Every marriage here gets a verdict.

## `good` (1) — the record shows a marriage that worked

Any ONE of these is enough:

- **affection or devotion is stated** — described as happy, close, devoted, inseparable; grief at the
  loss; nursing a spouse through illness; letters or accounts of love;
- **they built something together** — co-authored, co-composed, co-starred, co-founded a company or
  practice; one was the other's collaborator, model or muse; a shared political, scientific or
  philanthropic project;
- **children raised together AND nothing troubled on record** — no divorce, no conflict, no infidelity;
- **it lasted until one of them died AND nothing troubled on record** — a marriage that ran its full
  course without recorded trouble counts as having worked, even if the prose is dry;
- **they stood by each other through real adversity** — exile, war, imprisonment, persecution, poverty,
  serious illness.

## `bad` (0) — the record shows trouble, or shows nothing at all

Any ONE of these:

- **it ended in divorce, annulment or separation** — for this binary the ending is the verdict: a
  marriage that was dissolved did not go well, however amicably;
- **conflict on record** — acrimony, litigation, public feud, contested custody, estrangement, living
  apart in hostility;
- **infidelity, a long affair, bigamy, abandonment or desertion**;
- **violence, abuse, coercion, forced marriage, or a stated age under 18 at marriage** — a stated age
  under 18 makes it `bad` UNLESS the same record carries strong explicit evidence the marriage worked
  (stated love, lifelong devotion, sustained collaboration), in which case judge on the whole record and
  say in the evidence that the age was outweighed. A judge sent Anne Bradstreet — who wrote "To My Dear
  and Loving Husband" — to `bad` on the age alone; that is the failure this clause prevents;
- **addiction or gambling described as damaging the marriage**;
- **stated to be unhappy, loveless, miserable, or a marriage of convenience only**;
- **cruelty the couple inflicted together on other people**;
- **the record is too thin to affirm anything** — a bare marriage date, a name and nothing more, a
  genealogical listing with no children named. If you cannot point to a reason it worked, answer `bad`.

**The one case judges keep splitting on, ruled explicitly:** "he married X in 1878; they had three
children" — a dry genealogical entry that names children but gives no other texture — is **`good`**,
reason `children`. Children raised together with nothing troubled on record is an affirmative ground in
its own right; dryness of prose is not evidence against a marriage. Only a listing with **no children
and nothing else** is `thin_record` → `bad`. Two judges read this opposite ways, which is why it is
spelled out here.

## How to judge

1. **Judge the relationship, not the people.** Fame, rank, wealth, achievement, nationality and century
   are irrelevant. Do not treat an arranged dynastic match as bad *for being arranged* — judge it on
   whether the record shows it working.
2. **Judge only the pair named in `him` and `her`.** Descriptions frequently bleed in a previous spouse,
   a sibling, a same-named relative (including a daughter with her mother's name), or the couple's own
   children and grandchildren. Ignore all of that. If the named partner barely appears, say so in the
   evidence and answer on what little is actually about this pair.
3. **Infidelity against a *previous* spouse is not this marriage's fault.** Only trouble inside the
   judged relationship counts.
4. **Some pairs were never married at all** — a mistress, a concubine, a companion, a broken engagement,
   a disputed or unrecorded union. Say so in the evidence and set `not_a_marriage` true.
5. **The `children_together` number is often wrong.** Trust the prose.
6. **Never invent a story.** If the description does not support a reason the marriage worked, answer
   `bad` — that is what `bad` means here, not that the marriage was necessarily unhappy.

## Calibration — this matters

Across a batch of 200, **expect roughly half `good` and half `bad`.** The two failure modes are equally
bad: demanding explicit love letters (which pushes almost everything to `bad`), or accepting a bare
marriage date as evidence it worked (which pushes almost everything to `good`). If your batch comes out
past about 65/35 in either direction, re-read this rubric and check whether you have drifted — then
report the split you found, whatever it is. Do not manufacture a balance that the descriptions do not
support; the anchor is a check on your bar, not a quota.

## Output

One JSON object per marriage, same order as the input, exactly these fields:

```json
{"id": "r000123", "good": true, "confidence": "high|medium|low",
 "evidence": "<= 25 words, quoted from the description wherever possible",
 "reason": "affection|collaboration|children|lasted_to_death|adversity|divorce|conflict|infidelity|
            abuse|coercion|thin_record|other",
 "children_together": true, "joint_creative_work": false, "joint_business": false,
 "not_a_marriage": false}
```

`reason` is the single strongest ground for your verdict. Quote real words from the description in
`evidence` — a quote that cannot be found in the description is worse than no quote at all.

## Measured: the quality ranking is correlated with the label (2026-08-28)

The 10,000 marriages were selected and batched by a *record-quality* score (two-sided coverage,
relationship-word count, density, length). Across the first 14 validated batches that score turns out to
predict the verdict:

| moving with quality rank | slope per batch | r |
|---|---|---|
| trouble verdicts (divorce/conflict/infidelity/abuse/coercion) | **−2.44** | **−0.82** |
| `children` | +1.57 | +0.75 |
| `thin_record` | +0.73 | +0.65 |
| narrated-good (affection/collaboration/adversity/lasted_to_death) | +0.36 | +0.24 |

**This is the corpus, not judge drift.** The category that moves most, `trouble`, is the one a judge
cannot invent — a `divorce` verdict requires the text to state a divorce. The judgment-heavy
narrated-good grounds, which are what would inflate if the bar had slipped, are flat.

The mechanism is editorial: divorce, scandal and litigation generate paragraphs, while a quiet
forty-year marriage gets one sentence. So richly-documented marriages are genuinely enriched in
recorded trouble.

**Consequence for modelling, which must be reported with any result:** record verbosity tracks fame,
fame tracks era, and era is readable from a birth date by slow-planet phase. Any model fitted here can
reach the label through *Wikipedia's editorial attention* without touching the couple. This is why the
birth-decade control in `quality_stability.py` is not optional — it is the specific confound this
selection creates, and a doctrine model must beat it, not merely beat chance.
