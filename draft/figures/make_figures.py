"""Figures 1-3 for the proposal (Oct 22). Figure 1 is drawn here; Figures 2
and 3 are pictures of the plugin's real pages for the experiment
demonstrations, redrawn with plugin 0.10.5. Pictures are taken with headless
Chrome in the light theme and trimmed with Pillow. Run from the repository:

    python3 draft/figures/make_figures.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "plugin/warrant/scripts"))
import fonts  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
RUNS = REPO / "tests/longdemo/runs"
HH = RUNS / "experiment-high-high-2026-10-17-0933/disclosure"
HL = RUNS / "experiment-high-low-2026-10-17-1043/disclosure"
SCALE = 2


def shoot(html, png, width, height):
    """A picture of a page in the light theme, at twice the pixels."""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html.replace("prefers-color-scheme: dark", "prefers-color-scheme: never"))
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", f"--force-device-scale-factor={SCALE}",
                        f"--window-size={width},{height}", "--virtual-time-budget=4000", f"--screenshot={png}",
                        page.as_uri() + ("#" + html.split("#START=")[1].split("#")[0] if "#START=" in html else "")],
                       check=True, capture_output=True)


def trim(png, pad=24):
    """Cut the empty background from the bottom and sides, leaving a margin."""
    im = Image.open(png).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, im.size[1] - 2)))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        l, t, r, b = box
        p = pad * SCALE
        im = im.crop((max(0, l - p), max(0, t - p), min(im.size[0], r + p), min(im.size[1], b + p)))
    im.save(png)
    return im


# Figure 1: the pipeline, drawn with the disclosure's own stylesheet

FIG1_CSS = """
body { background: #ffffff; }
main.fig { max-width: none; width: 1560px; padding: 24px; display: grid; gap: 0;
  grid-template-columns: 430px 64px 1fr; align-items: stretch; }
.group { border: 1.5px dashed #b9c2cc; border-radius: 14px; padding: 16px 18px 18px; display: grid; gap: 14px; align-content: start; background: #f6f7f9; }
.group > .glabel { font-family: SERIF; font-weight: 600; font-size: 1.2rem; }
.group > .glabel span { display: block; font-family: SANS; font-weight: 400; font-size: 14px; color: var(--muted); margin-top: 2px; }
.right { display: grid; grid-template-columns: 330px 64px 1fr; gap: 0; align-items: center; }
.step { display: grid; gap: 8px; }
.step h3 { margin: 0; font-family: SERIF; font-weight: 600; font-size: 1.25rem; display: flex; align-items: center; gap: 10px; }
.step h3 i { font-style: normal; font-family: SANS; font-size: 14px; color: #fff; background: var(--w1); width: 26px; height: 26px; border-radius: 50%; display: inline-grid; place-items: center; }
.step p { color: var(--muted); }
.step code { font-family: MONO; font-size: 14px; color: var(--fg); background: #eef2f6; border: 1px solid var(--rule); border-radius: 6px; padding: 2px 8px; justify-self: start; }
.tag { justify-self: start; font-size: 12.5px; font-weight: 600; color: var(--w1); border: 1.5px solid var(--w1); border-radius: 999px; padding: 1px 9px; }
.arrow { display: grid; place-items: center; }
.outs { display: grid; gap: 16px; }
.outhead { margin-bottom: -6px; }
.setup { font-size: 14px; color: var(--muted); line-height: 1.7; padding: 8px 12px; border: 1px solid var(--rule); border-radius: 8px; background: #eef2f6; }
.setup b { color: var(--fg); font-weight: 600; }
.setup code { font-family: MONO; font-size: 13px; color: var(--fg); background: var(--surface); border: 1px solid var(--rule); border-radius: 5px; padding: 1px 6px; }
.bar { height: 22px; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 13.5px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend b { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.mini { display: grid; grid-template-columns: 1fr 210px; gap: 12px; }
.mpage { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 12px 14px; font-family: SERIF; font-size: 14.5px; line-height: 1.55; }
.mpage .mh { font-weight: 600; font-size: 15.5px; margin-bottom: 4px; }
.mpage mark { color: inherit; padding: 0 1px; border-bottom: 2px solid; }
.mpanel { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 10px 12px; display: grid; gap: 5px; font-size: 12.5px; color: var(--muted); align-content: start; }
.mpanel .k { font-size: 10.5px; letter-spacing: 0.07em; text-transform: uppercase; font-weight: 500; }
.mpanel .t { font-family: SERIF; font-weight: 600; font-size: 14px; color: var(--fg); line-height: 1.3; }
.mpanel .st { display: flex; gap: 6px; align-items: baseline; color: var(--fg); font-weight: 500; }
.mpanel .st b { width: 10px; height: 10px; border-radius: 2px; background: var(--w1); display: inline-block; flex: none; }
"""

ARROW = ('<svg width="56" height="40" viewBox="0 0 56 40"><line x1="4" y1="20" x2="44" y2="20" stroke="#5d6673" stroke-width="2.5"/>'
         '<path d="M42,12 L54,20 L42,28 z" fill="#5d6673"/></svg>')
FORK = ('<svg width="56" height="300" viewBox="0 0 56 300"><path d="M2,150 C28,150 26,60 44,60" stroke="#5d6673" stroke-width="2.5" fill="none"/>'
        '<path d="M2,150 C28,150 26,240 44,240" stroke="#5d6673" stroke-width="2.5" fill="none"/>'
        '<path d="M42,52 L54,60 L42,68 z" fill="#5d6673"/><path d="M42,232 L54,240 L42,248 z" fill="#5d6673"/></svg>')


def figure1():
    sys.path.insert(0, str(REPO / "plugin/warrant/scripts"))
    import render
    css = (FIG1_CSS.replace("SANS", fonts.SANS).replace("SERIF", fonts.SERIF).replace("MONO", fonts.MONO))
    seg = lambda c, w: f'<span style="width:{w}%;background:var(--{c})"></span>'
    bar = f'<div class="bar">{seg("made", 32)}{seg("w1", 8)}{seg("w2", 8)}{seg("w3", 30)}{seg("n1", 14)}{seg("n2", 8)}</div>'
    key = lambda c, l: f'<span><b style="background:var(--{c})"></b>{l}</span>'
    m = lambda c, t: f'<mark style="background:color-mix(in srgb, var(--{c}) 35%, transparent);border-color:var(--{c})">{t}</mark>'
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{fonts.css()}
{render.CSS}
{css}</style></head><body><main class="fig">
<section class="group"><div class="glabel">While the author works<span>in Claude Code or Codex, on their own computer</span></div>
  <div class="setup"><b>Once per project:</b> <code>/warrant:setup</code> starts the record and, for GitHub users, a private repository.</div>
  <div class="card step"><h3><i>1</i>Record</h3><span class="tag">Automatic</span>
    <p>Every prompt, every action the AI takes, and every reply, kept in the background. Each entry is linked to the last by a hash.</p></div>
  <div class="card step"><h3><i>2</i>Attest</h3>
    <p>At natural stopping points, the author signs off on a version of the work and the record, saved under their name.</p>
    <code>/warrant:attest</code></div>
</section>
<div class="arrow">{ARROW}</div>
<section class="group"><div class="glabel">When the author asks<span>at any point, for a draft or the final version</span></div>
  <div class="right">
    <div class="card step"><h3><i>3</i>Reader</h3>
      <p>Reads the finished work and the record against the checklists for that kind of paper.</p>
      <p>Finds each judgment call and verifiable claim, and codes who made it and whether it was warranted.</p>
      <p>Runs with each disclosure.</p></div>
    <div class="arrow">{FORK}</div>
    <div class="outs">
      <div class="step outhead"><h3><i>4</i>Output</h3></div>
      <div class="card step"><h3>Disclosure</h3>{bar}
        <div class="legend">{key("made", "You made the call")}{key("w2", "Handed over, warranted")}{key("n1", "Handed over, not warranted")}</div>
        <p>Delegation and warrant across the whole paper.</p>
        <code>/warrant:disclosure</code></div>
      <div class="card step"><h3>Paper trail</h3>
        <div class="mini"><div class="mpage"><div class="mh">Introduction</div>
          {m("made", "We ask whether costless motivators raise effort.")} Using an 18-arm online experiment, we
          {m("w1", "exclude workers who did not finish within 30 minutes")} and {m("w3", "compare each arm with no pay")}.
          {m("n1", "Prior work finds the same reversal")}.</div>
          <div class="mpanel"><div class="k">The trail</div><div class="t">Exclusion rule: unfinished or over 30 minutes</div>
            <div class="st"><b></b>Made by the tool, as you asked: you changed it</div>
            <div>Where it is made: paper.md, scripts/clean.py</div><div>Turns T3, T5</div></div></div>
        <p>Each call and claim marked in the paper, with the evidence behind it. Drawn from the disclosure's codes.</p>
        <code>/warrant:trail</code></div>
    </div>
  </div>
</section>
</main></body></html>"""
    (OUT / "figure1-pipeline.html").write_text(html)
    shoot(html, OUT / "figure1-pipeline.png", 1620, 1200)
    trim(OUT / "figure1-pipeline.png", pad=6)


# Figure 2: the two disclosures, side by side

def figure2():
    hide = ("<style>.meta, section:has(table.stage), section:has(details), "
            "section:has(.card ul.plain) { display: none !important; } main { padding-bottom: 8px; }</style>")
    parts = []
    for name, d in (("hh", HH), ("hl", HL)):
        png = OUT / f"figure2-{name}.png"
        shoot((d / "disclosure.html").read_text().replace("</head>", hide + "</head>"), png, 900, 2200)
        parts.append(trim(png))
    # Each page in its own framed box, so the two read as separate disclosures.
    pad, gap, edge, radius = 14 * SCALE, 28 * SCALE, 2 * SCALE, 14 * SCALE
    inner = max(p.size[1] for p in parts)
    cards = []
    for p in parts:
        w, h = p.size[0] + 2 * pad, inner + 2 * pad
        card = Image.new("RGB", (w, h), "#ffffff")
        ImageDraw.Draw(card).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=p.getpixel((2, 2)),
                                               outline="#b9c2cc", width=edge)
        card.paste(p.crop((edge, 0, p.size[0] - edge, p.size[1])), (pad + edge, pad))
        cards.append(card)
    sheet = Image.new("RGB", (sum(c.size[0] for c in cards) + gap, cards[0].size[1]), "#ffffff")
    x = 0
    for c in cards:
        sheet.paste(c, (x, 0))
        x += c.size[0] + gap
    sheet.save(OUT / "figure2-disclosures.png")
    for name in ("hh", "hl"):
        (OUT / f"figure2-{name}.png").unlink()


# Figure 3: the paper trail, one call opened

def figure3(unit="U33"):
    """The trail with one call opened. Headless Chrome draws a scrolled page
    blank, so the picture's copy of the page hides the paper's text before the
    call's passage instead of scrolling to it, ends the paper at a whole block,
    and sizes the trail panel to match."""
    html = (HH / "trail.html").read_text()
    pick = (f'const m0 = [...document.querySelectorAll("mark.u")].find(m => m.dataset.u.split(" ").includes("{unit}"));\n'
            'clicked = (m0.closest("table") || m0.closest("p, li, h1, h2, h3, h4, h5, h6, blockquote") || m0).textContent;\n'
            f'selectUnits(["{unit}"], {{from: "paper"}});\n'
            'const blk = document.querySelector("mark.u.sel").closest(".paper > *");\n'
            'for (let n = blk.previousElementSibling; n; n = n.previousElementSibling) n.style.display = "none";\n'
            'const limit = blk.getBoundingClientRect().top + 900;\n'
            'let cut = false;\n'
            'for (let n = blk.nextElementSibling; n; n = n.nextElementSibling) {\n'
            '  cut = cut || n.getBoundingClientRect().bottom > limit;\n'
            '  if (cut) n.style.display = "none";\n'
            '}\n'
            'const paper = document.querySelector(".paper"), shown = () => [...paper.children].filter(n => n.style.display !== "none");\n'
            'while (/^H[1-6]$/.test(shown().pop()?.tagName || "")) shown().pop().style.display = "none";\n'
            'const aside = document.querySelector("aside.trail"), bottom = paper.getBoundingClientRect().bottom;\n'
            'aside.style.maxHeight = "none";\n'
            'let over = false;\n'
            'for (const sec of aside.querySelectorAll(".body > *")) {\n'
            '  if (over) { sec.style.display = "none"; continue; }\n'
            '  if (sec.getBoundingClientRect().bottom <= bottom) continue;\n'
            '  over = true;\n'
            '  const items = [...sec.querySelectorAll("li, .k")];\n'
            '  let cut = false;\n'
            '  for (const it of items) { cut = cut || it.getBoundingClientRect().bottom > bottom; if (cut) it.style.display = "none"; }\n'
            '  if (!items.some(it => it.tagName === "LI" && it.style.display !== "none")) sec.style.display = "none";\n'
            '}')
    old = 'const start = decodeURIComponent(location.hash.slice(1));\nif (U[start]) selectUnits([start], {from: "hash"});'
    assert old in html
    png = OUT / "figure3-trail.png"
    shoot(html.replace(old, pick), png, 1600, 3400)
    trim(png, pad=8)


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3"]
    for n in which:
        {"1": figure1, "2": figure2, "3": figure3}[n]()
        print("figure", n, "done")
