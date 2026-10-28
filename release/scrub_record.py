#!/usr/bin/env python3
"""Make a run's record anonymous for the blind review copy, and let anyone
holding the original confirm that nothing else changed (DECISIONS.md, Oct 23).

    scrub_record.py make  ORIGINAL.bundle SCRUBBED.bundle [--withhold SHA256 ...] [--map MAP.json]
    scrub_record.py check ORIGINAL.bundle SCRUBBED.bundle [--withhold SHA256 ...]

`make` writes the scrubbed bundle. `check` makes it again from the original,
in a temporary folder, and compares: the two match only if every commit,
snapshot, log line, and text file comes out the same, since git names each
by its content. It prints what was changed and exits 0 on a match, 1 if not.

What changes, and nothing else:
- Three swaps in every text in the record: the Mac username becomes "user",
  the GitHub account becomes "anonymous.invalid" (a name GitHub can't have,
  so an install source pointing there reaches nothing), and an email address
  becomes author@example.invalid. The swaps are listed in swaps.json beside
  this script, which stays with the original record and is not in the review
  copy, since it names what it replaces.
- Python's cache files (__pycache__/, .pyc) are left out. They are compiled
  copies Python rebuilds when a script runs, and they hold the username in a
  form a text swap would corrupt.
- Texts named with --withhold (by their original SHA-256) are left out, as
  /warrant:withhold leaves texts out of a review copy. Their log lines stay,
  and the record still verifies, since a missing text counts as withheld.
- What follows from the swaps: each text file beside the log is renamed by
  the SHA-256 of its new content, and the log lines that name it follow; a
  Bash command's command_sha256 is recomputed when the line holds the whole
  command (a longer command's hash covers text the record never kept, so it
  stays), and a tool output's output_bytes when its text was kept whole;
  every prev_hash is recomputed down the chain; and every commit and
  snapshot is rewritten, keeping its author, dates, and message, so the
  lines naming a snapshot follow too.

Uses only Python's standard library and git.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from collections import Counter
from pathlib import Path

SWAPS = []  # (old, new) pairs of bytes, from swaps.json
GENESIS = "0" * 64
SIDECAR = re.compile(r"^provenance/log/text/([0-9a-f]{64})\.txt$")
LOG = re.compile(r"^provenance/log/(?:[^/]+/)?events\.jsonl$")
TEXT_FIELDS = ("prompt_sha256", "response_sha256", "output_sha256")


def left_out(path):
    return "/__pycache__/" in "/" + path or path.endswith(".pyc")


def swap(data, tally):
    for old, new in SWAPS:
        n = data.count(old)
        if n:
            tally[old.decode()] += n
            data = data.replace(old, new)
    return data


def git(repo, *args, data=None):
    r = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.decode().strip()}")
    return r.stdout


class Objects:
    """Reads the original's objects through one `git cat-file --batch`, and
    writes new ones straight into the new repository's object folder."""

    def __init__(self, src, dest):
        self.p = subprocess.Popen(["git", "-C", str(src), "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.dest = Path(dest) / "objects"

    def read(self, sha):
        self.p.stdin.write(sha.encode() + b"\n")
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if len(head) < 3:
            raise SystemExit(f"object {sha} is missing from the bundle")
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return head[1].decode(), data

    def write(self, kind, data):
        obj = kind.encode() + b" " + str(len(data)).encode() + b"\0" + data
        sha = hashlib.sha1(obj).hexdigest()
        path = self.dest / sha[:2] / sha[2:]
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(zlib.compress(obj))
        return sha

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def parse_tree(data):
    out, i = [], 0
    while i < len(data):
        sp, nul = data.index(b" ", i), data.index(b"\0", i)
        out.append((data[i:sp].decode(), data[sp + 1:nul].decode(), data[nul + 1:nul + 21].hex()))
        i = nul + 21
    return out


def tree_bytes(entries):
    key = lambda e: e[1].encode() + (b"/" if e[0] == "40000" else b"")  # git's order
    return b"".join(m.encode() + b" " + n.encode() + b"\0" + bytes.fromhex(s) for m, n, s in sorted(entries, key=key))


class Scrub:
    def __init__(self, src, dest, withhold):
        self.obj = Objects(src, dest)
        self.withhold = set(withhold)
        self.tally = Counter()
        self.commits, self.trees, self.blobs = {}, {}, {}
        self.digests, self.sizes, self.heads = {}, {}, {}
        self.dropped, self.withheld = set(), set()
        # Every text file beside a log, first, so a log line can be rewritten
        # before the files it names (the log sorts ahead of text/ in a tree).
        # Read from each commit's tree: a text file whose content another file
        # shares can be listed under that file's name elsewhere.
        seen = set()
        for c in git(src, "rev-list", "--all").decode().split():
            seen.update(git(src, "ls-tree", "-r", c, "--", "provenance/log/text/").decode().splitlines())
        for line in sorted(seen):
            sha, path = line.split(" ")[2].split("\t")
            m = SIDECAR.match(path)
            if m and m.group(1) not in self.digests:
                data = self.obj.read(sha)[1]
                self.sizes[m.group(1)] = len(data)
                new = swap(data, Counter())
                self.digests[m.group(1)] = hashlib.sha256(new).hexdigest()
                self.sizes[self.digests[m.group(1)]] = len(new)

    def blob(self, sha, path):
        """(new name, new sha) for a file, or None to leave it out."""
        m = SIDECAR.match(path)
        if m and m.group(1) in self.withhold:
            self.withheld.add(m.group(1))
            return None
        if (sha, path) not in self.blobs:
            data = self.obj.read(sha)[1]
            if LOG.match(path):
                new = self.log(data)
            elif b"\0" in data[:8000]:  # a binary file: a text swap would corrupt it
                if any(old in data for old, _ in SWAPS):
                    raise SystemExit(f"{path}: a binary file holds a name this script can't swap safely")
                new = data
            else:
                new = swap(data, self.tally)
            name = f"{self.digests[m.group(1)]}.txt" if m else path.rsplit("/", 1)[-1]
            self.blobs[(sha, path)] = (name, self.obj.write("blob", new))
        return self.blobs[(sha, path)]

    def log(self, data):
        if not data.endswith(b"\n"):
            raise SystemExit("a log without a final newline")
        out, prev = [], GENESIS
        for raw in data[:-1].split(b"\n"):
            r = json.loads(raw)
            if json.dumps(r, separators=(",", ":"), ensure_ascii=False).encode() != raw:
                raise SystemExit("a log line this script can't rewrite byte for byte")
            old = r
            r = json.loads(swap(raw, self.tally))
            for k in TEXT_FIELDS:
                if r.get(k) in self.digests:
                    r[k] = self.digests[r[k]]
            for i in r.get("instructions") or []:
                if isinstance(i, dict) and i.get("sha256") in self.digests:
                    i["sha256"] = self.digests[i["sha256"]]
            if isinstance(r.get("skill"), dict) and r["skill"].get("sha256") in self.digests:
                r["skill"]["sha256"] = self.digests[r["skill"]["sha256"]]
            if isinstance(old.get("command"), str) and \
                    hashlib.sha256(old["command"].encode()).hexdigest() == old.get("command_sha256"):
                r["command_sha256"] = hashlib.sha256(r["command"].encode()).hexdigest()
            out_sha = old.get("output_sha256")
            if "output_full_sha256" not in old and out_sha in self.sizes and old.get("output_bytes") == self.sizes[out_sha]:
                r["output_bytes"] = self.sizes[self.digests[out_sha]]
            snap = r.get("snapshot")
            if isinstance(snap, str):
                if snap in self.commits:
                    r["snapshot"] = self.commits[snap]
                elif snap in self.all:
                    raise SystemExit(f"a log line names snapshot {snap} before it was rewritten")
            r["prev_hash"] = prev
            line = json.dumps(r, separators=(",", ":"), ensure_ascii=False).encode()
            prev = hashlib.sha256(line).hexdigest()
            out.append(line)
        self.heads[hashlib.sha256(data[:-1].split(b"\n")[-1]).hexdigest()] = prev
        return b"\n".join(out) + b"\n"

    def tree(self, sha, path=""):
        if (sha, path) not in self.trees:
            entries = []
            for mode, name, esha in parse_tree(self.obj.read(sha)[1]):
                p = path + name
                if mode == "40000":
                    t = self.tree(esha, p + "/")
                    if t:
                        entries.append((mode, name, t))
                elif mode == "160000":
                    entries.append((mode, name, esha))
                elif left_out(p):
                    self.dropped.add(p)
                else:
                    b = self.blob(esha, p)
                    if b:
                        entries.append((mode, *b))
            self.trees[(sha, path)] = self.obj.write("tree", tree_bytes(entries)) if entries else None
        return self.trees[(sha, path)]

    def commit(self, sha):
        kind, data = self.obj.read(sha)
        head, _, msg = data.partition(b"\n\n")
        lines = []
        for line in head.split(b"\n"):
            key, _, val = line.partition(b" ")
            if key == b"tree":
                line = b"tree " + (self.tree(val.decode()) or self.obj.write("tree", b"")).encode()
            elif key == b"parent":
                line = b"parent " + self.commits[val.decode()].encode()
            elif any(old in line for old, _ in SWAPS) or key == b"gpgsig":
                raise SystemExit(f"commit {sha}: a header this script doesn't rewrite")
            lines.append(line)
        self.commits[sha] = self.obj.write("commit", b"\n".join(lines) + b"\n\n" + swap(msg, self.tally))

    def tag(self, sha):
        _, data = self.obj.read(sha)
        head, _, msg = data.partition(b"\n\n")
        head = re.sub(rb"^object ([0-9a-f]{40})", lambda m: b"object " + self.target(m.group(1).decode()).encode(), head)
        return self.obj.write("tag", head + b"\n\n" + swap(msg, self.tally))

    def target(self, sha):
        return self.commits.get(sha) or self.tag(sha)


def scrub(bundle, dest_git, withhold):
    """Rewrite the bundle into a new bare repository; returns (refs, Scrub)."""
    src = Path(tempfile.mkdtemp(prefix="wd-scrub-src-"))
    try:
        git(".", "clone", "-q", "--mirror", str(bundle), str(src))
        git(".", "init", "-q", "--bare", str(dest_git))
        s = Scrub(src, dest_git, withhold)
        s.all = set(git(src, "rev-list", "--all").decode().split())
        for c in git(src, "rev-list", "--topo-order", "--reverse", "--all").decode().split():
            s.commit(c)
        refs = {}
        for line in git(src, "for-each-ref", "--format=%(objectname) %(refname)").decode().splitlines():
            sha, ref = line.split(" ", 1)
            refs[ref] = s.target(sha)
        head = git(src, "symbolic-ref", "HEAD").decode().strip()
        s.obj.close()
        for ref, sha in refs.items():
            git(dest_git, "update-ref", ref, sha)
        git(dest_git, "symbolic-ref", "HEAD", head)
        return refs, s
    finally:
        shutil.rmtree(src, ignore_errors=True)


def bundle_refs(bundle):
    out = git(".", "bundle", "list-heads", str(bundle)).decode().split("\n")
    return {ref: sha for sha, ref in (l.split(" ", 1) for l in out if l) if ref != "HEAD"}


def summary(s):
    lines = [f"  {n} × {old!r}" for old, n in s.tally.items()] or ["  no swaps"]
    renamed = sum(old != new for old, new in s.digests.items())
    lines.append(f"  {renamed} of {len(s.digests)} text files beside the log renamed by their new SHA-256")
    lines.append(f"  {len(s.commits)} commits and snapshots rewritten, keeping author, dates, and message")
    if s.dropped:
        lines.append(f"  left out, Python's cache: {', '.join(sorted(s.dropped))}")
    if s.withheld:
        lines.append(f"  withheld: {', '.join(sorted(s.withheld))}")
    return "\n".join(lines)


def option(args, name):
    """The values after --name, up to the next option."""
    if name not in args:
        return []
    rest = args[args.index(name) + 1:]
    return rest[:next((i for i, a in enumerate(rest) if a.startswith("--")), len(rest))]


def main(args):
    withhold = option(args, "--withhold")
    mapfile = (option(args, "--map") or [None])[0]
    swaps = Path((option(args, "--swaps") or [Path(__file__).with_name("swaps.json")])[0])
    if len(args) < 3 or args[0] not in ("make", "check"):
        sys.exit(__doc__)
    if not swaps.is_file():
        sys.exit(f"No {swaps.name}: it lists the swaps and stays with the original record, outside the review copy.")
    SWAPS[:] = [(old.encode(), new.encode()) for old, new in json.loads(swaps.read_text())["swaps"]]
    mode, original, scrubbed = args[0], Path(args[1]), Path(args[2])
    work = Path(tempfile.mkdtemp(prefix="wd-scrub-"))
    try:
        refs, s = scrub(original, work / "new.git", withhold)
        if mode == "make":
            git(work / "new.git", "bundle", "create", "-q", str(scrubbed.resolve()), "--all")
            if mapfile:
                Path(mapfile).write_text(json.dumps({"commits": s.commits, "heads": s.heads, "texts": s.digests},
                                                    indent=1) + "\n")
            print(f"{scrubbed.name}: made\n{summary(s)}")
            return 0
        same = refs == bundle_refs(scrubbed)
        print(f"{scrubbed.name}: {'MATCHES' if same else 'DOES NOT MATCH'} the original with only these changes\n{summary(s)}")
        if not same:
            theirs = bundle_refs(scrubbed)
            for ref in sorted(set(refs) | set(theirs)):
                if refs.get(ref) != theirs.get(ref):
                    print(f"  {ref}: expected {refs.get(ref)}, found {theirs.get(ref)}")
        return 0 if same else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
