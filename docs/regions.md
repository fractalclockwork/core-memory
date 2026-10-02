# Major Regions

Functional blocks of the driver system and the core-plane interface. Normative connector geometry is in [design_spec.md](design_spec.md). Schematic ground truth: [kicad/core/core.kicad_sch](../kicad/core/core.kicad_sch).

## Block overview

```mermaid
flowchart TB
  PIO[Timing controller RP2040 PIO]
  Decode[Decode FWD/REV 138 banks]
  DriveFwd[Drive FWD matrix plus gate]
  DriveRev[Drive REV matrix plus gate]
  CCS[CCS Ic/2 sink]
  Sense[Sense bowtie latch]
  Inhibit[Inhibit drive]
  Plane[Core plane XA/XB YA/YB]

  PIO --> Decode
  Decode --> DriveFwd
  Decode --> DriveRev
  DriveFwd --> Plane
  DriveRev --> Plane
  DriveFwd --> CCS
  DriveRev --> CCS
  Plane --> Sense
  PIO --> Sense
  PIO --> Inhibit
  Inhibit --> Plane
  Inhibit --> CCS
```

## Region map

| Block | On sheet | Primary parts | Role |
|-------|----------|---------------|------|
| **Sense** | Upper left | TLV3501, BAT54S, 74AHC74, soft mid bias | Differential sense across YB65/66; clamp; strobe latch to DOUT |
| **CCS** | Below Sense | TL431, Bourns 3296W, OPA192, IRLZ44N, 1 Ω sense | Regulated half-select return for low-side drivers |
| **Inhibit** | Below CCS | FDS8958A, TC4427A/TC4426A on `INH_EN_n` | Series \(-I_c/2\) on folded sense (YB65→fold→YB66→CCS); no 4th inhibit wire |
| **Drive FWD** | Upper mid | FDS8958A, SS14, TC4427A/TC4426A | Forward READ half-bridges + gate drive on XA0/XB0 & YA0/YB0 |
| **Drive REV** | Upper right | FDS8958A, SS14, TC4427A/TC4426A | Reverse WRITE half-bridges + gate drive (ends swapped) |
| **Decode** | Lower band (Y0 only) | 74AHC138 ×8 (FWD×4 + REV×4) | Shared ADDR; bank enables → Drive FWD/REV `*_n` / `*r_n` |
| Plane connectors | Lib + footprints | CoreEdge XA/XB 64, YA/YB 66 | Dual-readout staggered card edge to the 9″ plane |
| Timing controller | Spec only | RP2040 / Pico (off-board or later) | Deterministic READ / STROBE / INHIBIT / WRITE |
| Testability | Partial | Keystone-style TPs; 2N7002 + LEDs planned | TP1 DOUT, TP2 Isense present; decoder/data LEDs not yet |

## Sense

On the sheet:

- Differential inputs from the folded loop (bowtie feedback / isolation network into the comparator)
- BAT54S clamps to protect the amp during inhibit spikes
- Soft mid-bias to AGND so the loop sits at a safe common-mode
- TLV3501 comparator → 74AHC74 clocked by SENSE STROBE

See [theory_of_operation.md](theory_of_operation.md) for the strobe window and [component_selection.md](component_selection.md) §4 for part rationale.

## CCS

Common low-side return through a linear MOSFET throttle. The OPA192 closes the loop around the 1 Ω sense resistor so pulse current stays at the trimpot setpoint despite inductive kick. Heat in the throttle MOSFET is expected; package choice (IRLZ44N or alternate) must allow linear-region dissipation.

## Inhibit

Reuses the sense wire (YB65 → fold at YA65/66 → YB66 → CCS). Soft mid + 1 kΩ iso (Sense) keep inhibit off AGND and off `SENSE_*`. Polarity convention relative to READ remains open ([design_choices.md](design_choices.md)).

## Drive FWD / Drive REV (1×1)

**Drive FWD** — X0/Y0 half-bridges (FDS8958A + SS14) plus TC4427A/TC4426A with 10 kΩ pull-ups on `*_n` (FETs above, gate drive below in one region).

**Drive REV** — second FDS8958A pair with ends swapped (HS→XB0/YB0, LS←XA0/YA0), shared `CCS_RET`, plus TC442x on `*r_n`.

## Decode (prototype)

74AHC138 ×4 FWD (U11–U14) + ×4 REV (U15–U18); only `~Y0` wired directly to `*_n` / `*r_n`. Enables: `~E0`←`FWD_EN_n` or `REV_EN_n`, `~E1`←GND, `E2`←`DEC_EN` (do not assert both banks). `ADDR_A[2:0]` default 000 via pull-downs; `DEC_EN` defaults off. No 74AHC125. Scaling to 8×8 = wire more 138 outputs + more FDS8958A banks.

**Bench plane map (1×1):** drive `XA0`/`XB0`/`YA0`/`YB0`; sense still on YB65/66 fold. Full cycle: CCS setpoint → FWD READ → strobe → INHIBIT → REV WRITE.

**Connectors** use custom footprints sized from the plane: 32-position dual-readout for X (64 pins), 33-position for Y (66 pins). Pin stagger and first-pin offset are normative in the design spec.

## Plane interface (summary)

| Axis | Connectors | Pins | Notes |
|------|------------|------|-------|
| X | XA, XB | 64 | Drive lines only |
| Y | YA, YB | 66 | 64 drive + YA/YB 65–66 folded sense (READ + inhibit; no 4th wire) |

Physical photos: [img/core_pcb_top.png](img/core_pcb_top.png), [img/core_pcb_bot_mirror.png](img/core_pcb_bot_mirror.png).
