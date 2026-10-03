# Design Documentation

Driver-board documentation for the 64×64 magnetic core plane.

## Reading order

1. [Signal naming](naming.md) — net taxonomy, block ABI, hierarchy scale path
2. [Theory of operation](theory_of_operation.md) — how a bit is read and written
3. [Major regions](regions.md) — functional circuit blocks on the schematic
4. [Implementation summary](implementation_summary.md) — present 1×1 prototype blocks + parts used
5. [Design choices](design_choices.md) — architecture rationale and open decisions
6. [Component selection](component_selection.md) — parts and why they were chosen
7. [Design specification](design_spec.md) — normative plane / connector / timing contract
8. [References](references.md) — bibliography and image sources

## Core element model

[Core-element simulation](core_element_sim.md) — isolated ngspice model of one 50-mil three-wire core, and how its sense pulse and B–H loop compare with the coincident-current literature. Not part of the driver schematic.

## Archives

- [Chip datasheets](datasheets/README.md) — offline PDF vault for selected MPNs
- [App notes](appnotes/) — supporting application notes (e.g. LTC AN13)
- [Images](img/) — photos and annotations of the physical core plane
