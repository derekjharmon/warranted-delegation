"""/warrant:disclosure: generate the disclosure for this project.

    /warrant:disclosure          a draft of the work as it stands now
    /warrant:disclosure final    the latest version marked with /warrant:attest final

The first time, it proposes the finished-work map, provenance/finished-work.md:
the paper plus everything its reported results depend on, one line per work
product, which the author checks and corrects (DECISIONS.md, Oct 6). Claude
walks the author through it in the chat, in plain words, and saves their
changes, so no one has to edit the file (DECISIONS.md, Oct 23). The map
also names the paper's checklist packs, which the reader adds to the spine
every paper gets; the tool proposes them from the project's files and the
author confirms or changes them (DECISIONS.md, Oct 7). The map is saved with
the next /warrant:attest, so changes to it are visible in the record.

After that, it copies the project to a stable snapshot (so the work can go on)
and runs the reader on it in the background, because a reader run takes
minutes and a hook can't wait that long. Claude narrates the run as it goes,
so the author sees the process as it unfolds (DECISIONS.md, Oct 16): the hook
gives Claude the steps, and Claude runs `disclose.py follow`, which waits for
the reader's next step and says it in plain words. The reader itself is
unchanged: `disclose.py read` runs it and writes a line to progress.jsonl as
each step starts, by wrapping its steps from outside. The result goes to
disclosure/<date-time>/disclosure.md, with the reader's units, codes, and run
details. /warrant:record says whether it's still running, done, or failed.
Headless (claude -p), it just runs in the background.

The reader runs on the tool the project named in setup (provenance/
settings.json): Codex or Gemini on the author's own account (backends.py),
or Claude. For Claude Code, the first disclosure in a copy asks whether
it reaches Claude through the author's own subscription, with no API key
(headless Claude Code), or the API, and remembers the answer; /disclosure api
or /disclosure subscription changes it (DECISIONS.md, Oct 16). Anything not
settled yet, such as the tool for a project set up before this version, is
asked the same way: the hook hands Claude the questions, Claude saves the
answers (setup.py save) and starts the run (disclose.py start). The API uses
the author's own key, from the macOS Keychain item
"warranted-delegation-anthropic", and its own Python environment in
~/.warranted-delegation (WD_HOME), which this sets up the first time.

A Word manuscript (.docx) is converted to text with pandoc in the stable copy,
never in the project, and the disclosure says so (DECISIONS.md, Oct 7).

For testing: WD_DISCLOSURE_STUB=1 writes a placeholder instead of calling
the reader.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import setup

MAP = Path("provenance") / "finished-work.md"
OUT = Path("disclosure")
HERE = Path(__file__).resolve().parent
PROGRESS = "progress.jsonl"  # in the run's folder: a line as each of the reader's steps starts
FOLLOW_WAIT = 100  # seconds follow waits for something new, inside the two minutes a tool call gets
STEPS = ["List the calls and claims in the finished work", "Find every other place each one appears",
         "Trace each one through the record", "Code who made each call and how it was warranted",
         "Check where the numbers came from and who typed the text", "Draw the disclosure"]
TOOL_PATHS = ("provenance/", ".claude/", ".claude-plugin/", ".githooks/", "plugin/", "disclosure/", ".gitignore")
WORKING_DOCS = {"readme", "claude", "agents", "gemini", "progress", "log", "plan", "decisions", "changelog",
                "license", "provenance", "notes"}
CODE = {".py", ".r", ".do", ".jl", ".sql", ".ipynb", ".m", ".sas", ".sps"}
TEXT = {".md", ".tex", ".docx", ".qmd", ".rmd", ".txt"}
RESULT_DIRS = ("output", "outputs", "results", "tables", "figures", "out")
# The checklist packs, in the order the map lists them, and the work products
# each one's rows anchor in. Every paper also has a manuscript and references.
PACKS = {
    "quantitative": ["collection", "cleaning", "analysis", "data", "results"],
    "experiments": ["preregistration", "materials", "collection", "cleaning", "analysis", "data", "results"],
    "qualitative": ["protocol", "codebook", "data"],
    "theory": [],
    "tool": ["code", "tests", "documentation", "results"],
}
NEEDS = {"experiments": "quantitative"}  # an experiment also takes the quantitative pack
OLD_TYPES = {"archival": "quantitative", "qualitative": "qualitative", "theory": "theory"}  # maps made before packs
QUAL_WORDS = ("transcript", "interview", "fieldnote", "field-note", "field_note", "codebook", "protocol")
QUAL_EXT = {".nvp", ".nvpx", ".qdpx", ".atlproj", ".mx24"}  # NVivo, ATLAS.ti, MAXQDA projects
EXP_WORDS = ("prereg", "aspredicted", "stimuli", "stimulus", "materials", "qualtrics", "experiment")
EXP_EXT = {".qsf"}  # a Qualtrics survey export
# Tables of data. A codebook beside one documents variables, so it doesn't make
# the paper qualitative (Oct 16: a correlation memo with codebook.md was
# proposed the qualitative pack, in the Codex live test).
TABULAR = {".csv", ".tsv", ".dta", ".sav", ".xlsx", ".xls", ".parquet", ".feather", ".rds"}


def slots_for(packs):
    slots = ["manuscript", "references"]
    for p in packs:
        slots += [s for s in PACKS[p] if s not in slots]
    return slots


def packs_of(slots):
    """The map's packs, with any pack an experiment needs; and names the tool doesn't have."""
    if "packs" in slots:
        names = [n.strip().lower() for n in slots["packs"].split(",") if n.strip()]
    else:
        names = [OLD_TYPES[slots["type"].lower()]] if slots.get("type", "").lower() in OLD_TYPES else []
    names += [NEEDS[n] for n in names if n in NEEDS and NEEDS[n] not in names]
    return [p for p in PACKS if p in names], [n for n in names if n not in PACKS]


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    return r.stdout if r.returncode == 0 else ""


def project_files(repo):
    tracked = git(repo, "ls-files").split("\n")
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").split("\n")
    return sorted(f for f in set(tracked + untracked)
                  if f and not f.startswith(TOOL_PATHS) and (Path(repo) / f).is_file())  # deleted files are still tracked until saved


# The map

def tabular_files(repo):
    """Data tables in the project folder, recorded or not (setup keeps data out
    of the record), outside .git and the tool's own folders."""
    found = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", "provenance", "disclosure", ".claude", "node_modules")
                   and not d.startswith(".")]
        found += [os.path.relpath(os.path.join(root, n), repo) for n in names if Path(n).suffix.lower() in TABULAR]
    return sorted(found)


