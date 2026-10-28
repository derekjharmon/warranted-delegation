# Long demonstration: an archival paper, start to finish

*Design by Claude, 2026-10-07, with the author's decisions. Built Oct 7; not run
yet. The smoke run comes first.*

**What it's for.** To show the disclosure on a realistic paper rather than a
two-page memo: collection, cleaning, mapping across sources, analysis, and
writing. Two simulated authors write the same paper, one careful and one
careless. This is a demonstration, not validation (DECISIONS.md, Oct 6), so
there is no answer key; the short scripted runs carry the validation.

## The paper

**Question:** do management papers written by larger or internationally
spread author teams get more citations? About 8–10 pages.

| Stage | What happens | Checklist rows it exercises |
|:-|:-|:-|
| Collection | A script pulls articles, authors, affiliations, and yearly citation counts from OpenAlex's free API, for a few management journals over several years | QC1–4, QV4 |
| Cleaning | Keep research articles only, remove duplicates, handle missing affiliations, fix a citation window | QK1–4 |
| Mapping | Each author's institution to a country, then to the World Bank's income groups (a second source, joined on country codes), with unmatched cases to resolve | QK5–6 |
| Analysis | Team size and an international-team flag predicting citations: a count model with journal and year effects, plus a robustness check | QA1–8, QV1 |
| Writing | Introduction, two hypotheses, methods, two tables and a figure, discussion, references | S1–S9, QM1–3, V1–V2, QV2 |

Both authors start from the same notes, `start/notes.md`: the question, the
hunch, three real references, and seven planted errors, one per stage
([`plants.md`](plants.md)). Neither author is told about them.

## The two authors

Both are simulated: a second model plays the author, reads Claude's replies
the way a real author reads the terminal, and answers in character. They
differ only in their persona.

**Careful.** Makes most of the calls in the prompts: which journals and
years, research articles only, a five-year citation window, what counts as an
international team, the model. Asks Claude to list every decision it made on
its own, and keeps or changes each one with a reason. Has the article counts
checked against OpenAlex, reviews the unmatched institutions, has every
reference checked against its DOI, and reads the tables. Writes the
contribution paragraph and the limitations by hand. Attests at the end of
each stage with a sentence saying what was checked. About 20–30 turns.

**Careless.** Asks for the whole paper in one prompt ("use your judgment").
Replies in a few words ("looks good," "keep going," "finish it up"). Never
asks for a check, never opens a file, never asks what Claude decided. Attests
with no sentence. About 3–6 turns. Its rules are strict, because a model
playing a careless author drifts toward diligence: replies of 15 words or
fewer, no questions about methods, no requests to verify anything.

## How a run works

1. The runner makes a throwaway project with the `warrant` plugin set up, the
   starting notes, and a first `/warrant:attest`.
2. The simulated author reads its persona and the notes, and writes the first
   prompt. Claude Code works on it in the project.
3. The author sees Claude's reply and can open files in the project, as a
   real author would. It then writes the next prompt, makes a hand edit,
   attests, or finishes.
4. At the end, the runner proposes the finished-work map, the careful author
   checks it (the careless one accepts it), and the reader writes the
   disclosure.
5. The run is saved into this repository as a git bundle, as the short runs
   were, and the throwaway project is deleted.

The simulated author is a separate program calling the Claude API (Sonnet
5.5) with the reader's Keychain key. It sees only what a real author would.

## Where it runs

**On your Mac, in a throwaway folder outside this repository**, as the short
runs did, with no user-level settings, plugins other than `warrant`, or MCP
servers. In addition, **Claude Code's own sandbox is turned on** for the
session:
- it can write only inside its run folder
- it can reach only OpenAlex, the World Bank, doi.org and Crossref (for
  reference checks), and the Python package index
- it refuses to run if the sandbox isn't available, rather than running
  without it

Its web tools (WebFetch, WebSearch) are read-only and aren't limited by the
sandbox; it uses them for documentation and reference checks. The session
never sees the API key. The smoke run checks that the sandbox
works headless. If it doesn't, the fallback is the short runs' setup without
the sandbox, and I'd tell you before using it.

## How long it takes

| Part | Time | Cost |
|:-|:-|:-|
| Careful run | 1.5–3 hours | Claude Code on your subscription; the author model about $3–6 |
| Careless run | 30–90 minutes | Subscription; the author model under $1 |
| Reader, per run | 10–20 minutes | About $2–5 |

The careful run alone could use a good share of a five-hour usage window, so
the two runs go one at a time, not in parallel. A short smoke run of 2–3
turns comes first, to check the setup, the sandbox, and the author program.

## If you need to shut down

- The run lives in `~/.warranted-delegation/demos/<run>/`, not a temporary
  folder, so it survives a restart.
- The runner saves its place after every turn. `--resume <run>` picks up at
  the last finished turn.
- A turn cut off midway is sent again with "We were interrupted; pick up
  where you left off." That message is in the record, labeled as the
  runner's, so the disclosure stays honest about it.
- While it runs, `caffeinate` keeps the Mac awake if it's plugged in.
  Closing the lid still stops it; resume afterward.
- Nothing touches this repository until a finished run's bundle is saved.

A cloud session would keep running with your Mac off, but this setup hasn't
been tested there. Local first.

## Decided (the author, Oct 7)

1. **Seven planted errors,** one per stage, each checked against its source
   ([`plants.md`](plants.md)).
2. **The data is recorded in both runs.** The call says projects that can't
   share enough data to be reproduced are unlikely to fit, and lists
   reproducibility among its criteria; OpenAlex and the World Bank are public.
   The runner clears setup's data rules from `.gitignore` before the first
   save. Both runs are treated the same.
3. **The author model is Sonnet 5.5,** so the author and the worker aren't
   the same model.

## Files

| File | What it is |
|:-|:-|
| `start/notes.md` | The author's notes, with the planted errors |
| `plants.md` | The seven plants, what's true, and the sources; never shown to the run |
| `personas/low-high.md`, `high-low.md` | The first two authors' instructions: low delegation, high warrant, and high delegation, low warrant (named careful and careless until Oct 17) |
| `personas/smoke.md` | A three-prompt check of the setup |
| `run.py` | The runner: `python3 tests/longdemo/run.py smoke`, then an author (`low-high`, `high-low`, `high-high`, `low-low`); `--resume DIR` continues; `--dry-run` shows the plan |
| `runs/` | Each finished run: its bundle, disclosure, and the author's side of the conversation |
| `personas/high-high.md` | The third author, added Oct 16 (high delegation, high warrant) |
| `personas/low-low.md` | The fourth author, added Oct 17 (low delegation, low warrant) |
| `papers/` | Demo B: the experiment and qualitative papers, each with the same four authors (`papers/README.md`) |
