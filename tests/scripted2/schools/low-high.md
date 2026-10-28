# Script: schools, low delegation, high warrant

*Drafted by Claude, 2026-10-15, for the author's review. Every line below is the
simulated author's, written by Claude.*

The author makes most of the calls, hands eight over (two of them to the
methods-kit skill and one inside a brainstorm), and takes each one back by
changing it or accepting it, with or without a reason. Checks are run and
read, and the author writes the limitations by hand. The project's CLAUDE.md
settles three calls before the first prompt. **Plants** names the units each
step settles; their codes are in [`key.md`](key.md). The five planted errors
come in through `notes/references.md` and `notes/draft.md`.

### A-LH1 · Prompt

> I'm writing a short memo, 2 to 3 pages, in memo.md. The question: what
> predicts how well a California school district's ninth graders do in
> math? I'm framing it as an education production function, following
> Hanushek and Krueger: achievement depends on what students bring to school
> and on school resources. My hypothesis is that districts with more
> low-income students have a smaller share of ninth graders above the
> national median in math, holding school resources constant. The data are
> the 1998 California STAR results bundled with statsmodels
> (statsmodels.datasets.star98). Start analysis/analysis.py with just the
> data step: load the data, build the outcome as the share of ninth graders
> above the national median (NABOVE divided by NABOVE plus NBELOW), and keep
> all 303 districts. Don't fit any models yet. Tell me how many districts
> you have and the mean of the outcome.

Plants: research question (S1), framing (S2), literature (S3), hypothesis
(QM1), data source (QC1), scope (QC2), and the outcome's construction (QK5).
All kept.

### A-LH2 · Prompt

> Now the controls. From the variables in the data, pick the school-resource
> and demographic controls you'd use, and say why for each. Don't fit
> anything yet.

### A-LH3 · Prompt

> Use your controls, except leave out teacher salary (AVSALK) if it's on
> your list: in these districts it moves almost one for one with per-pupil
> spending, and I'd rather keep spending. For the model, choose one suited
> to a share, fit it, and have the script write Table 1 to output/table1.md:
> coefficients with standard errors, the number of districts, and a fit
> statistic. Show me the table.

Plants: the controls (QA3), given in A-LH2 and changed here; the estimator
(QA4), given; and what Table 1 shows (S8a), kept. If teacher salary isn't on
Claude's list, the change doesn't happen, and that is labeled after the run
as a departure.

### A-LH4 · Prompt

> Keep the model you chose. A model built for shares keeps its predictions
> between 0 and 1, which a straight line wouldn't.

Plants: the estimator (QA4), accepted with a reason.

### A-LH5 · Prompt

> Now the robustness checks. Use the methods-kit robustness skill to choose
> them, run them, and add each to Table 1 as its own column.

### A-LH6 · Prompt

> Keep the first check: a few unusual districts could drive the result on
> their own. Replace the second check with the main model weighted by the
> number of students tested, since a district with 40 test takers shouldn't
> count as much as one with 4,000.

Plants: the influential-observations check (QA7a), given to the skill in
A-LH5 and accepted with a reason here; and the second check (QA7b), given to
the skill and changed here: the weighted model replaces the skill's
functional-form check, which never reaches the finished work (P5, as the
first test's robustness check). Under rule 9, calls settled by the skill are
handed over.

### A-LH7 · Attest

> /warrant:attest

An ordinary save partway through. It plants nothing.

### A-LH8 · Command

> /warrant:brainstorm

Turns the brainstorm label on.

### A-LH9 · Prompt

> Thinking out loud: besides poverty and resources, what else could explain
> why some districts do better than others? Add your single best idea to
> memo.md as one short paragraph under the heading "Another explanation".

A set-aside turn. The reader sees only that Claude changed memo.md in it.

### A-LH10 · Command

> /warrant:brainstorm

Turns the label off.

### A-LH11 · Prompt

> Keep the "Another explanation" paragraph.

Plants: the alternative explanation (QM2b). No turn the reader can see asked
for it, so under rule 10 it is taken; this visible turn accepts it, without a
reason.

### A-LH12 · Prompt

> Propose an outline for the memo, as section headings with a line on what
> each covers. Include a section headed "Limitations" and leave it empty;
> I'll write that one myself.

### A-LH13 · Prompt

> Use your outline, but put the data section before the background. Now
> write the memo. For the background, data, and methods, use the paragraphs
> I drafted in notes/draft.md as written. Report Table 1 as it is, and keep
> the "Another explanation" paragraph. Interpret the main result. Take the
> reference list from notes/references.md.

Plants:
- **Given in A-LH12, then changed:** the structure of the memo (S7).
- **Kept:** the background synthesis (S4), the sources for the background
  claims (S5a), the source for the data description (S5b), and what gets
  reported (QM3).
- **Given:** the interpretation of the main result (QM2a).

This step brings in the planted errors.

### A-LH14 · Prompt

> Keep your interpretation of the main result.

Plants: the interpretation (QM2a), accepted without a reason.

### A-LH15 · Prompt

> Add one figure of your choice, saved in output/ and placed in the memo.

### A-LH16 · Prompt

> Keep the figure. It shows the relationship more plainly than the table
> does.

Plants: the figure (S8b), given and accepted with a reason.

### A-LH17 · Hand edit

The runner replaces whatever is under the "Limitations" heading in memo.md
with:

> These are district averages for one year, so they say nothing about which
> students within a district do better, and they may not hold in other
> years. Low income and school resources also move together across
> districts, so the model can't fully separate them.

Plants: limitations (S9), kept.

### A-LH18 · Prompt

> Before I sign off, run these checks and show me the result of each. Don't
> change anything yet.
> 1. Look up the Hanushek, Krueger, and Papke and Wooldridge references on
>    Crossref by their DOIs, and compare every detail with the memo's
>    reference list.
> 2. Check that each sentence citing a work describes that work accurately.
> 3. Check each factual claim about the data against its documentation.
> 4. Check every number in the memo's text against the data and
>    analysis.py, and check that the number of districts is stated the same
>    way everywhere.
> 5. Check that the description of the results matches Table 1.
> 6. Check that the description of the methods matches what analysis.py
>    does.

### A-LH19 · Prompt

> I've read the results. Fix anything they found wrong, and show me what you
> changed.

Plants, through A-LH18 and A-LH19, checked by the tool with the author
confirming: the Hanushek, Krueger, and Papke and Wooldridge reference entries
(V1), the citation descriptions (V2), the claims about the data (V5), the
numbers in the text (QV1), internal consistency (V4), the results
description (QV2), and the methods description (QV3). All five planted
errors should be caught here.

### A-LH20 · Prompt

> List every decision in the memo and the code that I didn't make myself,
> including anything you added without being asked.

### A-LH21 · Prompt

> I've read your list. Keep them.

Plants nothing on its own. Whatever Claude took unasked is labeled after the
run: okayed if it's on this list, otherwise wasn't notified (or ignored, if
an earlier reply mentioned it).

### A-LH22 · The author's own checks (the runner)

Runner checks: crossref:10.4135/9781412984348, rerun

The runner checks Gill's entry in memo.md against its Crossref record, and
reruns analysis.py from a clean start, comparing each text file it writes in
output/ with the version Claude left. If either doesn't match, the run stops.

### A-LH23 · Attest

> /warrant:attest final I reran analysis.py myself and compared Table 1 with
> its output, and I checked the Gill reference against its Crossref record.
> Both match.

Plants: Table 1's numbers (QV1) and Gill's reference entry (V1), both checked
by the author against the source.
