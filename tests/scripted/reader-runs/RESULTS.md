# Reader results on the four scored runs

*Redrawn 2026-10-23: the disclosures in `reader-runs/` were drawn again from their saved codes with plugin 0.10.7, in the layout the demonstrations use, which leaves out the section outside the two measures (DECISIONS.md, Oct 22). No codes or scores changed.*

*2026-10-06. Reader 0.6, frozen and attested with the settled key and the
scoring script in `23abd4b` before it saw any scored run. Run with
`tests/scripted/score.py read`, scored with `score.py score`
([`score.md`](score.md)). Written up by Claude.*

*Note added 2026-10-07: the frozen reader reads the live `checklists/`
folder, which gained packs for experiments, qualitative work, and theory on
Oct 7. To reproduce these runs exactly, run `provenance/reader.py` from
commit `23abd4b`. Each run recorded the checklists' hashes in
`reader-run.json`, so a run on different checklists shows.*

## Validation (PLAN criterion 5)

**The reader is validated:** κ is at least 0.6 on all three primary codes.

| Code | Layer | n | Agreement | κ |
| :- | :- | -: | -: | -: |
| Discretion: kept vs handed over | primary | 83 | 86% | 0.71 |
| Judgment certification | primary | 37 | 78% | 0.70 |
| Right-answer certification | primary | 92 | 85% | 0.75 |
| Discretion: given vs taken | second | 37 | 86% | 0.47 |
| Unchecked claims: no check vs wasn't notified | second | 42 | 98% | 0.00 |

**Second layers.**
- **Given vs taken** falls below 0.6. Under PLAN's Deviations item 9, the
  disclosures report "handed over" without the split.
- **"No check" vs "wasn't notified" can't be estimated yet.** The key has
  only one claim coded "wasn't notified," so κ is 0 even at 98% agreement.
  The category stays in the codebook, but it is unvalidated until runs
  produce more cases.

**Listing.** The reader's quotes overlapped 175 of the key's 205 units (85%).
Most of the other 30 it did list, but it quoted a different spot (for
example, the interpretation anchored on "in years when a firm's market value
is 10 percent higher" instead of "The results support the hypothesis"), so
the pre-registered overlap rule doesn't pair them. The reader also lists at a
finer grain, especially numbers in the text: it listed 282 units against the
key's 205.

**Sensitivity check, not pre-registered.** Matching by checklist row first,
then by overlap, pairs 171 units, with κ of 0.74, 0.75, and 0.79 on the
primary codes, and 0.55 for given vs taken. The conclusion doesn't depend on
the matching rule.

**Cost:** $3.21 of API usage for all four runs (14 model calls, about 14
minutes); about $3.30 per full pass across three runs.

## Stability across three runs

The frozen reader was run twice more on the same four records
(`tests/scripted/replicate.py`, outputs in `rep2/` and `rep3/`), since current
models take no temperature setting.

| Run | Kept vs handed over | Judgment certification | Right-answer certification | Given vs taken (second layer) | Key units found | Cost |
| :- | -: | -: | -: | -: | -: | -: |
| 1 | 0.71 | 0.70 | 0.75 | 0.47 | 175 | $3.21 |
| 2 | 0.76 | 0.78 | 0.82 | 0.37 | 171 | $3.37 |
| 3 | 0.81 | 0.78 | 0.77 | 0.18 | 172 | $3.32 |

- **All three runs validate**, with every primary κ between 0.70 and 0.82.
- **Given vs taken is unstable as well as low** (0.18 to 0.47), which
  confirms dropping that split from the disclosures.
- **The disclosures' headline numbers barely move** (decisions handed over /
  handed-over decisions taken back / claims checked, in percent):

| Author | Run 1 | Run 2 | Run 3 |
| :- | :- | :- | :- |
| Careful | 35 / 100 / 40 | 33 / 100 / 32 | 30 / 100 / 29 |
| Unchecked | 23 / 33 / 0 | 31 / 38 / 0 | 25 / 29 / 0 |
| Careless | 83 / 0 / 0 | 84 / 0 / 0 | 87 / 0 / 0 |
| Owned | 93 / 88 / 79 | 88 / 92 / 85 | 90 / 92 / 87 |

The separation of the four cells holds in every run.

## What the disclosures show

These are the reader's own disclosures, before any comparison with the key
([careful](careful/disclosure.md), [unchecked](unchecked/disclosure.md),
[careless](careless/disclosure.md), [owned](owned/disclosure.md)).

