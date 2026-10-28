"""Draw the disclosure from a reader run: disclosure.md and disclosure.html.

    python3 render.py OUT_DIR    redraw OUT_DIR/disclosure.md and .html from the
                                 units.json, codes.json, and reader-run.json there

The reader calls this at the end of a run; it also redraws earlier runs
without calling the model again. Two rows, one for each kind of unit
(DECISIONS.md, Oct 7 design): judgment calls, split into the calls the
author made and the calls handed to the tool, and how each of those ended
up; and verifiable claims, by how each was checked. Outside the two rows,
how many of the calls the tool made went beyond what the author asked
(DECISIONS.md, Oct 16) and who typed the text, both computed and saved with
each run but not shown in the Stage 1 disclosure (DECISIONS.md, Oct 22). The markdown shows text bars
that read anywhere; the HTML page draws every level in its own shade and
prints cleanly to PDF. Oct 22 redesign (DECISIONS.md): one header shared with
the paper trail (a demonstration's condition, the paper's title, the
checklists in plain words), gray for the calls the author made, the stage
table under the two rows, and the fonts embedded (fonts.py).
"""
import html
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
CHECKLISTS = ["checklists/judgment-decisions.md", "checklists/checkable-claims.md"]
sys.path.insert(0, str(HERE))
import fonts  # noqa: E402
STAGES = ["Conceptualization", "Research design", "Data preparation and analysis",
          "Presentation of results", "Writing and editing"]

# The reader's codes, strongest first, and how the disclosure says them.
HANDED = {"changed": "you changed it", "elaborated and okayed": "you accepted it, with a reason",
          "okayed": "you accepted it", "ignored": "you ignored it", "wasn't notified": "you were never told"}
WARRANTED = ("changed", "elaborated and okayed", "okayed")
CLAIMS = {"you checked it against the source": "You checked it against the source",
          "tool checked, you confirmed": "The tool checked it, and you confirmed",
          "tool checked, you didn't see the result": "The tool checked it, and you didn't see the result",
          "no check": "No check", "wasn't notified": "You were never told"}
CHECKED = ("you checked it against the source", "tool checked, you confirmed")
WIDTH = 30


def stages():
    table = {}
    for c in CHECKLISTS:
        header = None
        for line in (TOOL / c).read_text().splitlines():
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if "Stage" in cells and "ID" in cells:
                header = cells
            elif header and len(cells) == len(header) and re.match(r"[A-Z]+\d+$", cells[0]):
                table[cells[0]] = cells[header.index("Stage")]
    return table


def tally(units, codes):
    stage_of = stages()
    rows = []
    for u in units:
        c = codes.get(u["id"], {})
        rows.append({**u, "discretion": c.get("discretion"), "certification": c.get("certification"),
                     "turns": c.get("turns"), "confidence": c.get("confidence"),
                     "stage": stage_of.get(re.sub(r"[a-z]+$", "", u["row"]), "Other")})
    decisions = [r for r in rows if r["kind"] == "decision"]
    claims = [r for r in rows if r["kind"] == "claim"]
    return rows, decisions, claims


def decision_parts(decisions):
    """The decision row: the author's calls, then each way a handed-over call ended."""
    made = sum(r["discretion"] == "kept" for r in decisions)
    handed = [r for r in decisions if r["discretion"] in ("given", "taken")]
    parts = [("made", "You made the call", made)]
    parts += [(code, label, sum(r["certification"] == code for r in handed)) for code, label in HANDED.items()]
    return parts, handed


def claim_parts(claims):
    return [(code, label, sum(r["certification"] == code for r in claims)) for code, label in CLAIMS.items()]


def pct(n, total):
    return f"{round(100 * n / total)}%" if total else "—"


