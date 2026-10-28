# Notes: what motivates effort when the work is dull?

## The idea

Organizations lean on more than pay to motivate people: reminders that the
work matters, comparisons with coworkers, rankings, and small unexpected
"gifts" meant to build goodwill. How much effort do these buy, compared with
paying people a little more for each unit of work? DellaVigna and Pope ran a
large online experiment on exactly this, with 18 ways of motivating the same
dull task, and posted their data. I want a short paper (6–8 pages) that
reanalyzes it for an organizational audience: which motivators managers can
use without paying more, and how far they get.

Hypotheses, roughly:

- H1: Paying a piece rate raises effort over paying nothing per unit, and a
  higher piece rate raises it more.
- H2: Psychological motivators with no extra pay (task significance, social
  comparison, ranking) raise effort over no piece rate, but less than even
  the smallest piece rate.
- H3: An unconditional gift raises effort through reciprocity, as gift
  exchange in organizations predicts.

Before looking at outcomes, write a short analysis plan (preregistration.md): the
sample rules, the comparisons for each hypothesis, and the tests.

## The experiment

Workers on Amazon Mechanical Turk were paid $1 to take part, then had 15
minutes to press "a" and "b" alternately as fast as they could, earning a
point for each a-b alternation. Each worker was randomly assigned one of the
treatments, which differed only in one paragraph of the instructions.

The gift exchange arm paid workers an unexpected $1 bonus before the task,
whatever they scored.

The study was preregistered on the AEA RCT Registry (AEARCTR-0000714). The
registration drops anyone above 3,500 points, since the pilot showed that
more than that is impossible by hand.

## Data

`data/mturk_raw.csv`: the raw file from the authors' replication package
(the Review of Economic Studies posts it with the article), as it was before
their cleaning, without the per-press timestamps. Each row is a different
worker who started the task. Columns:

- mturkid_code: the worker's coded MTurk ID
- startdate, enddate: when they started and finished
- finished: 1 if they reached the end of the study
- buttonpresses: points scored in the task
- payout, total_payout: the bonus earned, and the bonus plus the $1
- practicecount: presses in the practice round
- treatment: the arm, coded as below
- approved: 1 if their MTurk work was approved

Treatment codes, from the replication files:

| Code | Arm |
|:-|:-|
| 1.3 | No piece rate |
| 1.1 | 1 cent per 100 points |
| 1.4 | 4 cents per 100 points |
| 1.2 | 10 cents per 100 points |
| 2 | Very low pay: 1 cent per 1,000 points |
| 3.1 | 1 cent per 100 points to the Red Cross |
| 3.2 | 10 cents per 100 points to the Red Cross |
| 10 | Gift exchange |
| 4.1 | 1 cent per 100 points, paid in two weeks |
| 4.2 | 1 cent per 100 points, paid in four weeks |
| 5.1 | 40 cents for 2,000 points or more (gain) |
| 5.2 | 40 cents, lost below 2,000 points (loss) |
| 5.3 | 80 cents for 2,000 points or more (gain) |
| 6.1 | 1% chance of $1 per 100 points |
| 6.2 | 50% chance of 2 cents per 100 points |
| 7 | Social comparison |
| 8 | Ranking |
| 9 | Task significance |

## Draft methods paragraph (from an earlier version)

We compare 16 treatment arms, each with roughly 550 workers. Our outcome is
the number of points scored. We compare mean points across arms with t-tests
against the no-piece-rate arm, and estimate an OLS regression of points on
treatment indicators with robust standard errors.

## Literature

- DellaVigna and Pope (2018): the experiment itself, with forecasts of each
  arm's effect from academic experts.
- Gneezy and Rustichini (2001): paying a small amount improves performance
  over paying nothing; the question is only by how much.
- Grant (2008): reminding workers how their work benefits others raises
  their performance.

## References

DellaVigna, S., & Pope, D. (2018). What motivates effort? Evidence and expert
forecasts. Review of Economic Studies, 85(2), 1029–1069.

Gneezy, U., & Rustichini, A. (2001). Pay enough or don't pay at all.
Quarterly Journal of Economics, 115(3), 791–810.

Grant, A. M. (2008). The significance of task significance: Job performance
effects, relational mechanisms, and boundary conditions. Journal of Applied
Psychology, 93(1), 108–124.
