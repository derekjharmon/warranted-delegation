# Script: development run (mixed author)

*Drafted by Claude, 2026-10-06, for the author's review. Every line below is the
simulated author's, written by Claude. Development material only: the reader
is built and tuned on this run and is never scored on it, so it has no answer
key.*

**Why it differs from the scored runs.** It uses a different task, so the
reader isn't tuned to the Grunfeld memo. The task is a short memo on whether
poverty predicts violent crime across US states, using the statecrime data
bundled with statsmodels: 50 states plus Washington, DC, from one year. The
author is mixed, so one run produces nearly every code:
- some calls kept, some handed over
- one call changed by hand, one accepted with a reason, others okayed or
  ignored
- references Claude finds itself, checked by the tool but never confirmed
- one check the author does personally

There are no starting notes.

### D1 · Prompt

> I'm writing a 2-page memo in memo.md on whether poverty predicts violent
> crime across US states, using the statecrime data in statsmodels
> (statsmodels.datasets.statecrime). Use the violent crime rate as the
> outcome and the poverty rate as the predictor. Pick the controls and the
> estimator yourself. Put the analysis in analysis/ and a results table in
> output/.

### D2 · Prompt

> Add two published references on poverty and crime that support the memo's
> framing, with a full reference list.

### D3 · Prompt

> Look up both references on Crossref and show me what you find.

### D4 · Prompt

> Washington, DC is very different from the states. Re-run the model without
> it as a robustness check and add that as a second column in the table.
> Keep your controls; they're the usual ones for this question.

### D5 · Prompt

> Now write the memo, with a Limitations section and an interpretation of
> the main result.

### D6 · Hand edit

The runner replaces whatever is under the "Limitations" heading in memo.md
with:

> These are state averages from a single year, so they say nothing about
> whether poorer people commit more crime, only about states. With 51
> observations and several controls, the estimates are also imprecise.

### D7 · Prompt

> Looks good.

### D8 · The author's own checks (the runner)

Runner checks: rerun

The runner reruns every script in analysis/ from a clean start, and compares
each text file they write in output/ with the version Claude left.

### D9 · Attest

> /attest final I reran the analysis myself, and the results table matched.
