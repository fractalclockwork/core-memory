# Design Choices

Architecture decisions and tradeoffs for the core-plane driver. Part-level picks are in [component_selection.md](component_selection.md).

## Three-wire cores: no separate inhibit winding

Each core carries **X**, **Y**, and **sense** only (classic 3-wire). There is no fourth inhibit wire through the array. WRITE-0 inhibit reuses the sense path at high current; READ uses the same path as a millivolt differential. That time-multiplex forces Stage-1 isolation (1 kΩ), clamps, and soft mid-bias before Stage-5 can source/sink YB65/YB66 into the CCS.

## Folded differential sense (shared READ / inhibit loop)

The plane already folds the sense wire at YA65/66 and presents YB65/66 as a pair. Using that loop as a differential sense input rejects common-mode drive noise that would swamp a single-ended pickup. A dedicated sense-only winding is not available on this hardware, so the driver must protect and bias this shared path for both READ (small-signal) and INHIBIT (high current).

## Steering diodes on the driver board

The core PCB has no discrete diodes on the drive lines. Without Schottky steering at the matrix outputs, unselected lines form sneak paths that steal current and disturb half-select margins. Diodes belong on the driver board at the matrix outputs (SS14/SS16 class), not as a plane rework.

## 8×8 half-select matrix vs 64 line drivers

Driving 64 X and 64 Y lines with one switch each would explode MOSFET and connector fan-out. Grouping each axis into 8 high-side and 8 low-side switches (with direction for READ vs WRITE) yields an 8×8 coincident-current matrix: twelve address bits total, four 3-to-8 decoders, and a compact FDS8958A-based switch farm. Cost is more careful sequencing and mandatory steering diodes.

## Prototype 1×1 before scaling lines

Bring-up proves a full READ → STROBE → INHIBIT → WRITE cycle on one core (X0∩Y0) before cloning matrix FETs. Forward (Stages 3–4) and reverse (Stages 6–7) half-bridges share the same plane nets with swapped diode ends; Stage 8 installs the 74AHC138 ×4 decode path with only Y0 wired, plus FWD/REV OE buffers so polarity is exclusive. Extra 138 outputs and FDS8958A rows/columns come after this 1×1 works.

## Soft mid-bias and input clamps on sense

During inhibit, YB65/YB66 see large excursions. BAT54S clamps dump spikes into the rails; a soft resistive mid-bias to AGND keeps the comparator inputs from floating between cycles. Isolation resistors (e.g. 1 kΩ in Stage 1) limit clamp current into the amp. This favors a modern fast comparator (TLV3501) over older ±supply parts that assumed different front-ends.

## Manual TL431 + trimpot CCS

Bench bring-up needs a knob for \(I_c/2\) while probing cores of uncertain coercivity (400–800 mA full-select estimate). A TL431 reference and multi-turn 3296W divider set the OPA192 target without firmware or a DAC. A later digital setpoint (DAC or PWM + filter) can replace the trimpot once the operating current is known; the MOSFET + sense-resistor power stage stays.

## AHC logic and TC4427A level shift

The timing controller is 3.3 V (RP2040). Matrix gates need fast, hard \(V_{drive}\) edges. 74AHC138 accepts 3.3 V inputs with short propagation delay; TC4427A dual non-inverting drivers supply ampere-class gate current from the drive rail so FDS8958A switches cleanly in tens of nanoseconds. Skipping the gate drivers would leave slow, partial enhancement and mushy half-select pulses.

## RP2040 PIO for timing

READ → strobe → inhibit → WRITE needs fixed delays on the order of hundreds of nanoseconds. Main-CPU GPIO toggling under an OS or interrupt load introduces jitter that corrupts sense windows. PIO state machines give cycle-accurate multi-pin sequences while application code runs elsewhere. Another MCU with equivalent programmable I/O could substitute; the requirement is hardware sequencing, not the Pico brand.

## Decisions still open

| Topic | Notes |
|-------|--------|
| Exact \(I_c\) / \(I_c/2\) setpoint | Characterize on the real plane; trimpot covers 200–400 mA half-select for now |
| \(V_{drive}\) rail voltage | Must satisfy MOSFET gate drive, diode drops, and inductive headroom; value not frozen |
| Inhibit polarity convention | Which of YB65/YB66 is source vs sink relative to READ polarity |
| Inhibit switch topology | Discrete path vs reuse of matrix/CCS resources |
| On-board vs off-board RP2040 | Pico header vs soldered MCU vs external timing pod |
| Final CCS throttle MOSFET | IRLZ44N on Stage 2; AOD4184 (or similar) remains a thermal/package alternate |
| Diagnostic LED set | Planned on decoder outputs and DOUT; not yet on the schematic |
