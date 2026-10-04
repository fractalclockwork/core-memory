# Implementation Summary

Present state of the driver: hierarchical schematic under [`kicad/core/core.kicad_sch`](../kicad/core/core.kicad_sch). **Decode** and **Drive** are reusable blocks with `N`/`n` pins. Root places four decode calls (X/Y, FWD/REV) and **32** drive calls (groups 0–7 on each axis and direction). [`steer_64.kicad_sch`](../kicad/core/steer_64.kicad_sch) holds the SS14s for lines **0–63**. Coverage and scale gates: [coverage_matrix.md](coverage_matrix.md). ICD: [icd.md](icd.md).

Part rationale: [component_selection.md](component_selection.md). Architecture: [design_choices.md](design_choices.md), [regions.md](regions.md), [theory_of_operation.md](theory_of_operation.md).

## Architecture

Three-wire cores (X, Y, sense)—no separate inhibit winding. Sense/inhibit is two independent loops (`YA65`↔`YA66`, `YB65`↔`YB66`), joined on the driver at **`YA66`═`YB65`**. Outer ends `YA65`/`YB66` are shared for differential READ and series inhibit. The schematic array is the 64×64 on Magnetic Cores. Its sense checkerboard is the archived 2×2 rule scaled (one diagonal family per loop), not a traced plane weave. Drive is coincident half-select into two sinks (`CCS_X`, `CCS_Y`), with inhibit on its own sink (`CCS_INH`). Forward FET banks do READ (−Ic/2); reverse banks do WRITE (+Ic/2).

```
ADDR_XH/XL[2:0] ──┐
DEC_EN / FWD_EN_n ┼── Decode Block (N=axis, n=bank)
                  │   U11 138 + U12 238; four root calls (X/Y, FWD/REV)
                  ▼
        X_HS{0..7}_n / X_LS{0..7}_en
                  │
                  ▼
          drive_block (N=axis, n=group)
          TC4427A + FDS8958A; 32 root calls; SS14s on steer_64
                  └────────┬─────────┘
                           ▼
                 CCS_X / CCS_Y / plane
                           │
                  YA65/YB66 sense + inhibit (FDS8958A + TC4427A×2)
```

**Fail-safe:** `DEC_EN` pull-down (off); `FWD_EN_n` / `REV_EN_n` pull-up (inactive). Disabled **138** outputs HIGH → TC4427 → P-FET gates HIGH (off). Disabled **238** outputs LOW → TC4427 → N-FET gates LOW (off). HS inputs `*_n` have 10k pull-ups; LS inputs `*_en` have 10k pull-downs. Never assert both bank enables.

## Blocks on the sheet

| Block | What it does |
|-------|--------------|
| Sense | Sheet `sense`: 1k iso, BAT54S, TLV3501 → 74AHC74 |
| Magnetic Cores | Sheet `magnetic_core_64x64`: MCE_r00_c00–MCE_r63_c63; center tap `SENSE_FOLD` (`YA66`═`YB65`). Archived 2×2: `kicad/core/reference/magnetic_core_2x2.kicad_sch` |
| CCS | Sheet `ccs` ×3 (X, Y, inhibit): TL431 + 3296W → OPA192 → IRLZ44N + 1Ω; pin `CCS_RET` |
| Drive | Sheet `drive_block`: TC4427A + FDS8958A + C30/C31; pins `N_HSn`/`N_LSn`/`N_HS_OUT`/`N_LS_OUT`; **32** root calls; SS14s on `steer_64` |
| Inhibit | Sheet `inhibit`: FDS8958A on YA65/YB66; TC4427A×2 + 2N7002 (`INH_LS_en`) |
| Decode | Sheet `decode_block`: one axis 138+238 + C19/C20; pins `N_HS{0..7}_n`/`N_LS{0..7}_en`; four root calls (X/Y × FWD/REV) |
| Decode CTRL | Sheets `decode_ctrl` / `decode_ctrl_y`: pins `ADDR_NH/NL`, `BANK_EN`, `DEC_EN`, `REV_EN_n`; root binds X/Y and `FWD_EN_n` |
| Decoupling Logic | Sheet `decoupling_logic`: +3V3 bypass (Sense/Latch). CCS +5V is on each CCS instance |
| Decoupling VDRIVE | Sheet `decoupling_vdrive`: VDRIVE 100n+1u for Inhibit TC4427s |
## Decode map (one axis on Decode Block)

On [`decode_block.kicad_sch`](../kicad/core/decode_block.kicad_sch) (X FWD shown; Y and REV are the other three calls):

| Ref | Part | Role | ADDR | Hier outs |
|-----|------|------|------|-----------|
| U11 | 74AHC138 | HS | `ADDR_NH[2:0]` | `N_HS0_n` … `N_HS7_n` |
| U12 | 74AHC238 | LS | `ADDR_NL[2:0]` | `N_LS0_en` … `N_LS7_en` |

**Line select:** `Nn = 8·HS + LS`. Root maps X FWD: `ADDR_NH*`←`ADDR_XH*`, `BANK_EN`←`FWD_EN_n`, outs → `X_HS*_n` / `X_LS*_en`. Headers J40–J54 live on **Decode CTRL** (X sheet also has `BANK_EN` / `DEC_EN` / `REV_EN_n`; Y sheet is `ADDR_NH/NL` only). Local +3V3 100n (C19/C20) lives on **Decode Block**.

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

Plane hookup: all `XA*`/`XB*`/`YA*`/`YB*` 0…63 are wired through `steer_64`. Sense/inhibit outer ends are `YA65`/`YB66`; the center tap is `YA66`═`YB65` (`SENSE_FOLD`, 10 kΩ to AGND). SPICE e2e remains the 2×2 ladder unless an L3 ideal deck is run — see [coverage_matrix.md](coverage_matrix.md).

## Array model

The Magnetic Cores sheet is the schematic weave fixture (4,096 MCE). The checkerboard (even `x+y` on YA, odd on YB) is the 2×2 rule scaled; the real plane's geographic split is still untraced. Drive calls cover groups 0–7 on both axes and both directions. The steer sheet diodes lines 0–63. L3 ideal diagonal smoke writes X0/Y0 through X63/Y63 in **one** transient (`array64x64_ideal_tb.cir`). Legacy behavioral smoke remains two split decks.

- **Loop A:** `(x+y)` even, 2,048 cores, mirrored. The archived 2×2 is `YA65` ↔ MCE11 ↔ MCE00 ↔ `YA66`.
- **Loop B:** `(x+y)` odd, the other 2,048. The archived 2×2 is `YB65` ↔ MCE10 ↔ MCE01 ↔ `YB66`.
- **Center tap:** `YA66`═`YB65`, R1 10 kΩ→AGND. The plane does not join the loops.
- **Outer ends:** `YA65` / `YB66` for differential READ and series inhibit.

## Not implemented yet

- Octal steer tiles ([hierarchy_abi.md](hierarchy_abi.md)) — live fabric is still monolithic `steer_64`
- RP2040 PIO program / SIL. The root header only brings the stimulus nets out.
- Decoder / DOUT LEDs
- Bench calibration of \(I_c\), inhibit polarity, weave L/DCR
