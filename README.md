# Core Memory Driver

Electronics for driving and sensing an existing 9″ square ferrite core plane: a 64×64 array (4,096 bits / 512 bytes) with dual-readout edge connectors XA/XB and YA/YB.

Each core is **three-wire** (X, Y, sense)—there is no separate inhibit winding. Sense/inhibit is two independent 2,048-core loops (`YA65`↔`YA66` and `YB65`↔`YB66`). The driver ties `YA66` to `YB65` and reads/drives the outer ends `YA65`/`YB66`; see [docs/theory_of_operation.md](docs/theory_of_operation.md).

## Documentation

Start at [docs/README.md](docs/README.md). Frozen contracts: [docs/icd.md](docs/icd.md). Process layers L0–L4: [docs/reimplementation.md](docs/reimplementation.md). Coverage: [docs/coverage_matrix.md](docs/coverage_matrix.md).

## KiCad

Schematic and PCB live under [kicad/core/](kicad/core/). Custom symbols and card-edge footprints are in [kicad/libs/](kicad/libs/); generators are in [kicad/scripts/](kicad/scripts/). Steer fabric: `steer_64.kicad_sch` (octal tiles: [docs/hierarchy_abi.md](docs/hierarchy_abi.md)).

## Python tooling

Dependencies (e.g. [kiutils](https://pypi.org/project/kiutils/)) are managed with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run python kicad/scripts/gen_pipeline.py              # SPICE decks + coverage + ABI check
uv run python kicad/scripts/gen_pipeline.py --spice-only # ideal + behavioral decks only
uv run python kicad/scripts/gen_pipeline.py --kicad      # also regen KiCad sheets
uv run python kicad/scripts/gen_pipeline.py --check-abi  # octal tile pin budgets
```

Individual generators (also invoked by the pipeline `--kicad` path):

```bash
uv run python kicad/scripts/gen_xy_drive_page.py   # drive_block + steer_64
uv run python kicad/scripts/gen_xy_decode_page.py  # decode_block
uv run python kicad/scripts/gen_decoupling_pages.py
uv run python kicad/scripts/gen_ferrite_beads_page.py --array 64
uv run python kicad/scripts/gen_core_element_sim.py
```

## Simulation

```bash
kicad/core_element_sim/run_regression.sh          # L0 + L1
kicad/core_element_sim/run_regression.sh --l2     # + L2 e2e ladder
kicad/core_element_sim/run_regression.sh --ideal  # + L3 ideal n×n
```

The core-element model is exercised in [kicad/core_element_sim/](kicad/core_element_sim/). L0 detailed MCE and L3 `ideal_core` are separate — see [docs/core_element_sim.md](docs/core_element_sim.md).
