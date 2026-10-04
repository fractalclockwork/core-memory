# Coverage matrix (schematic / SPICE / SIL / bench)

**Rule:** never equate 2×2 e2e with 64×64 proof. Each cell is independent. Regenerate with:

```bash
uv run python kicad/scripts/gen_coverage_matrix.py
```

Layers: [reimplementation.md](reimplementation.md). ICD: [icd.md](icd.md). Hierarchy: [hierarchy_abi.md](hierarchy_abi.md).

## Legend

| Mark | Meaning |
|------|---------|
| PASS | Automated or documented gate passed |
| FAIL | Deliberate negative test (must keep failing) |
| smoke | Partial / subset / idealized |
| — | Not claimed |
| open | Known gap |

## Per-n coverage

| n | Schematic | SPICE L0/L1/L2 | SPICE L3 ideal | SIL | Bench |
|---|:---------:|:--------------:|:--------------:|:---:|:-----:|
| 1 | isolated TB sheet | L0 `coremem_tb` PASS | — | — | open (Ic, polarity) |
| 2 | archived `magnetic_core_2x2` + live drive/decode | L1 oracle PASS; single-CCS FAIL*; L2 e2e PASS | — | — | open |
| 8 | — | — | `array_ideal_nxn_tb` | open | — |
| 64 | `magnetic_core_64x64` + `steer_64` + 32× drive | L0 diagonal smoke (128 cores, split decks) | `array64x64_ideal_tb` | open (PIO) | open |

## Deck gates (SPICE)

| Layer | Deck | Expected | Notes |
|-------|------|----------|-------|
| L0 | `ideal_core_tb.cir` | PASS | Single ideal_core half-select / flip / restore |
| L0 | `coremem_tb.cir` | PASS | Half-select / read-1 / read-0 / restore |
| L1 | `array2x2_tb.cir` | FAIL* | Architecture record: single CCS must not coincident-flip |
| L1 | `array2x2_cycle_tb.cir` | PASS | Three CCS oracle |
| L2 | `array2x2_drive_tb.cir` | PASS | Real drive leg |
| L2 | `array2x2_matrix_tb.cir` | PASS | Diode matrix |
| L2 | `array2x2_inhibit_tb.cir` | PASS | Inhibit path |
| L2 | `array2x2_sense_tb.cir` | PASS | Sense FE |
| L2 | `array2x2_e2e_tb.cir` | PASS | Address-pin cycle |
| L2 | `array2x2_strobe_tb.cir` | PASS | Strobe window |
| L3 | `array_ideal_nxn_tb.cir` | PASS | Ideal cores; continuous addresses (n=8) |
| L3 | `array64x64_ideal_tb.cir` | PASS | Ideal diagonal, one transient |
| char | `array64x64_cycle.sh` | PASS | Behavioral subset; not L3 scale gate |

\* The L1 single-CCS deck prints `RESULT PASS` when it correctly demonstrates **no** coincident flip (split current). Treat that as “failure-mode recorded correctly,” not as a working coincident architecture.

## Hierarchical pin budgets (from `hierarchy_tiles`)

| Budget | Value |
|--------|------:|
| Monolithic steer pins | 320 |
| Monolithic magnetic pins | 258 |
| Legacy root plane pin instances | 512 |
| Octal tile pins | 34 |
| Octal tile count | 16 |
| Octal diodes (must = 512) | 512 |
| Plane drive ends | 256 |

## Schematic coverage (live tree)

| Region | Claim | Status |
|--------|-------|--------|
| Drive blocks | 32 calls, groups 0–7, X/Y, FWD/REV | present |
| Decode blocks | 4 calls | present |
| Steer | `steer_64`, diodes lines 0–63 | present (monolithic; octal tiles next) |
| Magnetic | 4,096 MCE on sheet | present (layout/net); SPICE scale via L3 |
| Sense / Inhibit / CCS×3 | hierarchical sheets | present |
| PIO / LEDs | firmware / indicators | not implemented |

## Open inputs (block scale confidence)

- Weave L/DCR (numeric)
- Inhibit polarity vs READ on the physical plane
- Normative Ic / Vdrive from bench
- Real sense geography (vs checkerboard model)
- Decoupling in transient netlists

## How to run

```bash
kicad/core_element_sim/run_regression.sh
kicad/core_element_sim/run_regression.sh --l2
kicad/core_element_sim/run_regression.sh --ideal
uv run python kicad/scripts/gen_pipeline.py --check-abi
```
