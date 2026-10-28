# Technical Appendix

**Contents**

- **A1. How the plugin records the work.** What the record keeps, how its entries are chained so that later changes show, the fingerprint that ties each disclosure to its record, and what the record misses.
- **A2. Attesting and the other saving commands.** How the author signs off on each version, the sentence the author can add, the final version, and sharing saves with coauthors.
- **A3. The checklists of judgment calls and verifiable claims.** Every item the reader looks for, the research stage it belongs to, and the reporting standard it comes from.
- **A4. How the reader codes a paper from its record.** The reader's four steps, the codes, the coding rules, two figures computed but not shown, the model the reader runs on, and its versions.
- **A5. The two preregistered tests of the reader.** Their design, tasks, answer keys, results, costs, and departures from the preregistrations.
- **A6. The twelve demonstrations on full papers.** The three papers and four simulated authors, where each author landed, what happened to the planted errors, and what went wrong.
- **A7. What AI-text detectors see in the same papers.** Two detectors' verdicts on the twelve demonstration papers and on four versions of a human-written article, two of them copy edited by Claude.
- **A8. Running the plugin in Codex.** How the plugin runs in Codex CLI, its live test, and the two items still open.
- **A9. Privacy, consent, and withholding.** What stays on the author's computer, what is sent where and with whose consent, and how the author keeps text out of what others see.
- **A10. The review copy.** What the copy reviewers receive holds, and every way it differs from the original repository for blind review.
- **A11. Where each number in the proposal comes from.** Each number's source and how to check it, mostly with one script.
- **A12. What Stage 2 adds to the tool.** The build work behind proposal §4, starting with a reader for long projects.
- References for the appendix

*The proposal describes warranted delegation and the plugin that puts it into practice. This appendix gives the detail behind each part of that work, and each section opens by saying what it covers and which part of the proposal it supports. Each section can be read on its own. File paths are relative to the top folder of the review copy, whose README is the place to start checking the work (A10).*

## A1. How the plugin records the work

This appendix describes the record the plugin keeps while the author works, which proposal §1 introduces and proposal Figure 1 shows as its first step. It covers what the record keeps, how each entry is linked to the one before it so that later changes show, the fingerprint that ties each disclosure to the exact record it read, and what the record does not keep.

### What the record keeps

The plugin's logger runs on the AI tool's hooks (i.e., the points at which the tool hands each event to an outside program), so it records without the author doing anything. Each event becomes one line of a log, written as compact JSON. The events are the start and end of each session, each prompt the author sends, each action the AI takes in the project (e.g., a shell command, a file edit, or a skill it uses), and the end of each turn with the AI's final message.

Long text is kept beside the log in separate files (sidecars), each named by the SHA-256 hash of its content (`provenance/log/text/<hash>.txt`). The sidecars hold the prompts, the AI's final messages, and the output of each tool call up to its first 20,000 bytes. The log line holds only the hash, so text can later be withheld without changing the log (A9).

Before each prompt and after each turn, the logger also takes a snapshot of the project's files and saves it as a commit on a separate reference (`refs/provenance/<log id>/snapshots`) that never touches the author's branches. Changes between a turn's two snapshots are the AI's work, and changes between the end of one turn and the next prompt are the author's, made by hand. The reader relies on this timing to say who changed each passage (A4). Snapshots leave out files the project ignores and any file over 25 MB.

At the start of each session the logger also records the instructions the AI works under, because a call settled in advance by an instruction file, a skill, or the AI's memory does not show in the conversation itself. For Claude Code these are the author's and the project's instruction files (CLAUDE.md), the AI's memory notes for the project, the skills in use, and the plugins turned on. For Codex they are the author's and the project's instruction files (AGENTS.md). The text of each is kept as a sidecar, and the list is written again whenever a file in it changes.

### The hash chain

