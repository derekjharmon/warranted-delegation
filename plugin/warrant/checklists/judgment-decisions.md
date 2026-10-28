# Judgment-decisions checklist

*Second draft by Claude, 2026-10-05, for the author to edit. Not yet adopted. Replaces `empirical-quantitative.md`. Stages for the seven rows that could sit in two stages ruled by the author, 2026-10-05. Packs for experiments, qualitative work, and theory: first draft by Claude, 2026-10-07; stages for their nine rows that could sit in two stages ruled by the author, 2026-10-07. Tool pack: first draft by Claude, 2026-10-15, accepted by the author as drafted, 2026-10-15.*

**What this list asks.** Journals ask "did AI write it?" This list asks "who made the calls in it?" Wording, grammar, spelling, translation, and formatting are left out on purpose: who typed the text is labor, not discretion. The calls inside the text (structure, interpretation, contribution, limitations) are in.

**Structure.** A **spine** of rows that applies to any paper, plus a **pack** for each type of paper. A paper takes the spine and one or more packs; a mixed-methods paper can take two. This draft has the spine and five packs: quantitative (archival or survey data); experiments, taken together with the quantitative pack the way JARS-Quant adds its Table 2 to Table 1; qualitative; theory; and tools, for papers that build research software (DECISIONS.md, Oct 12). Each pack's rows are worded to cover the kinds of paper within it, such as case studies, ethnography, and grounded theory in the qualitative pack. The tool proposes a paper's packs at its first disclosure, and the author confirms or changes them. Overlays by technique (such as network or text-as-data methods), simulation, and review papers are later packs.

**What a row is.** A type of decision that the finished work embodies and that could have gone another way. The core units of the disclosure come from these rows (decided Oct 5). Decisions the tool finds that fit no row are reported separately, labeled less certain.

**Repeatable rows.** Rows marked *(each)* occur once per instance: each exclusion rule, each hypothesis, each robustness check. Comparability holds at the level of the row.

**Anchors.** A row is located wherever it shows up in the finished work, not only in the manuscript. One decision can have several anchors, such as the cleaning code and the methods section, and still counts once.

**Codes.** Each decision gets two codes. *Discretion:* kept by you, given to the tool, or taken by the tool. *Certification,* if the tool had it: changed it · elaborated and okayed (accepted, with a reason) · okayed (accepted without saying why) · ignored · wasn't notified.

**Stage.** Each row rolls up into one of five research stages: conceptualization, research design, data preparation and analysis, presentation of results, writing and editing. The stage is fixed per row, so the roll-up is mechanical.

**Source.** "JARS" means the row follows an element of APA's JARS-Quant Table 1; "JARS-Quant T2" means its table for studies with an experimental manipulation, including Modules A and B on random and nonrandom assignment; "JARS-Qual" means APA's qualitative standards, Table 1. "Census" means it comes from an author activity in a census of journal AI policies (Harmon 2026). In the tool pack, "JOSS" is the Journal of Open Source Software's review checklist, "ACM" is ACM's artifact badges (Available, Functional, Reusable, Results Reproduced), and "FAIR4RS" is the FAIR principles for research software, by principle number. "Added" means none of them asks for it, usually because it lives in the code.

## Spine: any paper

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| S1 | Research question: the problem the paper addresses | Introduction | Conceptualization | JARS: Problem |
| S2 | Theoretical framing: the lens the argument uses | Introduction; theory section | Conceptualization | JARS: Hypotheses/aims |
| S3 | Literature positioned in: which conversations the paper joins | Introduction; reference list | Conceptualization | Census: Finding literature |
| S4 | Synthesis of prior work: how the literature is organized and what it is said to show | Literature review | Conceptualization | Census: Summarizing or synthesizing literature |
| S5 | Source for a key claim *(each)*: which work is cited in support | Manuscript text; reference list | Conceptualization | Added |
| S6 | Contribution claim *(each)* | Introduction; discussion | Conceptualization | Partly JARS: Implications |
| S7 | Argument structure: the order and organization of the paper's moves | Manuscript | Writing and editing | Census: Editing, formatting, structure |
| S8 | Presentation of results *(each figure or table)*: what is shown, and how | Figures; tables | Presentation of results | Census: Images and figures |
| S9 | Limitations and boundary conditions | Discussion | Writing and editing | JARS: Interpretation; Generalizability |

## Quantitative pack: archival or survey data

