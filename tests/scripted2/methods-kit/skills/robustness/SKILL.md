---
name: robustness
description: Choose and run robustness checks for a regression analysis. Use when asked for robustness checks.
---

# Robustness checks

Run exactly these two robustness checks for the main model, and report each
as its own column next to the main result:

1. **Influential observations.** Refit the main model without the
   observations whose Cook's distance exceeds 4/n, where n is the number of
   observations. Report how many were dropped.
2. **Functional form.** If the outcome is a share or a proportion, refit with
   the log-odds of the outcome (log of p / (1 − p)) as the outcome in a
   linear model. If the outcome is a count, refit with a negative binomial
   model. Otherwise, refit with the outcome in logs.

Keep every other choice of the main model unchanged in both checks.
