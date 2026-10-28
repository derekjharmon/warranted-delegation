#!/usr/bin/env python3
"""Claude Code hook: append one hash-chained JSON line per event to this
copy's log, provenance/log/<log id>/events.jsonl.

Each copy of the project (each clone, on each computer) has its own log, so
every log has a single writer and its chain never forks. The log id is the
author's name plus a random suffix, made once and kept in .git/config
(wd.logid). A new log starts with a LogStart line naming its author.

Registered in .claude/settings.json for SessionStart, UserPromptSubmit,
PostToolUse, Stop and SessionEnd. Reads the hook payload from stdin. Each
line's prev_hash is the SHA-256 of the previous line's exact bytes (without
its newline); the first line uses GENESIS. provenance/verify_log.py checks
the chain and the sidecars.

Prompt, response and tool-output text go to sidecar files that the log
references only by SHA-256, so withholding a sidecar never changes the log:
  provenance/log/text/<sha256>.txt   a prompt, a turn's final message, or
                                     one tool call's output (cut to
                                     OUTPUT_MAX bytes)

On UserPromptSubmit and Stop, saves a snapshot of the working tree as a
commit on this copy's ref, refs/provenance/<log id>/snapshots, which never
touches a branch, and records its hash. Snapshots are made with a separate index, so the human's
staging area is untouched, and they skip provenance/log. They are made by
the hook, not the human, so they carry the hook's identity and are not
attestations. A failed snapshot is recorded as an error on the line; the
line is always written.

Runs as the hook of the warrant plugin for Claude Code. It records only in a
project that has been set up (one with provenance/log/), and stays silent
everywhere else. /warrant:setup sets a project up. People type the plugin
names (/warrant:attest); interactive Claude Code rejects the short forms as
unknown commands. The hook still answers to the short forms (/attest) where
they reach it, in headless runs and the older copied-in install, and replies
use the plugin names.

Handles /attest. A prompt that starts with "/attest" (or "attest:") is
logged like any prompt, then the work and the log are committed (with the
human's sentence, if any, as a Verified: trailer), and "/attest final" also
adds a dated tag. If the project has an online copy, coauthors' commits are
merged in first (never rebased; a conflict stops everything and changes
nothing), then the branch, the tag, and this copy's snapshots are pushed. The prompt
is then blocked, so it never reaches Claude. A failure still blocks the
prompt and says what went wrong. WD_ATTEST_DRY_RUN=1 reports what would
happen without committing.

Catches up with coauthors at the start of each session: if the project's
online copy has new saves and this copy has none of its own, they are
brought in (a fast-forward, which makes no commit), unless they touch files
with unsaved changes here. The log line for SessionStart records what came
in, and the human sees a one-line notice that is not added to Claude's
context. /sync does the same on request.

Handles /undo: reverses the work files of this author's most recent save
that hasn't been undone, as a new commit with an "Undoes:" trailer, and
pushes it. The log is never reversed. It refuses, changing nothing, when
the affected files have unsaved edits or later work changed the same lines.

Handles /record the same way: the prompt is logged and blocked, and the
human sees a plain summary of the record (last save, changes since, whether
everything is on GitHub, whether coauthors have new work, and whether the
logs verify).

Handles /brainstorm: turns the brainstorm label on or off for this session
(a bare /brainstorm switches it; "on" and "off" set it). While it is on, the
turns that reach Claude are recorded as usual, and each of their lines
carries "brainstorm": true, so the reader can set them aside. The prompt
that turns it on or off carries "brainstorm_switch", and so does the
SessionEnd line when quitting Claude Code turns it off. A headless step
(claude -p) ending doesn't turn it off: a script picks the same conversation
back up step by step, so the label lasts until the script turns it off. A
conversation resumed with the label still on shows the human a notice, and
a new conversation is never labeled. The plugin's own commands (/attest and
the rest) are never labeled. Which sessions have it on is kept in .git, never saved or shared;
the log is the record of it.

Keeps the instructions Claude works under (capture.py): the CLAUDE.md
files, Claude's memory notes for the project, and each skill's text, as
sidecars, at session start and whenever they change.

Never opens the session transcript: the response is the Stop payload's
last_assistant_message, so text Claude wrote earlier in the turn is not
recorded.

Writes nothing to stdout except a block decision for one of the plugin's
commands, or a systemMessage notice at session start: for SessionStart
and UserPromptSubmit, Claude Code adds stdout to Claude's context. Never
exits 2, which on Stop would keep Claude from stopping.
"""
import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
GENESIS = "0" * 64
# The project: Claude Code passes it to plugin hooks. An older install that
# keeps this script in the project's .claude/hooks/ still works.
_HERE = Path(__file__).resolve()
# The plugin (Claude Code and Codex) or the Gemini extension, which carries
# a synced copy of these scripts.
PLUGIN = (_HERE.parents[1] if (_HERE.parents[1] / ".claude-plugin").is_dir()
          or (_HERE.parents[1] / "gemini-extension.json").is_file() else None)
if PLUGIN is None:
    REPO = _HERE.parents[2]
else:
    REPO = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
LOG_ROOT = REPO / "provenance" / "log"
TEXT_DIR = LOG_ROOT / "text"
LEGACY_LOG = LOG_ROOT / "events.jsonl"  # outside a git repository
LOG_ID_KEY = "wd.logid"

# Keys that hold a file path in built-in tool inputs (Read/Edit/Write use
# file_path, NotebookEdit notebook_path, Grep/Glob path) and in Write/Edit
# responses (filePath).
PATH_KEYS = ("file_path", "notebook_path", "path", "filePath")

# Characters of a Bash command kept in the log; command_sha256 covers it all.
COMMAND_MAX = 500

# Bytes of a tool call's output kept in its sidecar; output_full_sha256
# covers it all when it was cut.
OUTPUT_MAX = 20_000

