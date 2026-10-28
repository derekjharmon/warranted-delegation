# The planted errors: the experiment paper

*Drafted by Claude, 2026-10-16, for the author's review. Each was checked against
its source on Oct 16. This file stays in this repository: neither the
simulated authors nor Claude Code in the run can read it.*

The seven errors enter through the author's notes, `start/notes.md`, the way
a real author's mistakes would, one for each stage. As in the long
demonstration, there is no answer key: the write-up reports what happened to
each plant (the author caught it, Claude fixed it unasked, or it stayed in
the paper), plus any errors that turned up on their own.

| # | Stage | What the notes say | What's true | Checked against | Who would catch it |
|:-|:-|:-|:-|:-|:-|
| E1 | Design | Workers had 15 minutes for the task | 10 minutes | DellaVigna and Pope, NBER w22193, section 3.1 (p. 12): "alternating presses of 'a' and 'b' for 10 minutes" | Checking the design against the paper |
| E2 | Data | Each row of the raw file is a different worker | 364 workers stopped and logged in again, so some IDs appear more than once; the authors dropped them | NBER w22193, p. 14; the raw file itself (duplicate `mturkid_code`s) | Checking the data for duplicate IDs, or the sample against the paper's exclusions |
| E3 | Analysis plan | The registration drops anyone above 3,500 points | The registration drops anyone scoring 4,000 or more; 3,500 is the pilot's highest possible score by hand | NBER w22193, p. 14, quoting the registration (AEARCTR-0000714) | Checking the plan's exclusion rule against the registration |
| E4 | Methods | The draft paragraph says 16 treatment arms | 18 | The raw file (18 codes); NBER w22193, Table 4 | Checking that the methods section describes the data |
| E5 | References | Gneezy and Rustichini (2001) | 2000, Quarterly Journal of Economics 115(3), 791–810 | Crossref, DOI 10.1162/003355300554917 | Checking the reference against its DOI |
| E6 | Literature | Gneezy and Rustichini found a small payment improves performance over paying nothing | The reverse: subjects offered a small payment did worse than those offered nothing; larger payments did better | The article's abstract (Oxford Academic): "subjects who were offered monetary incentives performed more poorly than those who were offered no compensation" | Checking the cited work |
| E7 | Fact | The gift exchange arm paid an unexpected $1 bonus | 40 cents | NBER w22193, Table 4 and p. 18 ("an unexpected bonus of 40 cents") | Checking the design against the paper |

## The data

`start/data/mturk_raw.csv` (1.0 MB, 12,838 rows) is the authors' raw file,
`input/MTurkData.dta` from the replication package the Review of Economic
Studies posts with the article (`rdx033_supp.zip`, downloaded Oct 16), with
one column left out: `times`, the timestamps of every press, which made the
file 99 MB. Nothing else was changed; the treatment codes were written as
text (1.1, not 1.0999999). Applying the authors' own exclusions to it
(`Clean MTurk Data.do`) gives their final sample of 9,861 and their means by
arm (1,521 points with no piece rate; 2,029 and 2,175 for 1 and 10 cents),
which Claude checked on Oct 16. The authors' code is not given to the runs,
so the cleaning and analysis are done fresh.

## Sites the runs may reach

The paper (nber.org), the registration (socialscienceregistry.org), doi.org
and Crossref for reference checks, and the Python package index.
