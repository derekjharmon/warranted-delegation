# The settled key: how the labels are made

*Drafted by Claude, 2026-10-15, for the author's review; fixed with the
preregistration, before any run.*

One file per run, `<task>-<cell>.json`, read by `../score.py`. Each holds
the run's settled key: every planted unit and every unit labeled after the
run, with its codes and the quotes that anchor it in the finished work.

## A unit

Fields as in the first test (`../../scripted/labels/`), plus two:

| Field | Value |
| :- | :- |
| `id`, `kind`, `row`, `label` | K1, K2, …; decision or claim; the checklist row; a short name |
| `anchors` | Quotes copied exactly from the finished work, with their files |
| `discretion`, `certification` | The codes; a dash in the key is `null` |
| `basis` | The steps or turns that settle the codes |
| `labeled` | Which codes were labeled after the run (`discretion`, `certification`), or `override` where a departure overrode the planted code |
| `labeled_by` | `planted`, `Claude, by precedent`, `Claude, new kind` (the author labels these himself, so they're never in the spot-check draw), or `the author` |
| `precedent` | For a label Claude applied, the precedent it cites (P1–P17 in `../precedents.md`), or `new kind` |

## The steps, in order

1. **After each run, Claude labels it** from the run's full transcript
   (`tools.py transcripts`, with brainstorm turns shown and marked):
   - each planted unit, anchored in the finished work, with its planted code,
     unless Claude departed from the planted instruction, in which case the
     departure is labeled and overrides the planted code;
   - what Claude did unasked: calls it took, checks it ran, claims it
     added;
   - whether its replies told the author about each handed-over call, which
     decides ignored versus wasn't notified;
   - the cases the key leaves to the labels (for example, a call the author's
     notes write out, kept only if the finished work uses it as written).

   A label of a kind settled in the first test cites its precedent. A label
   that fits no precedent is marked `new kind`; the first cases under coding
   rules 9 and 10 are new kinds.
2. **Claude commits its labels** before the author sees them, so his labels below
   are independent.
3. **The author labels every new kind** himself, from the transcript, and settles
   any disagreement with Claude's label. Where the author rules, the label records
   it (`labeled_by: The author`), and later cases of the same kind cite his ruling.
4. **The author spot-checks a random tenth** of the labels applied by precedent,
   drawn by `tools.py spotcheck` with the seed fixed in the preregistration.
   He marks each one agree or gives his code; his code is the settled one,
   and the number he changes is reported.
5. **The settled key is committed**, and only then does the reader run
   (`../score.py read` refuses to start until the labels are committed).

Reported with the results: how many units were labeled after the runs, how
many applied a precedent and how many were new kinds, how many departures
overrode a planted code, the author's agreement with Claude on the new kinds, and
how many of the spot-checked labels he changed.