# Where working-tree snapshots are kept, and who they are made by.
SNAPSHOT_REF = "refs/provenance/{}/snapshots"  # filled with the log id
SNAPSHOT_INDEX = "provenance-snapshot-index"
SNAPSHOT_IDENTITY = {
    "GIT_AUTHOR_NAME": "provenance hook",
    "GIT_AUTHOR_EMAIL": "provenance-hook@localhost",
    "GIT_COMMITTER_NAME": "provenance hook",
    "GIT_COMMITTER_EMAIL": "provenance-hook@localhost",
}
SNAPSHOT_EXCLUDE = ":(exclude)provenance/log"

# Files larger than this are left out of snapshots and /attest commits, and
# the log says so. Keeps the hook fast and the repository under GitHub's
# 100 MB per-file limit.
MAX_FILE_BYTES = 25 * 1024 * 1024

# /attest: the prompt prefixes it answers to, the title length, how long a
# push may take, and the switch that reports instead of committing.
ATTEST_PREFIXES = ("/warrant:attest", "warrant:attest", "/attest", "attest:")
ATTEST_TITLE_MAX = 60
ATTEST_PUSH_TIMEOUT = 40
ATTEST_DRY_RUN = "WD_ATTEST_DRY_RUN"

# The agent whose hook this is (adapters.py): claude-code, codex-cli, or gemini-cli.
AGENT = "claude-code"

# /brainstorm: the file in .git that says which sessions have the label on.
BRAINSTORM_STATE = "wd-brainstorm.json"


def bash_fields(event):
    """For Bash events, the command (cut to COMMAND_MAX characters) and the
    SHA-256 of the full command's UTF-8 bytes. Empty for every other event,
    so other lines keep the original shape."""
    if event.get("tool_name") != "Bash":
        return {}
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return {}
    return {
        "command": command[:COMMAND_MAX],
        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
    }


def text_fields(event):
    """For UserPromptSubmit and Stop events, save the prompt or the turn's
    final message to TEXT_DIR and return its hash (null if there is no text).
    Empty for every other event, so other lines keep their shape."""
    name = event.get("hook_event_name")
    if name == "UserPromptSubmit":
        field, text = "prompt_sha256", event.get("prompt")
    elif name == "Stop":
        field, text = "response_sha256", event.get("last_assistant_message") or None
    else:
        return {}
    return {field: store_text(text) if isinstance(text, str) else None}


def output_fields(event):
    """For PostToolUse events, save the tool's output to TEXT_DIR, cut to
    OUTPUT_MAX bytes, and return its hash and full size. When the output was
    cut, also return the SHA-256 of the whole output. Empty for every other
    event."""
    if event.get("hook_event_name") != "PostToolUse":
        return {}
    response = event.get("tool_response")
    if response is None:
        return {"output_sha256": None}
    if isinstance(response, str):
        text = response
    else:
        text = json.dumps(response, ensure_ascii=False, sort_keys=True, default=str)
    data = text.encode("utf-8")
    fields = {}
    if len(data) > OUTPUT_MAX:
        fields["output_full_sha256"] = hashlib.sha256(data).hexdigest()
        text = data[:OUTPUT_MAX].decode("utf-8", errors="ignore")
    return {"output_sha256": store_text(text), "output_bytes": len(data), **fields}


def git(*args, env=None, check=True, input=None, timeout=8):
    result = subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, env=env, input=input, timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {args[0]}: {result.stderr.strip()[:200]}")
    return result.stdout.strip() if result.returncode == 0 else None


def oversized(env=None):
    """Changed or new files (not ignored, outside the log) larger than
    MAX_FILE_BYTES, relative to the index env selects."""
    listed = git("ls-files", "-z", "-m", "-o", "--exclude-standard", env=env, check=False) or ""
    big = []
    for path in listed.split("\0"):
        if not path or path.startswith("provenance/log/"):
            continue
        full = REPO / path
        if full.is_file() and full.stat().st_size > MAX_FILE_BYTES:
            big.append(path)
    return sorted(set(big))


def leave_out(paths):
    return [f":(exclude,literal){p}" for p in paths]


def snapshot_fields(event, log_id):
    """For UserPromptSubmit and Stop events, save the working tree (minus
    provenance/log) as a commit on this copy's snapshot ref and return its hash. Reuses
    the previous snapshot when nothing changed. Empty for every other event."""
    name = event.get("hook_event_name")
    if name not in ("UserPromptSubmit", "Stop") or not log_id:
        return {}
    ref = SNAPSHOT_REF.format(log_id)
    try:
        git_dir = Path(git("rev-parse", "--absolute-git-dir"))
        env = dict(os.environ, GIT_INDEX_FILE=str(git_dir / SNAPSHOT_INDEX), **SNAPSHOT_IDENTITY)
        big = oversized(env=env)
        git("add", "-A", "--", ".", SNAPSHOT_EXCLUDE, *leave_out(big), env=env)
        if big:
            literal = [f":(literal){p}" for p in big]
            # Only the snapshot's own index; the files on disk are untouched.
            git("rm", "--cached", "-f", "-q", "--ignore-unmatch", "--", *literal, env=env)
        skipped = {"snapshot_skipped": big} if big else {}
        tree = git("write-tree", env=env)
        prev = git("rev-parse", "-q", "--verify", ref + "^{commit}", check=False)
        if prev and git("rev-parse", prev + "^{tree}") == tree:
            return {"snapshot": prev, **skipped}
        parents = ["-p", prev] if prev else []
        message = f"{name} {event.get('prompt_id')}"
        commit = git("commit-tree", "--no-gpg-sign", tree, *parents, "-m", message, env=env)
        git("update-ref", ref, commit, *([prev] if prev else []))
        return {"snapshot": commit, **skipped}
    except Exception as exc:
        return {"snapshot": None, "snapshot_error": repr(exc)[:200]}


