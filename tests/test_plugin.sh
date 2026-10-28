#!/bin/sh
# Test the warrant plugin (plugin/warrant/) before anyone installs it.
#
# Everything happens in a throwaway folder, with a throwaway git config in
# place of yours (GIT_CONFIG_GLOBAL), and is deleted at the end (KEEP=1 keeps
# it). The hook makes real commits, but only in the throwaway projects.
# Nothing goes online: GitHub is skipped. This repository is never touched.
#
# Part A feeds the plugin's hook made-up events, as tests/test_multiauthor.sh
# does: setup, silence outside set-up projects, /warrant:attest, the bare
# /attest the hook still accepts (headless runs, older installs),
# /warrant:record, /warrant:brainstorm, capture of the instructions Claude
# works under (with a stand-in home folder), and moving an older copied-in
# install over.
# Part B runs Claude Code itself with the plugin loaded (--plugin-dir), to
# check the hooks are wired: setup and two saves make no model call; one
# short prompt makes one small model call on your Claude Code account.
#
# Usage: sh tests/test_plugin.sh
set -u

SRC=$(cd "$(dirname "$0")/.." && pwd -P)
PLUGIN="$SRC/plugin/warrant"
T=$(mktemp -d "${TMPDIR:-/tmp}/wd-plugin-test.XXXXXX")
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL="$T/gitconfig" WD_SETUP_SKIP_GITHUB=1
: > "$GIT_CONFIG_GLOBAL"
failures=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
expect() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

