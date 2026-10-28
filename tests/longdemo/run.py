#!/usr/bin/env python3
"""The long demonstrations: a simulated author writes a paper with Claude
Code, and the reader writes its disclosure.

    python3 tests/longdemo/run.py smoke              check the setup (three prompts)
    python3 tests/longdemo/run.py low-high           a full run of the archival paper; its
                                                     authors are low-high, high-low,
                                                     high-high, and low-low
    python3 tests/longdemo/run.py --paper experiment low-high
                                                     demo B: the experiment paper, or
                                                     --paper qualitative; the same authors
    python3 tests/longdemo/run.py --resume DIR       pick up an interrupted run
    python3 tests/longdemo/run.py --dry-run low-high show the plan; run nothing

Three papers, each written by four simulated authors in separate runs
(DECISIONS.md, Oct 16; the fourth author, Oct 17): the archival paper (this
folder: start/, personas/, plants.md), and demo B's experiment and
qualitative papers (papers/<paper>/, laid out the same way). Authors are
named by their place on the two measures, delegation and warrant, first
delegation, then warrant: low-high is low delegation, high warrant (careful);
high-low is high delegation, low warrant (careless); high-high hands over
most calls but checks and signs off on each; low-low makes the calls but
checks nothing. The archival paper's first two authors ran as careful and
careless until Oct 17, when every run was redone with the sessions kept away
from the author's own settings and files. Disclosure labels spell the measures
out.

The design is tests/longdemo/README.md; the personas are in personas/.

What a run does:
1. Makes a throwaway project in ~/.warranted-delegation/demos/<run>/, outside
   this repository, as "Simulated Author": the starting notes, a copy of the
   warrant plugin set up with /warrant:setup (GitHub skipped), and a first
   /warrant:attest.
   The runner then clears setup's data rules from .gitignore, so the run
   records its public data (the author, Oct 7).
2. Plays the simulated author (Sonnet 5.5, on the reader's Keychain key)
   against one headless Claude Code session (Opus 5.5, on the logged-in
   account). Claude Code runs in its own sandbox: its commands can write only
   in the run folder, reach only the sites the paper needs, and can read
   nothing in the home folder but the run's own folder; Claude's file tools
   read only the project; no CLAUDE.md is loaded; and it refuses to run
   without the sandbox. The author sees what a real author would: Claude's
   reply and the tool calls it made. The low-high, high-high, and smoke
   authors can also open files and edit them by hand; the qualitative paper's
   low-low author can read its transcripts, in data/, and nothing else.
3. Saves its place after every step (state.json). --resume continues at the
   last finished step. A turn cut off midway is sent again with a message
   labeled as the runner's, so the record shows it. If Claude Code fails (a
   usage limit, say), the run pauses for --resume instead of going on.
4. At the end: proposes the finished-work map (the author checks it, if it
   can read files), the author attests, and the plugin's reader writes the
   disclosure.
5. Saves the run into this repository as tests/longdemo/runs/<run>.bundle,
   with the disclosure and the author's side of the conversation, then
   deletes the run folder (--keep keeps it).

It never commits in this repository. While it runs, caffeinate keeps the Mac
awake if it's plugged in.
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PLUGIN = REPO / "plugin" / "warrant"
HOME = Path(os.environ.get("WD_HOME", Path.home() / ".warranted-delegation"))
DEMOS = HOME / "demos"
VENV_PY = HOME / "venv" / "bin" / "python"  # the reader's environment, which has anthropic
RUNS = HERE / "runs"
AUTHOR = ("Simulated Author", "simulated.author@example.invalid")
WORKER_MODEL = "claude-opus-5-5"
AUTHOR_MODEL = "claude-sonnet-5-5"
KEYCHAIN_ITEM = "warranted-delegation-anthropic"
# Keys a paper's data sources need, from the Keychain into the session's
# environment (the author, Oct 16: OpenAlex now charges requests against a daily
# allowance, and the keyless one is too small for the archival paper).
OPENALEX_ITEM = "warranted-delegation-openalex"
PERSONAS = {"smoke": {"max_prompts": 4, "files": True},
            "low-high": {"max_prompts": 35, "files": True},
            "high-low": {"max_prompts": 6, "files": False},
            "high-high": {"max_prompts": 30, "files": True},
            "low-low": {"max_prompts": 30, "files": False}}
# Each author's place on the two measures, for the disclosure's label (the author, Oct 17).
CORNERS = {"careful": "low delegation, high warrant", "careless": "high delegation, low warrant",
           "low-high": "low delegation, high warrant", "high-low": "high delegation, low warrant",
           "high-high": "high delegation, high warrant", "low-low": "low delegation, low warrant"}
STEP_TIMEOUT = 60 * 60  # one Claude Code turn
SESSION_LIMIT = 6 * 60 * 60  # one sitting of the runner; --resume continues
REPLY_CAP, READ_CAP, TOOLS_SHOWN = 12000, 40000, 40
# Sites Claude's commands may reach: the data sources, reference checks, and
# Python packages. WebFetch and WebSearch are read-only and not limited here.
CHECKS = ["doi.org", "api.crossref.org", "pypi.org", "files.pythonhosted.org"]
PAPERS = {
    "archival": {"dir": HERE, "authors": ("smoke", "low-high", "high-low", "high-high", "low-low"),
                 "domains": ["api.openalex.org", "openalex.org", "docs.openalex.org", "help.openalex.org",
                             "api.worldbank.org", *CHECKS],
                 "data": "this paper's data are public (OpenAlex, the World Bank)", "packs": None,
                 "keys": {"OPENALEX_API_KEY": OPENALEX_ITEM}},
    "experiment": {"dir": HERE / "papers" / "experiment", "authors": ("smoke", "low-high", "high-low", "high-high", "low-low"),
                   "domains": ["www.nber.org", "nber.org", "www.socialscienceregistry.org", "socialscienceregistry.org",
                               *CHECKS],
                   "data": "this paper's data are the authors' posted replication files",
                   "packs": ["quantitative", "experiments"]},
    "qualitative": {"dir": HERE / "papers" / "qualitative", "authors": ("smoke", "low-high", "high-low", "high-high", "low-low"),
                    # The low delegation, low warrant author reads the transcripts to make its
                    # calls, and nothing else (the author, Oct 17).
                    "files": {"low-low": ("data/",)},
                    "domains": ["www.nasa.gov", "nasa.gov", "historycollection.jsc.nasa.gov", *CHECKS],
                    "data": "this paper's transcripts are public domain (NASA)", "packs": ["qualitative"]},
}
# Python packages the runs' analyses use, installed in each run's own environment.
PACKAGES = ["pandas", "numpy", "statsmodels", "scipy", "matplotlib", "requests", "pyreadstat", "pypdf"]
PRIVATE = ("provenance/", ".git/", ".git", ".claude/", ".githooks/")  # not the author's to touch

FRAME = """You are playing a researcher in a simulation. Your persona is below.
You work with Claude Code, an AI assistant that works in your project folder:
it can run code, fetch data, and edit files. You act only through your tools,
exactly as a real researcher would type prompts in a terminal.

