"""The typefaces the disclosure and the paper trail share, embedded in each
page, so both look the same on any computer, offline included, and neither
asks an outside server for anything (DECISIONS.md, Oct 22). IBM Plex Sans and
Mono, and Source Serif 4, Latin only, under the SIL Open Font License; the
files and their licenses are in the plugin's fonts/ folder."""
import base64
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent / "fonts"
FACES = [("IBM Plex Sans", "normal", "400 600", "ibm-plex-sans.woff2"),
         ("IBM Plex Sans", "italic", "400", "ibm-plex-sans-italic.woff2"),
         ("Source Serif 4", "normal", "400 600", "source-serif-4.woff2"),
         ("Source Serif 4", "italic", "400", "source-serif-4-italic.woff2"),
         ("IBM Plex Mono", "normal", "400", "ibm-plex-mono-400.woff2"),
         ("IBM Plex Mono", "normal", "500", "ibm-plex-mono-500.woff2")]
SANS = '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
SERIF = '"Source Serif 4", "Iowan Old Style", Georgia, serif'
MONO = '"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace'


def css():
    """@font-face rules with each file inlined; a missing file is skipped, and
    the page falls back to the computer's own fonts."""
    rules = []
    for family, style, weight, name in FACES:
        path = FOLDER / name
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            rules.append(f'@font-face {{ font-family: "{family}"; font-style: {style}; font-weight: {weight}; '
                         f'font-display: swap; src: url(data:font/woff2;base64,{data}) format("woff2"); }}')
    return "\n".join(rules)