### Collection: collection instrument or script

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QC1 | Data source: which database, archive, platform, or population | Collection script; methods section | Research design | JARS: Sampling procedures |
| QC2 | Sampling frame and window: who or what is in scope, and the time period | Collection script; methods section | Research design | JARS: Inclusion/exclusion; Sampling procedures |
| QC3 | Sample size: intended size or stopping rule for primary data, or coverage for archival data | Collection script; methods section | Research design | JARS: Sample size/power/precision |
| QC4 | Measures collected: which variables or items are gathered, including ones never used | Collection script or instrument | Research design | JARS: Measures and covariates |
| QC5 | Instrument content *(each)*: item wording, scales, or prompts | Survey or interview instrument | Research design | JARS: Instrumentation |
| QC6 | Collection procedure: mode, timing, and how sources are linked at collection | Collection script; methods section | Research design | JARS: Data collection |

### Cleaning: cleaning code

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QK1 | Exclusion rule *(each)*: a rule that drops cases after collection | Cleaning code; methods section | Data preparation and analysis | JARS: Data diagnostics; Inclusion/exclusion |
| QK2 | Missing data: drop, impute, and by what method | Cleaning code | Data preparation and analysis | JARS: Data diagnostics |
| QK3 | Outliers: how they are defined and treated (winsorize, trim, keep) | Cleaning code | Data preparation and analysis | JARS: Data diagnostics |
| QK4 | Transformation *(each)*: logs, scaling, lags | Cleaning code | Data preparation and analysis | JARS: Data diagnostics |
| QK5 | Variable construction *(each)*: how an analysis variable is built from raw fields | Cleaning code | Data preparation and analysis | Added (JARS asks for definitions, not construction) |
| QK6 | Merging rules: how datasets are joined and matched | Cleaning code | Data preparation and analysis | Added |
| QK7 | Coding scheme *(each)*: the categories and decision rules for classifying text or cases | Codebook; classification code or prompt | Research design | Census: Deductive coding, classification |

### Analysis: analysis code

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QA1 | Dependent variable: which measure stands for the outcome | Analysis code; methods section | Data preparation and analysis | JARS: Measures and covariates |
| QA2 | Focal predictor *(each)*: which measure stands for the key construct | Analysis code; methods section | Data preparation and analysis | JARS: Measures and covariates |
| QA3 | Controls: which covariates are included | Analysis code; methods section | Data preparation and analysis | JARS: Measures and covariates |
| QA4 | Estimator: OLS, fixed effects, logit, multilevel, and so on | Analysis code; methods section | Research design | JARS: Analytic strategy |
| QA5 | Fixed effects and standard errors: which effects, and how errors are clustered | Analysis code | Data preparation and analysis | Added (finer than JARS asks) |
| QA6 | Inference rules: thresholds, one- or two-tailed tests, corrections for multiple tests | Analysis code; results section | Research design | JARS: Analytic strategy |
| QA7 | Robustness check *(each)* | Analysis code; results or appendix | Data preparation and analysis | Partly JARS: Analytic strategy |
| QA8 | Additional or exploratory analysis *(each)* | Analysis code; results or appendix | Data preparation and analysis | Partly JARS: Analytic strategy |

### Manuscript

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QM1 | Hypothesis *(each)* | Theory section | Conceptualization | JARS: Hypotheses/aims |
| QM2 | Interpretation of a main result *(each)* | Results; discussion | Presentation of results | JARS: Support of hypotheses; Interpretation |
| QM3 | What gets reported: which analyses appear in the paper, which go to an appendix, which are left out | Results; appendix | Presentation of results | Added |

## Experiments pack: studies with a manipulation

