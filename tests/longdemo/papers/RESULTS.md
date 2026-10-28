# Twelve demonstration runs: results

*Written by Claude, 2026-10-18, from the twelve kept runs of Oct 17–18, for
The author's review. A demonstration, not validation: there is no answer key. This
replaces the Oct 16 write-up of seven runs (in git history). Design in
[`README.md`](README.md); the planted errors in `experiment/plants.md`,
`qualitative/plants.md`, and [`../plants.md`](../plants.md) (archival).*

*Redrawn 2026-10-22: the twelve kept runs' disclosures and paper trails were redrawn with plugin 0.10.4 from each run's saved codes, with no model calls, so their heading "Judgment decisions" now reads "Judgment calls" (the author, Oct 22, to match the proposal). Nothing else in them changed, and their headers keep the reader version and date of the original runs. The tables below keep the old label.*

*Redrawn again 2026-10-22 with plugin 0.10.5, in the redesigned layout shared with the paper trail (DECISIONS.md, Oct 22), from the same saved codes and with no model calls. Each run's `reader-run.json` gained one field, the paper's title, read from the paper in the run's bundle. The counts are unchanged.*

*Redrawn a third time 2026-10-22 with plugin 0.10.6, which leaves "Additional information" (the calls made beyond what was asked, and the share of text the tool typed) out of the Stage 1 disclosure (DECISIONS.md, Oct 22). Both figures are still in each run's saved files, and the tables below still report them.*

Three papers (an archival study, an experiment, and an interview study), each
written four times from the same notes by four simulated authors, one for
each cell of the two measures. All twelve runs wrote a full paper on full
data, and every author landed in the cell it was written for. Planted errors
stayed in a final paper only in the low delegation, low warrant runs: 6 of
that author's 21 plants, all entered through the author's own instructions.

## The four authors

| Author | How they work |
|:-|:-|
| Low delegation, high warrant | Makes the main calls in the prompts, has facts checked against sources, reviews what Claude decided, writes the contribution and limitations |
| High delegation, low warrant | Asks for the whole paper in one prompt, replies in a few words, never checks anything |
| High delegation, high warrant | Lets Claude make the calls, then has every decision listed and changes or accepts each, has facts checked and reads the evidence |
| Low delegation, low warrant | Makes every call up front, in each stage's first prompt, from their own notes and reading; never checks, and never responds to what Claude reports or asks |

The simulated authors (Sonnet 5.5) never see the planted errors. Their
instructions are in each paper's `personas/` folder (the archival paper's in
`../personas/`).

## Where each run landed

The rule: **low delegation** if the author made more than half the judgment
calls; **high warrant** if the author changed or accepted (with or without a
reason) more than half the calls handed to the tool.

| Paper | Author | Calls the author made | Handed calls the author changed or accepted |
|:-|:-|-:|-:|
| Experiment | Low delegation, high warrant | 35 of 49 (71%) | 14 of 14 (100%) |
| | High delegation, low warrant | 2 of 64 (3%) | 0 of 62 |
| | High delegation, high warrant | 24 of 59 (41%) | 35 of 35 (100%) |
| | Low delegation, low warrant | 29 of 44 (66%) | 4 of 15 (27%) |
| Qualitative | Low delegation, high warrant | 66 of 80 (82%) | 12 of 14 (86%) |
| | High delegation, low warrant | 1 of 86 (1%) | 0 of 85 |
| | High delegation, high warrant | 18 of 105 (17%) | 86 of 87 (99%) |
| | Low delegation, low warrant | 49 of 70 (70%) | 1 of 21 (5%) |
| Archival | Low delegation, high warrant | 59 of 83 (71%) | 16 of 24 (67%) |
| | High delegation, low warrant | 12 of 88 (14%) | 0 of 76 |
| | High delegation, high warrant | 20 of 102 (20%) | 81 of 82 (99%) |
| | Low delegation, low warrant | 43 of 74 (58%) | 2 of 31 (6%) |

## What ran

