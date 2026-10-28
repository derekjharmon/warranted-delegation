#!/usr/bin/env python3
"""Rerun the frozen reader on the four scored runs and score each rerun, to
see how stable the result is. Current models take no temperature setting, so
reruns differ.

    python3 tests/scripted/replicate.py 2 3     # replicates 2 and 3

Replicate 1 is the original run in tests/scripted/reader-runs/<run>/. Each
replicate N goes to tests/scripted/reader-runs/rep<N>/<run>/ with its own
score.md and score.json, scored by the same frozen score.py. Refuses to start
unless the reader, the checklists, the key, and score.py are committed
unchanged.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402


def main():
    reps = [int(a) for a in sys.argv[1:]]
    if not reps or min(reps) < 2:
        sys.exit(__doc__)
    changed = score.sh(["git", "status", "--porcelain", "--", *score.FROZEN], score.REPO).strip()
    if changed:
        sys.exit(f"Commit these first, so the reader and the key are frozen:\n{changed}")
    for n in reps:
        out = score.OUT / f"rep{n}"
        for run, bundle in score.RUNS.items():
            base = Path(tempfile.mkdtemp(prefix=f"wd-rep{n}-{run}-"))
            path = HERE / "runs" / f"{bundle}.bundle"
            score.sh(["git", "clone", "-q", str(path), str(base / "project")])
            score.sh(["git", "-C", str(base / "project"), "fetch", "-q", str(path), "refs/provenance/*:refs/provenance/*"])
            print(f"rep{n} {run}: reading …", flush=True)
            r = subprocess.run([str(score.READER_PY), str(score.REPO / "provenance/reader.py"), str(base / "project"),
                                "--work", *score.WORK, "--out", str(out / run)], capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip()[-400:], flush=True)
            shutil.rmtree(base)
            if r.returncode:
                sys.exit(f"rep{n} {run}: the reader failed")
        score.OUT = out
        score.score()
        score.OUT = HERE / "reader-runs"
    for p in score._clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
