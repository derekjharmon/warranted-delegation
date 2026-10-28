"""Who typed the manuscript: the tool or a person, word by word.

A mechanical step, no model (DECISIONS.md, Oct 7). Journals ask "did AI
write it?", so the disclosure says what share of the final manuscript's words
the tool typed, on a line outside its two rows: typing is labor, not
discretion, so it isn't one of the warrant measures.

How. The record keeps a snapshot of the project before and after every turn.
Text that changed during a turn was typed by the tool; text that changed
between turns, or before the record began, was typed by a person. Walking the
snapshots in order, each word of the manuscript keeps the owner of the change
that put it there, so fixing one word in a paragraph the tool wrote makes that
word, not the paragraph, a person's.

Copies. Text a person typed, anywhere in the project (before the record
began, or by hand between turns), stays theirs when the tool copies it into
the manuscript, if the copied run is at least eight words; the careful
author's hand-written paragraphs, moved into the paper by Claude, showed why
(Oct 8). So does text a person writes in a prompt ("add this sentence: ..."),
except where the prompt quotes text already in the project, so quoting the
tool's own sentence back doesn't make it theirs (Oct 8). Limits: an edit a
person makes while the tool is mid-turn counts as the tool's, and a Word file
isn't read.

    python3 typed_by.py PROJECT OUT_DIR    add the result to a reader run and redraw it
"""
import difflib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXT = {".md", ".tex", ".qmd", ".rmd", ".txt"}
MIN_RUN = 8  # words a copied run needs to keep its typist


def git_lines(project, *args):
    r = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l] if r.returncode == 0 else []


# The tool's own folders: the record, and each disclosure's copy of the
# manuscript as it was read, which a later turn would otherwise count as text
# a person added (Oct 16, the Codex live test: a second disclosure credited
# the whole memo to people).
TOOL_DIRS = ("provenance/", "disclosure/", ".claude/", ".githooks/", ".claude-plugin/")


def text_paths(paths):
    return [p for p in paths if Path(p).suffix.lower() in TEXT and not p.startswith(TOOL_DIRS)]


_grams = {}  # blob -> the eight-word runs in it, so each version of a file is read once


def blob_grams(project, blob):
    if blob not in _grams:
        r = subprocess.run(["git", "-C", str(project), "cat-file", "blob", blob], capture_output=True)
        w = r.stdout.decode(errors="replace").split() if r.returncode == 0 else []
        _grams[blob] = {tuple(w[i:i + MIN_RUN]) for i in range(len(w) - MIN_RUN + 1)}
    return _grams[blob]


def prompt_runs(project, turn):
    """Runs of words a person wrote in a prompt, less what it quotes from the
    project as it stood when the prompt was sent."""
    words = (turn.get("prompt") or "").split()
    if len(words) < MIN_RUN or not turn.get("before"):
        return []
    there = []
    for line in git_lines(project, "ls-tree", "-r", turn["before"]):
        meta, path = line.split("\t", 1)
        if text_paths([path]):
            there.append(blob_grams(project, meta.split()[2]))
    quoted = [False] * len(words)
    for i in range(len(words) - MIN_RUN + 1):
        g = tuple(words[i:i + MIN_RUN])
        if any(g in s for s in there):
            quoted[i:i + MIN_RUN] = [True] * MIN_RUN
    runs, cur = [], []
    for w, q in zip(words + [None], quoted + [True]):
        if q:
            if len(cur) >= MIN_RUN:
                runs.append(cur)
            cur = []
        else:
            cur.append(w)
    return runs


def people_runs(project, turns):
    """Runs of words people typed: every text file before the record began,
    what was added by hand between turns, and what they wrote in prompts."""
    ordered = sorted(turns, key=lambda t: t.get("ts") or "")
    runs, prev = [], None
    first = next((t["before"] for t in ordered if t.get("before")), None)
    if first:
        runs += [words_at(project, first, f) for f in text_paths(git_lines(project, "ls-tree", "-r", "--name-only", first))]
    for t in ordered:
        if prev and t.get("before") and t["before"] != prev:
            for f in text_paths(git_lines(project, "diff", "--name-only", prev, t["before"])):
                old, new = words_at(project, prev, f), words_at(project, t["before"], f)
                for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
                    if op in ("insert", "replace"):
                        runs.append(new[j1:j2])
        runs += prompt_runs(project, t)
        prev = t.get("after") or t.get("before") or prev
    return [r for r in runs if len(r) >= MIN_RUN]


def credit(block, runs):
    """Owners for words the tool put in: a person's where they copy a person's run."""
    owners = ["tool"] * len(block)
    for run in runs:
        for m in difflib.SequenceMatcher(a=block, b=run, autojunk=False).get_matching_blocks():
            if m.size >= MIN_RUN:
                owners[m.a:m.a + m.size] = ["people"] * m.size
    return owners


def words_at(project, commit, path):
    r = subprocess.run(["git", "-C", str(project), "show", f"{commit}:{path}"], capture_output=True)
    return r.stdout.decode(errors="replace").split() if r.returncode == 0 else []


def attribute(project, turns, path):
    """[(word, owner)] for the manuscript as it stands, owner 'tool' or 'people'."""
    owned, last = [], None
    runs = people_runs(project, turns)

    def step(new, owner):
        nonlocal owned, last
        if new == last:
            return
        old = [w for w, _ in owned]
        out = []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
            if op == "equal":
                out += owned[i1:i2]
            elif owner == "tool":
                out += list(zip(new[j1:j2], credit(new[j1:j2], runs)))
            else:
                out += [(w, owner) for w in new[j1:j2]]
        owned, last = out, new

    for t in sorted(turns, key=lambda t: t.get("ts") or ""):
        if t.get("before"):
            step(words_at(project, t["before"], path), "people")
        if t.get("after"):
            step(words_at(project, t["after"], path), "tool")
    final = Path(project) / path
    step(final.read_text(errors="replace").split() if final.exists() else [], "people")
    return owned


def manuscripts(work_map, files):
    named = [p.strip() for p in (work_map or {}).get("manuscript", "").split(",")
             if p.strip() and p.strip().lower() != "none"]
    chosen = ([f for f in files if any(f == n or (n.endswith("/") and f.startswith(n)) for n in named)] if named
              else [f for f in files if "/" not in f])
    return [f for f in chosen if Path(f).suffix.lower() in TEXT and not f.lower().endswith(".docx.md")]  # Word: not measured


def summarize(project, turns, work_map, files):
    per_file, tool, total = {}, 0, 0
    for f in manuscripts(work_map, files):
        owned = attribute(project, turns, f)
        t = sum(o == "tool" for _, o in owned)
        per_file[f] = {"tool": t, "people": len(owned) - t}
        tool, total = tool + t, total + len(owned)
    return {"tool_words": tool, "words": total, "files": per_file} if total else None


def main():
    sys.path.insert(0, str(HERE))
    import reader
    import render
    project, out = Path(sys.argv[1]), Path(sys.argv[2])
    u = json.loads((out / "units.json").read_text())
    run_path = out / "reader-run.json"
    run = json.loads(run_path.read_text())
    _, turns, _ = reader.load_record(project)
    run["typed"] = summarize(project, turns, run.get("work_map"), u["files"])
    run_path.write_text(json.dumps(run, indent=1) + "\n")
    render.redraw(out)
    t = run["typed"]
    print(f"Typed by the tool: {t['tool_words']} of {t['words']} words" if t else "No text manuscript to attribute.")


if __name__ == "__main__":
    main()
