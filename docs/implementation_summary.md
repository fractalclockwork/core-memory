# Implementation Summary

Present state of the driver: hierarchical schematic under [`kicad/core/core.kicad_sch`](../kicad/core/core.kicad_sch). **Decode** and **Drive** are reusable blocks with `N`/`n` pins; root places one of each for X FWD / X0 FWD bring-up. Y / REV instances and remaining matrix FETs come later.

Part rationale: [component_selection.md](component_selection.md). Architecture: [design_choices.md](design_choices.md), [regions.md](regions.md), [theory_of_operation.md](theory_of_operation.md).

## Architecture

Three-wire cores (X, Y, sense)—no separate inhibit winding. Sense/inhibit is two independent loops (`YA65`↔`YA66`, `YB65`↔`YB66`), joined on the driver at **`YA66`═`YB65`**. Outer ends `YA65`/`YB66` are shared for differential READ and series inhibit. The schematic array is the 2×2 on Magnetic Cores (one diagonal per loop). Drive is coincident half-select into a shared CCS (`CCS_RET`). Forward FET banks do READ (−Ic/2); reverse banks do WRITE (+Ic/2).

```
ADDR_XH/XL[2:0] ──┐
DEC_EN / FWD_EN_n ┼── Decode Block (N=axis, n=bank)
                  │   U11 138 + U12 238; root = X FWD
                  ▼
        X_HS{0..7}_n / X_LS{0..7}_en
                  │
                  ▼
          drive_block (N=axis, n=line)
          one TC4427A + FDS8958A; root wires X0 FWD only
                  └────────┬─────────┘
                           ▼
                      CCS_RET / plane
                           │
                  YA65/YB66 sense + inhibit (FDS8958A + TC4427A×2)
```

**Fail-safe:** `DEC_EN` pull-down (off); `FWD_EN_n` / `REV_EN_n` pull-up (inactive). Disabled **138** outputs HIGH → TC4427 → P-FET gates HIGH (off). Disabled **238** outputs LOW → TC4427 → N-FET gates LOW (off). HS inputs `*_n` have 10k pull-ups; LS inputs `*_en` have 10k pull-downs. Never assert both bank enables.

## Blocks on the sheet

| Block | What it does |
|-------|--------------|
| Sense | Sheet `sense`: 1k iso, BAT54S, TLV3501 → 74AHC74 |
| Magnetic Cores | Sheet `ferrite_beads`: MCE00–MCE11 2×2; center tap `SENSE_FOLD` (`YA66`═`YB65`) |
| CCS | Sheet `ccs`: TL431 + 3296W → OPA192 → IRLZ44N + 1Ω; `CCS_RET` out |
| Drive | Sheet `drive_block`: TC4427A + FDS8958A + C30/C31; pins `N_HSn`/`N_LSn`/`NAn`/`NBn`; root = X0 FWD |
| Inhibit | Sheet `inhibit`: FDS8958A on YA65/YB66; TC4427A×2 + 2N7002 (`INH_LS_en`) |
| Decode | Sheet `decode_block`: one axis 138+238 + C19/C20; pins `N_HS{0..7}_n`/`N_LS{0..7}_en`; root = X FWD |
| Decode CTRL | Sheet `decode_ctrl`: J40–J54 / R40–R54 ADDR + bank enables |
| Decoupling Logic | Sheet `decoupling_logic`: +3V3/+5V bypass (Sense/Latch/CCS) |
| Decoupling VDRIVE | Sheet `decoupling_vdrive`: VDRIVE 100n+1u for Inhibit TC4427s |

## Decode map (one axis on Decode Block)

On [`decode_block.kicad_sch`](../kicad/core/decode_block.kicad_sch) (X FWD on root today):

| Ref | Part | Role | ADDR | Hier outs |
|-----|------|------|------|-----------|
| U11 | 74AHC138 | HS | `ADDR_NH[2:0]` | `N_HS0_n` … `N_HS7_n` |
| U12 | 74AHC238 | LS | `ADDR_NL[2:0]` | `N_LS0_en` … `N_LS7_en` |

**Line select:** `Nn = 8·HS + LS`. Root maps X FWD: `ADDR_NH*`←`ADDR_XH*`, `BANK_EN`←`FWD_EN_n`, outs → `X_HS*_n` / `X_LS*_en`. Headers J40–J54 live on **Decode CTRL**. Local +3V3 100n (C19/C20) lives on **Decode Block**.

Drive Block consumes `X_HS0_n` / `X_LS0_en` → `N_HSn` / `N_LSn`, plane `XA0`/`XB0`; local VDRIVE bypass C30/C31 on the block.

## Component selection (as used)

### Address decode and gate drive

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| 74AHC138 | Decode HS (U11 on `decode_block`) | Active-low Y → TC4427 for P-FET HS |
| 74AHC238 | Decode LS (U12 on `decode_block`) | Active-high Y → TC4427 for N-FET LS |
| TC4427A | All gate drivers (Drive + Inhibit) | Non-inverting only — no TC4426A |

See [component_selection.md](component_selection.md) §1.

### Drive matrix

| MPN | Role on sheet | Notes |
|-----|---------------|--------|
| FDS8958A | Drive Q10 on `drive_block`; Inhibit Q4 | One HS (P) + one LS (N) per package |
| SS14 | Steering on each matrix output | Plane has no diodes; blocks sneak paths |
| TC4427A | U20 on Drive Block (+ Inhibit×2) | Dual channels = HS+LS of that block |

### Constant-current sink / Sense

Unchanged (TL431, OPA192, IRLZ44N, TLV3501, BAT54S, 74AHC74, 1k iso). Soft mid on Magnetic Cores. DC-coupled Sense locked.

### Inhibit polarity helper

| MPN | Role | Notes |
|-----|------|-------|
| 2N7002 | Q7 inverts `INH_EN_n` → `INH_LS_en` | Same FET family as diagnostic LED buffers; lets Inhibit use TC4427A on both HS and LS |

## Bench cycle

After CCS setpoint:

1. Assert `DEC_EN` and pulse `FWD_EN_n` → READ (−Ic/2 on X0/Y0)
2. SENSE STROBE → latch DOUT
3. Inhibit (`INH_EN_n`) if restoring/writing 0
4. Pulse `REV_EN_n` → WRITE (+Ic/2)

Plane hookup: XA0/XB0 (driven). The 2×2 on Magnetic Cores also exposes XA1/XB1 and YA0/YB0 / YA1/YB1 for address stimuli. Sense/inhibit outer ends are `YA65`/`YB66`; the center tap is `YA66`═`YB65` (`SENSE_FOLD`, 10 kΩ to AGND).

## Array model

The Magnetic Cores sheet is the sim fixture for coincident address and the series sense string. It is a 2×2 stand-in for core count, not a second fold topology. Drive FET population is still one `drive_block` (X0 FWD); the other three line pairs are stimulated at the Magnetic Cores pins.

- **Loop A:** `YA65` ↔ MCE00 ↔ MCE11 ↔ `YA66` (stands in for 2,048 cores).
- **Loop B:** `YB65` ↔ MCE10 ↔ MCE01 ↔ `YB66` (the other 2,048).
- **Center tap:** `YA66`═`YB65`, R1 10 kΩ→AGND. The plane does not join the loops.
- **Outer ends:** `YA65` / `YB66` for differential READ and series inhibit.

## Not implemented yet

- Remaining drive matrix FETs (decode already covers X0–63 / Y0–63; drive still 1×1)
- Edge receptacles / full connector fan-out
- RP2040 PIO timing controller
- Decoder / DOUT LEDs
