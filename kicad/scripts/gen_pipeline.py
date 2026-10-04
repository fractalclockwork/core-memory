#!/usr/bin/env python3
"""Single entry point: weave AST → SPICE decks, coverage doc, optional KiCad regen.

Usage:
  uv run python kicad/scripts/gen_pipeline.py              # decks + coverage
  uv run python kicad/scripts/gen_pipeline.py --kicad       # also regen sheets
  uv run python kicad/scripts/gen_pipeline.py --check-abi   # tile pin budgets
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
MODELS = ROOT / "kicad" / "core_element_sim" / "models"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def gen_spice_decks() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from mce_array import (  # noqa: E402
        write_diagonal_deck,
        write_ideal_diagonal_deck,
        write_ideal_nxn_deck,
    )

    write_diagonal_deck(MODELS / "array64x64_cycle_tb.cir", n=64, i0=0, i1=32)
    write_diagonal_deck(MODELS / "array64x64_cycle_hi.cir", n=64, i0=32, i1=64)
    write_ideal_diagonal_deck(MODELS / "array64x64_ideal_tb.cir", n=64)
    write_ideal_nxn_deck(MODELS / "array_ideal_nxn_tb.cir", n=8)
    print("wrote behavioral + ideal SPICE decks")


def gen_coverage() -> None:
    _run([sys.executable, str(SCRIPTS / "gen_coverage_matrix.py")])


def check_abi() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import hierarchy_tiles  # noqa: E402

    hierarchy_tiles.assert_octal_covers_monolithic()
    for k, v in hierarchy_tiles.pin_budget().items():
        print(f"{k}={v}")
    print("hierarchy ABI OK")


def gen_kicad() -> None:
    py = [sys.executable]
    steps = [
        SCRIPTS / "gen_xy_drive_page.py",
        SCRIPTS / "gen_xy_decode_page.py",
        SCRIPTS / "gen_decoupling_pages.py",
        SCRIPTS / "gen_ferrite_beads_page.py",
    ]
    for script in steps:
        if script.name == "gen_ferrite_beads_page.py":
            _run([*py, str(script), "--array", "64"])
        else:
            _run([*py, str(script)])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad", action="store_true", help="regen KiCad sheets (full pipeline)")
    p.add_argument("--check-abi", action="store_true", help="verify octal tile coverage")
    p.add_argument("--spice-only", action="store_true", help="only rewrite SPICE decks")
    args = p.parse_args()

    if args.check_abi:
        check_abi()
        return

    gen_spice_decks()
    if args.spice_only:
        return
    gen_coverage()
    if args.kicad:
        gen_kicad()
    check_abi()


if __name__ == "__main__":
    main()
