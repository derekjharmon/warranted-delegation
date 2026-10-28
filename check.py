#!/usr/bin/env python3
"""Recheck the proposal's numbers from the saved materials, with no model
calls and no account: only git and Python 3.

    python3 check.py

Each line names a claim in the proposal or its appendix (Appendix A11),
recomputes it from the files in this copy, and prints PASS or FAIL with what
it found. A few lines print SAVED instead: they confirm the proposal reports a saved result
that can't be recomputed without a model (the planted errors' fates, judged
by a Claude subagent reading each record) or without paying again (the
reader's cost). Exits 1 if any check fails.

It takes a few minutes, mostly cloning the runs' bundles into a temporary
folder, which is deleted afterward. Nothing in the copy is changed.
"""
import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_root():
    """The copy's root: this file's folder, or its parent when run from reviewer/."""
    here = Path(__file__).resolve().parent
    for p in (here, here.parent):
        if (p / "tests" / "scripted2").is_dir():
            return p
    sys.exit("check.py: run it from the review copy (tests/scripted2/ not found).")


REPO = find_root()
DEMOS = REPO / "tests" / "longdemo" / "runs"
PAPERS = REPO / "tests" / "longdemo" / "papers"
# The twelve kept demonstrations (tests/longdemo/papers/RESULTS.md, "Files").
KEPT = {
    "experiment": ["experiment-low-high-2026-10-17-0841", "experiment-high-low-2026-10-17-1043",
                   "experiment-high-high-2026-10-17-0933", "experiment-low-low-2026-10-17-1022"],
    "qualitative": ["qualitative-low-high-2026-10-17-1528", "qualitative-high-low-2026-10-17-1028",
                    "qualitative-high-high-2026-10-17-0841", "qualitative-low-low-2026-10-17-1528"],
    "archival": ["low-high-2026-10-17-2006", "high-low-2026-10-18-2005",
                 "high-high-2026-10-17-0857", "low-low-2026-10-18-2036"],
}
PLANTS = {"experiment": PAPERS / "experiment" / "plants.md", "qualitative": PAPERS / "qualitative" / "plants.md",
          "archival": REPO / "tests" / "longdemo" / "plants.md"}
WARRANTED = ("changed", "elaborated and okayed", "okayed")
TMP = Path(tempfile.mkdtemp(prefix="wd-check-"))
tally = {"PASS": 0, "FAIL": 0, "SAVED": 0}


def report(status, where, claim, found):
    tally[status] += 1
    print(f"{status:<5}  {where:<8}  {claim}\n{'':17}{found}", flush=True)


PRIMARY_ROWS = ["decisions: kept vs handed over", "judgment certification", "claims: certification"]


def kappa_text(k):
    return "none" if k is None else f"{k:.2f}"


def load(path, name):
    """Import one of the copy's scripts as a module, without running it."""
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])
    return r.stdout


def kept_runs():
    return [r for runs in KEPT.values() for r in runs]