# hook DIR EVENT [PROMPT]: send one made-up event to the plugin's hook, as
# Claude Code would for a session in DIR. Prints the hook's reply, if any.
# The session is "test" unless WD_TEST_SESSION names another (set it in a
# subshell: sh keeps a variable set before a function call).
hook() {
	dir=$1 event=$2 prompt=${3:-}
	payload=$(python3 -c 'import json,os,sys,uuid; print(json.dumps({"session_id": os.environ.get("WD_TEST_SESSION", "test"), "prompt_id": uuid.uuid4().hex, "hook_event_name": sys.argv[2], "permission_mode": "default", "prompt": sys.argv[3], "cwd": sys.argv[1], "last_assistant_message": "ok"}))' "$dir" "$event" "$prompt")
	(cd "$dir" && printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$dir" CLAUDE_PLUGIN_ROOT="$PLUGIN" python3 "$PLUGIN/scripts/log_event.py")
}
# send DIR JSON: send a hand-written payload, as Claude Code would.
send() { (cd "$1" && printf '%s' "$2" | CLAUDE_PROJECT_DIR="$1" CLAUDE_PLUGIN_ROOT="$PLUGIN" python3 "$PLUGIN/scripts/log_event.py"); }
# last DIR CONDITION: a Python condition on the newest line of DIR's log (l);
# side(sha) reads a sidecar.
last() { tail -n 1 "$1"/provenance/log/*/events.jsonl | python3 -c '
import json, sys
from pathlib import Path
l = json.loads(sys.stdin.read())
side = lambda h: (Path(sys.argv[1]) / "provenance/log/text" / (h + ".txt")).read_text()
sys.exit(0 if eval(sys.argv[2]) else 1)' "$1" "$2"; }
# reason: what the hook said, whether it stopped the prompt (a reply for the
# person) or let it through with instructions added to Claude's context.
reason() { python3 -c 'import json,sys; t=sys.stdin.read(); d=json.loads(t) if t.strip() else {}; print(d.get("reason") or (d.get("hookSpecificOutput") or {}).get("additionalContext") or "")'; }
# context: only the instructions added to Claude's context, if any.
context() { python3 -c 'import json,sys; t=sys.stdin.read(); d=json.loads(t) if t.strip() else {}; print((d.get("hookSpecificOutput") or {}).get("additionalContext") or "")'; }
# answer DIR ARGS: save answers to setup's questions, as Claude does.
answer() { dir=$1; shift; python3 "$PLUGIN/scripts/setup.py" save "$dir" "$@"; }
# drain OUT: follow a disclosure run, as Claude does, until it ends; print all it said.
drain() { said=""; for i in 1 2 3 4 5 6 7 8 9 10; do s=$(python3 "$PLUGIN/scripts/disclose.py" follow "$1"); said="$said
$s"; echo "$s" | grep -qE "^(Done in|The run failed|The run stopped)" && break; done; echo "$said"; }
events() { cat "$1"/provenance/log/*/events.jsonl 2>/dev/null | wc -l | tr -d ' '; }
# field DIR KEY: KEY on the newest line of DIR's log, or "-" when absent.
field() { tail -n 1 "$1"/provenance/log/*/events.jsonl | python3 -c 'import json,sys; v=json.loads(sys.stdin.read()).get(sys.argv[1]); print("-" if v is None else str(v).lower())' "$2"; }

echo "Working in $T"

if [ -d "$SRC/checklists" ] && [ -f "$SRC/provenance/verify_log.py" ]; then
echo "== A0. The plugin carries the project's current checklists and verifier"
expect "the plugin's checklists match checklists/" 'cmp -s "$SRC/checklists/judgment-decisions.md" "$PLUGIN/checklists/judgment-decisions.md" && cmp -s "$SRC/checklists/checkable-claims.md" "$PLUGIN/checklists/checkable-claims.md"'
expect "the plugin's verify_log.py matches provenance/verify_log.py" 'cmp -s "$SRC/provenance/verify_log.py" "$PLUGIN/scripts/verify_log.py"'
else
	echo "(skipped: this copy has no separate checklists/ or provenance/ to compare)"
fi

echo "== A1. A project that isn't set up stays unrecorded"
mkdir "$T/plain" && git -C "$T/plain" init -q -b main
hook "$T/plain" SessionStart > /dev/null
hook "$T/plain" UserPromptSubmit "hello" > /dev/null
r=$(hook "$T/plain" UserPromptSubmit "/warrant:attest" | reason)
expect "no record is created" '[ ! -e "$T/plain/provenance" ]'
expect "a command says to run setup first" 'echo "$r" | grep -q "Type /warrant:setup first"'

echo "== A2. /warrant:setup asks for a name, sets the project up, then hands Claude its questions"
mkdir "$T/proj" && printf 'draft\n' > "$T/proj/paper.md"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:setup" | reason)
expect "without a name and email, setup asks for them" 'echo "$r" | grep -q "Type /warrant:setup Your Name"'
expect "and changes nothing yet" '[ ! -e "$T/proj/provenance" ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:setup Test Author <test@example.invalid>" | context)
expect "setup reports success" 'echo "$r" | grep -q "Set up for warranted delegation"'
expect "then lets the prompt reach Claude, with setup's questions and the command that saves the answers" 'echo "$r" | grep -q "^warrant:setup\." && echo "$r" | grep -q "Which tool do you use for this project?" && echo "$r" | grep -q "Options: Claude Code; Codex; Gemini" && echo "$r" | grep -q "scripts/setup.py\" save \".*/proj\" tool="'
expect "setup asks about recording (memory notes), not how the disclosure reaches Claude, which waits for the first disclosure" 'echo "$r" | grep -q "keep Claude.s memory notes" && ! echo "$r" | grep -q "How should the disclosure reach Claude"'
expect "git knows the name" '[ "$(git -C "$T/proj" config user.name)" = "Test Author" ]'
expect "the record folder exists" '[ -d "$T/proj/provenance/log" ]'
expect "verify_log.py is in the project" '[ -f "$T/proj/provenance/verify_log.py" ]'
expect "the commit rules are on" '[ "$(git -C "$T/proj" config core.hooksPath)" = ".githooks" ] && [ -x "$T/proj/.githooks/commit-msg" ]'
expect "data stays out (.gitignore)" 'grep -q "warranted delegation: data stays out" "$T/proj/.gitignore"'
expect "settings name the plugin" 'grep -q "warrant@warranted-delegation" "$T/proj/.claude/settings.json"'
expect "settings keep Claude from committing" 'grep -q "Bash(git commit \*)" "$T/proj/.claude/settings.json"'
expect "the setup prompt is in the new log" '[ "$(events "$T/proj")" -ge 2 ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:setup" | reason)
expect "running setup again changes nothing" 'echo "$r" | grep -q "Already set up"'
r=$(answer "$T/proj" tool=vscode)
expect "an answer setup doesn't know saves nothing" 'echo "$r" | grep -q "Nothing saved" && [ ! -e "$T/proj/provenance/settings.json" ]'
r=$(answer "$T/proj" tool=claude-code reader=api memory=off)
expect "the answers are saved: the tool with the project, the reader and memory for this copy" 'echo "$r" | grep -q "^Saved\." && grep -q "\"tool\": \"claude-code\"" "$T/proj/provenance/settings.json" && [ "$(git -C "$T/proj" config wd.readerpath)" = api ] && [ "$(git -C "$T/proj" config wd.capturememory)" = off ] && echo "$r" | grep -q "through the API"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:setup" | context)
expect "asked again, the current setting comes first" 'echo "$r" | grep -q "Options: \"No, leave them out\""'
r=$(answer "$T/proj" tool=claude-code reader=headless memory=on)
expect "and can be changed back" 'echo "$r" | grep -q "through your Claude subscription, with no API key" && [ "$(git -C "$T/proj" config wd.readerpath)" = headless ] && [ "$(git -C "$T/proj" config wd.capturememory)" = on ]'

echo "== A3. Recording, /warrant:attest, the bare /attest, /warrant:record"
n=$(events "$T/proj")
hook "$T/proj" UserPromptSubmit "Tighten the draft" > /dev/null
printf 'draft, tightened\n' > "$T/proj/paper.md"
hook "$T/proj" Stop > /dev/null
expect "a prompt and a reply are logged" '[ "$(events "$T/proj")" -eq $((n + 2)) ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:attest Read the draft twice." | reason)
expect "/warrant:attest commits" 'echo "$r" | grep -q "Attested in commit"'
expect "the commit is signed by the author" 'git -C "$T/proj" log -1 --format=%B | grep -q "Attested-by: Test Author"'
expect "the sentence is in the commit" 'git -C "$T/proj" log -1 --format=%B | grep -q "Verified: Read the draft twice."'
expect "replies name the plugin's commands" '! echo "$r" | grep -Eq "(^|[^:])/attest"'
r=$(hook "$T/proj" UserPromptSubmit "/attest" | reason)
expect "the hook still accepts the bare /attest" 'echo "$r" | grep -q "Attested in commit" && [ "$(git -C "$T/proj" rev-list --count HEAD)" -eq 2 ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:record" | reason)
expect "/warrant:record answers" 'echo "$r" | grep -q "Last save"'
expect "the record verifies" '(cd "$T/proj" && python3 provenance/verify_log.py > /dev/null)'

echo "== A3b. /warrant:brainstorm: labeled turns, kept in the record"
r=$(hook "$T/plain" UserPromptSubmit "/warrant:brainstorm" | reason)
expect "outside a set-up project, it says to run setup first" 'echo "$r" | grep -q "Type /warrant:setup first"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:brainstorm" | reason)
expect "a bare /warrant:brainstorm turns the label on" 'echo "$r" | grep -q "Brainstorm label on" && echo "$r" | grep -q "Claude did not see this"'
expect "its line marks the switch" '[ "$(field "$T/proj" brainstorm_switch)" = on ]'
hook "$T/proj" UserPromptSubmit "What if we framed it as a puzzle?" > /dev/null
expect "a prompt while it's on is recorded, labeled" '[ "$(field "$T/proj" brainstorm)" = true ] && [ "$(field "$T/proj" prompt_sha256)" != - ]'
hook "$T/proj" Stop > /dev/null
expect "and so is its reply" '[ "$(field "$T/proj" brainstorm)" = true ] && [ "$(field "$T/proj" response_sha256)" != - ]'
(WD_TEST_SESSION=other hook "$T/proj" UserPromptSubmit "Meanwhile, in another window" > /dev/null)
expect "another session isn't labeled" '[ "$(field "$T/proj" brainstorm)" = - ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:record" | reason)
expect "/warrant:record says it's on, with the turns so far" 'echo "$r" | grep -q "Brainstorm label: on in this conversation since .*1 turn so far"'
expect "the plugin's commands aren't labeled" '[ "$(field "$T/proj" brainstorm)" = - ]'
send "$T/proj" '{"session_id": "test", "prompt_id": "cmd1", "hook_event_name": "UserPromptSubmit", "prompt": "/warrant:setup"}' > /dev/null
send "$T/proj" '{"session_id": "test", "prompt_id": "cmd1", "hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion", "tool_input": {}, "tool_response": "Claude Code"}' > /dev/null
expect "nor are Claude's steps in a command's turn, such as setup's questions" '[ "$(field "$T/proj" tool)" = askuserquestion ] && [ "$(field "$T/proj" brainstorm)" = - ]'
r=$(WD_TEST_SESSION=other hook "$T/proj" UserPromptSubmit "/warrant:record" | reason)
expect "and another session's /warrant:record doesn't mention it" '! echo "$r" | grep -q "Brainstorm"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:brainstorm about the intro" | reason)
expect "anything typed after it gets a usage line, and changes nothing" 'echo "$r" | grep -q "by itself" && [ "$(field "$T/proj" brainstorm_switch)" = - ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:brainstorm on" | reason)
expect "\"on\" when it's on says so" 'echo "$r" | grep -q "already on"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:brainstorm" | reason)
expect "a second /warrant:brainstorm turns it off, counting the turns" 'echo "$r" | grep -q "Brainstorm label off, after 1 turn" && [ "$(field "$T/proj" brainstorm_switch)" = off ]'
hook "$T/proj" UserPromptSubmit "Back to the draft" > /dev/null
expect "after that, prompts aren't labeled" '[ "$(field "$T/proj" brainstorm)" = - ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:brainstorm off" | reason)
expect "\"off\" when it's off says so" 'echo "$r" | grep -q "already off"'
hook "$T/proj" UserPromptSubmit "/warrant:brainstorm on" > /dev/null
hook "$T/proj" SessionEnd > /dev/null
expect "quitting Claude Code turns the label off, and the session's last line says so" '[ "$(field "$T/proj" brainstorm_switch)" = off ]'
hook "$T/proj" UserPromptSubmit "Picking it back up" > /dev/null
expect "so a resumed conversation isn't labeled" '[ "$(field "$T/proj" brainstorm)" = - ]'
printf '{not json' > "$(git -C "$T/proj" rev-parse --absolute-git-dir)/wd-brainstorm.json"
n=$(events "$T/proj")
hook "$T/proj" UserPromptSubmit "With a damaged label file" > /dev/null
expect "a damaged label file never stops recording" '[ "$(events "$T/proj")" -eq $((n + 1)) ] && [ "$(field "$T/proj" brainstorm)" = - ]'
expect "the record verifies" '(cd "$T/proj" && python3 provenance/verify_log.py > /dev/null)'
expect "nothing about the label is saved in the project" '[ -z "$(git -C "$T/proj" status --porcelain -- . ":(exclude)provenance/log" | grep -i brainstorm)" ]'

echo "== A3b2. /warrant:withhold: text left out of the review copy, chosen by the person"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:withhold puzzle" | reason); search=$r
expect "a search shows the person the numbered matches, with the text around each, and Claude never sees them" 'echo "$r" | grep -q "entr.* containing \"puzzle\"" && echo "$r" | grep -q "1\. T[0-9]*, your prompt: .*framed it as a puzzle" && echo "$r" | grep -q "Claude did not see this"'
expect "and nothing is withheld until the person says which" '[ ! -e "$T/proj/provenance/withheld.json" ]'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:withhold 9" | reason)
expect "a number that wasn't shown is refused" 'echo "$r" | grep -q "no match numbered 9"'
pt=$(echo "$search" | sed -n 's/^  1\. T\([0-9]*\), your prompt.*/\1/p')
mkdir -p "$T/proj/disclosure/2026-01-01-000000" && printf 'T%s · AUTHOR%sS PROMPT:\nWhat if we framed it as a puzzle?\n\nT%s · CLAUDE%sS REPLY:\nok\n' "$pt" "'" "$pt" "'" > "$T/proj/disclosure/2026-01-01-000000/transcript.txt"
printf '{"U1": {"turns": "T%s", "basis": "the author asked to frame it as a puzzle"}, "U2": {"turns": "T1", "basis": "first save"}}' "$pt" > "$T/proj/disclosure/2026-01-01-000000/codes.json"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:withhold 1" | reason)
expect "withholding also takes the text out of disclosure runs already made: the transcript, and the basis of a code that cites the turn" 'echo "$r" | grep -q "from the files of 1 disclosure run already made" && ! grep -q puzzle "$T/proj/disclosure/2026-01-01-000000/transcript.txt" && grep -q "\[withheld\]" "$T/proj/disclosure/2026-01-01-000000/transcript.txt" && python3 -c "import json,sys; c=json.load(open(sys.argv[1])); sys.exit(not (c[\"U1\"][\"basis\"] == \"[rests partly on withheld text]\" and c[\"U2\"][\"basis\"] == \"first save\"))" "$T/proj/disclosure/2026-01-01-000000/codes.json"'
rm -rf "$T/proj/disclosure"
expect "choosing one withholds it and the search's own prompt, and the list is a file the next save keeps" 'echo "$r" | grep -q "Withheld 2 entries .*including the search.s own prompt" && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(len(d[\"entries\"]) != 2)" "$T/proj/provenance/withheld.json"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:withhold" | reason)
expect "/warrant:withhold alone lists what's withheld, by turn" 'echo "$r" | grep -q "Withheld from the review copy: 2 entries, in turns T"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:withhold 1" | reason)
expect "confirming again without a new search is refused" 'echo "$r" | grep -q "Search first"'
expect "a copy without the withheld texts still verifies, counting them as withheld" 'rm -rf "$T/withcopy" && cp -R "$T/proj" "$T/withcopy" && python3 -c "
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
for e in json.loads((p / \"provenance/withheld.json\").read_text())[\"entries\"]:
    (p / \"provenance/log/text\" / (e[\"sha256\"] + \".txt\")).unlink()
" "$T/withcopy" && (cd "$T/withcopy" && python3 provenance/verify_log.py | grep -q "[1-9][0-9]* withheld")'

echo "== A3c. Capture: the instructions Claude works under"
# A stand-in home folder, so the test never reads yours.
H="$T/home"; MEM="$H/.claude/projects/proj/memory"; SK="$H/.claude/plugins/cache/mk/demo/1.0/skills/tidy"
mkdir -p "$MEM" "$SK"
printf 'Always cite the DOI.\nHouse style: @rules.md\nWrite to me@example.edu\n' > "$H/.claude/CLAUDE.md"
printf 'Use APA style.\n' > "$H/.claude/rules.md"
printf -- '- [Style](style.md)\n' > "$MEM/MEMORY.md"
printf 'The author prefers short sentences.\n' > "$MEM/style.md"
printf -- '---\nname: tidy\n---\nTidy every table.\n' > "$SK/SKILL.md"
printf '{"plugins": {"demo@mk": [{"installPath": "%s", "version": "1.0"}]}}' "$H/.claude/plugins/cache/mk/demo/1.0" > "$H/.claude/plugins/installed_plugins.json"
printf '{"enabledPlugins": {"demo@mk": true}}' > "$H/.claude/settings.json"
printf '{"mcpServers": {"mail": {"command": "x", "env": {"KEY": "sk-not-a-real-key"}}}}' > "$H/.claude.json"
printf 'TRANSCRIPT-TEXT\n' > "$H/.claude/projects/proj/s1.jsonl"
pl() { python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d.update(session_id="test", cwd=sys.argv[2], transcript_path=sys.argv[3], permission_mode="default"); print(json.dumps(d))' "$1" "$T/proj" "$H/.claude/projects/proj/s1.jsonl"; }
at() { (export HOME="$H"; send "$T/proj" "$(pl "$1")"); }
at '{"hook_event_name": "SessionStart"}' > /dev/null
c='{e["kind"] for e in l["instructions"]} >= {"user", "import", "memory"} and sum(e["kind"] == "memory" for e in l["instructions"]) == 2'
expect "at session start, the record keeps the CLAUDE.md, a file it imports, and both memory files" 'last "$T/proj" "$c"'
c='"Always cite the DOI." in side([e for e in l["instructions"] if e["kind"] == "user"][0]["sha256"])'
expect "the text itself is kept, as a sidecar" 'last "$T/proj" "$c"'
c='"demo@mk 1.0" in l["plugins"] and l["agent"]["name"] == "claude-code"'
expect "and the plugins turned on, and the agent" 'last "$T/proj" "$c"'
expect "but no MCP servers: neither their names nor their settings" 'last "$T/proj" "\"mcp_servers\" not in l" && ! grep -rq "sk-not-a-real-key" "$T/proj/provenance/log"'
expect "and never the transcript beside the memory notes" '! grep -rq "TRANSCRIPT-TEXT" "$T/proj/provenance/log"'
at '{"hook_event_name": "UserPromptSubmit", "prompt": "Draft the abstract"}' > /dev/null
expect "a prompt with nothing changed adds nothing" 'last "$T/proj" "\"instructions\" not in l"'
printf 'The author prefers short sentences and no semicolons.\n' > "$MEM/style.md"
at '{"hook_event_name": "UserPromptSubmit", "prompt": "And the introduction"}' > /dev/null
c='"no semicolons" in side([e for e in l["instructions"] if e["path"].endswith("style.md")][0]["sha256"])'
expect "a memory note that changed is kept again at the next prompt" 'last "$T/proj" "$c"'
at '{"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "demo:tidy"}, "tool_response": {"commandName": "demo:tidy", "success": true}}' > /dev/null
c='l["skill"]["name"] == "demo:tidy" and "Tidy every table." in side(l["skill"]["sha256"])'
expect "a skill Claude invokes is kept with its text" 'last "$T/proj" "$c"'
at '{"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "artifact-design"}}' > /dev/null
expect "a skill that isn't on disk is kept by name" 'last "$T/proj" "l[\"skill\"] == {\"name\": \"artifact-design\", \"path\": None}"'
at '{"hook_event_name": "UserPromptSubmit", "prompt": "/demo:tidy the regression tables"}' > /dev/null
expect "a slash command the author types is kept with its text" 'last "$T/proj" "\"Tidy every table.\" in side(l[\"command_file\"][\"sha256\"])"'
r=$(at '{"hook_event_name": "UserPromptSubmit", "prompt": "/warrant:setup memory off"}' | reason)
expect "/warrant:setup memory off turns memory capture off" 'echo "$r" | grep -q "Memory capture off for this copy"'
c='l.get("memory_capture") == "off" and not any(e["kind"] == "memory" for e in l["instructions"])'
expect "and the record says so, without the memory notes" 'last "$T/proj" "$c"'
r=$(at '{"hook_event_name": "UserPromptSubmit", "prompt": "/warrant:record"}' | reason)
expect "/warrant:record says memory capture is off" 'echo "$r" | grep -q "Memory capture: off"'
r=$(at '{"hook_event_name": "UserPromptSubmit", "prompt": "/warrant:setup memory"}' | reason)
expect "/warrant:setup memory alone says how to use it" 'echo "$r" | grep -q "memory off or /warrant:setup memory on"'
at '{"hook_event_name": "UserPromptSubmit", "prompt": "/warrant:setup memory on"}' > /dev/null
expect "/warrant:setup memory on brings the memory notes back" 'last "$T/proj" "sum(e[\"kind\"] == \"memory\" for e in l[\"instructions\"]) == 2"'
expect "the record verifies" '(cd "$T/proj" && python3 provenance/verify_log.py > /dev/null)'

echo "== A3d. Codex CLI: the same logger, through the adapter"
mkdir "$T/codex" && git -C "$T/codex" init -q -b main && printf 'draft\n' > "$T/codex/paper.md"
printf 'Write in plain language.\n' > "$T/codex/AGENTS.md"
hook "$T/codex" UserPromptSubmit "/warrant:setup" > /dev/null
# cx JSON: a Codex hook event, as Codex runs a plugin hook: PLUGIN_ROOT set,
# no CLAUDE_PROJECT_DIR, the session's folder as the working directory.
mkdir -p "$T/nohome"  # a stand-in home folder, so the test never reads the user's own files
cx() { (cd "$T/codex" && printf '%s' "$1" | env -u CLAUDE_PROJECT_DIR HOME="$T/nohome" PLUGIN_ROOT="$PLUGIN" CLAUDE_PLUGIN_ROOT="$PLUGIN" python3 "$PLUGIN/scripts/log_event.py"); }
cpl() { python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d.update(session_id="cx1", cwd=sys.argv[2], transcript_path="/tmp/.codex/sessions/cx1.jsonl", model="gpt-x"); print(json.dumps(d))' "$1" "$T/codex"; }
cx "$(cpl '{"hook_event_name": "SessionStart", "source": "startup"}')" > /dev/null
c='l["agent"]["name"] == "codex-cli" and [e["kind"] for e in l["instructions"]] == ["project"] and l["instructions"][0]["path"] == "AGENTS.md" and "plugins" not in l'
expect "a Codex session start names the agent and captures AGENTS.md, not CLAUDE.md files" 'last "$T/codex" "$c"'
cx "$(cpl '{"hook_event_name": "UserPromptSubmit", "turn_id": "t1", "prompt": "Tighten the draft", "permission_mode": "default"}')" > /dev/null
expect "a prompt is logged with the turn id as its prompt id" 'last "$T/codex" "l[\"event\"] == \"UserPromptSubmit\" and l[\"prompt_id\"] == \"t1\""'
cx "$(cpl '{"hook_event_name": "PostToolUse", "turn_id": "t1", "tool_name": "Bash", "tool_use_id": "u1", "tool_input": {"command": "wc -w paper.md"}, "tool_response": "1 paper.md"}')" > /dev/null
expect "a shell command is logged, with its plain-text output" 'last "$T/codex" "l[\"command\"] == \"wc -w paper.md\" and side(l[\"output_sha256\"]) == \"1 paper.md\""'
printf 'draft, tightened\n' > "$T/codex/paper.md"
cx "$(cpl '{"hook_event_name": "PostToolUse", "turn_id": "t1", "tool_name": "apply_patch", "tool_use_id": "u2", "tool_input": {"command": "*** Begin Patch\n*** Update File: paper.md\n@@\n-draft\n+draft, tightened\n*** Add File: notes/new.md\n+hi\n*** End Patch"}, "tool_response": "Success"}')" > /dev/null
expect "a patch is logged as an edit of the files it names" 'last "$T/codex" "l[\"tool\"] == \"Edit\" and l[\"paths\"] == [\"paper.md\", \"notes/new.md\"] and l[\"prompt_id\"] == \"t1\""'
cx "$(cpl '{"hook_event_name": "Stop", "turn_id": "t1", "last_assistant_message": "Tightened it.", "stop_hook_active": false}')" > /dev/null
expect "the turn's final message is logged, closing the turn" 'last "$T/codex" "side(l[\"response_sha256\"]) == \"Tightened it.\" and l[\"prompt_id\"] == \"t1\""'
r=$(cx "$(cpl '{"hook_event_name": "UserPromptSubmit", "turn_id": "t2", "prompt": "warrant:attest Read the draft twice."}')" | reason)
expect "warrant:attest, with no slash, commits, and the reply names commands as Codex users type them" 'echo "$r" | grep -q "Attested in commit" && git -C "$T/codex" log -1 --format=%B | grep -q "Verified: Read the draft twice." && ! echo "$r" | grep -q "/warrant:"'
expect "a blocked command tells a Codex user that Codex, not Claude, didn't see it" 'echo "$r" | grep -q "Codex did not see this" && ! echo "$r" | grep -q "Claude did not see"'
r=$(cx "$(cpl '{"hook_event_name": "UserPromptSubmit", "turn_id": "t3", "prompt": "warrant:record"}')" | reason)
expect "warrant:record answers, blocked before the model" 'echo "$r" | grep -q "Last save"'
expect "the record verifies" '(cd "$T/codex" && python3 provenance/verify_log.py > /dev/null)'

echo "== A3e. Gemini CLI: the extension, through the adapter"
GEM="$PLUGIN"  # the Gemini CLI extension moved to Stage 2; the adapter is the plugin's own
mkdir "$T/gemini" && git -C "$T/gemini" init -q -b main && printf 'draft\n' > "$T/gemini/paper.md"
printf 'Cite every source.\n' > "$T/gemini/GEMINI.md"
hook "$T/gemini" UserPromptSubmit "/warrant:setup" > /dev/null
# gm JSON: a Gemini hook event, as Gemini runs an extension's hook.
gm() { (cd "$T/gemini" && printf '%s' "$1" | HOME="$T/nohome" GEMINI_SESSION_ID=g1 GEMINI_PROJECT_DIR="$T/gemini" CLAUDE_PROJECT_DIR="$T/gemini" python3 "$GEM/scripts/log_event.py"); }
gpl() { python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d.update(session_id="g1", cwd=sys.argv[2], transcript_path="/tmp/.gemini/tmp/g1.json", timestamp="2026-10-15T00:00:00Z"); print(json.dumps(d))' "$1" "$T/gemini"; }
o=$(gm "$(gpl '{"hook_event_name": "SessionStart", "source": "startup"}')")
c='l["agent"]["name"] == "gemini-cli" and [e["path"] for e in l["instructions"]] == ["GEMINI.md"]'
expect "a Gemini session start names the agent and captures GEMINI.md, and prints JSON" 'last "$T/gemini" "$c" && [ "$o" = "{}" ]'
o=$(gm "$(gpl '{"hook_event_name": "BeforeAgent", "prompt": "Tighten the draft"}')")
expect "a prompt (BeforeAgent) is logged with a prompt id the adapter makes, and passes" 'last "$T/gemini" "l[\"event\"] == \"UserPromptSubmit\" and l[\"prompt_id\"]" && [ "$o" = "{}" ]'
pid=$(tail -n 1 "$T"/gemini/provenance/log/*/events.jsonl | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["prompt_id"])')
gm "$(gpl '{"hook_event_name": "AfterTool", "tool_name": "run_shell_command", "tool_input": {"command": "wc -w paper.md", "description": "count"}, "tool_response": {"llmContent": "1 paper.md", "returnDisplay": "1 paper.md"}}')" > /dev/null
expect "a shell command (run_shell_command) is logged as Bash, with its output, in the same turn" 'last "$T/gemini" "l[\"tool\"] == \"Bash\" and l[\"command\"] == \"wc -w paper.md\" and side(l[\"output_sha256\"]) == \"1 paper.md\" and l[\"prompt_id\"] == \"'"$pid"'\""'
printf 'draft, tightened\n' > "$T/gemini/paper.md"
gm "$(gpl '{"hook_event_name": "AfterTool", "tool_name": "replace", "tool_input": {"file_path": "paper.md", "old_string": "draft", "new_string": "draft, tightened"}, "tool_response": {"llmContent": "ok"}}')" > /dev/null
expect "an edit (replace) is logged as Edit, with its file" 'last "$T/gemini" "l[\"tool\"] == \"Edit\" and l[\"paths\"] == [\"paper.md\"]"'
gm "$(gpl '{"hook_event_name": "AfterAgent", "prompt": "Tighten the draft", "prompt_response": "Tightened it."}')" > /dev/null
expect "the turn's final response (AfterAgent) closes the turn" 'last "$T/gemini" "l[\"event\"] == \"Stop\" and side(l[\"response_sha256\"]) == \"Tightened it.\" and l[\"prompt_id\"] == \"'"$pid"'\""'
o=$(gm "$(gpl '{"hook_event_name": "BeforeAgent", "prompt": "warrant:attest Read the draft twice."}')")
expect "/warrant:attest, as Gemini expands it, commits, and the prompt is denied before the model" 'echo "$o" | grep -q "\"decision\": \"deny\"" && echo "$o" | grep -q "Attested in commit" && git -C "$T/gemini" log -1 --format=%B | grep -q "Verified: Read the draft twice."'
expect "the record verifies" '(cd "$T/gemini" && python3 provenance/verify_log.py > /dev/null)'

if [ -f "$SRC/install.sh" ]; then
echo "== A4. Moving an older, copied-in install to the plugin"
mkdir "$T/old" && printf 'old work\n' > "$T/old/paper.md"
(cd "$T/old" && WD_INSTALL_SKIP_GITHUB=1 WD_INSTALL_SKIP_READER=1 WD_NAME="Old Author" WD_EMAIL=old@example.invalid \
	sh "$SRC/install.sh" > /dev/null)
expect "the older install has its own hooks" 'grep -q "log_event.py" "$T/old/.claude/settings.json"'
n=$(events "$T/old")
hook "$T/old" UserPromptSubmit "hello" > /dev/null
expect "before setup, the plugin stands aside, so nothing is logged twice" '[ "$(events "$T/old")" -eq "$n" ]'
r=$(hook "$T/old" UserPromptSubmit "/warrant:attest" | reason)
expect "and a plugin command says to switch over" 'echo "$r" | grep -q "Type /warrant:setup once to switch it over"'
n=$(events "$T/old")
r=$(hook "$T/old" UserPromptSubmit "/warrant:setup" | reason)
expect "the plugin leaves logging the switch-over prompt to the older hook, so it isn't logged twice" '[ "$(events "$T/old")" -eq "$n" ]'
expect "setup removes the older hooks, so nothing is logged twice" '! grep -q "log_event.py" "$T/old/.claude/settings.json" && echo "$r" | grep -q "the plugin records now"'
expect "and names the plugin instead" 'grep -q "warrant@warranted-delegation" "$T/old/.claude/settings.json"'
n=$(events "$T/old")
hook "$T/old" UserPromptSubmit "after the switch" > /dev/null
expect "after setup, the plugin records" '[ "$(events "$T/old")" -gt "$n" ]'
else
	echo "(skipped: install.sh, the older installer, isn't in this copy)"
fi

echo "== A5. /warrant:disclosure: the map first, then a run in the background that Claude narrates"
mkdir -p "$T/proj/analysis" "$T/proj/output" "$T/proj/notes"
printf 'print(1)\n' > "$T/proj/analysis/model.py"; printf 'a,b\n1,2\n' > "$T/proj/output/table1.csv"
printf 'my notes\n' > "$T/proj/notes/ideas.md"; mv "$T/proj/paper.md" "$T/proj/memo.md"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:disclosure" | context)
expect "the first time, it proposes the finished-work map, and Claude walks the author through it in the chat" '[ -f "$T/proj/provenance/finished-work.md" ] && echo "$r" | grep -q "^warrant:disclosure\. First, what the disclosure covers" && echo "$r" | grep -q "never have to edit the file" && echo "$r" | grep -q "manuscript: memo.md"'
expect "the walkthrough ends by starting the disclosure, whose reply Claude follows" 'echo "$r" | grep -q "scripts/disclose.py\" start \".*/proj\" claude-code" && echo "$r" | grep -q "saved with their next /warrant:attest"'
mkdir "$T/hl" && git -C "$T/hl" init -q -b main && printf 'draft\n' > "$T/hl/memo.md" && hook "$T/hl" UserPromptSubmit "/warrant:setup" > /dev/null
answer "$T/hl" tool=claude-code reader=headless > /dev/null
r2=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import disclose; print(disclose.start(sys.argv[2], sys.argv[3], "", narrate=False)[0])' "$PLUGIN/scripts" "$T/hl" "$PLUGIN" 2>&1)
expect "with no one there to answer (headless), it still hands over the map as a message" 'echo "$r2" | grep -q "I proposed this map" && [ -f "$T/hl/provenance/finished-work.md" ]'
expect "the map names the manuscript, the analysis, and the results" 'grep -q "^manuscript: memo.md" "$T/proj/provenance/finished-work.md" && grep -q "^analysis: analysis/" "$T/proj/provenance/finished-work.md" && grep -q "^results: output/" "$T/proj/provenance/finished-work.md"'
expect "a project with analysis code gets the quantitative pack" 'grep -q "^packs: quantitative$" "$T/proj/provenance/finished-work.md"'
expect "notes are left outside the map" '! grep -v "^#" "$T/proj/provenance/finished-work.md" | grep -q "notes" && echo "$r" | grep -q "outside it: notes/ideas.md"'
r=$(WD_DISCLOSURE_STUB=1 hook "$T/proj" UserPromptSubmit "/warrant:disclosure" | context)
expect "before anything is sent, it has Claude say what goes where and ask the author to agree; nothing runs yet" 'echo "$r" | grep -q "^warrant:disclosure\. Before anything is sent" && echo "$r" | grep -q "to Anthropic, through your Claude subscription" && echo "$r" | grep -q "consent=anthropic-subscription" && [ ! -d "$T/proj/disclosure" ]'
r=$(answer "$T/proj" consent=anthropic-subscription)
expect "the author's yes is remembered for this copy, with the date" 'echo "$r" | grep -q "you agreed" && git -C "$T/proj" config wd.consent | grep -q "^anthropic-subscription 20"'
r=$(WD_DISCLOSURE_STUB=1 hook "$T/proj" UserPromptSubmit "/warrant:disclosure" | context)
expect "each run then starts with a reminder of what the author agreed to" 'echo "$r" | grep -q "sends your finished work and record to Anthropic through your Claude subscription, with no API key, as you agreed on 20"'
expect "the second time, it starts a run and hands Claude the narration: the steps, and the command that follows the run" 'echo "$r" | grep -q "^warrant:disclosure\." && echo "$r" | grep -q "6. Draw the disclosure" && echo "$r" | grep -q "scripts/disclose.py\" follow" && echo "$r" | grep -q "your Claude subscription, with no API key"'
out=$(echo "$r" | sed -n 's/.*disclose.py" follow "\(.*\)"$/\1/p')
said=$(drain "$out")
expect "following it says each step in plain words, then where the disclosure is" 'echo "$said" | grep -q "^List the calls and claims in the finished work\.$" && echo "$said" | grep -q "^Draw the disclosure\.$" && echo "$said" | grep -q "^Done in about 1 minute, on your Claude subscription. The disclosure is in disclosure/"'
expect "each line is said once" '[ "$(echo "$said" | grep -c "^Draw the disclosure")" = 1 ]'
expect "the run writes a disclosure labeled as a draft" 'grep -q "Draft, not attested" "$T"/proj/disclosure/*/disclosure.md'
expect "the run keeps the manuscript as it was read, for the paper trail" '[ -f "$(ls -d "$T"/proj/disclosure/*/ | head -1)manuscript/memo.md" ]'
expect "the run is given the map's packs, and the disclosure names them" 'grep -q "plus packs: quantitative" "$T"/proj/disclosure/*/disclosure.md && grep -q "\"quantitative\"" "$T"/proj/disclosure/*/status.json'
mkdir "$T/snap" && git -C "$T/snap" init -q -b main && printf 'a\n' > "$T/snap/staged.md" && printf 'a\n' > "$T/snap/unstaged.md" && printf 'a\n' > "$T/snap/gone.md"
git -C "$T/snap" add -A && git -C "$T/snap" -c user.name=t -c user.email=t@t commit -q -m first
printf 'b\n' > "$T/snap/staged.md" && git -C "$T/snap" add staged.md && printf 'b\n' > "$T/snap/unstaged.md" && printf 'b\n' > "$T/snap/new.md" && rm "$T/snap/gone.md"
expect "a draft reads every change since the last save, staged or not, new files, and deletions" 'python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import disclose; from pathlib import Path; d = disclose.snapshot(Path(sys.argv[2]), Path(sys.argv[3]), None); sys.exit(not all((d / f).read_text() == \"b\n\" for f in (\"staged.md\", \"unstaged.md\", \"new.md\")) or (d / \"gone.md\").exists())" "$PLUGIN/scripts" "$T/snap" "$T/snapcopy"'
sleep 1
r=$(hook "$T/proj" UserPromptSubmit "/warrant:record" | reason)
expect "/warrant:record says where the latest disclosure is" 'echo "$r" | grep -q "Latest disclosure: disclosure/"'
r=$(hook "$T/proj" UserPromptSubmit "/warrant:disclosure final" | reason)
expect "a final disclosure needs a final version first" 'echo "$r" | grep -q "no final version yet"'
sed -i '' 's/^packs: quantitative$/packs: quantitative, network/' "$T/proj/provenance/finished-work.md"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:disclosure" | reason)
expect "a pack the tool doesn't have is refused, with the list of packs" 'echo "$r" | grep -q "packs the tool doesn.t have: network" && echo "$r" | grep -q "quantitative, experiments, qualitative, theory, tool"'

mkdir "$T/notool" && git -C "$T/notool" init -q -b main && printf 'draft\n' > "$T/notool/memo.md" && hook "$T/notool" UserPromptSubmit "/warrant:setup" > /dev/null
r=$(hook "$T/notool" UserPromptSubmit "/warrant:disclosure" | context)
expect "a project that hasn't named its tool is asked at disclosure time: the tool, then how it reaches Claude, then Claude starts the run" 'echo "$r" | grep -q "^warrant:disclosure\. Before the disclosure can run" && echo "$r" | grep -q "Which tool do you use for this project?" && echo "$r" | grep -q "How should the disclosure reach Claude?" && echo "$r" | grep -q "disclose.py\" start \".*notool\" claude-code$"'
answer "$T/notool" tool=codex-cli > /dev/null
r=$(WD_DISCLOSURE_STUB=1 hook "$T/notool" UserPromptSubmit "/warrant:disclosure" | context)
expect "a Codex project's disclosure goes ahead, reading through Codex (here, the map first)" 'echo "$r" | grep -q "First, what the disclosure covers"'
rm "$T/notool/provenance/finished-work.md"
answer "$T/notool" tool=claude-code > /dev/null
r=$(hook "$T/notool" UserPromptSubmit "/warrant:disclosure final" | context)
expect "a Claude Code copy that hasn't chosen is asked only how the disclosure reaches Claude, and the run keeps what was typed" 'echo "$r" | grep -q "How should the disclosure reach Claude?" && ! echo "$r" | grep -q "Which tool" && echo "$r" | grep -q "notool\" claude-code final$"'
answer "$T/notool" tool=claude-code reader=headless > /dev/null
r=$(python3 "$PLUGIN/scripts/disclose.py" start "$T/notool" claude-code)
expect "once the answers are saved, Claude starts it: here the map comes first, in the chat" 'echo "$r" | grep -q "^warrant:disclosure\. First, what the disclosure covers" && echo "$r" | grep -q "disclose.py\" start"'
answer "$T/notool" consent=anthropic-subscription > /dev/null
r=$(WD_DISCLOSURE_STUB=1 python3 "$PLUGIN/scripts/disclose.py" start "$T/notool" claude-code)
expect "then the run, with the narration, which says how to switch to the API" 'echo "$r" | grep -q "^warrant:disclosure\. The warrant plugin started the draft" && echo "$r" | grep -q "/warrant:disclosure api changes that"'
drain "$(echo "$r" | sed -n 's/.*disclose.py" follow "\(.*\)"$/\1/p')" > /dev/null
r=$(WD_DISCLOSURE_STUB=1 hook "$T/notool" UserPromptSubmit "/warrant:disclosure api" | context)
expect "/warrant:disclosure api switches this copy to the API, and since the path changed, asks for consent again" '[ "$(git -C "$T/notool" config wd.readerpath)" = api ] && echo "$r" | grep -q "to Anthropic, through the API, with your own key" && echo "$r" | grep -q "consent=anthropic-api"'
answer "$T/notool" consent=anthropic-api > /dev/null
r=$(WD_DISCLOSURE_STUB=1 hook "$T/notool" UserPromptSubmit "/warrant:disclosure" | context)
expect "once agreed, it runs through the API" 'echo "$r" | grep -q "through the API, billed to your own key"'
drain "$(echo "$r" | sed -n 's/.*disclose.py" follow "\(.*\)"$/\1/p')" > /dev/null
r=$(hook "$T/notool" UserPromptSubmit "/warrant:disclosure draft" | reason)
expect "anything else typed after it gets a usage line" 'echo "$r" | grep -q "Type /warrant:disclosure for a draft"'

if command -v pandoc > /dev/null; then
	mkdir "$T/word" && git -C "$T/word" init -q -b main && hook "$T/word" UserPromptSubmit "/warrant:setup" > /dev/null
	answer "$T/word" tool=claude-code reader=headless > /dev/null
	answer "$T/word" consent=anthropic-subscription > /dev/null
	printf '# A paper\n\nWritten in Word.\n' | pandoc -f markdown -o "$T/word/paper.docx"
	hook "$T/word" UserPromptSubmit "/warrant:disclosure" > /dev/null
	expect "a Word manuscript is proposed for the map" 'grep -q "^manuscript: paper.docx" "$T/word/provenance/finished-work.md"'
	WD_DISCLOSURE_STUB=1 hook "$T/word" UserPromptSubmit "/warrant:disclosure" > /dev/null
	for i in 1 2 3 4 5 6 7 8 9 10; do [ -n "$(ls "$T"/word/disclosure/*/disclosure.md 2> /dev/null)" ] && break; sleep 1; done
	expect "the disclosure converts it from Word in its copy, says so, and leaves the project alone" 'grep -q "Converted from Word for reading: paper.docx" "$T"/word/disclosure/*/disclosure.md && [ ! -e "$T/word/paper.docx.md" ]'
else
	fail "pandoc isn't installed; skipped the Word check"
fi

echo "== A5b. /warrant:trail: the paper trail for a disclosure"
r=$(hook "$T/proj" UserPromptSubmit "/warrant:trail" | reason)
expect "with no finished disclosure, it says to make one first" 'echo "$r" | grep -q "no finished disclosure yet"'
B=$(ls "$SRC"/tests/scripted2/runs/schools-low-low-*.bundle)
git clone -q "$B" "$T/trail" && git -C "$T/trail" fetch -q "$B" 'refs/provenance/*:refs/provenance/*'
mkdir -p "$T/trail/disclosure" && cp -R "$SRC/tests/scripted2/reader-runs/api/schools-low-low" "$T/trail/disclosure/2026-10-15-120000"
r=$(hook "$T/trail" UserPromptSubmit "/warrant:trail" | context)
expect "it picks the latest disclosure and hands Claude the command that draws it" 'echo "$r" | grep -q "^warrant:trail\." && echo "$r" | grep -q "scripts/trail.py\" \".*2026-10-15-120000\""'
cmd=$(echo "$r" | sed -n 's/^   \(python3 .*trail.py.*\)$/\1/p')
s=$(sh -c "$cmd")
expect "drawing it makes trail.html beside the disclosure, with every unit and the manuscript as read" 'echo "$s" | grep -q "Drew the paper trail for" && python3 - "$T/trail/disclosure/2026-10-15-120000" <<"PYCHECK"
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1]); page = (d / "trail.html").read_text()
data = json.loads(re.search(r"const DATA = (\{.*?\});\n", page, re.S).group(1))
units = json.loads((d / "units.json").read_text())["units"]
assert len(data["units"]) == len(units) and data["manuscript"] == ["memo.md"], (len(data["units"]), data["manuscript"])
assert any(a["restates"] for u in data["units"] for a in u["anchors"]), "no restatements marked"
steps = [t for u in data["units"] for t in u["trace"]]
assert steps and all(t["text"] and t["nq"] for t in steps), "a trace step without the words it names"
assert data["nturns"] >= 8 and "<!--PAPER-->" not in page and "/*DATA*/" not in page
assert "/Users/" not in page
assert not any("day" in t for t in data["turns"].values()), "a short record was given dates"
PYCHECK'
expect "a short record's timeline stays one column per turn; the page and trail.py agree on where grouping starts" 'grep -q "TURN_MAX = 100" "$PLUGIN/scripts/trail.html" && grep -q "^TIMELINE_TURNS = 100" "$PLUGIN/scripts/trail.py"'
r=$(hook "$T/trail" UserPromptSubmit "/warrant:trail 2026-01-01-000000" | reason)
expect "a run that isn't there is named in the reply" 'echo "$r" | grep -q "no finished disclosure called 2026-01-01-000000"'
expect "the markdown drawing handles headings, tables, lists, and emphasis without pandoc" '(cd "$PLUGIN/scripts" && python3 -c "
import trail
h = trail.markdown(\"# Title\\n\\nA *b* and **c**.\\n\\n| x | y |\\n|:-|-:|\\n| 1 | 2 |\\n\\n- one\\n- two\\n\")
assert h.startswith(\"<h1>Title</h1>\") and \"<em>b</em>\" in h and \"<strong>c</strong>\" in h, h
assert \"<td>1</td><td>2</td>\" in h and \"<ul><li>one</li><li>two</li></ul>\" in h, h
")'
cp -R "$SRC/tests/scripted2/reader-runs/api/schools-low-low" "$T/trail/disclosure/2026-10-15-130000"
python3 - "$T/trail/disclosure/2026-10-15-130000/units.json" <<'PYEDIT'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); u = json.loads(p.read_text())
u["units"][0]["label"] += ' (grep -n "<!--PAPER-->" and /*DATA*/null)'
p.write_text(json.dumps(u))
PYEDIT
python3 "$PLUGIN/scripts/trail.py" "$T/trail/disclosure/2026-10-15-130000" "$T/trail" >/dev/null
expect "a record or reading that quotes one of the page's blanks keeps it as text, and the page's data still reads" 'python3 - "$T/trail/disclosure/2026-10-15-130000" <<"PYCHECK"
import json, re, sys
from pathlib import Path
page = (Path(sys.argv[1]) / "trail.html").read_text()
data = json.loads(re.search(r"const DATA = (\{.*?\});\n", page, re.S).group(1))
assert data["units"][0]["label"].endswith("(grep -n \"<!--PAPER-->\" and /*DATA*/null)"), data["units"][0]["label"]
assert page.count("<!--PAPER-->") == 1 and page.count("id=\"paper\"><!--PAPER-->") == 0
PYCHECK'

echo "== A5c. The Codex and Gemini readers: the same calls, through stand-in commands"
mkdir -p "$T/fakebin"
cat > "$T/fakebin/codex" <<'FAKE'
#!/usr/bin/env python3
import json, sys
a = sys.argv[1:]
assert a[0] == "exec" and "--output-schema" in a and "--sandbox" in a and a[a.index("--sandbox") + 1] == "read-only", a
prompt = sys.stdin.read()
assert "Don't run any commands" in prompt and "CONTENT-MARK" in prompt, prompt[:200]
open(a[a.index("--output-last-message") + 1], "w").write(json.dumps({"units": [{"id": "U1"}]}))
print(json.dumps({"type": "thread.started"}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 7}}))
FAKE
cat > "$T/fakebin/gemini" <<'FAKE'
#!/usr/bin/env python3
import json, sys
prompt = sys.stdin.read()
assert "CONTENT-MARK" in prompt and "The JSON schema your reply must follow" in prompt, prompt[:200]
print(json.dumps({"response": "Here it is:\n```json\n{\"units\": [{\"id\": \"U1\"}]}\n```",
                  "stats": {"models": {"gemini-test": {"tokens": {"prompt": 90, "cached": 30, "candidates": 6}}}}}))
FAKE
chmod +x "$T/fakebin/codex" "$T/fakebin/gemini"
expect "the Codex and Gemini backends send the same instructions and content, and read back the answer and the usage" '(cd "$PLUGIN/scripts" && PATH="$T/fakebin:$PATH" python3 -c "
import backends
schema = {\"type\": \"object\", \"properties\": {\"units\": {\"type\": \"array\"}}, \"required\": [\"units\"], \"additionalProperties\": False}
content = [{\"type\": \"text\", \"text\": \"CONTENT-MARK\"}]
u = {}
assert backends.call_codex(\"SYSTEM\", content, schema, 100, u) == {\"units\": [{\"id\": \"U1\"}]}
assert (u[\"input_tokens\"], u[\"cache_read_input_tokens\"], u[\"output_tokens\"], u[\"calls\"]) == (100, 40, 7, 1), u
g = {}
assert backends.call_gemini(\"SYSTEM\", content, schema, 100, g) == {\"units\": [{\"id\": \"U1\"}]}
assert (g[\"input_tokens\"], g[\"model\"]) == (90, \"gemini-test\"), g
")'

echo "== A6. Checklist packs: proposed from the files, and only those packs are read"
for kind in exp qual theory; do mkdir -p "$T/packs-$kind" && git -C "$T/packs-$kind" init -q; done
printf 'p\n' > "$T/packs-exp/paper.md"; mkdir -p "$T/packs-exp/analysis" "$T/packs-exp/materials"
printf 'print(1)\n' > "$T/packs-exp/analysis/model.py"; printf 'h1\n' > "$T/packs-exp/preregistration.md"; printf 's\n' > "$T/packs-exp/materials/survey.qsf"
printf 'p\n' > "$T/packs-qual/paper.md"; mkdir -p "$T/packs-qual/transcripts"
printf 't\n' > "$T/packs-qual/transcripts/i01.txt"; printf 'c\n' > "$T/packs-qual/codebook.md"; printf 'q\n' > "$T/packs-qual/interview-protocol.md"
printf 'p\n' > "$T/packs-theory/paper.md"
proposed() { python3 -c 'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); import disclose; print(disclose.propose_map(Path(sys.argv[2]))[0])' "$PLUGIN/scripts" "$1"; }
m=$(proposed "$T/packs-exp")
expect "an experiment gets the quantitative and experiments packs, with its preregistration and materials" 'echo "$m" | grep -q "^packs: quantitative, experiments$" && echo "$m" | grep -q "^preregistration: preregistration.md$" && echo "$m" | grep -q "^materials: materials/$"'
m=$(proposed "$T/packs-qual")
expect "an interview study gets the qualitative pack, with its protocol, codebook, and transcripts" 'echo "$m" | grep -q "^packs: qualitative$" && echo "$m" | grep -q "^protocol: interview-protocol.md$" && echo "$m" | grep -q "^codebook: codebook.md$" && echo "$m" | grep -q "^data: transcripts/"'
mkdir "$T/packs-memo" && git -C "$T/packs-memo" init -q -b main && printf 'A memo.\n' > "$T/packs-memo/memo.md" && printf 'Variables.\n' > "$T/packs-memo/codebook.md" && printf 'id,x\n1,2\n' > "$T/packs-memo/teams.csv"
m=$(proposed "$T/packs-memo")
expect "a memo with a data table and its codebook gets the quantitative pack, and the codebook isn't the manuscript" 'echo "$m" | grep -q "^packs: quantitative$" && echo "$m" | grep -q "^manuscript: memo.md$" && echo "$m" | grep -q "^data: teams.csv"'
m=$(proposed "$T/packs-theory")
expect "a paper with no code or data gets the theory pack" 'echo "$m" | grep -q "^packs: theory$" && ! echo "$m" | grep -q "^analysis:"'
expect "a map from before packs (type: archival) still reads as the quantitative pack" 'python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import disclose; assert disclose.packs_of({\"type\": \"archival\"}) == ([\"quantitative\"], [])" "$PLUGIN/scripts"'
expect "naming experiments alone also brings in the quantitative pack" 'python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import disclose; assert disclose.packs_of({\"packs\": \"experiments\"}) == ([\"quantitative\", \"experiments\"], [])" "$PLUGIN/scripts"'
expect "the reader sees the spine and only the chosen packs" '(cd "$PLUGIN/scripts" && python3 -c "
import re, reader
ids = lambda t: re.findall(r\"(?m)^\\| ([A-Z]+[0-9]+) \\|\", t)
q = ids(reader.checklist_text(\"checklists/judgment-decisions.md\", [\"qualitative\"]))
assert \"S1\" in q and \"QL1\" in q and not any(i.startswith((\"QA\", \"EX\", \"TH\")) for i in q), q
assert len(ids(reader.checklist_text(\"checklists/judgment-decisions.md\"))) > len(q)
")'

cp -R "$SRC/tests/scripted/reader-runs/careful" "$T/render" && (cd "$PLUGIN/scripts" && python3 render.py "$T/render")
expect "the tool pack can be chosen: a tool paper sees the spine and the tool rows only" '(cd "$PLUGIN/scripts" && python3 -c "
import reader
j, c = (reader.checklist_text(x, [\"tool\"]) for x in reader.CHECKLISTS)
assert \"| TL1 |\" in j and \"| TL15 |\" in j and \"| S1 |\" in j and \"| QC1 |\" not in j, j[:200]
assert \"| TLV5 |\" in c and \"| QV1 |\" not in c
")'
expect "the disclosure is drawn in two rows, with each way a handed-over call ended" 'grep -q "^## Judgment calls: 26" "$T/render/disclosure.md" && grep -q "You made the call:\*\* 17 (65%)" "$T/render/disclosure.md" && grep -q "you accepted it, with a reason: 1" "$T/render/disclosure.md" && grep -q "^## Verifiable claims: 30" "$T/render/disclosure.md"'
expect "and as a page that draws them" 'grep -q "Verifiable claims: 30" "$T/render/disclosure.html" && grep -q "you were never told" "$T/render/disclosure.html"'
expect "the Stage 1 disclosure leaves out additional information, while the list still says which calls the tool made beyond what was asked" '! grep -q "Additional information" "$T/render/disclosure.md" && ! grep -q "Additional information" "$T/render/disclosure.html" && ! grep -q "Text typed by the tool" "$T/render/disclosure.html" && grep -q "| the tool, beyond what you asked |" "$T/render/disclosure.md" && grep -q "| the tool, as you asked |" "$T/render/disclosure.md"'
expect "the line reads the same in every case: one, several, none" '(cd "$PLUGIN/scripts" && python3 -c "
import render
d = lambda *c: [{\"discretion\": x, \"certification\": y} for x, y in c]
assert render.unasked(d((\"kept\", None))) is None
assert render.unasked(d((\"taken\", \"ignored\"))) == \"1 of the 1 call handed over. You did not warrant it.\"
assert render.unasked(d((\"taken\", \"okayed\"), (\"taken\", \"ignored\"), (\"taken\", \"ignored\"), (\"taken\", \"wasn\x27t notified\"), (\"given\", \"okayed\"))) == \"4 of the 5 calls handed over. You warranted 1 of them.\"
assert render.unasked(d((\"taken\", \"okayed\"), (\"taken\", \"changed\"), (\"given\", \"okayed\"))) == \"2 of the 3 calls handed over. You warranted both.\"
assert render.unasked(d((\"given\", \"okayed\"))) == \"none of the 1 call handed over.\"
")'
expect "the header names a demonstration's condition, the paper's title, and the checklists in plain words, and an author's own work gets no condition" '(cd "$PLUGIN/scripts" && python3 -c "
import render, tempfile, pathlib
assert render.condition({\"label\": \"Demonstration run (high delegation, low warrant), last save abc\"}) == \"high delegation, low warrant\"
assert render.condition({\"label\": \"Final version, final-2026-10-28 (commit abc1234)\"}) is None
assert render.checklist_line([\"quantitative\", \"experiments\"]) == \"Read against the checklists for any paper, quantitative studies, and experiments.\"
d = pathlib.Path(tempfile.mkdtemp())
(d / \"a.md\").write_text(\"---\\ntitle: \\\"A *Study* of Things\\\"\\nauthor: X\\n---\\n# Introduction\\n\")
(d / \"b.md\").write_text(\"Some notes\\n\\n# The Title Here\\n\")
assert render.paper_title(d, {\"manuscript\": \"a.md\"}, []) == \"A Study of Things\", render.paper_title(d, {\"manuscript\": \"a.md\"}, [])
assert render.paper_title(d, None, [\"b.md\"]) == \"The Title Here\"
assert render.paper_title(d, {\"manuscript\": \"none\"}, []) is None
(d / \"data_structure.md\").write_text(\"# Data structure\\n\"); (d / \"paper.md\").write_text(\"# The Paper\\n\")
assert render.paper_title(d, {\"manuscript\": \"data_structure.md, paper.md\"}, []) == \"The Paper\"
h = render.header_html({\"label\": \"Demonstration run (high delegation, high warrant), last save abc\", \"title\": \"T\", \"reader\": \"0.13.5\", \"model\": \"m\", \"date\": \"d\"}, [\"tool\"], \"disclosure\")
assert \"Demonstration: high delegation, high warrant\" in h and \"<p class=\\\"ptitle\\\">T</p>\" in h and \"research tools\" in h and \"Demonstration run, last save abc\" in h, h
")'
expect "the page carries its own fonts and asks no outside server for anything" 'grep -q "font/woff2;base64" "$T/render/disclosure.html" && ! grep -q "googleapis" "$T/render/disclosure.html" && ! grep -q "googleapis" "$PLUGIN/scripts/trail.html"'
expect "the disclosure's progress lines wrap the reader's own steps, which keep the same signatures, without changing its file" 'python3 - "$PLUGIN/scripts" "$T/progress" <<"PYCHECK"
import hashlib, inspect, json, sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1]); out = Path(sys.argv[2]); out.mkdir()
import disclose, reader
before = hashlib.sha256(Path(reader.__file__).read_bytes()).hexdigest()
real = {k: inspect.signature(getattr(reader, k)) for k in ("locate", "places", "trace", "code", "call")}
disclose.instrument(reader, out)
assert {k: inspect.signature(getattr(reader, k)) for k in real} == real
assert hashlib.sha256(Path(reader.__file__).read_bytes()).hexdigest() == before
fake = types.SimpleNamespace(BATCH=2, render=types.SimpleNamespace(write=lambda *a: None),
                             trace_numbers=types.SimpleNamespace(summarize=lambda *a: None))
fake.call = lambda client, system, content, schema, max_tokens, usage: {}
fake.places = lambda client, project, parts, units, usage: None
fake.trace = lambda project, units, turns, first_seen: units
def locate(client, project, work, usage, packs=None):
    fake.call(None, "", [], {}, 0, usage)
    units = [{"kind": "decision"}] * 3 + [{"kind": "claim"}] * 2
    fake.places(None, project, ["<file>"], units, usage)
    return ["memo.md"], units
def code(client, project, files, units, turns, usage):
    for i in range(0, len(units) + fake.BATCH, fake.BATCH):  # one more call than the batches: a retry
        fake.call(None, "", [], {}, 0, usage)
    return {}
fake.locate, fake.code = locate, code
(out / "progress.jsonl").unlink(missing_ok=True)
disclose.instrument(fake, out)
files, units = fake.locate(None, "p", ["memo.md"], {})
fake.trace("p", units, [1, 2], {}); fake.code(None, "p", files, units, [], {})
fake.trace_numbers.summarize(); fake.render.write()
said = [json.loads(l)["line"] for l in (out / "progress.jsonl").read_text().splitlines()]
assert said == ["Listing the calls and claims in the finished work.",
                "Found 3 calls and 2 claims in 1 file. Finding every other place each one appears.",
                "Tracing each of the 5 through the record, 2 turns.",
                "Coding who made each call and how it was warranted, in 3 batches.",
                "Coding: batch 1 of 3.", "Coding: batch 2 of 3.", "Coding: batch 3 of 3.",
                "Asking again about the units the first pass left out.",
                "Checking where the numbers came from and who typed the text.", "Drawing the disclosure."], said
PYCHECK'
mkdir -p "$T/big/data" && python3 -c "import json; open('$T/big/data/works.jsonl','w').write(''.join(json.dumps({'id': i, 'title': 'x' * 200}) + chr(10) for i in range(20000)))" && printf '\211PNG\r\n\032\n\000\000\000' > "$T/big/fig.png" && printf 'A paper.\n' > "$T/big/paper.md"
expect "the reader shows data files by their first lines and binary files by name, and reads the paper in full" '(cd "$PLUGIN/scripts" && python3 -c "
import sys, reader
from pathlib import Path
p = Path(sys.argv[1])
d = reader.file_text(p, \"data/works.jsonl\")
assert len(d) < 5000 and \"only the first lines\" in d, len(d)
assert \"not text, not shown\" in reader.file_text(p, \"fig.png\")
assert reader.file_text(p, \"paper.md\") == \"A paper.\\n\"
" "$T/big")'
mkdir -p "$T/nums/output" && printf 'irr 0.35045698\nN 1,833\n' > "$T/nums/output/results.txt" && printf 'The IRR is 0.350 (N = 1,833), about 1.16 for wider teams, in 2017; see 10.1126/science.1136099 and arXiv:2205.01833.\n' > "$T/nums/paper.md"
expect "reported numbers trace to saved outputs, with rounding; years and identifiers don't count" '(cd "$PLUGIN/scripts" && python3 -c "
import sys, trace_numbers
n = trace_numbers.summarize(sys.argv[1], {\"manuscript\": \"paper.md\", \"results\": \"output/\"}, [\"paper.md\"], [])
assert (n[\"traced\"], n[\"total\"], n[\"untraced\"]) == (2, 3, [\"1.16\"]), n
" "$T/nums")'
printf '%%PDF-1.7\n<< /Length 162052 /Height 987 >>\nstream 4600 83561\n' > "$T/nums/paper.pdf"
expect "a PDF beside its source is binary: the reader shows it by name and its numbers aren't counted" '(cd "$PLUGIN/scripts" && python3 -c "
import sys, reader, trace_numbers
from pathlib import Path
assert \"not text, not shown\" in reader.file_text(Path(sys.argv[1]), \"paper.pdf\")
n = trace_numbers.summarize(sys.argv[1], {\"manuscript\": \"paper.md, paper.pdf\", \"results\": \"output/\"}, [\"paper.md\", \"paper.pdf\"], [])
assert (n[\"traced\"], n[\"total\"]) == (2, 3), n
" "$T/nums")'
expect "who typed it: the tool's words, a person's one-word fix, and a person's paragraph the tool copied in" 'python3 - "$T/typed" "$PLUGIN/scripts" <<"PYCHECK"
import subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); p.mkdir(); sys.path.insert(0, sys.argv[2]); import typed_by
g = lambda *a: subprocess.run(["git", "-C", str(p), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True).stdout.strip()
def save(files):
    for f, t in files.items(): (p / f).write_text(t)
    g("add", "-A"); g("commit", "-qm", "s"); return g("rev-parse", "HEAD")
g("init", "-q")
mine = "my own paragraph about why team size matters for citations in management research"
a = save({"paper.md": "Title\n", "notes.md": mine + "\n"})
b = save({"paper.md": "Title\nthe tool wrote these five words\n" + mine + "\n"})
c = save({"paper.md": "Title\nthe tool wrote these six words\n" + mine + "\n"})
turns = [{"ts": "1", "before": a, "after": b}, {"ts": "2", "before": c, "after": c}]
n = typed_by.summarize(p, turns, {"manuscript": "paper.md"}, ["paper.md", "notes.md"])
assert (n["tool_words"], n["words"]) == (5, 20), n
PYCHECK'
expect "who typed it: an earlier disclosure's copy of the manuscript doesn't make the tool's words a person's" 'python3 - "$T/typed3" "$PLUGIN/scripts" <<"PYCHECK"
import subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); p.mkdir(); sys.path.insert(0, sys.argv[2]); import typed_by
g = lambda *a: subprocess.run(["git", "-C", str(p), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True).stdout.strip()
def save(files):
    for f, t in files.items():
        (p / f).parent.mkdir(parents=True, exist_ok=True); (p / f).write_text(t)
    g("add", "-A"); g("commit", "-qm", "s"); return g("rev-parse", "HEAD")
g("init", "-q")
memo = "after excluding one team the remaining teams show essentially no linear association at all"
a = save({"memo.md": "Memo\n"})
b = save({"memo.md": "Memo\n" + memo + "\n"})
c = save({"disclosure/run1/manuscript/memo.md": "Memo\n" + memo + "\n"})
turns = [{"ts": "1", "before": a, "after": b}, {"ts": "2", "before": c, "after": c}]
n = typed_by.summarize(p, turns, {"manuscript": "memo.md"}, ["memo.md"])
assert (n["tool_words"], n["words"]) == (14, 15), n
PYCHECK'
expect "who typed it: a sentence the author wrote in a prompt is theirs; the tool's sentence quoted back in a prompt stays the tool's" 'python3 - "$T/typed2" "$PLUGIN/scripts" <<"PYCHECK"
import subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); p.mkdir(); sys.path.insert(0, sys.argv[2]); import typed_by
g = lambda *a: subprocess.run(["git", "-C", str(p), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True).stdout.strip()
def save(files):
    for f, t in files.items(): (p / f).write_text(t)
    g("add", "-A"); g("commit", "-qm", "s"); return g("rev-parse", "HEAD")
g("init", "-q")
tool = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
mine = "larger teams draw on more networks so their papers travel further"
a = save({"paper.md": "Title\n"})
b = save({"paper.md": "Title\n" + tool + "\n"})
c = save({"paper.md": "Title\n" + tool + "\n" + mine + "\n" + tool + "\n"})
turns = [{"ts": "1", "before": a, "after": b, "prompt": "write the first sentence"},
         {"ts": "2", "before": b, "after": c, "prompt": "Please add this sentence: " + mine + " and then repeat " + tool}]
n = typed_by.summarize(p, turns, {"manuscript": "paper.md"}, ["paper.md"])
assert (n["tool_words"], n["words"]) == (20, 32), n
PYCHECK'
mkdir -p "$T/early/provenance/log/a"
printf '%s\n' '{"event": "UserPromptSubmit", "ts": "t1"}' '{"event": "PostToolUse", "tool": "Bash", "command": "ls"}' '{"event": "Stop"}' '{"event": "UserPromptSubmit", "prompt_id": "p2"}' '{"event": "PostToolUse", "prompt_id": "p2", "tool": "Edit", "paths": ["a.md"]}' > "$T/early/provenance/log/a/events.jsonl"
expect "the reader reads the earliest events, from before prompt IDs, into their turns" '(cd "$PLUGIN/scripts" && python3 -c "
import sys, reader
from pathlib import Path
turns = reader.load_record(Path(sys.argv[1]))[1]
assert [len(t[\"tools\"]) for t in turns] == [1, 1], turns
" "$T/early")'
expect "the reader sets a brainstorm turn aside, naming the files Claude changed, and shows whose each instruction is" 'python3 - "$T/aside" "$PLUGIN/scripts" <<"PYCHECK"
import hashlib, json, subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); p.mkdir(); sys.path.insert(0, sys.argv[2]); import reader
g = lambda *a: subprocess.run(["git", "-C", str(p), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True).stdout.strip()
def save(files):
    for f, t in files.items(): (p / f).write_text(t)
    g("add", "-A"); g("commit", "-qm", "s"); return g("rev-parse", "HEAD")
g("init", "-q")
idea, mine = "A bold idea Claude wrote while brainstorming\n", "The author typed this line\n"
a = save({"paper.md": "Title\n"})
b = save({"paper.md": "Title\n" + idea})
c = save({"paper.md": "Title\n" + idea + mine})
d = save({"paper.md": "Title\n" + idea + mine + "Claude tidied the table\n"})
text = p / "provenance" / "log" / "text"; text.mkdir(parents=True)
def side(t):
    h = hashlib.sha256(t.encode()).hexdigest(); (text / f"{h}.txt").write_text(t); return h
events = [
    {"event": "SessionStart", "plugins": ["demo@mk 1.0"],
     "instructions": [{"kind": "user", "path": "~/.claude/CLAUDE.md", "sha256": side("Always cite the DOI.")}]},
    {"event": "UserPromptSubmit", "prompt_id": "p1", "prompt_sha256": side("SECRET brainstorm prompt"), "snapshot": a, "brainstorm": True},
    {"event": "Stop", "prompt_id": "p1", "response_sha256": side("SECRET brainstorm reply"), "snapshot": b, "brainstorm": True},
    {"event": "UserPromptSubmit", "prompt_id": "p2", "prompt_sha256": side("Tidy the tables"), "snapshot": c},
    {"event": "PostToolUse", "prompt_id": "p2", "tool": "Skill",
     "skill": {"name": "demo:tidy", "path": "~/.claude/plugins/cache/mk/demo/1.0/skills/tidy/SKILL.md", "sha256": side("Tidy every table.")}},
    {"event": "Stop", "prompt_id": "p2", "response_sha256": side("Done."), "snapshot": d},
]
(p / "provenance" / "log" / "a").mkdir()
(p / "provenance" / "log" / "a" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
t = reader.transcript(p, reader.load_record(p)[1], [])
assert "SECRET" not in t, t
assert "T1 · SET ASIDE" in t and "Files Claude changed in it: paper.md." in t, t
hand = t.split("the author changed files by hand:]")[1].split("T2 · ")[0]
assert "+The author typed this line" in hand and "+A bold idea" not in hand, hand
assert "Always cite the DOI." in hand and "own instructions (their user-level CLAUDE.md)" in hand, t
assert "from the plugin demo, written by that plugin" in t and "Tidy every table." in t, t
PYCHECK'
expect "a record too long to read at once is read in pieces, each with its units' turns in full and the author's side of the rest; one that fits is read whole" 'python3 - "$T/pieces" "$PLUGIN/scripts" <<"PYCHECK"
import hashlib, json, subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); sys.path.insert(0, sys.argv[2])
import reader, render
p.mkdir()
g = lambda *a: subprocess.run(["git", "-C", str(p), *a], check=True, capture_output=True, text=True).stdout.strip()
g("init", "-q"); g("config", "user.name", "T"); g("config", "user.email", "t@example.invalid")
def save(files):
    for k, v in files.items(): (p / k).write_text(v)
    g("add", "-A"); g("commit", "-q", "-m", "s", "--allow-empty"); return g("rev-parse", "HEAD")
text = p / "provenance" / "log" / "text"; text.mkdir(parents=True)
def side(t):
    h = hashlib.sha256(t.encode()).hexdigest(); (text / f"{h}.txt").write_text(t); return h
events, body = [{"event": "SessionStart"}], "Title\n"
for n in range(1, 41):  # forty turns, each with a long reply and a tool call
    before = save({"paper.md": body})
    body += f"Line {n}\n"
    after = save({"paper.md": body})
    events += [{"event": "UserPromptSubmit", "prompt_id": f"p{n}", "prompt_sha256": side(f"MINE {n}"), "snapshot": before},
               {"event": "PostToolUse", "prompt_id": f"p{n}", "tool": "Edit", "paths": ["paper.md"],
                "output_sha256": side(f"edited {n}")},
               {"event": "Stop", "prompt_id": f"p{n}", "response_sha256": side(f"CLAUDE {n} " + "x" * 3000), "snapshot": after}]
(p / "provenance" / "log" / "a").mkdir()
(p / "provenance" / "log" / "a" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
turns = reader.load_record(p)[1]
units = [{"id": f"U{n}", "kind": "decision", "row": "R1", "label": f"call {n}",
          "anchors": [{"file": "paper.md", "quote": f"Line {n}"}], "trace": [{"turn": n, "file": "paper.md"}]} for n in (5, 35)]
piece = reader.transcript(p, turns, units, full={5, 6})
assert "MINE 20" in piece and "CLAUDE 20" not in piece and "[Claude\x27s side of T20 is not shown in this piece" in piece, piece[:400]
assert "CLAUDE 5 " in piece and "CLAUDE 6 " in piece, "turns in full"
whole = reader.transcript(p, turns, units)
seen = []
def model(limit):
    def call(client, system, content, schema, max_tokens, usage):
        rec = content[0]["text"]
        if len(rec) > limit:
            raise RuntimeError("Error code: 400 - prompt is too long: 2000000 tokens > 1000000 maximum")
        seen.append(rec)
        return {"codes": [{"id": x["id"]} for x in json.loads(content[-1]["text"].split("\n", 1)[1])]}
    return call
reader.call = model(10 ** 9)
usage = {}
codes, saved = reader.code(None, p, ["paper.md"], units, turns, usage)
assert "read_in_pieces" not in usage and len(seen) == 1 and saved == whole, "a record that fits is read whole"
reader.WINDOW, seen[:] = (3, 1), []
reader.call = model(len(whole) // 2)
usage = {}
codes, saved = reader.code(None, p, ["paper.md"], units, turns, usage)
read = usage["read_in_pieces"]
assert set(codes) == {"U5", "U35"} and read["pieces"] == 1 and read["windows"] == [(3, 1)], usage
assert "[This record is shown in part" in seen[0] and "CLAUDE 5 " in seen[0] and "CLAUDE 35 " in seen[0], "one batch, one piece"
assert "CLAUDE 20 " not in seen[0], "turns far from both units show only the author\x27s side"
assert all(f"CLAUDE {n} " in saved for n in range(1, 41)), "the saved transcript is the whole record"
two = len(seen[0])
seen[:] = []
reader.code_in_pieces(None, p, "", units[:1], turns, {})
one = len(seen[0])
seen[:] = []
reader.call = model((one + two) // 2)
usage = {}
codes, _ = reader.code_in_pieces(None, p, "", units, turns, usage)
assert set(codes) == {"U5", "U35"} and usage["read_in_pieces"]["pieces"] == 2, usage
assert "CLAUDE 5 " in seen[0] and "CLAUDE 35 " not in seen[0] and "CLAUDE 35 " in seen[1], "a batch too long splits, each with its own turns"
assert "Read in pieces: the record (40 turns)" in render.pieces_line({**read, "windows": [[3, 1]]})
PYCHECK'
expect "in pieces, the latest turns that quote six words in a row of a unit's text are shown in full too, and a piece too long for one unit drops them before narrowing its window" 'python3 - "$T/quoting" "$PLUGIN/scripts" <<"PYCHECK"
import hashlib, json, subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]); sys.path.insert(0, sys.argv[2])
import reader, render
p.mkdir()
g = lambda *a: subprocess.run(["git", "-C", str(p), *a], check=True, capture_output=True, text=True).stdout.strip()
g("init", "-q"); g("config", "user.name", "T"); g("config", "user.email", "t@example.invalid")
def save(files):
    for k, v in files.items(): (p / k).write_text(v)
    g("add", "-A"); g("commit", "-q", "-m", "s", "--allow-empty"); return g("rev-parse", "HEAD")
text = p / "provenance" / "log" / "text"; text.mkdir(parents=True)
def side(t):
    h = hashlib.sha256(t.encode()).hexdigest(); (text / f"{h}.txt").write_text(t); return h
claim = "The disclosure took forty one minutes in all."
events, body = [{"event": "SessionStart"}], "Title\n"
for n in range(1, 41):  # the claim is written at T5; T25, T30, and T35 check it, far from there
    before = save({"paper.md": body})
    body += (claim if n == 5 else f"Line {n}") + "\n"
    after = save({"paper.md": body})
    check = "Checked: the disclosure took **forty-one** minutes in all. " if n in (25, 30, 35) else ""
    events += [{"event": "UserPromptSubmit", "prompt_id": f"p{n}", "prompt_sha256": side(f"MINE {n}"), "snapshot": before},
               {"event": "Stop", "prompt_id": f"p{n}", "response_sha256": side(f"CLAUDE {n} " + check + "x" * 3000), "snapshot": after}]
(p / "provenance" / "log" / "a").mkdir()
(p / "provenance" / "log" / "a" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
turns = reader.load_record(p)[1]
unit = {"id": "U5", "kind": "claim", "row": "V1", "label": "time",
        "anchors": [{"file": "paper.md", "quote": claim}], "trace": [{"turn": 5, "file": "paper.md"}]}
assert reader.quoting([unit], turns) == {"U5": {25, 30, 35}}, "six words in a row, whatever the case, punctuation, or markup"
seen = []
def model(limit):
    def call(client, system, content, schema, max_tokens, usage):
        rec = content[0]["text"]
        if len(rec) > limit:
            raise RuntimeError("Error code: 400 - prompt is too long: 2000000 tokens > 1000000 maximum")
        seen.append(rec)
        return {"codes": [{"id": x["id"]} for x in json.loads(content[-1]["text"].split("\n", 1)[1])]}
    return call
reader.WINDOW, reader.QUOTED_CAP, reader.call = (3, 1), 2, model(10 ** 9)
usage = {}
reader.code_in_pieces(None, p, "", [unit], turns, usage)
assert "CLAUDE 5 " in seen[0] and "CLAUDE 30 " in seen[0] and "CLAUDE 35 " in seen[0], "the latest quoting turns, in full"
assert "CLAUDE 25 " not in seen[0] and "CLAUDE 20 " not in seen[0], "no more than the cap, and nothing else"
assert "and the latest turns that quote it" in seen[0], seen[0][:400]
read = usage["read_in_pieces"]
assert read["quoting"] == [6, 2] and "quoting_dropped" not in read, read
line = render.pieces_line({**read, "windows": [[3, 1]]})
assert "and up to 2 more that quote it, in full" in line and "to fit" not in line, line
assert "quote" not in render.pieces_line({"turns": 40, "pieces": 1, "windows": [[20, 5]]}), "a 0.14 run reads as before"
quoted = len(seen[0])
reader.QUOTED_CAP, seen[:] = 0, []
reader.code_in_pieces(None, p, "", [unit], turns, {})
bare = len(seen[0])
assert "CLAUDE 30 " not in seen[0] and "that quote it" not in seen[0], "a cap of 0 shows none"
reader.QUOTED_CAP, seen[:] = 2, []
reader.call = model((bare + quoted) // 2)
usage = {}
codes, _ = reader.code_in_pieces(None, p, "", [unit], turns, usage)
read = usage["read_in_pieces"]
assert set(codes) == {"U5"} and "CLAUDE 5 " in seen[0] and "CLAUDE 30 " not in seen[0], "too long: the quoting turns go first"
assert read["windows"] == [(3, 1)] and read["quoting_dropped"] == 1, read
assert "(the turns that quote it left out for some, to fit)" in render.pieces_line({**read, "windows": [[3, 1]]})
PYCHECK'

echo "== B. Claude Code with the plugin loaded"
if ! command -v claude > /dev/null; then
	fail "Claude Code isn't installed; skipped part B"
else
	mkdir "$T/live" && git -C "$T/live" init -q -b main
	git -C "$T/live" config user.name "Live Author" && git -C "$T/live" config user.email live@example.invalid
	run_claude() {
		prompt=$1; shift
		(cd "$T/live" && env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_SESSION_ID -u CLAUDE_EFFORT -u ANTHROPIC_API_KEY \
			claude -p "$prompt" "$@" --plugin-dir "$PLUGIN" --setting-sources project,local --strict-mcp-config --output-format json < /dev/null)
	}
	turns() { python3 -c 'import json,sys; print(json.load(sys.stdin).get("num_turns"))'; }
	t=$(run_claude "/warrant:setup" | turns)
	expect "/warrant:setup runs in the hook, with no model call" '[ "$t" = "0" ] && [ -d "$T/live/provenance/log" ]'
	expect "headless, setup can't ask its questions, so it keeps the defaults: Claude Code" 'grep -q "\"tool\": \"claude-code\"" "$T/live/provenance/settings.json"'
	printf '# A memo\n\nOne line.\n' > "$T/live/memo.md"
	t=$(run_claude "/warrant:disclosure" | turns)
	expect "headless, the disclosure can't ask either: it goes on with the subscription, unsaved, so a person is still asked" '[ "$t" = "0" ] && [ -f "$T/live/provenance/finished-work.md" ] && [ -z "$(git -C "$T/live" config wd.readerpath)" ]'
	t=$(run_claude "/warrant:disclosure" | turns)
	expect "but it never sends anything without the author's consent, which only a person can give" '[ "$t" = "0" ] && [ ! -d "$T/live/disclosure" ]'
	t=$(run_claude "Reply with the single word ok." | turns)
	stops() { cat "$T/live"/provenance/log/*/events.jsonl | python3 -c 'import json,sys; print(sum(json.loads(l).get("event") == "Stop" for l in sys.stdin))'; }
	expect "an ordinary prompt reaches Claude and is recorded" '[ "$t" != "0" ] && [ "$(stops)" -ge 1 ]'
	sid=$(python3 -c 'import uuid; print(uuid.uuid4())')
	t=$(run_claude "/warrant:brainstorm" --session-id "$sid" | turns)
	expect "/warrant:brainstorm runs in the hook, with no model call" '[ "$t" = "0" ] && grep -q "\"brainstorm_switch\":\"on\"" "$T/live"/provenance/log/*/events.jsonl'
	run_claude "Reply with the single word ok." --resume "$sid" > /dev/null
	labeled() { grep '"event":"UserPromptSubmit"' "$T/live"/provenance/log/*/events.jsonl | tail -n 1 | grep -q '"brainstorm":true'; }
	expect "a headless step ending leaves the label on, so the script's next step is labeled" 'labeled'
	run_claude "/warrant:brainstorm" --resume "$sid" > /dev/null
	t=$(run_claude "/warrant:attest" | turns)
	expect "/warrant:attest commits, with no model call" '[ "$t" = "0" ] && git -C "$T/live" log -1 --format=%B | grep -q "Attested-by: Live Author"'
	expect "the live record verifies" '(cd "$T/live" && python3 provenance/verify_log.py > /dev/null)'
	start_line() { grep '"event":"SessionStart"' "$T/live"/provenance/log/*/events.jsonl | tail -n 1; }
	c='l["agent"].get("setting_sources") == ["local", "project"]'
	expect "capture reads how Claude Code was started: no user settings" 'start_line | python3 -c "import json,sys; l=json.loads(sys.stdin.read()); sys.exit(0 if $c else 1)"'
	c='not any(e["kind"] == "user" for e in l["instructions"]) and any(p.startswith("warrant (--plugin-dir)") for p in l["plugins"])'
	expect "so it leaves out your own CLAUDE.md, and names the plugin it was given" 'start_line | python3 -c "import json,sys; l=json.loads(sys.stdin.read()); sys.exit(0 if $c else 1)"'
fi

echo
if [ "${KEEP:-0}" = 1 ]; then echo "Kept $T"; else rm -rf "$T"; fi
if [ "$failures" -eq 0 ]; then echo "All checks passed."; else echo "$failures check(s) failed."; exit 1; fi
