#!/usr/bin/env python3
"""Measure the vectors with each Python width implementation."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def text_of(vector: dict) -> str:
    return "".join(chr(int(cp, 16)) for cp in vector["codepoints"])


def implementations() -> dict:
    impls: dict[str, callable] = {}

    try:
        from rich.cells import cell_len

        impls["rich.cell_len"] = cell_len
    except ImportError:
        pass

    try:
        from wcwidth import wcswidth

        # wcswidth answers -1 for a string holding a character it considers
        # non-printable; keep that rather than folding it into 0.
        impls["wcwidth.wcswidth"] = wcswidth
        from wcwidth import wcwidth as wcwidth_one

        def per_char(s: str) -> int:
            return sum(max(wcwidth_one(c), 0) for c in s)

        impls["wcwidth per char"] = per_char
    except ImportError:
        pass

    return impls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[2] / "vectors.json",
    )
    args = parser.parse_args()

    doc = load(args.vectors)
    impls = implementations()
    if not impls:
        print("no width library installed; pip install rich wcwidth", file=sys.stderr)
        return 2

    names = list(impls)
    failures = dict.fromkeys(names, 0)

    header = f"{'vector':<32}{'want':>6}" + "".join(f"{n:>22}" for n in names)
    print(header)
    for vector in doc["vectors"]:
        text = text_of(vector)
        row = f"{vector['id']:<32}{vector['width']:>6}"
        for name in names:
            got = impls[name](text)
            if got != vector["width"]:
                failures[name] += 1
                row += f"{str(got) + ' x':>22}"
            else:
                row += f"{got:>22}"
        print(row)

    print()
    print(f"{'failures':<32}{'':>6}" + "".join(f"{failures[n]:>22}" for n in names)
          + f"  of {len(doc['vectors'])}")

    print("\ncontested (reported, not scored):")
    for case in doc["contested"]:
        text = text_of(case)
        measured = " ".join(f"{n}={impls[n](text)}" for n in names)
        print(
            f"  {case['id']:<30} narrow={case['width_narrow']} "
            f"eastasian={case['width_east_asian']}  {measured}"
        )

    # Disagreement is the point of the table, so a runner reports and stops
    # there. Whether a vector is defensible is judged across all of the
    # runners, not inside one of them.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
