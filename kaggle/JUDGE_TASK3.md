# The judging task (RUBRIC3, two scales)

Work independently. Do not read any other batch's output file.

1. Read `/Users/arash/Studio/artamatch/kaggle/RUBRIC3.md` in full. It is short and it is the whole
   task. **The rule four judges got backwards last time:** *"He married X in 1878; they had three
   children"* is **warmth 1, trouble 0** — not a happy marriage. And a divorce with no reason given is
   **trouble 1**, not 2 or 3.

2. Read your batch: `~/.artamatch-dev/bio/batches3/batch_<NNNN>.json`. Fields: `id`, `him`, `her`,
   `children_together`, `ended`, `description`. The prose is assembled from both partners' Wikipedia
   articles and is often not in English — read it directly, do not translate first.

3. Score **every** item, in input order. One JSON object per line, nothing else — no preamble, no
   commentary, no markdown fence.

   ```
   {"i":"s000123","w":2,"t":0,"g":"aff","q":"<= 12 words, verbatim","nm":0,"ch":1,"cw":0,"cb":0}
   ```

4. Write to `~/.artamatch-dev/bio/labels3/batch_<NNNN>.jsonl`. If that file already exists and holds
   as many lines as your batch has items, stop — it is done.

## What will be checked automatically

- **every `q` must appear verbatim** in its own description. This is checked by string search, and a
  batch below 90% is re-run. Quote real words; if there is nothing worth quoting, use `""`.
- every `i` present, exactly once, in input order
- `w` and `t` in 0–3, `g` from the seven allowed values
- the distribution of `w` and `t` is compared with neighbouring batches; a batch that is a large
  outlier is re-judged, the same divergence check that caught six drifting batches last time

## What not to do

- Do not aim for a balance. There is no expected split. Report what you read.
- Do not infer a divorce, an affair or a happiness the text does not state.
- Do not judge by era, nationality, rank or fame. Birth dates are deliberately absent from the batch;
  if the prose contains dates, they are not evidence about the marriage.
- Do not let a previous spouse, a sibling, a same-named relative or the couple's own children into the
  judgement. If the named partner barely appears, both scores are 0.