An experiment takes the quantitative pack and this one. The quantitative rows on sample size and stopping (QC3), measures (QC4), exclusions (QK1), and analysis apply as written; this pack adds the design of the manipulation.

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| EX1 | Conditions: which conditions are run, including the comparison condition | Materials; preregistration; methods section | Research design | JARS-Quant T2: Experimental manipulations |
| EX2 | Manipulation content *(each)*: what participants in a condition see or do (stimuli, instructions, vignettes) | Materials; methods section | Research design | JARS-Quant T2: Experimental manipulations |
| EX3 | Delivery: the setting or platform, who delivers the manipulation, how long exposure lasts, and incentives for compliance | Materials; methods section | Research design | JARS-Quant T2: Delivery, deliverer, setting, exposure |
| EX4 | Unit of assignment and analysis: what is assigned to conditions (person, team, session), and how the analysis accounts for it | Assignment code or platform settings; analysis code | Research design | JARS-Quant T2: Units of delivery and analysis |
| EX5 | Assignment procedure: how units are randomized, with any blocking or stratification; for nonrandom assignment, the rule and the steps against selection bias | Assignment code or platform settings; methods section | Research design | JARS-Quant T2, Modules A and B: Assignment method |
| EX6 | Masking: who is kept unaware of condition (participants, experimenters, coders) | Materials; methods section | Research design | JARS-Quant T2, Modules A and B: Masking |
| EX7 | Manipulation and attention checks *(each)*: which checks are included, and how their results are used | Materials; analysis code | Research design | JARS-Quant T2: Treatment fidelity |
| EX8 | Preregistration: what is registered before data collection | Preregistration | Research design | JARS: Registration information |
| EX9 | Departure from the preregistration *(each)* | Analysis code; methods section | Research design | Added |
| EX10 | Study set: which studies the paper includes, and what each later study adds (replication, mechanism, boundary) | Manuscript; preregistrations | Research design | Added |
| EX11 | Mediation or moderation test *(each)*: which are run, and how | Analysis code; results section | Data preparation and analysis | JARS-Quant T2, Module A: Statistical methods |

## Qualitative pack: interviews, fieldwork, documents, and cases

Covers interview studies, ethnography, case studies, grounded theory, and process studies. A row that doesn't fit a paper, such as protocol changes in a document study, simply has no units.

### Collection: protocol and data

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QL1 | Approach and design: the approach to inquiry (such as grounded theory, case study, ethnography, process study) and the design that follows from it | Methods section | Research design | JARS-Qual: Research design overview |
| QL2 | Selection of sites, cases, participants, or documents: the logic (purposive, theoretical, maximum variation) and the inclusion criteria | Methods section; data | Research design | JARS-Qual: Participant selection |
| QL3 | Recruitment and access: how participants or sites are reached, and any incentives | Methods section | Research design | JARS-Qual: Recruitment process |
| QL4 | Protocol content *(each)*: interview questions, observation focus, or document search terms | Protocol | Research design | JARS-Qual: Data collection |
| QL5 | Protocol change *(each)*: a change to the protocol in response to what is being found | Protocol versions; methods section | Research design | JARS-Qual: Data collection (alterations) |
| QL6 | Stopping: how many participants, cases, or documents, and when collection stops | Methods section | Research design | JARS-Qual: Recruitment process (number; rationale to halt) |
| QL7 | Recording and transcription: what is recorded, and how it is transcribed or summarized | Data; methods section | Data preparation and analysis | JARS-Qual: Recording and data transformation |
| QL8 | Researcher position: how the researchers' prior understandings, and their relationships with participants, are handled | Methods section | Research design | JARS-Qual: Researcher description; Researcher–participant relationship |

### Analysis: codebook and coding

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QL9 | Coding approach: codes set in advance or emerging from the data, and the unit coded | Codebook; methods section | Data preparation and analysis | JARS-Qual: Data-analytic strategies |
| QL10 | Code *(each)*: a code's definition and decision rules | Codebook | Data preparation and analysis | JARS-Qual: Analytic scheme; Census: Inductive or abductive interpretation; Deductive coding |
| QL11 | Who codes, and how disagreements are resolved | Codebook; methods section | Data preparation and analysis | JARS-Qual: Coders or analysts; Methodological integrity |
| QL12 | Analytic structure: how codes are grouped into themes, categories, or a data structure | Codebook; figures; findings | Data preparation and analysis | JARS-Qual: Analytic scheme development |
| QL13 | Integrity check *(each)*: member checks, triangulation, audits, or other checks added to the analysis | Methods section | Research design | JARS-Qual: Methodological integrity |

### Manuscript

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| QL14 | Finding *(each)*: a theme, category, or mechanism as stated | Findings | Presentation of results | JARS-Qual: Findings; Census: Theory development, interpreting findings |
| QL15 | Excerpts for a finding *(each finding)*: which quotes or field notes are shown in support | Findings | Presentation of results | JARS-Qual: Findings (demonstrating the analytic process) |
| QL16 | Model built from the findings: the process or theoretical model the paper proposes | Figures; discussion | Conceptualization | Census: Theory development, interpreting findings |
| QL17 | Rival interpretations: which disconfirming evidence or alternative readings are addressed | Findings; discussion | Presentation of results | JARS-Qual: Methodological integrity |

