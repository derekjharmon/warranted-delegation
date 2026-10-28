#!/usr/bin/env python3
"""Play one run of the second preregistered test as the simulated author.

    python3 tests/scripted2/run.py TASK CELL [--dry-run]
    python3 tests/scripted2/run.py smoke

TASK is schools, agreement, or rand; CELL is low-high, low-low, high-low, or
high-high (delegation, then warrant). The design is README.md; each script
is TASK/CELL.md, its planted key TASK/key.md.

--dry-run prints every step exactly as it would be sent, and runs nothing.

smoke checks the machinery with three short prompts: the methods-kit skill
is found and its text captured, a brainstorm turn is labeled, the project's
CLAUDE.md is captured as the project's and nothing of the user's is, one
recorder logs each prompt, and the record verifies. It saves nothing here
and deletes its project.

A real run, as in the first test (tests/scripted/run.py), except where noted:
1. Refuses to start unless the scripts, keys, starting materials, the
   methods-kit plugin, this runner, and the warrant plugin are committed
   unchanged, so the run uses the attested versions.
2. Makes a throwaway project outside this repository, signed by "Simulated
   Author", sets it up with the warrant plugin (/warrant:setup, GitHub
   skipped), copies in the task's starting materials (its notes and the
   author's CLAUDE.md), and saves them with /attest, so the record shows
   they are the author's and existed before Claude did anything.
3. Plays the script in one headless Claude Code session, loading copies of
   the warrant plugin and the methods-kit plugin made at the start of the
   run (--plugin-dir). The session loads no user-level settings,
   instructions, plugins, MCP servers, or memory: a plain Claude Code plus
   the two plugins and the project's own CLAUDE.md.
4. Between turns, makes the author's hand edits, sends the brainstorm
   commands, and runs the author's own checks. If a check fails, or Claude's
   work has no place for a hand edit, the run stops.
5. Verifies the record, saves the whole history as
   tests/scripted2/runs/TASK-CELL-<date>.bundle with a .json of run details,
   and deletes the throwaway project. A failed run keeps its project for
   diagnosis and prints the path.

Claude runs on the logged-in Claude Code account, not the reader's API key.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PLUGIN = REPO / "plugin" / "warrant"
METHODS_KIT = HERE / "methods-kit"
# Each task's main document (where the hand edit goes and the reference
# list is), the heading the author writes under, and its finished work.
TASKS = {
    "schools": {"doc": "memo.md", "limits": "Limitations", "work": ["memo.md", "analysis/", "output/"]},
    "agreement": {"doc": "README.md", "limits": "Limits", "work": ["README.md", "agree.py", "tests/", "validation/"]},
    "rand": {"doc": "memo.md", "limits": "Limitations", "work": ["memo.md", "plan.md", "analysis/", "output/"]},
}
CELLS = ("low-high", "low-low", "high-low", "high-high")
TEXT_OUTPUTS = {".md", ".csv", ".txt", ".tex", ".json", ".html"}
MODEL = "claude-opus-5-5"
AUTHOR = ("Simulated Author", "simulated.author@example.invalid")
STEP_TIMEOUT = 30 * 60
CLAUDE_FLAGS = [
    "--model", MODEL,
    "--setting-sources", "project,local",
    "--strict-mcp-config",
    "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash", "WebFetch", "WebSearch", "Skill",
    "--output-format", "json",
]
SMOKE = [
    {"id": "S1", "kind": "prompt", "text": "Use the methods-kit robustness skill, and tell me in one sentence "
     "which two checks it calls for. Don't run anything."},
    {"id": "S2", "kind": "command", "text": "/warrant:brainstorm"},
    {"id": "S3", "kind": "prompt", "text": "Write the word idea to idea.txt."},
    {"id": "S4", "kind": "command", "text": "/warrant:brainstorm"},
    {"id": "S5", "kind": "attest", "text": "/warrant:attest"},
]
TOOL_PATHS = ["tests/scripted2", ":(exclude)tests/scripted2/runs", "plugin/warrant"]


class RunFailed(Exception):
    pass


# Reading the scripts

def parse_script(task, cell):
    """Return the steps of TASK/CELL.md as dicts with id, kind, and text.
    Text comes only from the blockquotes, so the notes around them are
    never sent."""
    steps = []
    for block in re.split(r"^### ", (HERE / task / f"{cell}.md").read_text(), flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        step_id, _, label = heading.partition(" · ")
        kind = {"Prompt": "prompt", "Attest": "attest", "Command": "command", "Hand edit": "hand edit"}.get(label)
        if kind is None and label.startswith("The author's own checks"):
            kind = "author checks"
        if kind is None:
            raise RunFailed(f"{task}/{cell}.md step {step_id}: unknown kind {label!r}")
        text = join_quote([line[1:].removeprefix(" ") for line in body.splitlines() if line.startswith(">")])
        if kind == "hand edit" and not text:
            same = re.search(r"same as ([A-C]-LH\d+)", body, re.I)
            if not same:
                raise RunFailed(f"{task}/{cell}.md step {step_id}: hand edit has no text")
            text = next(s["text"] for s in parse_script(task, "low-high") if s["id"] == same.group(1))
        if kind != "author checks" and not text:
            raise RunFailed(f"{task}/{cell}.md step {step_id}: no text")
        step = {"id": step_id, "kind": kind, "text": text}
        if kind == "author checks":
            listed = re.search(r"^Runner checks: (.+)$", body, re.M)
            if not listed:
                raise RunFailed(f"{task}/{cell}.md step {step_id}: no Runner checks line")
            step["checks"] = [c.strip() for c in listed.group(1).split(",")]
            unknown = [c for c in step["checks"] if c not in ("rerun", "tests") and not c.startswith("crossref:")]
            if unknown:
                raise RunFailed(f"{task}/{cell}.md step {step_id}: unknown checks {unknown}")
        steps.append(step)
    return steps


def join_quote(lines):
    """Join a blockquote's wrapped lines. Numbered items start new lines,
    and their indented continuations join the item."""
    out = []
    for line in lines:
        if not line.strip():
            continue
        if re.match(r"\d+\. ", line):
            out.append(line)
        elif out and (line.startswith(" ") or not re.match(r"\d+\. ", out[-1])):
            out[-1] += " " + line.strip()
        else:
            out.append(line)
    return "\n".join(out)


# Running

def sh(args, cwd, env=None, timeout=600, check=True, input=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                            timeout=timeout, input=input)
    if check and result.returncode:
        raise RunFailed(f"{' '.join(map(str, args[:3]))} failed: {result.stderr.strip()[-500:]}")
    return result


def claude(text, project, env, session, first):
    start = time.time()
    # The run's copies of the two plugins sit beside its project.
    args = ["claude", "-p", text, *CLAUDE_FLAGS,
            "--plugin-dir", str(project.parent / "plugin"), "--plugin-dir", str(project.parent / "methods-kit")]
    args += ["--session-id", session] if first else ["--resume", session]
    result = sh(args, project, env=env, timeout=STEP_TIMEOUT, check=False)
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        out = {}
    return {"exit": result.returncode, "seconds": round(time.time() - start), "is_error": out.get("is_error"),
            "turns": out.get("num_turns"), "cost_usd": out.get("total_cost_usd"),
            "stderr": result.stderr.strip()[-500:] or None}


def head(project):
    return sh(["git", "rev-parse", "HEAD"], project, check=False).stdout.strip() or None


def attest(text, project, env, session, first):
    before = head(project)
    info = claude(text, project, env, session, first)
    body = sh(["git", "log", "-1", "--format=%B"], project, check=False).stdout
    if head(project) == before or f"Attested-by: {AUTHOR[0]}" not in body:
        raise RunFailed(f"{text!r} made no attested save")
    info["commit"] = head(project)
    return info


def command(text, project, env, session, first):
    """A plugin command, such as /warrant:brainstorm: the hook answers it, so
    Claude takes no turn."""
    info = claude(text, project, env, session, first)
    if info["turns"] not in (0, None) or info["exit"]:
        raise RunFailed(f"{text!r} reached Claude instead of the hook: {info}")
    return info


def hand_edit(text, project, task):
    """Put the author's paragraph under the main document's limits heading."""
    doc, heading = TASKS[task]["doc"], TASKS[task]["limits"]
    path = project / doc
    if not path.exists():
        raise RunFailed(f"hand edit: there is no {doc}")
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"(#{{1,6}})\s+(?:\d+\.?\s*)?{heading}\b", line, re.I)
        if m:
            level = len(m.group(1))
            end = next((j for j in range(i + 1, len(lines)) if re.match(rf"#{{1,{level}}}\s", lines[j])), len(lines))
            lines[i + 1:end] = ["", *text.splitlines(), ""]
            path.write_text("\n".join(lines).rstrip("\n") + "\n")
            return {"file": doc}
    raise RunFailed(f"hand edit: {doc} has no {heading} heading")


def author_checks(project, env, checks, task):
    """The author's own checks. crossref:DOI: the main document's reference
    entry for that work matches its Crossref record. rerun: every script in
    analysis/, run again from a clean start, writes the same text files in
    output/ that Claude left. tests: the project's tests all pass."""
    done = {}
    for check in checks:
        if check.startswith("crossref:"):
            doi = check.split(":", 1)[1]
            url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "warranted-delegation test"}),
                                        timeout=30) as r:
                record = json.load(r)["message"]
            author = record["author"][0]["family"]
            entry = reference_entry((project / TASKS[task]["doc"]).read_text(), author)
            year = str((record.get("published-print") or record.get("issued"))["date-parts"][0][0])
            wanted = [year, record["title"][0].split(":")[0]]
            if record.get("container-title"):
                wanted += [record["container-title"][0], record.get("volume"), (record.get("page") or "").split("-")[0]]
            missing = [w for w in wanted if w and norm(w) not in norm(entry)]
            if missing:
                raise RunFailed(f"author's check: the {author} entry doesn't match Crossref on {missing}")
            done[check] = "matches Crossref"
        elif check == "rerun":
            scripts = sorted((project / "analysis").glob("*.py"))
            outputs = {p: p.read_bytes() for p in (project / "output").rglob("*")
                       if p.is_file() and p.suffix in TEXT_OUTPUTS}
            if not scripts or not outputs:
                raise RunFailed("author's check: no scripts in analysis/ or no text files in output/")
            for p in outputs:
                p.unlink()
            for script in scripts:
                sh(["python3", str(script.relative_to(project))], project, env=env, timeout=600)
            differ = [str(p.relative_to(project)) for p, old in outputs.items()
                      if not p.exists() or p.read_bytes() != old]
            for p, old in outputs.items():
                p.write_bytes(old)
            if differ:
                raise RunFailed(f"author's check: a fresh run doesn't reproduce {differ}")
            done[check] = f"reproduced {len(outputs)} output files from {len(scripts)} scripts"
        elif check == "tests":
            r = sh(["python3", "-m", "unittest", "discover", "tests"], project, env=env, check=False)
            if r.returncode or "OK" not in r.stderr:
                raise RunFailed(f"author's check: the tests don't all pass: {r.stderr.strip()[-400:]}")
            done[check] = r.stderr.strip().splitlines()[-1]
    return done