def text_bar(groups, width=WIDTH):
    """groups: [(glyph, n)]. Largest remainders, and any nonzero group gets a character."""
    total = sum(n for _, n in groups)
    if not total:
        return " " * width
    exact = [n * width / total for _, n in groups]
    cells = [int(x) for x in exact]
    for i in sorted(range(len(groups)), key=lambda i: exact[i] - cells[i], reverse=True)[:width - sum(cells)]:
        cells[i] += 1
    for i, (_, n) in enumerate(groups):
        if n and not cells[i]:
            j = max(range(len(cells)), key=lambda k: cells[k])
            cells[j] -= 1
            cells[i] = 1
    return "".join(g * c for (g, _), c in zip(groups, cells))


def decision_bar(decisions, width=WIDTH):
    parts, _ = decision_parts(decisions)
    n = dict((k, v) for k, _, v in parts)
    return text_bar([("█", n["made"]), ("▒", sum(n[k] for k in WARRANTED)),
                     ("░", n["ignored"] + n["wasn't notified"])], width)


def claim_bar(claims, width=WIDTH):
    n = dict((k, v) for k, _, v in claim_parts(claims))
    return text_bar([("▓", sum(n[k] for k in CHECKED)), ("·", n["tool checked, you didn't see the result"]),
                     ("░", n["no check"] + n["wasn't notified"])], width)


def join(parts):
    return parts[0] if len(parts) == 1 else " and ".join(parts) if len(parts) == 2 else \
        ", ".join(parts[:-1]) + ", and " + parts[-1]


PACK_NAMES = {"quantitative": "quantitative studies", "experiments": "experiments", "qualitative": "qualitative studies",
              "theory": "theory papers", "tool": "research tools"}


def checklist_line(packs):
    """Which checklists the paper was read against, in plain words."""
    return "Read against the checklists for " + join(["any paper"] + [PACK_NAMES.get(p, p) for p in packs or []]) + "."


def condition(run):
    """A demonstration's condition, from its label, as in "Demonstration run
    (high delegation, high warrant), last save 4b094be"; None for an author's
    own work, whose disclosure names no cell."""
    m = re.match(r"Demonstration run \(([^)]+)\)", run.get("label") or "")
    return m.group(1) if m else None


def label_line(run):
    """The run's label, without a demonstration's condition, which the header shows on its own."""
    return re.sub(r"^Demonstration run \([^)]+\)", "Demonstration run", run.get("label") or "Draft, not attested")


def paper_title(project, work_map, files):
    """The paper's title, for the header: a markdown title block or first
    heading, a LaTeX \\title, or a Word file's title. None if there isn't one."""
    names = [f.strip() for f in ((work_map or {}).get("manuscript") or "").split(",") if f.strip() and f.strip() != "none"]
    names = names or [f for f in files if Path(f).suffix.lower() in (".md", ".qmd", ".rmd", ".tex", ".docx")][:1]

    def rank(name):  # with several manuscript files: a title block first, then a file named like the paper
        try:
            head = (Path(project) / name).read_text(errors="replace")[:4000] if Path(name).suffix.lower() != ".docx" else ""
        except OSError:
            head = ""
        block = bool(re.match(r"---\s*\n.*?^title:", head, re.S | re.M) or "\\title{" in head)
        return (not block, Path(name).stem.lower() not in ("paper", "manuscript", "main", "draft", "article"))
    for name in sorted(names, key=rank):
        path = Path(project) / name
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".docx":
                with zipfile.ZipFile(path) as z:
                    m = re.search(r"<dc:title>(.*?)</dc:title>", z.read("docProps/core.xml").decode(errors="replace"), re.S)
                title = html.unescape(m.group(1)) if m else ""
            else:
                text = path.read_text(errors="replace")
                m = (re.search(r"\\title\{(.+?)\}", text, re.S) if path.suffix.lower() == ".tex" else
                     re.match(r"---\s*\n.*?^title:\s*[\"']?(.+?)[\"']?\s*$", text, re.S | re.M)
                     or re.search(r"^#\s+(.+?)\s*$", text, re.M))
                title = m.group(1) if m else ""
        except (OSError, KeyError, zipfile.BadZipFile):
            continue
        title = re.sub(r"[*_`]", "", " ".join(title.split()))
        if title:
            return title
    return None