## Theory pack: papers with no original data

Covers propositional papers, process models, typologies, essays, and formal models. Framing, literature, contribution, and boundary conditions are spine rows (S2–S4, S6, S9). Review papers that report a search are a later pack.

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| TH1 | Core claim: the paper's central argument, in a sentence or two | Introduction; conclusion | Conceptualization | Census: Theory development |
| TH2 | Argument form: propositions, process model, typology, essay, or formal model | Manuscript | Conceptualization | Added |
| TH3 | Construct definition *(each)* | Theory section | Conceptualization | Census: Theory development |
| TH4 | Level of analysis | Theory section | Conceptualization | Added |
| TH5 | Premise or assumption *(each)*: what the argument takes as given | Theory section; model section | Conceptualization | Added |
| TH6 | Proposition or relationship *(each)*: what is related to what, and in which direction | Propositions; theory section | Conceptualization | Census: Theory development |
| TH7 | Mechanism *(each relationship)*: why the relationship holds | Theory section | Conceptualization | Census: Theory development |
| TH8 | Illustration *(each)*: an example, case, or vignette used to show the argument | Manuscript | Writing and editing | Added |
| TH9 | Model setup (formal models): actors, choices, payoffs, and functional forms | Model section; appendix | Research design | Added |

## Tool pack: papers that build a research tool

The calls behind a piece of research software, and behind the evidence that it works. A paper whose tool is validated with numbers also takes the quantitative pack, and the experiments pack's preregistration rows (EX8, EX9) apply when the validation is preregistered. A unit fits one row: a tool's validation takes the tool rows (TL11–TL15), not EX10.

### The tool

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| TL1 | Purpose and scope: what the tool is for, whom it serves, and what it leaves out on purpose | README; paper | Conceptualization | JOSS: Statement of need |
| TL2 | What it takes in *(each kind of input)*: what the tool records or reads, and what it deliberately doesn't | Code; documentation | Research design | Added (cf. FAIR4RS R1.2, provenance) |
| TL3 | Method *(each core step)*: how the tool turns its inputs into outputs (rules, scoring, prompts) | Code; methods section | Research design | JOSS: Functionality |
| TL4 | Models and services *(each)*: which model, API, or library the tool depends on, at which version and settings | Code; configuration | Research design | FAIR4RS R2 (references to other software); ACM: Functional |
| TL5 | Output: what the tool reports, in what form, and what it leaves out of the report | Code; sample output; documentation | Presentation of results | Added |
| TL6 | Failure handling *(each)*: what the tool does when a step fails (stop, skip, warn, fail closed) | Code | Research design | ACM: Functional |
| TL7 | Privacy and consent: what the tool sends where, what stays local, and what users can withhold | Code; documentation | Research design | Added |
| TL8 | Setup: how users install and start the tool, and what it changes on their machine | Installer or setup code; README | Research design | JOSS: Installation instructions; ACM: Reusable |
| TL9 | Test design *(each suite)*: what is tested, how, and what counts as passing | Test scripts | Data preparation and analysis | JOSS: Automated tests; ACM: Functional |
| TL10 | Availability: license, where the code lives, and how versions are identified | License file; repository; paper | Writing and editing | JOSS: License; FAIR4RS F1, A1, R1.1; ACM: Available |

### Evidence that it works

| ID | Decision | Usually anchored in | Stage | Source |
|:-|:-|:-|:-|:-|
| TL11 | Validation design: the cases the tool is tested on (real or simulated tasks, planted errors), and why they make a fair test | Test scripts; preregistration | Research design | ACM: Results Reproduced; Added |
| TL12 | Answer key: who labels the truth, how, and blind to what | Labels; preregistration | Research design | Added |
| TL13 | Matching rule: how the tool's output is paired with the key | Scoring code; preregistration | Data preparation and analysis | Added (DECISIONS.md, Oct 12) |
| TL14 | Agreement statistic and bar: which statistic, and what result counts as passing | Scoring code; preregistration | Data preparation and analysis | Added (DECISIONS.md, Oct 12) |
| TL15 | Settling disagreements: how disagreements among the key's coders are resolved | Labels; preregistration | Data preparation and analysis | Added (DECISIONS.md, Oct 12) |

*85 row types: 9 in the spine, 24 in the quantitative pack, 11 in the experiments pack, 17 in the qualitative pack, 9 in the theory pack, 15 in the tool pack.*
