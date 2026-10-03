# Major Regions

Functional blocks of the driver system and the core-plane interface. Normative connector geometry is in [design_spec.md](design_spec.md). Schematic ground truth: [kicad/core/core.kicad_sch](../kicad/core/core.kicad_sch).

## Block overview

```mermaid
flowchart TB
  PIO[Timing controller RP2040 PIO]
  Decode[Decode Block N/n]
  Drive[Drive Block N/n]
  CCS[CCS Ic/2 sink]
  Sense[Sense amp latch]
  Beads[Magnetic Cores MCE]
  Inhibit[Inhibit drive]
  Plane[Core plane XA/XB YA/YB]

  PIO --> Decode
  Decode --> Drive
  Drive --> Plane
  Drive --> CCS
  Plane --> Beads
  Beads --> Sense
  PIO --> Sense
  PIO --> Inhibit
  Inhibit --> Plane
  Inhibit --> CCS
```

## Region map

| Block | On sheet | Primary parts | Role |
|-------|----------|---------------|------|
| **Sense** | [`sense.kicad_sch`](../kicad/core/sense.kicad_sch) | TLV3501, BAT54S, 74AHC74, 1k iso | Differential sense across YB65/66; clamp; strobe latch to DOUT |
| **Magnetic Cores** | [`ferrite_beads.kicad_sch`](../kicad/core/ferrite_beads.kicad_sch) | MCE×4, soft mid R1 | 2×2 plane model; XA→XB / YA→YB; diagonal sense + center tap |
| **CCS** | [`ccs.kicad_sch`](../kicad/core/ccs.kicad_sch) | TL431, Bourns 3296W, OPA192, IRLZ44N, 1 Ω sense | Regulated half-select return for low-side drivers |
| **Inhibit** | [`inhibit.kicad_sch`](../kicad/core/inhibit.kicad_sch) | FDS8958A, TC4427A×2, 2N7002 invert | Series \(-I_c/2\) on folded sense (YB65→fold→YB66→CCS); no 4th inhibit wire |
| **Drive** | Mid (sheet ×1) | `drive_block` | One TC4427A + FDS8958A + local VDRIVE C30/C31; pins `N_*` / `NAn`/`NBn`; root wires X0 FWD |
| **Decode CTRL** | [`decode_ctrl.kicad_sch`](../kicad/core/decode_ctrl.kicad_sch) | J40–J54, R40–R54 | ADDR + `DEC_EN` / `FWD_EN_n` / `REV_EN_n` headers |
| **Decode** | Lower (sheet ×1) | `decode_block` | One axis: 138 HS + 238 LS + local +3V3 C19/C20; pins `N_*`; root wires X FWD |
| **Decoupling Logic** | Bottom (sheet) | `decoupling_logic` | +3V3/+5V bypass (Sense, Latch, CCS) |
| **Decoupling VDRIVE** | Bottom (sheet) | `decoupling_vdrive` | VDRIVE 100n+1u for Inhibit TC4427s (U7/U8) |
| Plane connectors | Lib + footprints | CoreEdge XA/XB 64, YA/YB 66 | Dual-readout staggered card edge to the 9″ plane |
| Timing controller | Spec only | RP2040 / Pico (off-board or later) | Deterministic READ / STROBE / INHIBIT / WRITE |
| Testability | Partial | Keystone-style TPs; 2N7002 + LEDs planned | TP1 DOUT, TP2 Isense present; decoder/data LEDs not yet |

## Sense

Hierarchical page [`sense.kicad_sch`](../kicad/core/sense.kicad_sch) (root sheet **Sense**). Pins: `YB65`/`YB66` only. `SENSE_STROBE` / `DOUT` are global labels.

- Differential inputs from the folded loop (1 kΩ isolation into the comparator)
- BAT54S clamps to protect the amp during inhibit spikes
- TLV3501 comparator → 74AHC74 clocked by SENSE STROBE

The plane model (MCE) and soft mid-bias live on **Magnetic Cores**. See [theory_of_operation.md](theory_of_operation.md) for the strobe window and [component_selection.md](component_selection.md) §4 for part rationale.

## Magnetic Cores

Hierarchical page [`ferrite_beads.kicad_sch`](../kicad/core/ferrite_beads.kicad_sch) (root sheet **Magnetic Cores**). Each core is an MCE: the six-pin layout of the old ferrite-bead stand-in, drawn as a diagonal toroid, with the [core-element](core_element_sim.md) SPICE model attached.

**Drive hierarchy pins (0-based matrix only):** `XA0`/`XA1`/`XB0`/`XB1`, `YA0`/`YA1`/`YB0`/`YB1` — same semantic class as physical contacts 1–64, indexed 0–63 in the schematic. These participate in the Drive/Decode pin story.