def unasked(decisions):
    """The line on the calls the tool made beyond what the author asked, or
    None when nothing was handed to the tool."""
    handed = [r for r in decisions if r["discretion"] in ("given", "taken")]
    if not handed:
        return None
    taken = [r for r in handed if r["discretion"] == "taken"]
    head = f"of the {len(handed)} call{'s' if len(handed) != 1 else ''} handed over."
    if not taken:
        return "none " + head
    ok = sum(r["certification"] in WARRANTED for r in taken)
    tail = ("You warranted " + ("it" if len(taken) == 1 else "both" if len(taken) == 2 else "all of them")
            if ok == len(taken) else "You did not warrant it" if len(taken) == 1 else
            "You warranted none of them" if not ok else f"You warranted {ok} of them")
    return f"{len(taken)} {head} {tail}."


def reader_standing(run):
    """For a reader other than Claude's, how it did against the test runs
    (DECISIONS.md, Oct 16)."""
    try:
        import backends
    except ImportError:
        return None
    return backends.STANDING.get(run.get("backend"))


def head_lines(run, packs):
    cond, title = condition(run), run.get("title")
    lines = ([f"**Demonstration: {cond}**", ""] if cond else []) + ([f"**{title}**", ""] if title else [])
    lines += ([checklist_line(packs), ""] if packs else [])
    lines += [f"*{label_line(run)}. Generated by the reader {run.get('reader')} ({run.get('model')}), {run.get('date')}.*", ""]
    standing = reader_standing(run)
    if standing:
        lines += [f"*{standing}*", ""]
    finger = run.get("fingerprint")
    if finger:
        lines += [f"**Fingerprint:** commit `{finger['commit']}`; " + "; ".join(
            f"log `{l['log']}` head `{l['head']}` ({l['events']} events{'' if l['verifies'] else ', DOES NOT VERIFY'})"
            for l in finger["logs"]), ""]
    if run.get("converted"):
        lines += [f"*Converted from Word for reading: {', '.join(run['converted'])}. Who typed it isn't measured inside "
                  "a Word file.*", ""]
    if run.get("record_read"):
        lines += [f"*{pieces_line(run['record_read'])}*", ""]
    return lines


def pieces_line(read):
    """How a record too long to read at once was read (reader 0.14; the
    turns that quote each group's text are added in 0.14.1)."""
    (before, after), narrowed = read["windows"][0], len(read["windows"]) > 1
    quoting = read.get("quoting")
    fits = [n for n, on in (("the turns that quote it left out", read.get("quoting_dropped")),
                            ("the window narrowed", narrowed)) if on]
    return (f"Read in pieces: the record ({read['turns']:,} turns) was too long to read at once, so each group of "
            f"calls and claims was coded with the turns from {before} before to {after} after where its text was "
            "written" + (f" and up to {quoting[1]} more that quote it" if quoting else "")
            + ", in full, and only the author's side of every other turn"
            + (f" ({' and '.join(fits)} for some, to fit)" if fits else "")
            + ". A first use, not yet validated against an answer key.")


def work_lines(files, work_map, outside):
    lines = ["## Finished Work Product", "", "*The files this disclosure covers, as the author confirmed them.*", ""]
    if not work_map:
        return lines + [", ".join(files), ""]
    n = len(outside or [])
    return lines + [*[f"- {k}: {v}" for k, v in work_map.items() if k not in ("type", "packs")], "",
                    f"**Not covered:** {n} other file{'' if n == 1 else 's'}, not counting the record and the tool's own"
                    + (f": {', '.join(outside[:40])}" + (f", and {n - 40} more" if n > 40 else "") if outside else "") + ".", ""]


