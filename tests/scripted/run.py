#!/usr/bin/env python3
"""Play one scripted test run as the simulated author.

    python3 tests/scripted/run.py careful|unchecked|careless|owned [--dry-run]
    python3 tests/scripted/run.py dev-mixed [--dry-run]
    python3 tests/scripted/run.py smoke

dev-mixed is development material for the reader: no starting notes, no
answer key, and its bundle goes in tests/scripted/runs/dev/.

--dry-run prints every step exactly as it would be sent, and runs nothing.

smoke checks the machinery with one small prompt and a save: the hooks
record the session, /attest saves, Claude's Python is the run's own, and the
record verifies. It saves nothing here and deletes its project.

A real run:
1. Refuses to start unless the scripts, the answer key, the starting notes,
   this runner and the tool are committed unchanged, so the run uses the
   attested versions.
2. Makes a throwaway project outside this repository, signed by "Simulated
   Author", sets it up with the warrant plugin as people install it
   (/warrant:setup, GitHub skipped), copies in the starting notes, and saves
   them with /attest, so the record shows they are the author's and existed
   before Claude did anything. The plugin is loaded from a copy made at the
   start of the run (--plugin-dir), so the run's tool can't change midway.
3. Plays the script in one headless Claude Code session. The session loads
   no user-level settings, instructions, plugins or MCP servers: a plain
   Claude Code plus the plugin, at its default effort; the record's capture
   of instructions shows this. Python runs from a
   virtual environment outside the project, so nothing Claude installs
   touches this machine's Python.
4. Between turns, makes the author's hand edits and runs the author's own
   checks. If a check fails, or Claude's work has no place for a hand edit,
   the run stops.
5. Verifies the record, saves the whole history (work, log, snapshots, tags)
   as tests/scripted/runs/<run>-<date>.bundle with a .json of run details,
   and deletes the throwaway project. A failed run keeps its project for
   diagnosis and prints the path; delete it afterward.

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
import urllib.request
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RUNS = ("careful", "unchecked", "careless", "owned")
DEV_RUNS = ("dev-mixed",)
TEXT_OUTPUTS = {".md", ".csv", ".txt", ".tex", ".json", ".html"}
MODEL = "claude-opus-5-5"
AUTHOR = ("Simulated Author", "simulated.author@example.invalid")
STEP_TIMEOUT = 30 * 60
CLAUDE_FLAGS = [
    "--model", MODEL,
    "--setting-sources", "project,local",
    "--strict-mcp-config",
    "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash", "WebFetch", "WebSearch",
    "--output-format", "json",
]
TOBIN_DOI = "10.2307/1991374"
SMOKE = [
    {"id": "S1", "kind": "prompt", "text": "Run `which python3` and `python3 -c 'import statsmodels; "
     "print(statsmodels.__version__)'`, and write both outputs, one per line, to env.txt."},
    {"id": "S2", "kind": "attest", "text": "/attest"},
]
TOOL_PATHS = ["tests/scripted", ":(exclude)tests/scripted/runs", "plugin/warrant"]
PLUGIN = REPO / "plugin" / "warrant"


class RunFailed(Exception):
    pass


# Reading the scripts

def parse_script(name):
    """Return the steps of tests/scripted/<name>.md as dicts with id, kind
    and text. Text comes only from the blockquotes, so the notes around
    them are never sent. An author-checks step lists its checks on a
    "Runner checks:" line; without one, it runs both."""
    steps = []
    for block in re.split(r"^### ", (HERE / f"{name}.md").read_text(), flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        step_id, _, label = heading.partition(" · ")
        kind = ("prompt" if label == "Prompt" else
                "attest" if label == "Attest" else
                "hand edit" if label == "Hand edit" else
                "author checks" if label.startswith("The author's own checks") else None)
        if kind is None:
            raise RunFailed(f"{name}.md step {step_id}: unknown kind {label!r}")
        quote = [line[1:].removeprefix(" ") for line in body.splitlines() if line.startswith(">")]
        text = join_quote(quote)
        if kind == "hand edit" and not text:
            same = re.search(r"same as careful (C\d+)", body, re.I)
            if not same:
                raise RunFailed(f"{name}.md step {step_id}: hand edit has no text")
            text = next(s["text"] for s in parse_script("careful") if s["id"] == same.group(1))
        if kind in ("prompt", "attest", "hand edit") and not text:
            raise RunFailed(f"{name}.md step {step_id}: no text")
        step = {"id": step_id, "kind": kind, "text": text}
        if kind == "author checks":
            listed = re.search(r"^Runner checks: (.+)$", body, re.M)
            step["checks"] = [c.strip() for c in listed.group(1).split(",")] if listed else ["tobin", "rerun"]
            unknown = set(step["checks"]) - {"tobin", "rerun"}
            if unknown:
                raise RunFailed(f"{name}.md step {step_id}: unknown checks {sorted(unknown)}")
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
    # The run's copy of the plugin sits beside its project.
    args = ["claude", "-p", text, *CLAUDE_FLAGS, "--plugin-dir", str(project.parent / "plugin")]
    args += ["--session-id", session] if first else ["--resume", session]
    result = sh(args, project, env=env, timeout=STEP_TIMEOUT, check=False)
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        out = {}
    return {
        "exit": result.returncode,
        "seconds": round(time.time() - start),
        "is_error": out.get("is_error"),
        "turns": out.get("num_turns"),
        "cost_usd": out.get("total_cost_usd"),
        "stderr": result.stderr.strip()[-500:] or None,
    }


def head(project):
    return sh(["git", "rev-parse", "HEAD"], project, check=False).stdout.strip() or None


def attest(text, project, env, session, first):
    before = head(project)
    info = claude(text, project, env, session, first)
    after = head(project)
    body = sh(["git", "log", "-1", "--format=%B"], project, check=False).stdout
    if after == before or f"Attested-by: {AUTHOR[0]}" not in body:
        raise RunFailed(f"{text!r} made no attested save")
    info["commit"] = after
    return info


def hand_edit(text, project):
    """Put the author's paragraph under the memo's Limitations heading."""
    memo = project / "memo.md"
    if not memo.exists():
        raise RunFailed("hand edit: there is no memo.md")
    lines = memo.read_text().splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"(#{1,6})\s+(?:\d+\.?\s*)?Limitations\b", line, re.I)
        if m:
            level = len(m.group(1))
            end = next((j for j in range(i + 1, len(lines))
                        if re.match(rf"#{{1,{level}}}\s", lines[j])), len(lines))
            lines[i + 1:end] = ["", *text.splitlines(), ""]
            memo.write_text("\n".join(lines).rstrip("\n") + "\n")
            return {"file": "memo.md"}
    raise RunFailed("hand edit: memo.md has no Limitations heading")


def author_checks(project, env, checks):
    """The author's own checks. tobin: Tobin's reference entry against its
    Crossref record. rerun: every script in analysis/, run again from a
    clean start, writes the same text files in output/ that Claude left."""
    done = {}
    if "tobin" in checks:
        with urllib.request.urlopen(f"https://api.crossref.org/works/{TOBIN_DOI}", timeout=30) as r:
            record = json.load(r)["message"]
        entry = reference_entry((project / "memo.md").read_text(), "Tobin")
        year = str(record["issued"]["date-parts"][0][0])
        wanted = [year, record["container-title"][0], record["title"][0], record["volume"], record["page"]]
        missing = [w for w in wanted if norm(w) not in norm(entry)]
        if missing:
            raise RunFailed(f"author's check: Tobin entry doesn't match Crossref on {missing}")
        done["tobin"] = "matches Crossref"

    if "rerun" in checks:
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
        done["rerun"] = f"reproduced {len(outputs)} output files from {len(scripts)} scripts"
    return done


def reference_entry(memo, author):
    """The memo's reference-list entry for an author, joined across wrapped
    lines. In-text citations elsewhere in the memo don't count."""
    parts = re.split(r"^#{1,6}\s+(?:\d+\.?\s*)?References\b.*$", memo, flags=re.I | re.M)
    if len(parts) < 2:
        raise RunFailed("author's check: memo.md has no References section")
    section = re.split(r"^#{1,6}\s", parts[-1], flags=re.M)[0]
    entries = [" ".join(p.split()) for p in re.split(r"\n\s*\n", section) if p.strip()]
    entry = next((e for e in entries if re.match(rf"[-*]?\s*{author}\b", e)), None)
    if entry is None:
        raise RunFailed(f"author's check: no {author} entry in the memo's References")
    return entry


