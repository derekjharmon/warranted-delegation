# Demo B: an experiment paper and a qualitative paper

*Design by Claude, 2026-10-16, with the author's decisions (DECISIONS.md, Oct 16).
Materials drafted for the author's review. Ran Oct 16; all twelve runs, with a fourth author (low delegation,
low warrant), ran Oct 17–18: results in [`RESULTS.md`](RESULTS.md).*

**What it's for.** The long demonstration showed the disclosure on one kind of
paper, an archival quantitative one. Demo B adds the other two kinds the
special issue's readers write, an experiment and an inductive qualitative
study, so the demonstrations cover every kind of paper (the author: "demos should
cover all paper types and both corners"). As before, these are
demonstrations, not validation: there is no answer key.

## Three papers, three authors each

| Paper | Question | Data | Packs |
|:-|:-|:-|:-|
| Archival (the long demonstration, `../`) | Do larger or internationally spread author teams get more citations? | OpenAlex, the World Bank | quantitative |
| Experiment (`experiment/`) | What motivates effort when the work is dull: pay, or psychological motivators and gifts? | DellaVigna and Pope's 18-arm experiment with 9,861 MTurk workers: the authors' raw file from their replication package | quantitative, experiments |
| Qualitative (`qualitative/`) | How did Shuttle engineers and managers raise and handle safety concerns, and what did each accident change? | NASA's STS Recordation Oral History Project transcripts (2010–2012), public domain | qualitative |

Each paper is written in three separate runs, from the same notes, by three
simulated authors (Sonnet 5.5), named by their place on the two measures:

| Author | Delegation | Warrant | How they work |
|:-|:-|:-|:-|
| Low-high (careful) | Low | High | Makes the main calls in the prompts, has facts checked against sources, reviews what Claude decided, writes the contribution and limitations by hand |
| High-low (careless) | High | Low | Asks for the whole paper in one prompt, replies in a few words, never checks anything |
| High-high | High | High | Lets Claude make the calls, then has every decision listed and accepts or changes each, has facts checked and reads the evidence, writes nothing by hand |

The archival paper already has its careful and careless runs (Oct 7, reread
Oct 16); it adds a high-high run. Demo B's two papers get all three: seven
new runs in all.

## Planted errors

Seven per paper, one per stage, entered through the author's notes and each
checked against its source on Oct 16: `experiment/plants.md`,
`qualitative/plants.md`. Neither the simulated authors nor Claude can read
them.

## Running it

Same runner, sandbox, and saving as the long demonstration (`../README.md`):

    python3 tests/longdemo/run.py --paper experiment smoke     a three-prompt check
    python3 tests/longdemo/run.py --paper experiment low-high  (or high-low, high-high)
    python3 tests/longdemo/run.py high-high                    the archival paper's third run

Each run now installs its own Python packages (pandas, statsmodels, pyreadstat
for Stata files, pypdf for the transcripts, and a few more), since the system
Python's are no longer complete. Each paper's sandbox reaches only its own
sources, Crossref and doi.org for reference checks, and the Python package
index. The runner proposes each paper's packs in the finished-work map, so
every author is read against the same checklist.

**Order:** a smoke run of each new paper first, then one run at a time:
archival high-high, then the experiment's three, then the qualitative
paper's three.

**Cost, from the archival runs:** about an hour of Claude's work per careful
or high-high run, on the subscription (more for the qualitative paper, whose
transcripts are long), and $5–15 on the API key per run for the simulated
author and the reader. Roughly $40–80 for the seven runs, plus a few dollars
for the smoke runs.
