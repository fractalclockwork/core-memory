#!/usr/bin/env python3
"""RETIRED — Drive REV gate drive is the TC4427A on the REV drive instances.

Use:  python3 kicad/scripts/gen_xy_drive_page.py
"""
from __future__ import annotations
import sys

print(
    "gen_stage7_rev_gatedrive.py is retired.\n"
    "REV gate drive is the TC4427A on Drive REV X / Drive REV Y.\n"
    "Regenerate with: python3 kicad/scripts/gen_xy_drive_page.py",
    file=sys.stderr,
)
raise SystemExit(1)