def second_test():
    s2 = load(REPO / "tests" / "scripted2" / "score.py", "score2")
    bundles = s2.runs()
    key = [u for t in s2.TASKS for c in s2.CELLS
           for u in json.loads((s2.HERE / "labels" / f"{t}-{c}.json").read_text())["units"]]
    planted = sum(u["labeled_by"] == "planted" for u in key)
    report("PASS" if (len(bundles), len(key)) == (12, 725) else "FAIL", "§3",
           "The second test: twelve runs, 725 units in the key", f"{len(bundles)} runs, {len(key)} units")
    report("PASS" if planted == 389 and planted * 2 > len(key) else "FAIL", "§5",
           "More than half of the key was fixed before the runs (389 of 725)",
           f"{planted} of {len(key)} units planted by script")
    paths = {b: s2.score_path(b, bundles) for b in s2.BACKENDS}
    kappas = [paths[b]["layers"][p]["kappa"] for b in s2.BACKENDS for p in s2.PRIMARY]
    lo, hi = min(kappas), max(kappas)
    report("PASS" if (f"{lo:.2f}", f"{hi:.2f}") == ("0.71", "0.78") and lo >= 0.6 else "FAIL", "§3",
           "κ of 0.71 to 0.78 on the three primary codes, on both paths, against a bar of 0.6",
           "; ".join(f"{b}: " + ", ".join(f"{paths[b]['layers'][p]['kappa']:.2f}" for p in s2.PRIMARY)
                     for b in s2.BACKENDS))
    found = {b: sum(v["found"] for v in paths[b]["listing"].values()) for b in s2.BACKENDS}
    shares = sorted(round(100 * n / len(key)) for n in found.values())
    report("PASS" if shares == [94, 96] else "FAIL", "§3", "The reader found 94% to 96% of the key's units",
           "; ".join(f"{b}: {n} of {len(key)} ({round(100 * n / len(key))}%)" for b, n in found.items()))
    layers = PRIMARY_ROWS + ["decisions: given vs taken", "claims: no check vs wasn't notified"]
    got = {b: [(paths[b]["layers"][n]["n"], kappa_text(paths[b]["layers"][n]["kappa"])) for n in layers] for b in s2.BACKENDS}
    report("PASS" if got == {"api": [(336, "0.73"), (188, "0.78"), (348, "0.72"), (188, "0.66"), (158, "0.00")],
                             "claude-code": [(342, "0.71"), (191, "0.77"), (355, "0.73"), (191, "0.63"), (157, "0.00")]}
           else "FAIL", "A5", "The second test's results table: units and κ for each code, on each path",
           "; ".join(f"{b}: " + ", ".join(f"{n} at {k}" for n, k in got[b]) for b in s2.BACKENDS))
    agree = sorted(round(100 * paths[b]["layers"][p]["agreement"]) for b in s2.BACKENDS for p in s2.PRIMARY)
    split = [round(100 * paths[b]["layers"][layers[-1]]["agreement"]) for b in s2.BACKENDS]
    report("PASS" if (agree[0], agree[-1]) == (84, 87) and set(split) == {97} else "FAIL", "A5",
           "Agreement of 84% to 87% on the primary codes; 97% on no check vs wasn't notified, at κ of 0",
           f"primary {agree[0]}% to {agree[-1]}%; no check vs wasn't notified " + ", ".join(f"{a}%" for a in split))
    costs = [json.loads(f.read_text())["cost_usd"] for f in sorted((s2.HERE / "reader-runs" / "api").glob("*/reader-run.json"))]
    report("SAVED" if len(costs) == 12 and f"{sum(costs):.2f}" == "19.37" else "FAIL", "A5",
           "$19.37 on the API for the second test's API pass",
           f"{len(costs)} saved run costs, ${sum(costs):.2f} in all. Rerunning needs an API key")
    for p in s2._clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)


