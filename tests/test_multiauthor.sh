#!/bin/sh
# Test /attest with two coauthors sharing one repository.
#
# Builds everything in a throwaway folder: a pretend shared repository (a
# bare git repository standing in for GitHub) and two copies of a project,
# one for "Ada Test" and one for "Ben Test", each set up with the
# warrant plugin's /warrant:setup (GitHub skipped), as people install it.
# It feeds the plugin's hook made-up events, including real
# /attest prompts, so the hook makes real commits, merges, and pushes, but
# only inside the throwaway folder, which is deleted at the end (KEEP=1
# keeps it). Nothing goes online, and this repository is never touched.
#
# Usage: sh tests/test_multiauthor.sh
set -u

SRC=$(cd "$(dirname "$0")/.." && pwd -P)
PLUGIN="$SRC/plugin/warrant"
T=$(mktemp -d "${TMPDIR:-/tmp}/wd-test.XXXXXX")
export GIT_CONFIG_NOSYSTEM=1 WD_SETUP_SKIP_GITHUB=1
failures=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
expect() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

# hook DIR PROMPT_ID EVENT [PROMPT]: send one made-up event to DIR's hook.
# Prints the hook's reply (only /attest prompts reply).
hook() {
	dir=$1 id=$2 event=$3 prompt=${4:-}
	payload=$(python3 -c 'import json,sys; print(json.dumps({"session_id": "test-" + sys.argv[1].rsplit("/", 1)[-1], "prompt_id": sys.argv[2], "hook_event_name": sys.argv[3], "permission_mode": "default", "prompt": sys.argv[4], "cwd": sys.argv[1], "last_assistant_message": "ok"}))' "$dir" "$id" "$event" "$prompt")
	(cd "$dir" && printf '%s' "$payload" | GIT_CONFIG_GLOBAL="$dir.gitconfig" CLAUDE_PROJECT_DIR="$dir" \
		CLAUDE_PLUGIN_ROOT="$PLUGIN" python3 "$PLUGIN/scripts/log_event.py")
}
# setup DIR "Name <email>": /warrant:setup in DIR, as that coauthor.
setup() {
	hook "$1" "setup-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')" UserPromptSubmit "/warrant:setup $2" > /dev/null
}
# attest DIR TEXT: type an /attest prompt in DIR; print the reason shown.
attest() {
	hook "$1" "attest-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')" UserPromptSubmit "$2" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])'
}
in_git() { dir=$1; shift; GIT_CONFIG_GLOBAL="$dir.gitconfig" git -C "$dir" "$@"; }

echo "Working in $T"
git init -q --bare -b main "$T/origin.git"

echo "== 1. Ada starts the project and makes the first save"
mkdir "$T/ada" && printf 'line one\n' > "$T/ada/paper.md"
setup "$T/ada" "Ada Test <ada@test>"
in_git "$T/ada" remote add origin "$T/origin.git"
hook "$T/ada" p1 UserPromptSubmit "hello"
hook "$T/ada" p1 Stop
reply=$(attest "$T/ada" "/attest First save")
echo "      reply: $reply"
expect "first save reaches the shared repository" '[ -n "$(git -C "$T/origin.git" rev-parse -q --verify main)" ]'
dlog=$(ls "$T"/ada/provenance/log/*/events.jsonl)
expect "Ada's log is in his own folder" 'case "$dlog" in */ada-test-*/events.jsonl) true;; *) false;; esac'
expect "his log starts with a LogStart line naming him" 'head -1 "$dlog" | grep -q "\"event\":\"LogStart\".*\"author\":\"Ada Test\""'
expect "his snapshots reach the shared repository" '[ -n "$(git -C "$T/origin.git" for-each-ref "refs/provenance/ada-test-*/snapshots")" ]'

echo "== 2. Ben joins with his own copy and saves"
git clone -q "$T/origin.git" "$T/ben"
setup "$T/ben" "Ben Test <ben@test>"
hook "$T/ben" v1 UserPromptSubmit "hello"
hook "$T/ben" v1 Stop
reply=$(attest "$T/ben" "/attest Ben's first save")
echo "      reply: $reply"
vlog=$(ls "$T"/ben/provenance/log/ben-test-*/events.jsonl 2>/dev/null)
expect "Ben's log is in his own folder" '[ -n "$vlog" ]'
expect "Ben's save reaches the shared repository" '[ "$(git -C "$T/origin.git" rev-parse main)" = "$(in_git "$T/ben" rev-parse HEAD)" ]'