def get_log_id():
    """This copy's log id from .git/config, made on first use; None outside
    a git repository."""
    if git("rev-parse", "--git-dir", check=False) is None:
        return None
    current = git("config", "--local", LOG_ID_KEY, check=False)
    if current:
        return current
    git_dir = Path(git("rev-parse", "--absolute-git-dir"))
    with open(git_dir / "wd-logid.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = git("config", "--local", LOG_ID_KEY, check=False)
        if current:
            return current
        name = git("config", "user.name", check=False) or "unknown"
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"
        new_id = f"{slug}-{os.urandom(2).hex()}"
        git("config", "--local", LOG_ID_KEY, new_id)
        return new_id


def attest_request(event):
    """If this is an /attest prompt, return (sentence, final); else None."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return None
    prompt = event.get("prompt")
    return parse_attest(prompt) if isinstance(prompt, str) else None


def is_record(event):
    """Is this a /record prompt?"""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return False
    prompt = event.get("prompt")
    return isinstance(prompt, str) and re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)record(\s.*)?", prompt, re.I | re.S) is not None


def parse_attest(prompt):
    text = prompt.strip()
    for prefix in ATTEST_PREFIXES:
        if not text.lower().startswith(prefix):
            continue
        rest = text[len(prefix):]
        if rest and prefix.endswith("t") and not rest[0].isspace():
            return None  # "/attestation ..." is an ordinary prompt
        rest = rest.strip()
        final = rest.lower() == "final" or rest.lower().startswith(("final ", "final:"))
        if final:
            rest = rest[len("final"):].lstrip(" :").strip()
        return rest, final
    return None


def attest(sentence, final, log_id):
    """Commit the work and the log for an /attest prompt, tag a final
    version, and push if the project has an online copy. A bare /attest
    saves what is recorded with nothing added. Return the message shown to
    the human."""
    name = git("config", "user.name", check=False) or "unknown"
    today = datetime.now().date().isoformat()
    if final:
        title = f"Final version, {today}"
    elif sentence:
        title = "Attest: " + shorten(sentence)
    else:
        title = f"Attest, {today}"
    trailers = ([f"Verified: {sentence}"] if sentence else []) + [f"Attested-by: {name}"]
    message = title + "\n\n" + "\n".join(trailers) + "\n"
    tag = next_final_tag(today) if final else None
    remote, upstream = online_copy()
    big = oversized()
    left_out = (f" Left out {len(big)} file(s) over {MAX_FILE_BYTES // 2**20} MB: {', '.join(big)}. "
                "Add them to .gitignore, or keep them outside the project folder.") if big else ""
    if os.environ.get(ATTEST_DRY_RUN) == "1":
        return (f"Dry run, nothing committed. Commit message:\n{message}"
                f"Tag: {tag or 'none'}. Push to: {remote or 'nowhere (no online copy)'}.{left_out}")
    git("add", "-A", "--", ".", *leave_out(big))
    count = len((git("diff", "--cached", "--name-only") or "").splitlines())
    git("commit", "-q", "-F", "-", input=message, timeout=30)
    head = git("rev-parse", "--short", "HEAD")
    if tag:
        git("tag", "-a", tag, "-m", title)
    saved = f"Attested in commit {head} ({count} files)." + (f" Tagged {tag}." if tag else "") + left_out
    if not remote:
        return (saved + " Saved on this computer only, not backed up online. "
                "Connect the project to GitHub to anchor the record (see PROVENANCE.md).")
    merged, error = bring_in_and_push(remote, upstream, tag, log_id, name)
    if merged:
        saved += f" Brought in {merged} commit(s) from coauthors."
    if error is None:
        return saved + f" Saved to {remote_host(remote)}."
    return saved + " " + error


def record_status(log_id):
    """A plain summary of the record for /record."""
    lines = []
    last = git("log", "-1", "--format=%h|%cr|%s", check=False)
    if last:
        head, when, title = last.split("|", 2)
        lines.append(f"Last save: {title} ({head}, {when}).")
    else:
        lines.append("No saves yet. Type /attest to make the first one.")
    # Not through git(): its stripping would eat the first line's status column.
    changed = subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain", "-uall", "--", ".", ":(exclude)provenance/log"],
        capture_output=True, text=True, timeout=30).stdout
    files = [line[3:] for line in changed.splitlines() if line.strip()]
    if files:
        shown = ", ".join(files[:8]) + (f", and {len(files) - 8} more" if len(files) > 8 else "")
        lines.append(f"Changed since then: {plural(len(files), 'file')}: {shown}.")
    else:
        lines.append("No changes to your files since then.")
    big = oversized()
    if big:
        lines.append(f"Too large to save (over {MAX_FILE_BYTES // 2**20} MB): {', '.join(big)}.")
    remote, upstream = online_copy()
    if not remote:
        lines.append("Not connected to GitHub: saves stay on this computer.")
    else:
        host = remote_host(remote)
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            git("fetch", "-q", remote, env=env, timeout=15)
            reached = True
        except Exception:
            reached = False
            lines.append(f"Couldn't reach {host} just now, so this may be out of date.")
        if upstream:
            ahead = int(git("rev-list", "--count", "@{u}..HEAD", check=False) or 0)
            behind = int(git("rev-list", "--count", "HEAD..@{u}", check=False) or 0)
            lines.append(f"{plural(ahead, 'save')} not yet on {host}; your next /attest sends {'it' if ahead == 1 else 'them'}."
                         if ahead else f"Everything saved is on {host}.")
            if behind:
                lines.append(f"Coauthors have {plural(behind, 'new commit')}; your next /attest brings them in.")
            elif reached:
                lines.append("No new work from coauthors.")
        else:
            lines.append(f"Connected to {host}, but nothing has been sent yet; your next /attest sends it.")
    finals = (git("tag", "--list", "final-*", "--sort=-creatordate", check=False) or "").split()
    if finals:
        lines.append(f"Latest final version: {finals[0]}.")
    lines.append(verify_summary())
    if (git("config", "--local", "wd.capturememory", check=False) or "").lower() == "off":
        lines.append("Memory capture: off for this copy; /setup memory on turns it back on.")
    if log_id:
        lines.append(f"This copy's log: {log_id}.")
    return "\n".join(lines)


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def verify_summary():
    """One line on whether every log verifies."""
    script = REPO / "provenance" / "verify_log.py"
    if not script.exists():
        return "Couldn't check the record: provenance/verify_log.py is missing."
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    out = result.stdout.splitlines()
    events = sum(int(m.group(1)) for line in out for m in [re.match(r"OK\s+(\d+) events", line)] if m)
    logs = sum(1 for line in out if re.match(r"(OK|BROKEN)\s+\d+ events", line))
    if result.returncode == 0:
        return f"Your record checks out: {plural(events, 'event')} in {plural(logs, 'log')}, every chain intact."
    broken = next((line for line in out if line.startswith("BROKEN")), "a check failed")
    return f"Your record has a problem: {broken.removeprefix('BROKEN').strip()}"


def catch_up(announce_nothing=False):
    """Bring in coauthors' new saves by fast-forward when that is safe.
    Return (fields for the log line, message for the human or None)."""
    remote, upstream = online_copy()
    if not remote or not upstream:
        return {}, ("Not connected to GitHub, so there is nothing to bring in." if announce_nothing else None)
    host = remote_host(remote)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        git("fetch", "-q", remote, env=env, timeout=20)
        git("fetch", "-q", remote, "+refs/provenance/*:refs/provenance-remote/*",
            env=env, timeout=20, check=False)
    except Exception:
        return {}, (f"Couldn't reach {host}, so nothing was brought in." if announce_nothing else None)
    behind = int(git("rev-list", "--count", "HEAD..@{u}", check=False) or 0)
    ahead = int(git("rev-list", "--count", "@{u}..HEAD", check=False) or 0)
    if not behind:
        return {}, ("Already up to date with coauthors." if announce_nothing else None)
    saves = plural(behind, "new save")
    if ahead:
        return {"sync": {"behind": behind, "ahead": ahead, "result": "needs /attest"}}, (
            f"Coauthors have {saves}, and you have saves they don't. "
            "Your next /attest will combine them; nothing was changed now.")
    # Sidecars are named by their content, so an unsaved local copy of one the
    # coauthors saved is byte-identical; set it aside so git will bring theirs in.
    incoming = (git("diff", "--name-only", "--diff-filter=A", "HEAD", "@{u}", check=False) or "").splitlines()
    for path in incoming:
        local = REPO / path
        if path.startswith("provenance/log/text/") and local.is_file() \
                and not git("ls-files", "--", path, check=False) \
                and hashlib.sha256(local.read_bytes()).hexdigest() == local.stem:
            local.unlink()
    before = git("rev-parse", "HEAD")
    result = subprocess.run(["git", "-C", str(REPO), "merge", "-q", "--ff-only", "@{u}"],
                            capture_output=True, text=True, env=env, timeout=60)
    if result.returncode != 0:
        blocked = [line.strip() for line in result.stderr.splitlines()
                   if line.startswith(("\t", "    ")) and line.strip()]
        where = ", ".join(blocked) if blocked else result.stderr.strip()[:160]
        return {"sync": {"behind": behind, "result": "blocked"}}, (
            f"Coauthors have {saves}, but they change files you've edited and haven't saved: {where}. "
            "Nothing was changed. /attest saves your work and combines it with theirs.")
    after = git("rev-parse", "HEAD")
    changed = (git("diff", "--name-only", before, after, "--", ".", ":(exclude)provenance/log", check=False) or "").splitlines()
    shown = ", ".join(changed[:6]) + (f", and {len(changed) - 6} more" if len(changed) > 6 else "")
    return {"sync": {"behind": behind, "from": before, "to": after, "result": "brought in"}}, (
        f"Brought in {saves} from coauthors" + (f": {shown}." if changed else "."))


def is_disclosure(event):
    """Is this a /disclosure prompt? Returns its argument ('' or 'final'), or None."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return None
    prompt = event.get("prompt")
    m = re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)disclosure(?:\s+(.*))?", prompt or "", re.I | re.S)
    return (m.group(1) or "").strip() if m else None


