#!/usr/bin/env python3
"""The reader: list the units in a project's finished work, trace each one
through the record, and code who made each call and how it was certified.

    reader.py <project> --work memo.md analysis/ output/ [--out DIR] [--locate-only]
              [--map provenance/finished-work.md] [--label "Draft, not attested"]

<project> is a copy of a project with its record: the log in provenance/log,
the snapshots under refs/provenance, and the finished work at HEAD. --work
names the finished work (files or folders), as mapped by the author.

Four steps:
1. Locate (model). Reads only the finished work and the checklists, and lists
   each unit: a decision (judgment) or a checkable claim (right answer), with
   its checklist row and exact quotes that anchor it in the work. Then
   places (model): every other place each unit appears in the work, added to
   its anchors as restatements.
2. Trace (mechanical). Searches the snapshots for each anchor and finds the
   turns that added or changed it, who made the change (Claude in a turn, the
   author between turns, or material saved before the record began), and any
   earlier file it was copied from.
3. Code (model). Reads the record as a numbered transcript and codes each
   unit, citing turns: discretion and certification for decisions, one
   certification code for claims.
4. Assemble (mechanical). Writes units.json, codes.json, disclosure.md and
   reader-run.json (model, token use, cost, fingerprint) to --out.

The model is called with the API key in the macOS Keychain item
"warranted-delegation-anthropic", never ANTHROPIC_API_KEY, which would bill
Claude Code sessions to the API; or, with --backend claude-code, through
headless Claude Code on the author's own subscription, with no key. Runs vary: current models take no
temperature setting.
"""
import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
import render  # noqa: E402
import trace_numbers  # noqa: E402
import typed_by  # noqa: E402
import verify_log  # noqa: E402
import backends  # noqa: E402

READER_VERSION = "0.14.1"
# 0.7 is the plugin's copy, run by /warrant:disclosure. It adds --map (the
# author's finished-work map, printed in the disclosure with every other file
# listed as outside it) and --label (draft or final). Coding is unchanged from
# 0.6, the version scored in tests/scripted/reader-runs/; that frozen copy
# stays in provenance/reader.py. 0.8 adds --packs: the locate step sees the
# spine and only the checklist packs the author's map names (DECISIONS.md,
# Oct 7); without --packs it sees every pack, as 0.6 did. 0.9 draws the
# disclosure with render.py, as disclosure.md and disclosure.html, in the two
# rows designed Oct 7. 0.10 adds the traced-numbers line (trace_numbers.py) and
# who typed it (typed_by.py), outside the two rows. 0.11 credits a person with
# text they wrote in a prompt that the tool put in the manuscript (typed_by.py).
# Coding is unchanged through 0.11. 0.12 is the fixed reader (DECISIONS.md,
# Oct 12 and 15), to be frozen with its own preregistration: a places step
# adds every other place each unit appears, marked "restates"; the transcript
# shows the instructions and skills the record captured, labeled by whose
# they are, and sets brainstorm turns aside as placeholders; coding rules 9
# (instructions) and 10 (set-aside turns) are new; and --backend claude-code
# runs every model call through headless Claude Code with no API key.
# 0.12 passed its preregistered test on both paths (tests/scripted2/
# RESULTS.md). 0.12.1 raises one output limit, the places step's, from 32,000
# to 128,000 tokens, after a full-length paper's 176 units outgrew it (Oct 16,
# the long demonstration's reread); what the model is asked and how it codes
# are unchanged from 0.12. 0.13 adds the Codex and Gemini backends
# (backends.py), for projects that use those tools (DECISIONS.md, Oct 16);
# the Claude paths are unchanged. 0.13.1 shows a PDF and other binary files by
# name only, as images already were: a PDF passed the old test (a zero byte in
# the first 4 KB) and was read as text (DECISIONS.md, Oct 16). How units are
# coded is unchanged. 0.13.2 names the Codex or Gemini model in the
# disclosure's header, which named Claude's (Oct 16, the Codex live test).
# 0.13.3: who typed it no longer counts a disclosure's saved copy of the
# manuscript as text a person added, which credited the manuscript to people
# after a second disclosure (the same test). 0.13.4 shows data files' first
# lines up to 500,000 characters in all, filling from the folders with the
# fewest data files, and counts the rest by folder: an archival run cached
# 3,469 OpenAlex responses in its data, and their previews came to 2.5 million
# tokens, past the model's limit (Oct 17). Of the earlier demonstrations, only
# one passed 270,000 (a qualitative run of Oct 17, since replaced, at 887,000);
# what the rest showed the model is unchanged, and so is how units are coded.
# 0.13.5 saves the paper's title with the run, for the redesigned disclosure
# and paper trail (DECISIONS.md, Oct 22). How units are coded is unchanged.
# 0.14 reads a record too long to read at once in pieces (DECISIONS.md,
# Oct 23): each batch of units gets the turns around where its text was
# written in full, and only the author's side of every other turn, with a
# note at the top of the record saying so. A record that fits is read whole,
# exactly as before. A first use, not yet validated against a key.
# 0.14.1 also shows in full, in each piece, the latest turns that quote six
# words in a row of one of its units' text (up to 10 per unit), so a check
# made far from where the text was written stays in view (DECISIONS.md,
# Oct 28): the second draft of Oct 27 read the author's okays but not the
# checks they answered. A piece too long for one unit drops those turns before
# narrowing its window, so it never shows less than 0.14 did. Records that fit
# are read whole, as before, and how units are coded is unchanged.
MODEL = "claude-opus-5-5"
KEYCHAIN_ITEM = "warranted-delegation-anthropic"
# USD per million tokens, Claude Opus 5.5 (checked 2026-10-06): input,
# 5-minute cache write, cache read, output.
PRICES = {"input_tokens": 4.0, "cache_creation_input_tokens": 5.0,
          "cache_read_input_tokens": 0.20, "output_tokens": 20.0}
CHECKLISTS = ["checklists/judgment-decisions.md", "checklists/checkable-claims.md"]
PACK_HEADINGS = {"quantitative": "## Quantitative pack", "experiments": "## Experiments pack",
                 "qualitative": "## Qualitative pack", "theory": "## Theory pack", "tool": "## Tool pack"}