def markdown(units, codes, run, files, work_map=None, outside=None, packs=None):
    rows, decisions, claims = tally(units, codes)
    dparts, handed = decision_parts(decisions)
    lines = ["# Warranted delegation disclosure", "", *head_lines(run, packs)]
    lines += [f"## Judgment calls: {len(decisions)}", "",
              f"`{decision_bar(decisions)}`", "",
              "█ you made the call · ▒ handed to the tool, then changed or accepted (warranted) · "
              "░ handed to the tool, then ignored or never told (not warranted)", "",
              f"- **You made the call:** {dparts[0][2]} ({pct(dparts[0][2], len(decisions))})",
              f"- **Handed to the tool:** {len(handed)} ({pct(len(handed), len(decisions))})"
              + (f". Of those {len(handed)}:" if handed else "")]
    lines += [f"  - {label}: {n} ({pct(n, len(handed))})" for _, label, n in dparts[1:] if handed]
    cparts = claim_parts(claims)
    lines += ["", f"## Verifiable claims: {len(claims)}", "", f"`{claim_bar(claims)}`", "",
              "▓ checked · · the tool checked, and you didn't see the result · ░ not checked", "",
              *[f"- {label}: {n} ({pct(n, len(claims))})" for _, label, n in cparts], ""]
    lines += ["## Calls and claims by research stage", "",
              "| Stage | Judgment calls | Made the call | Handed over, then changed or accepted | Handed over, then not | "
              "Verifiable claims | Checked | Not checked |",
              "| :- | :- | -: | -: | -: | :- | -: | -: |"]
    for s in STAGES + sorted({r["stage"] for r in rows} - set(STAGES)):
        d = [r for r in decisions if r["stage"] == s]
        c = [r for r in claims if r["stage"] == s]
        if not d and not c:
            continue
        h = [r for r in d if r["discretion"] in ("given", "taken")]
        lines.append(f"| {s} | `{decision_bar(d, 10)}` {len(d)} | {sum(r['discretion'] == 'kept' for r in d)} | "
                     f"{sum(r['certification'] in WARRANTED for r in h)} | {sum(r['certification'] not in WARRANTED for r in h)} | "
                     f"`{claim_bar(c, 10)}` {len(c)} | {sum(r['certification'] in CHECKED for r in c)} | "
                     f"{sum(r['certification'] not in CHECKED for r in c)} |")
    lines += ["", *work_lines(files, work_map, outside),
              "## Every call and claim", "", "| ID | Row | Call or claim | Who made the call | How it ended up | Turns | Confidence |",
              "| :- | :- | :- | :- | :- | :- | :- |"]
    for r in rows:
        who, how = describe(r)
        lines.append(f"| {r['id']} | {r['row']} | {r['label']} | {who} | {how} | {r.get('turns') or ''} | "
                     f"{r.get('confidence') or ''} |")
    uncoded = [u["id"] for u in units if u["id"] not in codes]
    if uncoded:
        lines += ["", f"*Units the reader could not code: {', '.join(uncoded)}.*"]
    unanchored = [u["id"] for u in units if not any(a.get("found") for a in u.get("anchors", []))]
    if unanchored:
        lines += ["", f"*Units whose quotes weren't found in the work: {', '.join(unanchored)}.*"]
    return "\n".join(lines) + "\n"


def extra_lines(run, decisions):
    """Additional information, kept apart from the two measures (DECISIONS.md, Oct 16 and 22).
    Not shown in the Stage 1 disclosure (DECISIONS.md, Oct 22): both figures are
    still computed and saved with each run, and Stage 2 can show them again."""
    more, typed = unasked(decisions), run.get("typed")
    if not (more or typed):
        return []
    lines = ["## Additional information", ""]
    if more:
        lines += [f"**Calls the tool made beyond what you asked:** {more[0].upper() + more[1:]}", ""]
    if typed:
        lines += [f"**Text typed by the tool:** {pct(typed['tool_words'], typed['words'])} of {typed['words']:,} words.", "",
                  "*Who typed the text is not the same as who stands behind it.*", ""]
    return lines


