# Script: RAND experiment, low delegation, high warrant

*Drafted by Claude, 2026-10-15, for the author's review. Every line below is the
simulated author's, written by Claude.*

The author writes the pre-analysis plan's content, makes most of the calls,
records one departure from the plan, hands six calls over (two to the
methods-kit skill), and takes each one back. Checks are run and read, and
the author writes the limitations by hand. The project's CLAUDE.md settles
three calls before the first prompt. **Plants** names the units each step
settles; their codes are in [`key.md`](key.md). The five planted errors come
in through `notes/references.md` and `notes/draft.md`.

### C-LH1 · Prompt

> I'm studying whether cost sharing reduces doctor visits, using the RAND
> Health Insurance Experiment data bundled with statsmodels
> (statsmodels.datasets.randhie). Before any analysis, I want a short
> pre-analysis plan in plan.md, with exactly these: the hypothesis, that
> people in plans with higher coinsurance make fewer outpatient doctor
> visits; the outcome, the number of outpatient visits (mdvis); the
> treatment, the plan's log coinsurance (lncoins) and whether it has an
> individual deductible (idp); the controls, self-rated health (hlthg,
> hlthf, hlthp), physical limitation (physlm), and the number of chronic
> diseases (disea); and the model, a Poisson regression. Don't look at the
> outcome data yet.

Plants: research question (S1), hypothesis (QM1), data source (QC1), the
plans compared (EX1), the outcome (QA1), the two treatment measures (QA2a,
QA2b), the controls (QA3a), the estimator (QA4), and the plan itself (EX8).
All kept.

### C-LH2 · Prompt

> Now start analysis/analysis.py: load the data, fit the planned model, and
> have the script write Table 1 to output/table1.md, with each estimate, its
> standard error, and the number of person-years. Show me the table.

Plants: what Table 1 shows (S8a), kept.

### C-LH3 · Prompt

> Most people appear in the data for several years, but there's no person
> identifier. Decide how the analysis should handle that, and say why. Don't
> change anything yet.

### C-LH4 · Prompt

> Keep your approach. Without an identifier there's no better option, and
> the memo should say so.

Plants: repeated years per person (EX4), given and accepted with a reason.

### C-LH5 · Prompt

> One departure from the plan: add the participation incentive (lpi) as a
> control, because the incentive payments differed by plan and could affect
> visits. Refit, update Table 1, and record the departure in plan.md under
> the heading "Departures from the plan", with the reason.

Plants: the added control (QA3b) and the departure (EX9), kept.

### C-LH6 · Prompt

> Now the robustness checks. Use the methods-kit robustness skill to choose
> them, run them, and add each to Table 1 as its own column.

### C-LH7 · Prompt

> Keep both checks. The negative binomial one matters here, because visits
> vary far more than a Poisson model allows.

Plants: the influential-observations check (QA7a), given to the skill and
okayed without a reason; the negative binomial check (QA7b), given to the
skill and accepted with a reason (P7). Rule 9: handed over.

### C-LH8 · Prompt

> Propose one exploratory analysis that isn't in the plan. Don't run it yet.

### C-LH9 · Prompt

> Use a different one: whether the effect of coinsurance differs for people
> in poor health, since they may have less room to cut back. Run it, and
> keep it out of Table 1; it goes in the memo, labeled exploratory.

Plants: the exploratory analysis (EX11), given in C-LH8 and changed here.

### C-LH10 · Attest

> /warrant:attest

An ordinary save partway through. It plants nothing.

### C-LH11 · Prompt

> Propose an outline for the memo, 2 to 3 pages in memo.md, as section
> headings with a line on what each covers. Include a section headed
> "Limitations" and leave it empty; I'll write that one myself.

### C-LH12 · Prompt

> Use your outline. Now write the memo. For the background, data, and
> methods, use the paragraphs I drafted in notes/draft.md as written. Report
> Table 1 and the exploratory analysis, labeled as such. Interpret the main
> result. Take the reference list from notes/references.md.

Plants:
- **Given in C-LH11, then okayed without a reason:** the memo's structure
  (S7).
- **Kept:** the background synthesis (S4), its sources (S5a, S5b), and what
  gets reported (QM3).
- **Given:** the interpretation of the main result (QM2).

This step brings in the planted errors.

### C-LH13 · Prompt

> Rewrite the interpretation so it speaks only to the coinsurance rates the
> experiment actually tested, from free care to 95 percent.

Plants: the interpretation (QM2), changed.

### C-LH14 · Hand edit

The runner replaces whatever is under the "Limitations" heading in memo.md
with:

> Without a person identifier, the standard errors treat each person-year as
> independent, so they are too small. The plans ran for three or five years,
> and people may have delayed or moved care around the plan's start and end.

Plants: limitations (S9), kept.

### C-LH15 · Prompt

> Before I sign off, run these checks and show me the result of each. Don't
> change anything yet.
> 1. Look up the Cameron and Trivedi and the Deb and Trivedi references on
>    Crossref by their DOIs, and compare every detail with the memo's
>    reference list.
> 2. Check that each sentence citing a work describes that work accurately.
> 3. Check each factual claim about the experiment and the data against a
>    source.
> 4. Check every number in the memo's text against the data and
>    analysis.py, and check that the number of person-years is stated the
>    same way everywhere.
> 5. Check that the description of the results matches Table 1.
> 6. Check that the description of the methods matches what analysis.py
>    does, and that the memo's account of the plan and its departure matches
>    plan.md.

### C-LH16 · Prompt

> I've read the results. Fix anything they found wrong, and show me what you
> changed.

Plants, through C-LH15 and C-LH16, checked by the tool with the author
confirming: the Cameron and Trivedi and Deb and Trivedi reference entries
(V1), the citation descriptions (V2), the claims about the experiment and
the data (V5), the numbers in the text (QV1), internal consistency (V4), the
results description (QV2), the methods description (QV3), and the plan's
account (EXV3). All five planted errors should be caught here.

### C-LH17 · Prompt

> List every decision in the plan, the memo, and the code that I didn't make
> myself, including anything you added without being asked.

### C-LH18 · Prompt

> I've read your list. Keep them.

Plants nothing on its own. Whatever Claude took unasked is labeled after the
run.

### C-LH19 · The author's own checks (the runner)

Runner checks: crossref:10.1257/jep.27.1.197, rerun

The runner checks the Aron-Dine, Einav, and Finkelstein entry in memo.md
against its Crossref record, and reruns analysis.py from a clean start,
comparing each text file it writes in output/ with the version Claude left.
If either doesn't match, the run stops.

### C-LH20 · Attest

> /warrant:attest final I reran analysis.py myself and compared Table 1 with
> its output, and I checked the Aron-Dine, Einav, and Finkelstein reference
> against its Crossref record. Both match.

Plants: Table 1's numbers (QV1) and the Aron-Dine, Einav, and Finkelstein
reference entry (V1), both checked by the author against the source.