echo "== 3. Ada saves again and brings in Ben's work"
hook "$T/ada" p2 UserPromptSubmit "hello"
reply=$(attest "$T/ada" "/attest Second save")
echo "      reply: $reply"
expect "Ada's /attest reports bringing in Ben's commit" 'echo "$reply" | grep -q "Brought in"'
expect "Ada now has both logs" '[ "$(ls "$T"/ada/provenance/log/*/events.jsonl | wc -l | tr -d " ")" = 2 ]'
expect "the merge commit is signed by Ada" 'in_git "$T/ada" log --merges -1 --format=%B | grep -q "^Attested-by: Ada Test"'
expect "the merge reaches the shared repository" '[ "$(git -C "$T/origin.git" rev-parse main)" = "$(in_git "$T/ada" rev-parse HEAD)" ]'
expect "nothing was rebased: Ben's commit is unchanged in Ada's history" 'in_git "$T/ada" merge-base --is-ancestor "$(in_git "$T/ben" rev-parse HEAD)" HEAD'

echo "== 4. Both edit the same line: Ben's save stops and changes nothing"
reply=$(attest "$T/ben" "/attest")   # Ben catches up with Ada's merge first
echo "      reply: $reply"
expect "Ben's catch-up merge is signed by Ben" 'in_git "$T/ben" log --merges -1 --format=%B | grep -q "^Attested-by: Ben Test"'
printf 'line one, as Ada has it\n' > "$T/ada/paper.md"
reply=$(attest "$T/ada" "/attest Ada edits line one")
echo "      reply: $reply"
printf 'line one, as Ben has it\n' > "$T/ben/paper.md"
before=$(git -C "$T/origin.git" rev-parse main)
reply=$(attest "$T/ben" "/attest Ben edits line one")
echo "      reply: $reply"
expect "Ben's /attest names the conflicting file" 'echo "$reply" | grep -q "conflicts with yours in: paper.md"'
expect "no merge is left half-done in Ben's copy" '[ ! -e "$T/ben/.git/MERGE_HEAD" ]'
expect "Ben's version of the file is untouched" 'grep -q "as Ben has it" "$T/ben/paper.md"'
expect "nothing was pushed" '[ "$(git -C "$T/origin.git" rev-parse main)" = "$before" ]'

echo "== 5. The final version is tagged and pushed"
reply=$(attest "$T/ada" "/attest final")
echo "      reply: $reply"
expect "the dated final tag reaches the shared repository" '[ -n "$(git -C "$T/origin.git" tag --list "final-*")" ]'

echo "== 6. Snapshots and logs"
expect "both copies' snapshots are in the shared repository" '[ "$(git -C "$T/origin.git" for-each-ref "refs/provenance/*/snapshots" | wc -l | tr -d " ")" = 2 ]'
expect "Ada has Ben's snapshots, kept apart from his own" '[ -n "$(in_git "$T/ada" for-each-ref "refs/provenance-remote/ben-test-*/snapshots")" ]'
expect "every log verifies in Ada's copy" '(cd "$T/ada" && python3 provenance/verify_log.py > /dev/null)'
expect "every log verifies in Ben's copy" '(cd "$T/ben" && python3 provenance/verify_log.py > /dev/null)'

echo "== 7. Catching up at session start, and /sync (a third coauthor, Jo)"
# start DIR: open a session in DIR; print the notice shown to the human, if any.
start() {
	hook "$1" "" SessionStart | python3 -c 'import sys,json; t=sys.stdin.read().strip(); print(json.loads(t)["systemMessage"] if t else "")'
}
git clone -q "$T/origin.git" "$T/jo"
setup "$T/jo" "Jo Test <jo@test>"
notice=$(start "$T/jo")
expect "nothing to bring in: no notice" '[ -z "$notice" ]'

hook "$T/ada" d7 UserPromptSubmit "same words"     # Ada's prompt, saved below
printf 'notes\n' > "$T/ada/notes.md"
attest "$T/ada" "/attest" > /dev/null
hook "$T/jo" j7 UserPromptSubmit "same words"        # Jo's identical prompt, unsaved
notice=$(start "$T/jo")
echo "      notice: $notice"
expect "Jo is told what came in" 'echo "$notice" | grep -q "Brought in 1 new save from coauthors: notes.md"'
expect "Jo's copy now matches the shared repository" '[ "$(in_git "$T/jo" rev-parse HEAD)" = "$(git -C "$T/origin.git" rev-parse main)" ]'
expect "catching up made no commit of Jo's" '[ -z "$(in_git "$T/jo" log --format=%an | grep "Jo Test")" ]'
expect "Jo's log records what came in" 'grep "\"event\":\"SessionStart\"" "$T"/jo/provenance/log/jo-test-*/events.jsonl | tail -1 | grep -q "\"result\":\"brought in\""'

printf 'line one, as Ada has it now\n' > "$T/ada/paper.md"
attest "$T/ada" "/attest" > /dev/null
printf 'line one, Jo is editing\n' > "$T/jo/paper.md"
before=$(in_git "$T/jo" rev-parse HEAD)
notice=$(start "$T/jo")
echo "      notice: $notice"
expect "Jo is told her unsaved file blocks it" 'echo "$notice" | grep -q "haven.t saved: paper.md"'
expect "nothing changed in Jo's copy" '[ "$(in_git "$T/jo" rev-parse HEAD)" = "$before" ] && grep -q "Jo is editing" "$T/jo/paper.md"'