def describe(r):
    if r["kind"] == "claim":
        return "—", CLAIMS.get(r.get("certification"), r.get("certification") or "—")
    if r.get("discretion") == "kept":
        return "you", "—"
    if r.get("discretion") in ("given", "taken"):
        who = "the tool, as you asked" if r["discretion"] == "given" else "the tool, beyond what you asked"
        return who, HANDED.get(r.get("certification"), r.get("certification") or "—")
    return r.get("discretion") or "—", r.get("certification") or "—"


# The page

CSS = """
:root { --bg: #fbfaf7; --surface: #ffffff; --fg: #1d232b; --muted: #5d6673; --rule: #dfe2e6;
  --made: #9aa1aa; --w1: #2f6aa3; --w2: #5b92c4; --w3: #9cc0e0; --n1: #e3a06c; --n2: #c4622b;
  --c1: #1f3f66; --c2: #4f86bd; --unseen: #f2d2b4; --c4: #e3a06c; --c5: #c4622b; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --bg: #14181d; --surface: #1b2128; --fg: #e6e9ed; --muted: #9aa4b1;
  --rule: #2e3640; --made: #6e7681; --w1: #5f99d1; --w2: #3f74a8; --w3: #2b5277; --n1: #b97447; --n2: #e08b55;
  --c1: #8fb8e6; --c2: #4f86bd; --unseen: #7a5a40; --c4: #b97447; --c5: #e08b55; color-scheme: dark; } }
@media print { :root { --bg: #ffffff; } details { display: block; } details > summary { display: none; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.55 SANS; }
main { max-width: 860px; margin: 0 auto; padding: 40px 20px 64px; display: grid; gap: 32px; }
h1 { font-family: SERIF; font-weight: 600; font-size: clamp(1.6rem, 1.2rem + 1.4vw, 2.2rem); line-height: 1.15; margin: 0; }
h2 { font-family: SERIF; font-weight: 600; font-size: 1.25rem; margin: 0 0 10px; }
.condition { justify-self: start; font-size: 1.05rem; font-weight: 600; padding: 5px 12px; border-radius: 999px;
  background: var(--surface); border: 1.5px solid var(--w1); }
.ptitle { font-family: SERIF; font-size: 1.35rem; font-weight: 600; line-height: 1.25; }
.checks { font-size: 1.05rem; }
p { margin: 0; }
.meta { color: var(--muted); font-size: 13.5px; display: grid; gap: 6px; }
.meta code { font-family: MONO; font-size: 12px; word-break: break-all; }
section { display: grid; gap: 12px; min-width: 0; }
.card { background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 18px 20px; display: grid; gap: 14px; }
.bar { display: flex; height: 30px; border-radius: 6px; overflow: hidden; background: var(--rule); }
.bar.small { height: 12px; border-radius: 4px; }
.bar span { display: block; height: 100%; }
.bar span + span { box-shadow: inset 1px 0 0 var(--surface); }
.key { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.key li { display: grid; grid-template-columns: 14px 1fr auto auto; gap: 10px; align-items: baseline; font-variant-numeric: tabular-nums; }
.key li.sub { padding-left: 22px; grid-template-columns: 14px 1fr auto auto; }
.key li.group { font-weight: 600; grid-template-columns: 14px 1fr auto auto; }
.key .sw { width: 14px; height: 14px; border-radius: 3px; align-self: center; }
.key .n { text-align: right; min-width: 2.5em; }
.key .p { text-align: right; min-width: 3.5em; color: var(--muted); }
.note { color: var(--muted); font-size: 13.5px; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; font-variant-numeric: tabular-nums; }
th { text-align: left; font-weight: 600; color: var(--muted); border-bottom: 1px solid var(--rule); padding: 6px 8px; vertical-align: bottom; }
td { border-bottom: 1px solid var(--rule); padding: 6px 8px; vertical-align: top; }
td.num, th.num { text-align: right; }
.wide { overflow-x: auto; }
.stage td:nth-child(2), .stage td:nth-child(4) { width: 22%; }
details summary { cursor: pointer; color: var(--muted); }
ul.plain { margin: 0; padding-left: 18px; }
.extra { display: grid; gap: 6px; }
""".replace("SANS", fonts.SANS).replace("SERIF", fonts.SERIF).replace("MONO", fonts.MONO)
DECISION_COLORS = {"made": "var(--made)", "changed": "var(--w1)", "elaborated and okayed": "var(--w2)",
                   "okayed": "var(--w3)", "ignored": "var(--n1)", "wasn't notified": "var(--n2)"}
