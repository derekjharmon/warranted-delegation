# The record format, for adapters

*Written by Claude, 2026-10-08, from the logger as built (`plugin/warrant/scripts/log_event.py`,
schema version 1). For the Codex and Gemini adapters, and any later agent.
Updated 2026-10-15: the brainstorm label, capture of the instructions the agent works under, and the Codex CLI and Gemini CLI adapters.*

Vendor neutrality comes from a shared record format, not from any one agent
(DECISIONS.md, Oct 1). Everything downstream (the verifier, `/warrant:attest`,
the reader, the disclosure, traced numbers, and who typed it) reads only this
record. An adapter's whole job is to produce it from another agent's session.

## The design: one logger, thin translators

The Claude Code hook already writes the record correctly: the hash chain,
sidecars, snapshots, and the commands. So an adapter should not write the
record itself. It should translate each event from its agent into the payload
the logger reads, and call the logger:

| Logger reads | What it is |
|:-|:-|
| `hook_event_name` | `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`, or `SessionEnd` |
| `session_id` | The agent's session, stable for the session |
| `prompt_id` | One id per prompt, shared by that prompt's tool calls and its `Stop`. If the agent has none, the adapter makes one at the prompt and keeps it until `Stop` |
| `prompt` | The person's exact prompt text (`UserPromptSubmit`) |
| `tool_name`, `tool_input`, `tool_response` | One tool call (`PostToolUse`). Use Claude Code's names where the tool is the same kind: a shell command is `Bash` with `tool_input.command`; a file edit is `Edit` or `Write` with `tool_input.file_path` |
| `last_assistant_message` | The agent's final message for the turn (`Stop`) |
| `cwd`, `permission_mode` | The working folder; the permission mode, if the agent has one |

The logger then handles everything below, and the commands (`/warrant:attest`,
`/warrant:record`, `/warrant:sync`, `/warrant:undo`, `/warrant:disclosure`,
`/warrant:trail`, `/warrant:withhold`, `/warrant:brainstorm`). An agent that can't define slash commands types each
command's name without the slash (`warrant:attest checked Table 2`,
`warrant:record`), which the logger accepts, as it still accepts `attest:`.

## The adapters, as built

`plugin/warrant/scripts/adapters.py` runs first in the logger and turns each
agent's event into the shape above, then turns the logger's reply into what
that agent reads. The logger tells the agents apart by their own markers.

| | Codex CLI (hooks, 0.148.0) | Gemini CLI (hooks, 0.64.0) |
| :- | :- | :- |
| Installed as | The same plugin, `plugin/warrant/`: Codex reads `.claude-plugin/plugin.json`, the marketplace file, and `hooks/hooks.json` | Not packaged in Stage 1: the extension moves to Stage 2 (DECISIONS.md, Oct 21 and 22). The adapter already reads Gemini's events, as below |
| Events | The same names | `BeforeAgent` → `UserPromptSubmit`, `AfterTool` → `PostToolUse`, `AfterAgent` → `Stop`; `SessionStart`, `SessionEnd` |
| `prompt_id` | Its `turn_id` | None given: the adapter makes one at each prompt and keeps it in `.git/wd-turns.json` until the turn ends |
| Final message | `last_assistant_message` | `prompt_response` |
| Shell | `Bash`, `tool_input.command` | `run_shell_command` → `Bash` |
| File edits | `apply_patch`, the whole patch in `tool_input.command`: the files are read from its headers into `tool_input.file_paths` | `write_file` → `Write`, `replace` → `Edit`, with `file_path` |
| Tool output | A string | `tool_response.llmContent` |
| The project | The hook's working folder (Codex doesn't name it) | `CLAUDE_PROJECT_DIR`, which Gemini sets |
| Commands | No custom slash commands: `warrant:attest` and the rest, typed as plain messages | The extension's `/warrant:attest` and the rest, which Gemini expands to `warrant:attest …` before the hook sees it |
| Blocking a command | `{"decision": "block"}`, as Claude Code | `{"decision": "deny"}`; every reply is JSON, `{}` when there's nothing to say |
| Trust | The person approves the plugin's hooks once, in `/hooks` | Installing the extension asks for consent |


## Where the record lives

| Path | What |
|:-|:-|
| `provenance/log/<log id>/events.jsonl` | One log per copy of the project, so each has a single writer and its chain never forks. The log id is the author's name plus a random suffix, kept in `.git/config` as `wd.logid` |
| `provenance/log/text/<sha256>.txt` | Sidecars: prompts, final messages, and tool outputs, named by the SHA-256 of their content. Withholding one never changes the log |
| `refs/provenance/<log id>/snapshots` | The working-tree snapshots, as a chain of commits that never touches a branch. Pushed with each save |
| `provenance/verify_log.py` | Checks every log's chain and sidecars, so anyone can verify a record without the plugin |

## A line

One JSON object per line, UTF-8, compact separators (`,` and `:` with no
spaces). The first line of a log is `LogStart`: `v`, `ts`, `event`, `log_id`,
`author`, and `prev_hash`. Every other line has:

| Field | Value |
|:-|:-|
| `v` | 1 |
| `ts` | UTC, ISO 8601 with milliseconds and `Z` |
| `session_id`, `prompt_id`, `event`, `permission_mode` | From the payload; `prompt_id` is null before the first prompt |
| `tool` | The tool's name, or null |
| `paths` | Files the event touched, relative to the project |
| `prev_hash` | SHA-256 of the previous line's exact bytes, without its newline; 64 zeros for the first line |

Plus, by event:

