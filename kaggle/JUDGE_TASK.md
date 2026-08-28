# The judging task (binary marriage quality)

Decide, for each historical marriage, whether it went well. Binary: good or bad. Work independently —
do not read any other batch's label file.

## Steps

1. Read the rubric in full: `/Users/arash/Studio/artamatch/kaggle/RUBRIC2.md`.
   **THE KEY RULING:** a dry genealogical entry that names children, with nothing troubled on record, is
   `good` (reason `children`). Dryness of prose is not evidence against a marriage. Only an entry naming
   NO children and giving nothing else at all is `thin_record`/bad. Four judges read this backwards on an
   earlier pass and their batches had to be re-judged — apply it as written.
2. Read your batch: `/Users/arash/.artamatch-dev/bio/batches/batch_<NNNN>.json`. Fields: `id`, `him`,
   `her`, `children_together`, `ended`, `description` — prose from both partners' Wikipedia articles,
   sometimes not in English, which you should read directly. A batch may hold fewer than 200 items;
   judge every item present.
3. Judge EVERY item, in input order.
   - `good` — stated affection; something built together; children named with nothing troubled on record;
     lasted until a death with nothing troubled on record; adversity endured together.
   - `bad` — divorce/annulment/separation (the ending is the verdict, however amicably); conflict;
     infidelity; abuse; coercion; addiction damaging it; stated unhappiness; a marriage of convenience;
     cruelty the couple inflicted together on others; OR the record names no children and gives nothing
     else.
   - Judge ONLY the pair named in `him`/`her`. Ignore prose about a previous spouse, a sibling, a
     same-named relative, or the couple's children's own marriages. Infidelity against a *previous*
     spouse is not this marriage's fault.
   - Trust the prose over BOTH structured fields. In particular do not award `good`/`children` when the
     structured count is nonzero but the prose names no child of this couple.
   - Never invent a story. Do not infer a divorce the text does not state.
   - A stated marriage age under 18 makes it `bad` UNLESS the record carries strong explicit evidence the
     marriage worked (see the rubric's Anne Bradstreet clause).
   - Use `other` for any ground outside the enum.
   - Set `confidence: "low"` when the description is garbled or is plainly about someone other than the
     named pair. This is the signal used downstream to drop wrong-person records, so use it.
   - Set `not_a_marriage: true` for a mistress, concubine, companion, broken engagement, or a union the
     record itself disputes — and still give a verdict.
4. Write `/Users/arash/.artamatch-dev/bio/labels2/batch_<NNNN>.json` — a JSON array, one object per input
   item, **same order and same count as the input**, each exactly:

```json
{"id":"...","good":true,"confidence":"high|medium|low","evidence":"<=25 words quoted from the description where possible","reason":"affection|collaboration|children|lasted_to_death|adversity|divorce|conflict|infidelity|abuse|coercion|thin_record|other","children_together":true,"joint_creative_work":false,"joint_business":false,"not_a_marriage":false}
```

## Calibration

Across a batch, expect roughly half good and half bad. If you land past about 65/35 either way, re-read
the rubric and check your bar — then **report the split you actually found**. Do not manufacture a
balance the descriptions do not support; the anchor is a check on your bar, not a quota.

## How to write it without losing the batch

Emitting 200 objects in one response blows the 64k output limit and loses everything. Work in **passes of
40**. After each pass, read the file back and write it out extended with that pass. Never emit more than
40 objects in one response.

## Validate before reporting

Array length equals the input's item count; ids match input order exactly; no duplicate ids; no evidence
over 25 words; every `reason` in the enum and on the correct side of the verdict; and every evidence
string a real substring of its own item's description, with accents preserved exactly.

## Report back only

The good/bad split, the confidence split, the reason distribution, and any ids that were wrong-person or
not actually a marriage.
