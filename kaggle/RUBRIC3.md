# RUBRIC3 — two questions about one marriage

*Proposed replacement for RUBRIC2.md. Not yet in use.*

You are reading what the historical record says about **one marriage**, assembled from both partners'
Wikipedia articles, plus two facts: how many children the couple had together, and how the record says
the marriage ended. The prose is often not in English; read it directly.

**Do not give a verdict.** Answer two questions about what is *written*.

---

## warmth 0–3 — how much does the record say this went well?

| | |
|---|---|
| **0** | nothing about the relationship itself |
| **1** | one dry fact only — they stayed married, they had children |
| **2** | something described — they worked together, stood by each other, were devoted |
| **3** | the record dwells on it — letters, grief at the loss, a partnership others wrote about |

## trouble 0–3 — how much does the record say it went badly?

| | |
|---|---|
| **0** | nothing troubled |
| **1** | a bare ending — a divorce or separation named, no reason given |
| **2** | something described — an affair, estrangement, litigation, a marriage called unhappy |
| **3** | the record dwells on it — violence, coercion, sustained cruelty, bigamy |

---

## Three rules, each earned by a real failure

1. **Score what is written, never what you infer.** *"He married X in 1878; they had three children"*
   is **warmth 1, trouble 0** — a marriage we know almost nothing about. In the last corpus this was
   3,177 marriages and every one of them was scored *happy*.

2. **A bare divorce is trouble 1.** Ending a marriage was legally impossible for most of the people in
   this corpus and routine for the rest, so the bare fact says more about the century than about the
   couple. Only acrimony the record actually describes raises it to 2 or 3.

3. **Judge only the pair named in `him` and `her`.** Descriptions bleed in a previous spouse, a
   sibling, a same-named relative, or the couple's own children. Ignore all of it. If the named
   partner barely appears, both scores are 0.

**There is no expected balance. Do not aim for one.** Report what you read.

---

## Seven worked examples

| what the record says | w | t | why |
|---|---|---|---|
| "He married Mary Ellis in 1878; they had three children." | 1 | 0 | a dry fact, not a happy marriage |
| "They married in 1931 and divorced in 1938." | 0 | 1 | a bare ending; the century, not the couple |
| "They divorced in 1938 after his affair with the actress became public." | 0 | 3 | the trouble is described |
| "The couple co-authored six books; he called her 'the better half of every page'." | 3 | 0 | described, and dwelt on |
| "She nursed him through his final illness; they had been married fifty-one years." | 2 | 0 | described support, not just duration |
| "Their marriage was passionate and violent; both were repeatedly arrested." | 3 | 3 | both true; the derivation drops it |
| *description is almost entirely about his first wife* | 0 | 0 | nothing about this pair |

---

## Output — one JSON object per marriage, on its own line, same order as the input

```json
{"i":"r000123","w":2,"t":0,"g":"aff","q":"<= 12 words, verbatim","nm":0,"ch":1,"cw":0,"cb":0}
```

| key | meaning |
|---|---|
| `i` | the row id, copied exactly |
| `w`, `t` | warmth and trouble, 0–3 |
| `g` | the single strongest thing the record says — one of `aff` `collab` `kids` `endured` `divorce` `harm` `none` |
| `q` | ≤ 12 words, **verbatim** from the description. A quote that cannot be found is worse than no quote |
| `nm` | 1 if these two were never actually married — a mistress, a companion, a broken engagement |
| `ch` | 1 if the prose names children of **this** pair. Trust the prose over the structured count |
| `cw`, `cb` | 1 if they made creative work together / ran a business together |

No prose, no preamble, no trailing commentary. One line per marriage, nothing else.

---

## The label is derived in code, never judged

```
margin = w − t

happy     margin >= +2
unhappy   margin <= −2
unused    |margin| <= 1
```

One symmetric rule. It drops the empty records — (0,0), (1,0), (0,1) — and the genuinely ambiguous
ones — (2,2), (3,3) — and keeps only what the record is clear about. Nothing is coerced into a class
for want of evidence, which is the single defect that made the previous label a clock: RUBRIC2 sent
`thin_record` to **bad**, and thin records skew old.

## Why two scales and not one

A single −3…+3 scale cannot separate *"the record says nothing"* from *"warm but troubled"* — both net
to zero. Two axes is the smallest design that tells absence apart from balance, and absence is the
class that must be dropped rather than labelled.

This is **not** the failed `neutral` class of the first pass, where 69% of marriages hid in the middle.
That let a judge avoid grading the marriage. Here the judge never grades the marriage at all: it
reports two counts about the text, and the middle is computed.
