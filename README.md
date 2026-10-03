# Core Memory Driver

Electronics for driving and sensing an existing 9″ square ferrite core plane: a 64×64 array (4,096 bits / 512 bytes) with dual-readout edge connectors XA/XB and YA/YB.

Each core is **three-wire** (X, Y, sense)—there is no separate inhibit winding. The folded sense loop (YB65/YB66 via YA65/66) is shared for differential READ and series WRITE-0 inhibit; see [docs/theory_of_operation.md](docs/theory_of_operation.md).

## Documentation

Start at [docs/README.md](docs/README.md) for theory of operation, board regions, design choices, component selection, the plane interface spec, and the chip-datasheet archive.

## KiCad

Schematic and PCB live under [kicad/core/](kicad/core/). Custom symbols and card-edge footprints are in [kicad/libs/](kicad/libs/); generators are in [kicad/scripts/](kicad/scripts/).

## Python tooling

Dependencies (e.g. [kiutils](https://pypi.org/project/kiutils/)) are managed with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run python kicad/scripts/gen_xy_drive_page.py   # drive_block.kicad_sch (N/n pins; local VDRIVE bypass; X0 FWD)
uv run python kicad/scripts/gen_xy_decode_page.py  # decode_block.kicad_sch (N/n pins; local +3V3 bypass; X FWD)
uv run python kicad/scripts/gen_decoupling_pages.py  # shared Sense/Latch/CCS + Inhibit caps; regen blocks
uv run python kicad/scripts/gen_ferrite_beads_page.py --phase 2  # 2×2 CoreBead stand-in page
```
