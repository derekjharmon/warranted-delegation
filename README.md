# Warranted delegation: the review copy

This copy holds the prototype and the evidence behind the proposal *Warranted Delegation: An Open-Source Tool for Showing Who Stands Behind AI-Assisted Research*. The prototype is `warrant`, a plugin for Claude Code and Codex. To read the proposal, the appendix, and the twelve demonstrations' disclosures and paper trails, open [`index.html`](index.html) in a browser.

## Four ways to review it

| | What it shows | What it needs | How |
|:-|:-|:-|:-|
| **1. Read** | The proposal and appendix, and what the tool produced for twelve demonstration papers | A browser | [`index.html`](index.html) |
| **2. Check without a model** | Most of the numbers in the proposal that need no model, recomputed from the files here, and every run's record verified | git and Python 3; a few minutes | `python3 check.py` |
| **3. Rerun the reader** | The reader's codes for the second test's twelve runs, scored against the preregistered key | Claude Code on a subscription, or an Anthropic API key (billed) | [`tests/scripted2/README.md`](tests/scripted2/README.md) |
| **4. Try it** | The plugin on a small sample project, from install to a first disclosure | Claude Code, on a Mac; about 20 minutes | [`reviewer/GUIDE.md`](reviewer/GUIDE.md), or watch a pass first: [`reviewer/walkthrough.mp4`](reviewer/walkthrough.mp4) (8½ minutes) |

`check.py` prints one line per claim (Appendix A11): PASS or FAIL with what it found, or SAVED for the few results that can't be recomputed without a model or without paying again. It changes nothing in the copy.

## What's here

- `plugin/warrant/`: the plugin. `.claude-plugin/marketplace.json` lets Claude Code install it from this folder.
- `check.py`: level 2.
- `reviewer/`: the guide, the sample project, and a video of one pass, for level 4.
- `tests/scripted/` and `tests/scripted2/`: the two preregistered tests of the reader, with their scripts, keys, runs, readings, and scores (Appendix A5).
- `tests/longdemo/`: the demonstrations, with each paper's starting materials, the simulated authors' instructions, the planted errors, and the twelve runs (Appendix A6).
- `tests/test_plugin.sh` and `tests/test_multiauthor.sh`: the plugin's own tests.
- `analyses/detectors/`: the AI-text detectors' results (Appendix A7).
- `docs/record-format.md`: what a record holds.
- `draft/`: the proposal, the appendix, and the script that draws Figures 1–3.
- `release/`: how this copy was made anonymous, and the script that confirms it for anyone holding the original records.

Each run's record is a git bundle (`.bundle`). To read one, clone it and fetch its snapshots:

```
git clone tests/longdemo/runs/<run>.bundle run
git -C run fetch ../tests/longdemo/runs/<run>.bundle 'refs/provenance/*:refs/provenance/*'
python3 plugin/warrant/scripts/verify_log.py run/provenance/log/*/events.jsonl
```

## How this copy was made anonymous

Review is double-blind, so this copy differs from the author's repository in these ways, and only these.

- **Run records.** Each record had three swaps: the computer's username became `user`, a GitHub account became `anonymous.invalid`, and an email address became `author@example.invalid`. Python's cache files (`__pycache__/`) were left out, and one tool output listing folder names on the author's computer was withheld, as `/warrant:withhold` withholds text. Every hash that follows from these changes was recomputed, so each record still verifies, and each commit keeps its author, dates, and message. `release/scrub_record.py` makes the changes. Given the original records, `release/check_copy.py` remakes every record and confirms that the copy matches.
- **The demonstrations' disclosures and paper trails** were drawn again from their saved codes, with no model rerun, so they carry the new fingerprints. Each disclosure was made just after its run's last save, and typing the disclosure command logged one more line, which no save kept. Their original fingerprints therefore named a log one line longer than the record holds. Here, each fingerprints the log as saved, one event fewer, so it can be checked against its record.
- **Third-party data** in the demonstrations' records is kept as it was downloaded. The bibliographic records the archival papers study list thousands of published authors, and the oral histories the qualitative papers read mention people and places.
- **The copy's own files.** Notes that named the author now say "the author", the multi-author test's two people are Ada and Ben, and source notes that would identify the author were removed from the checklists. The checklists' hashes therefore differ from those saved with each run (`reader-run.json`), which were taken from the checklists as the runs read them.
- **The detectors' results** for the published article keep only each detector's verdict and scores, under neutral names (`analyses/detectors/README.md`).
- **Left out:** the record of making the proposal itself, and the author's working files. The proposal prints that record's final fingerprint, and the full record will be released after review. Its [disclosure](draft/disclosure/disclosure.html) and [paper trail](draft/disclosure/trail.html) are in `draft/disclosure/`, with names and other identifying details replaced.
