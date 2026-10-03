#!/usr/bin/env python3
"""SUPERSEDED — use gen_xy_drive_page.py (one TC4427A+FDS8958A sheet, ×4)."""
from __future__ import annotations
import sys

print(
    "gen_drive_hierarchy.py is superseded.\n"
    "Use: python3 kicad/scripts/gen_xy_drive_page.py\n"
    "Drive is one hierarchical page (TC4427A + FDS8958A), instanced FWD/REV × X/Y.",
    file=sys.stderr,
)
raise SystemExit(1)