def propose_map(repo, packs=None):
    """The proposed map, and the files outside it. packs: propose these packs
    instead of guessing them from the files (the demonstrations' runner)."""
    files = project_files(repo)
    top_docs = [f for f in files if "/" not in f and Path(f).suffix.lower() in TEXT
                and Path(f).stem.lower() not in WORKING_DOCS]
    bib = [f for f in files if f.endswith(".bib")]
    code = [f for f in files if Path(f).suffix.lower() in CODE]
    code_dirs = sorted({f.split("/")[0] + "/" if "/" in f else f for f in code})
    named = lambda words: [d for d in code_dirs if any(w in d.lower() for w in words)]
    collection, cleaning = named(("collect", "scrape", "download", "fetch")), named(("clean", "prep", "wrangl"))
    analysis = [d for d in code_dirs if d not in collection + cleaning]
    results = sorted({f.split("/")[0] + "/" for f in files if f.split("/")[0].lower() in RESULT_DIRS})
    top = lambda fs: sorted({f.split("/")[0] + "/" if "/" in f else f for f in fs})
    has = lambda f, words: any(w in f.lower() for w in words)
    tables = tabular_files(repo)
    qual = [f for f in files if has(f, [w for w in QUAL_WORDS if w != "codebook"])
            or Path(f).suffix.lower() in QUAL_EXT or (has(f, ("codebook",)) and not tables)]
    exp = [f for f in files if has(f, EXP_WORDS) or Path(f).suffix.lower() in EXP_EXT]
    packs = packs or ((["quantitative"] if code or exp or tables else []) + (["experiments"] if exp else [])
                      + (["qualitative"] if qual else []) or ["theory"])
    # A codebook or protocol is its own work product, not the manuscript.
    top_docs = [f for f in top_docs if not has(f, ("codebook", "protocol"))]
    data = sorted({d + "/" for d in ("data", "raw", "raw_data", "transcripts", "interviews", "fieldnotes")
                   if (repo / d).is_dir()})
    data += [f for f in tables if "/" not in f]  # a table at the top, outside a data folder
    guess = {"manuscript": top_docs, "references": bib or top_docs, "collection": collection,
             "cleaning": cleaning, "analysis": analysis, "results": results,
             "data": [d + " (not in the record)" if not git(repo, "ls-files", d) else d for d in data],
             "preregistration": [f for f in exp if has(f, ("prereg", "aspredicted"))],
             "materials": top(f for f in exp if has(f, ("stimuli", "stimulus", "materials", "qualtrics"))
                              or Path(f).suffix.lower() in EXP_EXT),
             "protocol": [f for f in qual if has(f, ("protocol", "guide"))],
             "codebook": [f for f in qual if has(f, ("codebook",))]}
    lines = ["# Finished work",
             "#",
             "# The paper plus everything its reported results depend on (DECISIONS.md, Oct 6).",
             "# One line per work product: the files or folders, comma-separated, or none.",
             "# Memos, drafts, and notes are evidence, not finished work: leave them out.",
             "# Proposed by /warrant:disclosure; check it, correct it, and it's saved with",
             "# your next /warrant:attest.",
             "#",
             "# packs: the checklist packs for this kind of paper, added to the spine every",
             "# paper gets (DECISIONS.md, Oct 7): quantitative, experiments (which also",
             "# takes quantitative), qualitative, theory, tool (a paper that builds research",
             "# software). A mixed-methods paper names two.",
             "",
             f"packs: {', '.join(packs)}"]
    lines += [f"{slot}: {', '.join(guess.get(slot, [])) or 'none'}" for slot in slots_for(packs)]
    return "\n".join(lines) + "\n", [f for f in files if not any(_covers(p, f) for v in guess.values() for p in v)]


