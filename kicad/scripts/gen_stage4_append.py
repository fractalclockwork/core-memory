#!/usr/bin/env python3
"""RETIRED — Gate drive is the TC4427A on drive_block.kicad_sch (×4).

Use:  python3 kicad/scripts/gen_xy_drive_page.py
"""
from __future__ import annotations
import sys

print(
    "gen_stage4_append.py is retired.\n"
    "Gate drive is the TC4427A on drive_block.kicad_sch (one sheet, ×4).\n"
    "Regenerate with: python3 kicad/scripts/gen_xy_drive_page.py",
    file=sys.stderr,
)
raise SystemExit(1)
