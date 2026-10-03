# Core-Element Simulation

SPICE model of one three-wire memory core. The driver schematic uses it as the MCE (magnetic core element) symbol on [ferrite_beads.kicad_sch](../kicad/core/ferrite_beads.kicad_sch): the same six pins as the old ferrite-bead stand-in, with the flux probe kept inside the `mce` wrapper. This project remains the isolated testbench.

KiCad project: [kicad/core_element_sim/](../kicad/core_element_sim/). Subcircuit: [models/coremem.cir](../kicad/core_element_sim/models/coremem.cir). Batch deck: [models/coremem_tb.cir](../kicad/core_element_sim/models/coremem_tb.cir).

## Why this is not the LTspice Chan `K` statement

KiCad simulates with ngspice. In that engine a `K` line is a linear coupling coefficient. It does not accept the Chan parameters `Hc`, `Br`, `Bs`, `Lm`, and `A` that LTspice puts on a mutual inductor (Chan et al., IEEE Trans. CAD, 1991; see [references.md](references.md)).

Two further limits pushed the model off that formulation:

- Memory squareness here is \(B_r/B_s = 0.18/0.20 = 0.90\). LTspice’s Chan solver is known to stall when that ratio is much above about \(2/3\), especially under one-sided saturation.
- A 20–50 mV sense pulse across a 10–50 Ω damper is only a couple of milliamps. With ideal current sources that resistor does not stretch the flip out to 1 µs. The peaking time is a parameter of the core, `Tsw`.

The subcircuit still takes the same physical numbers. Switching is a domain-wall time: while \(|H| > H_c\), the normalized remanence \(m\) slews toward the driven rail in about `Tsw`, and each winding voltage is Faraday’s law, \(V = A\,dB/dt\), with \(B = B_r m + \mu_0 \mu_r H\) clamped to \(\pm B_s\).

## Geometry and material (50-mil toroid)

This run uses a typical vintage 50-mil core, not the 0.125 in diameter inferred in [design_spec.md](design_spec.md) §4 from the edge-contact width. The plane’s normative full-select band (400–800 mA) is unchanged. The half-select used below, 400 mA, is the top of that band and is the current the coercivity was matched to.

| Quantity | Value | Origin |
|----------|-------|--------|
| Outer / inner diameter | 1.27 mm / 0.76 mm | 50-mil toroid |
| Mean diameter | 1.0 mm | average of OD and ID |
| Magnetic path \(L_m\) | 0.00314 m | \(\pi \times 1.0\,\mathrm{mm}\) |
| Wall × height | 0.255 mm × 0.38 mm | \((OD-ID)/2\), typical height |
| Area \(A\) | \(0.097\times 10^{-6}\,\mathrm{m}^2\) | wall × height |
| \(B_s\), \(B_r\) | 0.20 T, 0.18 T | squareness \(B_r/B_s = 0.90\) |
| \(H_c\) | 150 A/m (about 1.9 Oe) | below full-select, above half-select |
| Turns | 1 on X, Y, and sense | three-wire core |
| `Tsw` | 1 µs | full-select peaking time |
| \(\mu_r\) | 20 | reversible permeability for the disturb |

Ampere’s law on one turn, \(H = I/L_m\):

- Half-select, 400 mA on X only: \(H \approx 127\,\mathrm{A/m}\), under \(H_c\). The core stays at \(+B_r\).
- Full-select, 400 mA on X and on Y: \(H \approx 255\,\mathrm{A/m}\), over \(H_c\). The core flips.

A remanence reversal \(\Delta B = 2 B_r\) through area \(A\) in 1 µs is an average sense voltage of about 35 mV, inside the 20–50 mV band expected for a single core with one sense turn.

## Stimulus

One 18 µs transient, 100 ns edges, X2/Y2/S2 grounded, 20 Ω across X and across Y. The core starts at \(m = +1\) (`tran … uic`).

| Window | Drive | Intended result |
|--------|-------|-----------------|
| 2–4 µs | \(I_x = -400\,\mathrm{mA}\) | half-select disturb |
| 6–8 µs | \(I_x = I_y = -400\,\mathrm{mA}\) | read 1, \(+B_r \to -B_r\) |
| 10–12 µs | same full-select again | read 0, already at \(-B_r\) |
| 14–16 µs | \(I_x = I_y = +400\,\mathrm{mA}\) | restore to \(+B_r\) |

Open [core_element_sim.kicad_pro](../kicad/core_element_sim/core_element_sim.kicad_pro) and run the simulator; the sheet carries `.tran 20n 18u uic`. Plot `V(S1)` and `V(B)` (1 V on `B` is 1 T). The same deck from the shell:

```bash
ngspice -b kicad/core_element_sim/models/coremem_tb.cir   # RESULT PASS or RESULT FAIL
python3 kicad/core_element_sim/plot_response.py           # plots/coremem_response.png
```

`ngspice` the program is optional. The plot script talks to `libngspice`, which is the library KiCad already uses. Regenerate the sheet with `uv run python kicad/scripts/gen_core_element_sim.py`.

## Comparison with the literature

![Drive, sense, aligned pulses, and B–H path for one 50-mil core.](../kicad/core_element_sim/plots/coremem_response.png)

The pink band on the sense plots is 20–50 mV. The dashed line on the aligned pulses is 1 µs. Both are the single-core targets used to size this model (one sense turn), in the same range as the millivolt, microsecond sense signals of coincident-current practice (Forrester 1951; Papian 1952; Rajchman 1953). They are not a trace digitized from a particular oscilloscope photo.

Numbers from the plot above:

| Event | Sense peak | Width at half amplitude | Remanence after the pulse |
|-------|------------|-------------------------|---------------------------|
| Half-select | −3.1 mV | 0.11 µs | stays \(+B_r\) (\(m \approx +1\)) |
| Read 1 | −41 mV | 1.01 µs | flips to \(-B_r\) |
| Read 0 | −6.2 mV | 0.12 µs | stays \(-B_r\) |
| Restore | +41 mV | 1.02 µs | returns to \(+B_r\) |

What lines up with the classic behavior:

- Only the intersection flips. Half-select field stays under \(H_c\), and a second full-select in the same direction does not flip the core again (Rajchman; Papian).
- The read-1 and the restore are tens of millivolts and about 1 µs wide. The read-0 and the half-select disturb are several times smaller, which is the discrimination a sense amplifier needs.
- The B–H path is square, with \(B_r/B_s = 0.90\). \(H_c = 150\,\mathrm{A/m}\) is about 1.9 Oe, in the range memory ferrites were specified in.

Where the waveform is not a scope photo:

Published read-1 pulses are bell-shaped. Menyuk and Goodenough (1955) describe flux reversal whose rate peaks in the middle of the switch, because that is when the domain-wall area is largest. This model slews \(m\) at a nearly constant rate once \(|H| > H_c\), so \(dB/dt\) is flat for about 1 µs. The spikes at the start and end of each current edge are the reversible term \(\mu_0 \mu_r dH/dt\), not the flip. The 20 Ω dampers are on the testbench, as in the original damping note; at these sense voltages they do not set the 1 µs width.

The read-1 peak (−41 mV) is the ~35 mV remanence reversal plus the reversible edge at the start of the ramp. Polarity follows the drive: negative current produces a negative read-1; the restore is the opposite spike.