| Event | Extra fields |
|:-|:-|
| `UserPromptSubmit` | `prompt_sha256` (the prompt's sidecar); `snapshot` (the project as the prompt was sent, including the person's hand edits since the last turn) |
| `PostToolUse` | For a shell command, `command` (its first 500 characters) and `command_sha256` (all of it); `output_sha256` (the output's sidecar, cut to 20,000 bytes), `output_bytes`, and `output_full_sha256` when cut |
| `Stop` | `response_sha256` (the final message's sidecar); `snapshot` (the project as the turn ended) |
| `SessionStart` | `sync`, when coauthors' saves were brought in; `instructions`, `agent`, `plugins` (capture, below) |
| `UserPromptSubmit` | `instructions`, when one of them changed since last recorded; `command_file`, when the prompt starts with a custom slash command |
| `PostToolUse` of a skill | `skill`: its name, path, and text's sidecar (`path` null when it isn't on disk) |
| `UserPromptSubmit`, `PostToolUse`, `Stop` | `brainstorm`: `true`, while the brainstorm label is on in that session (below) |
| The `/warrant:brainstorm` prompt; `SessionEnd` | `brainstorm_switch`: `"on"` or `"off"`, where the label starts and stops; on `SessionEnd` when quitting turned it off |
| any | `snapshot_error` or `snapshot_skipped`, when a snapshot failed or left out files over 25 MB; `capture_error`, when capture failed |

## Capture: the instructions the agent works under

A call settled in advance by an instruction file, a skill, or the agent's
memory doesn't show as anyone's in the conversation, so the record keeps
their text as sidecars (`plugin/warrant/scripts/capture.py`). `instructions`
is a list of files, each with `kind`, `path` (inside the project, relative
to it; under the home folder, as `~/…`), and `sha256` (plus `bytes` and
`full_sha256` past 200,000 bytes). Kinds for Claude Code: `user`
(`~/.claude/CLAUDE.md`), `ancestor` (a CLAUDE.md above the project),
`project`, `import` (brought in by an `@path` line), and `memory` (the
agent's memory notes for the project). The full list is written at session
start and again whenever a file in it changes, so the set in force at any
prompt is the latest one before it. With memory capture turned off for the
copy (`/warrant:setup memory off`, kept in `.git/config` as
`wd.capturememory`), the memory notes are left out and the line says
`"memory_capture": "off"`; with Claude Code's auto-memory turned off, it says
`"not loaded"`.

What a session loads depends on how the agent was started, so capture reads
the flags of the `claude` process that runs the hook: `--setting-sources`
(leaving out `user` drops `~/.claude/CLAUDE.md`, personal skills, and
user-level plugins) and `--plugin-dir`. Where that
process can't be read, it assumes the defaults.

At session start the line also names the agent and its version (which fixes
the text of skills built into it), with `setting_sources` when it differs
from the default, and the plugins turned on. Text that plugins add on their
own isn't visible to the hook; the names say where it could have come from.
MCP servers aren't listed: any server the agent uses shows in the record by
its tool calls' names.

For Codex CLI and Gemini CLI, `instructions` lists the person's own file
(`~/.codex/AGENTS.override.md` or `~/.codex/AGENTS.md`; `~/.gemini/GEMINI.md`,
where Gemini also saves its memory) and the project's (`AGENTS.override.md` or
`AGENTS.md`; `GEMINI.md`), and `agent` names the agent and its version. Skills,
plugins, and launch flags are captured for Claude Code only.

## The brainstorm label

`/warrant:brainstorm` turns the label on or off for one conversation (a bare
command switches it; `on` and `off` set it). Quitting the agent turns it
off. A headless step ending (`claude -p`) doesn't: a script resumes the same
conversation step by step, so the label lasts until the script turns it
off.
While it is on, each turn that reaches the agent is recorded as usual, hash
chained, with `"brainstorm": true` on its lines; the plugin's own commands
are never labeled. The record keeps these turns, and the disclosure leaves
them out: the reader sets aside a turn whose prompt line carries the label.
Which sessions have it on is kept in `.git/wd-brainstorm.json`, never saved
or shared; the log is the record of it.

An adapter gets this for free by passing the prompt through to the logger
with its `session_id`, and a `SessionEnd` when the person quits. In Codex
it's `warrant:brainstorm`; in Gemini, `/warrant:brainstorm`.

## Snapshots, and why their timing matters

Before each prompt and after each turn, the logger commits the working tree,
minus `provenance/log`, ignored files, and files over 25 MB, to the snapshot
ref, using a separate index so the person's staging area is untouched. It is
made with the hook's identity, so it is never an attestation. If nothing
changed, it reuses the last snapshot.

Who typed it and the reader's trace both depend on the timing: what changed
between a turn's two snapshots is the agent's work, and what changed between
one turn's end and the next prompt is the person's. An adapter must therefore
send `UserPromptSubmit` before the agent acts on the prompt, and `Stop` after
its last edit of the turn.

## When an agent can't report something

- **No per-tool events:** there are no `PostToolUse` lines, so the record
  shows prompts, replies, and snapshots, but not the commands run or what they
  printed. Checks then can't be seen, and numbers can't trace to a recorded
  run. The disclosure must say so (Antigravity, PROGRESS.md).
- **No final message:** `response_sha256` is null.
- **The agent is named** on every `SessionStart` line (`agent`, from
  capture), so the disclosure can say which agent made a record and what that
  agent can't report.

## An adapter passes when

1. `provenance/verify_log.py` verifies its log.
2. The reader's `load_record` reads it into turns, each with its prompt, tool
   calls and outputs, final message, and before and after snapshots.
3. A scripted session runs end to end: setup, a prompt with a shell command
   and a file edit, the turn's end, a hand edit, and `/warrant:attest` (or
   `attest:`), committing with an `Attested-by:` line.
4. Who typed it credits the hand edit to the person and the file edit to the
   agent.
