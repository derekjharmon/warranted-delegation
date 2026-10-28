"""The reader's other backends: the same calls through Codex or Gemini, on
the author's own account, for projects that use those tools (DECISIONS.md,
Oct 16). Claude's paths, the API and headless Claude Code, stay in reader.py.

Each call gets the reader's instructions, the content, and the answer's JSON
schema, and returns the parsed answer. It runs from an empty folder, so the
agent has nothing of the project's to read, and is told to answer from the
text alone. Each adds what it reports about tokens and time to usage.

    call_codex   codex exec, read-only, ephemeral, with --output-schema
    call_gemini  gemini -p, asking for JSON in the schema's shape (Gemini CLI
                 takes no schema), checked against the schema's required keys
"""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

CODEX = "codex-cli"
GEMINI = "gemini-cli"
NAMES = {CODEX: "Codex", GEMINI: "Gemini"}
TIMEOUT = 60 * 60
CODEX_MODEL = os.environ.get("WD_CODEX_MODEL")  # None: the account's default model, as the run records
CODEX_EFFORT = "high"
GEMINI_MODEL = os.environ.get("WD_GEMINI_MODEL")
# How each reader did on the second preregistered test's twelve runs
# (tests/scripted2/other_readers.py), as each disclosure it writes says. A reader
# that falls short of the bar is still offered, with that note (DECISIONS.md, Oct 16).
STANDING = {CODEX: "The Codex reader hasn't yet been scored against the test runs that validated Claude's.",
            GEMINI: "The Gemini reader hasn't yet been scored against the test runs that validated Claude's."}
ANSWER_ONLY = ("Answer from the text in this message alone. Don't run any commands or read any files. Reply with "
               "only the JSON the schema describes.")


def message(system, content):
    return f"{system}\n\n{ANSWER_ONLY}\n\n" + "".join(part["text"] for part in content)


def clean_env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("CLAUDE", "ANTHROPIC_", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"))}


def add(usage, key, n):
    usage[key] = usage.get(key, 0) + (n or 0)


def call_codex(system, content, schema, max_tokens, usage):
    start = time.time()
    with tempfile.TemporaryDirectory(prefix="wd-reader-") as empty:
        schema_file, last = Path(empty) / "schema.json", Path(empty) / "answer.json"
        schema_file.write_text(json.dumps(schema))
        args = ["codex", "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-rules", "--sandbox", "read-only",
                "--cd", empty, "--output-schema", str(schema_file), "--output-last-message", str(last), "--json",
                "--color", "never", "-c", f'model_reasoning_effort="{CODEX_EFFORT}"',
                *(["--model", CODEX_MODEL] if CODEX_MODEL else []), "-"]
        r = subprocess.run(args, input=message(system, content), capture_output=True, text=True, cwd=empty,
                           env=clean_env(), timeout=TIMEOUT)
        answer = last.read_text() if last.exists() else ""
    for line in r.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        u = event.get("usage") or (event.get("msg") or {}).get("usage") or {}
        add(usage, "input_tokens", u.get("input_tokens"))
        add(usage, "cache_read_input_tokens", u.get("cached_input_tokens"))
        add(usage, "output_tokens", u.get("output_tokens"))
        model = event.get("model") or (event.get("msg") or {}).get("model")
        if model:
            usage["model"] = model
    add(usage, "calls", 1)
    add(usage, "seconds", round(time.time() - start))
    try:
        return json.loads(answer)
    except json.JSONDecodeError:
        raise SystemExit(f"Codex gave no answer (exit {r.returncode}): {(r.stderr or r.stdout)[-500:]}")


def call_gemini(system, content, schema, max_tokens, usage):
    start = time.time()
    prompt = (message(system, content) + "\n\nThe JSON schema your reply must follow:\n"
              + json.dumps(schema))
    with tempfile.TemporaryDirectory(prefix="wd-reader-") as empty:
        args = ["gemini", "--output-format", "json", *(["--model", GEMINI_MODEL] if GEMINI_MODEL else [])]
        r = subprocess.run(args, input=prompt, capture_output=True, text=True, cwd=empty, env=clean_env(),
                           timeout=TIMEOUT)
    try:
        out = json.loads(r.stdout)
        text = out.get("response") or ""
        answer = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (json.JSONDecodeError, ValueError, AttributeError):
        raise SystemExit(f"Gemini gave no answer (exit {r.returncode}): {(r.stderr or r.stdout)[-500:]}")
    for model, m in ((out.get("stats") or {}).get("models") or {}).items():
        t = m.get("tokens") or {}
        add(usage, "input_tokens", t.get("prompt"))
        add(usage, "cache_read_input_tokens", t.get("cached"))
        add(usage, "output_tokens", t.get("candidates"))
        usage["model"] = model
    missing = [k for k in schema.get("required", []) if k not in answer]
    if missing:
        raise SystemExit(f"Gemini's answer is missing {', '.join(missing)}")
    add(usage, "calls", 1)
    add(usage, "seconds", round(time.time() - start))
    return answer
