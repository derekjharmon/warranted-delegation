# Checkable-claims checklist (right answers)

*First draft by Claude, 2026-10-05, for the author to edit. Not yet adopted. Companion to `judgment-decisions.md`. Stages for the two rows that could sit in two stages ruled by the author, 2026-10-05. Packs for experiments, qualitative work, and theory: first draft by Claude, 2026-10-07; stage for THV3 ruled by the author, 2026-10-07. Tool pack: first draft by Claude, 2026-10-15, accepted by the author as drafted, 2026-10-15.*

**What this list asks.** For anything in the finished work that a source can settle, was it checked against that source? Whether a claim is right does not depend on who decided it, so these rows get no discretion code. Your direction can set up a check (name the source, have the tool work from it) but can't run it.

**Structure.** A **spine** that applies to any paper, plus a **pack** for each type of paper. This draft has the spine and five packs, matching `judgment-decisions.md`: quantitative, experiments (taken together with the quantitative pack), qualitative, theory, and tools.

**What a row is.** A type of claim in the finished work that can be checked against a source outside the claim itself. The source can sit outside the paper, in its data and code, or in the paper itself.

**Repeatable rows.** Rows marked *(each)* occur once per instance: each reference, each reported number.

**Code.** Each claim gets one code, strongest to weakest: you checked it against the source · the tool checked it, and you confirmed the check · the tool checked it; you didn't see the result · no check · wasn't notified. The third value covers a check the tool ran silently and one it told you about that you didn't look at. Confirming a tool's check requires its output to be in the record.

**Stage.** Each row rolls up into one of five research stages, fixed per row.

**Listing.** "Yes" means the claims can be listed mechanically from the finished work. "Partly" means a coder still has to pick some of them out.

## Spine: any paper

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| V1 | Reference entry *(each)*: the work exists and its details are right | The publication record (DOI, publisher) | Reference list | Conceptualization | Yes |
| V2 | Citation description *(each)*: the cited work says what the text says it says | The cited work | Manuscript text | Conceptualization | Mostly: any sentence with a citation is a candidate |
| V3 | Quotation *(each)*: quoted text matches its source word for word | The source | Manuscript text | Conceptualization | Yes: quotation marks with a citation |
| V4 | Internal consistency *(each)*: the same fact is stated the same way throughout (N, numbers, hypothesis labels, defined terms) | The paper itself | Manuscript | Writing and editing | Partly: repeated numbers can be matched mechanically; wording can't |
| V5 | Factual claim about the world *(each)* | An outside source | Manuscript text | Conceptualization | No |

## Quantitative pack: archival or survey data

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| QV1 | Reported number *(each)*: a number in a table or the text matches what the code produces | The script that produced it, run after its last edit | Tables; manuscript text | Data preparation and analysis | Yes |
| QV2 | Result description *(each)*: direction, significance, and size as described match the output | The table or output | Results; discussion | Presentation of results | Partly: sentences that point to a table or result |
| QV3 | Methods description *(each)*: the methods section describes what the code actually does | The code | Methods section; code | Research design | Partly |
| QV4 | Collected data match their source | The source database, archive, or API | Collection script; data | Research design | Partly: spot checks |
| QV5 | Classification accuracy *(each scheme)*: labels follow the coding scheme | A human-coded sample | Classification output | Data preparation and analysis | Yes, once a scheme is listed |
| QV6 | Figure matches the data *(each)* | The data and the code that drew it | Figures | Presentation of results | Yes |

## Experiments pack: studies with a manipulation

Taken together with the quantitative pack, whose rows on reported numbers and results apply as written.

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| EXV1 | Participant flow *(each count)*: the numbers approached, started, completed, and analyzed match the data and agree across text, tables, and flowchart | The data | Methods section; flowchart; tables | Presentation of results | Yes |
| EXV2 | Manipulation-check result *(each)*: the reported result matches the output | The output of the analysis code | Results section | Presentation of results | Yes |
| EXV3 | Preregistration match: the reported hypotheses, sample, exclusions, and analyses match the preregistration, or the departures are stated | The preregistration | Methods section | Research design | Partly |
| EXV4 | Materials description: the methods describe what participants actually saw | The materials (survey export, stimuli) | Methods section | Research design | Partly |
| EXV5 | Balance across conditions: reported baseline comparisons match the data | The data and the code | Tables; results section | Presentation of results | Yes |

## Qualitative pack: interviews, fieldwork, documents, and cases

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| QLV1 | Excerpt from the data *(each)*: a quote or field note matches the transcript or notes word for word, and its attribution (role, site, time) is right | The data | Findings | Presentation of results | Yes: quoted excerpts |
| QLV2 | Data counts *(each)*: numbers of interviews, hours, sites, or documents match the data and agree across the paper | The data | Methods section; tables | Presentation of results | Yes |
| QLV3 | Coding description: the methods describe the coding actually done (stages, coders, codebook) | The codebook and the coded data | Methods section | Research design | Partly |
| QLV4 | Excerpt coding *(each)*: an excerpt shown for a theme is coded under that theme | The coded data | Findings | Data preparation and analysis | Yes, once the coded data are in the project |
| QLV5 | Transcript fidelity: transcripts match the recordings | The recordings | Data | Data preparation and analysis | Partly: spot checks |

## Theory pack: papers with no original data

Descriptions of the theories a paper builds on are spine row V2.

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| THV1 | Construct use *(each construct)*: the construct is used as defined throughout | The paper itself | Manuscript | Writing and editing | Partly |
| THV2 | Premise consistency: no stated premise is contradicted elsewhere in the paper | The paper itself | Manuscript | Writing and editing | Partly |
| THV3 | Derivation *(each result, formal models)*: a stated result follows from the model's assumptions | The derivation or proof | Model section; appendix | Data preparation and analysis | Yes |

## Tool pack: papers that build a research tool

Reported validation numbers are also quantitative row QV1; TLV3 is for agreement statistics and counts from the scoring output.

| ID | Checkable claim | Checked against | Usually anchored in | Stage | Listing |
|:-|:-|:-|:-|:-|:-|
| TLV1 | Behavior description *(each)*: the paper or documentation describes what the code actually does | The code, run | Paper; README; documentation | Research design | Partly |
| TLV2 | Test result *(each)*: a reported test outcome matches the test's output | The test, rerun | Paper; README | Presentation of results | Yes |
| TLV3 | Validation result *(each)*: a reported agreement or count matches the scoring output | The scoring script's output | Paper; results files | Presentation of results | Yes |
| TLV4 | Versions: the stated versions of models and libraries match what the tool uses | Code; configuration; run records | Documentation; paper | Research design | Yes |
| TLV5 | Setup works as described: the stated steps install and start the tool | A fresh install by someone else | README; guide | Research design | Partly |

*29 row types: 5 in the spine, 6 in the quantitative pack, 5 in the experiments pack, 5 in the qualitative pack, 3 in the theory pack, 5 in the tool pack.*