**Sense / fold nets (not Drive/Decode hierarchy):** `YA65`, `YB65`, `YA66`, `YB66`, `SENSE_FOLD` — physical Y pins 65/66 plus schematic fold-mid; different function (fold + sense/inhibit). On the stand-in sheet they are local labels (and optionally exported for Sense/Inhibit), **not** an extension of the `NAn`/`n` chain. Soft mid R1 10k→AGND at `SENSE_FOLD` (tied to `YA65` for now; plane shunt `YA65`═`YB65`).

2×2 MCE array matching plane markings ([img/top.jpeg](img/top.jpeg)):

```text
        XA0              XA1
         |                |
   YB0 --● MCE00 ---- ● MCE01 -- YA0
         |                |
   YB1 --● MCE10 ---- ● MCE11 -- YA1
         |                |
        XB0              XB1
```

- **X** top→bottom: `XA0`→MCE00→MCE10→`XB0`; `XA1`→MCE01→MCE11→`XB1`
- **Y** right→left: `YA0`→MCE01→MCE00→`YB0`; `YA1`→MCE11→MCE10→`YB1`
- **Sense (two loops + fold):**
  - YA half: `YA66` ↔ MCE11 ↔ MCE00 ↔ `YA65`
  - YB half: `YB66` ↔ MCE01 ↔ MCE10 ↔ `YB65`
  - Fold shunt: `YA65`═`YB65` + R1 10k→AGND
  - Full series path: `YA66` → YA half → fold → YB half → `YB66`
- **Symbol:** diagonal ellipse (toroid). X1/X2 top/bot, Y1/Y2 left/right, S1/S2 on LL→UR diagonal; **MCE01** and **MCE10** mirrored about Y

Each X/Y line pierces only the cores on its column/row. Regen baseline: [`gen_ferrite_beads_page.py`](../kicad/scripts/gen_ferrite_beads_page.py) `--phase 2` (hand-tuned sense fold may supersede the generator).

## CCS

Hierarchical page [`ccs.kicad_sch`](../kicad/core/ccs.kicad_sch) (root sheet **CCS**). Pin: `CCS_RET` (shared with Drive + Inhibit).

Common low-side return through a linear MOSFET throttle. The OPA192 closes the loop around the 1 Ω sense resistor so pulse current stays at the trimpot setpoint despite inductive kick. Heat in the throttle MOSFET is expected; package choice (IRLZ44N or alternate) must allow linear-region dissipation.

## Inhibit

Hierarchical page [`inhibit.kicad_sch`](../kicad/core/inhibit.kicad_sch) (root sheet **Inhibit**). Pins: `YB65`/`YB66`, `CCS_RET`, `VDRIVE`; `INH_EN_n` via on-page header J5.

Reuses the folded sense path (`YA66` ↔ `YB66` via `YA65`═`YB65`; bring-up may still wire Inhibit to `YB65`/`YB66` for the YB half only). Soft mid (Magnetic Cores) + 1 kΩ iso (Sense) keep inhibit off AGND and off `SENSE_*`. Both gate drivers are TC4427A: HS←`INH_EN_n`, LS←`INH_LS_en` (2N7002 invert). Polarity convention relative to READ remains open ([design_choices.md](design_choices.md)).

## Drive Block (1×1)

The sheet is a **function**; root wires are the **call arguments**. Define once with `N`/`n` pins; instantiate on root (today X0 FWD). Scale later with KiCad buses and PCB **Replicate Layout** — see [naming.md](naming.md).

| Sheet | File | Contents |
|-------|------|----------|
| **Drive Block** | [`drive_block.kicad_sch`](../kicad/core/drive_block.kicad_sch) | One half-bridge: TC4427A (HS+LS) + FDS8958A + SS14×2 |
| Root | [`core.kicad_sch`](../kicad/core/core.kicad_sch) | 1× `drive_block` — X0 FWD bring-up only |

Pin tokens: **`N`** = axis (`X`/`Y`), **`n`** = line (`0`…`63`). Hierarchical pins:

| Pin | Role |
|-----|------|
| `N_HSn` | HS gate input (active-low from 74AHC138) |
| `N_LSn` | LS gate input (active-high from 74AHC238) |
| `NAn` | Plane HS end (P-FET via SS14) |
| `NBn` | Plane LS end (N-FET via SS14) |
| `VDRIVE` / `CCS_RET` | Shared rails |

Parent polarity suffixes stay on the concrete nets for now. Current root map (X0 FWD):

