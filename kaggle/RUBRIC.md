# The marriage-quality rubric (ArtaMatch, 2026-08-28)

You are reading what the historical record says about one marriage, assembled from both partners'
Wikipedia articles, plus two structured facts: how many children the couple had together, and how the
record says the marriage ended. Classify the **relationship**, one of three classes.

## The classes

**happy** — the record shows a marriage that worked and gave something back. Any of:
- lasted until a death and the prose carries affection, devotion, partnership, "inseparable", "happy",
  long companionship, nursing through illness, grief at the loss;
- they built something together: children raised together, joint creative work (co-authored, co-composed,
  co-starred, one the other's model/muse/collaborator), a company or practice founded together, a
  political or scientific partnership, shared philanthropy;
- they stood by each other in real adversity (exile, war, imprisonment, poverty, illness).

**neutral** — the record shows a marriage that simply existed. Typical cases:
- dynastic, arranged or political matches described only as facts (who married whom, when, titles);
- a bare mention: "he married X in 1878; they had two children", with nothing about the relationship;
- ended by a death with no affective detail;
- mixed or contradictory evidence where neither reading dominates;
- an amicable divorce or annulment with no conflict recorded, and no lasting harm described.

**toxic** — the record shows harm, breakdown or cruelty. Any of:
- divorce with conflict: acrimony, contested custody, public feud, litigation, ruinous settlement;
- infidelity, a long-running affair, bigamy, abandonment, desertion;
- violence, abuse, coercion, forced or child marriage, imprisonment of one by the other;
- alcoholism, addiction or gambling described as damaging the marriage;
- estrangement, separation living apart in hostility, described as unhappy, miserable, loveless;
- one partner's death caused or hastened by the other, murder, or suicide connected to the marriage.

## How to judge

1. **Judge the relationship, not the people.** Fame, rank, wealth, achievement and nationality are
   irrelevant. A famous artist's cruel marriage is toxic; an unknown couple's devoted one is happy.
2. **Never judge by the century or by social class.** A 16th-century dynastic match is not "toxic"
   for being arranged, and a modern marriage is not "happy" for being modern. If the prose gives no
   affective information, that is **neutral**, whatever the era.
3. **Divorce is not automatically toxic.** Divorce plus conflict/infidelity/abuse is toxic. A quiet
   divorce with no recorded conflict is neutral. A marriage that ended in divorce is never happy.
4. **Contributions count.** Children raised together, art made together, a business built together,
   scientific or political collaboration — these are what a marriage gave the world, and they push
   toward happy even when the prose is otherwise dry. Children alone, with no other signal, is
   *weak* evidence: many dynastic marriages produced heirs and nothing else. Children plus any warmth,
   or children plus long duration until death, is happy.
5. **Read for what is actually claimed.** Do not infer abuse from a bad temper mentioned in passing,
   and do not infer devotion from a long marriage alone. Quote the words you relied on.
6. **When the text is about careers and says nothing about the marriage, say neutral with low
   confidence.** Do not invent a story.
7. **The happy bar is real evidence, not atmosphere.** Two independent judges of the same 120 marriages
   agreed 92% of the time and never once swapped happy for toxic — every disagreement was here, on thin
   positive evidence. So: a shared social life, a salon, attending events together, a honeymoon trip, a
   grand wedding, or simply living in the same house is **neutral**. Happy needs one of:
   affection or devotion actually stated; sustained collaboration (co-created works, a business, a
   practice, a campaign); children together *plus* warmth or a marriage lasting until death; or standing
   by each other through real adversity.

## Output

Return one JSON object per marriage, in the same order, with exactly these fields:

```json
{"id": "r000123", "label": "happy|neutral|toxic", "confidence": "high|medium|low",
 "evidence": "<= 25 words quoted or closely paraphrased from the description",
 "children_together": true, "joint_creative_work": false, "joint_business": false,
 "conflict": false, "infidelity": false, "abuse": false}
```

The seven booleans are what you actually saw evidence for in this description — not guesses.
