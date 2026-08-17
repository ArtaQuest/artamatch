# %% [markdown]
# # ArtaMatch Astrology — write an astrology model, and be scored on it
#
# > *Let's end this loneliness epidemic with astrology.*
#
# This is the same question as the [ArtaMatch Astrology
# competition](https://www.kaggle.com/competitions/artamatch-astrology), asked of a language model as a
# **modelling** task rather than a guessing one.
#
# The model is not shown couples and asked for probabilities. It is asked to **write the astrology** — a Python
# function that turns two birth dates into a prediction — and that function is then fitted, run on couples it has
# never seen, and scored by AUC. The number on the leaderboard is the AUC of the code it wrote.
#
# ## Why this and not couple-by-couple guessing
#
# An earlier version of this task read out 120 couples and asked for a probability each. That measures pattern
# recall over dates a model may well have memorised from Wikidata, and it caps what can be learned at whatever the
# model can hold in one prompt. Writing a model instead means the astrology has to be *stated as a rule* —
# sun-sign compatibility, a synastry aspect, a sexagenary clash, a nakshatra kūṭa — and the rule is then tested on
# 20,000 couples at once. A rule that only works on the couples in the prompt cannot survive that.
#
# ## What is scored
#
# One AUC, on a held-out slice of the training file that the generated code never sees while fitting. Same metric
# as the competition, so a score here sits on the same scale as a leaderboard place.
#
# | reference | AUC |
# |---|---|
# | chance | 0.500 |
# | signed difference of the two dates | reported per run |
# | the era rule — the two birth years and their mean | reported per run |
# | the Foundation's 19-tradition stack | reported per run |
#
# The references are **computed on the same held-out rows every run** and printed beside the score, rather than
# quoted from a previous dataset. They were hardcoded here until the question changed, at which point three
# numbers describing a retired parenthood dataset were being printed as though they described this one.
#
# **The era rule is the one that matters.** About 32% of the training marriages reach thirty years against 44% of
# the held-out ones, so a model that beats chance but not the era rule has read the calendar rather than the
# couple. That distinction is the point of the exercise.
#
# ## The rules given to the model
#
# It gets one attempt, plus one repair attempt if its code raises — which is what a person would get. numpy,
# pandas and scikit-learn are available; there is no internet and no ephemeris library, so any astronomy has to be
# arithmetic on the dates. Failing to produce runnable code scores 0.5, the same as guessing, because a model that
# does not run is worth exactly what a coin is.

# %%
import csv
import glob
import io
import re
import traceback

import numpy as np
import pandas as pd

import kaggle_benchmarks as kbench

SEED = 20260815
HOLDOUT = 0.30          # of the training file, held back from the generated code entirely
MAX_ROWS = 60000        # cap so a slow generated model cannot run the container out of time

BRIEF = """You are competing on ArtaMatch Astrology. Write an astrology model.

THE DATA. A pandas DataFrame with exactly three columns:

    dob_man            the man's date of birth,   'YYYY-MM-DD'
    dob_woman          the woman's date of birth, 'YYYY-MM-DD'
    lasted_30_years    1 if their marriage lasted thirty years or longer, else 0

The marriage's own dates are NOT given to you. They were used to compute the label and then discarded, because
the wedding year is the most era-revealing thing about a couple.

Everyone here was born between 1600 and 1900, a window chosen so that all of them are certainly dead — no
marriage is still running, and none was cut short by the records ending. Both dates in the scored rows are known
to the day.

A TRAINING ROW MAY BE INCOMPLETE, and this is deliberate rather than dirt. `00` means a component is unknown and
`0000-00-00` means the partner is absent from the source entirely:

    1794-06-12,1801-03-27,1     both known to the day
    1802-00-00,1809-11-00,0     his year only; her year and month
    1777-04-30,0000-00-00,1     she is not in the source at all

A marriage's duration is known just as exactly when one spouse's birthday is not, so those rows carry a real
label and half an input. Drop them in one line if you want only clean rows, or use them — there are several times
as many training rows with them than without. **The rows you are SCORED on are always complete and
day-precision**, so you never have to predict from a placeholder.

YOUR TASK. Return Python defining exactly this function:

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        '''Fit on `train` (which has lasted_30_years) and return one probability per row of `test`
        (which does not). Return a 1-D array of length len(test).'''

WHAT IS SCORED. Area under the ROC curve of your probabilities against the truth, on couples your code never
saw. Only the ranking matters.

BUILD ASTROLOGY. The features should come from astrological structure computed from the two dates — tropical or
sidereal sun position, the synodic phase of the Moon, aspects between the two charts, the Chinese sexagenary
cycle, a nakṣatra or kūṭa score, the Maya Long Count, whatever tradition you want to argue for. You may use any
tradition, and you may combine several.

CONSTRAINTS.
  * numpy (np), pandas (pd) and scikit-learn are importable. NOTHING ELSE — there is no internet and no
    ephemeris library, so any astronomy must be arithmetic you write yourself.
  * `predict` must return within a few minutes on 40,000 training rows and 18,000 test rows.
  * No file or network access. No printing.

WHAT WILL NOT WORK, said plainly so you do not waste the attempt: the strongest single effect in this data is
WHEN the couples were born, not who they were — earlier-born couples died younger and their marriages had less
room to reach thirty years. The era rule is computed on your held-out rows and reported against you, and you are
being scored ACROSS TIME: you fit on couples born up to 1850 and are scored on couples born after it, so a rule
that interpolates the calendar you trained on will not transfer. If your model beats chance only because it dated
the cohort, that will be visible.

One more thing you cannot see and should not try to exploit: whether a marriage ended by divorce or by a death is
not a column. Marriages with a recorded ending reach thirty years far less often than ones that ran until
somebody died, and that difference is the largest confound here.

Reply with ONE Python code block and nothing else."""