def read_map(path):
    slots = {}
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            key, _, value = line.partition(":")
            slots[key.strip().lower()] = value.strip()
    return slots


def work_paths(slots):
    paths = []
    for key, value in slots.items():
        if key in ("type", "packs") or value.lower() in ("", "none"):
            continue
        for p in value.split(","):
            p = p.strip()
            if p and "not in the record" not in p and p not in paths:
                paths.append(p)
    return paths


def _covers(pattern, f):
    return f == pattern or (pattern.endswith("/") and f.startswith(pattern))


# Starting a run

def start(repo, plugin, args, narrate=False, agent="claude-code"):
    """Start a run, or say what's needed first. Returns (a reply for the
    author, or None; instructions for Claude, or None): the questions not
    settled yet, or narrating the run. narrate: someone is there to answer
    and watch; headless (claude -p), the run just goes in the background."""
    reply = begin(repo, plugin, args, narrate, agent)
    if isinstance(reply, str):
        return reply, None
    if isinstance(reply, dict):
        return None, reply["ask"]
    out, status, kept = reply
    if narrate:
        return None, narration(plugin, out, status, setup.settings(repo))
    return (kept + f"Generating the {status['kind']} disclosure in the background; it takes a few minutes. "
            f"It will be in disclosure/{out.name}/: disclosure.md, and disclosure.html to view or print. "
            "Keep working; /record shows when it's ready."), None


