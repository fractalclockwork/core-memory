# Implementation Summary

Present state of the driver: hierarchical schematic under [`kicad/core/core.kicad_sch`](../kicad/core/core.kicad_sch). **Decode** and **Drive** are reusable blocks with `N`/`n` pins; root places one of each for X FWD / X0 FWD bring-up. Y / REV instances and remaining matrix FETs come later.

Part rationale: [component_selection.md](component_selection.md). Architecture: [design_choices.md](design_choices.md), [regions.md](regions.md), [theory_of_operation.md](theory_of_operation.md).

## Architecture

Three-wire cores (X, Y, sense)—no separate inhibit winding. Folded sense is two half-loops (`YA65`↔`YA66`, `YB65`↔`YB66`) shunted at **`YA65`═`YB65`**; full path `YA66`↔`YB66` is shared for differential READ and series inhibit. Drive is coincident half-select into a shared CCS (`CCS_RET`). Forward FET banks do READ (−Ic/2); reverse banks do WRITE (+Ic/2).

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
                  YB65/66 sense + inhibit (FDS8958A + TC4427A×2)
```

**Fail-safe:** `DEC_EN` pull-down (off); `FWD_EN_n` / `REV_EN_n` pull-up (inactive). Disabled **138** outputs HIGH → TC4427 → P-FET gates HIGH (off). Disabled **238** outputs LOW → TC4427 → N-FET gates LOW (off). HS inputs `*_n` have 10k pull-ups; LS inputs `*_en` have 10k pull-downs. Never assert both bank enables.

## Blocks on the sheet

| Block | What it does |
|-------|--------------|
| Sense | Sheet `sense`: 1k iso, BAT54S, TLV3501 → 74AHC74 |
| Ferrite Beads | Sheet `ferrite_beads`: FB00–FB11 2×2; fold mid `SENSE_FOLD` (tied to `YA65` for now) |
| CCS | Sheet `ccs`: TL431 + 3296W → OPA192 → IRLZ44N + 1Ω; `CCS_RET` out |
| Drive | Sheet `drive_block`: TC4427A + FDS8958A + C30/C31; pins `N_HSn`/`N_LSn`/`NAn`/`NBn`; root = X0 FWD |
| Inhibit | Sheet `inhibit`: FDS8958A on YB65/YB66; TC4427A×2 + 2N7002 (`INH_LS_en`) |
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

Unchanged (TL431, OPA192, IRLZ44N, TLV3501, BAT54S, 74AHC74, 1k iso). Soft mid on Ferrite Beads. DC-coupled Sense locked.

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

Plane hookup: XA0/XB0 (driven), XA1/XB1 / YA0/YB0 / YA1/YB1 on Ferrite Beads stand-in; sense/inhibit attach per **Bring-Up Deviations** below.

## Bring-Up Deviations

Temporary 1×1 test-state attach points. These are **not** the normative fold topology in [design_spec.md](design_spec.md) / [naming.md](naming.md); do not “resolve” them into the architecture docs.

- **Normative full fold:** two half-loops `YA65`↔`YA66` and `YB65`↔`YB66`, shunt `YA65`═`YB65`, series ends `YA66` / `YB66` for differential READ and series inhibit.
- **1×1 schematic today:** Inhibit sheet and Sense probe attach on the **YB half only** (`YB65` / `YB66`). Ferrite Beads fold mid is `SENSE_FOLD`, presently tied to `YA65` (same net as the `YA65`═`YB65` shunt).
- **Why:** prove the READ → STROBE → INHIBIT → WRITE cycle on one core before wiring the full series path through both halves.
- **Exit criterion:** when cloning past bring-up, move Sense/Inhibit to `YA66`↔`YB66` and drop this section.

## Not implemented yet

- Remaining drive matrix FETs (decode already covers X0–63 / Y0–63; drive still 1×1)
- Edge receptacles / full connector fan-out
- RP2040 PIO timing controller
- Decoder / DOUT LEDs
