"""/warrant:trail: the paper trail for a disclosure (DECISIONS.md, Oct 8 and
Oct 12).

    /warrant:trail                     the latest disclosure
    /warrant:trail 2026-10-16-100336   that run
    trail.py RUN_DIR PROJECT [--note TEXT]
                                       draw it; what Claude runs, and scripts

Draws trail.html beside the disclosure: the manuscript, with each unit the
reader found marked in the shade the disclosure gives it; on click, the words
it rests on, the reader's basis for its code, and the turns that produced it;
and the timeline of turns. A sentence that restates a call made elsewhere is
marked apart and points to where the call is made (Oct 12). No model calls
and no new judgment: only the reader's output (units.json, codes.json,
reader-run.json), the record as the reader saw it (transcript.txt), the
manuscript as it was read (saved with the run since Oct 16; before that, the
project's copy), and the project's snapshots, to follow copied text back to
whoever first saved it. Optional, local, and not part of the disclosure or
its fingerprint. Home folders and the user name are shortened, as ~ and user.

Run by the plugin's hook when the person types /warrant:trail: the hook
picks the run and hands Claude the command to draw it, so the person sees it
happen. Headless (claude -p), the hook draws it itself.
"""
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reader  # noqa: E402  the record, and who made each snapshot
import render  # noqa: E402  the disclosure's own labels, stages, and shades

OUT = Path("disclosure")
MANUSCRIPT = "manuscript"  # in a run's folder: the manuscript as it was read
TEXT = {".md", ".txt", ".qmd", ".rmd", ".tex"}
TIMELINE_TURNS = 100  # past this, the timeline groups turns by date (trail.html's TURN_MAX)
HOME = str(Path.home())

HEAD = re.compile(r"^T(\d+) · (AUTHOR'S PROMPT|CLAUDE'S REPLY):\s*$")
ATTEST = re.compile(r"^T(\d+) · ATTEST \(the author's signed save\): ?(.*)$")
FIRST = re.compile(r"^T(\d+) · The author's first save, before the record began\. Files: ?(.*)$")
ASIDE = re.compile(r"^T(\d+) · SET ASIDE: (.*)$")
INSTRUCTIONS = re.compile(r"^\[Instructions in force from T(\d+),")
BETWEEN = re.compile(r"^\[Between T(\d+) and T(\d+), the author changed files by hand:\]\s*$")
SKILL = re.compile(r"^   (The author typed the command|Claude used the skill) (.*)$")
TOOL = re.compile(r"^   tool (\S+): ?(.*)$")


# Markdown, without depending on anything outside Python

def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<em>\1</em>", s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: figure(m.group(2), m.group(1)), s)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)


def figure(src, caption):
    """An image, shown by its caption: the trail is one file, without the figure itself."""
    return f'<span class="figcap"><span class="note">[Figure, not shown here: {src}]</span> {caption}</span>'


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


ITEM = re.compile(r"\s*([-*+]|\d+[.)])\s+(.*)")


