"""/warrant:setup: set a project up for warranted delegation.

Run by the plugin's hook when the human types /warrant:setup. It never
commits. Safe to run again: each step skips what is already done. After the
steps below, the hook hands setup's questions to Claude, which asks them and
saves the answers with the save command below, so the author's choices are
prompted and clear, when they're relevant (DECISIONS.md, Oct 16). Setup asks
about recording: which tool the project uses, which the disclosure's reader
runs on, saved with the project; and, for Claude Code, whether the record
keeps Claude's memory notes, for this copy only. The first disclosure in a
copy asks whether it reaches Claude through the author's subscription or the
API (disclose.py). Headless Claude Code (claude -p), started by a script with
no one to answer, keeps the defaults and says so.

    /warrant:setup                         set up this folder
    /warrant:setup Your Name <you@uni.edu> also set git's name and email, if missing
    /warrant:setup memory off              stop keeping Claude's memory notes in this copy's record
    /warrant:setup memory on               keep them again (the default)

    setup.py save PROJECT tool=claude-code|codex-cli|gemini-cli [reader=headless|api] [memory=on|off]
                                           save the answers to setup's questions

Steps:
1. git: start a repository here if there isn't one, and check that git knows
   who you are (your attestations are signed with that name).
2. The record: provenance/log/ (recording starts once it exists),
   provenance/verify_log.py (so anyone can check the record without the
   plugin), and the git hooks that require a signature on every commit.
3. Data stays out of the record: a marked block in .gitignore for common
   data folders and formats.
4. The project's .claude/settings.json: names this plugin, so a coauthor who
   opens a copy is prompted to install it, keeps Claude from committing or
   pushing, and drops hooks from the older, copied-in install.
5. GitHub: a private repository for the project, if you are logged in to
   GitHub's command-line tool. If not, it says how, and setup can be run
   again. A copy that already has an online home is left as it is.

For testing: WD_SETUP_SKIP_GITHUB=1 skips step 5.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

MARKETPLACE = "warranted-delegation"
MARKETPLACE_REPO = "anonymous.invalid/warranted-delegation"
PLUGIN_ID = f"warrant@{MARKETPLACE}"
DENY = ["Bash(git commit *)", "Bash(git push *)"]
MEMORY_KEY = "wd.capturememory"  # as in capture.py
SETTINGS = Path("provenance") / "settings.json"  # saved with the project: the tool it uses
READER_KEY = "wd.readerpath"  # this copy: "headless" (the default) or "api"
CONSENT_KEY = "wd.consent"  # this copy: what the author agreed the disclosure may send where, and when
PROVIDERS = {"anthropic-subscription": ("Anthropic", "your Claude subscription"),
             "anthropic-api": ("Anthropic", "the API, with your own key"),
             "openai": ("OpenAI", "your Codex account"), "google": ("Google", "your Gemini account")}
TOOLS = {"claude-code": "Claude Code", "codex-cli": "Codex", "gemini-cli": "Gemini"}
KEYCHAIN_ITEM = "warranted-delegation-anthropic"  # as in reader.py
GITIGNORE_MARK = "# --- warranted delegation: data stays out of the record and off GitHub."
GITIGNORE_BLOCK = GITIGNORE_MARK + """
# Delete a line to record that kind of file. Files over 25 MB are always left out.
data/
raw/
raw_data/
*.dta
*.sav
*.sas7bdat
*.rds
*.RData
*.parquet
*.feather
*.h5
*.pkl
*.zip
# --- end warranted delegation
"""


def git(repo, *args, check=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])}: {r.stderr.strip()}")
    return r


def memory_switch(repo, setting):
    """Turn capture of Claude's memory notes off or on for this copy."""
    if not (repo / "provenance" / "log").is_dir():
        return "Set this project up first: type /setup."
    git(repo, "config", "--local", MEMORY_KEY, setting, check=True)
    if setting == "off":
        return ("Memory capture off for this copy. From now on the record doesn't keep Claude's memory notes "
                "for this project, and says that it doesn't. Notes it already kept stay in the record. "
                "Type /setup memory on to turn it back on.")
    return ("Memory capture on for this copy. From now on the record keeps Claude's memory notes for this "
            "project: the MEMORY.md index and the notes.")


def run(repo, plugin, args):
    """Set the project up. Returns the report and whether every step is done,
    so the questions can follow."""
    repo, plugin = Path(repo), Path(plugin)
    if re.match(r"memory\b", args.strip(), re.I):
        m = re.fullmatch(r"memory\s+(on|off)", args.strip(), re.I)
        if not m:
            return "Type /setup memory off or /setup memory on.", False
        return memory_switch(repo, m.group(1).lower()), False
    report = steps(repo, plugin, args)
    return report, report.startswith(("Set up for warranted delegation", "Already set up"))


