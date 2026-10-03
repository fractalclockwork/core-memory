#!/usr/bin/env python3
"""SUPERSEDED — use gen_xy_decode_page.py (single XY Decode page, 138+238 per axis)."""
from __future__ import annotations
import sys

print(
    "gen_stage8_decode.py is superseded.\n"
    "Use: python3 kicad/scripts/gen_xy_decode_page.py\n"
    "XY Decode is one hierarchical page (X/Y 138+238); root ×2 FWD/REV via BANK_EN.",
    file=sys.stderr,
)
raise SystemExit(1)
