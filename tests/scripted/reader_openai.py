#!/usr/bin/env python3
"""Rerun the frozen reader with an OpenAI model in place of Claude, on the four
scored runs, and score it against the same answer key: does the agreement hold
when Claude isn't grading Claude? (PROGRESS.md; the author chose Codex, Oct 7.)

    python3 tests/scripted/reader_openai.py [model]     # default gpt-5.3-codex

Everything but the model is the scored setup: provenance/reader.py (0.6.1;
its coding is 0.6's), its prompts and schemas, and the checklists exactly as
they stood when the reader was frozen (commit 23abd4b), before the packs were
added. Only the call to the model changes: OpenAI's Responses API, with the
same instructions, the same text, and the same JSON schema, at high reasoning
effort. The key comes from the Keychain item "warranted-delegation-openai",
never from an environment variable. Output goes to
tests/scripted/reader-runs/openai-<model>/<run>/, with score.md and score.json
there from the frozen score.py.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FROZEN_COMMIT = "23abd4b"
KEYCHAIN_ITEM = "warranted-delegation-openai"
sys.path.insert(0, str(HERE))
import score  # noqa: E402


def frozen_reader(checklists_dir):
    sys.path.insert(0, str(REPO / "provenance"))
    spec = importlib.util.spec_from_file_location("reader_frozen", REPO / "provenance" / "reader.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    reader.TOOL = checklists_dir  # read checklists/ from the frozen commit, not the live folder
    return reader


def openai_call(model, key):
    def call(client, system, content, schema, max_tokens, usage):
        text = "".join(c["text"] for c in content if c.get("type") == "text")
        body = {"model": model, "instructions": system,
                "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}],
                "max_output_tokens": max_tokens + 64000,  # room for reasoning tokens too
                "reasoning": {"effort": "high"},
                "text": {"format": {"type": "json_schema", "name": "reader", "schema": schema, "strict": False}}}
        start = time.time()
        for attempt in range(4):
            req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
                                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=1800) as r:
                    out = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(20 * (attempt + 1))
                    continue
                raise SystemExit(f"OpenAI refused the call ({e.code}): {detail}")
        u = out.get("usage") or {}
        for k, v in (("openai_input_tokens", u.get("input_tokens", 0)),
                     ("openai_cached_tokens", (u.get("input_tokens_details") or {}).get("cached_tokens", 0)),
                     ("openai_output_tokens", u.get("output_tokens", 0)),
                     ("openai_reasoning_tokens", (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0))):
            usage[k] = usage.get(k, 0) + (v or 0)
        usage["calls"] = usage.get("calls", 0) + 1
        usage["seconds"] = usage.get("seconds", 0) + round(time.time() - start)
        if out.get("status") != "completed":
            raise SystemExit(f"The model stopped early: {out.get('incomplete_details') or out.get('status')}")
        text_out = "".join(c.get("text", "") for o in out.get("output", []) if o.get("type") == "message"
                           for c in o.get("content", []) if c.get("type") == "output_text")
        return json.loads(text_out)
    return call


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.3-codex"
    key = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_ITEM, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        sys.exit(f'No key in the Keychain item "{KEYCHAIN_ITEM}".')
    work = Path(tempfile.mkdtemp(prefix="wd-openai-reader-"))
    (work / "checklists").mkdir()
    for name in ("judgment-decisions.md", "checkable-claims.md"):
        (work / "checklists" / name).write_text(
            score.sh(["git", "show", f"{FROZEN_COMMIT}:checklists/{name}"], REPO))
    reader = frozen_reader(work)
    reader.MODEL = model
    reader.PRICES = {}  # Claude's prices don't apply; tokens are recorded instead
    reader.client_from_keychain = lambda: None
    reader.call = openai_call(model, key)
    out = score.OUT / f"openai-{model}"
    for run, bundle in score.RUNS.items():
        base = Path(tempfile.mkdtemp(prefix=f"wd-openai-{run}-"))
        path = HERE / "runs" / f"{bundle}.bundle"
        score.sh(["git", "clone", "-q", str(path), str(base / "project")])
        score.sh(["git", "-C", str(base / "project"), "fetch", "-q", str(path), "refs/provenance/*:refs/provenance/*"])
        print(f"{run}: reading with {model} …", flush=True)
        sys.argv = ["reader.py", str(base / "project"), "--work", *score.WORK, "--out", str(out / run)]
        reader.main()
        shutil.rmtree(base)
    shutil.rmtree(work)
    score.OUT = out
    score.score()
    for p in score._clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)
    print(f"Scored: {out / 'score.md'}")


if __name__ == "__main__":
    main()