CLAIM_COLORS = {"you checked it against the source": "var(--c1)", "tool checked, you confirmed": "var(--c2)",
                "tool checked, you didn't see the result": "var(--unseen)", "no check": "var(--c4)",
                "wasn't notified": "var(--c5)"}


def header_html(run, packs, kind):
    """The header the disclosure and the paper trail share: what the page is,
    a demonstration's condition, the paper's title, the checklists, and the
    run's details."""
    e = html.escape
    cond, title = condition(run), run.get("title")
    meta = [f"<p>{e(label_line(run))}. Generated by the reader {e(str(run.get('reader')))} "
            f"({e(str(run.get('model')))}), {e(str(run.get('date')))}.</p>"]
    finger = run.get("fingerprint")
    if finger:
        meta.append("<p>Fingerprint: commit <code>" + e(finger["commit"]) + "</code>; " + "; ".join(
            f"log <code>{e(l['log'])}</code> head <code>{e(l['head'])}</code> ({l['events']} events"
            f"{'' if l['verifies'] else ', DOES NOT VERIFY'})" for l in finger["logs"]) + "</p>")
    standing = reader_standing(run)
    if standing:
        meta.append(f"<p>{e(standing)}</p>")
    if run.get("converted"):
        meta.append(f"<p>Converted from Word for reading: {e(', '.join(run['converted']))}. Who typed it isn't measured "
                    "inside a Word file.</p>")
    if run.get("record_read"):
        meta.append(f"<p>{e(pieces_line(run['record_read']))}</p>")
    return (f'<h1>Warranted delegation {e(kind)}</h1>'
            + (f'<p class="condition">Demonstration: {e(cond)}</p>' if cond else "")
            + (f'<p class="ptitle">{e(title)}</p>' if title else "")
            + (f'<p class="checks">{e(checklist_line(packs))}</p>' if packs else "")
            + f'<div class="meta">{"".join(meta)}</div>')


def bar_html(parts, colors, total, small=False, label=""):
    spans = "".join(f'<span style="width:{100 * n / total:.2f}%;background:{colors[k]}" title="{html.escape(l)}: {n}"></span>'
                    for k, l, n in parts if n) if total else ""
    return f'<div class="bar{" small" if small else ""}" role="img" aria-label="{html.escape(label)}">{spans}</div>'


def key_item(color, label, n, share, cls=""):
    sw = f'<span class="sw" style="background:{color}"></span>' if color else "<span></span>"
    return f'<li class="{cls}">{sw}<span>{html.escape(label)}</span><span class="n">{n}</span><span class="p">{share}</span></li>'


