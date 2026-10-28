"""Adapters: translate another agent's hook events into the payload the
logger reads (docs/record-format.md), so every agent feeds the same logger
and the same record.

normalize(event, env) returns (agent, event): the agent's name ("claude-code",
"codex-cli", or "gemini-cli") and the event in Claude Code's shape.
reply(agent, text) turns the logger's output into what that agent reads.

Codex CLI (hooks in 0.148.0) uses Claude Code's event names and fields
almost exactly. It names the turn's id turn_id, which becomes prompt_id, and
its file edits arrive as apply_patch with the whole patch in
tool_input.command, so the files are read from the patch's headers. Its hook
output is read the way Claude Code reads it ({"decision": "block", ...},
"systemMessage"), so replies pass through unchanged.

Gemini CLI (hooks in 0.64.0) has its own event and tool names and gives
hooks no turn id, so this makes one at each prompt and keeps it, in .git,
until the turn ends. A block is {"decision": "deny"}, context added for the
model comes from BeforeAgent, and hooks must print JSON, so an empty reply
becomes {}.
"""
import json
import os
import re
import uuid
from pathlib import Path

GEMINI_EVENTS = {"BeforeAgent": "UserPromptSubmit", "AfterAgent": "Stop", "AfterTool": "PostToolUse",
                 "SessionStart": "SessionStart", "SessionEnd": "SessionEnd"}
GEMINI_TOOLS = {"run_shell_command": "Bash", "write_file": "Write", "replace": "Edit", "read_file": "Read"}
TURNS = "wd-turns.json"  # in .git: Gemini's current prompt id per session
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$", re.M)


def agent_of(event, env):
    if env.get("GEMINI_SESSION_ID") or env.get("GEMINI_PROJECT_DIR") or event.get("hook_event_name") in (
            "BeforeAgent", "AfterAgent", "AfterTool", "BeforeTool", "BeforeModel", "AfterModel"):
        return "gemini-cli"
    transcript = str(event.get("transcript_path") or "")
    if "turn_id" in event or "/.codex/" in transcript or (env.get("PLUGIN_ROOT") and not env.get("CLAUDE_PROJECT_DIR")):
        return "codex-cli"
    return "claude-code"


def normalize(event, env, git_dir=None):
    agent = agent_of(event, env)
    if agent == "codex-cli":
        event = codex(event)
    elif agent == "gemini-cli":
        event = gemini(event, git_dir)
    return agent, event


def codex(event):
    event = dict(event)
    if event.get("turn_id") and not event.get("prompt_id"):
        event["prompt_id"] = event["turn_id"]
    if event.get("tool_name") == "apply_patch":
        patch = (event.get("tool_input") or {}).get("command") or ""
        files = [a or b for a, b in PATCH_FILE.findall(patch if isinstance(patch, str) else "")]
        event["tool_name"] = "Edit"
        event["tool_input"] = {"file_paths": list(dict.fromkeys(files))}
    return event


def gemini(event, git_dir):
    event = dict(event)
    name = event.get("hook_event_name")
    event["hook_event_name"] = GEMINI_EVENTS.get(name, name)
    sid = event.get("session_id") or ""
    turns = _read(git_dir)
    if name == "BeforeAgent":
        turns[sid] = uuid.uuid4().hex
        _write(git_dir, turns)
    if name in ("BeforeAgent", "AfterAgent", "AfterTool"):
        event["prompt_id"] = turns.get(sid)
    if name == "AfterAgent":
        event["last_assistant_message"] = event.get("prompt_response")
    if name == "AfterTool":
        tool = event.get("tool_name")
        event["tool_name"] = GEMINI_TOOLS.get(tool, tool)
        response = event.get("tool_response")
        if isinstance(response, dict):
            content = response.get("llmContent")
            event["tool_response"] = content if isinstance(content, str) else response
    return event


def reply(agent, text):
    """The logger's stdout, as this agent reads it."""
    if agent != "gemini-cli":
        return text
    if not text.strip():
        return "{}"
    out = json.loads(text)
    if out.get("decision") == "block":
        out["decision"] = "deny"
    if (out.get("hookSpecificOutput") or {}).get("hookEventName") == "UserPromptSubmit":
        out["hookSpecificOutput"]["hookEventName"] = "BeforeAgent"
    return json.dumps(out)


def _read(git_dir):
    try:
        return json.loads((Path(git_dir) / TURNS).read_text()) if git_dir else {}
    except Exception:
        return {}


def _write(git_dir, turns):
    if git_dir:
        path = Path(git_dir) / TURNS
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(turns))
        os.replace(tmp, path)
