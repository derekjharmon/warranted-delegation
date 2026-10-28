#!/usr/bin/env python3
"""Run the fixed reader on the four scored runs and score it, as an
exploratory comparison with the frozen reader (DECISIONS.md, Oct 12).

    python3 tests/scripted/explore_fixed.py api
    python3 tests/scripted/explore_fixed.py claude-code

These numbers are exploratory, not a test: the fix was designed from these
runs' misses (reader-runs/misses-checked.md). The frozen reader's
preregistered result stays the headline. The fixed reader gets its own
preregistered test on new runs.

Runs the plugin's reader (plugin/warrant/scripts/reader.py) through the API
(the Keychain key) or headless Claude Code (the subscription, no key), with
the spine and the quantitative pack, the checklist the frozen reader saw
(commit 23abd4b had no other packs). Each run goes to
tests/scripted/reader-runs/fixed-<version>-<backend>/<run>/, scored there by
the same frozen score.py and key. Refuses to start unless the reader, the
checklists, the key, and score.py are committed unchanged.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402

READER = score.REPO / "plugin" / "warrant" / "scripts" / "reader.py"


def version():
    text = READER.read_text()
    return text.split('READER_VERSION = "', 1)[1].split('"', 1)[0]


def main():
    if sys.argv[1:] not in (["api"], ["claude-code"]):
        sys.exit(__doc__)
    backend = sys.argv[1]
    frozen = [*score.FROZEN, "plugin/warrant/scripts", "plugin/warrant/checklists"]
    changed = score.sh(["git", "status", "--porcelain", "--", *frozen], score.REPO).strip()
    if changed:
        sys.exit(f"Commit these first, so the reader and the key are fixed:\n{changed}")
    out = score.OUT / f"fixed-{version()}-{backend}"
    for run, bundle in score.RUNS.items():
        base = Path(tempfile.mkdtemp(prefix=f"wd-fixed-{run}-"))
        path = HERE / "runs" / f"{bundle}.bundle"
        score.sh(["git", "clone", "-q", str(path), str(base / "project")])
        score.sh(["git", "-C", str(base / "project"), "fetch", "-q", str(path), "refs/provenance/*:refs/provenance/*"])
        print(f"{backend} {run}: reading …", flush=True)
        r = subprocess.run([str(score.READER_PY), str(READER), str(base / "project"), "--work", *score.WORK,
                            "--packs", "quantitative", "--backend", backend, "--out", str(out / run)],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:], flush=True)
        shutil.rmtree(base)
        if r.returncode:
            sys.exit(f"{backend} {run}: the reader failed")
    head = score.sh(["git", "rev-parse", "HEAD"], score.REPO).strip()
    (out / "read.json").write_text(json.dumps({"repo_head": head, "runs": score.RUNS, "work": score.WORK,
                                               "packs": ["quantitative"], "backend": backend,
                                               "exploratory": True}, indent=1) + "\n")
    score.OUT = out
    score.score()
    for p in score._clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