Every line of the log records `prev_hash` (i.e., the SHA-256 hash of the previous line's exact bytes), and the first line records 64 zeros in its place. Changing, inserting, or deleting any line therefore breaks every link after it. The script `provenance/verify_log.py` checks every log's chain and every sidecar's hash, and it runs without the plugin installed.

Each copy of a project (e.g., each coauthor's computer) writes its own log, named by the author and a random suffix, so every chain has a single writer and never forks.

### Fingerprints

A fingerprint ties a disclosure to the exact record it was read from. It consists of the commit of the attested version that was read and, for each log, the hash of its last line and its number of events. Every disclosure prints its fingerprint in its header (proposal Figures 2 and 3). Anyone holding the repository can check that the commit exists, that each log's last line has that hash, and that the chain verifies up to it.

### What the record does not keep

The record sees only what happens in the project, which proposal §5 lists as the second risk. Specifically, it does not keep the following.

- **AI used outside the project.** A chat window in a browser, an assistant in another program, or an AI session in a different folder leaves no trace.
- **The AI's text between tool calls.** Only each turn's final message is kept, because the plugin records what the end-of-turn hook hands it and never opens the session transcript.
- **Long output.** Tool output past its first 20,000 bytes is cut, and the hash of the full output is kept.
- **Images attached to a prompt.** The hooks receive only the prompt's text.
- **Paths changed by a shell command.** A command that edits files (e.g., `sed -i`) is logged without the paths it changed, although Claude Code's output for it, which the record keeps, now lists them. The snapshots show what changed.

The record is tamper-evident, not tamper-proof. Someone with write access could rewrite the whole log and recompute every hash. Each attested version fixes the record as it stood at that moment, and the proposal prints the final fingerprint of this repository's own record, so a rewrite after that point would show.

## A2. Attesting and the other saving commands

This appendix describes attesting, the one step the plugin adds while the author works (proposal §2), and the commands that support it. Attesting saves the work and the record together under the author's name, lets the author add a sentence for anything the record cannot see, and, when the project has a GitHub repository, shares the save with coauthors.

### Attesting

The author types `/warrant:attest` (in Codex, `warrant:attest`) at natural stopping points, with or without a sentence after it.

```
/warrant:attest
/warrant:attest Checked Table 2 against the output by hand.
/warrant:attest final
```

The plugin's hook catches the command before it reaches the AI. It records the command like any other prompt and then saves the work, the log, and the sidecars as a new git commit with two trailers (i.e., labeled lines at the end of the commit message). `Attested-by` gives the author's name from git, and `Verified` gives the author's sentence if there is one. The hook then blocks the command, so the AI never has the sentence in context.

The sentence is how the author reports anything the record cannot see, such as a source checked in print. The reader counts it only for the claims it names (A4). A bare `/warrant:attest` is a save rather than a statement, so the reader does not treat it as accepting a call or confirming a check.

`/warrant:attest final` also adds a dated tag (`final-YYYY-MM-DD`), which marks the version the final disclosure reads.

### Sharing with coauthors

When the project has a GitHub repository, each attest first brings in coauthors' new saves. It moves forward when there is nothing to combine and makes a merge commit when there is, and it never rewrites a commit. If coauthors changed the same part of a file, it stops, names the file, and pushes nothing. Otherwise it pushes the commit, any tag, and this copy's snapshots to the private repository. Files over 25 MB are left out, and the message names them.

### The other commands

Four more commands set up the project and support saving.

- `/warrant:setup`, run once per project, starts the record, puts the folder under version control, creates a private GitHub repository when the author uses GitHub, and asks a few questions (e.g., which AI tool the project uses).
- `/warrant:record` shows the last save, what has changed since, and whether every log verifies.
- `/warrant:sync` brings in coauthors' newest saves on request.
- `/warrant:undo` reverses the most recent save as a new save. History is never rewritten, and the record of the undo stays.

## A3. The checklists of judgment calls and verifiable claims

This appendix lists every item the reader looks for in a paper. Proposal §2 describes the checklists, and the reader (A4) codes each instance of an item that it finds. The section first says what the checklists contain, how they are organized, and where their items come from, and then gives the full lists.

### What the checklists contain

The reader works from two checklists. The first names the kinds of judgment calls a paper can contain (i.e., choices the finished work embodies that could reasonably have gone another way). The second names the kinds of verifiable claims (i.e., anything in the finished work that a source can settle). Wording, grammar, spelling, and formatting are left out on purpose, because who typed a sentence is labor rather than a call. The calls made in the text itself (framing, interpretation, contribution, and limitations) are included.

Each checklist has a core that every paper gets (the spine) and a section for each kind of paper (a pack). The packs cover quantitative studies using archival or survey data, experiments (used together with the quantitative pack), qualitative studies, theory papers, and research tools. A paper can take more than one pack, as a mixed-methods study would. At the first disclosure the plugin proposes the packs from the project's files, and the author confirms or changes them. The table counts the items in each part.

| | Judgment calls | Verifiable claims |
|:-|-:|-:|
| Spine (every paper) | 9 | 5 |
| Quantitative pack | 24 | 6 |
| Experiments pack | 11 | 5 |
| Qualitative pack | 17 | 5 |
| Theory pack | 9 | 3 |
| Tool pack | 15 | 5 |
| **Total** | **85** | **29** |

Each item is a type, and the reader finds every instance of it in the paper. Items marked *(each)* give one instance per occurrence (e.g., each exclusion rule or each reference entry). A call counts once even when it appears in several places, such as the cleaning code and the methods section, and each place is recorded as an anchor (i.e., a short quote that locates the call in the work). Each item also belongs to one of five research stages (conceptualization, research design, data preparation and analysis, presentation of results, and writing and editing). The stages let the disclosure show where in the work the calls and claims fell.

### Where the items come from

Each row of the lists below names the source of its item.

- **JARS.** The American Psychological Association's Journal Article Reporting Standards for quantitative research (JARS-Quant, Table 1, and Table 2 for studies with an experimental manipulation; Appelbaum et al. 2018) and for qualitative research (JARS-Qual, Table 1; Levitt et al. 2018).
- **The census.** The author tasks coded in a census of AI policies at 92 journals in 12 fields (Harmon 2026).
- **Research software.** For the tool pack, the Journal of Open Source Software's review checklist (JOSS n.d.), ACM's artifact badges (ACM 2020), and the FAIR principles for research software (FAIR4RS; Barker et al. 2022).
- **Added.** Items no standard asks for, usually because the call is made in the code (e.g., how datasets are merged) or in the validation of a tool (e.g., the answer key and the agreement bar).

The verifiable claims are defined by what they are checked against (the publication record, the cited work, the code, the data, or a preregistration).

### Judgment calls

The judgment calls follow, first the spine and then each pack. Within a pack, the calls are grouped by where they are made (e.g., the collection script, the cleaning code, or the manuscript).

**Spine: any paper**

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| S1 | Research question: the problem the paper addresses | Conceptualization | JARS: Problem |
| S2 | Theoretical framing: the lens the argument uses | Conceptualization | JARS: Hypotheses/aims |
| S3 | Literature positioned in: which conversations the paper joins | Conceptualization | Census (Harmon 2026): Finding literature |
| S4 | Synthesis of prior work: how the literature is organized and what it is said to show | Conceptualization | Census (Harmon 2026): Summarizing or synthesizing literature |
| S5 | Source for a key claim *(each)*: which work is cited in support | Conceptualization | Added |
| S6 | Contribution claim *(each)* | Conceptualization | Partly JARS: Implications |
| S7 | Argument structure: the order and organization of the paper's moves | Writing and editing | Census (Harmon 2026): Editing, formatting, structure |
| S8 | Presentation of results *(each figure or table)*: what is shown, and how | Presentation of results | Census (Harmon 2026): Images and figures |
| S9 | Limitations and boundary conditions | Writing and editing | JARS: Interpretation; Generalizability |

**Quantitative pack: archival or survey data**

*Collection: collection instrument or script*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QC1 | Data source: which database, archive, platform, or population | Research design | JARS: Sampling procedures |
| QC2 | Sampling frame and window: who or what is in scope, and the time period | Research design | JARS: Inclusion/exclusion; Sampling procedures |
| QC3 | Sample size: intended size or stopping rule for primary data, or coverage for archival data | Research design | JARS: Sample size/power/precision |
| QC4 | Measures collected: which variables or items are gathered, including ones never used | Research design | JARS: Measures and covariates |
| QC5 | Instrument content *(each)*: item wording, scales, or prompts | Research design | JARS: Instrumentation |
| QC6 | Collection procedure: mode, timing, and how sources are linked at collection | Research design | JARS: Data collection |

*Cleaning: cleaning code*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QK1 | Exclusion rule *(each)*: a rule that drops cases after collection | Data preparation and analysis | JARS: Data diagnostics; Inclusion/exclusion |
| QK2 | Missing data: drop, impute, and by what method | Data preparation and analysis | JARS: Data diagnostics |
| QK3 | Outliers: how they are defined and treated (winsorize, trim, keep) | Data preparation and analysis | JARS: Data diagnostics |
| QK4 | Transformation *(each)*: logs, scaling, lags | Data preparation and analysis | JARS: Data diagnostics |
| QK5 | Variable construction *(each)*: how an analysis variable is built from raw fields | Data preparation and analysis | Added (JARS asks for definitions, not construction) |
| QK6 | Merging rules: how datasets are joined and matched | Data preparation and analysis | Added |
| QK7 | Coding scheme *(each)*: the categories and decision rules for classifying text or cases | Research design | Census (Harmon 2026): Deductive coding, classification |

*Analysis: analysis code*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QA1 | Dependent variable: which measure stands for the outcome | Data preparation and analysis | JARS: Measures and covariates |
| QA2 | Focal predictor *(each)*: which measure stands for the key construct | Data preparation and analysis | JARS: Measures and covariates |
| QA3 | Controls: which covariates are included | Data preparation and analysis | JARS: Measures and covariates |
| QA4 | Estimator: OLS, fixed effects, logit, multilevel, and so on | Research design | JARS: Analytic strategy |
| QA5 | Fixed effects and standard errors: which effects, and how errors are clustered | Data preparation and analysis | Added (finer than JARS asks) |
| QA6 | Inference rules: thresholds, one- or two-tailed tests, corrections for multiple tests | Research design | JARS: Analytic strategy |
| QA7 | Robustness check *(each)* | Data preparation and analysis | Partly JARS: Analytic strategy |
| QA8 | Additional or exploratory analysis *(each)* | Data preparation and analysis | Partly JARS: Analytic strategy |

*Manuscript*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QM1 | Hypothesis *(each)* | Conceptualization | JARS: Hypotheses/aims |
| QM2 | Interpretation of a main result *(each)* | Presentation of results | JARS: Support of hypotheses; Interpretation |
| QM3 | What gets reported: which analyses appear in the paper, which go to an appendix, which are left out | Presentation of results | Added |

**Experiments pack: studies with a manipulation**

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| EX1 | Conditions: which conditions are run, including the comparison condition | Research design | JARS-Quant T2: Experimental manipulations |
| EX2 | Manipulation content *(each)*: what participants in a condition see or do (stimuli, instructions, vignettes) | Research design | JARS-Quant T2: Experimental manipulations |
| EX3 | Delivery: the setting or platform, who delivers the manipulation, how long exposure lasts, and incentives for compliance | Research design | JARS-Quant T2: Delivery, deliverer, setting, exposure |
| EX4 | Unit of assignment and analysis: what is assigned to conditions (person, team, session), and how the analysis accounts for it | Research design | JARS-Quant T2: Units of delivery and analysis |
| EX5 | Assignment procedure: how units are randomized, with any blocking or stratification; for nonrandom assignment, the rule and the steps against selection bias | Research design | JARS-Quant T2, Modules A and B: Assignment method |
| EX6 | Masking: who is kept unaware of condition (participants, experimenters, coders) | Research design | JARS-Quant T2, Modules A and B: Masking |
| EX7 | Manipulation and attention checks *(each)*: which checks are included, and how their results are used | Research design | JARS-Quant T2: Treatment fidelity |
| EX8 | Preregistration: what is registered before data collection | Research design | JARS: Registration information |
| EX9 | Departure from the preregistration *(each)* | Research design | Added |
| EX10 | Study set: which studies the paper includes, and what each later study adds (replication, mechanism, boundary) | Research design | Added |
| EX11 | Mediation or moderation test *(each)*: which are run, and how | Data preparation and analysis | JARS-Quant T2, Module A: Statistical methods |

**Qualitative pack: interviews, fieldwork, documents, and cases**

*Collection: protocol and data*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QL1 | Approach and design: the approach to inquiry (such as grounded theory, case study, ethnography, process study) and the design that follows from it | Research design | JARS-Qual: Research design overview |
| QL2 | Selection of sites, cases, participants, or documents: the logic (purposive, theoretical, maximum variation) and the inclusion criteria | Research design | JARS-Qual: Participant selection |
| QL3 | Recruitment and access: how participants or sites are reached, and any incentives | Research design | JARS-Qual: Recruitment process |
| QL4 | Protocol content *(each)*: interview questions, observation focus, or document search terms | Research design | JARS-Qual: Data collection |
| QL5 | Protocol change *(each)*: a change to the protocol in response to what is being found | Research design | JARS-Qual: Data collection (alterations) |
| QL6 | Stopping: how many participants, cases, or documents, and when collection stops | Research design | JARS-Qual: Recruitment process (number; rationale to halt) |
| QL7 | Recording and transcription: what is recorded, and how it is transcribed or summarized | Data preparation and analysis | JARS-Qual: Recording and data transformation |
| QL8 | Researcher position: how the researchers' prior understandings, and their relationships with participants, are handled | Research design | JARS-Qual: Researcher description; Researcher–participant relationship |

*Analysis: codebook and coding*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QL9 | Coding approach: codes set in advance or emerging from the data, and the unit coded | Data preparation and analysis | JARS-Qual: Data-analytic strategies |
| QL10 | Code *(each)*: a code's definition and decision rules | Data preparation and analysis | JARS-Qual: Analytic scheme; Census (Harmon 2026): Inductive or abductive interpretation; Deductive coding |
| QL11 | Who codes, and how disagreements are resolved | Data preparation and analysis | JARS-Qual: Coders or analysts; Methodological integrity |
| QL12 | Analytic structure: how codes are grouped into themes, categories, or a data structure | Data preparation and analysis | JARS-Qual: Analytic scheme development |
| QL13 | Integrity check *(each)*: member checks, triangulation, audits, or other checks added to the analysis | Research design | JARS-Qual: Methodological integrity |

*Manuscript*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| QL14 | Finding *(each)*: a theme, category, or mechanism as stated | Presentation of results | JARS-Qual: Findings; Census (Harmon 2026): Theory development, interpreting findings |
| QL15 | Excerpts for a finding *(each finding)*: which quotes or field notes are shown in support | Presentation of results | JARS-Qual: Findings (demonstrating the analytic process) |
| QL16 | Model built from the findings: the process or theoretical model the paper proposes | Conceptualization | Census (Harmon 2026): Theory development, interpreting findings |
| QL17 | Rival interpretations: which disconfirming evidence or alternative readings are addressed | Presentation of results | JARS-Qual: Methodological integrity |

**Theory pack: papers with no original data**

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| TH1 | Core claim: the paper's central argument, in a sentence or two | Conceptualization | Census (Harmon 2026): Theory development |
| TH2 | Argument form: propositions, process model, typology, essay, or formal model | Conceptualization | Added |
| TH3 | Construct definition *(each)* | Conceptualization | Census (Harmon 2026): Theory development |
| TH4 | Level of analysis | Conceptualization | Added |
| TH5 | Premise or assumption *(each)*: what the argument takes as given | Conceptualization | Added |
| TH6 | Proposition or relationship *(each)*: what is related to what, and in which direction | Conceptualization | Census (Harmon 2026): Theory development |
| TH7 | Mechanism *(each relationship)*: why the relationship holds | Conceptualization | Census (Harmon 2026): Theory development |
| TH8 | Illustration *(each)*: an example, case, or vignette used to show the argument | Writing and editing | Added |
| TH9 | Model setup (formal models): actors, choices, payoffs, and functional forms | Research design | Added |

**Tool pack: papers that build a research tool**

*The tool*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| TL1 | Purpose and scope: what the tool is for, whom it serves, and what it leaves out on purpose | Conceptualization | JOSS: Statement of need |
| TL2 | What it takes in *(each kind of input)*: what the tool records or reads, and what it deliberately doesn't | Research design | Added (cf. FAIR4RS R1.2, provenance) |
| TL3 | Method *(each core step)*: how the tool turns its inputs into outputs (rules, scoring, prompts) | Research design | JOSS: Functionality |
| TL4 | Models and services *(each)*: which model, API, or library the tool depends on, at which version and settings | Research design | FAIR4RS R2 (references to other software); ACM: Functional |
| TL5 | Output: what the tool reports, in what form, and what it leaves out of the report | Presentation of results | Added |
| TL6 | Failure handling *(each)*: what the tool does when a step fails (stop, skip, warn, fail closed) | Research design | ACM: Functional |
| TL7 | Privacy and consent: what the tool sends where, what stays local, and what users can withhold | Research design | Added |
| TL8 | Setup: how users install and start the tool, and what it changes on their machine | Research design | JOSS: Installation instructions; ACM: Reusable |
| TL9 | Test design *(each suite)*: what is tested, how, and what counts as passing | Data preparation and analysis | JOSS: Automated tests; ACM: Functional |
| TL10 | Availability: license, where the code lives, and how versions are identified | Writing and editing | JOSS: License; FAIR4RS F1, A1, R1.1; ACM: Available |

*Evidence that it works*

| ID | Judgment call | Stage | Source |
|:-|:-|:-|:-|
| TL11 | Validation design: the cases the tool is tested on (real or simulated tasks, planted errors), and why they make a fair test | Research design | ACM: Results Reproduced; Added |
| TL12 | Answer key: who labels the truth, how, and blind to what | Research design | Added |
| TL13 | Matching rule: how the tool's output is paired with the key | Data preparation and analysis | Added |
| TL14 | Agreement statistic and bar: which statistic, and what result counts as passing | Data preparation and analysis | Added |
| TL15 | Settling disagreements: how disagreements among the key's coders are resolved | Data preparation and analysis | Added |

### Verifiable claims

The verifiable claims follow in the same order, each with the source it is checked against.

**Spine: any paper**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| V1 | Reference entry *(each)*: the work exists and its details are right | The publication record (DOI, publisher) | Conceptualization |
| V2 | Citation description *(each)*: the cited work says what the text says it says | The cited work | Conceptualization |
| V3 | Quotation *(each)*: quoted text matches its source word for word | The source | Conceptualization |
| V4 | Internal consistency *(each)*: the same fact is stated the same way throughout (N, numbers, hypothesis labels, defined terms) | The paper itself | Writing and editing |
| V5 | Factual claim about the world *(each)* | An outside source | Conceptualization |

**Quantitative pack: archival or survey data**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| QV1 | Reported number *(each)*: a number in a table or the text matches what the code produces | The script that produced it, run after its last edit | Data preparation and analysis |
| QV2 | Result description *(each)*: direction, significance, and size as described match the output | The table or output | Presentation of results |
| QV3 | Methods description *(each)*: the methods section describes what the code actually does | The code | Research design |
| QV4 | Collected data match their source | The source database, archive, or API | Research design |
| QV5 | Classification accuracy *(each scheme)*: labels follow the coding scheme | A human-coded sample | Data preparation and analysis |
| QV6 | Figure matches the data *(each)* | The data and the code that drew it | Presentation of results |

**Experiments pack: studies with a manipulation**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| EXV1 | Participant flow *(each count)*: the numbers approached, started, completed, and analyzed match the data and agree across text, tables, and flowchart | The data | Presentation of results |
| EXV2 | Manipulation-check result *(each)*: the reported result matches the output | The output of the analysis code | Presentation of results |
| EXV3 | Preregistration match: the reported hypotheses, sample, exclusions, and analyses match the preregistration, or the departures are stated | The preregistration | Research design |
| EXV4 | Materials description: the methods describe what participants actually saw | The materials (survey export, stimuli) | Research design |
| EXV5 | Balance across conditions: reported baseline comparisons match the data | The data and the code | Presentation of results |

**Qualitative pack: interviews, fieldwork, documents, and cases**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| QLV1 | Excerpt from the data *(each)*: a quote or field note matches the transcript or notes word for word, and its attribution (role, site, time) is right | The data | Presentation of results |
| QLV2 | Data counts *(each)*: numbers of interviews, hours, sites, or documents match the data and agree across the paper | The data | Presentation of results |
| QLV3 | Coding description: the methods describe the coding actually done (stages, coders, codebook) | The codebook and the coded data | Research design |
| QLV4 | Excerpt coding *(each)*: an excerpt shown for a theme is coded under that theme | The coded data | Data preparation and analysis |
| QLV5 | Transcript fidelity: transcripts match the recordings | The recordings | Data preparation and analysis |

**Theory pack: papers with no original data**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| THV1 | Construct use *(each construct)*: the construct is used as defined throughout | The paper itself | Writing and editing |
| THV2 | Premise consistency: no stated premise is contradicted elsewhere in the paper | The paper itself | Writing and editing |
| THV3 | Derivation *(each result, formal models)*: a stated result follows from the model's assumptions | The derivation or proof | Data preparation and analysis |

**Tool pack: papers that build a research tool**

| ID | Claim | Checked against | Stage |
|:-|:-|:-|:-|
| TLV1 | Behavior description *(each)*: the paper or documentation describes what the code actually does | The code, run | Research design |
| TLV2 | Test result *(each)*: a reported test outcome matches the test's output | The test, rerun | Presentation of results |
| TLV3 | Validation result *(each)*: a reported agreement or count matches the scoring output | The scoring script's output | Presentation of results |
| TLV4 | Versions: the stated versions of models and libraries match what the tool uses | Code; configuration; run records | Research design |
| TLV5 | Setup works as described: the stated steps install and start the tool | A fresh install by someone else | Research design |

## A4. How the reader codes a paper from its record

This appendix describes the reader (i.e., the script that turns the finished work and its record into codes), which proposal §2 introduces and the tests in A5 validate. It covers the reader's four steps, the codes it assigns, the rules for applying them, two figures it computes but the Stage 1 disclosure does not show, the model it runs on, and its versions.

### The reader's steps

The reader (`plugin/warrant/scripts/reader.py`) runs when the author asks for a disclosure. The AI model does two of its four steps, and the script does the other two mechanically.

1. **List (model).** The model reads only the finished work and the checklists for its packs, and lists each judgment call and verifiable claim, each with its checklist item and short quotes copied exactly from the work as anchors. A second call then finds every other place each one appears in the work (e.g., a restatement in the abstract, a table note, or the conclusion) and adds it as an anchor.
2. **Trace (mechanical).** For each anchor, the script searches the snapshots for the turns that added or changed that text and records who made the change, whether the AI in a turn, the author between turns, or material saved before the record began. It also follows text copied from an earlier file back to whoever first saved it.
3. **Code (model).** The model reads the record as a numbered transcript of turns and codes each unit (i.e., each call or claim), citing the turns it relied on and quoting the few words that decided each code.
4. **Assemble (mechanical).** The script writes the units, the codes, the transcript as the model saw it, and the run's details (`units.json`, `codes.json`, `transcript.txt`, `reader-run.json`), then draws the disclosure. When the author types `/warrant:trail`, the plugin draws the paper trail from the same files, with no model.

The transcript shows each turn's prompt, the AI's tool calls with their output, and its final message. It also shows the author's hand edits between turns, each attest with its sentence, and the text of the instructions in force, labeled by whose they are. Turns the author labeled as brainstorming appear only as placeholders naming the files the AI changed. Data files are shown by their first lines, up to 500,000 characters in all.

### The codes

Each judgment call gets two codes, and each verifiable claim gets one. Where the disclosure shows a code in other words, those words follow the code's name in parentheses.

**Judgment calls** get a code for discretion and a code for how a handed-over call ended.
- **Discretion.** *Kept* if the author made the call, through their prompt or text they supplied. *Given* if the author handed it to the tool, by name or as part of a request that needed it. *Taken* if the tool made it beyond what was asked. The two measures count given and taken together as handed over.
- **How a handed-over call ended,** from strongest to weakest. *Changed* if the author overrode or modified it, by a prompt or by a hand edit. *Elaborated and okayed* ("you accepted it, with a reason") if the author accepted it with a reason. *Okayed* ("you accepted it") if the author accepted it explicitly. *Ignored* if a reply told the author about it and the author never responded. *Wasn't notified* ("you were never told") if no reply ever mentioned it. The first three count as warranted.

**Verifiable claims** get one code, from strongest to weakest.
- *You checked it against the source*, when the author says so in a prompt or an attest sentence.
- *Tool checked, you confirmed*, when the record shows the tool's check and the author then responded to it.
- *Tool checked, you didn't see the result*, when the tool checked but the author never responded to the reply that reported it.
- *No check*.
- *Wasn't notified* ("you were never told"), when nobody checked a claim the tool added beyond what was asked and no reply mentioned it.

The first two count as warranted. Claims get no code for discretion, because whether a claim is right does not depend on who made it.

### The coding rules

The rules settle the cases the codes leave open.

1. An open request hands over every call inside it. "Pick whatever approach you think is best" makes each call needed to fulfill it given, not taken. Taken is a call outside what was asked.
2. Text the author supplies keeps the calls in it, as long as the finished work uses it as written. A change to what it claims is the tool's call, taken unless the author asked for it.
3. A reference list alone keeps the literature but not the citing. Which source backs which claim is given, unless the author's own text or prompt sets it.
4. A call handed over and then overridden by the author is given, then changed, not kept.
5. Accepting without a reason is okayed, whether for one call or a whole list. It covers only what the author was shown. A reason counts only for the calls it is about.
6. A results table counts once for its numbers and takes the weakest code of any part of it.
7. A reply tells the author about a call if it mentions it, even in passing. A bare attest is a save, not a response.
8. When several codes apply, the strongest counts (except tables, rule 6).
9. A call settled in advance by instructions counts as made by whoever wrote them. The author's own instructions, or a skill the author keeps, make it kept. A memory note counts as the author's only when it records the author's own direction. A skill someone else wrote, such as another plugin's, hands the call over, given if the author asked for it and taken if the tool used it on its own.
10. A turn labeled brainstorming shows no direction and no reply. A call whose only trace is the tool's change in such a turn is handed over, and only turns the reader can see can certify it.

A check counts only if the record shows it, as a tool call that compares a claim with its source or looks the source up. A reply saying something was checked, with no such call, is not a check. An attest sentence counts only for the claims it names.

### Computed but not shown

The reader also computes two figures mechanically and saves them with every run. The Stage 1 disclosure does not show them, since the proposal does not develop them, and Stage 2 can show them again.
- **Calls the tool made beyond what was asked.** The share of handed-over calls coded taken, and how many of those the author warranted. It rests on the split between given and taken, which reached κ of 0.47 in the first test (37 units) and 0.66 and 0.63 in the second (about 190 units) (A5). The two measures count given and taken alike as handed over, so this figure changes neither. The list of calls and the paper trail still say, call by call, whether a handed-over call was asked for.
- **Text typed by the tool.** The share of the manuscript's words the AI wrote, from the snapshots. Text the AI copies from the author's own files, eight words or more, counts as the author's. Who typed the text is not the same as who stands behind it, so neither measure counts it.

### The model the reader runs on

The model is Claude Opus 5.5. It runs either through the API, with a key kept in the computer's keychain, or through headless Claude Code (i.e., Claude Code run by a script, with no one typing) on the author's own subscription, with no key. Both paths passed the second test (A5). For projects done in Codex, the reader runs through Codex on the author's OpenAI account. That path has not yet been scored against the test runs, and its disclosures say so in their header (A8).

### Versions

I froze reader 0.6 for the first test and reader 0.12 for the second. Version 0.12 added the step that finds every place a unit appears, coding rules 9 and 10, the tool pack, and the headless path. Later versions changed what the model is shown or what is saved, without changing how units are coded. They added a larger output limit for long papers (0.12.1), the Codex path (0.13), PDFs shown by name only (0.13.1), the Codex model named in the disclosure's header (0.13.2), a fix to how text typed by the tool is counted (0.13.3), a cap on data previews (0.13.4), the paper's title saved with each run (0.13.5), reading in pieces for a record too long to read at once (0.14, A12), and the turns that quote a piece's text shown in that piece too (0.14.1). Each run records the reader's version and the hashes of the reader and checklist files it used.

## A5. The two preregistered tests of the reader

This appendix reports the two preregistered tests behind the first kind of evidence in proposal §3. Each test asked whether the reader, frozen before it saw the scored runs, codes a record the way an answer key fixed in advance does. The section gives the design the two tests share and then each test's task, runs, key, and results.

### Design

In both tests, scripted simulated authors carried out a small research task in Claude Code, each working in one of the four cells (high or low delegation, crossed with high or low warrant). I planted errors in their notes. An answer key codes every judgment call and verifiable claim in the finished work, and the reader, frozen beforehand, codes the same work without seeing the key. Agreement is Cohen's κ on each code, pooled over runs, with a preregistered bar of 0.6 on each of three primary codes.
- Kept versus handed over
- How each handed-over call ended
- How each claim was checked

Two finer splits are reported but not held to the bar, given versus taken and no check versus wasn't notified.

Each key was built in two parts. The first part was planted before the runs. It covers every unit the scripts settle, recording where the discretion sat and how the author responded. The second part was labeled after the runs and covers what the scripts could not fix in advance, namely what Claude did unasked, whether its replies told the author, and any checks it ran on its own.

### The first test (October 6)

**Task.** A two-to-three-page memo asking whether a firm's market value predicts its investment, using the Grunfeld panel (11 US firms, 1935–1954). The notes contained five planted errors, one for each kind of verifiable claim (a reference entry, a citation description, a factual claim, a reported number, and a methods description).

**Runs.** There were four runs, one per cell. I built and tuned the reader (0.6) only on a separate development run and froze it before it saw the four scored runs.

**Results.** The reader cleared the bar on all three primary codes.

| Code | Units | Agreement | κ |
|:-|-:|-:|-:|
| Kept vs handed over | 83 | 86% | 0.71 |
| How a handed-over call ended | 37 | 78% | 0.70 |
| How a claim was checked | 92 | 85% | 0.75 |
| Given vs taken (reported) | 37 | 86% | 0.47 |

The reader found 85% of the key's units. Two later runs of the same frozen reader gave primary κ between 0.76 and 0.82.

**A reader built on another model.** To check that Claude was not simply grading Claude, I ran the frozen reader with OpenAI's gpt-5.3-codex in place of Claude, on the same four records and with the same prompts, and scored it with the same script against the same key. It cleared the same bar.

| Code | Claude (three runs) | gpt-5.3-codex |
|:-|:-|-:|
| Kept vs handed over | 0.71, 0.76, 0.81 | 0.66 |
| How a handed-over call ended | 0.70, 0.78, 0.78 | 0.68 |
| How a claim was checked | 0.75, 0.82, 0.77 | 0.79 |

### The second test (October 15)

**What it tested.** The second test held the fixed reader (0.12) to the bar on new tasks, new runs, and a new key, through the API and through headless Claude Code, each path on its own. I saved the preregistration, the materials, and the frozen reader together before any run existed.

**Tasks.** Each of the three tasks came with the simulated author's notes, five planted errors, and an instruction file the simulated author wrote.
- **Schools**, a quantitative memo on what predicts ninth graders' math scores across 303 California school districts
- **Agreement**, a small research tool that computes percent agreement and Cohen's κ between two coders, with tests and a README, whose calls fall in the tool pack
- **RAND**, an experiment on whether cost sharing reduces doctor visits, using the RAND Health Insurance Experiment (20,190 person-years), with a pre-analysis plan written first

**Runs.** There were twelve runs, each task in all four cells. Every run also included calls settled in advance by the simulated author's instruction file (coded kept) and by a skill from another plugin written by someone else (coded handed over), and two runs included a turn labeled brainstorming.

**The key.** The key holds 725 units (350 judgment calls and 375 verifiable claims). Of these, 389 were planted before the runs, and the rest were labeled after them. Claude labeled those by the rulings from the first test, and I ruled on the 11 new kinds of case, agreeing with Claude's code on 7. I also checked a random tenth of the labels applied by precedent (33 labels, drawn with a fixed seed) and changed none. The settled key was saved before the reader read any run.

**Results.** The fixed reader cleared the bar on both paths.

| Code | API: units | API: κ | Headless: units | Headless: κ |
|:-|-:|-:|-:|-:|
| Kept vs handed over | 336 | 0.73 | 342 | 0.71 |
| How a handed-over call ended | 188 | 0.78 | 191 | 0.77 |
| How a claim was checked | 348 | 0.72 | 355 | 0.73 |
| Given vs taken (reported) | 188 | 0.66 | 191 | 0.63 |
| No check vs wasn't notified (reported) | 158 | 0.00 | 157 | 0.00 |

Agreement on the primary codes was 84% to 87% on both paths, and every task cleared 0.6 on every primary code on both paths. The reader found 684 of the key's 725 units through the API (94%) and 697 headless (96%). The split between no check and wasn't notified stays at κ of 0 despite 97% agreement, because the key has few claims coded wasn't notified, so that category is not yet validated. The disclosure counts both as not warranted, so neither measure depends on the split.

Of the 60 planted errors, four never appeared, because in four high delegation runs Claude wrote the methods description to match the code. Of the other 56, 50 were caught by the author's checks or fixed by Claude unasked. Six survived, five in the RAND low delegation, low warrant run and one in the RAND high delegation, low warrant run.

**Cost.** The API pass cost $19.37, and the headless pass cost nothing beyond the subscription.

**Departures from the preregistration.** Seven runs first refused to start, before doing anything, because the plugin's folder had briefly changed while they were queued. They were requeued once it was restored and finished normally. After the preregistration was attested, the labeling tool gained a check command and a new label value, neither of which changes the procedure. The scorer needed one fix to read an image file. One summary line in the key miscounts, and the labels follow the key's table instead.

## A6. The twelve demonstrations on full papers

This appendix reports the demonstrations behind the second kind of evidence in proposal §3 and the two disclosures in proposal Figure 2. They show the disclosure on full papers, one of each kind the special issue's readers write. They are demonstrations rather than validation, because no answer key exists for a full paper. The section describes the papers and the simulated authors and then reports where each author landed, what happened to the planted errors, what went wrong, and the limits.

### The papers and the simulated authors

Each paper asks a question of real, public data.

| Paper | Question | Data | Packs |
|:-|:-|:-|:-|
| Archival | Do larger or internationally spread author teams get more citations? | OpenAlex and the World Bank | Quantitative |
| Experiment | What motivates effort on dull work, pay or psychological motivators and gifts? | DellaVigna and Pope's (2018) 18-arm experiment with 9,861 MTurk workers, from the authors' replication package | Quantitative, experiments |
| Qualitative study | How did Space Shuttle engineers and managers raise and settle safety concerns, and what did each accident change? | NASA's STS Recordation Oral History Project transcripts (2010–2012; NASA History Office n.d.), freely available from NASA | Qualitative |

Four simulated authors wrote each paper from the same notes, one in each cell. Each works in the way the table describes.

| Author | How they work |
|:-|:-|
| Low delegation, high warrant | Makes the main calls in the prompts, has facts checked against sources, reviews what Claude decided, and writes the contribution and limitations |
| High delegation, low warrant | Asks for the whole paper in one prompt, replies in a few words, and never checks anything |
| High delegation, high warrant | Lets Claude make the calls, then has every decision listed and changes or accepts each, and has facts checked and reads the evidence |
| Low delegation, low warrant | Makes every call up front, in each stage's first prompt, from their own notes and reading, never checks, and never responds to what Claude reports or asks |

The simulated authors were played by Claude Sonnet 5.5, following written instructions. Claude Code (Opus 5.5) did the work, headless on a subscription, in a sandbox whose commands could reach only the paper's own data sources, Crossref and doi.org for checking references, and Python's package index. Its web search and page-reading tools were not limited. The reader then read each finished paper and its record through the API.

Each paper's notes contained seven planted errors, one in each part of the work (the design or data collection, the data, the analysis or coding, the methods description, a reference entry, a description of the literature, and a factual claim). I checked each against its source beforehand, and neither the simulated authors nor Claude could read the list.

### Where each author landed

An author counts as low delegation if they made more than half the judgment calls, and as high warrant if they changed or accepted more than half the calls handed to the tool. Every author landed in the cell it was written for.

| Paper | Author | Calls the author made | Handed calls warranted |
|:-|:-|-:|-:|
| Experiment | Low delegation, high warrant | 35 of 49 (71%) | 14 of 14 (100%) |
| | High delegation, low warrant | 2 of 64 (3%) | 0 of 62 |
| | High delegation, high warrant | 24 of 59 (41%) | 35 of 35 (100%) |
| | Low delegation, low warrant | 29 of 44 (66%) | 4 of 15 (27%) |
| Qualitative study | Low delegation, high warrant | 66 of 80 (82%) | 12 of 14 (86%) |
| | High delegation, low warrant | 1 of 86 (1%) | 0 of 85 |
| | High delegation, high warrant | 18 of 105 (17%) | 86 of 87 (99%) |
| | Low delegation, low warrant | 49 of 70 (70%) | 1 of 21 (5%) |
| Archival | Low delegation, high warrant | 59 of 83 (71%) | 16 of 24 (67%) |
| | High delegation, low warrant | 12 of 88 (14%) | 0 of 76 |
| | High delegation, high warrant | 20 of 102 (20%) | 81 of 82 (99%) |
| | Low delegation, low warrant | 43 of 74 (58%) | 2 of 31 (6%) |

The two low warrant authors differ in where their claims went unchecked. The high delegation, low warrant authors left most claims with no check at all (54% to 84%). For the low delegation, low warrant authors Claude checked more of the claims, but the author never saw the results (33% to 72%).

### The planted errors

The table counts what happened to each kind of author's 21 planted errors across the three papers.

| Author, all three papers | Caught by the author | Fixed by Claude unasked | Stayed in the paper | Left out of the paper |
|:-|-:|-:|-:|-:|
| Low delegation, high warrant | 12 | 4 | 0 | 5 |
| High delegation, low warrant | 0 | 21 | 0 | 0 |
| High delegation, high warrant | 10 | 9 | 0 | 2 |
| Low delegation, low warrant | 3 | 11 | 6 | 1 |

All six errors that stayed belong to the low delegation, low warrant authors, and each came in through the author's own instructions. Claude flagged two of them. One got no reply, and in the other, in the qualitative study, the author required a wrong publication year after two flags. The high delegation, low warrant papers are free of all 21 plants because Claude fixed every one, in turns the author never read. In the archival paper, two of those fixes came from Claude's memory and went in as fact. The low delegation, high warrant authors left out what they could not verify. Where Claude's correction of a planted error could not be checked against the source, they kept the claim out of the paper, while the same unverified corrections appear as fact in the high delegation, low warrant papers.

### What went wrong

The runs had the following problems, each handled as described.

- **A runner crash.** A simulated author's reply ran out of room mid-prompt, and the runner stopped. Replies now have more room, and a cut-off prompt is refused and resent. The crashed runs were run again.
- **A data allowance.** Four archival runs scheduled on one day exhausted the data source's daily allowance, and two runs fell short (one wrote no paper, and one covered too few articles). Both were run again on later days.
- **Two authors outside their cells.** The first qualitative-study low delegation, high warrant run landed in high delegation, and the first low delegation, low warrant run in high warrant. I tightened their instructions, and both reruns landed in their cells. The first runs are kept, set aside.
- **A prompt too large for the model.** One archival run cached 3,469 data downloads, whose previews came to 2.5 million tokens. Reader 0.13.4 caps the previews at 500,000 characters, and that run was read with it.
- **Who did what, in one transcript.** In one archival run, the transcript shows Claude's background download as the author's hand change. No code relies on it, so the run's cell does not change.

### Limits

Each simulated author wrote each paper once. The authors were simulated, the work was done by Claude, and the reader is also Claude. There is no answer key, so the codes are the reader's own, and each planted error's fate is a reading of the record and the paper by a separate Claude session, checked against the planted list.

**Cost.** The reader cost $73.11 on the API for the twelve runs, from $3.02 to $15.75 per paper.

## A7. What AI-text detectors see in the same papers

This appendix compares AI-text detectors with the disclosure, the comparison proposal §1 draws when it says detectors ask how much of the text a machine wrote. I scored the twelve demonstration papers and four versions of a published, human-written article with two commercial detectors.

### What was scored

Pangram (model 4.1) and GPTZero (model of 2026-10-07) scored the body text of sixteen documents on October 19. Twelve were the demonstration papers. The other four were versions of one published, single-authored management journal article whose accepted manuscript predates ChatGPT.
- The accepted manuscript
- The journal's own copy edit
- Two copy edits by Claude (Opus 5.5), one following a journal copy editor's brief and one told only "Copy edit this."

### Results

| Text | Pangram | GPTZero |
|:-|:-|:-|
| The accepted manuscript | Human, 0% AI | Human, 0% |
| The journal's copy edit | Human, 0% AI | Human, 0% |
| Claude's copy edit, journal brief | Human, 0% AI | Human, 1% |
| Claude's copy edit, "Copy edit this." | Human, 0% AI | Human, 6% |
| Twelve demonstration papers | AI on all twelve (47% to 99% AI) | AI on ten, human on two |

Claude's plain copy edit cut or changed 23% of the original's words of body text, as much as the journal's copy editor did, and both detectors still read it as human. The detectors flagged the demonstration papers whatever the author's cell. The two papers GPTZero read as human are qualitative studies, which quote the oral histories at length.

### What the comparison shows

Claude typed the simulated papers by design, so the detectors' verdicts on them say little on their own. Set beside the article, the results show that detectors answer who typed the text. They read a human paper that AI copy edited heavily as human, and they cannot tell apart four papers that their disclosures place in four different cells.

### Limits

The comparison rests on one human-written article and on one run per text per detector, on one day, and both vendors change their models. Only body text was scored. GPTZero's first response for one paper came back cut off and was run again. The texts themselves cannot be shared, so the share of words each copy edit changed cannot be checked from the review copy, although the detectors' scores can.

## A8. Running the plugin in Codex

This appendix describes how the plugin runs in Codex CLI, OpenAI's coding agent, which the proposal names alongside Claude Code. It covers how the plugin is set up there, its live test, and two items still open, which Stage 2 addresses (A12). In Stage 1, reviewers' hands-on path uses Claude Code.

### How it works

The same plugin works in Codex CLI, which reads Claude Code's plugin files. The author adds the plugin's marketplace and the plugin, then approves its hooks once in Codex's `/hooks` screen. Codex plugins cannot add slash commands, so the author types each command as a plain message (e.g., `warrant:attest` or `warrant:disclosure`). An adapter (`plugin/warrant/scripts/adapters.py`) translates Codex's hook events into the logger's format, so both tools write the same record (A1). Codex's file edits arrive as patches, and the adapter reads the edited files from each patch's headers.

### The live test (October 16)

Recording worked once the plugin's post-tool hook was turned on in `/hooks`, which Codex leaves off at first. The Codex reader ran a full disclosure of the reviewer guide's sample project in 3 minutes on my account. The current plugin includes the fixes from the test. Setup tells Codex users to turn the hook on, messages name Codex and OpenAI's model, and the disclosure's header names the model that read it.

### Open items

- **Codex's sandbox.** The sandbox blocks two of the disclosure's own steps, saving the author's consent and calling Codex as the reader. Until the plugin's hook does those steps itself, as it already does saves, a Codex user runs the disclosure with the sandbox opened for that session.
- **The Codex reader.** It has not yet been scored against the test runs that validated Claude's reader, and its disclosures say so in their header.

Gemini CLI's events are already handled by the same adapter, and its extension moves to Stage 2 (A12).

## A9. Privacy, consent, and withholding

This appendix describes how the plugin handles private material, which supports the ethics paragraph of proposal §5 (the author keeps the record, decides what to share, and can withhold private passages). It covers what stays on the author's computer, what is sent where and with whose consent, and the commands that keep text out of what others see.

**What stays local.** The record stays in the author's project and, when the author uses GitHub, in a private repository. Data files are kept out of the record and off GitHub by default. Setup writes a list of data folders and file types (such as `data/`, `raw/`, `.dta`, `.sav`, `.parquet`) into the project's ignore file, and the author deletes a line to record that kind of file. Files over 25 MB are always left out.

**What is sent where.** The AI tool sends the author's prompts and the files it reads to its provider, as it always does. The disclosure sends the finished work and the record to the provider of the project's tool, by the path the author chose, which is Anthropic through the subscription or the API, or OpenAI for Codex. The first disclosure in each copy says this and asks the author to agree before anything is sent. The answer is remembered and recorded, every later disclosure starts with a one-line reminder, and it asks again if the provider or the path changes.

**Withholding.** `/warrant:withhold` finds entries by a word or a turn number and shows the numbered matches to the author only, never to the AI, so the text is not copied into new parts of the record. The author confirms by number or `all`, and the search's own prompt is withheld along with what it found. The list of withheld entries is a file the next save keeps, and nothing is deleted. Withheld text stays out of what others see. The review copy leaves it out, and each disclosure's own files (the saved transcript and the paper trail) show "[withheld]" in its place. The reader still reads everything, so coding is unaffected, and a code that rests on a turn with withheld text says so in its basis.

**Brainstorming.** `/warrant:brainstorm` labels a session's turns as brainstorming. The record keeps them as usual, and the disclosure sets them aside (A4, rule 10).

**Memory.** An author who does not want the AI's memory notes in the record can turn their capture off for a copy (`/warrant:setup memory off`). The record then says capture was off.

**What a hash does not hide.** A withheld prompt's hash stays in the log. Anyone can hash a short, predictable prompt such as "yes" and compare, so withholding protects only text that cannot be guessed.

## A10. The review copy

This appendix describes the copy of this repository that reviewers receive, which holds the prototype and the evidence for proposal §3. It lists what the copy holds and every way it differs from the original for blind review.

### What the copy holds

The review copy is a new repository made from this one by a script, `release/release.py`, which is not part of the plugin. It holds no history from this repository. It contains the following.
- The plugin and its tests
- The two preregistered tests, with their runs, readings, and scores (A5)
- The twelve demonstrations, with each run's full record, disclosure, and paper trail (A6)
- The detectors' results (A7)
- A reviewer guide and a small sample project for trying the plugin
- This proposal and appendix, the script that draws proposal Figures 1–3, and `check.py` (A11)
- This proposal's own disclosure and paper trail, as reports

Its start page, `index.html`, links every demonstration's disclosure and paper trail. Its README sets out four levels of review (reading, checking without a model, rerunning the reader, and trying the tool), with what each shows, needs, and takes.

The copy leaves out this repository's own record. The proposal prints that record's final fingerprint, and the full record is released after review, so the fingerprint can then be checked against it.

### How the copy differs from the original

For blind review, the copy differs from this repository only in the following ways.
- **Run records.** The computer's username, a GitHub account, and an email address are replaced. Python's cache files are left out, and one tool output that lists folder names on the author's computer is withheld (A9). Every hash that follows is recomputed, so each record still verifies, and each commit keeps its author, dates, and message. Given the original records, `release/check_copy.py` remakes each one and confirms that the copy matches.
- **The demonstrations' disclosures and paper trails** are drawn again from their saved codes, with no model rerun, so they show the new fingerprints. Each fingerprints its record as saved. The originals named one more line, logged when the disclosure command was typed after the last save, which no save kept.
- **Third-party data** in the records, such as the bibliographic records the archival papers study, is kept as downloaded.
- **The copy's own files** replace the author's name, and the checklists lose source notes that would identify the author, so their hashes differ from those saved with each run.
- **The detectors' results** for the published article keep only each detector's verdict and scores (A7).

Before the copy is final, the script searches every file, and every object in every record, for the author's name and accounts, and stops if it finds any outside the third-party data. The editors make the copy available to reviewers.

## A11. Where each number in the proposal comes from

This appendix lists every number the proposal reports, where it comes from, and how to check it. In the last column, "check" means running `python3 check.py` at the root of the review copy, which recomputes the row and prints pass or fail. It needs only git and Python 3.

| Section | Claim | Source | How to check |
|:-|:-|:-|:-|
| §3 | The second test: twelve runs, 725 units in the key | `tests/scripted2/RESULTS.md`; the key in `tests/scripted2/labels/` | check |
| §3 | κ of 0.71 to 0.78 on the three primary codes, against a bar of 0.6 | `tests/scripted2/reader-runs/score.md` | check (`score.py score`) |
| §3 | The reader found 94% to 96% of the key's units | the same | check |
| §5 | OpenAI's model read the first test at κ of 0.66 to 0.79 | `tests/scripted/reader-runs/RESULTS.md` | check (`tests/scripted/score.py score`) |
| §3 | Three papers, four authors each, seven planted errors per paper | `tests/longdemo/papers/RESULTS.md`; each paper's `plants.md` | check |
| §3 | Every author landed in its cell | each run's saved codes (`disclosure/codes.json`) | check (applies the cell rule) |
| §3 | Each run's record is intact | each run's bundle | check (`verify_log.py` in a clone). Hashes were recomputed after names were replaced, and one text is withheld (A10) |
| §3 | The high delegation, low warrant papers were free of all 21 planted errors | `tests/longdemo/papers/RESULTS.md` | A Claude subagent judged each error's fate from the record and the paper. check shows that reading but cannot recompute it |
| §3 | $3 to $16 to read a full-length paper through the API | `tests/longdemo/papers/RESULTS.md` (cost column) | check shows the saved costs. Rerunning needs an API key |
| §3 | The proposal's own disclosure, 113 judgment calls (25 made by the author, 88 handed over and all 88 changed or accepted) and 125 verifiable claims (116 checked) | the disclosure (`draft/disclosure/disclosure.html`) | Read its counts |
| §3 | Its record, 2,011 turns, and its fingerprint (the commit, 10,462 events, and the last line's hash) | the disclosure's header | Check against the full record once it is released after review (A10) |
| §3 | It was read in 24 pieces, in 46 minutes and $110 through the API | the run's saved record (`reader-run.json`, `status.json`) | Check against the run record once it is released after review (A10) |
| §3 | A disclosure took 5 to 12 minutes on a small project | The second test's 24 saved runs, 4.6 to 12.2 minutes each (`tests/scripted2/reader-runs/`, each run's `reader-run.json`) | Time a run yourself (levels 3–4) |
| §3 | About 20 minutes from install to a first disclosure | `reviewer/GUIDE.md`; a run on a newly set-up Mac | Follow the guide (level 4) |
| Figure 2 | The two disclosures' numbers | the two runs' `disclosure/` folders | check (redraws each from its saved codes and compares) |
| §5 | More than half the key was fixed before the runs (389 of 725) | `tests/scripted2/RESULTS.md`; the key's source for each unit | check |
| Table 1 | CRediT's 14 roles; STM's 9 categories | NISO (2022), STM (2025) | Outside the copy |

### Other results in this appendix

The appendix's other results can be reproduced as follows.

| Result | Where | How to reproduce |
|:-|:-|:-|
| Rerunning the second test's reader | `tests/scripted2/` | `score.py read api` or `score.py read claude-code`, then `score.py score` (the API path is billed) |
| A demonstration's disclosure | `tests/longdemo/runs/<run>/disclosure/` | `python3 plugin/warrant/scripts/render.py <that folder>`, from the saved codes with no model calls |
| A demonstration's paper trail | the same folder, with the run's bundle | Clone the bundle, then `python3 plugin/warrant/scripts/trail.py <folder> <clone>` |
| Detector scores | `analyses/detectors/` | `python3 detect.py table` prints the saved results; rerunning needs each vendor's key, and the article's texts, which aren't in the copy (A7) |
| Figures 1–3 | `draft/figures/` | `python3 draft/figures/make_figures.py`, with Chrome installed |
| The plugin's own tests | `tests/` | `bash tests/test_plugin.sh` and `bash tests/test_multiauthor.sh` |
| The run records are their originals with only the documented changes | the original records, held by the editors | `python3 release/check_copy.py <original> <copy>` (A10) |

A model's reading varies from run to run, since current models take no temperature setting. Rerunning the reader therefore gives close but not identical codes, which is why the first test reports two further runs (A5).

## A12. What Stage 2 adds to the tool

This appendix lists the build work for Stage 2. Most of it extends the tool, the second step in proposal §4, and the rest supports the other two steps (author checks on real projects with coauthors, and depositing disclosures). The first item, a reader for long projects, would also let a record as long as this proposal's own be read at once rather than in pieces (proposal §3).

- **Reading long projects.** The reader reads the whole record at once when it fits. A record too long for one read is read in pieces (reader 0.14.1). Each piece holds a group of 25 calls and claims with the turns from 20 before to 5 after where its text was written and up to 10 more that quote it, in full, and only the author's side of every other turn. This proposal's own record, 1,444 turns, was the first read this way, in 11 pieces, 41 minutes, and $49.85 through the API. Because every piece repeats the author's side of the whole record, the cost climbs with the record's length, and the pieces stop fitting at two to three times this length. Stage 2 builds a reader that reads the record once, so the cost follows the paper's calls instead of the record's length, with the aim of a disclosure cheap enough to run on every draft. It will be held to the same bar against the answer keys before it is used on longer records.
- **Chat tools.** Work done in a chat window leaves no trace in the record today (A1). Stage 2 extends recording to chat-based AI tools.
- **More agents.** Gemini CLI, whose events the adapter already handles, and Antigravity.
- **The AI's text between tool calls**, which the record does not keep today (A1).
- **Windows.** The plugin runs on Mac for Stage 1.
- **Codex for reviewers and users.** Moving the disclosure's blocked steps into the plugin's hook (A8), scoring the Codex reader on the second test, and adding Codex steps to the reviewer guide. For Stage 1, reviewers' hands-on path uses Claude Code.
- **Coauthors.** A second real author making attested saves, and a disclosure for each coauthor, for the projects in the first step of proposal §4.
- **Depositing disclosures.** A command that sends a disclosure and its fingerprint to a third party such as OSF or Zenodo for a dated copy and a DOI, the start of the registry in the third step of proposal §4.
- **Prompting for warrant.** An optional mode the author chooses, which never asks (as now), asks at the final save, or asks at every save. When it asks, the tool lists the handed-over calls the author has not changed or okayed, so the author can take them up before saving. The disclosure states the mode and marks which calls were warranted when asked.
- **Confidence in each call and claim.** An exploratory measure, separate from warrant, of how far a reader can rely on each call or claim, built from what the record shows and shown in the paper trail. For a claim, it records whether the claim was checked against its source, by whom, and whether it changed after the check. For a call, it records whether alternatives were weighed, whether a reason was given, and whether the call matches the preregistration. A low score should predict errors, which the demonstrations' planted errors and the author checks in proposal §4 can test.

## References

ACM (2020) Artifact review and badging, version 1.1. Association for Computing Machinery. https://www.acm.org/publications/policies/artifact-review-and-badging-current

Appelbaum M, Cooper H, Kline RB, Mayo-Wilson E, Nezu AM, Rao SM (2018) Journal article reporting standards for quantitative research in psychology: The APA Publications and Communications Board task force report. *American Psychologist* 73(1):3–25. https://doi.org/10.1037/amp0000191

Barker M, Chue Hong NP, Katz DS, Lamprecht AL, Martinez-Ortiz C, Psomopoulos F, Harrow J, Castro LJ, Gruenpeter M, Martinez PA, Honeyman T (2022) Introducing the FAIR Principles for research software. *Scientific Data* 9:622. https://doi.org/10.1038/s41597-022-01710-x

DellaVigna S, Pope D (2018) What motivates effort? Evidence and expert forecasts. *Review of Economic Studies* 85(2):1029–1069. https://doi.org/10.1093/restud/rdx033

Harmon D (2026) Journal AI policies: What 92 journals say about generative AI, for authors and for reviewers. Version of October 1, 2026. https://derekharmon.com/ai/policies

JOSS (n.d.) Review checklist. *Journal of Open Source Software*. https://joss.readthedocs.io/en/latest/review_checklist.html

Levitt HM, Bamberg M, Creswell JW, Frost DM, Josselson R, Suárez-Orozco C (2018) Journal article reporting standards for qualitative primary, qualitative meta-analytic, and mixed methods research in psychology: The APA Publications and Communications Board task force report. *American Psychologist* 73(1):26–46. https://doi.org/10.1037/amp0000151

NASA History Office (n.d.) Space Transportation System Recordation Oral Histories. https://www.nasa.gov/history/history-publications-and-resources/oral-histories/sts-recordation-oral-histories/