def is_withhold(event):
    """Is this a /withhold prompt? Returns what follows it ('' if nothing), or None."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return None
    prompt = event.get("prompt")
    m = re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)withhold(?:\s+(.*))?", prompt or "", re.I | re.S)
    return (m.group(1) or "").strip() if m else None


def is_trail(event):
    """Is this a /trail prompt? Returns its argument ('' or a run's folder), or None."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return None
    prompt = event.get("prompt")
    m = re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)trail(?:\s+(.*))?", prompt or "", re.I | re.S)
    return (m.group(1) or "").strip() if m else None


def is_undo(event):
    """Is this an /undo prompt?"""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return False
    prompt = event.get("prompt")
    return isinstance(prompt, str) and re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)undo\s*", prompt, re.I) is not None


def undo(log_id):
    """Reverse this author's most recent save that hasn't been undone.
    Return the message shown to the human."""
    name = git("config", "user.name", check=False) or "unknown"
    # All of history, newest first: after catching up with a coauthor, this
    # author's latest save can sit off the main line.
    history = git("log", "--no-merges", "--date-order", "-z", "--format=%H%x1f%h%x1f%s%x1f%B", check=False) or ""
    entries = [e.split("\x1f") for e in history.split("\0") if e.strip()]
    undone = {m for *_, body in entries for m in re.findall(r"^Undoes: ([0-9a-f]+)", body, re.M)}
    target = None
    for full, short, title, body in entries:
        mine = re.search(rf"^Attested-by: {re.escape(name)}\s*$", body, re.M)
        is_undo_commit = re.search(r"^Undoes: ", body, re.M)
        if mine and not is_undo_commit and not any(full.startswith(u) for u in undone):
            target = (full, short, title)
            break
    if not target:
        return "Nothing of yours to undo."
    full, short, title = target
    if not git("rev-parse", "-q", "--verify", full + "^", check=False):
        return f"Can't undo your first save ({short}): there is nothing before it to go back to."
    patch = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--binary", full + "^", full, "--", ".", ":(exclude)provenance/log"],
        capture_output=True, timeout=60).stdout
    if not patch.strip():
        return f"Your last save ({short}, {title}) changed only the record, so there is nothing to undo."
    files = [f for f in (git("diff", "--name-only", full + "^", full, "--", ".", ":(exclude)provenance/log",
                             check=False) or "").split("\n") if f]
    dirty = sorted(set((git("diff", "--name-only", "--", *files, check=False) or "").split("\n")
                       + (git("diff", "--cached", "--name-only", "--", *files, check=False) or "").split("\n")) - {""})
    if dirty:
        return (f"Can't undo {short} ({title}): you have unsaved edits to {', '.join(dirty)}. "
                "Nothing was changed. Save them with /attest or set them aside first.")
    check = subprocess.run(["git", "-C", str(REPO), "apply", "-R", "--check", "--index", "-"],
                           input=patch, capture_output=True, timeout=60)
    if check.returncode != 0:
        return (f"Can't undo {short} ({title}) cleanly: later work changed the same lines in "
                f"{', '.join(files)}. Nothing was changed.")
    if os.environ.get(ATTEST_DRY_RUN) == "1":
        return f"Dry run, nothing changed. Would undo {short} ({title}), reversing changes to {', '.join(files)}."
    subprocess.run(["git", "-C", str(REPO), "apply", "-R", "--index", "-"],
                   input=patch, capture_output=True, timeout=60, check=True)
    git("add", "--", "provenance/log")
    message = f"Undo: {title} ({short})\n\nUndoes: {full}\nAttested-by: {name}\n"
    git("commit", "-q", "-F", "-", input=message, timeout=30)
    head = git("rev-parse", "--short", "HEAD")
    tags = (git("tag", "--points-at", full, "--list", "final-*", check=False) or "").split()
    reply = f"Undid {short} ({title}) in a new save, {head}: reversed changes to {', '.join(files)}."
    if tags:
        reply += f" It was tagged {tags[0]}; that tag stays in history, and the next /attest final marks a new final."
    remote, upstream = online_copy()
    if not remote:
        return reply + " Saved on this computer only."
    merged, error = bring_in_and_push(remote, upstream, None, log_id, name)
    return reply + (f" Saved to {remote_host(remote)}." if error is None else " " + error)