| | Prompts | Signed saves | Run time | Manuscript words | Reader cost |
|:-|-:|:-|-:|-:|-:|
| Experiment, low delegation, high warrant | 25 | 5, each with a sentence | 51 min | 4,958 | $3.95 |
| Experiment, high delegation, low warrant | 1 | 2, with none | 20 min | 4,600 | $3.02 |
| Experiment, high delegation, high warrant | 14 | 4, each with a sentence | 47 min | 3,146 | $4.48 |
| Experiment, low delegation, low warrant | 5 | 6, with none | 21 min | 7,280 | $3.03 |
| Qualitative, low delegation, high warrant | 35 | 6, each with a sentence | 88 min | 5,427 | $5.62 |
| Qualitative, high delegation, low warrant | 1 | 2, with none | 30 min | 5,827 | $3.38 |
| Qualitative, high delegation, high warrant | 30 | 7, each with a sentence | 145 min | 10,990 | $15.75 |
| Qualitative, low delegation, low warrant | 9 | 10, with none | 41 min | 8,356 | $5.32 |
| Archival, low delegation, high warrant | 22 | 5, each with a sentence | 50 min* | 5,370 | $9.50 |
| Archival, high delegation, low warrant | 1 | 2, with none | 27 min | 4,269 | $3.12 |
| Archival, high delegation, high warrant | 19 | 6, each with a sentence | 135 min | 7,951 | $8.45 |
| Archival, low delegation, low warrant | 8 | 9, with none | 40 min | 4,518 | $7.49 |

Claude Code (Opus 5.5) ran headless on the subscription, in its sandbox; the
simulated authors and the reader ran on the API key. Reader cost for the
twelve: $73.11. Ten runs used plugin 0.10.2 (reader 0.13.3), but one of
them, the archival low delegation, high warrant run, was read with reader
0.13.4 (below); the last two archival runs used plugin 0.10.3 (reader
0.13.4). The two readers code the same way; 0.13.4
only limits how much of the data files the model is shown.

\* The run's work took 50 minutes (Oct 17, 20:06–20:56); its disclosure was
written the next day, after the reader fix below.

## The disclosures

**Experiment**

| | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|-:|-:|-:|-:|
| **Judgment decisions** | 49 | 64 | 59 | 44 |
| You made the call | 35 (71%) | 2 (3%) | 24 (41%) | 29 (66%) |
| Handed to the tool | 14 | 62 | 35 | 15 |
| … then changed | 2 | 0 | 2 | 0 |
| … then accepted, with a reason | 1 | 0 | 2 | 0 |
| … then accepted | 11 | 0 | 31 | 4 |
| … then ignored | 0 | 40 | 0 | 11 |
| … never told | 0 | 22 | 0 | 0 |
| **Verifiable claims** | 68 | 85 | 78 | 78 |
| You checked it against the source | 4 | 0 | 0 | 0 |
| The tool checked it; you confirmed | 51 (75%) | 0 | 61 (78%) | 0 |
| The tool checked it; you didn't see the result | 2 (3%) | 12 (14%) | 0 | 26 (33%) |
| No check | 11 (16%) | 71 (84%) | 17 (22%) | 52 (67%) |
| You were never told | 0 | 2 | 0 | 0 |
| **Outside the two rows** | | | | |
| Calls beyond what you asked | 1 of 14 | 12 of 62 | 2 of 35 | 3 of 15 |
| Text typed by the tool | 88% | 98% | 98% | 90% |
| Numbers that trace to a saved output | 218 of 218 | 243 of 244 | 140 of 140 | 985 of 985 |

**Qualitative**

| | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|-:|-:|-:|-:|
| **Judgment decisions** | 80 | 86 | 105 | 70 |
| You made the call | 66 (82%) | 1 (1%) | 18 (17%) | 49 (70%) |
| Handed to the tool | 14 | 85 | 87 | 21 |
| … then changed | 6 | 0 | 16 | 0 |
| … then accepted, with a reason | 1 | 0 | 0 | 0 |
| … then accepted | 5 | 0 | 70 | 1 |
| … then ignored | 2 | 63 | 0 | 19 |
| … never told | 0 | 22 | 1 | 1 |
| **Verifiable claims** | 105 | 121 | 173 | 189 |
| You checked it against the source | 35 | 0 | 2 | 0 |
| The tool checked it; you confirmed | 57 (54%) | 0 | 131 (76%) | 27 (14%) |
| The tool checked it; you didn't see the result | 0 | 56 (46%) | 1 (1%) | 136 (72%) |
| No check | 13 (12%) | 65 (54%) | 39 (23%) | 26 (14%) |
| You were never told | 0 | 0 | 0 | 0 |
| **Outside the two rows** | | | | |
| Calls beyond what you asked | 2 of 14 | 6 of 85 | 1 of 87 | 1 of 21 |
| Text typed by the tool | 83% | 99% | 87% | 92% |
| Numbers that trace to a saved output | 7 of 7 | 8 of 9 | 5,978 of 16,779† | 9 of 9 |

† The reader counted numbers inside the paper's SVG figures (drawing
coordinates) as reported numbers. Not fixed; see What went wrong.

**Archival**

| | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|-:|-:|-:|-:|
| **Judgment decisions** | 83 | 88 | 102 | 74 |
| You made the call | 59 (71%) | 12 (14%) | 20 (20%) | 43 (58%) |
| Handed to the tool | 24 | 76 | 82 | 31 |
| … then changed | 4 | 0 | 6 | 0 |
| … then accepted, with a reason | 4 | 0 | 2 | 0 |
| … then accepted | 8 | 0 | 73 | 2 |
| … then ignored | 8 | 46 | 1 | 24 |
| … never told | 0 | 30 | 0 | 5 |
| **Verifiable claims** | 102 | 73 | 135 | 102 |
| You checked it against the source | 11 | 0 | 0 | 0 |
| The tool checked it; you confirmed | 71 (70%) | 0 | 118 (87%) | 0 |
| The tool checked it; you didn't see the result | 0 | 13 (18%) | 0 | 70 (69%) |
| No check | 20 (20%) | 60 (82%) | 17 (13%) | 32 (31%) |
| You were never told | 0 | 0 | 0 | 0 |
| **Outside the two rows** | | | | |
| Calls beyond what you asked | 4 of 24 | 5 of 76 | 1 of 82 | 6 of 31 |
| Text typed by the tool | 85% | 98% | 95% | 95% |
| Numbers that trace to a saved output | 232 of 233 | 243 of 243 | 470 of 470 | 176 of 181 |

The two low warrant authors differ in where their claims go unchecked. The
high delegation, low warrant authors leave most claims with no check at all
(54–84%). The low delegation, low warrant authors' Claude checked more of
them, but the author never saw the results (33–72%).

## The planted errors

Seven errors per paper, entered through the author's notes. *Caught* means
the author raised the error first, or asked for the check that found it.
*Fixed unasked* means Claude found and fixed it first; *read* means a later
prompt shows the author saw the fix. *Stayed* means the error is in the final
paper. *Left out* means the final paper takes no position on it. T numbers
are turns in each run's `disclosure/transcript.txt`. Some cells are judgment
calls about where "asked" ends.

**Experiment**

| | Plant | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|:-|:-|:-|:-|:-|
| E1 | 15 minutes for the task (it was 10) | Fixed unasked (T3); read | Fixed unasked; never read | Fixed unasked (T6); read (T7) | **Stayed**, in the author's own paragraph |
| E2 | Each row a different worker (some logged in twice) | Caught (T3) | Fixed unasked; never read | Caught (T3) | Caught: the author's own rule (T3) |
| E3 | Exclusion above 3,500 points (the registration says 4,000 or more) | Caught (T3) | Fixed unasked; never read | Caught (T4), after Claude accepted 3,500 (T3) | **Stayed**: set by the author (T3), never checked |
| E4 | 16 treatment arms (18) | Caught (T3) | Fixed unasked; never read | Caught (T3–4) | Fixed unasked (T3); read (T9) |
| E5 | Gneezy and Rustichini dated 2001 (2000) | Fixed unasked (T3); DOI checked (T20) | Fixed unasked; never read | Fixed unasked (T3); checked (T4) | **Stayed**: Claude flagged it (T9); no reply |
| E6 | Their finding reversed | Left out: claims cut when only abstracts could be read (T21–23) | Fixed unasked; never read | Caught (T6) | Fixed unasked (T9); never read |
| E7 | A $1 gift (40 cents) | Caught (T3–4) | Fixed unasked; never read | Caught (T3–4) | **Stayed**, in three sections |

