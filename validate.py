#!/usr/bin/env python3
"""Check vectors.json for the mistakes a hand-edited data file invites.

This does not judge whether a width is the right answer -- that argument
belongs in the `why` field and in the runner tables. It checks that the file
says what it means to say.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def fail(message: str) -> None:
    print(f"  {message}")


def main() -> int:
    doc = json.loads((ROOT / "vectors.json").read_text(encoding="utf-8"))
    problems: list[str] = []

    seen: set[str] = set()
    for group, required in (("vectors", ("width",)), ("contested", ("width_narrow", "width_east_asian"))):
        for entry in doc[group]:
            where = f"{group}/{entry.get('id', '<unnamed>')}"
            if entry["id"] in seen:
                problems.append(f"{where}: duplicate id")
            seen.add(entry["id"])

            for key in ("id", "codepoints", "category", "why", *required):
                if key not in entry:
                    problems.append(f"{where}: missing {key}")

            for cp in entry.get("codepoints", []):
                if not (len(cp) >= 4 and cp == cp.upper() and all(c in "0123456789ABCDEF" for c in cp)):
                    problems.append(f"{where}: {cp!r} is not an upper-case hex code point")
                elif int(cp, 16) > 0x10FFFF:
                    problems.append(f"{where}: {cp} is beyond the Unicode range")

            text = entry.get("text")
            if text is not None:
                expected = "".join(chr(int(cp, 16)) for cp in entry["codepoints"])
                if text != expected:
                    problems.append(f"{where}: text does not match codepoints")

            if not entry.get("why", "").endswith("."):
                problems.append(f"{where}: why should be a sentence")

    # The generator is the source of truth; a hand edit to vectors.json would
    # be silently lost the next time it runs.
    before = (ROOT / "vectors.json").read_bytes()
    subprocess.run([sys.executable, str(ROOT / "build_vectors.py")], check=True, capture_output=True)
    after = (ROOT / "vectors.json").read_bytes()
    if before != after:
        problems.append("vectors.json differs from what build_vectors.py produces; edit the table there")

    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems:
            fail(problem)
        return 1

    print(
        f"ok: {len(doc['vectors'])} scored vectors, "
        f"{len(doc['contested'])} contested cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