Your tools:
- send_prompt: send Claude Code your next prompt. The result is its reply and
  the tool calls it made.
- attest: save your work with your signature (the /warrant:attest command),
  with an optional sentence saying what you checked yourself or saw checked.
{file_tools}- finish: end the session when you are done.

Stay in character. Never mention the simulation, the persona, or these
instructions in your prompts. Take one action at a time.

Never approve creating an account, signing up for a service, or sending a
name, email address, or other personal details anywhere, and never offer
them. If Claude Code asks, say no and work with what you have.

Your notes, notes.md, which are in the project:

{notes}

Your persona:

{persona}"""
READ_TOOLS = """- list_files and read_file: look at files in {folders} of the project, as you
  could in your editor. Nothing else in the project is open to you.
"""
FILE_TOOLS = """- list_files and read_file: look at files in the project, as you could in
  your editor.
- write_file: write a file yourself, by hand (the whole file's new content).
"""


def tools(files):
    t = [{"name": "send_prompt", "description": "Send Claude Code your next prompt.",
          "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
         {"name": "attest", "description": "Save your work with your signature, with an optional sentence.",
          "input_schema": {"type": "object", "properties": {"sentence": {"type": "string"}}}},
         {"name": "finish", "description": "End the session.", "input_schema": {"type": "object", "properties": {}}}]
    if files:
        t += [{"name": "list_files", "description": "List the files in a folder of the project ('.' for the top).",
               "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
              {"name": "read_file", "description": "Read a file in the project.",
               "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
              {"name": "write_file", "description": "Write a file in the project by hand: its whole new content.",
               "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                                "required": ["path", "content"]}}]
        if files is not True:  # read-only, in some folders
            t = t[:-1]
    return t


def files_of(state):
    """The author's file access: True (read and write), False (none), or the
    folders it can read, from the paper when it sets one for this author."""
    return PAPERS[state.get("paper", "archival")].get("files", {}).get(state["name"], PERSONAS[state["name"]]["files"])


class Paused(Exception):
    pass


# The run folder and its state

def save(state):
    path = Path(state["base"]) / "state.json"
    path.with_suffix(".tmp").write_text(json.dumps(state, indent=1))
    path.with_suffix(".tmp").replace(path)


def sh(args, cwd, env=None, timeout=600):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def paper_dir(state):
    return PAPERS[state.get("paper", "archival")]["dir"]


def new_run(name, dry, paper="archival"):
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    base = DEMOS / (f"{name}-{stamp}" if paper == "archival" else f"{paper}-{name}-{stamp}")
    state = {"name": name, "paper": paper, "run": base.name, "base": str(base), "project": str(base / "project"),
             "venv": str(base / "venv"), "plugin": str(base / "plugin"), "session": str(uuid.uuid4()),
             "started": datetime.now().isoformat(timespec="seconds"), "phase": "setup", "prompts": 0,
             "messages": [], "pending": None, "steps": [], "author_usage": {}, "nudges": 0}
    if dry:
        return state
    (base / "project").mkdir(parents=True)
    shutil.copytree(PLUGIN, base / "plugin", ignore=shutil.ignore_patterns("__pycache__"))
    python = shutil.which("python3")
    sh([python, "-m", "venv", str(base / "venv")], base)
    r = sh([str(base / "venv" / "bin" / "python"), "-m", "pip", "install", "--quiet", *PACKAGES], base, timeout=1800)
    if r.returncode:
        raise SystemExit(f"Couldn't install the analysis packages: {r.stderr.strip()[-400:]}")
    p = state["project"]
    for args in (["git", "init", "-q", "-b", "main"], ["git", "config", "user.name", AUTHOR[0]],
                 ["git", "config", "user.email", AUTHOR[1]]):
        sh(args, p)
    for item in (paper_dir(state) / "start").iterdir():  # the notes, and any data the paper starts from
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, Path(p) / item.name)
    state["versions"] = {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                         "claude_code": sh(["claude", "--version"], base).stdout.strip(),
                         "python_packages": sh([str(base / "venv" / "bin" / "python"), "-m", "pip", "freeze"],
                                               base).stdout.split(),
                         "runner_commit": sh(["git", "rev-parse", "HEAD"], REPO).stdout.strip()}
    save(state)
    return state


# Claude Code

def settings(state):
    # Nothing of the author's outside the run (the author, Oct 17): commands can read only
    # the run's own folder in the home directory, and Claude's file tools only
    # the project.
    return {"sandbox": {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
                        "autoAllowBashIfSandboxed": True,
                        "filesystem": {"allowWrite": [state["project"], state["venv"]],
                                       "denyRead": [str(Path.home()), str(REPO)], "allowRead": [state["base"]]},
                        "network": {"allowedDomains": PAPERS[state.get("paper", "archival")]["domains"]}},
            "permissions": {"blockReadsOutsideWorkingDirectories": True}}


def session_env(state):
    # A fresh session: none of this session's Claude Code variables, never the
    # reader's API key, no auto-memory, no CLAUDE.md (the author's own, in his home
    # folder, loaded before Oct 17 because the runs live there), and GitHub
    # skipped at setup.
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") and k != "CLAUDE_CONFIG_DIR") and k != "ANTHROPIC_API_KEY"}
    venv = Path(state["venv"])
    env.update(PATH=f"{venv / 'bin'}:{env['PATH']}", VIRTUAL_ENV=str(venv),
               CLAUDE_CODE_DISABLE_AUTO_MEMORY="1", CLAUDE_CODE_DISABLE_CLAUDE_MDS="1", WD_SETUP_SKIP_GITHUB="1")
    # Tools that look in the home folder, which the sandbox can't read, look in
    # the run's environment instead (writable, and outside the record): git's
    # global config is empty, and caches and config go to the venv folder.
    env.update(GIT_CONFIG_GLOBAL=os.devnull, XDG_CONFIG_HOME=str(venv / ".config"), XDG_CACHE_HOME=str(venv / ".cache"),
               MPLCONFIGDIR=str(venv / ".cache" / "matplotlib"), PIP_CACHE_DIR=str(venv / ".cache" / "pip"),
               PIP_CONFIG_FILE=os.devnull)
    env.update(paper_keys(state))
    return env


def paper_keys(state):
    # The data sources' keys, by variable name. A missing key is left out, and
    # the session works with the keyless allowance, as before Oct 16.
    keys = {}
    for var, item in PAPERS[state.get("paper", "archival")].get("keys", {}).items():
        value = subprocess.run(["security", "find-generic-password", "-s", item, "-w"],
                               capture_output=True, text=True).stdout.strip()
        if value:
            keys[var] = value
    return keys


def leak_check(state):
    # A key must never reach the record, the disclosure, or this repository:
    # stop before the reader sends the record anywhere, and again before saving.
    base, project = Path(state["base"]), Path(state["project"])
    shown = json.dumps(state.get("messages", []))
    for var, value in paper_keys(state).items():
        where = []
        if sh(["git", "log", "--all", "--format=%h", "-S", value], project).stdout.strip():
            where.append("the project's history or record")
        for folder in (project, base / "disclosure"):
            if folder.is_dir() and subprocess.run(["grep", "-r", "-l", "-F", "--exclude-dir=.git", value, str(folder)],
                                                  capture_output=True).stdout:
                where.append(str(folder))
        if value in shown:
            where.append("what the simulated author was shown")
        if where:
            raise Paused(f"{var}'s value appears in {', '.join(where)}; nothing was read or saved. "
                         "Remove it before resuming.")


def claude(text, state, first=False):
    args = ["claude", "-p", text, "--model", WORKER_MODEL, "--plugin-dir", state["plugin"],
            "--setting-sources", "project,local", "--strict-mcp-config", "--settings", json.dumps(settings(state)),
            "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "WebFetch", "WebSearch",
            "--output-format", "json"]
    args += ["--session-id", state["session"]] if first else ["--resume", state["session"]]
    if paper_keys(state):  # names only, never values (Oct 17: two of four archival runs never found the key)
        args += ["--append-system-prompt", "These keys are set in your environment for this project's data "
                 f"sources: {', '.join(paper_keys(state))}."]
    start = time.time()
    try:
        r = sh(args, state["project"], env=session_env(state), timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"error": f"no reply within {STEP_TIMEOUT // 60} minutes", "seconds": round(time.time() - start)}
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        out = {}
    info = {"seconds": round(time.time() - start), "turns": out.get("num_turns"),
            "cost_usd": out.get("total_cost_usd"), "reply": out.get("result")}
    if r.returncode or out.get("is_error"):
        info["error"] = (out.get("result") or r.stderr.strip() or r.stdout.strip())[-800:]
    return info


def head(state):
    return sh(["git", "rev-parse", "HEAD"], state["project"]).stdout.strip() or None


def events(state):
    out = []
    for log in sorted((Path(state["project"]) / "provenance" / "log").glob("*/events.jsonl")):
        out += [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    return out


def attest(sentence, state, first=False):
    before = head(state)
    info = claude("/warrant:attest" + (f" {sentence.strip()}" if sentence and sentence.strip() else ""), state, first)
    after = head(state)
    body = sh(["git", "log", "-1", "--format=%B"], state["project"]).stdout
    if after == before or f"Attested-by: {AUTHOR[0]}" not in body:
        raise Paused(f"/warrant:attest made no signed save: {info.get('error') or info.get('reply')}")
    info["commit"] = after
    return info


def record_data(project, why):
    """The data are public, so every run records them, for reproducibility
    (the author, Oct 7): clear setup's data rules from .gitignore. Files over 25 MB
    are still left out by the plugin."""
    gi = Path(project) / ".gitignore"
    lines, out, inside = gi.read_text().splitlines(), [], False
    for line in lines:
        if line.startswith("# --- warranted delegation:"):
            inside = True
            out += [line, f"# Long demonstration: {why},", "# so they are recorded, for reproducibility."]
            continue
        if line.startswith("# --- end warranted delegation"):
            inside = False
        if not inside:
            out.append(line)
    gi.write_text("\n".join(out) + "\n")


def setup(state):
    info = claude("/warrant:setup", state, first=True)
    if not (Path(state["project"]) / "provenance" / "log").is_dir():
        raise SystemExit(f"/warrant:setup didn't set up the project: {info}")
    record_data(state["project"], PAPERS[state.get("paper", "archival")]["data"])
    info = attest("", state)
    state["steps"].append({"kind": "setup", "commit": info["commit"]})
    state["phase"] = "author"
    save(state)


def send(text, state, resent=False):
    """One prompt to Claude Code. Returns what the author sees."""
    seen = len(events(state))
    info = claude(text, state)
    if info.get("error"):
        raise Paused(f"Claude Code stopped: {info['error']}")
    calls = [e for e in events(state)[seen:] if e.get("event") == "PostToolUse"]
    lines = [f"- {e.get('tool')}: {(e.get('command') or ' '.join(e.get('paths') or []))[:160]}" for e in calls]
    shown = lines[:TOOLS_SHOWN] + ([f"- and {len(lines) - TOOLS_SHOWN} more"] if len(lines) > TOOLS_SHOWN else [])
    state["steps"].append({"kind": "prompt", "n": state["prompts"], "seconds": info["seconds"],
                           "turns": info["turns"], "cost_usd": info["cost_usd"], "tool_calls": len(calls),
                           "resent": resent})
    reply = (info.get("reply") or "").strip()
    return (("[Your last prompt was cut off and the runner sent it on.]\n\n" if resent else "")
            + f"Claude ran {len(calls)} tool calls:\n" + ("\n".join(shown) or "(none)")
            + f"\n\nClaude's reply:\n{reply[:REPLY_CAP]}" + (" [cut]" if len(reply) > REPLY_CAP else ""))


# The simulated author

def inside(state, path, write=False):
    root = Path(state["project"]).resolve()
    p = (root / path).resolve()
    rel = p.relative_to(root).as_posix() if p.is_relative_to(root) else None
    if rel == "provenance/finished-work.md" and state["phase"] == "map":
        return p  # the author checks the map at the end
    if rel is None or (rel + "/").startswith(PRIVATE):
        raise ValueError(f"{path} isn't a file you can {'write' if write else 'read'} in the project")
    files = files_of(state)
    if files is not True and (write or not any((rel + "/").startswith(f) for f in (files or ()))):
        raise ValueError(f"{path} isn't open to you; you can read only in {', '.join(files or ()) or 'no folder'}")
    return p


def local_tool(name, args, state):
    try:
        if name == "list_files":
            p = inside(state, args.get("path") or ".")
            items = sorted(x.relative_to(p).as_posix() + ("/" if x.is_dir() else "") for x in p.iterdir()
                           if not x.name.startswith(".git") and x.name not in ("provenance", ".claude", ".githooks"))
            return "\n".join(items) or "(empty)"
        if name == "read_file":
            text = inside(state, args["path"]).read_text(errors="replace")
            return text[:READ_CAP] + (f"\n[cut at {READ_CAP} characters]" if len(text) > READ_CAP else "")
        if name == "write_file":
            p = inside(state, args["path"], write=True)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            state["steps"].append({"kind": "hand edit", "path": args["path"]})
            return f"Wrote {args['path']}."
    except Exception as exc:
        return f"Couldn't: {exc}"
    return f"Unknown tool {name}"


def author_call(client, state, system, files):
    msgs = copy.deepcopy(state["messages"])
    last = msgs[-1]["content"]
    if isinstance(last, list) and last:
        last[-1]["cache_control"] = {"type": "ephemeral"}
    start = time.time()
    resp = client.messages.create(model=AUTHOR_MODEL, max_tokens=16000,
                                  system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                                  tools=tools(files), messages=msgs)
    u = state["author_usage"]
    for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        u[k] = u.get(k, 0) + (getattr(resp.usage, k, 0) or 0)
    u["calls"] = u.get("calls", 0) + 1
    u["seconds"] = u.get("seconds", 0) + round(time.time() - start)
    # Keep only what the conversation needs, so it can be sent again on --resume.
    return [{"type": "text", "text": b.text} if b.type == "text" else
            {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
            for b in resp.content if b.type in ("text", "tool_use")]


def act(block, state):
    """Carry out one of the author's terminal actions; returns the tool result text."""
    name, args = block["name"], block.get("input") or {}
    if name == "send_prompt":
        if "text" not in args:  # the author's reply ran out of room mid-prompt
            return "Not sent: your prompt was cut off before it ended. Send it again."
        limit = PERSONAS[state["name"]]["max_prompts"]
        if state["prompts"] >= limit:
            return f"Not sent: that's your limit of {limit} prompts. Attest if you want to, then finish."
        state["prompts"] += 1
        return send(args["text"], state)
    if name == "attest":
        info = attest(args.get("sentence") or "", state)
        state["steps"].append({"kind": "attest", "sentence": args.get("sentence") or "", "commit": info["commit"]})
        return "Saved and signed."
    if name == "finish":
        state["phase"] = "map" if state["phase"] == "author" else "read"
        return "Done."


def author_loop(client, state, deadline):
    files = files_of(state)
    folder = paper_dir(state) if (paper_dir(state) / "personas" / f"{state['name']}.md").exists() else HERE
    persona = (folder / "personas" / f"{state['name']}.md").read_text().split("\n\n", 2)[2]  # drop the title and the note
    file_tools = FILE_TOOLS if files is True else READ_TOOLS.format(folders=", ".join(files)) if files else ""
    system = FRAME.format(file_tools=file_tools, notes=(paper_dir(state) / "start" / "notes.md").read_text(),
                          persona=persona)
    if not state["messages"]:
        state["messages"].append({"role": "user", "content": [{"type": "text", "text":
            "Your project folder has your notes in notes.md, and it's set up and saved once. Begin."}]})
    while state["phase"] in ("author", "map"):
        if time.time() > deadline:
            raise Paused("the runner's time for this sitting ran out")
        if state["pending"]:  # an action was cut off; finish it
            block, results = state["pending"]["block"], state["pending"]["results"]
            if block["name"] == "send_prompt" and "text" not in block["input"]:  # cut off, and counted, before Oct 17's fix
                state["prompts"] -= 1
                text = act(block, state)
            elif block["name"] == "send_prompt":
                text = send("We were interrupted. (This message is from the demonstration's runner, not the "
                            "author.) Here is the author's prompt again; pick up where you left off.\n\n"
                            + block["input"]["text"], state, resent=True)
            else:
                text = act(block, state)
            state["messages"].append({"role": "user", "content": results + [
                {"type": "tool_result", "tool_use_id": block["id"], "content": text}]})
            state["pending"] = None
            save(state)
            continue
        content = author_call(client, state, system, files)
        state["messages"].append({"role": "assistant", "content": content})
        uses = [b for b in content if b.get("type") == "tool_use"]
        if not uses:
            state["nudges"] += 1
            if state["nudges"] > 3:
                raise Paused("the author stopped using its tools")
            state["messages"].append({"role": "user", "content": [{"type": "text", "text": "Act with one of your tools."}]})
            save(state)
            continue
        results, terminal = [], None
        for b in uses:  # in the author's order; anything after an action waits for its result
            if terminal is not None:
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": "Not done: one action at a time."})
            elif b["name"] in ("list_files", "read_file", "write_file"):
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": local_tool(b["name"], b["input"], state)})
            else:
                terminal = b
        if terminal:
            state["pending"] = {"block": terminal, "results": results}
            save(state)
            results = results + [{"type": "tool_result", "tool_use_id": terminal["id"], "content": act(terminal, state)}]
            state["pending"] = None
        state["messages"].append({"role": "user", "content": results})
        if state["phase"] == "map" and not state.get("map"):
            state["messages"][-1]["content"].append({"type": "text", "text": map_step(state, files)})
        save(state)


# The finished-work map, the disclosure, and saving the run

def disclose_module(state):
    sys.path.insert(0, str(Path(state["plugin"]) / "scripts"))  # the run's own copy of the plugin
    import disclose
    return disclose


def map_step(state, files):
    d = disclose_module(state)
    # The archival paper's map is guessed from its files, as before; demo B's
    # papers propose their packs, so every author is read against the same checklist.
    text, _ = d.propose_map(Path(state["project"]), PAPERS[state.get("paper", "archival")]["packs"])
    (Path(state["project"]) / d.MAP).write_text(text)
    state["map"] = True
    if files is True:
        return ("Before the disclosure is written, check the finished-work map, provenance/finished-work.md: "
                "the paper plus everything its reported results depend on, and the checklist packs. Correct it "
                "with write_file if anything is wrong, then attest and finish.")
    return "The finished-work map is in provenance/finished-work.md. Attest and finish."


def read(state):
    leak_check(state)
    d = disclose_module(state)
    project = Path(state["project"])
    slots = d.read_map(project / d.MAP)
    packs, unknown = d.packs_of(slots)
    paths = [p for p in d.work_paths(slots) if (project / p.rstrip("/")).exists()]
    out = Path(state["base"]) / "disclosure"
    label = f"Demonstration run ({CORNERS.get(state['name'], state['name'] + ' author')}), last save {(head(state) or '')[:7]}"
    r = sh([str(VENV_PY), str(Path(state["plugin"]) / "scripts" / "reader.py"), str(project), "--work", *paths,
            "--packs", *(packs or ["quantitative"]), "--out", str(out), "--map", str(project / d.MAP),
            "--label", label], REPO, timeout=3 * 60 * 60)
    (Path(state["base"]) / "reader.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        raise Paused(f"the reader failed: {(r.stderr or r.stdout).strip()[-400:]}")
    state["phase"] = "save"
    save(state)


def keep(state, keep_folder):
    leak_check(state)
    RUNS.mkdir(exist_ok=True)
    dest = RUNS / state["run"]
    dest.mkdir(exist_ok=True)
    r = sh(["git", "bundle", "create", str(RUNS / f"{state['run']}.bundle"), "--all"], state["project"])
    if r.returncode:
        raise Paused(f"git bundle failed: {r.stderr.strip()}")
    if (Path(state["base"]) / "disclosure").is_dir():
        shutil.copytree(Path(state["base"]) / "disclosure", dest / "disclosure", dirs_exist_ok=True)
    (dest / "author.json").write_text(json.dumps(state["messages"], indent=1) + "\n")
    record = {k: v for k, v in state.items() if k not in ("messages", "pending")}
    record["finished"] = datetime.now().isoformat(timespec="seconds")
    (dest / "run.json").write_text(json.dumps(record, indent=1) + "\n")
    state["phase"] = "done"
    save(state)
    if not keep_folder:
        shutil.rmtree(state["base"])
    print(f"Saved tests/longdemo/runs/{state['run']}.bundle and tests/longdemo/runs/{state['run']}/")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("persona", nargs="?", choices=sorted(PERSONAS))
    ap.add_argument("--paper", choices=sorted(PAPERS), default="archival")
    ap.add_argument("--resume", type=Path, help="a run folder in ~/.warranted-delegation/demos/")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the run folder after saving the run")
    args = ap.parse_args()
    if not (args.persona or args.resume):
        ap.error("name a persona, or --resume a run")
    if args.persona and args.persona not in PAPERS[args.paper]["authors"]:
        ap.error(f"the {args.paper} paper's authors are {', '.join(PAPERS[args.paper]['authors'])}")
    if args.dry_run:
        state = new_run(args.persona, dry=True, paper=args.paper)
        print(json.dumps({"run folder": state["base"], "worker": WORKER_MODEL, "author": AUTHOR_MODEL,
                          "limits": PERSONAS[args.persona], "settings": settings(state)}, indent=1))
        return
    try:
        import anthropic
    except ImportError:
        if VENV_PY.exists() and Path(sys.executable) != VENV_PY:
            os.execv(str(VENV_PY), [str(VENV_PY), __file__, *sys.argv[1:]])
        raise SystemExit("The runner needs the anthropic package; run /warrant:disclosure once to set it up.")
    subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
    state = json.loads((args.resume / "state.json").read_text()) if args.resume else new_run(args.persona, dry=False, paper=args.paper)
    print(f"Run folder: {state['base']}")
    key = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_ITEM, "-w"],
                         capture_output=True, text=True).stdout.strip()
    client = anthropic.Anthropic(api_key=key)
    deadline = time.time() + SESSION_LIMIT
    try:
        if state["phase"] == "setup":
            setup(state)
        if state["phase"] in ("author", "map"):
            author_loop(client, state, deadline)
        if state["phase"] == "read":
            read(state)
        if state["phase"] == "save":
            keep(state, args.keep)
    except Paused as why:
        save(state)
        print(f"Paused: {why}\nResume with: python3 tests/longdemo/run.py --resume {state['base']}")
        sys.exit(2)


if __name__ == "__main__":
    main()