def first_test():
    s1 = load(REPO / "tests" / "scripted" / "score.py", "score1")
    saved = s1.OUT
    results = {}
    for name, folder in (("Claude", saved), ("OpenAI's model", saved / "openai-gpt-5.3-codex"),
                         ("rerun 2", saved / "rep2"), ("rerun 3", saved / "rep3")):
        out = TMP / f"first-test-{len(results)}"
        for run in s1.RUNS:
            shutil.copytree(folder / run, out / run)
        s1.OUT = out
        quiet(s1.score)
        results[name] = json.loads((out / "score.json").read_text())
    for p in s1._clones.values():
        shutil.rmtree(p.parent, ignore_errors=True)
    primary = ["decisions: kept vs handed over", "judgment certification", "claims: certification"]
    claude, openai = (results[n] for n in ("Claude", "OpenAI's model"))
    report("PASS" if claude["validated"] else "FAIL", "§3", "The first test: the reader cleared the bar of 0.6",
           "κ " + ", ".join(f"{claude['layers'][p]['kappa']:.2f}" for p in primary))
    ks = [openai["layers"][p]["kappa"] for p in primary]
    report("PASS" if openai["validated"] and (f"{min(ks):.2f}", f"{max(ks):.2f}") == ("0.66", "0.79") else "FAIL",
           "§5", "OpenAI's model read the first test and cleared the same bar, at κ of 0.66 to 0.79",
           "κ " + ", ".join(f"{k:.2f}" for k in ks))
    layers = primary + ["decisions: given vs taken"]
    got = [(claude["layers"][n]["n"], round(100 * claude["layers"][n]["agreement"]), kappa_text(claude["layers"][n]["kappa"]))
           for n in layers]
    report("PASS" if got == [(83, 86, "0.71"), (37, 78, "0.70"), (92, 85, "0.75"), (37, 86, "0.47")] else "FAIL", "A5",
           "The first test's results table: units, agreement, and κ for each code",
           "; ".join(f"{n} units, {a}%, κ {k}" for n, a, k in got))
    found, total = (sum(v[k] for v in claude["listing"].values()) for k in ("found", "key units"))
    report("PASS" if round(100 * found / total) == 85 else "FAIL", "A5", "The reader found 85% of the first test's key",
           f"{found} of {total} ({round(100 * found / total)}%)")
    runs = [results[n] for n in ("Claude", "rerun 2", "rerun 3", "OpenAI's model")]
    table = [[kappa_text(r["layers"][p]["kappa"]) for r in runs] for p in primary]
    report("PASS" if table == [["0.71", "0.76", "0.81", "0.66"], ["0.70", "0.78", "0.78", "0.68"], ["0.75", "0.82", "0.77", "0.79"]]
           and all(r["validated"] for r in runs) else "FAIL", "A5",
           "Claude's three runs and gpt-5.3-codex on the first test, κ on each primary code; all clear the bar",
           "; ".join(f"{name}: Claude {', '.join(row[:3])}, gpt-5.3-codex {row[3]}"
                     for name, row in zip(("kept vs handed over", "how a handed-over call ended", "how a claim was checked"), table)))
    return s1


def demonstrations():
    counts = {p: len(re.findall(r"^\| *[A-Z]\d+ *\|", f.read_text(), re.M)) for p, f in PLANTS.items()}
    present = [r for r in kept_runs() if (DEMOS / r / "disclosure").is_dir() and (DEMOS / f"{r}.bundle").is_file()]
    report("PASS" if len(present) == 12 and set(counts.values()) == {7} else "FAIL", "§3",
           "Three papers, four authors each, seven planted errors per paper",
           f"{len(present)} runs with a record and a disclosure; plants: "
           + ", ".join(f"{p} {n}" for p, n in counts.items()))
    render = load(REPO / "plugin" / "warrant" / "scripts" / "render.py", "render")
    lines, misplaced = [], []
    for paper, runs in KEPT.items():
        for r in runs:
            d = DEMOS / r / "disclosure"
            _, decisions, _ = render.tally(json.loads((d / "units.json").read_text())["units"],
                                           json.loads((d / "codes.json").read_text()))
            made = sum(x["discretion"] == "kept" for x in decisions)
            handed = [x for x in decisions if x["discretion"] in ("given", "taken")]
            warranted = sum(x["certification"] in WARRANTED for x in handed)
            landed = (f"{'low' if 2 * made > len(decisions) else 'high'}-"
                      f"{'high' if 2 * warranted > len(handed) else 'low'}")
            meant = re.search(r"(low|high)-(low|high)-2026", r).group(0)[:-5]
            if landed != meant:
                misplaced.append(f"{paper} {meant} landed {landed}")
            lines.append(f"{paper} {meant}: made {made} of {len(decisions)}, warranted {warranted} of {len(handed)}")
    report("FAIL" if misplaced else "PASS", "§3",
           "Every author landed in its cell (low delegation: made more than half the calls; "
           "high warrant: changed or accepted more than half of those handed over)",
           ("; ".join(misplaced) if misplaced else "12 of 12 in their cells") + "\n"
           + "\n".join(f"{'':19}{line}" for line in lines))
    unchecked = {"high-low": ("no check", []), "low-low": ("tool checked, you didn't see the result", [])}
    for r in kept_runs():
        meant = re.search(r"(low|high)-(low|high)-2026", r).group(0)[:-5]
        if meant in unchecked:
            d = DEMOS / r / "disclosure"
            _, _, claims = render.tally(json.loads((d / "units.json").read_text())["units"],
                                        json.loads((d / "codes.json").read_text()))
            code, shares = unchecked[meant]
            shares.append(round(100 * sum(c["certification"] == code for c in claims) / len(claims)))
    hl, ll = (sorted(unchecked[c][1]) for c in ("high-low", "low-low"))
    report("PASS" if (hl[0], hl[-1], ll[0], ll[-1]) == (54, 84, 33, 72) else "FAIL", "A6",
           "The high delegation, low warrant authors left 54% to 84% of claims with no check; for the low delegation, "
           "low warrant authors, 33% to 72% were checked by Claude but never seen",
           f"high delegation, low warrant: {', '.join(f'{x}%' for x in unchecked['high-low'][1])} with no check; "
           f"low delegation, low warrant: {', '.join(f'{x}%' for x in unchecked['low-low'][1])} checked but not seen")
    differ = []
    for r in kept_runs():
        src, out = DEMOS / r / "disclosure", TMP / "redraw" / r
        shutil.copytree(src, out)
        quiet(render.redraw, out)
        differ += [f"{r}/{f}" for f in ("disclosure.md", "disclosure.html")
                   if (out / f).read_bytes() != (src / f).read_bytes()]
    report("FAIL" if differ else "PASS", "Figure 2",
           "Each demonstration's disclosure follows from its saved codes (Figure 2 shows two of them)",
           ", ".join(differ) + " differ when redrawn" if differ else "all 12 redraw identically")