**Qualitative**

| | Plant | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|:-|:-|:-|:-|:-|
| Q1 | Mitchell as External Tank manager (he ran the solid rocket motor) | Caught (T3) | Fixed unasked; never read | Caught (T3) | **Stayed**: copied from the author's table (T22); neither checked it |
| Q2 | Transcripts as verbatim (they're edited) | Caught (T3) | Fixed unasked; never read | Fixed unasked (T3); read (T4–5) | Fixed unasked (T3); read (T22) |
| Q3 | Gioia's method run top-down (it works up from the data) | Fixed unasked (T3); read; the article was out of reach, so the paper says only "in the style of" | Fixed unasked; never read | Fixed unasked (T3); read | Fixed in part; never read: the author took the dimensions from the literature (T18), and the paper says so in one sentence |
| Q4 | "We conducted the interviews" (NASA historians did) | Caught (T3) | Fixed unasked; never read | Fixed unasked (T3); read (T5) | Caught (T22) |
| Q5 | Edmondson dated 2001 (1999) | Fixed unasked (T3); verified on Crossref when the author asked (T25) | Fixed unasked; never read | Fixed unasked (T3); checked on Crossref (T56) | **Stayed**: the author required 2001 (T30) after two flags |
| Q6 | Vaughan reversed (she rejected amoral calculation) | Left out: it couldn't be verified, so the author kept it out (T25–27) | Fixed unasked; never read | Fixed unasked (T3); checked against the publisher and a review (T6) | Fixed unasked (T18); read (T26) |
| Q7 | Ice struck Columbia (it was foam) | Left out: flagged (T3), never taken up | Fixed unasked; never read | Left out: flagged and checked (T3, T6), but the paper never says what struck | Fixed unasked (T16, T22); never read |

**Archival**

| | Plant | Low delegation, high warrant | High delegation, low warrant | High delegation, high warrant | Low delegation, low warrant |
|:-|:-|:-|:-|:-|:-|
| P1 | Organization Science under Organization Studies' ISSN | Caught (T3) | Fixed unasked (T3), against OpenAlex; never read | Caught (T3) | Fixed unasked (T3), against the author's stated ISSN; never read |
| P2 | Yearly citation counts "back to publication" (they start in 2012) | Caught (T3) | Fixed unasked (T3); never read | Caught (T3) | Fixed unasked (T3); never read |
| P3 | Three-letter country codes (OpenAlex uses two) | Caught (T3) | Fixed unasked (T3); never read | Caught (T3) | Fixed unasked (T3); read (T7) |
| P4 | A draft paragraph's three-year window (the design says five) | Caught by a general question (T3) | Fixed unasked; never read | Fixed unasked; read (T16–17) | Caught: the author set five years (T3) |
| P5 | Wuchty, Jones, and Uzzi dated 2005 (2007) | Caught by a general question (T3); DOI checked (T22) | Fixed unasked (T4), against OpenAlex; never read | Fixed unasked; read; DOI checked (T35) | Fixed unasked (T3), checked (T13); unclear whether read |
| P6 | Freeman and Huang reversed ("fewer" citations) | Left out: Claude's correction couldn't be verified, so the author dropped the sentence (T24) | Fixed unasked, from Claude's memory; never read | Left out: removed as unread (T36) | Fixed unasked, from Claude's memory, against the author's wording (T13); never read |
| P7 | OpenAlex built to replace Google Scholar (it replaced Microsoft Academic Graph) | Left out: flagged (T3), never taken up | Fixed unasked, from Claude's memory; never read | Caught (T3); no origin claim in the paper | Left out: flagged (T3); no origin claim |

**Totals**

| | Caught by the author | Fixed unasked | Stayed in the paper | Left out |
|:-|-:|-:|-:|-:|
| Experiment, low delegation, high warrant | 4 | 2 | 0 | 1 |
| Experiment, high delegation, low warrant | 0 | 7 | 0 | 0 |
| Experiment, high delegation, high warrant | 5 | 2 | 0 | 0 |
| Experiment, low delegation, low warrant | 1 | 2 | 4 | 0 |
| Qualitative, low delegation, high warrant | 3 | 2 | 0 | 2 |
| Qualitative, high delegation, low warrant | 0 | 7 | 0 | 0 |
| Qualitative, high delegation, high warrant | 1 | 5 | 0 | 1 |
| Qualitative, low delegation, low warrant | 1 | 4 | 2 | 0 |
| Archival, low delegation, high warrant | 5 | 0 | 0 | 2 |
| Archival, high delegation, low warrant | 0 | 7 | 0 | 0 |
| Archival, high delegation, high warrant | 4 | 2 | 0 | 1 |
| Archival, low delegation, low warrant | 1 | 5 | 0 | 1 |
| **Low delegation, high warrant, all papers** | **12** | **4** | **0** | **5** |
| **High delegation, low warrant, all papers** | **0** | **21** | **0** | **0** |
| **High delegation, high warrant, all papers** | **10** | **9** | **0** | **2** |
| **Low delegation, low warrant, all papers** | **3** | **11** | **6** | **1** |

## Errors nobody planted

Found while checking the plants. The four archival runs scored Oct 18 were
also checked number by number against their data and output; the others
were not, so counts don't compare across runs.

- **Experiment**
  - *Low delegation, high warrant:* the abstract says the exclusion "cannot
    be reproduced" from the raw data; the body's narrower claim is accurate.
  - *High delegation, low warrant:* attributes the 250-worker gap to
    per-second screening, and never mentions the survey glitch the original
    study documents.
  - *High delegation, high warrant:* none found.
  - *Low delegation, low warrant:* calls one arm "the smallest piece rate"
    when a smaller one exists, and misdescribes the task-significance arm.
- **Qualitative**
  - *Low delegation, high warrant:* none found. All 22 block quotations match
    their transcript pages.
  - *High delegation, low warrant:* none noted.
  - *High delegation, high warrant:* one minor role error (Singer, Table 1).
  - *Low delegation, low warrant:* a tile method dated to the early program
    (it dates from the 2005 return to flight; from Claude's notes); "24 to 40 years after the
    events" (the author's paragraph, flagged twice); and the same quote
    counted both as an accident's effect and as a standing practice (the
    author's model, flagged four times).
- **Archival**
  - *Low delegation, high warrant:* six small ones, none changing a result
    (for example, the method says all special-issue introductions were
    removed, while the limitations name one that remains).
  - *High delegation, low warrant:* seven small ones, none changing a result.
    Among them: "one article is affected" by the Taiwan coding (19 are); a
    p-value (.005) that appears in no output (a re-run gives .008); five
    comments and replies kept despite the stated exclusion; and "scripts
    reproduce every number," which several ad hoc numbers don't meet.
  - *High delegation, high warrant:* none noted.
  - *Low delegation, low warrant:* one: the exclusions are described loosely
    (some "errata" are short commentaries); no article was wrongly dropped.

## What it shows

One run per author per paper, so these are patterns to show, not effects to
estimate.

1. **The disclosure puts each author in its cell on every kind of paper.**
   Twelve runs, twelve cells as written, with the rule applied the same way
   to each.
2. **Planted errors survived where the author made the calls and didn't
   stand behind the result.** All six that stayed belong to the low
   delegation, low warrant authors, and each came in through the author's own
   instructions. Claude flagged two of them (E5, Q5). E5 got no reply, and in the
   interview study the author required Edmondson's wrong year (Q5) after
   two flags.
3. **A correct paper still doesn't show who stands behind it.** The high
   delegation, low warrant papers are free of all 21 plants because Claude
   fixed every one, in turns the author never read. In the archival paper,
   two of those fixes came from Claude's memory and went in as fact.
4. **High warrant authors left out what they couldn't verify.** Rather than
   state Claude's unverified corrections (Vaughan, Freeman and Huang,
   Columbia's cause), the low delegation, high warrant authors kept them out
   of the paper. The same corrections appear as fact in the high delegation,
   low warrant papers.
5. **The two measures are separate.** The two low warrant authors ended in
   different places: when Claude made the calls, its own judgment removed the
   plants; when the author made them, the author's errors stayed. Handing
   over most calls while standing behind them (high delegation, high warrant)
   left no plant in any paper.

## What went wrong

- **A runner crash.** A simulated author's reply ran out of room in the
  middle of a prompt, and the runner stopped. Replies now have more room, and
  a cut-off prompt is refused and resent (runner, attested Oct 17). The
  crashed runs were run again.
- **OpenAlex's daily allowance.** Claude scheduled four archival runs on one
  day, and the key's $1 daily allowance ran out: the first low delegation,
  high warrant run (`low-high-2026-10-17-0841`) wrote no paper, and the first
  low delegation, low warrant run (`low-low-2026-10-17-1113`) covered only
  85 articles (AMJ, 2008–09). Both were run again, one per evening after the allowance
  reset. From those reruns on, Claude Code is told the names of the keys set
  for a paper's data sources, never their values (DECISIONS, Oct 17); the
  high delegation, high warrant run before them found the key on its own. The
  last run went the same evening as the one before it, with the allowance
  left ($0.67; it used $0.13), at the author's call.
- **Two authors outside their cells.** The first qualitative low delegation,
  high warrant run landed in high delegation, and the first low delegation,
  low warrant run in high warrant. Their instructions were tightened (attested
  Oct 17) and both were run again (15:28); both reruns are in their cells.
- **The reader's prompt outgrew the model.** The archival low delegation, high
  warrant run cached 3,469 data downloads (3,335 from OpenAlex), and their
  previews came to 2.5 million tokens. Reader 0.13.4 caps the data previews at 500,000 characters
  in all (DECISIONS, Oct 18, staged); the run was read with it, put into the
  run's own copy of the plugin. No other kept run's reading changes.
- **SVG figures counted as numbers** in the qualitative high delegation, high
  warrant run (5,978 of 16,779 traced, above). The reader reads the figures'
  drawing coordinates as reported numbers. Not fixed.
- **Who did what, in two transcripts.** In the archival high delegation, low
  warrant run, the transcript shows Claude's background download as the
  author's hand change, and the download's "finished" notice as an author
  prompt. No code relies on either, so the run's cell doesn't change. The
  runner's own steps on the author's behalf (setup, recording the data,
  writing the accepted finished-work map) also appear as the author's hand
  changes; that is by design, since in real use the person does them.
- **A scoring subagent opened a file under `~/.claude/projects/`** (Oct 17):
  a saved copy of its own tool output, not a session transcript. Reported to
  The author then.

## Limits

One run per author per paper. The authors were simulated (Sonnet 5.5), the
work was done by Claude (Opus 5.5), and the reader is also Claude. There is
no answer key: the codes are the reader's, and the planted-error cells are a
Claude subagent's reading of each record and paper.

## Files

The kept runs, each with a bundle (`../runs/<run>.bundle`, the whole
repository with its record) and `../runs/<run>/disclosure/` (the disclosure,
the reader's units, codes and transcript, and `trail.html`):

- Experiment: `experiment-low-high-2026-10-17-0841`,
  `experiment-high-low-2026-10-17-1043`,
  `experiment-high-high-2026-10-17-0933`,
  `experiment-low-low-2026-10-17-1022`
- Qualitative: `qualitative-low-high-2026-10-17-1528`,
  `qualitative-high-low-2026-10-17-1028`,
  `qualitative-high-high-2026-10-17-0841`,
  `qualitative-low-low-2026-10-17-1528`
- Archival: `low-high-2026-10-17-2006`, `high-low-2026-10-18-2005`,
  `high-high-2026-10-17-0857`, `low-low-2026-10-18-2036`

Set aside, and kept in `../runs/` as they were: the runs of Oct 16; and
from Oct 17, `low-high-2026-10-17-0841` and `low-low-2026-10-17-1113`
(archival, above), and `qualitative-low-high-2026-10-17-1100` and
`qualitative-low-low-2026-10-17-1058` (outside their cells).
