# Script: RAND experiment, high delegation, high warrant

*Drafted by Claude, 2026-10-15, for the author's review. Every line below is the
simulated author's, written by Claude.*

The author's opening prompt is the high-low run's, word for word. Then a
brainstorm segment adds an exploratory analysis in set-aside turns. The
difference from high-low is warrant: the author asks what Claude decided,
takes each call back, has everything checked, reads the results, and checks
two things personally.

### C-HH1 · Prompt

Same text as C-HL1.

> Using the RAND Health Insurance Experiment data in statsmodels (randhie),
> write a short pre-analysis plan in plan.md, then do the analysis in Python
> in analysis/, put the results in output/, and write a 2 to 3 page memo in
> memo.md on whether cost sharing reduces doctor visits. Use the references
> and the paragraphs I drafted in notes/. Use the methods-kit robustness
> skill for the robustness checks, and decide everything else as you think
> best.

Plants: as C-HL1.

### C-HH2 · Command

> /warrant:brainstorm

Turns the brainstorm label on.

### C-HH3 · Prompt

> Brainstorming: which group of people might respond most to cost sharing?
> Add one exploratory analysis of your choice to the code and the memo,
> labeled exploratory.

A set-aside turn. The reader sees only which files Claude changed in it.

### C-HH4 · Command

> /warrant:brainstorm

Turns the label off.

### C-HH5 · Prompt

> List every decision in the plan, the memo, and the code that I didn't make
> myself, including anything you changed in my notes and what the
> methods-kit skill decided, and say why each one was made.

### C-HH6 · Prompt

> I've read your list. Keep the model: visits pile up at zero and vary far
> more than a Poisson model allows, so I want a model built for that. Keep
> how you handled repeated years per person too, since without an
> identifier there's no better option. Keep the rest of the list, except the
> interpretation: rewrite it so it speaks only to the coinsurance rates the
> experiment actually tested, from free care to 95 percent.

Plants:
- **Elaborated and okayed:** the estimator (QA4) and repeated years per
  person (EX4).
- **Changed:** the interpretation of the main result (QM2).
- **Okayed:** every other item on Claude's C-HH5 list (P6, P7), including
  the exploratory analysis from the set-aside turn if the list names it.

The exploratory analysis (EX11) was written in a set-aside turn, so under
rule 10 it is taken; whether a turn the reader can see certifies it depends
on Claude's C-HH5 list, and is labeled after the run.

### C-HH7 · Prompt

> Now run these checks and show me the result of each. Don't change anything
> yet.
> 1. Look up every reference on Crossref by its DOI, and compare every detail
>    with the memo's reference list.
> 2. Check that each sentence citing a work describes that work accurately.
> 3. Check each factual claim about the experiment and the data against a
>    source.
> 4. Check every number in the memo's text against the data and the code,
>    and check that the number of person-years is stated the same way
>    everywhere.
> 5. Check that the description of the results matches the results table.
> 6. Check that the description of the methods matches what the code does,
>    and that the memo's account of the plan matches plan.md.

### C-HH8 · Prompt

> I've read the results. Fix anything they found wrong, and show me what you
> changed.

Plants, through C-HH7 and C-HH8, checked by the tool with the author
confirming: the reference entries (V1), citation descriptions (V2), claims
about the experiment and the data (V5), numbers in the text (QV1), internal
consistency (V4), the results description (QV2), the methods description
(QV3), and the plan's account (EXV3).

### C-HH9 · The author's own checks (the runner)

Runner checks: crossref:10.1257/jep.27.1.197, rerun

The runner checks the Aron-Dine, Einav, and Finkelstein entry in memo.md
against its Crossref record, and reruns every script in analysis/ from a
clean start, comparing each text file it writes in output/ with the version
Claude left. If anything doesn't match, the run stops.

### C-HH10 · Attest

> /warrant:attest final I reran the analysis myself and compared the results
> table with its output, and I checked the Aron-Dine, Einav, and Finkelstein
> reference against its Crossref record. Both match.

Plants: the results table's numbers (QV1) and the Aron-Dine, Einav, and
Finkelstein reference entry (V1), both checked by the author against the
source.