def steps(repo, plugin, args):
    done, notes = [], []

    # 1. git and identity
    if shutil.which("git") is None:
        return "Setup needs git. On a Mac, run xcode-select --install in Terminal, then /setup again."
    if git(repo, "rev-parse", "--is-inside-work-tree").returncode:
        git(repo, "init", "-q", "-b", "main", check=True)
        done.append("started a git repository here")
    top = Path(git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != repo.resolve():
        return f"Open Claude Code in the project's top folder ({top}) and run /setup there."
    name = git(repo, "config", "user.name").stdout.strip()
    email = git(repo, "config", "user.email").stdout.strip()
    if not (name and email):
        m = re.fullmatch(r"(.+?)\s*<([^<>\s]+@[^<>\s]+)>", args)
        if not m:
            return ("Git doesn't know your name and email yet; your attestations are signed with them. "
                    "Type /setup Your Name <you@example.edu>, using the email on your GitHub account.")
        name, email = m.group(1).strip(), m.group(2)
        git(repo, "config", "--global", "user.name", name, check=True)
        git(repo, "config", "--global", "user.email", email, check=True)
        done.append(f"set git's name and email to {name} <{email}>")

    # 2. The record and the commit rules
    (repo / "provenance" / "log").mkdir(parents=True, exist_ok=True)
    for src, dst in ((plugin / "scripts" / "verify_log.py", repo / "provenance" / "verify_log.py"),
                     (plugin / "githooks" / "commit-msg", repo / ".githooks" / "commit-msg"),
                     (plugin / "githooks" / "prepare-commit-msg", repo / ".githooks" / "prepare-commit-msg")):
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            done.append(f"added {dst.relative_to(repo)}")
        elif dst.read_bytes() != src.read_bytes():
            notes.append(f"kept your existing {dst.relative_to(repo)}, which differs from the plugin's")
    for hook in ("commit-msg", "prepare-commit-msg"):
        os.chmod(repo / ".githooks" / hook, 0o755)
    if git(repo, "config", "core.hooksPath").stdout.strip() != ".githooks":
        git(repo, "config", "core.hooksPath", ".githooks", check=True)
        done.append("turned on the commit rules (every commit needs an Attested-by line)")

    # 3. Data stays out
    gi = repo / ".gitignore"
    text = gi.read_text() if gi.exists() else ""
    if GITIGNORE_MARK not in text:
        gi.write_text(text + ("\n" if text and not text.endswith("\n") else "") + GITIGNORE_BLOCK)
        done.append("kept common data folders and formats out of the record (.gitignore)")

    # 4. The project's Claude Code settings
    sp = repo / ".claude" / "settings.json"
    settings = json.loads(sp.read_text()) if sp.exists() else {}
    before = json.dumps(settings, sort_keys=True)
    if not MARKETPLACE_REPO.split("/")[0].endswith(".invalid"):  # the review copy: installed from the copy itself
        settings.setdefault("extraKnownMarketplaces", {})[MARKETPLACE] = {
            "source": {"source": "github", "repo": MARKETPLACE_REPO}}
    settings.setdefault("enabledPlugins", {})[PLUGIN_ID] = True
    deny = settings.setdefault("permissions", {}).setdefault("deny", [])
    deny += [rule for rule in DENY if rule not in deny]
    old = settings.get("hooks", {})
    for event in list(old):
        groups = [g for g in old[event] if not any("log_event.py" in h.get("command", "") for h in g.get("hooks", []))]
        if len(groups) != len(old[event]):
            notes.append(f"removed the older copied-in {event} hook; the plugin records now")
        if groups:
            old[event] = groups
        else:
            del old[event]
    if "hooks" in settings and not settings["hooks"]:
        del settings["hooks"]
    if json.dumps(settings, sort_keys=True) != before:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(settings, indent=2) + "\n")
        done.append("named the plugin in .claude/settings.json, so coauthors are prompted to install it")

    # 5. GitHub
    remote = git(repo, "remote", "get-url", "origin").stdout.strip()
    if remote:
        notes.append(f"this copy is connected to {remote}")
    elif os.environ.get("WD_SETUP_SKIP_GITHUB") == "1":
        notes.append("skipped GitHub (WD_SETUP_SKIP_GITHUB=1)")
    elif shutil.which("gh") is None:
        notes.append("no online copy yet: install GitHub's command-line tool from https://cli.github.com, "
                     "then /setup again")
    elif subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=30).returncode:
        notes.append("no online copy yet: log in to GitHub by typing ! gh auth login --web, then /setup again")
    else:
        subprocess.run(["gh", "auth", "setup-git"], capture_output=True, timeout=30)
        r = subprocess.run(["gh", "repo", "create", repo.name, "--private", "--source", str(repo), "--remote", "origin"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode:
            notes.append(f"couldn't create the GitHub repository: {r.stderr.strip()[-200:]}")
        else:
            done.append(f"created a private GitHub repository, {r.stdout.strip() or repo.name}")

    lines = ["Set up for warranted delegation." if done else "Already set up; nothing needed changing."]
    lines += [f"- {d[0].upper()}{d[1:]}." for d in done]
    lines += [f"- Note: {n}." for n in notes]
    lines.append("Recording is on in this project.")
    return "\n".join(lines)


# The questions (DECISIONS.md, Oct 16)

def settings(repo):
    """The project's tool (None until setup's questions are answered), and
    this copy's reader path and memory capture."""
    repo = Path(repo)
    try:
        tool = json.loads((repo / SETTINGS).read_text()).get("tool")
    except Exception:
        tool = None
    reader = git(repo, "config", "--local", READER_KEY).stdout.strip()
    memory = git(repo, "config", "--local", MEMORY_KEY).stdout.strip() or "on"
    consent = git(repo, "config", "--local", CONSENT_KEY).stdout.split()
    return {"tool": tool if tool in TOOLS else None, "reader": reader if reader in ("api", "headless") else None,
            "memory": "off" if memory == "off" else "on",
            "consent": consent[0] if consent else None, "consent_date": consent[1] if len(consent) > 1 else None}


def provider(s):
    """Where this copy's disclosure sends the work, as a consent key."""
    return {"claude-code": "anthropic-api" if s["reader"] == "api" else "anthropic-subscription",
            "codex-cli": "openai", "gemini-cli": "google"}.get(s["tool"])


def has_key():
    """Is there an API key in the Keychain? Asks only whether the item exists;
    the key itself is never read here."""
    try:
        return subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_ITEM],
                              capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def save(repo, answers):
    """Save the answers to setup's questions: tool=..., and for Claude Code,
    reader=... and memory=..."""
    repo = Path(repo)
    if not (repo / "provenance" / "log").is_dir():
        return "This project isn't set up yet. Type /setup first."
    tool, reader, memory = answers.get("tool"), answers.get("reader"), answers.get("memory")
    if answers.get("consent") and not tool:
        return consent(repo, answers["consent"])
    if tool not in TOOLS or reader not in (None, "headless", "api") or memory not in (None, "on", "off"):
        return ("Nothing saved: give tool=claude-code, codex-cli, or gemini-cli, and for Claude Code "
                "reader=headless or api, and memory=on or off.")
    path = repo / SETTINGS
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
    data["tool"] = tool
    path.write_text(json.dumps(data, indent=1) + "\n")
    name = TOOLS[tool]
    lines = ["Saved."]
    if tool == "claude-code":
        lines.append("- This project uses Claude Code, so its disclosure is read by Claude, on each author's own "
                     "account. This is saved with the project, so coauthors use the same; your next save keeps it.")
    else:
        lines.append(f"- This project uses {name}, so its disclosure is read by {name}, on each author's own account. "
                     "This is saved with the project, so coauthors use the same; your next save keeps it.")
    if reader:
        git(repo, "config", "--local", READER_KEY, reader, check=True)
        if reader == "api":
            lines.append("- In this copy, the disclosure reaches Claude through the API, billed to your own key. "
                         + ("Your key is in the Keychain." if has_key() else
                            "There's no API key in the Keychain yet: copy your key from console.anthropic.com, "
                            "then in Terminal type  security add-generic-password -U -a \"$USER\" -s "
                            f"{KEYCHAIN_ITEM} -w \"$(pbpaste)\""))
        else:
            lines.append("- In this copy, the disclosure reaches Claude through your Claude subscription, with no "
                         "API key. It counts against your subscription's usage limits.")
    if memory:
        git(repo, "config", "--local", MEMORY_KEY, memory, check=True)
        lines.append("- In this copy, the record keeps Claude's memory notes for this project." if memory == "on" else
                     "- In this copy, the record leaves out Claude's memory notes for this project, and says so.")
    return "\n".join(lines)


def consent(repo, key):
    """The author agreed that the disclosure may send the work by this path
    (DECISIONS.md, Oct 16): remembered for this copy, with the date."""
    if key not in PROVIDERS:
        return f"Nothing saved: consent is one of {', '.join(PROVIDERS)}."
    git(repo, "config", "--local", CONSENT_KEY, f"{key} {datetime.now():%Y-%m-%d}", check=True)
    who, how = PROVIDERS[key]
    return (f"Saved: you agreed that the disclosure may send your finished work and your record to {who}, through "
            f"{how}, for this copy. Each disclosure reminds you, and asks again if that changes.")


def defaults(repo, agent):
    """Headless setup can't ask, so it keeps the defaults and says so."""
    s = settings(repo)
    if s["tool"] is None:
        save(repo, {"tool": agent if agent in TOOLS else "claude-code"})
        s = settings(repo)
    return (f"Setup's questions need someone to answer them, so this headless run kept the defaults: the project "
            f"uses {TOOLS[s['tool']]}" + (f", and the record keeps Claude's memory notes" if s["tool"] == "claude-code"
                                          and s["memory"] == "on" else "") + ". Type /setup in Claude Code to choose.")


# The questions, as Claude is told to ask them, here and in disclose.py.

ASK = ("Ask these questions one at a time, and wait for each answer. Use your question tool if you have one "
       "(AskUserQuestion in Claude Code); otherwise ask in plain words. Give the options in this order, with their "
       "descriptions. Don't recommend one; the first is the current setting, or the default.")
READER = [("Your Claude subscription", "No API key. It counts against your subscription's usage limits.", "headless"),
          ("The API, with your own key", "Billed to your key: about $2 for a small project, more for a large one.", "api")]
MEMORY = [("Yes, keep them", "Guidance of yours that Claude saved in its notes then counts as yours.", "on"),
          ("No, leave them out", "The record says they were left out.", "off")]


def options(items, current):
    return "; ".join(f'"{label}" ({desc})' for label, desc, _ in sorted(items, key=lambda o: o[2] != current))


def ask_tool(s, agent):
    first = s["tool"] or (agent if agent in TOOLS else "claude-code")
    return (f'"Which tool do you use for this project?" Options: '
            f'{"; ".join(TOOLS[k] for k in [first] + [k for k in TOOLS if k != first])}. Say that the disclosure\'s '
            "reader runs on it, through each author's own account, and that the choice is saved with the project, so "
            "coauthors use the same.")


def ask_reader(s):
    return (f'"How should the disclosure reach Claude?" Options: {options(READER, s["reader"] or "headless")}. Say '
            "that this is for this copy only, and that it's remembered: /disclosure api or /disclosure subscription "
            "changes it.")


def ask_memory(s):
    return (f'"Should the record keep Claude\'s memory notes for this project?" Options: {options(MEMORY, s["memory"])}. '
            "Say that this is for this copy only.")


def named(text, agent):
    """The plugin's commands as the person types them: /warrant:attest, or
    warrant:attest in Codex, which has no custom slash commands."""
    text = re.sub(r"(?<![\w:/])/(attest|record|sync|undo|setup|disclosure|trail|withhold|brainstorm)\b", r"/warrant:\1", text)
    return re.sub(r"(?<![\w])/warrant:", "warrant:", text) if agent == "codex-cli" else text


def questions(repo, plugin, agent, report):
    """What Claude is told to do after the hook's steps: tell the author what
    setup did, ask about recording, save the answers."""
    s = settings(repo)
    return "\n".join([
        "warrant:setup. The warrant plugin's hook ran setup's steps and reported:", "", report, "",
        "Now walk the author through setup's questions, so the choices are theirs and clear (DECISIONS.md, Oct 16).",
        "1. Tell the author in a sentence or two what setup did, from the report. Don't paste it.",
        "2. " + ASK,
        "   a. " + ask_tool(s, agent),
        "   b. Only if the answer is Claude Code: " + ask_memory(s),
        "3. Save the answers by running this command, filled in: tool is claude-code, codex-cli, or gemini-cli; for "
        "Claude Code, memory is on or off. For Codex or Gemini, leave memory out.",
        f'   python3 "{Path(plugin) / "scripts" / "setup.py"}" save "{repo}" tool=... memory=...',
        "4. Tell the author, in plain words, what it printed, and that /attest makes their first save. If the "
        "answer was Claude Code, say that the first disclosure will ask how it reaches Claude."
        + (" Then tell them that Codex leaves one of the plugin's hooks off: type /hooks, choose PostToolUse, and "
           "press Space to turn the warrant hook on. Without it, the record keeps their prompts but not Codex's "
           "commands and edits (Oct 16, the Codex live test)." if agent == "codex-cli" else "")
        + " Do nothing else in this turn.",
    ])


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "save":
        print(save(sys.argv[2], dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)))
    else:
        sys.exit(__doc__)