def begin(repo, plugin, args, ask=False, agent="claude-code"):
    repo, plugin = Path(repo), Path(plugin)
    mp = repo / MAP
    words = args.lower().split()
    if any(w not in ("final", "api", "subscription") for w in words) or {"api", "subscription"} <= set(words):
        return ("Type /disclosure for a draft, or /disclosure final for the version marked final. Add api or "
                "subscription to change how it reaches Claude in this copy.")
    final = "final" in words
    if "api" in words or "subscription" in words:
        setup.git(repo, "config", "--local", setup.READER_KEY, "api" if "api" in words else "headless", check=True)
    chosen, kept = setup.settings(repo), ""
    need_tool = chosen["tool"] is None
    need_reader = chosen["reader"] is None and chosen["tool"] in (None, "claude-code")
    if (need_tool or need_reader) and ask:
        # Asked when it's relevant, not sent back to setup (DECISIONS.md, Oct 16).
        return {"ask": asking(repo, plugin, args, chosen, agent, need_tool)}
    if need_tool or need_reader:
        # Headless: no one to ask, so the defaults, unsaved, so a person is still asked.
        chosen.update(tool=chosen["tool"] or (agent if agent in setup.TOOLS else "claude-code"),
                      reader=chosen["reader"] or "headless")
        kept = (f"No one is here to answer the disclosure's questions, so this run keeps the defaults: "
                f"{setup.TOOLS[chosen['tool']]}" + (", through your Claude subscription" if chosen["tool"] ==
                                                    "claude-code" else "") + ". ")
    if chosen["tool"] != "claude-code":
        # Codex's and Gemini's readers run on the author's own account (DECISIONS.md, Oct 16).
        name, command = setup.TOOLS[chosen["tool"]], chosen["tool"].split("-")[0]
        if not shutil.which(command) and os.environ.get("WD_DISCLOSURE_STUB") != "1":
            return (f"This project uses {name}, so its disclosure runs through {name}, and the {command} command "
                    "isn't on this computer's path. Install it and sign in, or type /setup and choose another tool.")
        backend = chosen["tool"]
    else:
        backend = "api" if chosen["reader"] == "api" else "claude-code"
    if backend == "claude-code" and not shutil.which("claude") and os.environ.get("WD_DISCLOSURE_STUB") != "1":
        return ("The disclosure reaches Claude through Claude Code, and the claude command isn't on this computer's "
                "path. Install Claude Code, or type /disclosure api to use the API instead.")
    if backend == "api" and not setup.has_key() and os.environ.get("WD_DISCLOSURE_STUB") != "1":
        return ("This copy sends the disclosure through the API, and there's no API key in the Keychain. Copy your key "
                "from console.anthropic.com, then in Terminal type  security add-generic-password -U -a \"$USER\" -s "
                f"{setup.KEYCHAIN_ITEM} -w \"$(pbpaste)\"  or type /disclosure subscription to use your Claude "
                "subscription instead.")
    if not mp.exists():
        text, outside = propose_map(repo)
        mp.write_text(text)
        if ask:
            return {"ask": mapping(repo, plugin, args, text, outside, agent)}
        body = [l for l in text.splitlines() if l and not l.startswith("#")]
        return ("First, the finished work and its checklist packs. I proposed this map in provenance/finished-work.md:\n"
                + "\n".join(f"  {l}" for l in body)
                + (f"\n  outside it: {', '.join(outside[:12])}" + (", …" if len(outside) > 12 else "") if outside else "")
                + "\nCheck it and correct anything wrong, then type /disclosure again."
                  " The map is saved with your next /attest.")
    slots = read_map(mp)
    packs, unknown = packs_of(slots)
    if unknown:
        return (f"The finished-work map names packs the tool doesn't have: {', '.join(unknown)}. "
                f"The packs are {', '.join(PACKS)}.")
    if not packs:
        return "The finished-work map doesn't name its checklist packs. Add a line such as  packs: quantitative"
    paths = work_paths(slots)
    missing = [p for p in paths if not (repo / p.rstrip("/")).exists()]
    if not paths:
        return "The finished-work map (provenance/finished-work.md) lists no files. Add the manuscript at least."
    if missing:
        return f"The finished-work map names files that aren't in the project: {', '.join(missing)}. Fix the map first."
    word = [f for f in project_files(repo) if f.lower().endswith(".docx") and any(_covers(p, f) for p in paths)]
    if word and not shutil.which("pandoc"):
        return (f"The finished work includes a Word file ({', '.join(word)}), and reading it needs pandoc. "
                "In Terminal, type  brew install pandoc  (or get the installer from pandoc.org), then /disclosure again.")
    for d in sorted((repo / OUT).glob("*/status.json")):
        s = json.loads(d.read_text())
        if s.get("state") == "running" and _alive(s.get("pid")):
            return f"A disclosure is already being generated ({d.parent.name}). /record shows when it's ready."
    # The author opts in to what the disclosure sends where, before anything is
    # sent; asked again if the provider or the path changes (DECISIONS.md, Oct 16).
    key = setup.provider(dict(chosen, reader=None if backend != "api" else "api"))
    if chosen["consent"] != key:
        if not ask:
            who, how = setup.PROVIDERS[key]
            return (f"This disclosure would send your finished work and your record to {who}, through {how}, and you "
                    "haven't agreed to that in this copy. Type /disclosure in Claude Code, where it asks.")
        return {"ask": consenting(repo, plugin, args, key, agent)}
    tag = None
    if final:
        tag = git(repo, "tag", "--list", "final-*", "--sort=-creatordate").split("\n")[0].strip()
        if not tag:
            return "There's no final version yet. Mark one with /attest final, or type /disclosure for a draft."
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S") + ("-final" if final else "")
    out = repo / OUT / stamp
    out.mkdir(parents=True)
    head = git(repo, "rev-parse", "--short", "HEAD").strip() or "none"
    dirty = bool(git(repo, "status", "--porcelain", "--", *paths).strip())
    label = (f"Final version, {tag} (commit {git(repo, 'rev-parse', '--short', tag + '^{commit}').strip()})" if final
             else f"Draft, not attested: the work as of {datetime.now():%Y-%m-%d %H:%M}, last save {head}"
             + (", with unsaved changes" if dirty else ""))
    status = {"state": "running", "started": datetime.now().isoformat(timespec="seconds"),
              "kind": "final" if final else "draft", "label": label, "work": paths, "packs": packs, "tag": tag,
              "backend": backend}
    (out / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    log = open(out / "job.log", "w")
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "job", str(repo), str(plugin), str(out)],
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, close_fds=True)
    status["pid"] = proc.pid
    (out / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    return out, status, kept


def consenting(repo, plugin, args, key, agent):
    """What Claude is told to do before anything is sent: say what goes where,
    and ask the author to agree (DECISIONS.md, Oct 16)."""
    scripts = Path(plugin) / "scripts"
    who, how = setup.PROVIDERS[key]
    return "\n".join([
        "warrant:disclosure. Before anything is sent, the author has to agree to what the disclosure sends where "
        "(DECISIONS.md, Oct 16).",
        f'1. Tell the author, in these words: "The disclosure sends your finished work and your record (your prompts, '
        f"the tool's replies, its tool outputs, and the changes to your files, including any text you've withheld) to "
        f'{who}, through {how}, for the reader to code. Nothing is sent until you agree."',
        "2. Ask with your question tool if you have one (AskUserQuestion in Claude Code), otherwise in plain words: "
        f'"Send your work and record to {who} for this disclosure and later ones?" Options: "Yes, send them" '
        "(Remembered for this copy. Each disclosure reminds you, and asks again if the provider or the path "
        'changes.); "No, don\'t send them" (No disclosure runs.). Don\'t recommend either.',
        "3. If the answer is yes, run:",
        f'   python3 "{scripts / "setup.py"}" save "{repo}" consent={key}',
        "   then start the disclosure by running:",
        f'   python3 "{scripts / "disclose.py"}" start "{repo}" {agent}' + (f" {args.strip()}" if args.strip() else ""),
        "   and follow what it prints, as before: pass a message on in plain words and stop, or follow instructions "
        "beginning \"warrant:disclosure.\" exactly.",
        "4. If the answer is no, tell the author that no disclosure ran and nothing was sent, and stop.",
    ])


def asking(repo, plugin, args, chosen, agent, need_tool):
    """What Claude is told to do when something isn't settled: ask, save the
    answers, then start the run."""
    scripts = Path(plugin) / "scripts"
    tool = "" if need_tool else f"tool={chosen['tool']} "
    return "\n".join([
        "warrant:disclosure. Before the disclosure can run, the author has to decide "
        + ("which tool this project uses and, for Claude Code, " if need_tool else "")
        + "how the disclosure reaches Claude. Ask now, while it's relevant, so the choice is theirs and clear "
        "(DECISIONS.md, Oct 16).",
        "1. " + setup.ASK,
        *(["   a. " + setup.ask_tool(chosen, agent), "   b. Only if the answer is Claude Code: " + setup.ask_reader(chosen)]
          if need_tool else ["   a. " + setup.ask_reader(chosen)]),
        "2. Save the answers by running this command, filled in: "
        + ("tool is claude-code, codex-cli, or gemini-cli; for Claude Code, " if need_tool else "")
        + "reader is headless (the subscription) or api" + ("; for Codex or Gemini, leave reader out." if need_tool else "."),
        f'   python3 "{scripts / "setup.py"}" save "{repo}" {tool or "tool=... "}reader=...',
        "3. Then start the disclosure by running:",
        f'   python3 "{scripts / "disclose.py"}" start "{repo}" {agent}' + (f" {args.strip()}" if args.strip() else ""),
        "   It prints either a message for the author, which you pass on in plain words, and then stop; or "
        "instructions beginning \"warrant:disclosure.\", which you follow exactly.",
    ])


def mapping(repo, plugin, args, text, outside, agent):
    """What Claude is told to do with the proposed map: walk the author through
    it in the chat, in plain words, and save their changes, so no one has to
    edit the file (DECISIONS.md, Oct 23)."""
    scripts = Path(plugin) / "scripts"
    body = [l for l in text.splitlines() if l and not l.startswith("#")]
    return "\n".join([
        "warrant:disclosure. First, what the disclosure covers: the finished work, meaning the paper plus everything "
        "its reported results depend on, and the checklist packs for this kind of paper. The plugin proposed it from "
        "the project's files and saved it in provenance/finished-work.md. Walk the author through it here, in plain "
        "words, so they never have to edit the file (DECISIONS.md, Oct 23). The proposal:",
        *(f"   {l}" for l in body),
        *([f"   outside it: {', '.join(outside[:12])}" + (", …" if len(outside) > 12 else "")] if outside else []),
        "1. Tell the author in plain words what you take the finished work to be: the kind of paper (the packs), the "
        "manuscript, then each other part that has files, such as the code that collects, cleans, or analyzes the "
        "data, the data, the results, or a preregistration, one short line each with its files. Skip the parts that "
        "are none. Then say in one line what is left outside it; memos, drafts, and notes are evidence, not finished "
        "work. Don't show the file.",
        "2. Ask whether that's right, or what to add, drop, or move. Wait for the answer, and take changes in plain "
        "words.",
        "3. Edit provenance/finished-work.md to match. Keep its comment lines and its slots; each slot takes its "
        "files, comma-separated, or none. The packs are " + ", ".join(PACKS) + "; experiments also takes "
        "quantitative, and a mixed-methods paper names two.",
        "4. Say the result back in plain words, and ask again. Repeat until the author says it's right. The map is "
        "saved with their next /attest, so the record shows it.",
        "5. Then start the disclosure by running:",
        f'   python3 "{scripts / "disclose.py"}" start "{repo}" {agent}' + (f" {args.strip()}" if args.strip() else ""),
        "   It prints either a message for the author, which you pass on in plain words, and then stop; or "
        "instructions beginning \"warrant:disclosure.\", which you follow exactly.",
    ])


def narration(plugin, out, status, chosen):
    """What Claude is told to do: narrate the run so the author sees it unfold
    (DECISIONS.md, Oct 16), without reading or judging anything itself."""
    how = {"api": "the API, billed to your own key", "codex-cli": "Codex, on your own account",
           "gemini-cli": "Gemini, on your own account"}.get(status.get("backend"),
                                                             "your Claude subscription, with no API key")
    who = setup.PROVIDERS.get(chosen.get("consent"), ("the reader's provider",))[0]
    model = {"codex-cli": "OpenAI's model", "gemini-cli": "Google's model"}.get(status.get("backend"), "Claude")
    return "\n".join([
        f"warrant:disclosure. The warrant plugin started the {status['kind']} disclosure ({status['label']}). "
        f"The reader, a fixed script, runs it in the background, reaching {model} through {how}. Narrate it so the "
        "author sees the process as it unfolds (DECISIONS.md, Oct 16). You don't read, judge, or change anything "
        "yourself.",
        "1. Make a task list of these six steps (use your task list tool if you have one):",
        *[f"   {i}. {s}" for i, s in enumerate(STEPS, 1)],
        "2. Remind the author, in one sentence, of what they agreed to: \"This disclosure sends your finished work "
        f"and record to {who} through {how}, as you agreed on {chosen.get('consent_date') or 'an earlier day'}.\"",
        f"   Then tell the author in one sentence that it has started, that it reaches {model} through "
        f"{how}" + (f" (/disclosure {'subscription' if status.get('backend') == 'api' else 'api'} changes that for "
                     "next time)" if status.get("backend") in ("api", "claude-code") else "")
        + ", and that it takes a few minutes, longer for a large project.",
        "3. Run this command, and run it again each time it returns, until it says the run is done, failed, or stopped:",
        f'   python3 "{Path(plugin) / "scripts" / "disclose.py"}" follow "{out}"',
        "   Each time, it prints what has happened since the last time, in plain words, after waiting up to two "
        "minutes for something new. Pass each new line on to the author as one short sentence, and mark each "
        "finished step done. When it says only that a step is still going, say nothing and run it again.",
        "4. When it's done, tell the author where the disclosure is and give the summary lines it printed, word for "
        "word. If it failed or stopped, say what it printed. Do nothing else in this turn.",
    ])


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


# The background job

def job(repo, plugin, out):
    repo, plugin, out = Path(repo), Path(plugin), Path(out)
    status = json.loads((out / "status.json").read_text())
    tmp = Path(tempfile.mkdtemp(prefix="warrant-disclosure-"))
    try:
        copy = snapshot(repo, tmp / "project", status.get("tag"))
        if not (copy / MAP).exists():
            (copy / MAP).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / MAP, copy / MAP)
        mp = copy / MAP
        work, converted = convert_word(copy, mp, status["work"])
        status["converted"] = converted
        keep_manuscript(copy, mp, out)
        if os.environ.get("WD_DISCLOSURE_STUB") == "1":
            for step, line in zip(("list", "places", "trace", "code", "numbers", "draw"), STEPS):
                progress(out, step, line + ".")
            (out / "disclosure.md").write_text(f"# Who made the calls in this work\n\n*{status['label']}. "
                                               "Placeholder written for testing; the reader was not called.*\n\n"
                                               f"**Checklists:** the spine, plus packs: {', '.join(status['packs'])}.\n"
                                               + (f"\n*Converted from Word for reading: {', '.join(converted)}.*\n" if converted else ""))
        else:
            backend = status.get("backend", "api")
            python = reader_python() if backend == "api" else Path(sys.executable)
            r = subprocess.run([str(python), str(Path(__file__).resolve()), "read", str(out), str(copy),
                                "--work", *work, "--packs", *status["packs"], "--out", str(out), "--map", str(mp),
                                "--label", status["label"], *(["--converted", *converted] if converted else []),
                                "--backend", backend],
                               capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1][:300])
        import withhold  # withheld text stays out of the run's own files (DECISIONS.md, Oct 16)
        withhold.redact_run(out, repo)
        run = json.loads((out / "reader-run.json").read_text()) if (out / "reader-run.json").exists() else {}
        status.update(state="done", finished=datetime.now().isoformat(timespec="seconds"),
                      cost_usd=run.get("cost_usd"))
    except Exception as exc:
        status.update(state="failed", finished=datetime.now().isoformat(timespec="seconds"), error=str(exc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        (out / "status.json").write_text(json.dumps(status, indent=1) + "\n")


def keep_manuscript(copy, mp, out):
    """The manuscript as it was read, saved with the run, so /trail can draw
    it later even after the work changes (a Word file as its converted text)."""
    for f in [x.strip() for x in read_map(mp).get("manuscript", "").split(",")]:
        src = copy / f
        if f and f.lower() != "none" and src.is_file():
            (out / "manuscript" / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / "manuscript" / f)


def convert_word(copy, mp, work):
    """Convert each Word file in the finished work to text, in the copy: paper.docx
    becomes paper.docx.md, which the map and the work list then name instead."""
    files = git(copy, "ls-files", "--cached", "--others", "--exclude-standard", "--", *work).split("\n") if work else []
    word = [f for f in files if f.lower().endswith(".docx")]
    for f in word:
        subprocess.run(["pandoc", "-f", "docx", "-t", "gfm", "--wrap=none", "-o", str(copy / (f + ".md")), str(copy / f)],
                       check=True, capture_output=True, timeout=300)
        git(copy, "add", "-f", f + ".md")  # in the throwaway copy only, so the reader lists it
    if word:
        text = mp.read_text()
        for f in word:
            text = re.sub(rf"(?<![\w./-]){re.escape(f)}(?![\w.])", f + ".md", text)
        mp.write_text(text)
    return [f + ".md" if f in word else f for f in work], word


def snapshot(repo, dest, tag):
    """A stable copy to read: the project at a tag, or as it stands now
    (the last save plus unsaved changes), with its record and snapshots."""
    subprocess.run(["git", "clone", "-q", str(repo), str(dest)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "-q", str(repo), "refs/provenance/*:refs/provenance/*",
                    "refs/provenance-remote/*:refs/provenance-remote/*"], capture_output=True)
    if tag:
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", tag], check=True, capture_output=True)
        return dest
    # Every change since the last save, staged or not, and every new file; a
    # file deleted since is deleted from the copy too.
    changed = (git(repo, "diff", "--name-only", "HEAD").split("\n")
               + git(repo, "ls-files", "--others", "--exclude-standard").split("\n"))
    for f in filter(None, changed):
        src = repo / f
        if src.is_file():
            (dest / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / f)
        elif (dest / f).is_file():
            (dest / f).unlink()
    for log in (repo / "provenance" / "log").rglob("*"):
        if log.is_file():
            target = dest / log.relative_to(repo)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(log, target)
    return dest


# Following the run (DECISIONS.md, Oct 16)

def progress(out, step, line):
    with open(Path(out) / PROGRESS, "a") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "step": step, "line": line}) + "\n")