REPLY_CAP = 8000
OUTPUT_CAP = 400
DIFF_CAP = 2000
INSTRUCTION_CAP = 12000  # characters of one instruction file or skill shown to the coder
TRANSCRIPT_BUDGET = 400_000  # characters; past this, replies far from any traced turn are left out
BATCH = 25
WINDOW = (20, 5)  # turns before and after each traced turn, in full, when the record is read in pieces
QUOTE_WORDS = 6  # in pieces, a turn that quotes this many words in a row of a unit's text is shown in full too
QUOTED_CAP = 10  # the latest this many such turns per unit
# The reader codes calls and claims, not raw data: a data file (in the map's
# data slot, or a data format) is shown by its first lines only. Recording the
# data put 15 MB of OpenAlex JSON into a finished work, Oct 7.
DATA_FORMATS = {".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".feather",
                ".dta", ".sav", ".rds", ".rdata", ".pkl", ".h5", ".xml", ".gz", ".zip"}
DATA_PREVIEW = 4000  # characters
DATA_BUDGET = 500_000  # characters of data previews in all; past this, data files are counted, not shown
PLACES_BATCH = 60  # units per call in the places step; the finished work is cached between calls
PLACES_CAP = 128000  # output tokens per places call; a full paper outgrew 32,000 (Oct 16)
LOCATE_CAP = 128000  # output tokens for the unit list; an 8–10 page paper outgrew 32,000 (Oct 7)
DATA_PATHS = []  # the map's data slot, set in main()

DISCRETION = ["kept", "given", "taken"]
JUDGMENT = ["changed", "elaborated and okayed", "okayed", "ignored", "wasn't notified"]
RIGHT_ANSWER = ["you checked it against the source", "tool checked, you confirmed",
                "tool checked, you didn't see the result", "no check", "wasn't notified"]

LOCATE = """You are the reader for warranted delegation, a disclosure of who made the
calls in a piece of AI-assisted research and how the author certified what
the AI tool did. Your job in this step is only to LIST the units in the
finished work. You will not see the record of how the work was made, and you
must not code anything.

The finished work is the paper plus everything its reported results depend
on (code, data, generated tables). The two checklists below define the units:

- A DECISION (judgment) is a call the finished work embodies that could have
  gone another way. Each decision belongs to one row of the judgment-decisions
  checklist.
- A CHECKABLE CLAIM (right answer) is anything in the finished work that a
  source can settle. Each belongs to one row of the checkable-claims
  checklist.

Rules for listing:
1. Use only the spine rows and the pack rows that fit this work.
2. Rows marked (each) give one unit per instance: each reference entry, each
   robustness check, each sentence that describes a cited work.
3. A results table counts as ONE checkable claim for its numbers (row QV1).
   A number stated in the text counts on its own.
4. A decision is listed once even if it shows up in several places (for
   example, in the code and in the methods section); give each place as an
   anchor.
5. Leave out wording, grammar, and formatting: who typed the text is labor,
   not a call.
6. Anchors are quotes copied EXACTLY from the finished work, character for
   character, each from a single line where possible, and short (under 200
   characters). Give the file each quote is from. Anchor analysis decisions
   in the code where you can, and also in the text that reports them.
7. Leave out decisions the work does not embody. A path not taken is not a
   unit.
8. Grain, for rows where it matters:
   - S8: one unit per table or figure.
   - QM2: one unit per main result interpreted, not one per sentence of the
     interpretation.
   - QA7 and QA8: one unit per separate model, test, or diagnostic the work
     reports. Statistics reported from a model already listed (confidence
     intervals, standardized coefficients, effect sizes) belong to that
     model; their numbers are checkable claims (QV1), not decisions.

Return every unit."""

PLACES = """You are the reader for warranted delegation, a disclosure of who made the
calls in a piece of AI-assisted research. Units have already been listed
from the finished work, each with its anchors. Your job in this step is only
to find, for each unit, EVERY OTHER place in the finished work where the
same call or claim appears: stated again, summarized, or embodied again. For
example, a modeling choice can appear in the code, the methods, the
introduction, the abstract, a table note, and the conclusion. Do not list new
units, and do not code anything.

Rules:
1. A place is a quote copied EXACTLY from the finished work, character for
   character, from a single line where possible, and short (under 200
   characters), with the file it is from.
2. Give a place only if it states or embodies this unit's call or claim, not
   one that only mentions its topic.
3. Leave out the unit's own anchors.
4. A unit that appears nowhere else gets an empty list.

Return every unit you are given, by its id."""

