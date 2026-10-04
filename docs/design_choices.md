# Design Choices

Architecture decisions and tradeoffs for the core-plane driver. Part-level picks are in [component_selection.md](component_selection.md). Net grammar, hierarchical block ABI, and the bus / Replicate Layout scale path: [naming.md](naming.md).

## Three-wire cores: no separate inhibit winding

Each core carries **X**, **Y**, and **sense** only (classic 3-wire). There is no fourth inhibit wire through the array. WRITE-0 inhibit reuses the sense path at high current; READ uses the same path as a millivolt differential. That time-multiplex forces Sense-block isolation (1 kΩ), clamps, and soft center-tap bias before Inhibit can source `YA65` and sink `YB66` into the CCS.

## Series differential sense (shared READ / inhibit loops)

The plane has two independent sense/inhibit loops (`YA65`↔`YA66` and `YB65`↔`YB66`), 2,048 cores each. The driver joins them with an external center-tap jumper **`YA66`═`YB65`** and uses the outer ends (`YA65`/`YB66`) as a differential pair. That rejects common-mode drive noise that would swamp a single-ended pickup, and it keeps a single TLV3501 and a single inhibit driver. A dedicated sense-only winding is not available on this hardware, so the driver must protect and bias this shared path for both READ (small-signal) and INHIBIT (high current).

Each loop’s DCR and inductance are half of a continuous 4,096-core weave. Wiring the loops in series presents that full-array L and DCR to the driver, so \(V_{drive}\) and the CCS current stay at \(I_c/2\).

If the series-loop noise floor is too high on the bench, the deferred alternative is to drive and sense the loops in parallel: `YA65` and `YB65` both fed from the inhibit P-FET, `YA66` and `YB66` both returned to `CCS_INH` (that sink then takes \(I_c\), and \(V_{drive}\) can be lower), plus a second TLV3501 whose output is OR’d with the first. That is not the 2×2 sim fixture or the initial 8×8 build.

## Steering diodes on the driver board

The core PCB has no discrete diodes on the drive lines. Without Schottky steering at the matrix outputs, unselected lines form sneak paths that steal current and disturb half-select margins. Diodes belong on the driver board at the matrix outputs (SS14/SS16 class), not as a plane rework.

## 8×8 half-select matrix vs 64 line drivers

Driving 64 X and 64 Y lines with one switch each would explode MOSFET and connector fan-out. Grouping each axis into 8 high-side and 8 low-side switches (with direction for READ vs WRITE) yields an 8×8 coincident-current matrix: twelve address bits total, eight 3-to-8 decoders (FWD×4 + REV×4), and a compact FDS8958A-based switch farm. Cost is more careful sequencing and mandatory steering diodes.

## Prototype 1×1 before scaling lines

Bring-up proves a full READ → STROBE → INHIBIT → WRITE cycle on the 2×2 before the 64-line banks. Drive is one hierarchical page [`drive_block.kicad_sch`](../kicad/core/drive_block.kicad_sch): a TC4427A (HS+LS) plus one FDS8958A, with switch-node pins `N_HS_OUT` / `N_LS_OUT`. The SS14s are on [`steer_2x2.kicad_sch`](../kicad/core/steer_2x2.kicad_sch). Decode is one hierarchical page [`decode_block.kicad_sch`](../kicad/core/decode_block.kicad_sch): one axis = 74AHC138 HS + 74AHC238 LS (`ADDR_NH/NL`, `N_HS{0..7}_n`, `N_LS{0..7}_en`; line# = 8·HS + LS). Root places four decode calls and eight drive calls. REV binds `BANK_EN`←`REV_EN_n` and remaps outs to `*r_*`. HS groups 1–7 and LS groups 2–7 are the later fan-out.

## Soft mid-bias and input clamps on sense

During inhibit, the outer ends see large excursions. BAT54S clamps dump spikes into the rails; a soft resistive bias from the center tap (`YA66`/`YB65`) to AGND keeps the comparator inputs from floating between cycles. Isolation resistors (e.g. 1 kΩ in Sense) limit clamp current into the amp (~8 mA into clamps at 12 V). This favors a modern fast comparator (TLV3501) over older ±supply parts that assumed different front-ends.

A 1:1 pulse-transformer sense front-end was considered and **deferred**: on this 3-wire plane the same fold ends carry series inhibit, so a low-DCR primary across those pins would shunt inhibit current around the cores. AC-coupling the primary would still slam inhibit edges onto the secondary and force clamps/blanking, erasing the BOM win. DC-coupled Sense stays.

## Manual TL431 + trimpot CCS

Bench bring-up needs a knob for \(I_c/2\) while probing cores of uncertain coercivity (400–800 mA full-select estimate). A TL431 reference and multi-turn 3296W divider set the OPA192 target without firmware or a DAC. A later digital setpoint (DAC or PWM + filter) can replace the trimpot once the operating current is known; the MOSFET + sense-resistor power stage stays.

## AHC logic and TC4427A level shift

The timing controller is 3.3 V (RP2040). Matrix gates need fast, hard \(V_{drive}\) edges. 74AHC138/238 accept 3.3 V inputs with short propagation delay; TC4427A dual non-inverting drivers supply ampere-class gate current from the drive rail so FDS8958A switches cleanly in tens of nanoseconds. Low-side decode uses 74AHC238 (active-high) so every gate driver can be TC4427A — TC4426A is not stocked.

FWD vs REV steering uses duplicated decoder banks gated by `FWD_EN_n` / `REV_EN_n`. That removes a mux layer and keeps fail-safe behavior native (disabled 138 → HIGH → P off; disabled 238 → LOW → N off).

## RP2040 PIO for timing

READ → strobe → inhibit → WRITE needs fixed delays on the order of hundreds of nanoseconds. Main-CPU GPIO toggling under an OS or interrupt load introduces jitter that corrupts sense windows. PIO state machines give cycle-accurate multi-pin sequences while application code runs elsewhere. Another MCU with equivalent programmable I/O could substitute; the requirement is hardware sequencing, not the Pico brand.

## Decisions still open

| Topic | Notes |
|-------|--------|
| Exact \(I_c\) / \(I_c/2\) setpoint | Characterize on the real plane; trimpot covers 200–400 mA half-select for now |
| \(V_{drive}\) rail voltage | Must satisfy MOSFET gate drive, diode drops, and inductive headroom; value not frozen |
| Inhibit polarity vs READ | Source is `YA65` and sink is `YB66`; whether that direction matches the core’s read polarity is still a bench question |
| Inhibit switch topology | Discrete path vs reuse of matrix/CCS resources |
| On-board vs off-board RP2040 | Pico header vs soldered MCU vs external timing pod |
| Final CCS throttle MOSFET | IRLZ44N in CCS; AOD4184 (or similar) remains a thermal/package alternate |
| Diagnostic LED set | Planned on decoder outputs and DOUT; not yet on the schematic |