def saved_results():
    text = (PAPERS / "RESULTS.md").read_text()
    totals = {m.group(1): [int(x) for x in m.group(2, 3, 4, 5)] for m in re.finditer(
        r"^\| \*\*(.+?), all papers\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|$", text, re.M)}
    stayed = {cell: t[2] for cell, t in totals.items()}
    hl = totals.get("High delegation, low warrant", [None] * 4)
    ok = (stayed.get("Low delegation, low warrant") == 6 and sum(stayed.values()) == 6 and hl[1] == 21 and hl[2] == 0)
    report("SAVED" if ok else "FAIL", "§3",
           "Six planted errors stayed, all with the low delegation, low warrant authors; "
           "the high delegation, low warrant papers were free of all 21",
           "stayed: " + ", ".join(f"{c} {n}" for c, n in stayed.items())
           + f"; high delegation, low warrant fixed unasked {hl[1]}. A Claude subagent's reading, not recomputed")
    report("SAVED" if totals == {"Low delegation, high warrant": [12, 4, 0, 5], "High delegation, low warrant": [0, 21, 0, 0],
                                 "High delegation, high warrant": [10, 9, 0, 2], "Low delegation, low warrant": [3, 11, 6, 1]}
           else "FAIL", "A6", "The planted errors' fates by author, all three papers (caught, fixed unasked, stayed, left out)",
           "; ".join(f"{c}: {', '.join(map(str, t))}" for c, t in totals.items()) + ". A Claude subagent's reading, not recomputed")
    section = text.split("## What ran", 1)[1].split("\n## ", 1)[0]
    costs = [float(c) for c in re.findall(r"\| \$(\d+\.\d\d) \|$", section, re.M)]
    ok = len(costs) == 12 and int(min(costs)) == 3 and round(max(costs)) == 16
    report("SAVED" if ok else "FAIL", "§3", "$3 to $16 to read a full-length paper through the API",
           f"{len(costs)} saved costs, ${min(costs):.2f} to ${max(costs):.2f}. Rerunning needs an API key")


