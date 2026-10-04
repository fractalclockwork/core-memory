# Design review (process retrospective)

Short record of what worked and what to change. Full process: [reimplementation.md](reimplementation.md). ICD: [icd.md](icd.md).

## Verdict

The project succeeded as a **physics-and-architecture discovery engine** through the 2×2 end-to-end ladder (three CCS sinks, series fold, address→DOUT). It struggled as a **scalable productization engine**: detailed MCE was pushed toward 64×64 before an idealized array model existed; hierarchical pin explosion at steer↔plane was discovered late; generators and docs diverged; “full plane in KiCad” was conflated with “full plane in SPICE.”

## What went well

1. **Isolated MCE** before the array — reusable ~35 mV / ~1 µs contract.
2. **Single-CCS FAIL deck** — proved coincident full-select needs three sinks.
3. **Fidelity ladder** on fixed 2×2 weave — oracle → drive → matrix → inhibit → sense → e2e → strobe.
4. **Dual-loop fold archaeology** — soft mid, series inhibit on sense ends.
5. **Drive/decode block ABI** — FETs and decoders compressed correctly.
6. **Shared weave math** — `mce_array.py` as seed of one AST for sch + sim.

## What went wrong

1. Scaled detailed `coremem` instead of introducing an **idealized core** first.
2. **Pin explosion** at 256 plane ends (320-pin steer, 258-pin magnetic) designed late.
3. **Generators evolved in place** (stage1–8 → live scripts); scale names lagged (`steer_2x2`).
4. **Docs claimed bank coverage** the sim did not exercise; schematic ≠ SPICE ≠ bench.
5. Late freeze of plane topology / core-size disclaimer.
6. Missing L/DCR, PIO SIL, decoupling in nets — n×n could only prove coincidence logic.
7. Expanded 4096-MCE schematic before L3 runtime contract existed.

## Carry forward

**Keep:** isolated MCE bench; single-CCS FAIL; block ladder on small n; CCS×3; weave AST; soft fold.

**Change:** idealized core before n>2; hierarchy for 64 lines on day one; one regen pipeline; coverage matrix; separate magnetic schematic from SPICE plant; runtime as a gate.

**Do not repeat:** 4096 detailed MCEs as scale proof; growing `steer_2x2` without rename/ABI redesign; docs implying 64×64 e2e; treating checkerboard sense as traced geography.
