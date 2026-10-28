#!/usr/bin/env python3
"""Run the frozen reader on the four scored runs, and score it against the
settled answer key in tests/scripted/labels/.

    python3 tests/scripted/score.py read     # run the reader on each bundle
    python3 tests/scripted/score.py score    # compare its codes with the key

read: clones each run's bundle (with its snapshots) into a throwaway folder,
runs provenance/reader.py on it with the finished work memo.md, analysis/ and
output/, and keeps the reader's output in tests/scripted/reader-runs/<run>/.
It refuses to start unless the reader, the checklists, and the key are
committed unchanged.

score: matches each key unit to a reader unit of the same kind (decision or
claim) whose quoted anchors overlap it in the same file, takes the reader
unit with the most overlap, and compares codes. One reader unit may match
several key units, since the two may list at different grain. It reports:
- listing: key units the reader found, missed, and reader units matching no
  key unit
- agreement and Cohen's kappa on each layer, pooled over the four runs:
  - decisions, primary: kept vs handed over (given or taken)
  - decisions, second layer: given vs taken, where both say handed over
  - judgment certification, where both say handed over
  - claims, primary: you checked / tool checked, you confirmed / tool
    checked, you didn't see the result / unchecked
  - claims, second layer: no check vs wasn't notified, where both say
    unchecked
PLAN's 0.6 rule applies to the three primary codes (decisions primary,
judgment certification, claims primary). Results go to
tests/scripted/reader-runs/score.md and score.json.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RUNS = {"careful": "careful-2026-10-06-1457", "unchecked": "unchecked-2026-10-06-1446",
        "careless": "careless-2026-10-06-1434", "owned": "owned-2026-10-06-1521"}
WORK = ["memo.md", "analysis/", "output/"]
OUT = HERE / "reader-runs"
READER_PY = Path.home() / ".warranted-delegation/venv/bin/python"
FROZEN = ["provenance/reader.py", "checklists", "tests/scripted/labels", "tests/scripted/score.py"]


def sh(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{' '.join(map(str, args[:3]))} failed: {r.stderr.strip()[-400:]}")
    return r.stdout


def read():
    changed = sh(["git", "status", "--porcelain", "--", *FROZEN], REPO).strip()
    if changed:
        sys.exit(f"Commit these first, so the reader and the key are frozen:\n{changed}")
    for run, bundle in RUNS.items():
        base = Path(tempfile.mkdtemp(prefix=f"wd-score-{run}-"))
        path = HERE / "runs" / f"{bundle}.bundle"
        sh(["git", "clone", "-q", str(path), str(base / "project")])
        sh(["git", "-C", str(base / "project"), "fetch", "-q", str(path), "refs/provenance/*:refs/provenance/*"])
        print(f"{run}: reading …", flush=True)
        r = subprocess.run([str(READER_PY), str(REPO / "provenance/reader.py"), str(base / "project"),
                            "--work", *WORK, "--out", str(OUT / run)], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:])
        shutil.rmtree(base)
        if r.returncode:
            sys.exit(f"{run}: the reader failed")
    head = sh(["git", "rev-parse", "HEAD"], REPO).strip()
    (OUT / "read.json").write_text(json.dumps({"repo_head": head, "runs": RUNS, "work": WORK}, indent=1) + "\n")


def squash(text):
    return " ".join(text.split())


def spans(unit, texts):
    out = []
    for a in unit["anchors"]:
        text = texts.get(a["file"])
        q = squash(a["quote"])
        if text is None or not q:
            continue
        i = text.find(q)
        if i >= 0:
            out.append((a["file"], i, i + len(q)))
    return out


def overlap(s1, s2):
    return sum(max(0, min(b1, b2) - max(a1, a2)) for f1, a1, b1 in s1 for f2, a2, b2 in s2 if f1 == f2)


def kappa(pairs):
    if not pairs:
        return None, None
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pe = sum((sum(x == c for x, _ in pairs) / n) * (sum(y == c for _, y in pairs) / n) for c in cats)
    return po, ((po - pe) / (1 - pe) if pe < 1 else 1.0)


def handed(d):
    return "kept" if d == "kept" else "handed over" if d in ("given", "taken") else None


def ra_primary(c):
    return "unchecked" if c in ("no check", "wasn't notified") else c


def score():
    layers = {k: [] for k in ("decisions: kept vs handed over", "decisions: given vs taken",
                              "judgment certification", "claims: certification", "claims: no check vs wasn't notified")}
    listing, per_run, mismatches = {}, {}, []
    for run, bundle in RUNS.items():
        key = json.loads((HERE / "labels" / f"{run}.json").read_text())["units"]
        rdir = OUT / run
        runits = json.loads((rdir / "units.json").read_text())["units"]
        codes = json.loads((rdir / "codes.json").read_text())
        files = {a["file"] for u in key + runits for a in u["anchors"]}
        texts = {f: squash(sh(["git", "show", f"{_tip(bundle)}:{f}"], _clone(bundle))) for f in files if _exists(bundle, f)}
        rspans = {u["id"]: spans(u, texts) for u in runits}
        used, found = set(), 0
        for k in key:
            ks = spans(k, texts)
            # prefer a reader unit from the same checklist row, then the most overlap
            best = max((u for u in runits if u["kind"] == k["kind"] and overlap(ks, rspans[u["id"]]) > 0),
                       key=lambda u: (u["row"].rstrip("abc") == k["row"], overlap(ks, rspans[u["id"]])),
                       default=None)
            if best is None or overlap(ks, rspans[best["id"]]) == 0:
                mismatches.append((run, k["id"], k["row"], k["label"], "not found by the reader"))
                continue
            found += 1
            used.add(best["id"])
            c = codes.get(best["id"], {})
            if k["kind"] == "decision":
                layers["decisions: kept vs handed over"].append((handed(k["discretion"]), handed(c.get("discretion"))))
                if handed(k["discretion"]) == handed(c.get("discretion")) == "handed over":
                    layers["decisions: given vs taken"].append((k["discretion"], c.get("discretion")))
                    layers["judgment certification"].append((k["certification"], _none(c.get("certification"))))
            else:
                layers["claims: certification"].append((ra_primary(k["certification"]), ra_primary(c.get("certification"))))
                if ra_primary(k["certification"]) == ra_primary(c.get("certification")) == "unchecked":
                    layers["claims: no check vs wasn't notified"].append((k["certification"], c.get("certification")))
            mine = (k.get("discretion"), k.get("certification"))
            theirs = (_none(c.get("discretion")) if k["kind"] == "decision" else None, _none(c.get("certification")))
            if mine != theirs:
                mismatches.append((run, k["id"], k["row"], k["label"],
                                   f"key {k.get('discretion') or ''} {k['certification'] or ''} | reader {c.get('discretion')} {c.get('certification')} ({best['id']})"))
        listing[run] = {"key units": len(key), "found": found, "reader units": len(runits),
                        "reader units matching no key unit": len(runits) - len(used)}
    results = {name: dict(zip(("agreement", "kappa"), kappa(pairs)), n=len(pairs)) for name, pairs in layers.items()}
    primary = ["decisions: kept vs handed over", "judgment certification", "claims: certification"]
    passed = all((results[p]["kappa"] or 0) >= 0.6 for p in primary)
    lines = ["# Reader scored against the settled key", "",
             "*Generated by `tests/scripted/score.py`.*", "",
             f"**Validated (κ ≥ 0.6 on all three primary codes): {'yes' if passed else 'no'}.**", "",
             "| Layer | n | Agreement | κ |", "| :- | -: | -: | -: |"]
    for name, r in results.items():
        tag = " (primary)" if name in primary else " (second layer)"
        lines.append(f"| {name}{tag} | {r['n']} | {_pct(r['agreement'])} | {_num(r['kappa'])} |")
    lines += ["", "## Listing", "", "| Run | Key units | Found by the reader | Reader units | Reader units matching no key unit |",
              "| :- | -: | -: | -: | -: |"]
    lines += [f"| {r} | {v['key units']} | {v['found']} | {v['reader units']} | {v['reader units matching no key unit']} |" for r, v in listing.items()]
    lines += ["", "## Units where the reader and the key differ", "", "| Run | Key unit | Row | Unit | Difference |", "| :- | :- | :- | :- | :- |"]
    lines += [f"| {r} | {i} | {row} | {label} | {why} |" for r, i, row, label, why in mismatches]
    OUT.mkdir(exist_ok=True)
    (OUT / "score.md").write_text("\n".join(lines) + "\n")
    (OUT / "score.json").write_text(json.dumps({"layers": results, "listing": listing, "validated": passed}, indent=1) + "\n")
    print("\n".join(lines[:12 + len(results)]))


_clones = {}


def _clone(bundle):
    if bundle not in _clones:
        base = Path(tempfile.mkdtemp(prefix="wd-score-view-"))
        sh(["git", "clone", "-q", str(HERE / "runs" / f"{bundle}.bundle"), str(base / "p")])
        _clones[bundle] = base / "p"
    return _clones[bundle]


def _tip(bundle):
    return sh(["git", "rev-parse", "HEAD"], _clone(bundle)).strip()


def _exists(bundle, f):
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{f}"], cwd=_clone(bundle)).returncode == 0


def _none(x):
    return None if x in (None, "none") else x


def _pct(x):
    return "—" if x is None else f"{round(100 * x)}%"


def _num(x):
    return "—" if x is None else f"{x:.2f}"


if __name__ == "__main__":
    {"read": read, "score": score}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
    for p in _clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)