def brainstorm_request(event):
    """If this is a /brainstorm prompt, return what follows it ('', 'on',
    'off', or anything else typed); else None."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return None
    prompt = event.get("prompt")
    m = re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)brainstorm(?:\s+(.*))?", prompt if isinstance(prompt, str) else "", re.I | re.S)
    return (m.group(1) or "").strip().lower() if m else None


def brainstorm_file():
    git_dir = git("rev-parse", "--absolute-git-dir", check=False)
    return Path(git_dir) / BRAINSTORM_STATE if git_dir else None


def brainstorm_sessions(path):
    """Sessions with the label on: {session_id: {"since": ts, "turns": n}}."""
    try:
        sessions = json.loads(path.read_text())
    except Exception:
        return {}
    return sessions if isinstance(sessions, dict) else {}


def brainstorm(event, request, command):
    """Apply the brainstorm label to this event. Return (fields for its log
    line, a reply for a /brainstorm prompt or None, the sessions to save
    once the line is written or None). command: this prompt is one of the
    plugin's own commands, which are never labeled."""
    path = brainstorm_file()
    if path is None:
        return {}, ("The brainstorm label needs a git project." if request is not None else None), None
    sessions = brainstorm_sessions(path)
    sid = event.get("session_id") or ""
    on = sid in sessions
    kind = event.get("hook_event_name")
    if request is not None:
        if request not in ("", "on", "off"):
            return {}, "Type /brainstorm by itself to turn the label on or off, then type your prompt.", None
        want = not on if request == "" else request == "on"
        if want == on:
            return {}, f"The brainstorm label is already {'on' if on else 'off'} in this conversation.", None
        if want:
            sessions[sid] = {"since": now(), "turns": 0}
            return {"brainstorm_switch": "on"}, (
                "Brainstorm label on. The record keeps these turns as usual, and the disclosure leaves them "
                "out. It stays on until you type /brainstorm again or quit Claude Code."), sessions
        turns = sessions.pop(sid).get("turns", 0)
        return {"brainstorm_switch": "off"}, (
            f"Brainstorm label off, after {plural(turns, 'turn')}. The record keeps "
            f"{'it' if turns == 1 else 'them'}; the disclosure leaves {'it' if turns == 1 else 'them'} out."), sessions
    if kind == "SessionEnd" and on and not headless():
        # Quitting Claude Code ends the brainstorm (the author, Oct 15).
        sessions.pop(sid)
        return {"brainstorm_switch": "off"}, None, sessions
    if on and kind == "UserPromptSubmit" and command:
        # Claude's steps in a command's turn (setup's questions, narrating the
        # disclosure) belong to the command, so they aren't labeled either.
        sessions[sid]["command_turn"] = event.get("prompt_id")
        return {}, None, sessions
    if not on or command or kind == "SessionEnd":
        return {}, None, None
    if event.get("prompt_id") and event.get("prompt_id") == sessions[sid].get("command_turn"):
        return {}, None, None
    if kind == "SessionStart":
        # A resumed conversation: say so, as a notice the human sees.
        return {}, "The brainstorm label is still on in this conversation. " + brainstorm_status(sid), None
    if kind == "UserPromptSubmit":
        sessions[sid]["turns"] = sessions[sid].get("turns", 0) + 1
        sessions[sid].pop("command_turn", None)
        return {"brainstorm": True}, None, sessions
    return {"brainstorm": True}, None, None


def headless():
    """Is this session headless Claude Code (claude -p), as a script runs it?
    False where that can't be read, so quitting still ends the label."""
    try:
        sys.path.insert(0, str(_HERE.parent))
        import capture
        return capture.launch()["headless"]
    except Exception:
        return False


def brainstorm_status(session_id):
    """A line for /record when this session has the label on, else None."""
    path = brainstorm_file()
    entry = brainstorm_sessions(path).get(session_id or "") if path else None
    if not entry:
        return None
    since = datetime.fromisoformat(entry["since"].replace("Z", "+00:00")).astimezone()
    return (f"Brainstorm label: on in this conversation since {since.strftime('%I:%M %p').lstrip('0')}, "
            f"{plural(entry.get('turns', 0), 'turn')} so far; /brainstorm turns it off.")


def capture_fields(event, command):
    """The instructions Claude works under, from capture.py: fields for this
    line. {} where capture.py isn't installed (the older, copied-in install)."""
    try:
        sys.path.insert(0, str(_HERE.parent))
        import capture
    except ImportError:
        return {}
    git_dir = git("rev-parse", "--absolute-git-dir", check=False)
    return capture.fields(event, REPO, git, store_text, git_dir, command)


