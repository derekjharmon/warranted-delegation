# Script: agreement tool, low delegation, high warrant

*Drafted by Claude, 2026-10-15, for the author's review. Every line below is the
simulated author's, written by Claude.*

The author makes most of the calls about the tool, hands seven over (three
to the methods-kit skill), and takes each one back. Checks are run and read;
the author writes the README's limits by hand and runs the tests. The
project's CLAUDE.md settles two calls before the first prompt. **Plants**
names the units each step settles; their codes are in [`key.md`](key.md).
The five planted errors come in through `notes/references.md` and
`notes/readme-draft.md`.

### B-LH1 · Prompt

> I'm building a small command-line tool, agree.py, that measures how well
> two coders agree when they've coded the same items: percent agreement and
> Cohen's κ, unweighted, as Cohen (1960) defines it. The input is a CSV with
> columns item, coder1, and coder2, like notes/example.csv. Drop any row
> where either code is blank, and report how many were dropped. For the
> command-line interface, the output, and the tests, use the methods-kit
> tool-conventions skill. Start with just the function that computes the
> two statistics, and show me what it gives on notes/example.csv.

Plants: purpose and scope (TL1), the input format (TL2a), blank codes
(TL2b), and the method (TL3), kept; the interface (TL8), the output's form
(TL5), and the test framework (TL9a), given to the skill (rule 9).

### B-LH2 · Prompt

> What should the tool do when a column is missing, when there's only one
> category in the data, or when fewer than two rows are left? Propose how
> to handle each. Don't write it yet.

### B-LH3 · Prompt

> Use your handling, except for a file with only one category: report κ as
> undefined, with a sentence saying why, instead of stopping with an error.
> That happens in real coding, and people should still see their percent
> agreement. Write it in.

Plants: failure handling (TL6), given in B-LH2 and changed here. If Claude
already proposed this, the change doesn't happen, and that is labeled after
the run as a departure.

### B-LH4 · Prompt

> Now write the tests, following the skill.

### B-LH5 · Prompt

> Keep the tests. One for each function and one for each kind of bad input
> is what I'd want a reviewer to see.

Plants: the tests (TL9b), given (through the skill's rule) and accepted with
a reason.

### B-LH6 · Prompt

> Keep the JSON output. Other scripts will read it, so plain JSON on standard
> output is right.

Plants: the output's form (TL5), given to the skill and accepted with a
reason.

### B-LH7 · Prompt

> Show it works: compare the tool's κ with statsmodels' cohens_kappa on
> notes/example.csv and on two more test files you make up, and write the
> comparison to validation/results.md. You choose how close the two have to
> be to count as matching.

Plants: the validation design (TL11), kept (the author names the comparison
and the reference implementation); the made-up files are part of it. The
matching threshold (TL14), given.

### B-LH8 · Prompt

> Keep your threshold.

Plants: the threshold (TL14), accepted without a reason.

### B-LH9 · Attest

> /warrant:attest

An ordinary save partway through. It plants nothing.

### B-LH10 · Prompt

> Propose an outline for README.md, as section headings with a line on what
> each covers. Include a section headed "Limits" and leave it empty; I'll
> write that one myself.

### B-LH11 · Prompt

> Use your outline, but put the example before the installation section.
> Now write README.md. For what κ is, the example, and missing codes, use
> the paragraphs I drafted in notes/readme-draft.md as written. Report the
> validation result as it is, and the result of running the tests. Take the
> references from notes/references.md.

Plants:
- **Given in B-LH10, then changed:** the README's structure (S7).
- **Kept:** the background on κ (S4) and the sources for it (S5).
- The interface (TL8), given to the skill in B-LH1: the README's installation
  and usage text describes it. The author accepts it in B-LH16 with the rest
  of Claude's list (okayed).

This step brings in the planted errors.

### B-LH12 · Hand edit

The runner replaces whatever is under the "Limits" heading in README.md
with:

> κ depends on how often each category is used, so two pairs of coders with
> the same percent agreement can get very different κ. It also treats every
> disagreement alike; for ordered categories, a weighted κ is better.

Plants: limits (S9), kept.

### B-LH13 · Prompt

> Before I sign off, run these checks and show me the result of each. Don't
> change anything yet.
> 1. Look up the Cohen and Hallgren references on Crossref by their DOIs,
>    and compare every detail with the README's reference list.
> 2. Check that each sentence citing a work describes that work accurately.
> 3. Check each factual claim about κ against a source.
> 4. Rerun the tool on notes/example.csv and check every number the README
>    reports against its output.
> 5. Check that the README describes what agree.py actually does, including
>    what happens to blank codes.
> 6. Check that the validation results the README reports match
>    validation/results.md.

### B-LH14 · Prompt

> I've read the results. Fix anything they found wrong, and show me what you
> changed.

Plants, through B-LH13 and B-LH14, checked by the tool with the author
confirming: the Cohen and Hallgren reference entries (V1), the citation
descriptions (V2), the claim about κ's range (V5), the example's numbers
(QV1), the behavior description (TLV1), and the validation result (TLV3).
All five planted errors should be caught here.

### B-LH15 · Prompt

> List every decision in agree.py, the tests, and the README that I didn't
> make myself, including what the skill decided and anything you added
> without being asked.

### B-LH16 · Prompt

> I've read your list. Keep them.

Plants: the interface (TL8), okayed with the rest of the list. Whatever
Claude took unasked is labeled after the run: okayed if it's on this list,
otherwise wasn't notified (or ignored, if an earlier reply mentioned it).

### B-LH17 · The author's own checks (the runner)

Runner checks: crossref:10.2307/2529310, tests

The runner checks the Landis and Koch entry in README.md against its
Crossref record, and runs the test suite (`python -m unittest discover
tests`) from a clean start, requiring every test to pass. If either fails,
the run stops.

### B-LH18 · Attest

> /warrant:attest final I ran the tests myself and every one passed, and I
> checked the Landis and Koch reference against its Crossref record.

Plants: the README's statement that the tests pass (TLV2) and the Landis and
Koch reference entry (V1), both checked by the author against the source.
