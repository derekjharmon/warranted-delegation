"""Capture: the instructions Claude works under, kept in the record.

A call settled in advance by a CLAUDE.md, a skill, or Claude's memory notes
doesn't show as anyone's in the conversation, so the record keeps their text
(DECISIONS.md, Oct 12 and Oct 15). Called by log_event.py; returns fields
for the log line, and stores each file's text as a sidecar through the
store() function it is given, so withholding one never changes the log.

What is kept, and when:
- "instructions", at session start and at any prompt where one of them has
  changed: the instruction files this session loads, each with its text.
  user     ~/.claude/CLAUDE.md
  ancestor CLAUDE.md or CLAUDE.local.md in a folder above the project
  project  CLAUDE.md, CLAUDE.local.md or .claude/CLAUDE.md in the project
  import   a file one of these brings in with an @path line
  memory   Claude's memory notes for this project (the MEMORY.md index and
           the notes)
  When memory notes aren't kept, the line says why: "memory_capture" is
  "off" (this copy turned it off with /warrant:setup memory off) or "not
  loaded" (the session ran with Claude Code's auto-memory turned off).
- "agent", "plugins", at session start: the Claude Code version (which
  fixes the text of the skills built into it) and any flags that changed
  what it loads, and the plugins turned on. Text that plugins add on their
  own isn't visible to the hook; the names say where it could have come
  from. MCP servers aren't listed (the author, Oct 15): any server Claude uses
  shows in the record by its tool calls' names.
- "skill", on a Skill tool call: the skill's file and text, or its name
  alone when it isn't on disk (built into Claude Code, or provided from
  elsewhere).
- "command_file", on a prompt that starts with a custom slash command: the
  command's or skill's file and text.

What a session loads depends on how Claude Code was started, so this reads
the flags of the claude process that runs the hook: --setting-sources (user
settings, which include ~/.claude/CLAUDE.md, personal skills and user-level
plugins, can be left out) and --plugin-dir. Where that
process can't be read, it assumes Claude Code's defaults.

The memory notes are found next to the session transcript, from the hook
payload's transcript_path. The transcript itself is never opened.
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
STATE = "wd-capture.json"            # in .git: the last instruction set recorded
MEMORY_KEY = "wd.capturememory"      # in .git/config: "off" turns memory capture off
FILE_MAX = 200_000                   # bytes of one file kept; full_sha256 covers it all
IMPORT_DEPTH = 5                     # how deep @path imports are followed
SOURCES = ("user", "project", "local")
# The plugin's own commands are handled by its hook, not loaded as text.
OWN = {"attest", "record", "sync", "undo", "setup", "disclosure", "trail", "withhold", "brainstorm"}

_launch = None


def launch():
    """How this session's Claude Code was started, as far as it changes what
    it loads: {"sources", "plugin_dirs"}, and whether it runs headless
    (claude -p), as a script does."""
    global _launch
    if _launch is None:
        _launch = parse_flags(claude_args())
    return _launch


def claude_args():
    """The arguments after "claude" in the nearest claude process above this
    hook, or [] when there is none or it can't be read."""
    pid = os.getppid()
    for _ in range(4):
        try:
            out = subprocess.run(["ps", "-ww", "-o", "ppid=,args=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return []
        if not out:
            return []
        ppid, _, args = out.partition(" ")
        tokens = args.split()
        at = next((i for i, t in enumerate(tokens) if Path(t).name == "claude"), None)
        if at is not None:
            return tokens[at + 1:]
        pid = int(ppid)
    return []


def parse_flags(args):
    flags = {"sources": set(SOURCES), "plugin_dirs": [], "headless": "-p" in args or "--print" in args}
    for i, arg in enumerate(args):
        value = args[i + 1] if i + 1 < len(args) else ""
        if arg == "--setting-sources":
            flags["sources"] = {s for s in value.split(",") if s in SOURCES}
        elif arg.startswith("--setting-sources="):
            flags["sources"] = {s for s in arg.split("=", 1)[1].split(",") if s in SOURCES}
        elif arg == "--plugin-dir" and value:
            flags["plugin_dirs"].append(Path(value).expanduser())
    return flags


def shown(path, repo=None):
    """A path as the record shows it: inside the project, relative to it;
    under the home folder, as ~/..."""
    for base, prefix in ((repo, ""), (HOME, "~/")):
        if base is None:
            continue
        try:
            return prefix + Path(path).relative_to(base).as_posix()
        except ValueError:
            continue
    return Path(path).as_posix()


def kept(path, kind, store, repo=None):
    """One file's entry, its text stored as a sidecar; None if unreadable."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    entry = {"kind": kind, "path": shown(path, repo)}
    if len(data) > FILE_MAX:
        entry["bytes"] = len(data)
        entry["full_sha256"] = hashlib.sha256(data).hexdigest()
        data = data[:FILE_MAX]
    entry["sha256"] = store(data.decode("utf-8", errors="replace"))
    return entry


def imports(path, seen, depth=1):
    """Files an instruction file brings in with @path lines, followed
    IMPORT_DEPTH deep. Only paths that exist count, so an email address or
    a handle never does."""
    if depth > IMPORT_DEPTH:
        return []
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return []
    text = re.sub(r"```.*?```|`[^`\n]*`", "", text, flags=re.S)  # imports don't count inside code
    found = []
    for ref in re.findall(r"(?<![\w@])@((?:~/|/|\.{1,2}/)?[\w.~/-]+)", text):
        target = (HOME / ref[2:]) if ref.startswith("~/") else (Path(path).parent / ref)
        try:
            target = target.resolve()
        except OSError:
            continue
        if target.is_file() and target not in seen:
            seen.add(target)
            found.append(target)
            found += imports(target, seen, depth + 1)
    return found


def memory_dir(repo, event):
    """This project's memory folder, beside the session transcript."""
    transcript = event.get("transcript_path")
    if transcript:
        return Path(transcript).expanduser().parent / "memory"
    return CLAUDE_DIR / "projects" / re.sub(r"[^A-Za-z0-9-]", "-", str(repo)) / "memory"


def memory_state(git):
    """None when memory notes are kept, or why they aren't."""
    if os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "").lower() in ("1", "true", "yes"):
        return "not loaded"
    if (git("config", "--local", MEMORY_KEY, check=False) or "").strip().lower() == "off":
        return "off"
    return None


# Other agents' instruction files (adapters.py names the agent): the user's
# own, then one per folder from the project's top down, the first that
# exists of the names listed (Codex reads AGENTS.override.md in place of
# AGENTS.md). Neither has memory notes the hook can find.
OTHER_AGENTS = {
    "codex-cli": {"user": [HOME / ".codex" / "AGENTS.override.md", HOME / ".codex" / "AGENTS.md"],
                  "names": ["AGENTS.override.md", "AGENTS.md"], "version": ["codex", "--version"]},
    "gemini-cli": {"user": [HOME / ".gemini" / "GEMINI.md"], "names": ["GEMINI.md"],
                   "version": ["gemini", "--version"]},
}


def other_agent_set(repo, profile, store):
    entries = []
    user = next((p for p in profile["user"] if p.is_file()), None)
    if user:
        entry = kept(user, "user", store, repo)
        entries += [entry] if entry else []
    project = next((repo / n for n in profile["names"] if (repo / n).is_file()), None)
    if project:
        entry = kept(project, "project", store, repo)
        entries += [entry] if entry else []
    return entries, None


def instruction_set(repo, event, git, store):
    """The instruction files this session loads, and why memory notes
    aren't among them (None when they are)."""
    if event.get("agent") in OTHER_AGENTS:
        return other_agent_set(repo, OTHER_AGENTS[event["agent"]], store)
    sources = launch()["sources"]
    entries, seen = [], set()

    def add(path, kind):
        path = Path(path).resolve()
        if path in seen or not path.is_file():
            return
        seen.add(path)
        entry = kept(path, kind, store, repo)
        if entry:
            entries.append(entry)
            for extra in imports(path, seen):
                entry = kept(extra, "import", store, repo)
                if entry:
                    entries.append(entry)

    if "user" in sources:
        add(CLAUDE_DIR / "CLAUDE.md", "user")
    for folder in reversed(repo.parents):
        if "project" in sources:
            add(folder / "CLAUDE.md", "ancestor")
        if "local" in sources:
            add(folder / "CLAUDE.local.md", "ancestor")
    if "project" in sources:
        add(repo / "CLAUDE.md", "project")
        add(repo / ".claude" / "CLAUDE.md", "project")
    if "local" in sources:
        add(repo / "CLAUDE.local.md", "project")
    memory = memory_state(git)
    if memory is None:
        folder = memory_dir(repo, event)
        if folder.is_dir():
            for path in sorted(folder.rglob("*.md")):
                add(path, "memory")
    return entries, memory


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def installed():
    """{plugin name: (id, version, folder)} for the plugins this session can
    load: installed ones, and any given with --plugin-dir."""
    found = {}
    for pid, copies in (read_json(CLAUDE_DIR / "plugins" / "installed_plugins.json").get("plugins") or {}).items():
        if copies:
            found[pid.split("@")[0]] = (pid, copies[-1].get("version"), copies[-1].get("installPath"))
    for folder in launch()["plugin_dirs"]:
        meta = read_json(folder / ".claude-plugin" / "plugin.json")
        if meta.get("name"):
            found[meta["name"]] = (f"{meta['name']} (--plugin-dir)", meta.get("version"), str(folder))
    return found


def enabled_plugins(repo):
    sources = launch()["sources"]
    on = {}
    for source, settings in (("user", CLAUDE_DIR / "settings.json"),
                             ("project", repo / ".claude" / "settings.json"),
                             ("local", repo / ".claude" / "settings.local.json")):
        if source in sources:
            on.update(read_json(settings).get("enabledPlugins") or {})
    have = {pid: version for pid, version, _ in installed().values()}
    names = {f"{pid} {have.get(pid) or ''}".strip() for pid, enabled in on.items() if enabled and pid in have}
    for name, (pid, version, _) in installed().items():
        if pid.endswith("(--plugin-dir)"):
            names.add(f"{pid} {version or ''}".strip())
    return sorted(names)


def agent(name="claude-code"):
    command = OTHER_AGENTS[name]["version"] if name in OTHER_AGENTS else ["claude", "--version"]
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"\d+\.\d+\.\d+", out)
        version = m.group(0) if m else None
    except Exception:
        version = None
    found = {"name": name, "version": version}
    if name in OTHER_AGENTS:
        return found
    flags = launch()
    if flags["sources"] != set(SOURCES):
        found["setting_sources"] = sorted(flags["sources"])
    return found