in_git "$T/jo" checkout -q -- paper.md               # Jo drops her edit
reply=$(hook "$T/jo" j8 UserPromptSubmit "/sync" | python3 -c 'import sys,json; print(json.load(sys.stdin)["reason"])')
echo "      /sync: $reply"
expect "/sync brings in Ada's save" 'echo "$reply" | grep -q "Brought in 1 new save"'
reply=$(hook "$T/jo" j9 UserPromptSubmit "/sync" | python3 -c 'import sys,json; print(json.load(sys.stdin)["reason"])')
expect "/sync again says up to date" 'echo "$reply" | grep -q "Already up to date"'

in_git "$T/jo" remote set-url origin "$T/missing.git"   # Jo goes offline
printf 'jo draft\n' > "$T/jo/jo.md"
attest "$T/jo" "/attest" > /dev/null                     # her save stays on her computer
in_git "$T/jo" remote set-url origin "$T/origin.git"    # back online
printf 'more notes\n' >> "$T/ada/notes.md"
attest "$T/ada" "/attest" > /dev/null
before=$(in_git "$T/jo" rev-parse HEAD)
notice=$(start "$T/jo")
echo "      notice: $notice"
expect "with saves on both sides, Jo is told /warrant:attest will combine them" 'echo "$notice" | grep -q "next /warrant:attest will combine"'
expect "nothing changed in Jo's copy" '[ "$(in_git "$T/jo" rev-parse HEAD)" = "$before" ]'
expect "every log verifies in Jo's copy" '(cd "$T/jo" && python3 provenance/verify_log.py > /dev/null)'

echo "== 8. /undo"
undo() { hook "$1" "undo-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')" UserPromptSubmit "/undo" | python3 -c 'import sys,json; print(json.load(sys.stdin)["reason"])'; }
dlog=$(ls "$T"/ada/provenance/log/ada-test-*/events.jsonl)
printf 'oops\n' > "$T/ada/oops.md"
attest "$T/ada" "/attest" > /dev/null
lines_before=$(wc -l < "$dlog")
reply=$(undo "$T/ada")
echo "      reply: $reply"
expect "the mistaken file is gone" '[ ! -e "$T/ada/oops.md" ]'
expect "the undo is a new save naming what it undid" 'in_git "$T/ada" log -1 --format=%B | grep -q "^Undoes: " && in_git "$T/ada" log -1 --format=%s | grep -q "^Undo: "'
expect "the undone save is still in history" 'in_git "$T/ada" log --format=%s | grep -c "^Attest" | grep -qv "^0$"'
expect "the record was not undone: the log only grew" '[ "$(wc -l < "$dlog")" -gt "$lines_before" ]'
expect "the undo reaches the shared repository" '[ "$(git -C "$T/origin.git" rev-parse main)" = "$(in_git "$T/ada" rev-parse HEAD)" ]'

printf 'a line Ada adds\n' >> "$T/ada/notes.md"
attest "$T/ada" "/attest" > /dev/null
printf 'an unsaved edit\n' >> "$T/ada/notes.md"
before=$(in_git "$T/ada" rev-parse HEAD)
reply=$(undo "$T/ada")
echo "      reply: $reply"
expect "unsaved edits to the same file block the undo" 'echo "$reply" | grep -q "unsaved edits to notes.md"'
expect "nothing changed" '[ "$(in_git "$T/ada" rev-parse HEAD)" = "$before" ] && grep -q "an unsaved edit" "$T/ada/notes.md"'
in_git "$T/ada" checkout -q -- notes.md

in_git "$T/jo" remote set-url origin "$T/origin.git"
attest "$T/jo" "/attest" > /dev/null                         # Jo combines her offline save
hook "$T/jo" j10 UserPromptSubmit "/sync" > /dev/null
sed -i '' 's/a line Ada adds/a line Jo rewrote/' "$T/jo/notes.md"
attest "$T/jo" "/attest" > /dev/null                         # Jo changes Ada's line
hook "$T/ada" d10 UserPromptSubmit "/sync" > /dev/null     # Ada brings it in
before=$(in_git "$T/ada" rev-parse HEAD)
reply=$(undo "$T/ada")
echo "      reply: $reply"
expect "later work on the same lines blocks the undo" 'echo "$reply" | grep -q "later work changed the same lines"'
expect "nothing changed" '[ "$(in_git "$T/ada" rev-parse HEAD)" = "$before" ] && grep -q "a line Jo rewrote" "$T/ada/notes.md"'
expect "every log verifies in Ada's copy" '(cd "$T/ada" && python3 provenance/verify_log.py > /dev/null)'

if [ "${KEEP:-0}" = 1 ]; then echo "Kept $T"; else rm -rf "$T"; fi
echo
if [ "$failures" -eq 0 ]; then echo "All checks passed."; else echo "$failures check(s) failed."; exit 1; fi