def markdown(text):
    """Headings, paragraphs, lists, tables, quotes, and code: enough to draw a
    paper and Claude's replies. Pandoc draws the manuscript when it's there."""
    out, para, lines, i = [], [], text.split("\n"), 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            flush()
            j, code = i + 1, []
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                code.append(lines[j])
                j += 1
            out.append("<pre><code>" + esc("\n".join(code)) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            flush()
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\s*\|?[\s:|-]*-[\s:|-]*", lines[i + 1]):
            flush()
            head, rows, i = cells(line), [], i + 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table>")
            continue
        m = ITEM.match(line)
        if m:
            flush()
            tag, items = ("ol" if m.group(1)[0].isdigit() else "ul"), []
            while i < len(lines) and lines[i].strip():
                mm = ITEM.match(lines[i])
                if mm:
                    items.append(mm.group(2))
                elif items:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if not line.strip():
            flush()
        else:
            para.append(re.sub(r"^\s*>\s?", "", line).strip())
        i += 1
    flush()
    return "\n".join(out)


FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def front_matter(text):
    """A markdown file's title block (YAML front matter), drawn as a heading,
    and the rest of the text."""
    m = FRONT.match(text)
    if not m:
        return "", text
    fields = dict(re.findall(r'(?m)^(\w+):\s*"?(.*?)"?\s*$', m.group(1)))
    head = (f"<h1>{esc(fields['title'])}</h1>" if fields.get("title") else "") + "".join(
        f"<p class='byline'>{esc(fields[k])}</p>" for k in ("subtitle", "author", "date") if fields.get(k))
    return head, text[m.end():]


def manuscript_html(path, text):
    """The manuscript as a page: pandoc where it's installed, else markdown()."""
    head, text = front_matter(text) if path.suffix.lower() in (".md", ".qmd", ".rmd") else ("", text)
    return head + body_html(path, text)


def body_html(path, text):
    if shutil.which("pandoc"):
        fmt = "docx" if path.suffix.lower() == ".docx" else "gfm-raw_html"
        r = subprocess.run(["pandoc", "-f", fmt, "-t", "html", "--wrap=none", *([str(path)] if fmt == "docx" else [])],
                           input=None if fmt == "docx" else text, capture_output=True, text=True)
        if r.returncode == 0:
            return re.sub(r'<img src="([^"]*)" alt="([^"]*)"[^>]*>', lambda m: figure(m.group(1), m.group(2)), r.stdout)
    if path.suffix.lower() in (".md", ".qmd", ".rmd"):
        return markdown(text)
    return "<pre>" + esc(text) + "</pre>"


# The record as the reader saw it

def private(text):
    return text.replace(HOME, "~").replace(Path.home().name, "user")


def parse_transcript(text):
    """Each turn of transcript.txt: its kind, the prompt, skills, tools,
    reply, the instructions newly in force, and hand edits before it."""
    turns, cur, part, between, instr = {}, None, None, None, None
    turn = lambda n: turns.setdefault(n, {"kind": "prompt", "prompt": [], "tools": [], "reply": [], "skills": [],
                                          "instructions": []})
    for line in private(text).splitlines():
        m, b = HEAD.match(line), BETWEEN.match(line)
        a, f, s, i = ATTEST.match(line), FIRST.match(line), ASIDE.match(line), INSTRUCTIONS.match(line)
        if m:
            cur = turn(int(m.group(1)))
            part = "prompt" if m.group(2).startswith("AUTHOR") else "reply"
        elif a or f or s:
            x = a or f or s
            cur = turn(int(x.group(1)))
            cur["kind"] = "attest" if a else "first" if f else "aside"
            cur["prompt"] = [x.group(2) if a or s else "The author's first save, before the record began. Files: "
                             + x.group(2)]
            part = "prompt" if a else None
        elif i:
            instr, part = turn(int(i.group(1)))["instructions"], "instructions"
        elif b:
            between = {"diff": []}
            turn(int(b.group(2)))["hand"] = between
            part = "between"
        elif part == "between":
            between["diff"].append(line)
        elif part == "instructions":
            instr.append(line)
        elif cur is not None and part in ("prompt", "tools", "skill") and SKILL.match(line):
            cur["skills"].append(line.strip().split(". Its text:")[0].replace("Claude used the skill", "The AI used the skill"))
            part = "skill"
        elif cur is not None and part in ("prompt", "tools", "skill") and TOOL.match(line):
            t = TOOL.match(line)
            cur["tools"].append(f"{t.group(1)}: {t.group(2)[:160]}")
            part = "tools"
        elif part in ("tools", "skill"):
            continue  # tool output, and a skill's text
        elif part in ("prompt", "reply") and cur is not None:
            cur[part].append(line)
    out = {}
    for n, t in sorted(turns.items()):
        hand = t.get("hand")
        diff = "\n".join(hand["diff"]).strip() if hand else ""
        reply = "\n".join(t["reply"]).strip()
        out[n] = {"kind": t["kind"], "prompt": "\n".join(t["prompt"]).strip(), "tools": t["tools"],
                  "skills": t["skills"], "instructions": "\n".join(t["instructions"]).strip()[:12000],
                  "reply": markdown(reply) if reply else "",
                  "hand": {"files": re.findall(r"^diff --git a/(\S+)", diff, re.M),
                           "diff": diff[:6000] + ("\n…" if len(diff) > 6000 else "")} if hand else None}
    return out


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, d):
        self.parts.append(d)


STRIP = re.compile(r"[\s*_`|\\#]")


def norm(s):
    return STRIP.sub("", html.unescape(s))


