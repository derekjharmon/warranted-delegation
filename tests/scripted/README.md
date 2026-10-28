# Scripted test task

*Drafted by Claude, 2026-10-06, for the author's review. Nothing has run.*

**What it's for.** It produces small projects whose answers we know in
advance. They are used to score the reader against those answers (PLAN
criterion 5, as changed Oct 5), and to show that careful and careless work
produce different disclosures (PLAN's seeded-error demonstration).

## The task

A memo of 2–3 pages, `memo.md`, asking whether a firm's market value predicts
how much it invests. The data are the Grunfeld panel bundled with Python's
statsmodels: 11 US firms, 1935–1954, with investment, market value, and
capital stock. The finished work consists of `memo.md` (with its reference
list), `analysis/analysis.py`, and `output/table1.md`.

**Starting materials, the same for every run.** An empty project with the
tool installed, plus the simulated author's notes: a reference list,
[`start/notes/references.md`](start/notes/references.md), and paragraphs
drafted earlier, [`start/notes/draft.md`](start/notes/draft.md). The three
references are real and were checked against Crossref on Oct 6. The notes
carry **five planted errors**, one for each kind of checkable claim: a
reference entry, a citation description, a factual claim, a reported number,
and a methods description. They're listed in the [answer key](answer-key.md).
The careful run's checks should catch all five, and the careless run should
let them through.

## The runs

| Run | Cell in the 2×2 | What the simulated author does |
| :- | :- | :- |
| [Careful](careful.md) | Directed tightly and followed up | Makes most calls in the prompts. Hands a few over and takes each back, by changing it or by accepting it with a reason. Has checks run and reads them. Writes the Limitations section by hand. Attests with a sentence |
| [Unchecked](unchecked.md) | Directed tightly, but let additions pass | Gives the same direction as the careful author and hands over the same three calls, but never takes them back: no response to what comes back, no checks, no asking what Claude decided on its own. Attests as soon as the writing is done |
| [Careless](careless.md) | Abdicated | Asks for the whole memo in one prompt ("pick whatever approach you think is best"), then attests without comment |
| [Owned](owned.md) | Delegated a lot, but checked and owned it | Opens with the careless prompt word for word, then asks Claude what it decided, takes each call back, has everything checked, and checks two things personally. Added after the other three ran |

Together the four runs pull the two measures apart. Careful and unchecked
differ only in follow-up, the second measure, and so do owned and careless.
Unchecked and careless differ mainly in direction, the first, and so do
careful and owned. The unchecked run is also where Claude's unasked
additions should show most clearly as taken and not notified.

**Development material.** The reader is built and tuned only on a separate
[development run](dev-mixed.md), never on the four scored runs. The author attests
the frozen reader before it sees them.

## How a run works

1. **Setup.** The runner makes a throwaway project outside this repository,
   installs the tool without GitHub, and copies in the starting materials.
   The runner is a script, not yet written; the author sees it before it runs.
2. **Playing the script.** The runner sends the script's lines to Claude Code
   in order, in one headless session. Between turns it makes the author's
   hand edits, and it sends the `/attest` lines as written. The lines don't
   adapt to Claude's replies; each is worded to make sense whatever Claude
   says.
3. **The author's own checks.** Where the script says the author checked
   something, the runner first does that check for real: it reruns the
   script and compares the table, or looks the reference up on Crossref.
   That way the statement is true of the simulation. If a check fails, the
   run stops.
4. **Saving.** At the end, the run is saved here as a git bundle,
   `tests/scripted/runs/<run>-<date>.bundle`, a complete history anyone can
   clone. It records the Claude Code version and model. Then the throwaway
   project is deleted.

## The answer key

It has two halves.

- **Planted, before the run** ([`answer-key.md`](answer-key.md)). For every
  unit the script settles: where the discretion sat, and how the author
  responded. The author attests the key before any run, so the commit's date shows
  it came first.
- **Labeled after the run, by the author and Claude independently.** This half
  covers:
  - everything Claude did without being asked (discretion taken)
  - whether its replies told the author about each decision, which decides
    "ignored" versus "wasn't notified"
  - any checks it ran unasked
  - any place it departed from a planted instruction

  Agreement between the two of us is reported, and the author settles
  disagreements. A departure overrides the planted code for that unit, and
  the number of overrides is reported.

## Scoring

The reader codes each run without seeing the key. Agreement is reported as κ
for each of the three codes, pooled over runs:
- discretion
- judgment certification
- right-answer certification

It is reported whatever it is. Below 0.6 on any code, the reader is reported
as unvalidated, and the demonstration's disclosures are coded by hand (PLAN).

**Discretion is scored in two layers.**
- **Primary: kept versus handed over,** where handed over is given and taken
  combined. This is what the first measure uses, and coders should agree on
  it even when the request was broad.
- **Secondary: given versus taken,** among the calls handed over. It has its
  own κ and is flagged as less reliable where the request was broad, since
  the line then depends on how far the request reached.

The 0.6 rule applies to the primary layer. If the secondary layer falls
below 0.6, the disclosure reports only "handed over," and the measure loses
nothing.

**Right-answer certification is scored the same way** (rule 11): "no check"
and "wasn't notified" count together as unchecked in the primary layer, and
the split between them, which marks where the tool went beyond, is a second
layer.
Listing is reported separately: how many of the key's units the reader
found, and how many units it found that the key doesn't have.

## The simulated author

Claude wrote every line the simulated author types, including the
attestation sentences and the Limitations paragraph, as part of the script.
No person did this work, and the paper says so.

## Before scoring

PLAN needs two Deviations lines. The wording, with the author's reasons, comes
later.
1. **The key is written in two halves.** Criterion 5 says the true codes are
   written down before each run, but the hand-labeled half can only be
   written after.
2. **Discretion is scored in two layers.** The 0.6 rule applies to kept
   versus handed over. A low score on given versus taken drops that split
   from the disclosure instead of invalidating the reader.