def norm(text):
    return re.sub(r"[\s\-–—]+", " ", re.sub(r"[*_]", "", str(text)).lower()).strip()


# Integrity and saving

def require_committed():
    changed = sh(["git", "status", "--porcelain", "--", *TOOL_PATHS], REPO).stdout.strip()
    if changed:
        raise RunFailed(f"commit these first, so the run uses the attested versions:\n{changed}")
    return {"repo_head": head(REPO),
            "answer_key": sh(["git", "log", "-1", "--format=%H %cI", "--",
                              "tests/scripted/answer-key.md"], REPO).stdout.strip()}


def report_smoke(project, venv, record):
    lines = (project / "env.txt").read_text().split() if (project / "env.txt").exists() else []
    events = [json.loads(l) for f in (project / "provenance" / "log").glob("*/events.jsonl")
              for l in f.read_text().splitlines()]
    kinds = sorted({e.get("event") for e in events})
    snapshots = sh(["git", "for-each-ref", "--format=%(refname)", "refs/provenance"], project).stdout.split()
    checks = {
        "Claude's python3 is the run's own": bool(lines) and lines[0].startswith(str(venv)),
        "the hooks recorded the session": "UserPromptSubmit" in kinds and "PostToolUse" in kinds,
        "snapshots were taken": bool(snapshots),
        "saves are signed by the simulated author": all(
            f"Attested-by: {AUTHOR[0]}" in sh(["git", "log", "-1", "--format=%B", s["commit"]], project).stdout
            for s in record["steps"] if s.get("commit")),
        "each prompt was recorded once (one recorder, the plugin)": all(
            n == 1 for n in Counter(e.get("prompt_id") for e in events
                                    if e.get("event") == "UserPromptSubmit").values()),
        "the plugin ran from the run's copy": all(
            any(p.startswith("warrant (--plugin-dir)") for p in e.get("plugins", []))
            for e in events if e.get("event") == "SessionStart"),
        "capture shows no user-level instructions, and no memory": all(
            not any(i["kind"] == "user" for i in e.get("instructions", []))
            and e.get("memory_capture") == "not loaded"
            for e in events if e.get("event") == "SessionStart"),
    }
    print(f"\nevents logged: {len(events)} ({', '.join(map(str, kinds))})")
    print(f"env.txt: {' '.join(lines) or '(missing)'}")
    for label, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
    print(f"PASS  the record verifies: {record['verify_log'][-1]}")
    if not all(checks.values()):
        raise RunFailed("smoke test failed")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment(env):
    py = sh(["python3", "-c", "import sys, statsmodels, pandas; print(sys.version.split()[0], "
             "statsmodels.__version__, pandas.__version__)"], REPO, env=env).stdout.split()
    return {"claude_code": sh(["claude", "--version"], REPO).stdout.strip(), "model": MODEL,
            "plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
            "python": py[0], "statsmodels": py[1], "pandas": py[2]}


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    names = [a for a in args if a in (*RUNS, *DEV_RUNS, "smoke")]
    if len(names) != 1 or len(args) != len(names) + dry:
        sys.exit(__doc__)
    name = names[0]
    smoke = name == "smoke"
    steps = SMOKE if smoke else parse_script(name)

    if dry:
        print(f"{name}: setup save (/attest), then {len(steps)} steps\n")
        for s in steps:
            print(f"--- {s['id']} · {s['kind']}")
            print(s["text"] if s["text"] else f"(the runner's checks: {', '.join(s['checks'])})")
            print()
        return

    versions = {} if smoke else require_committed()
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    base = Path(tempfile.mkdtemp(prefix=f"wd-scripted-{name}-"))
    project = base / "project"
    project.mkdir()
    print(f"Throwaway project: {project}")

    venv = base / "venv"
    sh([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], base)
    # A fresh session: none of this session's Claude Code variables (effort,
    # parent session), and never the reader's API key. Auto-memory is off, so
    # the session writes nothing under ~/.claude/projects (a careful run did,
    # Oct 6).
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") and k != "CLAUDE_CONFIG_DIR") and k != "ANTHROPIC_API_KEY"}
    env.update(PATH=f"{venv / 'bin'}:{env['PATH']}", VIRTUAL_ENV=str(venv), CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")

    record = {"run": name, "started": datetime.now().isoformat(timespec="seconds"),
              "environment": environment(env), "attested_versions": versions,
              "script_sha256": None if smoke else sha256(HERE / f"{name}.md"),
              "answer_key_sha256": sha256(HERE / "answer-key.md"),
              "runner_sha256": sha256(__file__), "steps": []}
    try:
        sh(["git", "init", "-q", "-b", "main"], project)
        sh(["git", "config", "user.name", AUTHOR[0]], project)
        sh(["git", "config", "user.email", AUTHOR[1]], project)
        shutil.copytree(PLUGIN, base / "plugin", ignore=shutil.ignore_patterns("__pycache__"))
        claude("/warrant:setup", project, dict(env, WD_SETUP_SKIP_GITHUB="1"), str(uuid.uuid4()), True)
        if not (project / "provenance" / "log").is_dir():
            raise RunFailed("/warrant:setup didn't set up the project")
        if name in RUNS:
            shutil.copytree(HERE / "start", project, dirs_exist_ok=True)

        info = attest("/attest", project, env, str(uuid.uuid4()), first=True)
        record["steps"].append({"id": "setup", "kind": "attest", **info})
        print(f"setup: notes saved as the author's ({info['commit'][:7]})")

        session, first = str(uuid.uuid4()), True
        record["session"] = session
        for s in steps:
            print(f"{s['id']} · {s['kind']} …", end=" ", flush=True)
            if s["kind"] == "prompt":
                info = claude(s["text"], project, env, session, first)
                first = False
                if info["exit"] or info["is_error"]:
                    raise RunFailed(f"{s['id']}: Claude Code reported an error: {info}")
            elif s["kind"] == "attest":
                info = attest(s["text"], project, env, session, first)
            elif s["kind"] == "hand edit":
                info = hand_edit(s["text"], project)
            else:
                info = author_checks(project, env, s["checks"])
            record["steps"].append({"id": s["id"], "kind": s["kind"], **info})
            print("done")

        verify = sh(["python3", "provenance/verify_log.py"], project, env=env, check=False)
        record["verify_log"] = [l.strip() for l in verify.stdout.splitlines() if l.strip()] or verify.stderr.strip()
        if verify.returncode:
            raise RunFailed(f"the record doesn't verify: {verify.stdout}{verify.stderr}")
        record["final_commit"] = head(project)
        record["finished"] = datetime.now().isoformat(timespec="seconds")
        if smoke:
            report_smoke(project, venv, record)
            shutil.rmtree(base)
            print("Smoke test passed. Throwaway project deleted.")
            return

        out = HERE / "runs" / ("dev" if name in DEV_RUNS else "")
        out.mkdir(parents=True, exist_ok=True)
        bundle = out / f"{name}-{stamp}.bundle"
        sh(["git", "bundle", "create", str(bundle), "--all"], project)
        record["bundle_sha256"] = sha256(bundle)
        (out / f"{name}-{stamp}.json").write_text(json.dumps(record, indent=2) + "\n")
    except (RunFailed, subprocess.TimeoutExpired) as e:
        print(f"\nRun failed: {e}\nThe throwaway project is kept for diagnosis: {project}")
        (base / "run-record.json").write_text(json.dumps(record, indent=2) + "\n")
        sys.exit(1)

    shutil.rmtree(base)
    print(f"Saved {bundle.relative_to(REPO)} and its .json. Throwaway project deleted.")


if __name__ == "__main__":
    main()
