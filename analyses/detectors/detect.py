"""Two AI-text detectors, Pangram and GPTZero, on four versions of one published
article and the twelve demonstration papers, for the proposal
(DECISIONS.md, Oct 12, 13 and 16; the author, Oct 19: the twelve demonstrations
replace the long demonstration's first round).

    python3 detect.py texts                 each text's words and fingerprint (no calls)
    python3 detect.py run pangram|gptzero   score each text not yet scored
    python3 detect.py table                 the results, as a table

Each detector reads a paper's body text:
  article as analyze.py reads it (the introduction to the references, without
         the title, abstract, footnotes, tables, or acknowledgment), with its
         paragraphs kept; the word counts match analyze.py's exactly.
  demos  paper.md at the attested commit of each kept run's bundle, from the
         first section after the abstract to the references, data statement,
         or appendix, without tables, figures, HTML comments, or Markdown's
         marks.
The texts stay outside the repository (the article's texts are not in the review copy). results/ keeps each detector's response with the text taken out,
plus the text's word count and fingerprint, so a rerun can be checked
against it. Keys come from the Keychain and are never printed.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analyses" / "article-copyediting"))

ARTICLE = None  # the article's texts are not in the review copy
ARTICLE_TEXTS = [  # id, label, source
    ("article-accepted", "Accepted manuscript", None),
    ("article-journal-edit", "The journal's copy edit",
     None),
    ("article-claude-brief", "Claude's copy edit, journal brief", None),
    ("article-claude-plain", "Claude's copy edit, \"Copy edit this.\"", None),
]
RUNS = REPO / "tests" / "longdemo" / "runs"
KEPT = {  # (paper, author): the kept run (tests/longdemo/papers/RESULTS.md)
    ("archival", "low-high"): "low-high-2026-10-17-2006",
    ("archival", "high-low"): "high-low-2026-10-18-2005",
    ("archival", "high-high"): "high-high-2026-10-17-0857",
    ("archival", "low-low"): "low-low-2026-10-18-2036",
    ("experiment", "low-high"): "experiment-low-high-2026-10-17-0841",
    ("experiment", "high-low"): "experiment-high-low-2026-10-17-1043",
    ("experiment", "high-high"): "experiment-high-high-2026-10-17-0933",
    ("experiment", "low-low"): "experiment-low-low-2026-10-17-1022",
    ("qualitative", "low-high"): "qualitative-low-high-2026-10-17-1528",
    ("qualitative", "high-low"): "qualitative-high-low-2026-10-17-1028",
    ("qualitative", "high-high"): "qualitative-high-high-2026-10-17-0841",
    ("qualitative", "low-low"): "qualitative-low-low-2026-10-17-1528",
}
AUTHORS = {"low-high": "Low delegation, high warrant", "high-low": "High delegation, low warrant",
           "high-high": "High delegation, high warrant", "low-low": "Low delegation, low warrant"}
END = re.compile(r"(references|data and code|data statement|appendix|acknowledg|supplement|interview transcripts)", re.I)
STRIP = {"text", "inputText", "sentence"}  # response fields that carry the text itself


def article_body(tid, source):
    """The body text with its paragraphs, cut where analyze.body_only cuts the words."""
    import analyze, copyedit  # only here: `table` reads the saved results and needs neither
    raw = source.read_text() if source.suffix == ".txt" else copyedit.manuscript(source)
    if source.suffix == ".txt":
        raw = copyedit.manuscript_only(raw)
    lines = [l.strip() for l in raw.splitlines()]
    k = next((i for i, l in enumerate(lines) if l.startswith("Keywords:")), None)
    if k is not None:  # the final: title, author, abstract, keywords, then the first section
        start = next(i for i in range(k + 1, len(lines)) if lines[i].startswith("Institutions"))
    else:
        start = next(i for i, l in enumerate(lines) if l.upper() == "INTRODUCTION") + 1
    end = next(i for i in range(start, len(lines))
               if lines[i] == "REFERENCES" or lines[i].startswith("I thank Martin Kilduff"))
    text = "\n\n".join(l for l in lines[start:end] if l)
    b, _ = analyze.split_refs(analyze.words(raw))
    expected = len(analyze.body_only(b))
    if len(analyze.words(text)) != expected:
        sys.exit(f"{tid}: {len(analyze.words(text))} words, but analyze.py reads {expected}")
    return text


def demo_body(md):
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.splitlines()
    heads = [(i, re.sub(r"^#+\s*(?:\d+(?:\.\d+)*\.?\s*)?", "", l).strip())
             for i, l in enumerate(lines) if re.match(r"^#{1,6}\s", l)]
    if heads and heads[0][0] < 3 and not re.match(r"(introduction|abstract)", heads[0][1], re.I) \
            and not re.match(r"^#+\s*1\.", lines[heads[0][0]]):
        heads = heads[1:]  # the title
    k = next((n for n, (_, h) in enumerate(heads) if h.lower() == "abstract"), None)
    start = heads[k + 1][0] if k is not None else heads[0][0]
    end = next((i for i, h in heads if i > start and END.match(h)), len(lines))
    out = []
    for l in lines[start:end]:
        if l.lstrip().startswith("|") or l.lstrip().startswith("!["):
            continue
        l = re.sub(r"^#+\s*", "", l)
        l = re.sub(r"^\s*>\s?", "", l)
        l = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", l)
        l = re.sub(r"\*\*|__|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)", "", l)
        out.append(l.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def texts():
    """[(id, group, label, text)] for the sixteen texts."""
    out = [(tid, "Article", label, article_body(tid, src)) for tid, label, src in ARTICLE_TEXTS]
    with tempfile.TemporaryDirectory() as tmp:
        for (paper, author), run in KEPT.items():
            clone = Path(tmp) / run
            subprocess.run(["git", "clone", "-q", str(RUNS / f"{run}.bundle"), str(clone)], check=True)
            md = subprocess.run(["git", "-C", str(clone), "show", "HEAD:paper.md"], capture_output=True,
                                text=True, check=True).stdout
            out.append((f"{paper}-{author}", paper, AUTHORS[author], demo_body(md)))
    return out


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


def key(name):
    return subprocess.run(["security", "find-generic-password", "-s", f"warranted-delegation-{name}", "-w"],
                          capture_output=True, text=True, check=True).stdout.strip()


def call(method, url, headers, body=None):
    """curl, since GPTZero's firewall turns away Python's own requests; the key goes in on stdin's config, not argv."""
    cfg = "".join(f'header = "{k}: {v}"\n' for k, v in headers.items())
    args = ["curl", "-s", "-m", "300", "-X", method, "-w", "\n%{http_code}", "-K", "-", url]
    if body is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(body, tmp)
        tmp.close()
        args[-1:-1] = ["--data-binary", f"@{tmp.name}"]
    try:
        out = subprocess.run(args, input=cfg, capture_output=True, text=True).stdout
    finally:
        if body is not None:
            Path(tmp.name).unlink()
    payload, code = out.rsplit("\n", 1)
    if code != "200":
        raise RuntimeError(f"HTTP {code}: {payload[:300]}")
    return json.loads(payload)