REPAIR = """Your code raised this:

{err}

Return the corrected Python — the same `predict(train, test)` contract, one code block, nothing else."""


def find_train():
    for pattern in ("/kaggle/input/artamatch-astrology/train.csv",
                    "/kaggle/input/*/train.csv", "/kaggle/input/**/train.csv", "**/train.csv"):
        hits = sorted(glob.glob(pattern, recursive=True))
        if hits:
            return hits[0]
    raise RuntimeError("train.csv not found; attach artaquest-foundation/artamatch-astrology. "
                       f"/kaggle/input holds {sorted(glob.glob('/kaggle/input/*'))}")


def label_of(df):
    """The target column, discovered. Hardcoding it meant a renamed target silently scored nothing."""
    cand = [c for c in df.columns if c not in ("id", "dob_man", "dob_woman")]
    if len(cand) != 1:
        raise RuntimeError(f"expected exactly one target column, found {cand}")
    return cand[0]


def later_year(df):
    """The later of the two KNOWN birth years. An absent partner is `0000-00-00`, and a plain max() over the
    year strings would make that absent partner the later birth at year zero."""
    a = df.dob_man.str[:4].astype(int).to_numpy()
    b = df.dob_woman.str[:4].astype(int).to_numpy()
    return np.maximum(np.where(a == 0, b, a), np.where(b == 0, a, b))


def load():
    """Split the training file the way the COMPETITION splits: by time, not at random.

    This used to hold out a random 30%, while claiming a score here sits on the same scale as a leaderboard
    place. It does not — measured on this project's own data, the same stack scored 0.6452 inside its training
    era and 0.5159 across it, so a random holdout flatters a model by about 0.13 against the competition it is
    supposed to mirror. The later 30% of couples by birth year are held out instead.

    The two halves also differ in precision, exactly as the dataset does. Coarse and one-sided rows stay in the
    FIT half — the brief tells the model they are there and they are most of the data — while the HELD half is
    strictly complete and day-precision, so a model is never scored on a row it could only guess at.
    """
    df = pd.read_csv(find_train(), dtype={"dob_man": str, "dob_woman": str})
    lab = label_of(df)
    complete = ~(df.dob_man.str.contains("-00") | df.dob_woman.str.contains("-00"))

    yr = later_year(df)
    cut = int(np.quantile(yr[complete.to_numpy()], 1.0 - HOLDOUT))
    held = df[complete.to_numpy() & (yr > cut)].reset_index(drop=True)
    fit = df[yr <= cut].reset_index(drop=True)          # every precision, including one-sided rows
    if len(fit) > MAX_ROWS:
        fit = fit.sample(n=MAX_ROWS, random_state=SEED).reset_index(drop=True)
    if held.empty or held[lab].nunique() < 2:
        raise RuntimeError(f"the held-out slice above {cut} has fewer than two classes — cannot score")
    print(f"  split by TIME at {cut}: fit on couples born up to it, scored on the ones after")
    return fit, held


