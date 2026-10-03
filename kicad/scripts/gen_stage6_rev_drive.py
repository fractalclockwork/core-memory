#!/usr/bin/env python3
"""RETIRED — Drive REV is two instances of drive_block.kicad_sch (X and Y).

Use:  python3 kicad/scripts/gen_xy_drive_page.py
"""
from __future__ import annotations
import sys

print(
    "gen_stage6_rev_drive.py is retired.\n"
    "Drive REV is drive_block.kicad_sch with HS/LS plane pins swapped on root.\n"
    "Regenerate with: python3 kicad/scripts/gen_xy_drive_page.py",
    file=sys.stderr,
)
raise SystemExit(1)
