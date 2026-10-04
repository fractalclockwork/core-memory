# Hierarchical fabric ABI (steer / magnetic)

**Problem this solves:** FET drive/decode were factored into small blocks, but the steer↔plane boundary exposed **256** A/B ends on both Steer (**320** hierarchical pins) and Magnetic Cores (**258** pins), with the same nets duplicated on the root (~512 pin instances). The sheet formerly named `steer_2x2` grew to lines 0–63 in place.

**Rule:** hierarchical boundaries match the manufacturing pin budget, not the 2×2 bring-up size.

## Target naming

| Artifact | Name | Role |
|----------|------|------|
| Live steer fabric (legacy monolithic) | `steer_64.kicad_sch` | Renamed from `steer_2x2`; full 0…63 SS14 matrix |
| Preferred long-term | `steer_octal_{X,Y}_g{0..7}.kicad_sch` | One HS group × one axis (FWD+REV) |
| Preferred line tile | `steer_line` (optional) | One line, 4 diodes, 6 pins |
| Magnetic fabric | `magnetic_core_64x64.kicad_sch` | Generated weave; prefer bus pins on root |

## Pin budgets

| Boundary | Monolithic (legacy) | Octal tiles (target) | Line tiles (alt) |
|----------|--------------------:|---------------------:|-----------------:|
| Steer sheet pins | 320 (64 switch + 256 plane) | 34 per octal × 16 sheets | 6 per line × 128 |
| Magnetic sheet pins | 258 | Prefer `XA[63:0]`… buses on root | same |
| Root plane pin instances | 512 (Steer + Magnetic) | Wire buses once; tiles bind locally | same |

### Octal tile pin list (one axis, one HS group `g`)

Lines `L = 8·g + k` for `k = 0…7`.

| Pin | Count | Nets |
|-----|------:|------|
| `HS`, `HSR` | 2 | `{axis}HS{g}`, `{axis}HS{g}R` |
| `LS[0..7]`, `LSR[0..7]` | 16 | `{axis}LS{k}`, `{axis}LS{k}R` |
| `A[0..7]`, `B[0..7]` | 16 | `{axis}A{L}`, `{axis}B{L}` |
| **Total** | **34** | — |

Diode law (unchanged):

```text
FWD:  HS  → diode → B{line}
      A{line} → diode → LS{ls}
REV:  HSR → diode → A{line}
      B{line} → diode → LSR{ls}
```

Helpers: [`hierarchy_tiles.py`](../kicad/scripts/hierarchy_tiles.py).

### Line tile pin list (optional finer grain)

| Pin | Role |
|-----|------|
| `HS`, `LS`, `HSR`, `LSR` | Switch nodes for this line’s group |
| `A`, `B` | Plane ends |

Four SS14s inside. Root or octal parent binds group fan-out.

## Magnetic plane

1. **Layout / net semantics:** generated 64×64 MCE sheet from the weave AST ([`mce_array.py`](../kicad/scripts/mce_array.py)).
2. **SPICE scale proof:** use L3 [`ideal_core`](../kicad/core_element_sim/models/ideal_core.cir), not 4,096 detailed `coremem` instances.
3. **Root ABI:** prefer KiCad buses `XA[0..63]`, `XB[0..63]`, `YA[0..63]`, `YB[0..63]` plus `YA65` / `YB66`. Do not duplicate 256 hierarchical stubs on both Steer and Magnetic if a single bus vector can feed both.

Fold `YA66`═`YB65` stays **local** on the magnetic sheet (`SENSE_FOLD`); it is not a Drive/Decode hierarchical pin.

## Migration

| Step | Action |
|------|--------|
| Done | Rename monolithic sheet `steer_2x2` → `steer_64`; update generators and root `Sheetfile` |
| Next | Emit octal tiles from `hierarchy_tiles` / pipeline; root places 16 tile calls |
| Later | Drop monolithic steer from the live tree; keep only as archive if needed |

## What never enters Drive/Decode

`YA65`, `YB65`, `YA66`, `YB66`, `SENSE_FOLD` — sense/fold only ([naming.md](naming.md) §8).
