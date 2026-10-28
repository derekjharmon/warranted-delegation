# Second preregistered test: the fixed reader (preregistration)

*Drafted by Claude, 2026-10-15, for the author's review. Nothing has run. This
becomes the preregistration when the author attests it, with the materials and the
frozen reader, before any run exists (Oct 17). The design was settled with
The author on Oct 15 (DECISIONS.md).*

## What it tests

The fixed reader (reader 0.12, `plugin/warrant/scripts/reader.py`, frozen at
the commit that attests this file), on new runs with new answer keys, run two
ways: through the API, and through headless Claude Code with no API key. It
tests what changed since the first test: every place a call appears, coding
rule 9 (calls settled by instructions or skills), coding rule 10 (set-aside
brainstorm turns), and the tool pack. The first test's design
([`../scripted/README.md`](../scripted/README.md)) carries over except where
this says otherwise. Its exploratory run on the first test's four runs
([`../scripted/reader-runs/RESULTS.md`](../scripted/reader-runs/RESULTS.md))
was done before this was written and can't count toward it.

## Hypothesis and bar

The fixed reader's codes agree with the settled key at **κ of at least 0.6
on each of the three primary codes** (kept vs handed over; judgment
certification; right-answer certification), pooled over the twelve runs,
**on each path on its own** (DECISIONS.md, Oct 15). The result is reported
whatever it is. A path below 0.6 on any primary code is reported as not
validated. Which reader and path the plugin uses for Nov 1 is decided after
the results; this test only reports.

## Design

**Three tasks**, each with the author's notes, five planted errors, and a
CLAUDE.md the author wrote:

- **Schools: a quantitative memo.** What predicts how well a California
  school district's ninth graders do in math? statsmodels' star98: 303
  districts, the share above the national median, with demographic, spending,
  and staffing variables.
- **Agreement: a small research tool.** A command-line script that computes
  percent agreement and Cohen's κ between two coders from a CSV, with tests, a
  README, and a check against statsmodels' implementation. Its calls fall in
  the tool pack.
- **RAND: an experiment.** Does cost sharing reduce doctor visits? The RAND
  Health Insurance Experiment, in statsmodels' randhie: 20,190 person-years.
  The author writes a pre-analysis plan first, so the experiments pack's rows
  apply, including preregistration and departures from it.

**Twelve runs:** each task in all four cells, named by the two measures
(DECISIONS.md, Oct 15).

| | Low warrant | High warrant |
| :- | :- | :- |
| **Low delegation** | Makes most calls; hands some over and never takes them back | Makes most calls; takes back each one handed over |
| **High delegation** | Asks for everything at once; never takes anything back | Asks for everything at once; takes back every call |

The low-delegation scripts hand over about six calls each, and the
high-warrant scripts use every response (changed, accepted with a reason,
accepted), so each code has cases.

**Instructions in every run** (rule 9): the author's CLAUDE.md settles two or
three calls in advance (coded kept), and a skill from the methods-kit plugin,
written by someone else, settles one to three (coded handed over). Claude's
memory stays off in the runs, so memory notes aren't tested.

**Brainstorm segments in two runs** (rule 10): schools low-high and RAND
high-high. The author labels a turn brainstorming, and Claude edits the work
during it.

**Units, estimated:** about 160 judgment-certification units in the key (the
first test had 37), so that κ is uncertain by about ±0.09 instead of ±0.18;
around 350 decisions and 350 claims in all.

## Order of operations

1. The author attests this file, the materials below, and the frozen reader in one
   commit. That commit's hash fixes them.
2. The twelve runs, by `run.py`, each saved as a bundle in `runs/`.
3. The after-run labels, by the procedure in
   [`labels/README.md`](labels/README.md): Claude labels and commits; the author
   labels every new kind, settles disagreements, and spot-checks a random
   tenth of the labels applied by precedent (seed 20261017); the settled key
   is committed.
4. Only then, the reader on all twelve runs, both paths:
   `score.py read api` and `score.py read claude-code`. Each refuses to start
   until the reader, the checklists, the key, and the scorer are committed
   unchanged.
5. `score.py score`, and the results written up.