CODE = """You are the reader for warranted delegation, a disclosure of who made the
calls in a piece of AI-assisted research and how the author certified what
the AI tool did. In this step you CODE units already listed from the
finished work, using the record of how the work was made.

The record is a numbered transcript of turns. In each turn, the author typed
a prompt, the tool (Claude) acted with tool calls, and Claude replied.
Between turns, the author may have changed files by hand; those changes are
shown. "/attest" lines are the author's signed saves; a sentence after
/attest is the author's own statement, for example of a check done off the
record. Material "in the author's first save, before the record began" is
the author's by attestation only. For each unit you also get a trace: the
turns whose work added or changed its anchors, and any earlier file the text
was copied from. The trace is mechanical and reliable about WHERE text came
from; you judge WHO made the call and HOW it was certified.

The record also shows the instructions Claude worked under, as captured.
Blocks headed "Instructions in force from T..." give the text of the
author's own instructions, the project's, and Claude's memory notes; a turn
shows any skill Claude used or command the author typed. Each is labeled
with whose it is. A turn marked SET ASIDE is one the author labeled
brainstorming: you see only which files Claude changed in it.

Codes for a DECISION:
- discretion:
  - kept: the author made the call. Their prompt specified it, or it comes
    from text the author supplied.
  - given: the author handed the call to the tool, by name ("pick the
    controls") or as part of a request that needed it.
  - taken: the tool made the call outside what was asked.
- certification, only when the discretion is given or taken:
  - changed: the author overrode or modified the tool's call, by a prompt or
    by a hand edit.
  - elaborated and okayed: the author accepted it and gave a reason.
  - okayed: the author accepted it explicitly without a reason.
  - ignored: a reply told the author about the call, and the author never
    responded to it.
  - wasn't notified: no reply ever told the author about the call.

Codes for a CHECKABLE CLAIM (one code):
- you checked it against the source: the author says they checked this
  claim against its source, in a prompt or an /attest sentence.
- tool checked, you confirmed: the tool checked it, the check's output is in
  the record, and the author then confirmed reading it.
- tool checked, you didn't see the result: the tool checked it, asked or
  not, but the author never confirmed reading the result. This includes a
  check reported in a reply the author never responded to.
- no check: nobody checked it, and it is the author's, or part of what the
  author asked for.
- wasn't notified: nobody checked it, Claude added it beyond what was asked
  (it belongs to a call you would code taken), and no reply ever mentioned
  it. This marks where the tool went beyond.

Coding rules:
1. An open request hands over every call inside it. "Pick whatever approach
   you think is best" makes each call needed to fulfill it given, not taken.
   Taken is a call outside what was asked, such as a figure when only a table
   was asked for. Extra analyses, checks, or content that the request did
   not need are taken.
2. Text the author supplies keeps the calls in it, such as the synthesis and
   the sources it cites, as long as the finished work uses it as written. If
   Claude changed what it claims, that change is Claude's call: taken, unless
   the author asked for the change. A call written out in the author's text is
   kept; a call the author's question or notes only point toward, such as how
   to measure a construct the question names, is given.
3. A reference list alone keeps the literature but not the citing: which
   source backs which claim is given, unless the author's own text or prompt
   sets it.
4. A call handed over and then overridden by the author is given, then
   changed, not kept.
5. Accepting without a reason is okayed, whether for a single call ("Use your
   outline") or a whole list at once ("Keep them"), or a "Looks good" after a
   reply that described the call. It covers only what the author was shown. A
   reason counts only for the calls it is about: "Keep X, because... Keep the
   rest" makes X elaborated and okayed and the rest okayed.
6. A results table counts once for its numbers. It takes the weakest code of
   any part of it: it counts as checked only if the check covered the whole
   table.
7. A reply tells the author about a call if it mentions the call, even in
   passing; so does an item on a list of decisions Claude gives. A bare
   /attest, with no sentence, is a signed save, not a response: it neither
   okays a call nor confirms a check.
8. When several codes apply, the strongest counts (except tables, rule 6).
9. A call settled in advance by instructions counts as made by whoever wrote
   them. A call that the author's own instructions or the project's settle,
   or a skill or command the author or the project keeps, is kept: the
   author made it in advance. A memory note Claude wrote counts as the
   author's when it records the author's own direction ("the author
   prefers...", "the author decided..."); a note that records only Claude's
   own view settles nothing. A call settled by a skill someone else wrote,
   such as a plugin's, is handed over, as to Claude: given if the author
   asked for the skill or the work it does, taken if Claude used it on its
   own. Name the skill in the basis.
10. Code from the turns you can see. A set-aside turn shows no direction and
   no reply: a call whose only trace is Claude's change in a set-aside turn
   is handed over (given if a turn you can see asked for it, taken
   otherwise), and only turns you can see can certify it.

What counts as a check, and whose:
- A check compares a claim with its source: rerunning the code and comparing
  the output with the reported number, looking a reference up, reading the
  cited work. Producing a number in the first place is not a check of it.
- A check counts only if the record shows it: a tool call that compares the
  claim with its source or looks the source up. A reply saying something was
  checked, with no such tool call, is not a check, because the record cannot
  verify it.
- The author confirms a tool's check by responding to the reply that
  reported it, whether specifically ("I've read the results") or generally
  ("Looks good"). A check reported in a reply the author never responded to
  was not confirmed.
- An /attest sentence counts only for the claims it names. "The results
  table matched" covers that table's numbers, not the text describing them
  or other numbers in the text.

When one check, statement, or acceptance covers several units, code those
units alike.

Judge from what the record shows, not from whether the work is good. Code
the presence of a reason, never its quality. Cite the turns you relied on
(for example "T3, T7") and quote the few words that decided each code.
Say how confident you are. Return a code for every unit you are given. For
a checkable claim, set discretion to "none"; for a decision the author kept,
set certification to "none"."""

def obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props),
            "additionalProperties": False}


UNITS_SCHEMA = obj({"units": {"type": "array", "items": obj({
    "id": {"type": "string", "description": "U1, U2, ..."},
    "kind": {"type": "string", "enum": ["decision", "claim"]},
    "row": {"type": "string", "description": "Checklist row ID, such as QA4 or V1"},
    "label": {"type": "string", "description": "A short name for this unit"},
    "anchors": {"type": "array", "items": obj({"file": {"type": "string"}, "quote": {"type": "string"}})},
})}})

PLACES_SCHEMA = obj({"places": {"type": "array", "items": obj({
    "id": {"type": "string"},
    "anchors": {"type": "array", "items": obj({"file": {"type": "string"}, "quote": {"type": "string"}})},
})}})

CODES_SCHEMA = obj({"codes": {"type": "array", "items": obj({
    "id": {"type": "string"},
    "discretion": {"type": "string", "enum": DISCRETION + ["none"],
                   "description": "Decisions only; 'none' for a checkable claim"},
    # Without the repeat of "wasn't notified", which headless Claude Code's schema check rejects.
    "certification": {"type": "string", "enum": list(dict.fromkeys(JUDGMENT + RIGHT_ANSWER + ["none"])),
                      "description": "'none' for a decision the author kept"},
    "turns": {"type": "string", "description": "Turns relied on, such as 'T2, T5'"},
    "basis": {"type": "string", "description": "The few words in the record that decided the codes"},
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
})}})
EFFORT = "high"
HEADLESS = "claude-code"  # the backend that runs through headless Claude Code, with no API key
HEADLESS_TIMEOUT = 60 * 60


# The record

