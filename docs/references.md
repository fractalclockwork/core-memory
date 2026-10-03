# References

## Core plane (physical evidence)

Citations `[cite: 1]` and `[cite: 2]` in [design_spec.md](design_spec.md) refer to inspection of the existing 9″ core PCB:

1. **Top face / primary inspection** — odd-numbered edge contacts on the top face; XA/XB/YA/YB labeling; four sense/inhibit terminals `YA65`, `YA66`, `YB65`, `YB66` (two independent 2,048-core loops; the series jumper is on the driver, not the plane). See [img/top.jpeg](img/top.jpeg), [img/core_pcb_top.png](img/core_pcb_top.png), and the annotated GIMP source [img/core_pcb.xcf](img/core_pcb.xcf).
2. **Bottom face** — even-numbered contacts on the bottom face; complementary view of the sense terminals and connector stagger. See [img/bot.jpeg](img/bot.jpeg), [img/core_pcb_bot_mirror.png](img/core_pcb_bot_mirror.png).

## Coincident-current cores

Cited from [core_element_sim.md](core_element_sim.md). The 20–50 mV and 1 µs marks on the plot are the single-core targets used to size the model, not quotations from these papers.

1. J. W. Forrester, “Digital information storage in three dimensions using magnetic cores,” *J. Appl. Phys.*, vol. 22, no. 1, pp. 44–48, Jan. 1951.
2. W. N. Papian, “A coincident-current magnetic memory cell for the storage of digital information,” *Proc. IRE*, vol. 40, no. 4, pp. 475–478, Apr. 1952.
3. J. A. Rajchman, “A myriabit magnetic-core matrix memory,” *Proc. IRE*, vol. 41, no. 10, pp. 1407–1421, Oct. 1953.
4. N. Menyuk and J. B. Goodenough, “Magnetic materials for digital-computer components. I. A theory of flux reversal in polycrystalline ferromagnetics,” *J. Appl. Phys.*, vol. 26, no. 1, pp. 8–18, Jan. 1955.
5. J. H. Chan, A. Vladimirescu, X.-C. Gao, P. Liebmann, and J. Valainis, “Nonlinear transformer model for circuit simulation,” *IEEE Trans. Computer-Aided Design*, vol. 10, no. 4, pp. 476–482, Apr. 1991.

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
| [regions.md](regions.md) | Functional block map |
| [design_choices.md](design_choices.md) | Architecture rationale |
| [component_selection.md](component_selection.md) | Part choices |
| [design_spec.md](design_spec.md) | Normative interface and timing |
| [core_element_sim.md](core_element_sim.md) | Single-core ngspice model and literature comparison |
| [../kicad/core/core.kicad_sch](../kicad/core/core.kicad_sch) | Schematic ground truth (functional blocks) |
| [../kicad/core_element_sim/](../kicad/core_element_sim/) | Isolated core-element KiCad project |
