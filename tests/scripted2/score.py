#!/usr/bin/env python3
"""Run the frozen reader on the second test's twelve runs, and score it
against the settled key in tests/scripted2/labels/.

    python3 tests/scripted2/score.py read api            # the reader through the API
    python3 tests/scripted2/score.py read claude-code    # through headless Claude Code, no key
    python3 tests/scripted2/score.py score               # both paths against the key

read: for each run's bundle in runs/ (exactly one per task and cell), clones
it with its snapshots into a throwaway folder and runs the frozen reader
(plugin/warrant/scripts/reader.py) on it, with the task's finished work and
packs, keeping the output in reader-runs/<backend>/<task>-<cell>/. It
refuses to start unless the reader, the checklists, the key, and this script
are committed unchanged, so the key is settled before the reader sees any
run, as in the first test.

score: the first test's scoring (tests/scripted/score.py), unchanged except
that it covers twelve runs and scores each path on its own. Each key unit is
matched to a reader unit of the same kind whose quotes, restatements
included, overlap it in the same file, preferring the same checklist row
(rows compared without a letter suffix, so S5a and S5 are the same row),
then the most overlap. One reader unit may match several key units. Layers,
pooled over the twelve runs:
- decisions, primary: kept vs handed over (given or taken)
- decisions, second layer: given vs taken, where both say handed over
- judgment certification, where both say handed over
- claims, primary: you checked / tool checked, you confirmed / tool checked,
  you didn't see the result / unchecked
- claims, second layer: no check vs wasn't notified, where both say
  unchecked
The bar (README): κ of at least 0.6 on the three primary codes, for each
path on its own. Per-task results are reported beside the pooled ones, not
held to the bar. Results go to reader-runs/score.md and score.json.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from run import TASKS, CELLS  # noqa: E402

READER = REPO / "plugin" / "warrant" / "scripts" / "reader.py"
READER_PY = Path.home() / ".warranted-delegation/venv/bin/python"
PACKS = {"schools": ["quantitative"], "agreement": ["tool"], "rand": ["quantitative", "experiments"]}
BACKENDS = ("api", "claude-code")
OUT = HERE / "reader-runs"
FROZEN = ["plugin/warrant/scripts", "plugin/warrant/checklists", "tests/scripted2/labels", "tests/scripted2/score.py"]
PRIMARY = ["decisions: kept vs handed over", "judgment certification", "claims: certification"]


def sh(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{' '.join(map(str, args[:3]))} failed: {r.stderr.strip()[-400:]}")
    return r.stdout


def runs():
    """{(task, cell): bundle path}, exactly one bundle per run."""
    found = {}
    for task in TASKS:
        for cell in CELLS:
            bundles = sorted((HERE / "runs").glob(f"{task}-{cell}-*.bundle"))
            if len(bundles) != 1:
                sys.exit(f"{task} {cell}: expected one bundle in runs/, found {len(bundles)}")
            found[(task, cell)] = bundles[0]
    return found


def read(backend):
    changed = sh(["git", "status", "--porcelain", "--", *FROZEN], REPO).strip()
    if changed:
        sys.exit(f"Commit these first, so the reader and the key are frozen:\n{changed}")
    for (task, cell), bundle in runs().items():
        base = Path(tempfile.mkdtemp(prefix=f"wd-score2-{task}-{cell}-"))
        sh(["git", "clone", "-q", str(bundle), str(base / "project")])
        sh(["git", "-C", str(base / "project"), "fetch", "-q", str(bundle), "refs/provenance/*:refs/provenance/*"])
        print(f"{backend} {task} {cell}: reading …", flush=True)
        r = subprocess.run([str(READER_PY), str(READER), str(base / "project"), "--work", *TASKS[task]["work"],
                            "--packs", *PACKS[task], "--backend", backend,
                            "--out", str(OUT / backend / f"{task}-{cell}")], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:], flush=True)
        shutil.rmtree(base)
        if r.returncode:
            sys.exit(f"{backend} {task} {cell}: the reader failed")
    head = sh(["git", "rev-parse", "HEAD"], REPO).strip()
    (OUT / backend / "read.json").write_text(json.dumps(
        {"repo_head": head, "backend": backend, "runs": {f"{t}-{c}": b.name for (t, c), b in runs().items()}},
        indent=1) + "\n")


def text_at(clone, f):
    """A file at the run's final commit, as text. Undecodable bytes are
    replaced, so an image a reader unit names (a PNG figure) is read without
    error and simply matches no quote. Added Oct 15, after the reading, when
    the first image anchor stopped the scorer; it changes nothing for text
    files (reported as a departure with the results)."""
    r = subprocess.run(["git", "show", f"HEAD:{f}"], cwd=clone, capture_output=True)
    if r.returncode:
        sys.exit(f"git show HEAD:{f} failed: {r.stderr.decode(errors='replace').strip()[-400:]}")
    return r.stdout.decode("utf-8", errors="replace")


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
    cats = sorted({x for p in pairs for x in p}, key=str)
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pe = sum((sum(x == c for x, _ in pairs) / n) * (sum(y == c for _, y in pairs) / n) for c in cats)
    return po, ((po - pe) / (1 - pe) if pe < 1 else 1.0)


def handed(d):
    return "kept" if d == "kept" else "handed over" if d in ("given", "taken") else None


def ra_primary(c):
    return "unchecked" if c in ("no check", "wasn't notified") else c


def row(r):
    return re.sub(r"[a-z]+$", "", r or "")


def none(x):
    return None if x in (None, "none") else x


def score_path(backend, bundles):
    layers = {k: [] for k in ("decisions: kept vs handed over", "decisions: given vs taken",
                              "judgment certification", "claims: certification",
                              "claims: no check vs wasn't notified")}
    by_task = {t: {k: [] for k in PRIMARY} for t in TASKS}
    listing, mismatches = {}, []
    for (task, cell), bundle in bundles.items():
        name = f"{task}-{cell}"
        key = json.loads((HERE / "labels" / f"{name}.json").read_text())["units"]
        rdir = OUT / backend / name
        runits = json.loads((rdir / "units.json").read_text())["units"]
        codes = json.loads((rdir / "codes.json").read_text())
        clone = _clone(bundle)
        files = {a["file"] for u in key + runits for a in u["anchors"]}
        texts = {f: squash(text_at(clone, f)) for f in files
                 if subprocess.run(["git", "cat-file", "-e", f"HEAD:{f}"], cwd=clone).returncode == 0}
        rspans = {u["id"]: spans(u, texts) for u in runits}
        used, found = set(), 0
        for k in key:
            ks = spans(k, texts)
            best = max((u for u in runits if u["kind"] == k["kind"] and overlap(ks, rspans[u["id"]]) > 0),
                       key=lambda u: (row(u["row"]) == row(k["row"]), overlap(ks, rspans[u["id"]])), default=None)
            if best is None:
                mismatches.append((name, k["id"], k["row"], k["label"], "not found by the reader"))
                continue
            found += 1
            used.add(best["id"])
            c = codes.get(best["id"], {})
            pairs = []
            if k["kind"] == "decision":
                pairs.append(("decisions: kept vs handed over", (handed(k["discretion"]), handed(c.get("discretion")))))
                if handed(k["discretion"]) == handed(c.get("discretion")) == "handed over":
                    pairs.append(("decisions: given vs taken", (k["discretion"], c.get("discretion"))))
                    pairs.append(("judgment certification", (k["certification"], none(c.get("certification")))))
            else:
                pairs.append(("claims: certification", (ra_primary(k["certification"]), ra_primary(c.get("certification")))))
                if ra_primary(k["certification"]) == ra_primary(c.get("certification")) == "unchecked":
                    pairs.append(("claims: no check vs wasn't notified", (k["certification"], c.get("certification"))))
            for layer, pair in pairs:
                layers[layer].append(pair)
                if layer in PRIMARY:
                    by_task[task][layer].append(pair)
            mine = (k.get("discretion"), k.get("certification"))
            theirs = (none(c.get("discretion")) if k["kind"] == "decision" else None, none(c.get("certification")))
            if mine != theirs:
                mismatches.append((name, k["id"], k["row"], k["label"],
                                   f"key {k.get('discretion') or ''} {k['certification'] or ''} | "
                                   f"reader {c.get('discretion')} {c.get('certification')} ({best['id']})"))
        listing[name] = {"key units": len(key), "found": found, "reader units": len(runits),
                         "reader units matching no key unit": len(runits) - len(used)}
    results = {n: dict(zip(("agreement", "kappa"), kappa(p)), n=len(p)) for n, p in layers.items()}
    tasks = {t: {n: dict(zip(("agreement", "kappa"), kappa(p)), n=len(p)) for n, p in v.items()} for t, v in by_task.items()}
    passed = all((results[p]["kappa"] or 0) >= 0.6 for p in PRIMARY)
    return {"layers": results, "by_task": tasks, "listing": listing, "mismatches": mismatches, "validated": passed}


def score():
    bundles = runs()
    paths = {b: score_path(b, bundles) for b in BACKENDS}
    both = all(p["validated"] for p in paths.values())
    lines = ["# The fixed reader scored against the settled key", "",
             "*Generated by `tests/scripted2/score.py`.*", "",
             f"**Validated (κ ≥ 0.6 on all three primary codes, on each path on its own): {'yes' if both else 'no'}.**", "",
             "| Layer | " + " | ".join(f"{b}: n | {b}: agreement | {b}: κ" for b in BACKENDS) + " |",
             "| :- |" + " -: | -: | -: |" * len(BACKENDS)]
    for name in paths[BACKENDS[0]]["layers"]:
        tag = " (primary)" if name in PRIMARY else " (second layer)"
        cells = " | ".join(f"{r['n']} | {_pct(r['agreement'])} | {_num(r['kappa'])}"
                           for r in (paths[b]["layers"][name] for b in BACKENDS))
        lines.append(f"| {name}{tag} | {cells} |")
    lines += [""] + [f"- {b}: {'clears' if paths[b]['validated'] else 'does not clear'} the bar." for b in BACKENDS]
    lines += ["", "## By task (reported, not held to the bar)", "", "| Task | Code | " +
              " | ".join(f"{b}: n | {b}: κ" for b in BACKENDS) + " |", "| :- | :- |" + " -: | -: |" * len(BACKENDS)]
    for t in TASKS:
        for name in PRIMARY:
            cells = " | ".join(f"{paths[b]['by_task'][t][name]['n']} | {_num(paths[b]['by_task'][t][name]['kappa'])}"
                               for b in BACKENDS)
            lines.append(f"| {t} | {name} | {cells} |")
    for b in BACKENDS:
        lines += ["", f"## Listing: {b}", "", "| Run | Key units | Found | Reader units | Reader units matching no key unit |",
                  "| :- | -: | -: | -: | -: |"]
        lines += [f"| {r} | {v['key units']} | {v['found']} | {v['reader units']} | {v['reader units matching no key unit']} |"
                  for r, v in paths[b]["listing"].items()]
        lines += ["", f"## Units where the reader and the key differ: {b}", "", "| Run | Key unit | Row | Unit | Difference |",
                  "| :- | :- | :- | :- | :- |"]
        lines += [f"| {r} | {i} | {rw} | {label} | {why} |" for r, i, rw, label, why in paths[b]["mismatches"]]
    OUT.mkdir(exist_ok=True)
    (OUT / "score.md").write_text("\n".join(lines) + "\n")
    (OUT / "score.json").write_text(json.dumps({b: {k: v for k, v in p.items() if k != "mismatches"}
                                                for b, p in paths.items()} | {"validated": both}, indent=1) + "\n")
    print("\n".join(lines[:9 + len(paths[BACKENDS[0]]["layers"]) + 3]))


_clones = {}


def _clone(bundle):
    if bundle not in _clones:
        base = Path(tempfile.mkdtemp(prefix="wd-score2-view-"))
        sh(["git", "clone", "-q", str(bundle), str(base / "p")])
        _clones[bundle] = base / "p"
    return _clones[bundle]


def _pct(x):
    return "—" if x is None else f"{round(100 * x)}%"


def _num(x):
    return "—" if x is None else f"{x:.2f}"


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["read"] and len(args) == 2 and args[1] in BACKENDS:
        read(args[1])
    elif args == ["score"]:
        score()
    else:
        sys.exit(__doc__)
    for p in _clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)
