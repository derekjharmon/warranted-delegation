"""Which reported numbers trace to a saved output or a recorded run.

A mechanical step, no model (DECISIONS.md, Oct 7): authors aren't required to
produce every result with a saved script, so the disclosure says how many of
the manuscript's numbers can be found in the project's saved results or in
what the record's commands printed. It reports where numbers came from, not
whether anyone checked them; that stays with the claims row.

    python3 trace_numbers.py PROJECT OUT_DIR [--map MAP]

adds the result to OUT_DIR/reader-run.json and redraws the disclosure there,
so it can be applied to a run made before this step existed.

Rules. A number counts if it is distinctive: it has decimals, or three or
more digits, and it is not a year (1900-2099) or part of an identifier (a
DOI, an arXiv ID, a version). It traces if the same number appears in a
saved result or a recorded command's output, rounded to the number of
decimals the manuscript prints. Saved results are the map's results slot
(or folders named like output/ and results/); data and code are not
searched, since numbers there would match by chance.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT_DIRS = ("output", "outputs", "results", "tables", "figures", "out")
TEXT = {".md", ".txt", ".csv", ".tsv", ".tex", ".log", ".json", ".html", ".smcl", ".out", ".qmd", ".rmd"}
# A number not glued to letters, slashes, colons, or another number's digits.
NUMBER = re.compile(r"(?<![\w.:/])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{3,})(?![\w/]|\.\d)")
TOKEN = re.compile(r"\d+(?:\.\d+)?")
# Formats that are never text, whatever their first bytes look like.
BINARY = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".doc", ".docx", ".pptx", ".xlsx", ".xls",
          ".zip", ".gz", ".dta", ".sav", ".rds", ".rdata", ".parquet", ".feather", ".pkl", ".npy", ".h5"}


def is_binary(path, raw=None):
    """Not text: a binary format, a PDF by its header, a zero byte, or control
    characters in the first 4 KB. Shared with the reader, which shows such a
    file by name only, so this line skips what the model never saw
    (DECISIONS.md, Oct 16: a PDF passed the old zero-byte test)."""
    path = Path(path)
    if path.suffix.lower() in BINARY:
        return True
    if raw is None:
        with open(path, "rb") as fh:
            raw = fh.read(4096)
    head = raw[:4096]
    control = sum(b < 9 or 13 < b < 32 or b == 127 for b in head)
    return head.startswith(b"%PDF-") or b"\0" in head or control > len(head) // 100


def plain(n):
    return n.replace(",", "")


def distinctive(n):
    m = plain(n)
    if "." in m:
        return True
    return len(m) >= 3 and not (len(m) == 4 and 1900 <= int(m) <= 2099)


def numbers_in(text):
    return [n for n in NUMBER.findall(text) if distinctive(n)]


def haystack(texts):
    """Every number in the searched texts, and each decimal rounded to 1-6 places."""
    exact, rounded = set(), set()
    for t in texts:
        t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)
        for tok in TOKEN.findall(t):
            exact.add(tok)
            if "." in tok:
                v = float(tok)
                rounded.update(f"{v:.{d}f}" for d in range(1, 7))
            exact.add(tok.lstrip("0") or "0")
    return exact, rounded


def traces(n, exact, rounded):
    m = plain(n)
    return m in exact or ("." in m and m in rounded) or (m.startswith("0.") and m[1:] in exact)


def searched_texts(project, work_map, files):
    """The saved results, and what the record's commands printed."""
    project = Path(project)
    slots = work_map or {}
    results = [p.strip() for p in slots.get("results", "").split(",") if p.strip() and p.strip().lower() != "none"]
    if not results:
        results = [d + "/" for d in RESULT_DIRS if (project / d).is_dir()]
    texts = []
    for r in results:
        base = project / r.rstrip("/")
        paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []
        for p in paths:
            if p.suffix.lower() in TEXT and p.stat().st_size < 20_000_000:
                texts.append(p.read_text(errors="replace"))
    log_dir = project / "provenance" / "log"
    for log in sorted(log_dir.glob("*/events.jsonl")):
        for line in log.read_text().splitlines():
            e = json.loads(line) if line.strip() else {}
            sha = e.get("output_sha256") if e.get("event") == "PostToolUse" else None
            side = log_dir / "text" / f"{sha}.txt" if sha else None
            if side and side.exists():
                texts.append(side.read_text(errors="replace"))
    return texts


def manuscript_files(project, work_map, files):
    slots = work_map or {}
    named = [p.strip() for p in slots.get("manuscript", "").split(",") if p.strip() and p.strip().lower() != "none"]
    if named:
        return [f for f in files if any(f == n or (n.endswith("/") and f.startswith(n)) for n in named)
                and (project / f).is_file() and not is_binary(project / f)]
    return [f for f in files if "/" not in f and Path(f).suffix.lower() in {".md", ".tex", ".qmd", ".rmd", ".txt"}]


def summarize(project, work_map, files, units):
    project = Path(project)
    exact, rounded = haystack(searched_texts(project, work_map, files))
    found, missing = [], []
    for f in manuscript_files(project, work_map, files):
        text = (project / f).read_text(errors="replace")
        # The reference list holds identifiers and page ranges, not results.
        text = re.split(r"(?im)^#+\s*references\b", text)[0]
        for n in numbers_in(text):
            (found if traces(n, exact, rounded) else missing).append(n)
    per_unit = {}
    for u in units:
        if u.get("kind") != "claim":
            continue
        quoted = " ".join(a.get("quote", "") for a in u.get("anchors", []))
        gone = sorted({n for n in numbers_in(quoted) if not traces(n, exact, rounded)})
        if gone:
            per_unit[u["id"]] = gone
    return {"traced": len(found), "total": len(found) + len(missing),
            "untraced": sorted(set(missing), key=missing.index), "per_unit": per_unit}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--map", type=Path)
    args = ap.parse_args()
    sys.path.insert(0, str(HERE))
    import render
    u = json.loads((args.out / "units.json").read_text())
    run_path = args.out / "reader-run.json"
    run = json.loads(run_path.read_text())
    work_map = run.get("work_map")
    if args.map:
        import disclose
        work_map = disclose.read_map(args.map)
        run["work_map"] = work_map
    run["numbers"] = summarize(args.project, work_map, u["files"], u["units"])
    run_path.write_text(json.dumps(run, indent=1) + "\n")
    render.redraw(args.out)
    n = run["numbers"]
    print(f"{n['traced']} of {n['total']} reported numbers trace; not traced: {', '.join(n['untraced']) or 'none'}")


if __name__ == "__main__":
    main()