def checklists():
    """A3's table: the checklist items under the spine and each pack."""
    counts = {}
    for kind, name in ((0, "judgment-decisions.md"), (1, "checkable-claims.md")):
        part = None
        for line in (REPO / "plugin" / "warrant" / "checklists" / name).read_text().splitlines():
            if line.startswith("## "):
                part = line[3:].split()[0].rstrip(":")
            elif part and re.match(r"\| *[A-Z]+\d+ *\|", line):
                counts.setdefault(part, [0, 0])[kind] += 1
    report("PASS" if counts == {"Spine": [9, 5], "Quantitative": [24, 6], "Experiments": [11, 5], "Qualitative": [17, 5],
                                "Theory": [9, 3], "Tool": [15, 5]} else "FAIL", "A3",
           "The checklists: 85 kinds of judgment call and 29 of verifiable claim, by spine and pack",
           ", ".join(f"{p} {a} and {b}" for p, (a, b) in counts.items())
           + f"; {sum(a for a, _ in counts.values())} and {sum(b for _, b in counts.values())} in all")


def chains(s1):
    """Clone each run's bundle with its snapshots and verify every log in it."""
    s2 = sys.modules.get("score2") or load(REPO / "tests" / "scripted2" / "score.py", "score2")
    bundles = ([DEMOS / f"{r}.bundle" for r in kept_runs()] + sorted(s2.runs().values())
               + [s1.HERE / "runs" / f"{b}.bundle" for b in s1.RUNS.values()])
    verify = REPO / "plugin" / "warrant" / "scripts" / "verify_log.py"
    # Texts the review copy withholds, by design (release/withheld.json): at most that many may be missing.
    declared = REPO / "release" / "withheld.json"
    declared = json.loads(declared.read_text())["texts"] if declared.is_file() else {}
    broken, events, sidecars, snapshots, withheld = [], 0, 0, 0, 0
    for i, bundle in enumerate(bundles):
        clone = TMP / "chains" / str(i)
        try:
            git("clone", "-q", str(bundle), str(clone))
            git("fetch", "-q", str(bundle), "refs/provenance/*:refs/provenance/*", cwd=clone)
        except RuntimeError as e:
            broken.append(f"{bundle.name}: could not clone ({e})")
            continue
        logs = sorted((clone / "provenance" / "log").glob("*/events.jsonl"))
        if not logs:
            broken.append(f"{bundle.name}: no log")
        for log in logs:
            r = subprocess.run([sys.executable, str(verify), str(log)], capture_output=True, text=True)
            first = re.search(r"^(OK|BROKEN)\s+(\d+) events", r.stdout, re.M)
            side = re.search(r"sidecars: (\d+) checked, (\d+) withheld", r.stdout)
            snap = re.search(r"snapshots: (\d+) present, (\d+) withheld", r.stdout)
            allowed = len(declared.get(bundle.relative_to(REPO).as_posix(), []))
            if r.returncode or not first or not side or int(side.group(2)) > allowed or (snap and snap.group(2) != "0"):
                broken.append(f"{bundle.name}: " + " ".join(r.stdout.split()[-12:] if r.stdout.strip() else [r.stderr[-200:]]))
            else:
                events += int(first.group(2))
                sidecars += int(side.group(1))
                withheld += int(side.group(2))
                snapshots += int(snap.group(1)) if snap else 0
        shutil.rmtree(clone, ignore_errors=True)
    report("FAIL" if broken else "PASS", "§3",
           "Each run's record is intact: the twelve demonstrations and both tests' runs",
           "; ".join(broken) if broken else
           f"{len(bundles)} records verify: {events:,} events, {sidecars:,} text files, {snapshots:,} snapshots, "
           + (f"{withheld} text withheld, as release/withheld.json declares" if withheld else "none missing"))


def main():
    print(f"Checking the proposal's numbers in {REPO}\n", flush=True)
    try:
        second_test()
        s1 = first_test()
        demonstrations()
        checklists()
        saved_results()
        chains(s1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed, {tally['SAVED']} confirmed from saved results.")
    return 1 if tally["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
