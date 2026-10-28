#!/usr/bin/env python3
"""Verify the hash chains in the project's logs and the sidecar files they
reference.

Usage: python3 provenance/verify_log.py [path/to/events.jsonl]

With no argument, checks every copy's log, provenance/log/<log id>/events.jsonl,
plus provenance/log/events.jsonl if one exists from before logs were split by
copy. Each log is its own chain.

Exits 0 if every line parses and its prev_hash equals the SHA-256 of the
previous line's exact bytes (64 zeros for the first line), and every sidecar
present matches the hash its line records; exits 1 and lists each problem
otherwise. A missing sidecar is counted as withheld, not as an error.
Sidecars live beside the log: text/<sha256>.txt for prompt_sha256,
response_sha256 and output_sha256, and transcripts/<session_id>.jsonl, whose
first transcript_bytes bytes must hash to transcript_sha256.

Also counts the working-tree snapshots the log names (snapshot): present if
the commit is in this repository, withheld if not. Snapshots are pushed with
each save; a clone that hasn't fetched refs/provenance counts them as withheld.

Prints the head hash (SHA-256 of the last line): the chain cannot show edits
to the last line or removal of trailing lines, so compare the head against a
copy recorded elsewhere, e.g. the committed log.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

GENESIS = "0" * 64
LOG_ROOT = Path(__file__).resolve().parent / "log"


def verify(path):
    data = path.read_bytes()
    if not data:
        return 0, [], GENESIS, []
    errors = []
    if not data.endswith(b"\n"):
        errors.append("last line has no trailing newline (incomplete write or edit)")
        data += b"\n"
    lines = data[:-1].split(b"\n")
    records = []
    prev = GENESIS
    for n, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
            found = record.get("prev_hash")
        except (ValueError, AttributeError):
            found = None
        if not isinstance(found, str):
            errors.append(f"line {n}: not a JSON object with a prev_hash")
        else:
            records.append((n, record))
            if found != prev:
                cause = ("lines were removed from the start" if n == 1 else
                         f"line {n - 1} was altered, or lines were inserted or removed here")
                errors.append(
                    f"line {n}: prev_hash mismatch (expected {prev[:16]}..., "
                    f"found {found[:16]}...) - {cause}"
                )
        prev = hashlib.sha256(line).hexdigest()
    return len(lines), errors, prev, records


def sidecar_root(path):
    """The folder holding text/ and transcripts/: the log's own folder for an
    unsplit log, its parent for a copy's log."""
    return path.parent if (path.parent / "text").exists() or path.parent == LOG_ROOT else path.parent.parent


def check_sidecars(log_dir, records):
    """Return (errors, checked, withheld) for the sidecars the records name."""
    errors, checked, withheld = [], 0, 0
    transcripts = {}
    for n, record in records:
        for field in ("prompt", "response", "output"):
            digest = record.get(f"{field}_sha256")
            # Lines from before the sidecars hold the text inline instead.
            if not isinstance(digest, str) or field in record:
                continue
            path = log_dir / "text" / f"{digest}.txt"
            if not path.exists():
                withheld += 1
                continue
            checked += 1
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append(f"line {n}: text/{digest}.txt does not match its name")
        digest, size = record.get("transcript_sha256"), record.get("transcript_bytes")
        if not isinstance(digest, str) or not isinstance(size, int):
            continue
        session = record.get("session_id")
        if session not in transcripts:
            path = log_dir / "transcripts" / f"{session}.jsonl"
            transcripts[session] = path.read_bytes() if path.is_file() else None
        copy = transcripts[session]
        if copy is None:
            withheld += 1
            continue
        checked += 1
        if len(copy) < size or hashlib.sha256(copy[:size]).hexdigest() != digest:
            errors.append(
                f"line {n}: transcripts/{session}.jsonl does not start with the "
                f"{size} bytes this line hashed (copy altered or truncated)"
            )
    return errors, checked, withheld


def count_snapshots(log_dir, records):
    """Return (present, withheld) for the snapshot commits the records name."""
    names = {r.get("snapshot") for _, r in records if isinstance(r.get("snapshot"), str)}
    if not names:
        return 0, 0
    try:
        result = subprocess.run(
            ["git", "-C", str(log_dir), "cat-file", "--batch-check"],
            input="".join(f"{n}^{{commit}}\n" for n in sorted(names)),
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return 0, len(names)
    missing = result.stdout.count(" missing")
    return len(names) - missing, missing


def check(path):
    """Verify one log and print its result. Return True if it is intact."""
    count, errors, head, records = verify(path)
    sidecar_errors, checked, withheld = check_sidecars(sidecar_root(path), records)
    errors += sidecar_errors
    for err in errors:
        print(f"BROKEN  {err}")
    status = "BROKEN" if errors else "OK"
    print(f"{status}  {count} events  head {head}  ({path})")
    print(f"        sidecars: {checked} checked, {withheld} withheld")
    present, missing = count_snapshots(path.parent, records)
    if present or missing:
        print(f"        snapshots: {present} present, {missing} withheld")
    return not errors


def main():
    if len(sys.argv) > 1:
        paths = [Path(sys.argv[1])]
    else:
        paths = sorted(LOG_ROOT.glob("*/events.jsonl"))
        if (LOG_ROOT / "events.jsonl").exists():
            paths.insert(0, LOG_ROOT / "events.jsonl")
    paths = [p for p in paths if p.exists()]
    if not paths:
        print(f"{LOG_ROOT}: no log yet")
        return 0
    results = [check(p) for p in paths]
    if len(paths) > 1:
        print(f"{'OK' if all(results) else 'BROKEN'}  {len(paths)} logs")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
