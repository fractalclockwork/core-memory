# Component Selection

Part choices for the core-memory driver. Architecture rationale is in [design_choices.md](design_choices.md). Offline PDFs live in [datasheets/](datasheets/README.md).

Schematic ground truth for the 1×1 prototype (functional blocks): [kicad/core/core.kicad_sch](../kicad/core/core.kicad_sch). Present wiring map: [implementation_summary.md](implementation_summary.md).

---

## 1. Address Decoding & Level Shifting

The 3.3 V logic from the timing controller must become high-current, high-voltage gate drive so the matrix MOSFETs snap open and closed cleanly.

| MPN | Role | Package | Key params | Alternate | Datasheet |
|-----|------|---------|------------|-----------|-----------|
| 74AHC138 | 3-to-8 decoder HS (×4: FWD/REV × X-H/Y-H) | SOIC-16 | Active-low Y0–Y7; bank enables | 74HC138 | [sn74ahc138.pdf](datasheets/sn74ahc138.pdf) |
| 74AHC238 | 3-to-8 decoder LS (×4: FWD/REV × X-L/Y-L) | SOIC-16 | Active-high Y0–Y7; same enables as 138 | 74HC238 | [sn74ahc238.pdf](datasheets/sn74ahc238.pdf) |
| TC4427A | Dual non-inverting gate driver (all channels) | SOIC-8 / DIP-8 | 1.5 A peak from \(V_{drive}\) | — (TC4426A removed) | [tc4427a.pdf](datasheets/tc4427a.pdf) |

AHC decoders accept 3.3 V inputs. **HS** uses 74AHC138 (active-low Y + TC4427 → P-FET). **LS** uses 74AHC238 (active-high Y + TC4427 → N-FET) so the board stocks only TC4427A gate drivers. Same enable wiring on both (`~E0`/`~E1`/`E2` family): bank EN, GND, `DEC_EN`. Disabled 138 → Y HIGH (P off); disabled 238 → Y LOW (N off).

**KiCad symbol vs MPN:** sheets use pin-compatible lib_id `74xx:74HC138` / `74xx:74HC238` with Value set to the ordered MPN (`74AHC138` / `74AHC238`). Do not treat the HC lib_id as the BOM part.

---

## 2. The Drive Matrix (64×64)

| MPN | Role | Package | Key params | Alternate | Datasheet |
|-----|------|---------|------------|-----------|-----------|
| FDS8958A | Dual N + P PowerTrench switch | SOIC-8 | One HS + one LS per package; low Rds(on) | Discrete complementary pair | [fds8958a.pdf](datasheets/fds8958a.pdf) |
| SS14 | Steering Schottky | SMA | 1 A, low Vf, fast recovery | SS16 (higher Vr) | [ss14.pdf](datasheets/ss14.pdf) |

One FDS8958A per matrix node keeps layout compact. Schottky steering at matrix outputs blocks sneak paths; the plane has no on-board diodes.

---

## 3. Constant-Current Sink (manual)

Low-side matrix returns share an adjustable CCS so \(I_c/2\) stays flat into the inductive load (target band ~200–400 mA).

| MPN | Role | Package | Key params | Alternate | Datasheet |
|-----|------|---------|------------|-----------|-----------|
| TL431 | Precision shunt reference | SOT-23 / TO-92 | Stable Vref for setpoint divider | TLV431 (lower Vref) | [tl431.pdf](datasheets/tl431.pdf) |
| Bourns 3296W | 10 kΩ multi-turn trimpot | 3296W | Bench adjustment of \(I_c/2\) | 3296Y (side adjust) | [3296.pdf](datasheets/3296.pdf) |
| OPA192 | Feedback error amp | SOIC-8 | 10 MHz GBW, fast slew | OPA191 | [opa192.pdf](datasheets/opa192.pdf) |
| IRLZ44N | Throttle N-MOSFET (CCS) | TO-220 / DPAK family | Linear-region dissipation | AOD4184 | [irlz44n.pdf](datasheets/irlz44n.pdf) |
| 1.0 Ω 1% 2 W | Current sense | 2512 SMD | Low inductance thick film | 0.47 Ω (if higher I) | — (no IC datasheet) |

Speed matters when the drive pulse hits: the op-amp must contain inductive overshoot within the microsecond pulse. The throttle MOSFET runs in its linear region and must handle the waste heat.

---

## 4. Sense & Inhibit Front End (pins 65 & 66)

Isolates the differential read pulse from common-mode noise and protect the amp during inhibit.

| MPN | Role | Package | Key params | Alternate | Datasheet |
|-----|------|---------|------------|-----------|-----------|
| BAT54S | Dual series Schottky clamp | SOT-23 | Clamp YB65/66 to rails | BAT54C | [bat54s.pdf](datasheets/bat54s.pdf) |
| TLV3501 | High-speed comparator (Sense) | SOT-23-5 / SOIC | 4.5 ns tpd, 3.3 V logic out | LT1016 (legacy ±5 V class) | [tlv3501.pdf](datasheets/tlv3501.pdf) |
| 74AHC74 | D flip-flop read latch | SOIC-14 | Captures comparator on SENSE STROBE | 74LVC74 | [sn74ahc74.pdf](datasheets/sn74ahc74.pdf) |

Sense uses **TLV3501** (not LT1016): single-supply 3.3 V logic-friendly output and very short propagation delay. Classic comparator layout/strobe advice remains useful — see [AN13](appnotes/an13f.pdf). The latch clocks ~150–300 ns into READ to miss capacitive ringing and catch the core flip.

---

## 5. Hardware Testability

| MPN / series | Role | Package | Key params | Alternate | Datasheet |
|--------------|------|---------|------------|-----------|-----------|
| Keystone 5000-series | Loop test points | Through-hole loop | SENSE STROBE, DOUT, Isense | Equivalent loop TP | [keystone_5000.pdf](datasheets/keystone_5000.pdf) |
| 2N7002 | LED buffer N-MOSFET | SOT-23 | Decoder / DOUT indicators | 2N7002K | [2n7002.pdf](datasheets/2n7002.pdf) |
| 0805 LED | Diagnostic indicators | 0805 | Address + data visibility | — | — |

Populate loop-style test points on SENSE STROBE, the sense-latch output, and the top of the current-sense resistor (TP1 DOUT and TP2 Isense are already on Sense / CCS). Route decoder and latched data through small N-FETs to 0805 LEDs for step debugging before full-speed PIO cycles.