| Run | Cell | Decisions handed over | Handed-over decisions the author took back* | Claims checked against a source** |
| :- | :- | -: | -: | -: |
| Careful | Directed tightly, followed up | 35% | 100% | 40% |
| Unchecked | Directed tightly, let additions pass | 23% | 33% | 0% |
| Careless | Abdicated | 83% | 0% | 0% |
| Owned | Delegated a lot, checked and owned | 93% | 88% | 79% |

\* Changed, elaborated and okayed, or okayed.
\** By the author, or by a tool with the author confirming.

The two measures move independently, as the 2×2 predicts:
- **Direction** splits careful and unchecked (little handed over) from careless
  and owned (most handed over).
- **Follow-up** splits careful and owned (taken back and checked) from
  unchecked and careless (neither).

The finished memos can't show this. The careless memo is as correct as the
careful one, and the unchecked memo, the most tightly directed, is the one
that kept all five planted errors.

## A non-Claude reader (Oct 8)

To test whether the agreement holds when Claude isn't grading Claude, the
frozen reader (0.6.1, the same prompts and schemas) was run with OpenAI's
`gpt-5.3-codex` in place of Claude, on the same four records, with the
checklists as they stood at the frozen commit (`23abd4b`), and scored by the
same `score.py` against the same key (`tests/scripted/reader_openai.py`;
outputs in [`openai-gpt-5.3-codex/`](openai-gpt-5.3-codex/score.md)).

| Code | Claude, run 1 | Claude, run 2 | Claude, run 3 | gpt-5.3-codex |
| :- | -: | -: | -: | -: |
| Kept vs handed over (primary) | 0.71 | 0.76 | 0.81 | 0.66 |
| Judgment certification (primary) | 0.70 | 0.78 | 0.78 | 0.68 |
| Claims certification (primary) | 0.75 | 0.82 | 0.77 | 0.79 |
| Given vs taken (second layer) | 0.47 | 0.37 | 0.18 | 0.65 |

It also passes criterion 5's bar (κ ≥ 0.6 on all three primary codes): a
little lower than Claude on the two decision codes and on par for claims. It
found 172 of the key's 205 units (84%; Claude's first run, 85%) and listed at
a finer grain. Given vs taken came out higher than in any Claude run; one run
is not enough to restore that split to the disclosures. The key itself was
half labeled by Claude, so this narrows the "Claude graded Claude" objection
without removing it. 19 model calls, about 41 minutes, 406,851 input and
189,805 output tokens (147,129 of them reasoning).

## The fixed reader on the same four runs (exploratory)

*Added 2026-10-15 by Claude. Exploratory, not a test: the fix was designed
from these runs' misses ([`misses-checked.md`](misses-checked.md)), so these
numbers can't validate it; the frozen reader's preregistered result above
stays the headline (DECISIONS.md, Oct 12). The fixed reader gets its own
preregistered test on new runs ([`../../scripted2/README.md`](../../scripted2/README.md)).*

Reader 0.12 (`plugin/warrant/scripts/reader.py` at `7b3920a`): a places step
adds every other place each unit appears, the transcript shows the
instructions the record captured and sets brainstorm turns aside (neither
occurs in these runs), and coding rules 9 and 10 are new. Run with the spine
and the quantitative pack, the checklist the frozen reader saw, by
[`../explore_fixed.py`](../explore_fixed.py), through the API and through
headless Claude Code with no key, and scored by the same frozen `score.py`
and key. Outputs: [`fixed-0.12-api/`](fixed-0.12-api/) and
[`fixed-0.12-claude-code/`](fixed-0.12-claude-code/).

| | Frozen reader (Oct 6) | Fixed, API | Fixed, headless |
| :- | -: | -: | -: |
| Key units found (of 205) | 175 | 198 | 198 |
| κ, kept vs handed over | 0.71 | 0.80 | 0.76 |
| κ, judgment certification | 0.70 | 0.81 | 0.78 |
| κ, right-answer certification | 0.75 | 0.73 | 0.72 |
| κ, given vs taken (second layer) | 0.47 | 0.37 | 0.13 |
| n, judgment certification | 37 | 45 | 44 |
| Time, all four runs | about 14 min | 26 min | 27 min |
| Cost | $3.21 (API) | $5.87 (API) | none billed; $9.22 at list prices, on the subscription |

- **Listing:** the misses the hand check found, mostly the same call quoted
  elsewhere, are nearly gone: 7 key units unfound on each path, against 30.
- **Codes:** both primary decision codes rose by about 0.1 on both paths;
  right-answer certification held. Given vs taken stays below 0.6, so the
  disclosures keep reporting "handed over" without the split.
- **The two paths** agree closely, the headless path a little lower on every
  code; the new test scores each against the bar on its own.
- **Cost:** the places step adds a model call per 60 units, so a run costs
  about 80% more than the frozen reader's.