def auc(y, s):
    """Rank AUC with ties averaged, written out so the task does not depend on sklearn being importable."""
    pairs = sorted(zip(np.asarray(s, float).tolist(), np.asarray(y, int).tolist()))
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    n1 = sum(1 for _, yy in pairs if yy == 1)
    n0 = len(pairs) - n1
    if n1 == 0 or n0 == 0:
        return 0.5
    s1 = sum(r for r, (_, yy) in zip(ranks, pairs) if yy == 1)
    return (s1 - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def extract_code(text):
    """The fenced block, or the whole reply if the model forgot the fence."""
    t = getattr(text, "text", str(text))
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", t, re.S)
    if blocks:
        return max(blocks, key=len)
    return t


def run_candidate(code, fit, held):
    """Execute the generated code and get its probabilities for the held-out rows.

    Anything it raises is returned as text so it can be handed back for one repair. A model that cannot produce
    runnable code scores chance, which is what a coin scores, and that is the honest grade.
    """
    ns = {"np": np, "pd": pd, "__name__": "__candidate__"}
    exec(compile(code, "<candidate>", "exec"), ns)          # noqa: S102 — grading generated code is the task
    fn = ns.get("predict")
    if not callable(fn):
        raise RuntimeError("no callable `predict` was defined")
    out = fn(fit.copy(), held.drop(columns=[label_of(held)]).copy())
    out = np.asarray(out, dtype=float).ravel()
    if out.shape[0] != len(held):
        raise RuntimeError(f"predict returned {out.shape[0]} values for {len(held)} rows")
    if not np.isfinite(out).all():
        raise RuntimeError("predict returned non-finite values")
    return out


def references(fit, held):
    """The rules the model has to beat, COMPUTED on these held-out rows rather than quoted.

    They were three hardcoded constants, and when the question changed from parenthood to marriage duration the
    task went on printing numbers that described a retired dataset as though they described this one. A reference
    that cannot move when the data moves is not a reference.

    Direction is folded away with max(a, 1-a) because which way the era points is itself a property of the
    dataset — for parenthood the older couple was likelier, for duration it is the later-born one — and the
    question is only how much of the label the calendar explains.
    """
    lab = label_of(held)
    y = held[lab]
    out = {}
    era = (held.dob_man.str[:4].astype(int) + held.dob_woman.str[:4].astype(int)).to_numpy(float)
    a = auc(y, era)
    out["the era rule (sum of the two birth years)"] = max(a, 1.0 - a)
    gap = (held.dob_woman.str[:4].astype(int) - held.dob_man.str[:4].astype(int)).to_numpy(float)
    a = auc(y, gap)
    out["the signed age gap (woman - man)"] = max(a, 1.0 - a)
    return out


@kbench.task(
    name="ArtaMatch Astrology",
    description="Write an astrology model from two birth dates; scored by AUC on couples it never saw.",
)
def artamatch_astrology(llm) -> float:
    fit, held = load()
    lab = label_of(held)
    print(f"  {len(fit):,} couples to fit on, {len(held):,} held out "
          f"({held[lab].mean():.1%} positive; the fitting half is {fit[lab].mean():.1%})")

    code = extract_code(llm.prompt(BRIEF))
    print(f"  the model wrote {len(code):,} characters of Python")
    preds, err = None, None
    try:
        preds = run_candidate(code, fit, held)
    except Exception:
        err = traceback.format_exc(limit=3)[-1200:]
        print(f"  first attempt raised; offering one repair\n{err.splitlines()[-1][:160]}")
        code2 = extract_code(llm.prompt(REPAIR.format(err=err)))
        try:
            preds = run_candidate(code2, fit, held)
            print("  the repair ran")
        except Exception:
            print(f"  the repair also raised: {traceback.format_exc(limit=2).splitlines()[-1][:160]}")

    if preds is None:
        print("\n  no runnable model was produced — scoring chance, which is what it is worth")
        return 0.5

    got = auc(held[lab], preds)
    refs = references(fit, held)
    era = refs["the era rule (sum of the two birth years)"]
    print(f"\n  AUC of the model it wrote : {got:.4f}")
    for name, val in refs.items():
        print(f"  {name:<41}: {val:.4f}")
    print(f"\n  {'beats the era rule — it read the couple' if got > era else 'does NOT beat the era rule — it read the calendar'}")
    return got


artamatch_astrology.run(kbench.llm)