def page(units, codes, run, files, work_map=None, outside=None, packs=None):
    rows, decisions, claims = tally(units, codes)
    dparts, handed = decision_parts(decisions)
    cparts = claim_parts(claims)
    e = html.escape
    d_total = len(decisions)
    dec = [bar_html(dparts, DECISION_COLORS, d_total, label=f"Judgment calls: {d_total}"),
           '<ul class="key">', key_item(DECISION_COLORS["made"], "You made the call", dparts[0][2], pct(dparts[0][2], d_total), "group"),
           key_item("", "Handed to the tool", len(handed), pct(len(handed), d_total), "group")]
    dec += [key_item(DECISION_COLORS[k], l, n, pct(n, len(handed)), "sub") for k, l, n in dparts[1:]]
    dec += ["</ul>", '<p class="note">Gray is the calls you made. Blues are the ways a handed-over call was warranted, '
                     'strongest first, and oranges the ways it was not. Shares under "Handed to the tool" are of the calls handed over.</p>']
    c_total = len(claims)
    cla = [bar_html(cparts, CLAIM_COLORS, c_total, label=f"Verifiable claims: {c_total}"), '<ul class="key">']
    cla += [key_item(CLAIM_COLORS[k], l, n, pct(n, c_total)) for k, l, n in cparts]
    cla += ["</ul>", '<p class="note">Blues are the claims checked against their source, and oranges the ways a claim was not.</p>']
    stage_rows = []
    for s in STAGES + sorted({r["stage"] for r in rows} - set(STAGES)):
        d = [r for r in decisions if r["stage"] == s]
        c = [r for r in claims if r["stage"] == s]
        if not d and not c:
            continue
        dp, _ = decision_parts(d)
        stage_rows.append(f"<tr><td>{e(s)}</td><td>{bar_html(dp, DECISION_COLORS, len(d), True, f'{s}: calls')}</td>"
                          f"<td class='num'>{len(d)}</td><td>{bar_html(claim_parts(c), CLAIM_COLORS, len(c), True, f'{s}: claims')}</td>"
                          f"<td class='num'>{len(c)}</td></tr>")
    unit_rows = []
    for r in rows:
        who, how = describe(r)
        unit_rows.append(f"<tr><td>{e(r['id'])}</td><td>{e(r['row'])}</td><td>{e(r['label'])}</td><td>{e(who)}</td>"
                         f"<td>{e(how)}</td><td>{e(r.get('turns') or '')}</td></tr>")
    if work_map:
        n = len(outside or [])
        items = "".join(f"<li>{e(k)}: {e(v)}</li>" for k, v in work_map.items() if k not in ("type", "packs"))
        covered = (f'<ul class="plain">{items}</ul><p class="note">Not covered: {n} other file{"" if n == 1 else "s"}, not '
                   f'counting the record and the tool\'s own{": " + e(", ".join(outside[:40])) if outside else ""}.</p>')
    else:
        covered = f"<p>{e(', '.join(files))}</p>"
    work = (f'<section><h2>Finished Work Product</h2><div class="card"><p class="note">The files this disclosure covers, '
            f'as the author confirmed them.</p>{covered}</div></section>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Warranted delegation disclosure</title><style>{fonts.css()}
{CSS}</style></head>
<body><main>
<header style="display:grid;gap:10px">{header_html(run, packs, "disclosure")}</header>
<section><h2>Judgment calls: {d_total}</h2><div class="card">{"".join(dec)}</div></section>
<section><h2>Verifiable claims: {c_total}</h2><div class="card">{"".join(cla)}</div></section>
<section><h2>Calls and claims by research stage</h2><div class="card wide"><table class="stage"><thead><tr><th>Stage</th><th>Judgment calls</th>
<th class="num">n</th><th>Verifiable claims</th><th class="num">n</th></tr></thead><tbody>{"".join(stage_rows)}</tbody></table></div></section>
{work}
<section><h2>Every call and claim</h2><details><summary>Show all {len(rows)}</summary><div class="wide">
<table><thead><tr><th>ID</th><th>Row</th><th>Call or claim</th><th>Who made the call</th><th>How it ended up</th><th>Turns</th></tr></thead>
<tbody>{"".join(unit_rows)}</tbody></table></div></details></section>
</main></body></html>
"""


def write(out, units, codes, run, files, work_map=None, outside=None, packs=None):
    out = Path(out)
    (out / "disclosure.md").write_text(markdown(units, codes, run, files, work_map, outside, packs))
    (out / "disclosure.html").write_text(page(units, codes, run, files, work_map, outside, packs))


def redraw(out):
    out = Path(out)
    u = json.loads((out / "units.json").read_text())
    codes = json.loads((out / "codes.json").read_text())
    run = json.loads((out / "reader-run.json").read_text())
    write(out, u["units"], codes, run, u["files"], run.get("work_map"), run.get("outside"), run.get("packs"))


if __name__ == "__main__":
    for d in sys.argv[1:] or ["."]:
        redraw(d)