def reference_entry(doc, author):
    """The document's reference-list entry for an author, joined across
    wrapped lines. In-text citations elsewhere don't count."""
    parts = re.split(r"^#{1,6}\s+(?:\d+\.?\s*)?References\b.*$", doc, flags=re.I | re.M)
    if len(parts) < 2:
        raise RunFailed("author's check: the document has no References section")
    section = re.split(r"^#{1,6}\s", parts[-1], flags=re.M)[0]
    entries = [" ".join(p.split()) for p in re.split(r"\n\s*\n|\n(?=[-*] )", section) if p.strip()]
    entry = next((e for e in entries if re.match(rf"[-*]?\s*{re.escape(author)}\b", e)), None)
    if entry is None:
        raise RunFailed(f"author's check: no {author} entry in the References")
    return entry


def norm(text):
    return re.sub(r"[\s\-–—]+", " ", re.sub(r"[*_]", "", str(text)).lower()).strip()


# Integrity and saving

def require_committed():
    changed = sh(["git", "status", "--porcelain", "--", *TOOL_PATHS], REPO).stdout.strip()
    if changed:
        raise RunFailed(f"commit these first, so the run uses the attested versions:\n{changed}")
    return {"repo_head": head(REPO)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment(env):
    py = sh(["python3", "-c", "import sys, statsmodels, pandas; print(sys.version.split()[0], "
             "statsmodels.__version__, pandas.__version__)"], REPO, env=env).stdout.split()
    return {"claude_code": sh(["claude", "--version"], REPO).stdout.strip(), "model": MODEL,
            "plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
            "python": py[0], "statsmodels": py[1], "pandas": py[2]}


def events_of(project):
    return [json.loads(l) for f in (project / "provenance" / "log").glob("*/events.jsonl")
            for l in f.read_text().splitlines() if l.strip()]


def report_smoke(project, record):
    events = events_of(project)
    starts = [e for e in events if e.get("event") == "SessionStart"]
    checks = {
        "the methods-kit skill was found and its text captured": any(
            (e.get("skill") or {}).get("sha256") and "methods-kit" in (e.get("skill") or {}).get("name", "")
            for e in events),
        "the brainstorm turn is labeled, and the switches recorded": any(e.get("brainstorm") for e in events)
            and [e.get("brainstorm_switch") for e in events if e.get("brainstorm_switch")][:2] == ["on", "off"],
        "the project's CLAUDE.md is captured as the project's, and nothing of the user's": all(
            any(i["kind"] == "project" and i["path"] == "CLAUDE.md" for i in e.get("instructions", []))
            and not any(i["kind"] == "user" for i in e.get("instructions", [])) for e in starts) and bool(starts),
        "each prompt was recorded once (one recorder)": all(
            n == 1 for n in Counter(e.get("prompt_id") for e in events if e.get("event") == "UserPromptSubmit").values()),
        "both plugins ran from the run's copies": all(
            any(p.startswith("warrant (--plugin-dir)") for p in e.get("plugins", []))
            and any(p.startswith("methods-kit (--plugin-dir)") for p in e.get("plugins", [])) for e in starts),
    }
    print(f"\nevents logged: {len(events)}")
    for label, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
    print(f"PASS  the record verifies: {record['verify_log'][-1]}")
    if not all(checks.values()):
        raise RunFailed("smoke test failed")


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    smoke = args == ["smoke"]
    if not smoke and not (len(args) == 2 and args[0] in TASKS and args[1] in CELLS):
        sys.exit(__doc__)
    task, cell = ("schools", "smoke") if smoke else args
    steps = SMOKE if smoke else parse_script(task, cell)
    if dry:
        print(f"{task} {cell}: setup save (/attest), then {len(steps)} steps\n")
        for s in steps:
            print(f"--- {s['id']} · {s['kind']}")
            print(s["text"] if s["text"] else f"(the runner's checks: {', '.join(s['checks'])})")
            print()
        return

    versions = {} if smoke else require_committed()
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    base = Path(tempfile.mkdtemp(prefix=f"wd-scripted2-{task}-{cell}-"))
    project = base / "project"
    project.mkdir()
    print(f"Throwaway project: {project}")
    venv = base / "venv"
    sh([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], base)
    shutil.copytree(PLUGIN, base / "plugin", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(METHODS_KIT, base / "methods-kit")
    # A fresh session: none of this session's Claude Code variables, never the
    # reader's API key, and no auto-memory.
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") and k != "CLAUDE_CONFIG_DIR") and k != "ANTHROPIC_API_KEY"}
    env.update(PATH=f"{venv / 'bin'}:{env['PATH']}", VIRTUAL_ENV=str(venv), CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")

    record = {"task": task, "cell": cell, "started": datetime.now().isoformat(timespec="seconds"),
              "environment": environment(env), "attested_versions": versions,
              "script_sha256": None if smoke else sha256(HERE / task / f"{cell}.md"),
              "key_sha256": sha256(HERE / task / "key.md"), "runner_sha256": sha256(__file__),
              "work": TASKS[task]["work"], "steps": []}
    try:
        sh(["git", "init", "-q", "-b", "main"], project)
        sh(["git", "config", "user.name", AUTHOR[0]], project)
        sh(["git", "config", "user.email", AUTHOR[1]], project)
        claude("/warrant:setup", project, dict(env, WD_SETUP_SKIP_GITHUB="1"), str(uuid.uuid4()), True)
        if not (project / "provenance" / "log").is_dir():
            raise RunFailed("/warrant:setup didn't set up the project")
        shutil.copytree(HERE / task / "start", project, dirs_exist_ok=True)

        info = attest("/warrant:attest", project, env, str(uuid.uuid4()), first=True)
        record["steps"].append({"id": "setup", "kind": "attest", **info})
        print(f"setup: notes and CLAUDE.md saved as the author's ({info['commit'][:7]})")

        session, first = str(uuid.uuid4()), True
        record["session"] = session
        for s in steps:
            print(f"{s['id']} · {s['kind']} …", end=" ", flush=True)
            if s["kind"] == "prompt":
                info = claude(s["text"], project, env, session, first)
                if info["exit"] or info["is_error"]:
                    raise RunFailed(f"{s['id']}: Claude Code reported an error: {info}")
            elif s["kind"] == "attest":
                info = attest(s["text"], project, env, session, first)
            elif s["kind"] == "command":
                info = command(s["text"], project, env, session, first)
            elif s["kind"] == "hand edit":
                info = hand_edit(s["text"], project, task)
            else:
                info = author_checks(project, env, s["checks"], task)
            if s["kind"] in ("prompt", "attest", "command"):
                first = False
            record["steps"].append({"id": s["id"], "kind": s["kind"], **info})
            print("done")

        verify = sh(["python3", "provenance/verify_log.py"], project, env=env, check=False)
        record["verify_log"] = [l.strip() for l in verify.stdout.splitlines() if l.strip()] or verify.stderr.strip()
        if verify.returncode:
            raise RunFailed(f"the record doesn't verify: {verify.stdout}{verify.stderr}")
        record["final_commit"] = head(project)
        record["finished"] = datetime.now().isoformat(timespec="seconds")
        if smoke:
            report_smoke(project, record)
            shutil.rmtree(base)
            print("Smoke test passed. Throwaway project deleted.")
            return
        out = HERE / "runs"
        out.mkdir(exist_ok=True)
        bundle = out / f"{task}-{cell}-{stamp}.bundle"
        sh(["git", "bundle", "create", str(bundle), "--all"], project)
        record["bundle_sha256"] = sha256(bundle)
        (out / f"{task}-{cell}-{stamp}.json").write_text(json.dumps(record, indent=2) + "\n")
    except (RunFailed, subprocess.TimeoutExpired) as e:
        print(f"\nRun failed: {e}\nThe throwaway project is kept for diagnosis: {project}")
        (base / "run-record.json").write_text(json.dumps(record, indent=2) + "\n")
        sys.exit(1)
    shutil.rmtree(base)
    print(f"Saved {bundle.relative_to(REPO)} and its .json. Throwaway project deleted.")


if __name__ == "__main__":
    main()
