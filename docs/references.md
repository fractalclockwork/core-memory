# References

## Core plane (physical evidence)

Citations `[cite: 1]` and `[cite: 2]` in [design_spec.md](design_spec.md) refer to inspection of the existing 9″ core PCB:

1. **Top face / primary inspection** — odd-numbered edge contacts on the top face; XA/XB/YA/YB labeling; YA65–YA66 bare-wire shunt folding the sense loop. See [img/top.jpeg](img/top.jpeg), [img/core_pcb_top.png](img/core_pcb_top.png), and the annotated GIMP source [img/core_pcb.xcf](img/core_pcb.xcf).
2. **Bottom face** — even-numbered contacts on the bottom face; complementary view of the fold and connector stagger. See [img/bot.jpeg](img/bot.jpeg), [img/core_pcb_bot_mirror.png](img/core_pcb_bot_mirror.png).

## Application notes

| ID | Document | Archive |
|----|----------|---------|
| AN13 | Linear Technology AN13, *High Speed Comparator Techniques* (LT1016-era methods still relevant to sense-front-end layout and strobing) | [appnotes/an13f.pdf](appnotes/an13f.pdf) |

## Chip datasheets

Manufacturer PDFs for selected MPNs are archived under [datasheets/](datasheets/README.md). Prefer those local copies for offline work; source URLs are recorded in the datasheet index.

## Project documents

| Document | Role |
|----------|------|
| [theory_of_operation.md](theory_of_operation.md) | Read/write cycle narrative |
| [regions.md](regions.md) | Block / stage map |
| [design_choices.md](design_choices.md) | Architecture rationale |
| [component_selection.md](component_selection.md) | Part choices |
| [design_spec.md](design_spec.md) | Normative interface and timing |
| [../kicad/core/core.kicad_sch](../kicad/core/core.kicad_sch) | Schematic ground truth for Stages 1–2 |
