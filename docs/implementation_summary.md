# Implementation Summary

Present state of the driver: one-page A1 schematic [`kicad/core/core.kicad_sch`](../kicad/core/core.kicad_sch), organized by **functional blocks**. Scope is a **1×1 prototype** (core X0∩Y0) that can run a full READ → STROBE → INHIBIT → WRITE cycle, with decode banked for later 8×8 scaling.

Part rationale: [component_selection.md](component_selection.md). Architecture: [design_choices.md](design_choices.md), [regions.md](regions.md), [theory_of_operation.md](theory_of_operation.md).

## Architecture

Three-wire cores (X, Y, sense)—no separate inhibit winding. Folded sense on YB65/66 (via YA65/66) is shared for differential READ and series inhibit. Drive is coincident half-select into a shared CCS (`CCS_RET`). Forward FET banks do READ (−Ic/2); reverse banks do WRITE (+Ic/2).

```
ADDR_A[2:0] ──┬──────────────────┐
DEC_EN ───────┼── E2 (all 138s)  │
              │                  │
     FWD_EN_n │~E0      REV_EN_n │~E0
              ▼                  ▼
      74AHC138 ×4 FWD     74AHC138 ×4 REV
      U11–U14 (Y0 only)   U15–U18 (Y0 only)
      ~E1←GND             ~E1←GND
              │                  │
              ▼ ~Y0              ▼ ~Y0
      X/Y_*0_n            X/Y_*0r_n
              │                  │
              ▼                  ▼
      TC442x Drive FWD    TC442x Drive REV
              │                  │
              ▼                  ▼
      FDS8958A+SS14       FDS8958A+SS14
      (READ)              (WRITE)
              └────────┬─────────┘
                       ▼
                  CCS_RET / plane
                       │
              YB65/66 sense + inhibit
```

No `74AHC125` mux layer. Decoder `~Y0` drives gate-driver nets directly.

**Fail-safe:** TC442x active-low inputs pulled up to +3V3; `DEC_EN` pull-down (off); `FWD_EN_n` / `REV_EN_n` pull-up (inactive). A disabled 138 forces all `~Yn` HIGH → TC4427 HS gate HIGH (P-FET off) and TC4426 LS gate LOW (N-FET off). Never assert both bank enables.

## Blocks on the sheet

| Block | What it does |
|-------|--------------|
| Sense | Bowtie FB_A/FB_B, 1k iso, BAT54S clamps, soft mid→AGND, TLV3501 → 74AHC74 (STROBE→DOUT) |
| CCS | TL431 + 3296W pot → OPA192 → IRLZ44N + 1Ω; all LS returns on `CCS_RET` |
| Drive FWD | Q2/Q3 half-bridges + TC4427A/TC4426A → XA0/XB0 & YA0/YB0 (HS→A, LS←B) |
| Drive REV | Q5/Q6 + TC442x, ends swapped (HS→B, LS←A) for WRITE |
| Inhibit | Series drive YB65→fold→YB66→CCS (`INH_EN_n`) |
| Decode | 74AHC138×4 FWD + ×4 REV; bank enables on `~E0`; `~Y0`→`*_n`/`*r_n` |

## Decode map (1×1)

| Bank | Ref | Axis | `~Y0` net |
|------|-----|------|-----------|
| FWD | U11 | X HS | `X_HS0_n` |
| FWD | U12 | X LS | `X_LS0_n` |
| FWD | U13 | Y HS | `Y_HS0_n` |
| FWD | U14 | Y LS | `Y_LS0_n` |
| REV | U15 | X HS | `X_HS0r_n` |
| REV | U16 | X LS | `X_LS0r_n` |
| REV | U17 | Y HS | `Y_HS0r_n` |
| REV | U18 | Y LS | `Y_LS0r_n` |

Enables (KiCad `74HC138` pin names): `~E0`←bank EN, `~E1`←GND, `E2`←`DEC_EN`. Headers J10–J12 = `ADDR_A[2:0]` (10k→GND); J13 = `DEC_EN` (10k→GND); J14/J15 = `FWD_EN_n` / `REV_EN_n` (10k→+3V3). Bypass C19–C26.

## Component selection (as used)

### Address decode and gate drive

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| 74AHC138 | Decode ×8 (U11–U18); only ~Y0 used | 3.3 V; bank enables as above |
| TC4427A | Drive FWD/REV + Inhibit (non-inv HS) | VDRIVE rail; ampere-class gate drive |
| TC4426A | Drive FWD/REV + Inhibit (inv LS) | Active-low `*_n` with 10k to +3V3 |

See [component_selection.md](component_selection.md) §1; [sn74ahc138.pdf](datasheets/sn74ahc138.pdf), [tc4427a.pdf](datasheets/tc4427a.pdf).

### Drive matrix

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| FDS8958A | Drive FWD Q2/Q3, Drive REV Q5/Q6, Inhibit Q4 | One HS (P) + one LS (N) per package |
| SS14 | Steering on each matrix output | Plane has no diodes; blocks sneak paths |

See [component_selection.md](component_selection.md) §2; [fds8958a.pdf](datasheets/fds8958a.pdf), [ss14.pdf](datasheets/ss14.pdf).

### Constant-current sink

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| TL431 | CCS reference | With Bourns 3296W setpoint |
| OPA192 | CCS error amp | Loop around 1Ω sense |
| IRLZ44N | CCS throttle | Linear-region heat expected |
| 1.0 Ω 1% | Current sense | TP2 at Isense |

Target half-select ~200–400 mA. `CCS_RET` shared by Drive FWD, Drive REV, and Inhibit. See [component_selection.md](component_selection.md) §3.

### Sense and inhibit front end

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| BAT54S | Sense clamps | Protect amp during inhibit spikes |
| TLV3501 | Sense comparator | 3.3 V, ~4.5 ns; not LT1016 |
| 74AHC74 | Sense latch | Clock ~150–300 ns into READ |
| Soft mid 10k→AGND | Sense | Soft YA65/66 mid so inhibit can traverse fold |
| 1k iso | Sense | Limits clamp current (~8 mA at 12 V) |

**Locked DC-coupled:** pulse-transformer sense deferred—primary across YB65/66 would shunt series inhibit on this 3-wire plane. See [design_choices.md](design_choices.md).

See [component_selection.md](component_selection.md) §4; [AN13](appnotes/an13f.pdf).

### Testability

| Item | Status |
|------|--------|
| TP1 DOUT, TP2 Isense | On sheet (Sense / CCS) |
| Headers J1–J9, J10–J15 | Bench drive / address / bank enables |
| 2N7002 + LEDs | Planned, not populated |

See [component_selection.md](component_selection.md) §5.

## Bench cycle

After CCS setpoint:

1. Assert `DEC_EN` and pulse `FWD_EN_n` → READ (−Ic/2 on X0/Y0)
2. SENSE STROBE → latch DOUT
3. Inhibit (`INH_EN_n`) if restoring/writing 0
4. Pulse `REV_EN_n` → WRITE (+Ic/2)

Plane hookup: XA0, XB0, YA0, YB0; sense fold YB65/66.

## Not implemented yet

- Remaining 63 X/Y lines and 138 outputs Y1–Y7
- Edge receptacles / full connector fan-out
- RP2040 PIO timing controller
- Decoder / DOUT LEDs