def pangram(text):
    h = {"x-api-key": key("pangram"), "Content-Type": "application/json"}
    task = call("POST", "https://text.external-api.pangram.com/task", h, {"text": text, "model": "pangram-4"})
    for _ in range(240):
        time.sleep(5)
        r = call("GET", f"https://text.external-api.pangram.com/task/{task['task_id']}", h)
        if r.get("stage") in ("STAGE_SUCCESS", "STAGE_FAILED"):
            return r
    raise RuntimeError(f"Pangram task {task['task_id']} still running after 20 minutes")


def gptzero(text):
    h = {"x-api-key": key("gptzero"), "Content-Type": "application/json", "Accept": "application/json"}
    return call("POST", "https://api.gptzero.me/v2/predict/text", h, {"document": text})


def stripped(x):
    if isinstance(x, dict):
        return {k: (f"<{len(v.split())} words, taken out>" if k in STRIP and isinstance(v, str) else stripped(v))
                for k, v in x.items()}
    if isinstance(x, list):
        return [stripped(v) for v in x]
    return x


def run(detector):
    fn = {"pangram": pangram, "gptzero": gptzero}[detector]
    out = HERE / "results" / detector
    out.mkdir(parents=True, exist_ok=True)
    for tid, group, label, text in texts():
        path = out / f"{tid}.json"
        if path.exists():
            print(f"{tid}: already scored")
            continue
        words = len(text.split())
        print(f"{tid}: {words} words ...", flush=True)
        r = fn(text)
        meta = {"id": tid, "group": group, "label": label, "words": words, "sha256": fingerprint(text),
                "detector": detector, "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        path.write_text(json.dumps({"meta": meta, "response": stripped(r)}, indent=1) + "\n")
        print(f"  saved {path.relative_to(REPO)}", flush=True)


def table():
    """The saved results, with no texts and no calls: group, label, and words come from each result's meta."""
    rows = []
    for tid in [t[0] for t in ARTICLE_TEXTS] + [f"{paper}-{author}" for paper, author in KEPT]:
        p, g = (HERE / "results" / d / f"{tid}.json" for d in ("pangram", "gptzero"))
        p, g = (json.loads(x.read_text()) if x.exists() else {} for x in (p, g))
        meta = p.get("meta") or g.get("meta") or {}
        group, label, words = meta.get("group", ""), meta.get("label", tid), meta.get("words")
        p = p.get("response", {})
        g = (g.get("response", {}).get("documents") or [{}])[0]
        cp = g.get("class_probabilities", {})
        pct = lambda v: "" if v is None else f"{100 * v:.0f}%"
        rows.append(f"| {group} | {label} | {f'{words:,}' if words else ''} | {p.get('headline', '')} | "
                    f"{pct(p.get('fraction_ai'))} | {pct(p.get('fraction_ai_assisted'))} | {pct(p.get('fraction_human'))} | "
                    f"{g.get('predicted_class', '')} | {pct(cp.get('ai'))} | {pct(cp.get('mixed'))} | {pct(cp.get('human'))} |")
    print("| Paper | Version or author | Words | Pangram | AI | AI-assisted | Human | GPTZero | AI | Mixed | Human |")
    print("|:-|:-|-:|:-|-:|-:|-:|:-|-:|-:|-:|")
    print("\n".join(rows))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["texts"]:
        total = 0
        for tid, group, label, text in texts():
            n = len(text.split())
            total += n
            print(f"{tid:26} {n:6,} words  {fingerprint(text)[:12]}")
        print(f"{'all':26} {total:6,} words")
    elif len(a) == 2 and a[0] == "run" and a[1] in ("pangram", "gptzero"):
        run(a[1])
    elif a == ["table"]:
        table()
    else:
        sys.exit(__doc__)
