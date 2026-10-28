#!/usr/bin/env python3
"""Tools for the after-run labels (README.md here).

    python3 tests/scripted2/labels/tools.py transcripts    # one full transcript per run
    python3 tests/scripted2/labels/tools.py spotcheck      # draw the author's random tenth
    python3 tests/scripted2/labels/tools.py check [RUN …]  # validate the label files

transcripts: writes transcripts/<task>-<cell>.txt from each run's bundle: the
record as the reader's transcript shows it, but with nothing shortened, and
with brainstorm turns shown in full and marked, since the labels apply rule
10 (only turns the reader can see certify a call) knowing what the turns
held.

spotcheck: from the labels Claude applied by precedent, draws a random
tenth (rounded up) with the seed fixed in the preregistration, and writes
spotcheck.md for the author: each label, the precedent it cites, and its basis in
the record, with a column for his verdict.
"""
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST = HERE.parent
REPO = TEST.parent.parent
sys.path.insert(0, str(TEST))
sys.path.insert(0, str(REPO / "plugin" / "warrant" / "scripts"))
from run import TASKS, CELLS  # noqa: E402

SEED = 20261017  # fixed in the preregistration, before any label exists
SHARE = 0.10


def bundles():
    out = {}
    for task in TASKS:
        for cell in CELLS:
            found = sorted((TEST / "runs").glob(f"{task}-{cell}-*.bundle"))
            if found:
                out[f"{task}-{cell}"] = found[-1]
    return out


def transcripts():
    import reader
    reader.REPLY_CAP = reader.OUTPUT_CAP = reader.DIFF_CAP = reader.INSTRUCTION_CAP = 10 ** 9
    reader.TRANSCRIPT_BUDGET = 10 ** 12
    (HERE / "transcripts").mkdir(exist_ok=True)
    for name, bundle in bundles().items():
        base = Path(tempfile.mkdtemp(prefix=f"wd-labels-{name}-"))
        project = base / "project"
        subprocess.run(["git", "clone", "-q", str(bundle), str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "fetch", "-q", str(bundle), "refs/provenance/*:refs/provenance/*"],
                       check=True)
        _, turns, _ = reader.load_record(project)
        for t in turns:
            if t.get("brainstorm"):
                t["brainstorm"] = False
                t["prompt"] = "[LABELED BRAINSTORMING: the reader sees only a placeholder for this turn]\n" + t["prompt"]
        (HERE / "transcripts" / f"{name}.txt").write_text(reader.transcript(project, turns, []) + "\n")
        shutil.rmtree(base)
        print(f"transcripts/{name}.txt")


def spotcheck():
    pool = []
    for path in sorted(HERE.glob("*.json")):
        for u in json.loads(path.read_text())["units"]:
            if u.get("labeled_by") == "Claude, by precedent":
                pool.append((path.stem, u))
    if not pool:
        sys.exit("No labels applied by precedent yet.")
    k = math.ceil(SHARE * len(pool))
    drawn = random.Random(SEED).sample(pool, k)
    lines = ["# Spot-check of labels applied by precedent", "",
             f"*Drawn by `tools.py spotcheck`: {k} of {len(pool)} labels, seed {SEED}, as preregistered. "
             "The author marks each one agree, or gives the code he'd use; the number he'd change is reported.*", "",
             "| # | Run | Unit | Row | Label | Precedent | Basis | The author |", "| -: | :- | :- | :- | :- | :- | :- | :- |"]
    for i, (run, u) in enumerate(drawn, 1):
        code = " ".join(x for x in (u.get("discretion"), u.get("certification")) if x)
        lines.append(f"| {i} | {run} | {u['id']} {u['label']} | {u['row']} | {code} | {u.get('precedent')} | "
                     f"{u.get('basis', '')} | |")
    (HERE / "spotcheck.md").write_text("\n".join(lines) + "\n")
    print(f"spotcheck.md: {k} of {len(pool)}")


DISCRETION = {"kept", "given", "taken"}
JUDGMENT = {"changed", "elaborated and okayed", "okayed", "ignored", "wasn't notified"}
CLAIMS = {"you checked it against the source", "tool checked, you confirmed",
          "tool checked, you didn't see the result", "no check", "wasn't notified"}
LABELED_BY = {"planted", "Claude, by precedent", "Claude, new kind", "The author"}


def check(names=None):
    """Each label file's fields and codes are valid, and every quote is found,
    word for word, in that run's finished work."""
    problems = 0
    for name, bundle in bundles().items():
        path = HERE / f"{name}.json"
        if names and name not in names or not path.exists():
            continue
        base = Path(tempfile.mkdtemp(prefix=f"wd-check-{name}-"))
        subprocess.run(["git", "clone", "-q", str(bundle), str(base / "p")], check=True)
        squash = lambda t: " ".join(t.split())
        units, ids, found = json.loads(path.read_text())["units"], set(), []
        for u in units:
            where = f"{name} {u.get('id')}"
            for field in ("id", "kind", "row", "label", "anchors", "discretion", "certification", "basis", "labeled",
                          "labeled_by", "precedent"):
                if field not in u:
                    found.append(f"{where}: no {field}")
            if u.get("id") in ids:
                found.append(f"{where}: repeated id")
            ids.add(u.get("id"))
            if u.get("kind") == "decision":
                if u.get("discretion") not in DISCRETION:
                    found.append(f"{where}: discretion {u.get('discretion')!r}")
                want = {None} if u.get("discretion") == "kept" else JUDGMENT
                if u.get("certification") not in want:
                    found.append(f"{where}: certification {u.get('certification')!r} with {u.get('discretion')}")
            elif u.get("kind") == "claim":
                if u.get("discretion") is not None or u.get("certification") not in CLAIMS:
                    found.append(f"{where}: claim codes {u.get('discretion')!r}, {u.get('certification')!r}")
            else:
                found.append(f"{where}: kind {u.get('kind')!r}")
            if u.get("labeled_by") not in LABELED_BY:
                found.append(f"{where}: labeled_by {u.get('labeled_by')!r}")
            if u.get("labeled_by") == "Claude, by precedent" and not u.get("precedent"):
                found.append(f"{where}: no precedent cited")
            if not u.get("anchors"):
                found.append(f"{where}: no anchors")
            for a in u.get("anchors") or []:
                f = base / "p" / a.get("file", "")
                if not f.is_file() or squash(a.get("quote", "")) not in squash(f.read_text(errors="replace")):
                    found.append(f"{where}: quote not found in {a.get('file')}: {a.get('quote', '')[:60]!r}")
        shutil.rmtree(base)
        problems += len(found)
        print(f"{name}: {len(units)} units, {len(found)} problems")
        for line in found[:40]:
            print("   ", line)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        check(sys.argv[2:])
    {"transcripts": transcripts, "spotcheck": spotcheck}.get(sys.argv[1] if len(sys.argv) > 1 else "",
                                                             lambda: sys.exit(__doc__))()