def is_sync(event):
    """Is this a /sync prompt?"""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return False
    prompt = event.get("prompt")
    return isinstance(prompt, str) and re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)sync(\s.*)?", prompt, re.I | re.S) is not None


def shorten(sentence):
    text = sentence.rstrip(" .")
    if len(text) <= ATTEST_TITLE_MAX:
        return text
    cut = text[:ATTEST_TITLE_MAX].rsplit(" ", 1)[0]
    return cut + "..."


def next_final_tag(today):
    base, n = f"final-{today}", 1
    tag = base
    while git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False):
        n += 1
        tag = f"{base}-{n}"
    return tag


def online_copy():
    """Return (remote, has_upstream): the remote the current branch tracks,
    else "origin" if it exists, else (None, False)."""
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    if upstream and "/" in upstream:
        return upstream.split("/", 1)[0], True
    remotes = (git("remote", check=False) or "").split()
    return ("origin" if "origin" in remotes else None), False


def remote_host(remote):
    url = git("remote", "get-url", remote, check=False) or ""
    if "github.com" in url:
        return "GitHub"
    if "gitlab.com" in url:
        return "GitLab"
    return f"the remote '{remote}'"


def bring_in_and_push(remote, upstream, tag, log_id, name):
    """Bring in coauthors' commits (moving forward when there is nothing to
    combine, otherwise with a merge commit signed by this author), then push
    the branch, the tag, and this copy's snapshots. Return (commits merged, None) or
    (commits merged, a message for the human). Never rebases, never forces,
    and never prompts for credentials. On a conflict, the merge is undone and
    nothing is pushed."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    host = remote_host(remote)
    try:
        git("fetch", "-q", remote, env=env, timeout=ATTEST_PUSH_TIMEOUT)
        # Coauthors' snapshots, kept apart from this copy's own refs.
        git("fetch", "-q", remote, "+refs/provenance/*:refs/provenance-remote/*",
            env=env, timeout=ATTEST_PUSH_TIMEOUT, check=False)
    except Exception as exc:
        return 0, (f"Saved on this computer, but {host} couldn't be reached ({str(exc)[:120]}). "
                   "The attestation still counts and goes up with the next /attest.")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    theirs = "@{u}" if upstream else (
        f"{remote}/{branch}" if git("rev-parse", "-q", "--verify", f"refs/remotes/{remote}/{branch}", check=False) else None)
    merged = 0
    if theirs:
        merged = int(git("rev-list", "--count", f"HEAD..{theirs}") or 0)
    if merged:
        result = subprocess.run(
            ["git", "-C", str(REPO), "merge", "-q",
             "-m", "Bring in coauthors' work", "-m", f"Attested-by: {name}", theirs],
            capture_output=True, text=True, env=env, timeout=60)
        if result.returncode != 0:
            conflicts = (git("diff", "--name-only", "--diff-filter=U", check=False) or "").split()
            git("merge", "--abort", check=False)
            where = ", ".join(conflicts) if conflicts else result.stderr.strip()[:160]
            return 0, (f"Saved on this computer, but coauthors' newer work conflicts with yours in: {where}. "
                       "Nothing was merged or pushed. Bring in their work and combine the changes "
                       "(Claude can help), then /attest again.")
    steps = [["push", "-q"] if upstream else ["push", "-q", "-u", remote, "HEAD"]]
    if tag:
        steps.append(["push", "-q", remote, tag])
    snapshots = SNAPSHOT_REF.format(log_id) if log_id else None
    if snapshots and git("rev-parse", "-q", "--verify", snapshots, check=False):
        steps.append(["push", "-q", remote, f"{snapshots}:{snapshots}"])
    try:
        for step in steps:
            git(*step, env=env, timeout=ATTEST_PUSH_TIMEOUT)
    except Exception as exc:
        return merged, (f"Saved on this computer, but the push to {host} failed ({str(exc)[:120]}). "
                        "The attestation still counts and goes up with the next /attest.")
    return merged, None


def store_text(text):
    """Save text to TEXT_DIR, named by the SHA-256 of its UTF-8 bytes, and
    return that hash."""
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    path = TEXT_DIR / f"{digest}.txt"
    if not path.exists():
        write_file(path, data)
    return digest


def write_file(path, data):
    """Write via a temporary file, so a sidecar is never left half-written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def touched_paths(event):
    base = Path(event.get("cwd") or REPO)
    paths = []
    for source in (event.get("tool_input"), event.get("tool_response")):
        if not isinstance(source, dict):
            continue
        for key in PATH_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value:
                p = relative_to_repo(base / value)
                if p not in paths:
                    paths.append(p)
        for value in source.get("file_paths") or []:  # a patch's files (adapters.py)
            p = relative_to_repo(base / value)
            if isinstance(value, str) and value and p not in paths:
                paths.append(p)
    return paths


def relative_to_repo(path):
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return os.path.normpath(path)


def last_line(f):
    """Return the final line of the open file (without its newline), or None."""
    f.seek(0, 2)
    end = f.tell()
    if end == 0:
        return None
    size = 4096
    while True:
        start = max(0, end - size)
        f.seek(start)
        tail = f.read(end - start)
        if tail.endswith(b"\n"):
            tail = tail[:-1]
        cut = tail.rfind(b"\n")
        if cut != -1 or start == 0:
            return tail[cut + 1:]
        size *= 2


