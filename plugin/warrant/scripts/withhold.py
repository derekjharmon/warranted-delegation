"""/warrant:withhold: mark entries whose text the review copy leaves out
(DECISIONS.md, Oct 12 and Oct 16).

    /warrant:withhold salary      find every entry containing "salary"
    /warrant:withhold T12         every entry in turn 12
    /warrant:withhold 1 3 5       leave out those of the matches just shown
    /warrant:withhold all         leave out all of them
    /warrant:withhold             what's left out so far

Run by the plugin's hook, which shows the matches to the person directly:
Claude never sees them, so the text isn't copied into new parts of the
record. An entry is a prompt, a reply of Claude's, or a tool's output; each
is a text file beside the log, named by its fingerprint. Withholding writes
the fingerprint to provenance/withheld.json, which the next /warrant:attest
saves. Nothing is deleted: the record and the author's own disclosure keep
everything. /warrant:release leaves those texts out of the review copy, and
the record still verifies there, since a missing text counts as withheld.
Each disclosure's own files show "[withheld]" in their place: the transcript
saved with the run, and the trail drawn from it. The reader still reads
everything, so coding is unaffected; a code that relies on a turn with
withheld text gets the basis "[rests partly on withheld text]", since a basis
can paraphrase (DECISIONS.md, Oct 16). Runs already made are redacted when
something is withheld, and each new run as it finishes.
The search's own prompt holds the searched-for text, so confirming a search
withholds that prompt too. The record's lines keep each command's first 500
characters and the names of files; those stay in the copy, and the reply
says when a match is in one.
"""
import json
import re
from datetime import datetime
from pathlib import Path

WITHHELD = Path("provenance") / "withheld.json"
OUT = Path("disclosure")
MARK, BASIS = "[withheld]", "[rests partly on withheld text]"
PENDING = "wd-withhold.json"  # in .git: the matches last shown, until confirmed
KINDS = {"prompt_sha256": "your prompt", "response_sha256": "Claude's reply", "output_sha256": "a tool's output"}
SHOWN = 30


