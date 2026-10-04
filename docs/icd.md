# Plane Interface Control Document (ICD)

**Status:** frozen for reimplementation. Changes require an explicit ICD revision.

Normative companions: [design_spec.md](design_spec.md) (physical plane), [naming.md](naming.md) (net grammar), [hierarchy_abi.md](hierarchy_abi.md) (sheet boundaries).

## 1. Physical plane

| Item | Contract |
|------|----------|
| Array | 64×64 = 4,096 three-wire cores |
| Edge connectors | XA, XB (64 contacts each); YA, YB (66 contacts each) |
| Drive contacts | Physical **1–64** ↔ logical nets `XA0`…`XA63` / `XB0`…`XB63` / `YA0`… / `YB0`… (`p ↔ n+1`) |
| Sense contacts | YA/YB physical **65**, **66** — **not** drive lines |

## 2. Dual-loop fold (sense / inhibit)

Two independent 2,048-core loops on the plane; the driver joins them.

```text
YA65 ── Loop A (2,048) ── YA66 ══ SENSE_FOLD ══ YB65 ── Loop B (2,048) ── YB66
                              │
                           10 kΩ → AGND
```

| Node | Role |
|------|------|
| `YA65`, `YB66` | Outer ends: differential READ and series inhibit |
| `YA66`═`YB65` | Driver jumper; schematic local name `SENSE_FOLD` |
| Soft mid | 10 kΩ → AGND (not hard AGND), so inhibit current continues through Loop B into `CCS_INH` |

Inhibit (write-0 / restore-0): source `VDRIVE` into `YA65`, sink `YB66` → `CCS_INH` at \(I_c/2\).

Checkerboard weave used in schematic/sim (`(x+y)` even → YA, odd → YB) is a **model topology**, not a traced plane geography.

## 3. Drive ends (2×64 + 2×64)

| Bus | Count | Meaning |
|-----|------:|---------|
| `XA[0..63]` | 64 | X high-side end (A) |
| `XB[0..63]` | 64 | X low-side end (B) |
| `YA[0..63]` | 64 | Y high-side end (A) |
| `YB[0..63]` | 64 | Y low-side end (B) |
| **Total plane drive ends** | **256** | Dual-ended X and Y |

FWD/READ: source B from `VDRIVE`, sink A into that axis CCS.  
REV/WRITE: source A, sink B. Never assert FWD and REV together.

Address decode: `line = 8·HS + LS` (HS, LS ∈ 0…7) → logical 0…63.

## 4. Constant-current sinks (mandatory ×3)

| Sink | Serves | Setpoint |
|------|--------|----------|
| `CCS_X` | X low-side returns | \(I_c/2\) (bring-up band 200–400 mA; sim often 400 mA) |
| `CCS_Y` | Y low-side returns | same |
| `CCS_INH` | Inhibit return from `YB66` | same |

**One shared sink is forbidden for coincident full-select.** The single-CCS FAIL deck ([`array2x2_tb.cir`](../kicad/core_element_sim/models/array2x2_tb.cir)) is a permanent regression of that architecture error.

## 5. Enable and address polarity

| Net | Active | Fail-safe |
|-----|--------|-----------|
| `DEC_EN` | high to enable decode | 10 kΩ → GND (off) |
| `FWD_EN_n` | low to enable FWD banks | 10 kΩ → +3V3 (off) |
| `REV_EN_n` | low to enable REV banks | 10 kΩ → +3V3 (off) |
| `INH_EN_n` | low to enable inhibit | inactive between pulses |
| `SENSE_STROBE` | rising edge clocks sense latch | — |
| `ADDR_{X,Y}{H,L}[2:0]` | HS/LS bank select per axis | — |

Gate net grammar: `^[XY]_(HS|LS)[0-9]{1,2}r?_(n|en)$` — see [naming.md](naming.md).

## 6. Hierarchical block ABI (silicon)

| Block | Pins (summary) | Scale |
|-------|----------------|-------|
| `drive_block` | `N_HSn`, `N_LSn`, `N_HS_OUT`, `N_LS_OUT`, `VDRIVE`, `CCS_RET` | 32 root calls (8 groups × X/Y × FWD/REV) |
| `decode_block` | `ADDR_NH/NL[2:0]`, `BANK_EN`, `DEC_EN`, `N_HS{0..7}_n`, `N_LS{0..7}_en` | 4 root calls (X/Y × FWD/REV) |
| Sense / Inhibit / CCS | See [regions.md](regions.md) | Not part of Drive/Decode pin chain |

Plane ends and steer diodes are **not** inside `drive_block`. Target fabric boundaries: [hierarchy_abi.md](hierarchy_abi.md).

## 7. What “done” means (do not conflate)

| Claim | Means |
|-------|--------|
| 2×2 e2e PASS | Address pins → decode → drive → sense latch on four cores |
| Idealized n×n PASS | Coincidence / inhibit / decode on idealized plant within runtime budget |
| Schematic 64-line | Generated fabric covers lines 0–63 |
| Bench | Measured \(I_c\), inhibit polarity, sense noise on the physical plane |

See [coverage_matrix.md](coverage_matrix.md).
