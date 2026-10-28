# Results: the second preregistered test (the fixed reader)

*Redrawn 2026-10-23: the disclosures in `reader-runs/` were drawn again from their saved codes with plugin 0.10.7, in the layout the demonstrations use, which leaves out the section outside the two measures (DECISIONS.md, Oct 22). No codes or scores changed.*

*2026-10-15, written by Claude. Preregistration and frozen reader attested
in `057f94d` (README.md); twelve runs played that evening; the settled key
attested in `d73f8bb`; the reader then run on all twelve, through the API and
through headless Claude Code with no API key; scored by `score.py`
([`reader-runs/score.md`](reader-runs/score.md)).*

*Corrected 2026-10-23: the settled key (`d73f8bb`) has 389 planted units and 325 labeled by precedent; the summary below says 390 and 324. The total, 725, and every score are unchanged.*

## The result

**The fixed reader is validated on both paths:** κ is at least 0.6 on all
three primary codes, through the API and headless, each on its own.

| Code | Layer | API: n | API: κ | Headless: n | Headless: κ |
| :- | :- | -: | -: | -: | -: |
| Discretion: kept vs handed over | primary | 336 | 0.73 | 342 | 0.71 |
| Judgment certification | primary | 188 | 0.78 | 191 | 0.77 |
| Right-answer certification | primary | 348 | 0.72 | 355 | 0.73 |
| Discretion: given vs taken | second | 188 | 0.66 | 191 | 0.63 |
| Unchecked claims: no check vs wasn't notified | second | 158 | 0.00 | 157 | 0.00 |

Agreement on the primary codes is 84–87% on both paths. For comparison, the
first test's frozen reader scored 0.71, 0.70, and 0.75 on four runs, with 37
judgment-certification units; this test has 188–191, so that κ is now
measured about twice as precisely.

**Second layers.**
- **Given vs taken clears 0.6 on both paths for the first time** (0.66 and
  0.63; the first test: 0.47). Whether the disclosure now reports the split
  is a decision for the author; this test only reports it.
- **No check vs wasn't notified** stays at κ 0 despite 97% agreement: the key
  has few "wasn't notified" claims, so the category is still unvalidated.

**By task**, reported and not held to the bar: every task clears 0.6 on
every primary code on both paths. The agreement tool (the tool pack) is
lowest: kept vs handed over 0.71 through the API and 0.64 headless;
right-answer certification 0.63 and 0.66. Schools is highest (judgment
certification 0.83 and 0.87).

**Listing.** The reader found 684 of the key's 725 units through the API
(94%) and 697 headless (96%); the first test's frozen reader found 85%. It
lists at a finer grain, as before: 885 and 895 units, 281 on each path
matching no key unit.

## The runs and the key

- **Twelve runs**, three tasks in four cells each, about 30 minutes in all;
  every record verifies. The other author's skill was used and captured in
  every run, and both brainstorm segments were labeled where the scripts put
  them.
- **The key: 725 units** (350 decisions, 375 claims), including **209
  judgment-certification units** against the target of about 160. 390 planted,
  324 labeled by Claude under a first-test ruling, 11 new kinds; 29 overrides
  where Claude departed from a script, most of them checks that by the record
  never read the source.
- **The author's part:** he ruled on the 11 new kinds, agreeing with Claude's code
  on 7, and spot-checked 33 of the 325 labels applied by precedent (a random
  tenth, seed 20261017), changing none (`labels/author.md`,
  `labels/spotcheck.md`).
- **The planted errors:** of the 56 that were errors in their run (error 5
  was no error in four high-delegation runs, where the description matched
  the code), 50 were caught by the checks or fixed by Claude unasked. Six
  survived: all five in RAND low-delegation, low-warrant, and one in RAND
  high-delegation, low-warrant. In most low-warrant runs Claude fixed the
  errors unasked, as in the first test, so only the disclosure tells those
  runs apart from careful ones. Each run's fates are in `labels/notes/`.

**Cost:** $19.37 on the API key for the API pass (85 minutes of model time);
the headless pass billed nothing extra ($31.90 at list prices, on the
subscription; 90 minutes).

## Departures from the preregistration

1. **Seven runs first refused to start.** Claude's adapter work briefly
   changed the attested plugin folder while the runs were queued, and each
   run's start-up check refused, before making a project or running anything.
   They were requeued once the folder was clean and finished normally.
2. **`labels/tools.py` gained a `check` command** (it validates label files)
   **and a `Claude, new kind` value** (so new kinds stay out of the spot-check
   draw) after the attest. Neither changes the procedure.
3. **`score.py` reads files with undecodable bytes replaced** (`text_at`),
   changed after the reading and before any score was seen, when a reader
   unit naming a PNG figure stopped the scorer. A quote can't match inside an
   image either way; nothing changes for text files.
4. **The agreement key's summary line miscounts** its low-high planted
   decisions (it says 9 kept and 8 handed over; its table, which the labels
   follow, gives 10 and 7).

Before Claude's labels were committed, two of them were made consistent
across the six labeling agents (noted in the runs' notes): "what counts as
blank" was marked a new kind in all four agreement runs, and two RAND
methods descriptions became "no check" to match the first test's ruling.

## Limits

Claude did the runs, the reading, and most of the labeling; the author ruled on
the new kinds and spot-checked a tenth, and the "Claude graded Claude" limit
is larger than in the first test. The simulated author's lines are scripted,
the tasks are small, and two of the three are quantitative. Current models
take no temperature setting, so a rerun would vary.
