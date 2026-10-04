# Design Documentation

Driver-board documentation for the 64×64 magnetic core plane.

## Reading order

1. [Interface control document (ICD)](icd.md) — frozen plane / CCS / enable contract
2. [Reimplementation process (L0–L4)](reimplementation.md) — single core → ideal n×n → fabric
3. [Coverage matrix](coverage_matrix.md) — schematic vs SPICE vs SIL vs bench (do not conflate)
4. [Hierarchical fabric ABI](hierarchy_abi.md) — steer/magnetic pin budgets and octal tiles
5. [Design review](design_review.md) — process retrospective
6. [Signal naming](naming.md) — net taxonomy, block ABI, hierarchy scale path
7. [Theory of operation](theory_of_operation.md) — how a bit is read and written
8. [Major regions](regions.md) — functional circuit blocks on the schematic
9. [Implementation summary](implementation_summary.md) — present schematic state + parts used
10. [Design choices](design_choices.md) — architecture rationale and open decisions
11. [Component selection](component_selection.md) — parts and why they were chosen
12. [Design specification](design_spec.md) — normative plane / connector / timing contract
13. [References](references.md) — bibliography and image sources

## Core element model

[Core-element simulation](core_element_sim.md) — L0 `coremem`, L1/L2 2×2 ladder, L3 `ideal_core` n×n. Regression: `kicad/core_element_sim/run_regression.sh`. Pipeline: `uv run python kicad/scripts/gen_pipeline.py`.

## Archives

- [Chip datasheets](datasheets/README.md) — offline PDF vault for selected MPNs
- [App notes](appnotes/) — supporting application notes (e.g. LTC AN13)
- [Images](img/) — photos and annotations of the physical core plane