def plain(quote):
    """A quote from the markdown source as the drawn page shows it: without
    list markers, title-block keys, or the syntax of links and images."""
    q = re.sub(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+", "", quote)
    q = re.sub(r"(?m)^\s*>\s?", "", q)
    q = re.sub(r'(?m)^\s*(?:title|subtitle|author|date):\s*"?(.*?)"?\s*$', r"\1", q)
    q = re.sub(r"!?\[([^\]\n]*)\]\([^)\n]*\)", r"\1", q)
    q = q.replace("![", "")
    return re.sub(r"\]\([^)\n]*\)?", "", q)


# Drawing it

def manuscript_files(out, project, run, units):
    """The manuscript the map names, as the run read it."""
    named = [f.strip() for f in ((run.get("work_map") or {}).get("manuscript") or "").split(",")
             if f.strip() and f.strip().lower() != "none"]
    if not named:  # a run read without a map: the text file most units are anchored in
        counts = {}
        for u in units:
            for a in u["anchors"]:
                if Path(a["file"]).suffix.lower() in TEXT:
                    counts[a["file"]] = counts.get(a["file"], 0) + 1
        named = [max(counts, key=counts.get)] if counts else []
    files = []
    for f in named:
        read_as = f + ".md" if f.lower().endswith(".docx") and (out / MANUSCRIPT / (f + ".md")).exists() else f
        path = out / MANUSCRIPT / read_as if (out / MANUSCRIPT / read_as).exists() else project / f
        if path.is_file() and not reader.trace_numbers.is_binary(path):  # a PDF beside its source: the source
            files.append((read_as, path))
    return files


def build(out, project, note=None):
    out, project = Path(out), Path(project)
    units = json.loads((out / "units.json").read_text())["units"]
    codes = json.loads((out / "codes.json").read_text())
    run = json.loads((out / "reader-run.json").read_text())
    rows, decisions, claims = render.tally(units, codes)
    turns = parse_transcript((out / "transcript.txt").read_text())
    files = manuscript_files(out, project, run, units)
    if not files:
        raise SystemExit("No manuscript to draw: the finished-work map names none, or it isn't there.")
    paper = "".join((f"<p class='eyebrow'>{esc(name)}</p>" if len(files) > 1 else "")
                    + manuscript_html(path, path.read_text(errors="replace")) for name, path in files)
    names = [name for name, _ in files]

    # Text Claude copied in: follow it back to whoever first saved it in the source file.
    _, rturns, first_seen = reader.load_record(project)
    refs = reader.git(project, "for-each-ref", "--format=%(refname)", "refs/provenance", check=False).split()

    def origin(src, text):
        cs = reader.git(project, "log", "--reverse", "--format=%H", "-S", text, *refs, "--", src,
                        check=False).split() if refs else []
        return ({"file": src, **reader.turn_of_snapshot(cs[0], first_seen, rturns)} if cs
                else {"file": src, "by": "unknown"})

    p = Text()
    p.feed(paper)
    flat = norm("".join(p.parts))
    data_units, missing = [], []
    for r in rows:
        if r["kind"] == "decision":
            key = "made" if r["discretion"] == "kept" else r["certification"]
            who = "the tool, as you asked" if r["discretion"] == "given" else "the tool, beyond what you asked"
            label = "You made the call" if key == "made" else f"Made by {who}: " + render.HANDED.get(key, key or "uncoded")
            group = "made" if key == "made" else ("warranted" if key in render.WARRANTED else "not")
        else:
            key = r["certification"]
            label = render.CLAIMS.get(key, key or "uncoded")
            group = ("checked" if key in render.CHECKED else
                     "unseen" if key == "tool checked, you didn't see the result" else "not")
        cited = [int(x) for x in re.findall(r"T(\d+)", r.get("turns") or "")]
        first = min(cited) if cited else min([t["turn"] for t in r.get("trace", []) if t.get("turn")] or [0])
        for a in r["anchors"]:
            if a["file"] in names and a.get("found") and norm(plain(a["quote"])) not in flat:
                missing.append((r["id"], a["quote"][:80]))
        data_units.append({
            "id": r["id"], "kind": r["kind"], "row": r["row"], "stage": r["stage"], "label": r["label"],
            "key": key, "status": label, "group": group, "turns": cited, "first": first,
            "basis": codes.get(r["id"], {}).get("basis"), "confidence": r.get("confidence"),
            "anchors": [{"file": a["file"], "quote": a["quote"], "found": a.get("found"), "nq": norm(plain(a["quote"])),
                         "restates": bool(a.get("restates"))} for a in r["anchors"]],
            "trace": [{"file": t["file"], "turn": t.get("turn"), "by": t.get("by"), "change": t.get("change"),
                       "text": t["text"], "nq": norm(plain(t["text"])),
                       "copied": [origin(f, t["text"]) for f in t.get("copied_from", [])]}
                      for t in r.get("trace", [])]})

    # A long record's timeline groups its turns by day, week, or month (DECISIONS.md, Oct 23), so each
    # turn gets its local date; a short record's timeline is one column per turn, as before.
    if max(turns, default=0) > TIMELINE_TURNS:
        for t in rturns:
            if int(t["n"]) in turns and t.get("ts"):
                turns[int(t["n"])]["day"] = datetime.fromisoformat(t["ts"].replace("Z", "+00:00")).astimezone().date().isoformat()

    dparts, handed = render.decision_parts(decisions)
    cparts = render.claim_parts(claims)
    data = {"units": data_units, "turns": turns, "nturns": max(turns) if turns else 0, "manuscript": names,
            "decisionParts": [[k, l, n] for k, l, n in dparts], "claimParts": [[k, l, n] for k, l, n in cparts],
            "handed": len(handed), "note": note,
            "run": {"label": run.get("label"), "date": run.get("date"), "reader": run.get("reader"),
                    "model": run.get("model")}}
    # The header the disclosure uses (DECISIONS.md, Oct 22). Runs read before
    # reader 0.13.5 saved no title, so it's read here from the manuscript.
    head_run = {**run, "title": run.get("title") or render.paper_title(project, run.get("work_map"), names)}
    # The blanks are filled in one pass over the template, so a record that
    # quotes a blank (a search for "<!--PAPER-->", say) keeps it as text.
    fill = {"/*FONTS*/": render.fonts.css(),
            "<!--HEADER-->": render.header_html(head_run, run.get("packs"), "paper trail"),
            "/*DATA*/null": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
            "<!--PAPER-->": private(paper)}
    page = (HERE / "trail.html").read_text()
    page = re.sub("|".join(map(re.escape, fill)), lambda m: fill[m[0]], page)
    dest = out / "trail.html"
    dest.write_text(page)
    return dest, len(data_units), missing


def latest(repo, name=""):
    """The run to draw: the one named, or the latest finished one."""
    runs = sorted(d for d in (Path(repo) / OUT).glob("*/") if (d / "units.json").exists()
                  and (d / "codes.json").exists() and (d / "transcript.txt").exists())
    if name:
        runs = [d for d in runs if d.name == name.strip()]
    return runs[-1] if runs else None


def start(repo, plugin, args, narrate=False):
    """Returns (a reply for the person, or None; instructions for Claude, or None)."""
    run = latest(repo, args)
    if run is None:
        return ((f"There's no finished disclosure called {args.strip()}." if args.strip() else
                 "There's no finished disclosure yet. Type /disclosure first; the trail is drawn from it."), None)
    if not narrate:
        dest, n, _ = build(run, repo)
        return f"Drew the paper trail for {n} units: {dest.relative_to(repo)}. Open it in a browser.", None
    return None, "\n".join([
        f"warrant:trail. The warrant plugin's hook picked the disclosure in {run.relative_to(repo)}. Draw its paper "
        "trail so the author sees it happen. It makes no model calls and no new judgments; you don't read or judge "
        "anything yourself.",
        "1. Tell the author in one sentence that you're drawing the paper trail for that disclosure.",
        "2. Run this command:",
        f'   python3 "{Path(plugin) / "scripts" / "trail.py"}" "{run}" "{repo}"',
        "3. Tell the author what it printed, in plain words: where trail.html is, and that it opens in a browser. "
        "Say it isn't part of the disclosure, and stays on this computer unless they share it. Do nothing else in "
        "this turn.",
    ])


if __name__ == "__main__":
    args = sys.argv[1:]
    note = args[args.index("--note") + 1] if "--note" in args else None
    args = [a for i, a in enumerate(args) if a != "--note" and (i == 0 or args[i - 1] != "--note")]
    if len(args) != 2:
        sys.exit(__doc__)
    dest, n, missing = build(args[0], args[1], note)
    print(f"Drew the paper trail for {n} units: {dest}")
    if missing:
        print(f"{len(missing)} quotes in the manuscript couldn't be placed in the drawn page; those units are "
              "listed under the paper instead.")
