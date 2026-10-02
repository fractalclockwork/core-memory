# Theory of Operation

How the driver board reads and writes a single bit on the 64×64 ferrite core plane.

## Core physics (brief)

Each ferrite core stores one bit as magnetic remanence in one of two directions. A full-select current \(I_c\) through a core flips its state; half-select \(I_c/2\) does not. Addressing one bit means driving \(I_c/2\) on one X line and \(I_c/2\) on one Y line so only the intersection sees \(I_c\).

Readout is destructive: the READ pulse forces the core toward a known polarity. If the core was previously the opposite polarity, it flips and induces a millivolt-scale spike on the sense wire; if it was already that polarity, the spike is negligible. After sensing, a WRITE (restore) pulse returns the desired data, optionally with an INHIBIT current so a restore-to-0 does not flip the core back to 1.

For this plane, expect \(I_c\) in the 400–800 mA range (0.125″ cores), so regulated half-select is about 200–400 mA. See [design_spec.md](design_spec.md) for the normative numbers.

## Three wires per core (no inhibit winding)

Each ferrite core is threaded by exactly **three** wires:

| Wire | Count on plane | Role |
|------|----------------|------|
| **X** | 64 lines | Half-select address |
| **Y** | 64 lines | Half-select address |
| **Sense** | One long wire through all 4,096 cores | READ pickup **and** WRITE-0 inhibit |

This is classic 3-wire core memory: there is **no fourth inhibit winding**. Inhibit current is **time-multiplexed onto the sense wire** (high current during WRITE/RESTORE 0; quiet differential sensing during READ). The driver must therefore protect and bias the same YB65/YB66 pins for both regimes.

## Folded sense / inhibit loop

The plane has no separate sense connector pair beyond the Y edge fold. The sense wire snakes through all 4,096 cores, exits at YA65, shunts across to YA66 at the board edge, and returns through the array to YB66. That fold:

- Presents a **balanced differential pair** at YB65 / YB66 for the sense amplifier during READ.
- Lets the same two pins carry **series inhibit** during WRITE: current into YB65, across the YA65/66 shunt, and out YB66 (or reverse), putting all cores in series at \(-I_c/2\).

On the driver board the YA mid is **soft-biased** (10 kΩ → AGND), not hard-tied, so inhibit current completes through the return half and CCS instead of dumping at the fold. Plane photos documenting the shunt and connectors are in [img/](img/); sources are listed in [references.md](references.md).

```mermaid
flowchart LR
  YB65[YB65] --> ArrayA[Sense half A]
  ArrayA --> YA65[YA65]
  YA65 --> Shunt[YA65/66 shunt to AGND]
  Shunt --> YA66[YA66]
  YA66 --> ArrayB[Sense half B]
  ArrayB --> YB66[YB66]
  YB65 -.-> SenseAmp[Differential sense amp]
  YB66 -.-> SenseAmp
```

## Access cycle

Every access is a READ / RESTORE sequence. Software bit-banging on a general-purpose MCU is too jittery; the plan is deterministic sequencing from RP2040 PIO (or equivalent hardware state machine).

```mermaid
sequenceDiagram
  participant X as X matrix
  participant Y as Y matrix
  participant S as Sense latch
  participant I as Inhibit path
  participant CCS as Ic/2 CCS

  Note over X,CCS: READ phase
  X->>CCS: drive -Ic/2 on selected X
  Y->>CCS: drive -Ic/2 on selected Y
  Note over S: wait ~150-300 ns for ringing
  S->>S: SENSE STROBE clocks comparator into 74AHC74

  alt restore or write 0
    I->>I: INHIBIT -Ic/2 on YB65 to YB66
  end

  Note over X,CCS: WRITE phase
  X->>CCS: drive +Ic/2 on selected X
  Y->>CCS: drive +Ic/2 on selected Y
```

1. **READ** — Drive \(-I_c/2\) into the addressed X and Y lines (forward polarity for read). Only the selected core sees full \(I_c\).
2. **SENSE STROBE** — After ~150–300 ns for capacitive ringing to settle, clock the D flip-flop that samples the TLV3501 comparator across YB65/YB66.
3. **INHIBIT** — If writing or restoring a 0, drive \(-I_c/2\) through the folded sense path (YB65 ↔ YB66 via YA shunt) so the subsequent WRITE cannot flip that core to 1.
4. **WRITE** — Drive \(+I_c/2\) into the same X and Y lines (reverse polarity) to restore or write 1 when inhibit is off.

## Constant-current sink

Low-side matrix returns share an adjustable constant-current sink that holds \(I_c/2\) flat into the inductive load. The CCS block on the schematic implements this with a TL431 reference, multi-turn trimpot, OPA192 feedback amp, IRLZ44N throttle MOSFET, and a 1 Ω sense resistor. Without regulation, pulse amplitude would wander with temperature, MOSFET Rds(on), and wiring resistance, corrupting half-select margins.

## Timing controller

Sub-microsecond edges and fixed delays (strobe window, inhibit overlap, write width) need cycle-accurate hardware. The design targets Raspberry Pi Pico / RP2040 PIO blocks driven by tight C or assembly, independent of the main CPU’s interrupt load. Firmware is out of scope for this document set; the electrical contract is in [design_spec.md](design_spec.md) §5.
