# Magnetic Core Memory Drive and Sense Circuit: Design Specification

Normative plane interface, drive architecture, and timing contract. Narrative context: [theory_of_operation.md](theory_of_operation.md). Citation keys `[cite: 1]` / `[cite: 2]` are defined in [references.md](references.md).

## 1. Physical Parameters & Interface Specification
* **PCB Dimensions:** The magnetic core plane is constructed on a 9-inch square PCB featuring four edge connector interfaces labeled XA, XB, YA, and YB [[cite: 1](references.md#core-plane-physical-evidence)].
* **Connector Type:** Dual-readout staggered edge connector.
* **Contact Dimensions:** Pins are 0.125" wide with a 0.1875" (3/16") center-to-center pitch on each face.
* **Staggered Layout:** Odd-numbered pins are located on the top face [[cite: 1](references.md#core-plane-physical-evidence)], and even-numbered pins are located on the bottom face [[cite: 2](references.md#core-plane-physical-evidence)]. Pin 1 begins 1.3125" (1-5/16") from the right edge, offsetting the top and bottom contacts by exactly 0.0625" to maximize contact area while preventing wiper shorts during insertion.
* **Axis Connectors:**
    * **X-Axis (XA, XB):** 64 pins total. Requires a 32-position, dual-readout staggered receptacle.
    * **Y-Axis (YA, YB):** 66 pins total. Requires a 33-position, dual-readout staggered receptacle.
* **Matrix Capacity:** 64×64 bidirectional drive lines yield exactly 4,096 cores (512 bytes).
* **Pin numbering vs address:** Physical edge contacts are labeled **1–64** (drive) plus Y **65/66** (sense). Schematic and firmware address drive lines **0–63**. Mapping: physical pin \(p\) ↔ logical index \(p-1\). Pins 65/66 are **not** drive lines and are **not** part of the Drive/Decode hierarchical pin chain — see §1.1 and §2.
* **Midpoint Shunt:** Sense is two half-loops (`YA65`↔`YA66` and `YB65`↔`YB66`) joined by a fold shunt **`YA65`═`YB65`**. The full series path is `YA66` → YA half → fold → YB half → `YB66`. (Earlier text that described an YA65–YA66 bare-wire fold was incorrect.) [[cite: 1](references.md#core-plane-physical-evidence), [cite: 2](references.md#core-plane-physical-evidence)]

### 1.1 Three naming layers (keep separate)

Normative net grammar, block ABI, buses, and scale path: **[naming.md](naming.md)**. Mixing physical (1–64 / Y 65–66), syntax (`XA0`…, block `N`/`n`), and semantic (drive vs sense/fold) layers is a recurring source of schematic and doc bugs. Drive Block / Decode Block hierarchical pins only cover the matrix — do not extend that chain to 65/66.

## 2. Sense and Inhibit Architecture (Pins 65 & 66)
Each core is a **three-wire** element (X, Y, sense). There is **no separate inhibit winding**; inhibit is series current on the folded sense wire, time-multiplexed with READ.
* **Two half-loops + fold:** YA loop `YA65`↔`YA66`; YB loop `YB65`↔`YB66`; fold shunt **`YA65`═`YB65`**. Full path ends: `YA66` / `YB66`.
* **Common-Mode Noise Rejection (Read Phase):** A high-speed differential comparator (schematic: TLV3501; see [component_selection.md](component_selection.md)) across the fold ends isolates the millivolt flip spike. Classic techniques: [AN13](appnotes/an13f.pdf). Temporary 1×1 attach points: [implementation_summary.md § Bring-Up Deviations](implementation_summary.md#bring-up-deviations).
* **Center-Tap Bias:** Soft-bias the fold mid `YA65`/`YB65` (schematic: 10 kΩ → AGND), not a hard AGND short, so inhibit current traverses both halves into the CCS.
* **Series Inhibit Drive (Write Phase):** Source/sink \(-I_c/2\) on `YA66`↔`YB66` so current flows one half, crosses `YA65`═`YB65`, and returns through the other half — all cores in series.

## 3. Drive Architecture (64x64 Matrix)
* **Matrix Structure:** Group the 64 lines per axis into 8 rows and 8 columns. Implement 8 High-Side source switches and 8 Low-Side sink switches per axis, per direction (Forward for READ, Reverse for WRITE).
* **Address Decoding:** A 12-bit address word seamlessly maps to this geometry. 6 bits decode the X-axis (3 bits for High-Side, 3 bits for Low-Side), and 6 bits decode the Y-axis. Standard 3-to-8 line decoders (74AHC138 HS / 74AHC238 LS; see [component_selection.md](component_selection.md)) control the matrix.
* **Steering Diodes:** Because there are no discrete diodes populated on the memory plane itself [[cite: 1](references.md#core-plane-physical-evidence), [cite: 2](references.md#core-plane-physical-evidence)], fast-recovery Schottky diodes must be placed on the driver board at the output of the switch matrices to prevent back-feeding and "sneak paths" through unselected core lines.

## 4. Current Recommendations ($I_c$)
* **Coercive Current ($I_c$):** Given the 0.125-inch core diameter, expect a full-select current between 400mA and 800mA. 
* **Drive Regulation:** The half-select current ($I_c/2$) of 200mA to 400mA must be strictly regulated. Implement an adjustable constant-current sink on the common return path of the Low-Side drivers. A power op-amp driving an N-channel MOSFET, monitored by a low-ohm sense resistor, ensures the current remains perfectly flat despite the inductive load.

## 5. Timing & Sequencing
Core memory operations require sub-microsecond, deterministic pulse sequencing. A READ destroys the data, so every access is a READ / RESTORE cycle.
1. **READ Phase:** Drive $-I_c/2$ into the target X and Y lines. 
2. **SENSE STROBE:** Wait ~150-300ns for capacitive ringing to settle, then clock the D-flip-flop connected to the YB 65/66 differential comparator.
3. **INHIBIT Phase:** If writing/restoring a '0', drive $-I_c/2$ on the full fold ends `YA66`↔`YB66` (1×1 bring-up may use the YB half only — [Bring-Up Deviations](implementation_summary.md#bring-up-deviations)).
4. **WRITE Phase:** Drive $+I_c/2$ into the target X and Y lines.

Standard software bit-banging will introduce cycle jitter that corrupts memory. Utilizing hardware-level programmable state machines—such as the PIO (Programmable I/O) blocks on an RP2040/Raspberry Pi Pico—driven by tight C or Assembly routines allows for multi-phase sub-microsecond sequence execution with absolute cycle accuracy independent of the main CPU clock.
