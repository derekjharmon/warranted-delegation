#!/usr/bin/env python3
"""For anyone holding the original record: confirm that every run record in
the review copy is its original with only the changes scrub_record.py makes.

    python3 release/check_copy.py ORIGINAL COPY

ORIGINAL is the original repository, which keeps release/swaps.json (the
swaps name what they replace, so they aren't in the copy); COPY is the review
copy. Each bundle in COPY is remade from the bundle at the same path in
ORIGINAL and compared (scrub_record.py check). Exits 0 if every one matches.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scrub_record  # noqa: E402


def main(args):
    if len(args) != 2:
        sys.exit(__doc__)
    original, copy = (Path(a).expanduser().resolve() for a in args)
    withheld = json.loads((copy / "release" / "withheld.json").read_text())["texts"]
    swaps = original / "release" / "swaps.json"
    bad = []
    bundles = sorted(p.relative_to(copy).as_posix() for p in copy.rglob("*.bundle") if ".git" not in p.parts)
    for rel in bundles:
        args = ["check", str(original / rel), str(copy / rel), "--swaps", str(swaps)]
        if withheld.get(rel):
            args += ["--withhold", *withheld[rel]]
        if scrub_record.main(args):
            bad.append(rel)
        print()
    print(f"{len(bundles) - len(bad)} of {len(bundles)} run records match their originals with only these changes.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