def git(project, *args, check=True):
    result = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True)
    if check and result.returncode:
        raise SystemExit(f"git {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def load_record(project):
    """Return the events of every log, the turns, and which event first
    recorded each snapshot. Each turn carries what the record captured about
    the instructions Claude worked under (instruction files in force from
    that turn, skills used in it, a slash command's file) and whether the
    author labeled it brainstorming."""
    events = []
    for log in sorted((project / "provenance" / "log").glob("*/events.jsonl")):
        events += [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    text_dir = project / "provenance" / "log" / "text"

    def side(sha):
        path = text_dir / f"{sha}.txt"
        return path.read_text(errors="replace") if sha and path.exists() else None

    turns, by_prompt, first_seen = [], {}, {}
    session = {}  # captured at session start, for the session's first turn
    for e in events:
        if e.get("snapshot") and e["snapshot"] not in first_seen:
            first_seen[e["snapshot"]] = e
        kind, pid = e.get("event"), e.get("prompt_id")
        # The earliest events (Oct 1, 2026) predate prompt IDs; they belong to
        # the turn they follow in the log.
        current = by_prompt.get(pid) if pid else (turns[-1] if turns else None)
        if kind == "SessionStart":
            session = {k: e[k] for k in ("instructions", "memory_capture", "plugins") if k in e}
        elif kind == "UserPromptSubmit":
            prompt = side(e.get("prompt_sha256")) or ""
            turn = {"n": len(turns) + 1, "prompt_id": pid, "ts": e.get("ts"),
                    "prompt": prompt, "before": e.get("snapshot"), "after": None,
                    "reply": None, "tools": [], "skills": [],
                    "brainstorm": e.get("brainstorm") is True,
                    "plugins": session.get("plugins"),
                    "instructions": e.get("instructions", session.get("instructions")),
                    "memory_capture": e.get("memory_capture", session.get("memory_capture")),
                    "command_file": e.get("command_file")}
            for item in turn["instructions"] or []:
                item["text"] = side(item.get("sha256"))
            for item in [turn["command_file"]] if turn["command_file"] else []:
                item["text"] = side(item.get("sha256"))
            session = {}
            turns.append(turn)
            if pid:
                by_prompt[pid] = turn
        elif kind == "PostToolUse" and current:
            what = e.get("command") or " ".join(e.get("paths") or [])
            out = side(e.get("output_sha256")) or ""
            current["tools"].append({"tool": e.get("tool"), "what": what, "output": out[:OUTPUT_CAP]})
            if e.get("skill"):
                current["skills"].append(dict(e["skill"], text=side(e["skill"].get("sha256"))))
        elif kind == "Stop" and current:
            current["reply"] = side(e.get("response_sha256"))
            current["after"] = e.get("snapshot")
    return events, turns, first_seen


def turn_of_snapshot(commit, first_seen, turns):
    """Who made the change that a snapshot first recorded."""
    e = first_seen.get(commit)
    if e is None:
        return {"by": "unknown"}
    n = next((t["n"] for t in turns if t["prompt_id"] == e.get("prompt_id")), None)
    if e.get("event") == "Stop":
        return {"by": "Claude", "turn": n}
    if n == 1:
        return {"by": "the author's first save, before the record began", "turn": n}
    return {"by": "the author, between turns", "turn": n}


# Step 1: locate

def work_files(project, work):
    tracked = git(project, "ls-files", "--", *work).split("\n")
    return [f for f in tracked if f and (project / f).is_file()]


def checklist_text(c, packs=None):
    """A checklist with its introduction, the spine, and only the named packs.
    Without packs, the whole checklist, as the scored reader saw it."""
    text = (TOOL / c).read_text()
    if not packs:
        return text
    parts = re.split(r"(?m)^(?=## )", text)
    for p in packs:
        if not any(part.startswith(PACK_HEADINGS[p]) for part in parts):
            raise SystemExit(f"{c} has no {p} pack.")
    keep = [part for part in parts if not part.startswith("## ") or part.startswith("## Spine")
            or any(part.startswith(PACK_HEADINGS[p]) for p in packs)]
    return re.sub(r"(?m)^\*\d+ row types:.*\n?", "", "".join(keep))


def file_text(project, f):
    """A finished-work file as the model sees it: in full, or a data file's first lines."""
    path = project / f
    raw = path.read_bytes()
    if trace_numbers.is_binary(path, raw):  # a PDF, an image, a spreadsheet, or another binary file
        return f"[{path.suffix.lstrip('.') or 'binary'} file, {len(raw):,} bytes; not text, not shown]"
    text = raw.decode(errors="replace")
    if not is_data(project, f):
        return text
    if len(text) <= DATA_PREVIEW:
        return text
    return (text[:DATA_PREVIEW].rsplit("\n", 1)[0] + f"\n[data file: {len(text):,} characters, {text.count(chr(10)):,} lines; "
            "only the first lines are shown]")


def is_data(project, f):
    path = project / f
    return path.suffix.lower() in DATA_FORMATS or any(f == d or (d.endswith("/") and f.startswith(d)) for d in DATA_PATHS)


def work_parts(project, files):
    """The finished work as the model sees it, one part per file. Data previews stop at
    DATA_BUDGET, filled from the folders with the fewest data files first, so a folder of
    cached downloads gives way before a results table; the rest are counted by folder."""
    texts = {f: file_text(project, f) for f in files}
    folder = {f: f.rsplit("/", 1)[0] + "/" if "/" in f else "./" for f in files}
    data = [f for f in files if is_data(project, f)]
    count = {}
    for f in data:
        count[folder[f]] = count.get(folder[f], 0) + 1
    shown, used = set(), 0
    for f in sorted(data, key=lambda f: (count[folder[f]], f)):
        if used + len(texts[f]) <= DATA_BUDGET:
            shown.add(f)
            used += len(texts[f])
    parts, more = [], {}
    for f in files:
        if f in data and f not in shown:
            n, size = more.get(folder[f], (0, 0))
            more[folder[f]] = (n + 1, size + (project / f).stat().st_size)
        else:
            parts.append(f'<file path="{f}">\n{texts[f]}\n</file>')
    parts += [f'<files folder="{d}">[{n:,} more data files in this folder, {size:,} bytes; not shown]</files>'
              for d, (n, size) in more.items()]
    return parts


def locate(client, project, work, usage, packs=None):
    files = work_files(project, work)
    parts = work_parts(project, files)
    lists = [f'<checklist path="{c}">\n{checklist_text(c, packs)}\n</checklist>' for c in CHECKLISTS]
    message = ("\n\n".join(lists) + "\n\nThe finished work:\n\n" + "\n\n".join(parts) +
               "\n\nList every unit in this finished work.")
    result = call(client, LOCATE, [{"type": "text", "text": message}], UNITS_SCHEMA, LOCATE_CAP, usage)
    units = result["units"]
    for u in units:
        for a in u["anchors"]:
            a["found"] = find_anchor(project, a)
    places(client, project, parts, units, usage)
    return files, units


def places(client, project, parts, units, usage):
    """Every other place each unit appears in the finished work (DECISIONS.md,
    Oct 12), added to its anchors marked "restates", so a call stated in the
    introduction and made in the methods is found in both."""
    prefix = [{"type": "text", "text": "The finished work:\n\n" + "\n\n".join(parts),
               "cache_control": {"type": "ephemeral"}}]
    for i in range(0, len(units), PLACES_BATCH):
        batch = [{k: u[k] for k in ("id", "kind", "row", "label")} |
                 {"anchors": [{"file": a["file"], "quote": a["quote"]} for a in u["anchors"]]}
                 for u in units[i:i + PLACES_BATCH]]
        ask = {"type": "text", "text": f"Find every other place for each of these {len(batch)} units:\n"
                                       + json.dumps(batch, indent=1)}
        found = {p["id"]: p["anchors"] for p in call(client, PLACES, prefix + [ask], PLACES_SCHEMA,
                                                      PLACES_CAP, usage)["places"]}
        for u in units[i:i + PLACES_BATCH]:
            have = [squash(a["quote"]) for a in u["anchors"]]
            for a in found.get(u["id"], []):
                q = squash(a["quote"])
                if not q or any(q in h or h in q for h in have):
                    continue
                have.append(q)
                u["anchors"].append({"file": a["file"], "quote": a["quote"], "restates": True,
                                     "found": find_anchor(project, a)})


def squash(text):
    return " ".join(text.split())


def find_anchor(project, anchor):
    path = project / anchor["file"]
    if not path.is_file():
        return False
    return squash(anchor["quote"]) in squash(path.read_text(errors="replace"))


# Step 2: trace

def needle(project, anchor):
    """The longest line of the quote that appears exactly in the file."""
    text = (project / anchor["file"]).read_text(errors="replace")
    lines = sorted((l.strip() for l in anchor["quote"].splitlines()), key=len, reverse=True)
    for line in lines:
        if len(line) >= 12 and line in text:
            return line
    quote = anchor["quote"].strip()
    return quote if quote in text else None


def trace(project, units, turns, first_seen):
    refs = git(project, "for-each-ref", "--format=%(refname)", "refs/provenance",
               "refs/provenance-remote").split()
    for u in units:
        u["trace"] = []
        for a in u["anchors"]:
            if not a.get("found"):
                continue
            hit = needle(project, a)
            if not hit or not refs:
                continue
            commits = git(project, "log", "--reverse", "--format=%H", "-S", hit, *refs,
                          "--", a["file"], check=False).split()
            for c in commits:
                parent = git(project, "rev-parse", "--verify", "-q", f"{c}^", check=False).strip()
                now = count(project, c, a["file"], hit)
                before = count(project, parent, a["file"], hit) if parent else 0
                step = {"file": a["file"], "text": hit[:80], **turn_of_snapshot(c, first_seen, turns),
                        "change": "added" if before == 0 else "removed" if now == 0 else "changed"}
                if before == 0 and parent:
                    elsewhere = git(project, "grep", "-l", "-F", hit, parent, "--", ".",
                                    ":(exclude)provenance/log", check=False).split()
                    copied = [p.split(":", 1)[1] for p in elsewhere if p.split(":", 1)[1] != a["file"]]
                    if copied:
                        step["copied_from"] = copied
                u["trace"].append(step)
    return units


def count(project, commit, path, text):
    blob = subprocess.run(["git", "-C", str(project), "show", f"{commit}:{path}"],
                          capture_output=True, text=True)
    return blob.stdout.count(text) if blob.returncode == 0 else 0


# Step 3: code

def whose(item):
    """Whose a captured instruction file or skill is, as the coder is told."""
    kind, path, name = item.get("kind"), item.get("path") or "", item.get("name") or ""
    if kind == "user":
        return "the author's own instructions (their user-level CLAUDE.md)"
    if kind in ("project", "ancestor"):
        return "the project's instructions, which the author keeps"
    if kind == "import":
        return "a file the instructions above bring in"
    if kind == "memory":
        return "a memory note Claude wrote for this project; it may record the author's own direction"
    if ":" in name:
        return f"from the plugin {name.split(':', 1)[0]}, written by that plugin's author, not by this author"
    if path.startswith("~/.claude/"):
        return "the author's own skill"
    if path:
        return "the project's own skill, which the author keeps"
    return "built into Claude Code; its text isn't on disk"


def instructions_block(t, instructions, plugins, shown):
    """What Claude was told from this turn on: instruction files new or
    changed since last shown, in full, and the plugins when they change."""
    lines = []
    for item in instructions or []:
        if item.get("sha256") in shown:
            continue
        shown[item.get("sha256")] = t["n"]
        text = (item.get("text") or "[text not in this copy of the record]")[:INSTRUCTION_CAP]
        lines.append(f"--- {item.get('path')}: {whose(item)}\n{text.strip()}")
    if t.get("memory_capture") == "off":
        lines.append("--- The author turned off capture of Claude's memory notes, so they aren't shown.")
    if plugins and plugins != shown.get("plugins"):
        shown["plugins"] = plugins
        lines.append(f"--- Plugins turned on: {', '.join(plugins)}. A plugin can add instructions the "
                     "record doesn't show.")
    if not lines:
        return None
    return (f"[Instructions in force from T{t['n']}, as the record captured them. Calls these settle are "
            "made by whoever wrote them:]\n" + "\n\n".join(lines))


def skill_lines(t, shown):
    out = []
    for item in [t["command_file"]] * bool(t.get("command_file")) + t.get("skills", []):
        used = "The author typed the command" if item is t.get("command_file") else "Claude used the skill"
        line = f"   {used} {item.get('name')}: {whose(item)}"
        sha = item.get("sha256")
        if sha and sha in shown:
            line += f" (its text is shown at T{shown[sha]})"
        elif sha:
            shown[sha] = t["n"]
            line += f". Its text:\n{(item.get('text') or '[not in this copy of the record]')[:INSTRUCTION_CAP].strip()}"
        out.append(line)
    return out


@functools.lru_cache(maxsize=None)
def hand_diff(project, before, after):
    return git(project, "diff", before, after, "--", ".", ":(exclude)provenance/log", check=False)


@functools.lru_cache(maxsize=None)
def changed_files(project, before, after):
    if not (before and after) or before == after:
        return []
    return git(project, "diff", "--name-only", before, after, "--", ".", ":(exclude)provenance/log",
               check=False).split()


def transcript(project, turns, units, full=None):
    """The record as numbered turns. Past the budget, replies and tool
    output far from every traced turn are shortened to their first lines.
    A turn the author labeled brainstorming is set aside: a placeholder
    names the files Claude changed in it, so those changes aren't read as
    the author's hand edits (DECISIONS.md, Oct 15). With full, a set of turn
    numbers, the record is a piece (0.14): those turns in full, and only the
    author's side of the rest, with a line naming the files Claude changed;
    nothing is shortened."""
    traced = {s.get("turn") for u in units for s in u.get("trace", []) if s.get("turn")}
    near = {n + d for n in traced for d in range(0, 5)}
    out, prev_after, shown = [], None, {}
    carried = {"instructions": None, "plugins": None}  # from set-aside turns, shown at the next turn
    for t in turns:
        if prev_after and t["before"] and t["before"] != prev_after:
            diff = hand_diff(project, prev_after, t["before"])
            out.append(f"[Between T{t['n'] - 1} and T{t['n']}, the author changed files by hand:]\n"
                       f"{diff[:DIFF_CAP]}")
        prev_after = t["after"] or t["before"]
        if t.get("brainstorm"):
            carried = {"instructions": t.get("instructions") or carried["instructions"],
                       "plugins": t.get("plugins") or carried["plugins"]}
            files = changed_files(project, t["before"], t["after"])
            out.append(f"T{t['n']} · SET ASIDE: the author labeled this turn brainstorming, so its prompt, "
                       "tool calls, and reply are not shown. " +
                       (f"Files Claude changed in it: {', '.join(files)}." if files else
                        "Claude changed no files in it."))
            continue
        block = instructions_block(t, t.get("instructions") or carried["instructions"],
                                   t.get("plugins") or carried["plugins"], shown)
        carried = {"instructions": None, "plugins": None}
        if block:
            out.append(block)
        side = full is not None and t["n"] not in full  # the author's side only
        prompt = t["prompt"].strip()
        if t["n"] == 1 and re.match(r"/(warrant:)?attest\b", prompt):
            files = [f for f in git(project, "ls-tree", "-r", "--name-only", t["before"], check=False).split()
                     if not f.startswith((".claude/", ".githooks/", "provenance/", ".gitignore", "install.sh"))] \
                if t["before"] else []
            out.append(f"T1 · The author's first save, before the record began. Files: {', '.join(files)}")
        elif re.match(r"/(warrant:)?attest\b", prompt):
            out.append(f"T{t['n']} · ATTEST (the author's signed save): {prompt}")
        else:
            out.append(f"T{t['n']} · AUTHOR'S PROMPT:\n{prompt}")
        if side:
            out += skill_lines({**t, "skills": []}, shown)  # the author's own command, not Claude's skills
            files = changed_files(project, t["before"], t["after"])
            out.append(f"   [Claude's side of T{t['n']} is not shown in this piece: {len(t['tools'])} tool calls, "
                       + (f"files changed: {', '.join(files)}]" if files else "no files changed]"))
            continue
        out += skill_lines(t, shown)
        for tool in t["tools"]:
            line = f"   tool {tool['tool']}: {tool['what'][:200]}"
            if tool["output"]:
                line += f"\n      output: {squash(tool['output'])[:OUTPUT_CAP]}"
            out.append(line)
        if t["reply"] is not None:
            reply = t["reply"].strip()
            out.append(f"T{t['n']} · CLAUDE'S REPLY:\n{reply[:REPLY_CAP]}")
    text = "\n\n".join(out)
    if full is None and len(text) > TRANSCRIPT_BUDGET:
        text = "\n\n".join(
            block if not re.match(r"T(\d+) · CLAUDE'S REPLY", block) or
            int(re.match(r"T(\d+)", block).group(1)) in near else block[:600] + " [shortened]"
            for block in out)
    return text


def code(client, project, files, units, turns, usage):
    record = transcript(project, turns, units)
    work = "\n\n".join(work_parts(project, files))
    prefix = [{"type": "text", "text": f"<finished_work>\n{work}\n</finished_work>\n\n"
                                       f"<record>\n{record}\n</record>",
               "cache_control": {"type": "ephemeral"}}]
    codes = {}
    todo = sorted(units, key=lambda u: (u["kind"], u["row"]))  # a row's units are coded together
    for attempt in range(3):  # ask again for any unit the model left out
        for i in range(0, len(todo), BATCH):
            batch = [{k: u[k] for k in ("id", "kind", "row", "label")} |
                     {"anchors": [{"file": a["file"], "quote": a["quote"]} for a in u["anchors"]],
                      "trace": u.get("trace", [])} for u in todo[i:i + BATCH]]
            ask = {"type": "text", "text": f"Code these {len(batch)} units, every one of them:\n"
                                           + json.dumps(batch, indent=1)}
            try:
                result = call(client, CODE, prefix + [ask], CODES_SCHEMA, 16000, usage)
            except (Exception, SystemExit) as e:  # the model's own limit decides; nothing is sent twice otherwise
                if too_long(e) and not codes and attempt == 0 and i == 0:
                    return code_in_pieces(client, project, work, units, turns, usage)
                raise
            wanted = {u["id"] for u in batch}
            codes.update({c["id"]: c for c in result["codes"] if c["id"] in wanted})
        todo = [u for u in todo if u["id"] not in codes]
        if not todo:
            break
        usage["retried_units"] = usage.get("retried_units", 0) + len(todo)
    return codes, record


def ask_for(group):
    batch = [{k: u[k] for k in ("id", "kind", "row", "label")} |
             {"anchors": [{"file": a["file"], "quote": a["quote"]} for a in u["anchors"]],
              "trace": u.get("trace", [])} for u in group]
    return {"type": "text", "text": f"Code these {len(batch)} units, every one of them:\n" + json.dumps(batch, indent=1)}


def code_in_pieces(client, project, work, units, turns, usage):
    """A record too long to read at once, read in pieces (0.14; DECISIONS.md,
    Oct 23), when the model refuses the whole record as too long: each batch
    of units is coded with its own record, the turns around where its text
    was written in full, the latest turns that quote its text in full too
    (0.14.1), and the author's side of every other turn. A piece the model
    also refuses is split; a single unit's piece drops its quoting turns, then
    narrows its window, and is tried again. The saved transcript is the whole
    record."""
    codes, done = {}, {"pieces": 0, "windows": set(), "dropped": set()}
    found = quoting(units, turns)
    todo = sorted(units, key=lambda u: (u["kind"], u["row"]))
    for attempt in range(3):
        for i in range(0, len(todo), BATCH):
            code_piece(client, project, work, units, turns, todo[i:i + BATCH], WINDOW, codes, done, usage, found)
        todo = [u for u in todo if u["id"] not in codes]
        if not todo:
            break
        usage["retried_units"] = usage.get("retried_units", 0) + len(todo)
    usage["read_in_pieces"] = {"turns": len(turns), "pieces": done["pieces"],
                               "windows": sorted(done["windows"], reverse=True),
                               "quoting": [QUOTE_WORDS, QUOTED_CAP]}
    if done["dropped"]:
        usage["read_in_pieces"]["quoting_dropped"] = len(done["dropped"])
    return codes, transcript(project, turns, units, full={t["n"] for t in turns})


def quoting(units, turns):
    """For each unit, the turns that quote QUOTE_WORDS words in a row of its
    text, in what the reader is shown of them: the prompt, the reply, and the
    tool lines (0.14.1). Case, punctuation, and markup are ignored. A turn set
    aside as brainstorming is never shown, so it never counts."""
    words = lambda text: re.findall(r"[a-z0-9]+", text.lower())
    wanted = {}
    for u in units:
        for a in u.get("anchors", []):
            w = words(a.get("quote", ""))
            for i in range(len(w) - QUOTE_WORDS + 1):
                wanted.setdefault(" ".join(w[i:i + QUOTE_WORDS]), set()).add(u["id"])
    found = {}
    for t in turns:
        if t.get("brainstorm"):
            continue
        w = words("\n".join([t["prompt"], (t["reply"] or "")[:REPLY_CAP]]
                            + [f"{x['what'][:200]}\n{x['output']}" for x in t["tools"]]))
        for i in range(len(w) - QUOTE_WORDS + 1):
            for uid in wanted.get(" ".join(w[i:i + QUOTE_WORDS]), ()):
                found.setdefault(uid, set()).add(t["n"])
    return found


def code_piece(client, project, work, units, turns, group, window, codes, done, usage, found=None, quoted=True):
    before, after = window
    traced = sorted({s["turn"] for u in group for s in u.get("trace", []) if s.get("turn")})
    full = {n for t in traced for n in range(t - before, t + after + 1)}
    extra = set()
    if quoted and QUOTED_CAP:
        for u in group:
            extra |= set(sorted((found or {}).get(u["id"], set()) - full)[-QUOTED_CAP:])
    record = piece_note(full | extra, turns, bool(extra)) + transcript(project, turns, units, full | extra)
    prefix = [{"type": "text", "text": f"<finished_work>\n{work}\n</finished_work>\n\n<record>\n{record}\n</record>",
               "cache_control": {"type": "ephemeral"}}]
    try:
        result = call(client, CODE, prefix + [ask_for(group)], CODES_SCHEMA, 16000, usage)
    except (Exception, SystemExit) as e:
        if not too_long(e):
            raise
        if len(group) > 1:
            half = len(group) // 2
            code_piece(client, project, work, units, turns, group[:half], window, codes, done, usage, found, quoted)
            code_piece(client, project, work, units, turns, group[half:], window, codes, done, usage, found, quoted)
            return
        if extra:
            done["dropped"].add(group[0]["id"])
            code_piece(client, project, work, units, turns, group, window, codes, done, usage, found, False)
            return
        if window != (0, 0):
            code_piece(client, project, work, units, turns, group, (before // 2, after // 2), codes, done, usage,
                       found, False)
            return
        raise SystemExit(f"Even one unit's piece of the record is too long to read ({group[0]['id']}).")
    done["pieces"] += 1
    done["windows"].add(window)
    wanted = {u["id"] for u in group}
    codes.update({c["id"]: c for c in result["codes"] if c["id"] in wanted})


def too_long(e):
    """The model refused a request as longer than it can read."""
    return bool(re.search(r"prompt is too long|too many (input )?tokens|exceeds? the (model's )?context", str(e), re.I))


def piece_note(full, turns, quoted=False):
    shown = sorted(n for n in full if 1 <= n <= len(turns))
    spans, start = [], None
    for k, n in enumerate(shown):
        start = n if start is None else start
        if k + 1 == len(shown) or shown[k + 1] != n + 1:
            spans.append(f"T{start}" if start == n else f"T{start}–T{n}")
            start = None
    return ("[This record is shown in part, because the whole of it is too long to read at once. "
            f"Shown in full: {', '.join(spans) or 'no turns'}, the turns around where these units' text was written"
            + (" and the latest turns that quote it" if quoted else "") + ". "
            "Every other turn shows only the author's side (the prompt, any /attest, and hand edits) and a line "
            "naming the files Claude changed. Claude's replies and tool calls in those turns are not shown, so "
            "their absence is not evidence that Claude did nothing then.]\n\n")


# The model

def client_from_keychain():
    key = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_ITEM, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        raise SystemExit(f'No API key in the Keychain item "{KEYCHAIN_ITEM}".')
    import anthropic
    return anthropic.Anthropic(api_key=key)


def call(client, system, content, schema, max_tokens, usage):
    if client == HEADLESS:
        return call_headless(system, content, schema, max_tokens, usage)
    if client == backends.CODEX:
        return backends.call_codex(system, content, schema, max_tokens, usage)
    if client == backends.GEMINI:
        return backends.call_gemini(system, content, schema, max_tokens, usage)
    start = time.time()
    with client.messages.stream(model=MODEL, max_tokens=max_tokens, system=system,
                                output_config={"effort": EFFORT,
                                               "format": {"type": "json_schema", "schema": schema}},
                                messages=[{"role": "user", "content": content}]) as stream:
        response = stream.get_final_message()
    for k in PRICES:
        usage[k] = usage.get(k, 0) + (getattr(response.usage, k, 0) or 0)
    usage["calls"] = usage.get("calls", 0) + 1
    usage["seconds"] = usage.get("seconds", 0) + round(time.time() - start)
    if response.stop_reason == "max_tokens":
        raise SystemExit(f"The model ran out of room (max_tokens {max_tokens}).")
    return json.loads("".join(b.text for b in response.content if b.type == "text"))


def call_headless(system, content, schema, max_tokens, usage):
    """The same call through headless Claude Code on the author's own
    subscription, with no API key (DECISIONS.md, Oct 12): the reader's
    system prompt in place of Claude Code's, no tools, settings, MCP
    servers, skills, or memory, from an empty folder, with the message on
    stdin. Claude Code returns the structured output through a tool turn."""
    start = time.time()
    message = "".join(part["text"] for part in content)
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") and k != "CLAUDE_CONFIG_DIR") and k != "ANTHROPIC_API_KEY"}
    env.update(CLAUDE_CODE_DISABLE_AUTO_MEMORY="1", CLAUDE_CODE_MAX_OUTPUT_TOKENS=str(max_tokens))
    with tempfile.TemporaryDirectory(prefix="wd-reader-") as empty:
        r = subprocess.run(["claude", "-p", "--model", MODEL, "--effort", EFFORT, "--system-prompt", system,
                            "--tools", "", "--setting-sources", "", "--strict-mcp-config",
                            "--disable-slash-commands", "--no-session-persistence",
                            "--output-format", "json", "--json-schema", json.dumps(schema)],
                           input=message, capture_output=True, text=True, cwd=empty, env=env,
                           timeout=HEADLESS_TIMEOUT)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"Claude Code gave no result (exit {r.returncode}): {(r.stderr or r.stdout)[-500:]}")
    if out.get("is_error") or out.get("structured_output") is None:
        raise SystemExit(f"Claude Code reported an error: {str(out.get('result') or out)[:500]}")
    for k in PRICES:
        usage[k] = usage.get(k, 0) + ((out.get("usage") or {}).get(k) or 0)
    usage["calls"] = usage.get("calls", 0) + 1
    usage["seconds"] = usage.get("seconds", 0) + round(time.time() - start)
    usage["subscription_list_usd"] = round(usage.get("subscription_list_usd", 0) + (out.get("total_cost_usd") or 0), 4)
    return out["structured_output"]


def cost(usage):
    return round(sum(usage.get(k, 0) * p for k, p in PRICES.items()) / 1e6, 2)


# Step 4: assemble

def fingerprint(project):
    heads = []
    for log in sorted((project / "provenance" / "log").glob("*/events.jsonl")):
        n, errors, head, _ = verify_log.verify(log)
        heads.append({"log": log.parent.name, "events": n, "head": head, "verifies": not errors})
    return {"commit": git(project, "rev-parse", "HEAD").strip(), "logs": heads}


def read_map(path):
    """The author's finished-work map: 'work product: paths' lines."""
    slots = {}
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            key, _, value = line.partition(":")
            slots[key.strip().lower()] = value.strip()
    return slots


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--work", nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--locate-only", action="store_true")
    ap.add_argument("--units", type=Path, help="reuse units.json from an earlier run, skipping locate")
    ap.add_argument("--map", type=Path, help="the author's finished-work map")
    ap.add_argument("--converted", nargs="+", help="Word files converted to text for reading")
    ap.add_argument("--packs", nargs="+", choices=sorted(PACK_HEADINGS),
                    help="the checklist packs, added to the spine; without it, every pack")
    ap.add_argument("--label", help="how the disclosure is labeled: draft, attested, or final")
    ap.add_argument("--backend", choices=["api", HEADLESS, backends.CODEX, backends.GEMINI], default="api",
                    help="the API, with the key in the Keychain; headless Claude Code on the author's "
                         "subscription, with no key; or Codex or Gemini, on the author's own account")
    args = ap.parse_args()
    project = args.project.resolve()
    out = (args.out or project / "disclosure").resolve()
    out.mkdir(parents=True, exist_ok=True)

    client = client_from_keychain() if args.backend == "api" else args.backend
    usage = {}
    events, turns, first_seen = load_record(project)
    if args.map:
        DATA_PATHS[:] = [p.strip() for p in read_map(args.map).get("data", "").split(",")
                         if p.strip() and p.strip().lower() != "none" and "not in the record" not in p]
    if args.units:
        units = json.loads(args.units.read_text())["units"]
        files = work_files(project, args.work)
    else:
        files, units = locate(client, project, args.work, usage, args.packs)
    units = trace(project, units, turns, first_seen)
    (out / "units.json").write_text(json.dumps({"files": files, "units": units}, indent=1) + "\n")
    print(f"Located {len(units)} units ({sum(u['kind'] == 'decision' for u in units)} decisions) "
          f"in {len(files)} files; {sum(not any(a.get('found') for a in u['anchors']) for u in units)} unanchored.")

    run = {"reader": READER_VERSION, "backend": args.backend, "model": MODEL, "effort": EFFORT, "date": datetime.now().date().isoformat(),
           "reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "checklists_sha256": {c: hashlib.sha256((TOOL / c).read_bytes()).hexdigest() for c in CHECKLISTS},
           "work": args.work, "packs": args.packs, "label": args.label, "converted": args.converted}
    if not args.locate_only:
        codes, record = code(client, project, files, units, turns, usage)
        if "read_in_pieces" in usage:
            run["record_read"] = usage.pop("read_in_pieces")
        (out / "codes.json").write_text(json.dumps(codes, indent=1) + "\n")
        (out / "transcript.txt").write_text(record)
        finger = fingerprint(project)
        work_map, outside = None, None
        if args.map:
            work_map = read_map(args.map)
            every = [f for f in git(project, "ls-files").split("\n") if f]
            # The record and the tool's own files aren't work, finished or not.
            tool = ("provenance/", ".githooks/", ".claude/", ".claude-plugin/", "disclosure/", ".gitignore")
            outside = sorted(f for f in set(every) - set(files) if not f.startswith(tool))
        run.update(fingerprint=finger, work_map=work_map, outside=outside,
                   numbers=trace_numbers.summarize(project, work_map, files, units),
                   typed=typed_by.summarize(project, turns, work_map, files),
                   title=render.paper_title(project, work_map, files))
        if args.backend in (backends.CODEX, backends.GEMINI):  # named before drawing, so the header says which model read it
            run.update(model=usage.get("model") or f"{backends.NAMES[args.backend]}'s default model",
                       effort=backends.CODEX_EFFORT if args.backend == backends.CODEX else None)
        render.write(out, units, codes, run, files, work_map, outside, args.packs)
    run["usage"] = usage
    run["cost_usd"] = cost(usage)
    if args.backend in (backends.CODEX, backends.GEMINI):  # on the author's own account, not billed per call
        run.update(model=usage.get("model") or f"{backends.NAMES[args.backend]}'s default model", cost_usd=None,
                   effort=backends.CODEX_EFFORT if args.backend == backends.CODEX else None)
    (out / "reader-run.json").write_text(json.dumps(run, indent=1) + "\n")
    print(f"{usage.get('calls', 0)} model calls, {usage.get('seconds', 0)} s, about ${run['cost_usd']}. Output in {out}")


if __name__ == "__main__":
    main()