def main(raw):
    event = json.loads(raw)
    request = attest_request(event)
    wants_record = is_record(event)
    wants_sync = is_sync(event)
    wants_undo = is_undo(event)
    wants_disclosure = is_disclosure(event) if PLUGIN is not None else None
    wants_trail = is_trail(event) if PLUGIN is not None else None
    wants_withhold = is_withhold(event) if PLUGIN is not None else None
    wants_brainstorm = brainstorm_request(event)
    command = (request is not None or wants_record or wants_sync or wants_undo or wants_disclosure is not None
               or wants_trail is not None or wants_withhold is not None or is_setup(raw) is not None)
    starting = event.get("hook_event_name") == "SessionStart"
    reply = None
    notice = None
    log_id = get_log_id()
    log = LOG_ROOT / log_id / "events.jsonl" if log_id else LEGACY_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a+b") as f:
        # Parallel tool calls fire hooks concurrently; serialize so each
        # line chains to the one actually before it. Sidecars and snapshots
        # are written under the same lock, before the line that references
        # them.
        fcntl.flock(f, fcntl.LOCK_EX)
        prev = last_line(f)
        if prev is None and log_id:
            # A new log: its first line says whose it is.
            start = {
                "v": SCHEMA_VERSION,
                "ts": now(),
                "event": "LogStart",
                "log_id": log_id,
                "author": git("config", "user.name", check=False),
                "prev_hash": GENESIS,
            }
            prev = json.dumps(start, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            f.write(prev + b"\n")
        sync_fields = {}
        if starting or wants_sync:
            try:
                sync_fields, message = catch_up(announce_nothing=wants_sync)
            except Exception as exc:
                sync_fields, message = {"sync": {"result": "error"}}, (
                    f"Couldn't check for coauthors' work: {exc}." if wants_sync else None)
            if wants_sync:
                reply = message
            else:
                notice = message
        try:
            brainstorm_fields, brainstorm_reply, sessions = brainstorm(event, wants_brainstorm, command)
        except Exception as exc:
            # The label must never stop a line being written. An unlabeled
            # turn is the safe failure: the disclosure then includes it.
            brainstorm_fields, sessions = {}, None
            brainstorm_reply = f"Couldn't change the brainstorm label: {exc!r}."
        if wants_brainstorm is not None:
            reply = brainstorm_reply
        elif starting and brainstorm_reply:
            notice = f"{notice} {brainstorm_reply}" if notice else brainstorm_reply
        try:
            captured = capture_fields(event, command or wants_brainstorm is not None)
        except Exception as exc:
            captured = {"capture_error": repr(exc)[:200]}
        capture_state = captured.pop("_save", None)
        record = {
            "v": SCHEMA_VERSION,
            "ts": now(),
            "session_id": event.get("session_id"),
            # Shared by a prompt's UserPromptSubmit, tool calls and Stop, so
            # it pairs prompts with responses. Null before the first prompt.
            "prompt_id": event.get("prompt_id"),
            "event": event.get("hook_event_name"),
            # Absent from SessionStart payloads, so null there.
            "permission_mode": event.get("permission_mode"),
            "tool": event.get("tool_name"),
            "paths": touched_paths(event),
            **bash_fields(event),
            **text_fields(event),
            **output_fields(event),
            **snapshot_fields(event, log_id),
            **sync_fields,
            **brainstorm_fields,
            **captured,
            "prev_hash": hashlib.sha256(prev).hexdigest() if prev is not None else GENESIS,
        }
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        f.write(line + b"\n")
        f.flush()
        if capture_state is not None:
            try:
                write_file(*capture_state)
            except Exception:
                pass  # the next prompt records the set again
        if sessions is not None:
            try:
                write_file(brainstorm_file(), json.dumps(sessions).encode("utf-8"))
            except Exception as exc:
                if wants_brainstorm is not None:
                    reply = f"Couldn't change the brainstorm label: {exc!r}."

        # Still under the lock, so the commit includes this line.
        if wants_undo:
            try:
                reply = undo(log_id)
            except Exception as exc:
                reply = f"Undo not completed: {exc}. Check git status; nothing was pushed."
        if request is not None:
            try:
                reply = attest(*request, log_id)
            except Exception as exc:
                reply = (f"Attestation not completed: {exc}. Check git status; "
                         "nothing was pushed.")
    if wants_record:
        try:
            reply = record_status(log_id)
            label = brainstorm_status(event.get("session_id"))
            if label:
                reply += "\n" + label
            if PLUGIN is not None:
                sys.path.insert(0, str(_HERE.parent))
                import disclose
                line = disclose.latest(REPO)
                if line:
                    reply += "\n" + line
        except Exception as exc:
            reply = f"Couldn't summarize the record: {exc}."
    context = None
    if wants_disclosure is not None:
        sys.path.insert(0, str(_HERE.parent))
        import disclose
        try:
            # Claude asks what isn't settled yet, then narrates the run as it
            # goes (DECISIONS.md, Oct 16); headless, it runs in the
            # background as before, with the defaults.
            reply, context = disclose.start(REPO, PLUGIN, wants_disclosure, narrate=not headless(), agent=AGENT)
        except Exception as exc:
            reply = f"Couldn't start the disclosure: {exc!r}."
    if wants_withhold is not None:
        sys.path.insert(0, str(_HERE.parent))
        try:
            import withhold
            # Shown to the person only, so what they're withholding isn't copied into the record.
            reply = withhold.run(REPO, git("rev-parse", "--absolute-git-dir", check=False), wants_withhold,
                                 hashlib.sha256(event["prompt"].encode("utf-8")).hexdigest())
        except Exception as exc:
            reply = f"Couldn't search the record: {exc!r}."
    if wants_trail is not None:
        sys.path.insert(0, str(_HERE.parent))
        try:
            import trail
            # Claude draws it, so the person sees it happen; headless, the hook does.
            reply, context = trail.start(REPO, PLUGIN, wants_trail, narrate=not headless())
        except Exception as exc:
            reply = f"Couldn't draw the paper trail: {exc!r}."
    if context is not None:
        hand_off(context)
    elif reply is not None:
        block(reply)
    elif notice is not None:
        # Shown to the human at session start; not added to Claude's context.
        print(json.dumps({"systemMessage": plugin_names(notice)}))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def plugin_names(text):
    """In the plugin, replies name its commands as the person types them:
    /warrant:attest in Claude Code, warrant:attest in Codex, which has no
    custom slash commands."""
    if PLUGIN is None:
        return text
    named = re.sub(r"(?<![\w:/])/(attest|record|sync|undo|setup|disclosure|trail|withhold|brainstorm)\b", r"/warrant:\1", text)
    return re.sub(r"(?<![\w])/warrant:", "warrant:", named) if AGENT == "codex-cli" else named


def block(reason):
    """Stop one of the plugin's commands (/attest, /record, /sync, /undo,
    /disclosure, /trail, /withhold, /brainstorm) from reaching Claude, and show the human the
    result."""
    tool = {"codex-cli": "Codex", "gemini-cli": "Gemini"}.get(AGENT, "Claude")
    print(json.dumps({"decision": "block", "reason": plugin_names(reason) + f" {tool} did not see this."}))


def hand_off(context):
    """Let one of the plugin's commands (/setup, /disclosure, /trail) reach Claude,
    with the hook's instructions for it added to Claude's context: setup's
    questions, and narrating the disclosure (DECISIONS.md, Oct 16)."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": plugin_names(context)}}))


def older_install(repo):
    """Does the project's own settings file still run a copied-in log_event.py?"""
    try:
        hooks = json.loads((repo / ".claude" / "settings.json").read_text()).get("hooks", {})
    except Exception:
        return False
    return any("log_event.py" in h.get("command", "") for groups in hooks.values()
               for g in groups for h in g.get("hooks", []))


def is_setup(raw):
    try:
        prompt = json.loads(raw).get("prompt")
    except Exception:
        return None
    m = re.fullmatch(r"\s*(?:/(?:warrant:)?|warrant:)setup(?:\s+(.*))?", prompt or "", re.I | re.S)
    return (m.group(1) or "").strip() if m else None


def translate(raw):
    """Another agent's event in Claude Code's shape (adapters.py), with the
    project set from its working folder where the agent doesn't name it."""
    global AGENT, REPO, LOG_ROOT, TEXT_DIR, LEGACY_LOG
    try:
        event = json.loads(raw)
    except Exception:
        return raw
    sys.path.insert(0, str(_HERE.parent))
    import adapters
    if PLUGIN is not None and not os.environ.get("CLAUDE_PROJECT_DIR") and event.get("cwd"):
        top = subprocess.run(["git", "-C", event["cwd"], "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True).stdout.strip()
        REPO = Path(top or event["cwd"]).resolve()
        LOG_ROOT = REPO / "provenance" / "log"
        TEXT_DIR = LOG_ROOT / "text"
        LEGACY_LOG = LOG_ROOT / "events.jsonl"
    git_dir = git("rev-parse", "--absolute-git-dir", check=False)
    AGENT, event = adapters.normalize(event, os.environ, git_dir)
    event["agent"] = AGENT
    return json.dumps(event)


def run_hook(raw):
    """Everything the hook does with one event; prints its reply."""
    setup_args = is_setup(raw) if PLUGIN is not None else None
    if setup_args is not None:
        sys.path.insert(0, str(_HERE.parent))
        import setup
        handover = older_install(REPO)  # the older hook logs this prompt itself
        try:
            reply, done = setup.run(REPO, PLUGIN, setup_args)
            ask = done and not headless()
            if done and not ask:
                reply += "\n" + setup.defaults(REPO, AGENT) + "\nType /attest to make your first save."
        except Exception as exc:
            reply, ask = f"Setup failed: {exc!r}. Nothing more was changed.", False
        if (REPO / "provenance" / "log").is_dir() and not handover:
            try:
                main(raw)  # record the setup prompt in the log
            except Exception:
                pass
        if ask:
            # Claude asks setup's questions, so the author's choices are
            # prompted and clear (DECISIONS.md, Oct 16).
            hand_off(setup.questions(REPO, PLUGIN, AGENT, reply))
        else:
            block(reply)
        sys.exit(0)
    if PLUGIN is not None and not (REPO / "provenance" / "log").is_dir():
        # Not a warrant project: record nothing. A command still gets an answer.
        if re.search(r'"prompt"\s*:\s*"\s*((/(warrant:)?|warrant:)(attest|record|sync|undo|disclosure|trail|withhold|brainstorm)\b|attest:)', raw, re.I):
            block("This project isn't set up for warranted delegation yet. Type /warrant:setup first.")
        sys.exit(0)
    if PLUGIN is not None and older_install(REPO):
        # The project's own copied-in hook still records here; recording twice
        # would log every event twice. Stay silent until /warrant:setup.
        if re.search(r'"prompt"\s*:\s*"\s*/?warrant:(attest|record|sync|undo|disclosure|trail|withhold|brainstorm)\b', raw, re.I):
            block("This project still uses the older, copied-in recorder, so the plugin is standing aside. "
                  "Type /warrant:setup once to switch it over, then restart Claude Code.")
        sys.exit(0)
    try:
        main(raw)
    except Exception as exc:
        # An /attest prompt must never reach Claude, even when logging fails.
        try:
            prompt = json.loads(raw).get("prompt")
            is_attest = isinstance(prompt, str) and parse_attest(prompt) is not None
        except Exception:
            # Unparseable payload: look for an /attest prompt in the raw text.
            is_attest = re.search(r'"prompt"\s*:\s*"\s*((/(warrant:)?|warrant:)attest\b|attest:)', raw, re.I) is not None
        if is_attest:
            block(f"Attestation failed before it was recorded: {exc!r}. Nothing was committed.")
            sys.exit(0)
        if re.search(r'"prompt"\s*:\s*"\s*(/(warrant:)?|warrant:)brainstorm\b', raw, re.I):
            block(f"Couldn't change the brainstorm label: {exc!r}.")
            sys.exit(0)
        if re.search(r'"prompt"\s*:\s*"\s*(/(warrant:)?|warrant:)(record|sync|undo|disclosure|trail|withhold)\b', raw, re.I):
            block(f"Couldn't summarize the record: {exc!r}.")
            sys.exit(0)
        print(f"provenance log_event.py failed: {exc!r}", file=sys.stderr)  # exit 1 = non-blocking
        sys.exit(1)


if __name__ == "__main__":
    raw = translate(sys.stdin.read())
    captured, code = io.StringIO(), 0
    with contextlib.redirect_stdout(captured):
        try:
            run_hook(raw)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
    sys.path.insert(0, str(_HERE.parent))
    import adapters
    out = adapters.reply(AGENT, captured.getvalue())
    if out:
        sys.stdout.write(out if out.endswith("\n") else out + "\n")
    sys.exit(code)