def read(out, args):
    """Run the reader, as `reader.py ARGS` would, writing a plain line to
    progress.jsonl as each of its steps starts. The reader's file is
    unchanged, so its fingerprint in the run details is the validated one;
    its steps are wrapped from outside."""
    sys.argv = [str(HERE / "reader.py"), *args]
    import reader
    instrument(reader, out)
    reader.main()


def instrument(reader, out):
    say = lambda step, line: progress(out, step, line)
    real = {k: getattr(reader, k) for k in ("locate", "places", "trace", "code", "call")}
    write, numbers = reader.render.write, reader.trace_numbers.summarize
    batch = {"step": None, "n": 0, "of": 0}

    def locate(client, project, work, usage, packs=None):
        say("list", "Listing the calls and claims in the finished work.")
        return real["locate"](client, project, work, usage, packs)

    def places(client, project, parts, units, usage):
        decisions = sum(u["kind"] == "decision" for u in units)
        say("places", f"Found {decisions} calls and {len(units) - decisions} claims in {len(parts)} "
                      f"file{'s' if len(parts) != 1 else ''}. Finding every other place each one appears.")
        batch.update(step=None)
        return real["places"](client, project, parts, units, usage)

    def trace(project, units, turns, first_seen):
        say("trace", f"Tracing each of the {len(units)} through the record, {len(turns)} turns.")
        return real["trace"](project, units, turns, first_seen)

    def code(client, project, files, units, turns, usage):
        n = -(-len(units) // reader.BATCH)
        say("code", f"Coding who made each call and how it was warranted, in {n} batch{'es' if n != 1 else ''}.")
        batch.update(step="code", n=0, of=n)
        try:
            return real["code"](client, project, files, units, turns, usage)
        finally:
            batch.update(step=None)

    def call(client, system, content, schema, max_tokens, usage):
        if batch["step"] == "code":
            batch["n"] += 1
            say("code", f"Coding: batch {batch['n']} of {batch['of']}." if batch["n"] <= batch["of"] else
                "Asking again about the units the first pass left out.")
        return real["call"](client, system, content, schema, max_tokens, usage)

    def summarize(*args, **kwargs):
        say("numbers", "Checking where the numbers came from and who typed the text.")
        return numbers(*args, **kwargs)

    def draw(*args, **kwargs):
        say("draw", "Drawing the disclosure.")
        return write(*args, **kwargs)

    reader.locate, reader.places, reader.trace, reader.code, reader.call = locate, places, trace, code, call
    reader.trace_numbers.summarize, reader.render.write = summarize, draw


def follow(out, wait=FOLLOW_WAIT):
    """Wait for the run's next step, up to `wait` seconds, and print what has
    happened since the last time, in plain words; at the end, a summary."""
    out = Path(out)
    pos = out / "follow.pos"
    seen = int(pos.read_text()) if pos.exists() else 0
    deadline = time.time() + wait
    while True:
        status = json.loads((out / "status.json").read_text())  # before the lines, so a finished run's are all there
        lines = [json.loads(l) for l in (out / PROGRESS).read_text().splitlines() if l.strip()] \
            if (out / PROGRESS).exists() else []
        alive = status.get("state") != "running" or _alive(status.get("pid"))
        if lines[seen:] or status.get("state") != "running" or not alive or time.time() >= deadline:
            break
        time.sleep(1)
    finished = status.get("state") != "running" or not alive
    if finished:
        pos.unlink(missing_ok=True)  # nothing left to follow, and nothing to save with the run
    else:
        pos.write_text(str(len(lines)))
    said = [l["line"] for l in lines[seen:]]
    if status.get("state") == "done":
        said += summary(out, status)
    elif status.get("state") == "failed":
        said.append(f"The run failed: {status.get('error')}")
    elif not alive:
        said.append("The run stopped without finishing. Type /disclosure to start it again.")
    elif not said:
        said.append("Still going: " + (lines[-1]["line"] if lines else "starting.")
                    + " (Nothing new; run this again.)")
    print("\n".join(said))


def summary(out, status):
    started, finished = (datetime.fromisoformat(status[k]) for k in ("started", "finished"))
    minutes = max(1, round((finished - started).total_seconds() / 60))
    cost = (f", about ${status['cost_usd']} on your API key" if status.get("backend") == "api"
            and status.get("cost_usd") is not None else {"claude-code": ", on your Claude subscription",
                                                          "codex-cli": ", on your Codex account",
                                                          "gemini-cli": ", on your Gemini account"}.get(status.get("backend"), ""))
    lines = [f"Done in about {minutes} minute{'s' if minutes != 1 else ''}{cost}. The disclosure is in "
             f"disclosure/{out.name}/: disclosure.md, and disclosure.html to view or print."]
    try:
        import render
        units = json.loads((out / "units.json").read_text())["units"]
        _, decisions, claims = render.tally(units, json.loads((out / "codes.json").read_text()))
    except Exception:
        return lines
    made = sum(r["discretion"] == "kept" for r in decisions)
    handed = [r for r in decisions if r["discretion"] in ("given", "taken")]
    warranted = sum(r["certification"] in render.WARRANTED for r in handed)
    checked = sum(r["certification"] in render.CHECKED for r in claims)
    lines.append(f"Judgment calls: {len(decisions)}. You made {made} ({render.pct(made, len(decisions))}); "
                 f"{len(handed)} were handed to the tool, and you changed or accepted {warranted} of those.")
    lines.append(f"Verifiable claims: {len(claims)}. {checked} were checked ({render.pct(checked, len(claims))}).")
    return lines


def reader_python():
    home = Path(os.environ.get("WD_HOME", Path.home() / ".warranted-delegation"))
    python = home / "venv" / "bin" / "python"
    if not (python.exists() and subprocess.run([str(python), "-c", "import anthropic"]).returncode == 0):
        subprocess.run([sys.executable, "-m", "venv", str(home / "venv")], check=True, capture_output=True)
        subprocess.run([str(python), "-m", "pip", "install", "--quiet", "anthropic"], check=True, capture_output=True)
    return python


# For /warrant:record

def latest(repo):
    runs = sorted((Path(repo) / OUT).glob("*/status.json"))
    if not runs:
        return None
    d = runs[-1]
    s = json.loads(d.read_text())
    where = f"disclosure/{d.parent.name}/disclosure.md"
    if s.get("state") == "running":
        return (f"Disclosure: being generated since {s['started'][11:16]}." if _alive(s.get("pid"))
                else f"Disclosure: the run started at {s['started'][11:16]} stopped without finishing; type /disclosure again.")
    if s.get("state") == "failed":
        return f"Disclosure: the last run failed: {s.get('error')}"
    cost = f", about ${s['cost_usd']}" if s.get("cost_usd") is not None else ""
    return f"Latest disclosure: {where}, and disclosure.html beside it ({s['kind']}{cost})."


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "job":
        job(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "follow":
        follow(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "start":
        # After Claude has asked the questions and saved the answers.
        reply, context = start(sys.argv[2], HERE.parent, " ".join(sys.argv[4:]), narrate=True, agent=sys.argv[3])
        print(setup.named(context or reply, sys.argv[3]))
    elif len(sys.argv) > 3 and sys.argv[1] == "read":
        read(sys.argv[2], sys.argv[3:])