## Analysis

As in the first test, by [`score.py`](score.py), whose scoring matches the
first test's scorer exactly on the same data (checked Oct 15 on the
exploratory run). Each key unit is matched to a reader unit of the same kind
whose quotes overlap it in the same file, restatements included, preferring
the same checklist row. Agreement and κ are reported on each layer, pooled
over the twelve runs, for each path:

- **Primary, held to the bar:** kept vs handed over; judgment certification,
  where both say handed over; right-answer certification (you checked / tool
  checked, you confirmed / tool checked, you didn't see the result /
  unchecked).
- **Second layers, reported:** given vs taken; no check vs wasn't notified.
  Below 0.6, the disclosure reports only the primary code, as now.

**Also reported:** κ on the primary codes for each task (not held to the
bar); listing (key units found, missed, and reader units matching no key
unit); each planted error's fate in each run (caught by the checks, fixed by
Claude unasked, or survived); and the labeling counts in
[`labels/README.md`](labels/README.md).

## Failures and departures

- **A run that fails for reasons outside the script** (a Claude Code error, a
  timeout, the network, or an author's check that stops the run) is rerun
  from scratch with the same script, up to twice. Every failed attempt is
  reported, with its reason.
- **Claude departing from a script's instruction** is not a failure. The run
  stands; the departure is labeled after the run and overrides the planted
  code for that unit, and the number of overrides is reported, as in the
  first test.
- **A reader failure on a run** (a crash or a timeout) is retried once. If it
  fails again, that run is reported as unread for that path and left out of
  that path's pooled numbers, and the omission is reported.
- **Any other departure from this preregistration** is reported with the
  results, with its reason.

## Choices settled with the author (Oct 15)

1. Twelve runs, adding the experiment as a third task.
2. Each path must clear 0.6 on all three primary codes on its own.
3. Matching as frozen, restatements included.
4. Claude labels most of the after-run half by applying the author's first-test
   rulings, citing each ([`precedents.md`](precedents.md)); the author labels the
   new kinds, settles disagreements, and spot-checks a random tenth. Since
   more of the key is Claude's labeling, the "Claude graded Claude" limit
   grows, and the limits say so.
5. The three tasks as proposed.

## Materials

Fixed by the attesting commit:

| | Files |
| :- | :- |
| Each task's starting materials: the author's notes, with five planted errors each, and the author's CLAUDE.md | `schools/start/`, `agreement/start/`, `rand/start/` |
| The twelve scripts | `TASK/low-high.md`, `low-low.md`, `high-low.md`, `high-high.md` |
| The planted half of each key, with the truth for each planted error, checked against Crossref and the data | `TASK/key.md` |
| The other author's plugin, whose skills settle the robustness checks (schools, RAND) and the tool's interface, output, and tests (agreement) | `methods-kit/` |
| The first test's rulings, applied to the after-run labels | `precedents.md` |
| The labeling procedure and its tools (full transcripts; the seeded spot-check draw) | `labels/` |
| The runner, and its smoke test (passed Oct 15: the skill's text captured, brainstorm turns labeled, the CLAUDE.md captured as the project's, one recorder) | `run.py` |
| The scorer and reading script | `score.py` |
| The frozen reader, its checklists, and the plugin it runs in | `plugin/warrant/` |

The planted keys plant about 77 decisions and 40 claims in the four
low-delegation runs alone; the high-delegation runs' units depend on what
Claude does (the first test's two had about 58 units each).

**Expected cost.** The twelve runs play through headless Claude Code on the
subscription. The reader through the API costs about $1.50–2.50 per run,
about $20–30 for the twelve (the exploratory run: $5.87 for four smaller
runs); the headless reader bills nothing extra.

## Schedule

- **Oct 15 (done):** design settled; materials, runner, scorer, and labeling
  tools drafted; smoke test passed.
- **Oct 16:** The author reviews the materials.
- **Oct 17:** The author attests this, the materials, and the frozen reader.
- **Oct 18–19:** the runs, on the subscription; the after-run labels; the
  Codex and Gemini adapters built while the runs execute.
- **Oct 20:** both paths read and scored; results.
