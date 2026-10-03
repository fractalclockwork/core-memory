#!/usr/bin/env python3
"""RETIRED — Drive FETs live on drive_block.kicad_sch (one half-bridge, ×4).

Use:  python3 kicad/scripts/gen_xy_drive_page.py
"""
from __future__ import annotations
import sys

print(
    "gen_stage3_append.py is retired.\n"
    "Drive FETs live in drive_block.kicad_sch (one TC4427A + FDS8958A, ×4).\n"
    "Regenerate with: python3 kicad/scripts/gen_xy_drive_page.py",
    file=sys.stderr,
)
raise SystemExit(1)