| Block pin | Parent net |
|-----------|------------|
| `N_HSn` | `X_HS0_n` |
| `N_LSn` | `X_LS0_en` |
| `NAn` | `XA0` |
| `NBn` | `XB0` |

Named instances (`drive_fwd_xn`, `drive_rev_yn`, Y, REV plane-swap) come later. Refs today: U20, Q10.

## Decode Block (8×8 one axis)

Same **function-call** pattern as Drive: one `decode_block` definition; root passes address/enables and receives gate nets such as `X_HS0_n` / `X_LS0_en` (taxonomy: `[N]_[HS|LS][n][r?]_(n|en)`). Buses (`X_HS[0..7]_n`, …) come when cloning past 1×1 — [naming.md](naming.md).

| Sheet | File | Contents |
|-------|------|----------|
| **Decode Block** | [`decode_block.kicad_sch`](../kicad/core/decode_block.kicad_sch) | One axis: 74AHC138 HS + 74AHC238 LS; all Y0–Y7 wired |
| **Decode CTRL** | [`decode_ctrl.kicad_sch`](../kicad/core/decode_ctrl.kicad_sch) | J40–J54 headers + R40–R54 fail-safe pull-downs/ups |
| Root | [`core.kicad_sch`](../kicad/core/core.kicad_sch) | Decode CTRL + 1× `decode_block` — X FWD bring-up |

Pin tokens: **`N`** = axis (`X`/`Y`), **`n`** = HS/LS bank index (`0`…`7`). Hierarchical pins:

| Pin | Role |
|-----|------|
| `ADDR_NH[2:0]` / `ADDR_NL[2:0]` | HS / LS address into the 3-to-8s |
| `BANK_EN` / `DEC_EN` | `~E0` / `E2` ( `~E1`←GND ) |
| `N_HS{0..7}_n` | HS outs (active-low) |
| `N_LS{0..7}_en` | LS outs (active-high) |

`line# = 8·HS + LS`. Parent polarity suffixes stay on concrete nets. Current root map (X FWD):

| Block pin | Parent net |
|-----------|------------|
| `ADDR_NH*` / `ADDR_NL*` | `ADDR_XH*` / `ADDR_XL*` |
| `BANK_EN` | `FWD_EN_n` |
| `DEC_EN` | `DEC_EN` |
| `N_HS{0..7}_n` / `N_LS{0..7}_en` | `X_HS*_n` / `X_LS*_en` |

Y / REV instances (`BANK_EN`←`REV_EN_n`, outs → `*r_*`) come later. Refs today: U11/U12.

**Bench plane map (1×1 drive):** Drive Block still `XA0`/`XB0` only; Magnetic Cores exposes XA0/1 XB0/1 YA0/1 YB0/1; sense on YB65/66 fold.

## Decoupling (Logic / VDRIVE)

Per-IC bypass lives in the reusable blocks; shared rails stay on two hierarchy pages (global power nets; no hierarchical pins):

| Sheet / block | File | Rails / parts |
|---------------|------|---------------|
| **Drive Block** | [`drive_block.kicad_sch`](../kicad/core/drive_block.kicad_sch) | VDRIVE: C30 100n + C31 1u next to TC4427 |
| **Decode Block** | [`decode_block.kicad_sch`](../kicad/core/decode_block.kicad_sch) | +3V3: C19/C20 100n next to U11/U12 |
| **Decoupling Logic** | [`decoupling_logic.kicad_sch`](../kicad/core/decoupling_logic.kicad_sch) | +3V3: C1/C2 (Sense), C3/C4 (Latch); +5V: C5/C6 (CCS) |
| **Decoupling VDRIVE** | [`decoupling_vdrive.kicad_sch`](../kicad/core/decoupling_vdrive.kicad_sch) | VDRIVE: C11–C14 (Inhibit U7/U8) — each 100n+1u pair |

Regen: [`gen_decoupling_pages.py`](../kicad/scripts/gen_decoupling_pages.py) (also regenerates `drive_block` / `decode_block` and strips root caps).

**Connectors** use custom footprints sized from the plane: 32-position dual-readout for X (64 pins), 33-position for Y (66 pins). Pin stagger and first-pin offset are normative in the design spec.

## Plane interface (summary)

| Axis | Connectors | Pins | Notes |
|------|------------|------|-------|
| X | XA, XB | 64 | Drive lines only |
| Y | YA, YB | 66 | **1–64** drive (schematic `YA0`…`YB63`) + **65/66** sense/fold only — not part of Drive/Decode hierarchy |

Physical photos: [img/core_pcb_top.png](img/core_pcb_top.png), [img/core_pcb_bot_mirror.png](img/core_pcb_bot_mirror.png).