def find_skill(name, repo):
    """The file behind a skill or slash command name, or None."""
    name = name.strip().lstrip("/")
    if ":" in name:
        plugin, short = name.split(":", 1)
        entry = installed().get(plugin)
        roots = [Path(entry[2])] if entry and entry[2] else []
    else:
        short = name
        roots = [repo / ".claude"] + ([CLAUDE_DIR] if "user" in launch()["sources"] else [])
    for root in roots:
        for candidate in (root / "skills" / short / "SKILL.md", root / "commands" / f"{short}.md"):
            if candidate.is_file():
                return candidate
        for skill in sorted((root / "skills").glob("*/SKILL.md")):
            head = skill.read_text(errors="replace")[:1000]
            if re.search(rf"^name:\s*['\"]?{re.escape(short)}['\"]?\s*$", head, re.M):
                return skill
    return None


def skill_entry(name, repo, store):
    path = find_skill(name, repo)
    if path is None:
        return {"name": name, "path": None}
    entry = kept(path, "skill", store, repo) or {"path": shown(path, repo)}
    entry.pop("kind", None)
    return {"name": name, **entry}


def fields(event, repo, git, store, git_dir, command):
    """The capture fields for this event's log line. "_save" is the state to
    write once the line is written: (path, bytes)."""
    kind = event.get("hook_event_name")
    out = {}
    if kind == "PostToolUse" and event.get("tool_name") == "Skill":
        tool_input = event.get("tool_input") or {}
        response = event.get("tool_response") if isinstance(event.get("tool_response"), dict) else {}
        name = tool_input.get("skill") or tool_input.get("command") or response.get("commandName")
        if isinstance(name, str) and name:
            out["skill"] = skill_entry(name, repo, store)
        return out
    if kind not in ("SessionStart", "UserPromptSubmit"):
        return out
    if kind == "UserPromptSubmit" and not command:
        m = re.match(r"\s*/([\w:.-]+)", event.get("prompt") or "")
        name = m.group(1).lower() if m else ""
        if m and not name.startswith("warrant:") and name not in OWN:
            entry = skill_entry(m.group(1), repo, store)
            if entry.get("path"):
                out["command_file"] = entry
    entries, memory = instruction_set(repo, event, git, store)
    digest = hashlib.sha256(json.dumps([entries, memory], sort_keys=True).encode()).hexdigest()
    state_path = Path(git_dir) / STATE if git_dir else None
    last = read_json(state_path).get("set") if state_path else None
    if kind == "SessionStart" or digest != last:
        out["instructions"] = entries
        if memory:
            out["memory_capture"] = memory
        if state_path:
            out["_save"] = (state_path, json.dumps({"set": digest}).encode())
    if kind == "SessionStart":
        name = event.get("agent") or "claude-code"
        out["agent"] = agent(name)
        if name == "claude-code":
            out["plugins"] = enabled_plugins(repo)
    return out