def entries(repo):
    """Every entry with its own text: (turn, kind, fingerprint), numbered as the reader numbers turns."""
    repo = Path(repo)
    events = []
    for log in sorted((repo / "provenance" / "log").glob("*/events.jsonl")):
        events += [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    out, turn, by_prompt = [], 0, {}
    for e in events:
        if e.get("event") == "UserPromptSubmit":
            turn += 1
            if e.get("prompt_id"):
                by_prompt[e["prompt_id"]] = turn
        n = by_prompt.get(e.get("prompt_id"), turn)
        for field, kind in KINDS.items():
            if e.get(field):
                out.append({"turn": n, "kind": kind, "sha256": e[field]})
    return out, events


def text_of(repo, sha):
    path = Path(repo) / "provenance" / "log" / "text" / f"{sha}.txt"
    return path.read_text(errors="replace") if path.exists() else None


def withheld(repo):
    try:
        return json.loads((Path(repo) / WITHHELD).read_text())
    except Exception:
        return {"entries": []}


def snippet(text, term):
    i = text.lower().find(term.lower())
    a, b = max(0, i - 50), min(len(text), i + len(term) + 50)
    return ("…" if a else "") + re.sub(r"\s+", " ", text[a:b]) + ("…" if b < len(text) else "")


def run(repo, git_dir, args, prompt_sha=None):
    repo, args = Path(repo), args.strip()
    pending_file = Path(git_dir) / PENDING if git_dir else None
    done = withheld(repo)
    have = {e["sha256"] for e in done["entries"]}
    if not args:
        if not done["entries"]:
            return "Nothing is withheld yet. Type /withhold and a word, such as /withhold salary, to find entries."
        turns = sorted({e["turn"] for e in done["entries"]})
        return (f"Withheld from the review copy: {len(done['entries'])} entries, in turns "
                f"{', '.join(f'T{t}' for t in turns[:40])}{', …' if len(turns) > 40 else ''}. They stay in your "
                "record and your disclosure.")
    if re.fullmatch(r"(all|\d+(\s+\d+)*)", args, re.I):
        try:
            pending = json.loads(pending_file.read_text())
        except Exception:
            return "Search first: type /withhold and a word, or a turn such as T12."
        picks = (list(range(1, len(pending["matches"]) + 1)) if args.lower() == "all"
                 else [int(x) for x in args.split()])
        bad = [p for p in picks if not 1 <= p <= len(pending["matches"])]
        if bad:
            return f"There's no match numbered {', '.join(map(str, bad))}; the last search showed {len(pending['matches'])}."
        chosen = [pending["matches"][p - 1] for p in picks] + (
            [{"turn": pending["search_turn"], "kind": "your prompt", "sha256": pending["search_sha"]}]
            if pending.get("search_sha") else [])
        new = [dict(m, withheld=datetime.now().isoformat(timespec="seconds")) for m in chosen if m["sha256"] not in have]
        done["entries"] += new
        (repo / WITHHELD).write_text(json.dumps(done, indent=1) + "\n")
        pending_file.unlink(missing_ok=True)
        runs = redact_all(repo)
        return (f"Withheld {len(new)} entr{'y' if len(new) == 1 else 'ies'} from the review copy"
                + (", including the search's own prompt" if pending.get("search_sha") and pending["search_sha"] not in have else "")
                + (f", and from the files of {runs} disclosure run{'s' if runs != 1 else ''} already made" if runs else "")
                + ". They stay in your record, and the reader still reads them. Your next /attest saves the list.")
    all_entries, events = entries(repo)
    m = re.fullmatch(r"T(\d+)", args, re.I)
    if m:
        matches = [e for e in all_entries if e["turn"] == int(m.group(1))]
        what, term = f"in turn {m.group(1)}", None
    else:
        term = args.strip('"\'')
        matches = [e for e in all_entries if term.lower() in (text_of(repo, e["sha256"]) or "").lower()
                   and e["sha256"] != prompt_sha]
        what = f'containing "{term}"'
    matches = [e for e in matches if e["sha256"] not in have]
    if not matches:
        return f"No entries {what} that aren't already withheld."
    in_lines = sum(1 for e in events if term and term.lower() in (e.get("command") or "").lower()) if term else 0
    current = next((e.get("turn") for e in all_entries if e["sha256"] == prompt_sha), None)
    if pending_file:
        pending_file.write_text(json.dumps({"matches": matches, "search_sha": prompt_sha if term else None,
                                            "search_turn": current}))
    lines = [f"{len(matches)} entr{'y' if len(matches) == 1 else 'ies'} {what}:"]
    for i, e in enumerate(matches[:SHOWN], 1):
        text = text_of(repo, e["sha256"]) or ""
        lines.append(f"  {i}. T{e['turn']}, {e['kind']}: {snippet(text, term) if term else re.sub(chr(10), ' ', text[:100])}")
    if len(matches) > SHOWN:
        lines.append(f"  … and {len(matches) - SHOWN} more (all of them are included in 'all').")
    lines.append("Type /withhold followed by the numbers to leave out of the review copy (such as /withhold 1 3), or "
                 "/withhold all. Nothing changes until you do.")
    if in_lines:
        lines.append(f"Note: the text also appears in {in_lines} command line{'s' if in_lines != 1 else ''} in the "
                     "record, which the review copy keeps.")
    return "\n".join(lines)


# The disclosure's own files

def forms(text):
    """The forms a text takes in the reader's transcript: whole, cut to the
    reply limit, shortened, or squashed as a tool's output."""
    import reader
    squashed = reader.squash(text)
    return {f for f in (text.strip(), text.strip()[:reader.REPLY_CAP], text.strip()[:600], squashed[:reader.OUTPUT_CAP],
                        squashed) if len(f) >= 12}


def redact_run(out, repo):
    """Put [withheld] in place of withheld text in one disclosure run's
    files; returns whether anything changed."""
    out, entries_ = Path(out), withheld(repo)["entries"]
    if not entries_ or not (out / "transcript.txt").exists():
        return False
    texts = [x for x in (text_of(repo, e["sha256"]) for e in entries_) if x]
    record = original = (out / "transcript.txt").read_text()
    for f in sorted({f for x in texts for f in forms(x)}, key=len, reverse=True):
        record = record.replace(f, MARK)
    changed = record != original
    (out / "transcript.txt").write_text(record)
    turns = {e["turn"] for e in entries_}
    if (out / "codes.json").exists():
        codes = json.loads((out / "codes.json").read_text())
        for c in codes.values():
            cited = {int(n) for n in re.findall(r"T(\d+)", c.get("turns") or "")}
            if cited & turns and c.get("basis") != BASIS:
                c["basis"], changed = BASIS, True
        (out / "codes.json").write_text(json.dumps(codes, indent=1) + "\n")
    if changed and (out / "trail.html").exists():
        import trail
        trail.build(out, repo)
    return changed


def redact_all(repo):
    return sum(redact_run(d, repo) for d in sorted((Path(repo) / OUT).glob("*/")))
