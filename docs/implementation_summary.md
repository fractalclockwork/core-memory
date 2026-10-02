# Implementation Summary

Present state of the driver: one-page A1 schematic [`kicad/core/core.kicad_sch`](../kicad/core/core.kicad_sch), Stages 1–8 approved. Scope is a **1×1 prototype** (core X0∩Y0) that can run a full READ → STROBE → INHIBIT → WRITE cycle, with decode wired for later 8×8 scaling.

Part rationale lives in [component_selection.md](component_selection.md). Architecture notes: [design_choices.md](design_choices.md), [regions.md](regions.md), [theory_of_operation.md](theory_of_operation.md).

## Architecture

Three-wire cores (X, Y, sense)—no separate inhibit winding. Folded sense on YB65/66 (via YA65/66) is shared for differential READ and series inhibit. Drive is coincident half-select into a shared CCS (`CCS_RET`). Forward FET banks do READ (−Ic/2); reverse banks do WRITE (+Ic/2).

```
ADDR_A[2:0], DEC_EN
        │
        ▼
  74AHC138 ×4  ──Y0──►  74AHC125 ×2  ──►  TC4427A / TC4426A
                        FWD_EN_n /          │
                        REV_EN_n            ▼
                                   FDS8958A + SS14
                                   (fwd Stage 3, rev Stage 6)
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                     XA0/XB0       YA0/YB0        CCS_RET
                     YA0/YB0                         ▲
                          │                          │
                          └──── plane ──── YB65/66 ──┤
                                         sense/inhibit
```

Fail-safe: TC442x active-low inputs pulled up to +3V3; `DEC_EN` defaults off; `FWD_EN_n` / `REV_EN_n` default Hi-Z (do not assert both).

## Stages on the sheet

| Stage | Block | What it does |
|-------|--------|--------------|
| 1 | Sense | Bowtie FB_A/FB_B, 1k iso, BAT54S clamps, soft mid→AGND, TLV3501 → 74AHC74 (STROBE→DOUT) |
| 2 | CCS | TL431 + 3296W pot → OPA192 → IRLZ44N + 1Ω; all LS returns on `CCS_RET` |
| 3 | Fwd drive | Q2/Q3 half-bridges → XA0/XB0 & YA0/YB0 (HS→A, LS←B) |
| 4 | Fwd gates | TC4427A/TC4426A, 10k pull-ups, headers on `*_n` |
| 5 | Inhibit | Series drive YB65→fold→YB66→CCS (`INH_EN_n`) |
| 6 | Rev drive | Q5/Q6, ends swapped (HS→B, LS←A) for WRITE |
| 7 | Rev gates | Same TC442x pattern on `*r_n` |
| 8 | Decode | 74AHC138×4 (Y0 only); 74AHC125×2 steers FWD→`*_n` / REV→`*r_n` |

## Component selection (as used)

### Address decode and gate drive

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| 74AHC138 | Stage 8 ×4 (XH/XL/YH/YL); only ~Y0 used | 3.3 V logic in; proto straps ADDR=000 |
| 74AHC125 | Stage 8 ×2 | OE = `FWD_EN_n` / `REV_EN_n`; Hi-Z when inactive |
| TC4427A | Stages 4, 5, 7 (non-inv HS) | VDRIVE rail; ampere-class gate drive |
| TC4426A | Stages 4, 5, 7 (inv LS) | Same family; active-low `*_n` with 10k to +3V3 |

See [component_selection.md](component_selection.md) §1; datasheets [sn74ahc138.pdf](datasheets/sn74ahc138.pdf), [tc4427a.pdf](datasheets/tc4427a.pdf).

### Drive matrix

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| FDS8958A | Q2/Q3 fwd, Q5/Q6 rev, Q4 inhibit | One HS (P) + one LS (N) per package |
| SS14 | Steering on each matrix output | Plane has no diodes; blocks sneak paths |

See [component_selection.md](component_selection.md) §2; [fds8958a.pdf](datasheets/fds8958a.pdf), [ss14.pdf](datasheets/ss14.pdf).

### Constant-current sink

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| TL431 | Stage 2 reference | With Bourns 3296W setpoint |
| OPA192 | Stage 2 error amp | Loop around 1Ω sense |
| IRLZ44N | Stage 2 throttle | Linear-region heat expected |
| 1.0 Ω 1% | Current sense | TP2 at Isense |

Target half-select ~200–400 mA. See [component_selection.md](component_selection.md) §3.

### Sense and inhibit front end

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| BAT54S | Stage 1 clamps | Protect amp during inhibit spikes |
| TLV3501 | Stage 1 comparator | 3.3 V, ~4.5 ns; not LT1016 |
| 74AHC74 | Stage 1 latch | Clock ~150–300 ns into READ |
| Soft mid 10k→AGND | Stage 1 | Soft YA65/66 mid so inhibit can traverse fold |
| 1k iso | Stage 1 | Keeps VDRIVE/inhibit out of +3V3 via clamps |

See [component_selection.md](component_selection.md) §4; [AN13](appnotes/an13f.pdf).

### Testability

| Item | Status |
|------|--------|
| TP1 DOUT, TP2 Isense | On sheet (Stages 1–2) |
| Headers J1–J9, J10–J15 | Bench drive / address / FWD-REV enables |
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
