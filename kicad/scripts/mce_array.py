"""64×64 (and N×N) MCE weave shared by the schematic and the cycle deck.

Columns x = 0..n-1 left to right, rows y = 0..n-1 top to bottom.
(x+y) even is the YA loop; (x+y) odd is the YB loop. This is the 2×2
checkerboard scaled. It is not a trace of the plane's sense geography.

Subcircuit pin order is X1 X2 Y1 Y2 S1 S2 after Sim.Pins:
  subckt Y1 is the YA side, Y2 the YB side;
  subckt S2 is symbol S1 (entry), subckt S1 is symbol S2 (exit).
"""

from __future__ import annotations

from pathlib import Path


def ya_order(n: int) -> list[tuple[int, int]]:
    """Even diagonals x-y, each from its bottom-right core toward the top-left."""
    cores: list[tuple[int, int]] = []
    for d in range(n - 1, -n, -1):
        if d % 2 != 0:
            continue
        diag = [(x, x - d) for x in range(n) if 0 <= x - d < n]
        diag.sort(key=lambda p: -p[0])
        cores.extend(diag)
    return cores


def yb_order(n: int) -> list[tuple[int, int]]:
    """Odd diagonals x+y, each from its left/bottom core toward the top-right."""
    cores: list[tuple[int, int]] = []
    for s in range(1, 2 * (n - 1) + 1, 2):
        diag = [(x, s - x) for x in range(n) if 0 <= s - x < n]
        diag.sort(key=lambda p: p[0])
        cores.extend(diag)
    return cores


def spice_nets(n: int) -> dict[tuple[int, int], tuple[str, str, str, str, str, str]]:
    """Map each core to subcircuit nets (X1, X2, Y1, Y2, S1, S2)."""
    s1: dict[tuple[int, int], str] = {}
    s2: dict[tuple[int, int], str] = {}

    def link(order: list[tuple[int, int]], entry: str, exit_name: str, tag: str) -> None:
        for i, core in enumerate(order):
            s2[core] = entry if i == 0 else f"n{tag}{i - 1}"
            s1[core] = exit_name if i == len(order) - 1 else f"n{tag}{i}"

    link(ya_order(n), "YA65", "FOLD", "ya")
    link(yb_order(n), "FOLD", "YB66", "yb")

    nets: dict[tuple[int, int], tuple[str, str, str, str, str, str]] = {}
    for y in range(n):
        for x in range(n):
            x1 = f"XA{x}" if y == 0 else f"nx{x}_{y}"
            x2 = f"XB{x}" if y == n - 1 else f"nx{x}_{y + 1}"
            y1 = f"YA{y}" if x == n - 1 else f"ny{x}_{y}"
            y2 = f"YB{y}" if x == 0 else f"ny{x - 1}_{y}"
            nets[(x, y)] = (x1, x2, y1, y2, s1[(x, y)], s2[(x, y)])
    return nets


def assert_matches_2x2() -> None:
    """The N=2 weave is the archived four-core netlist."""
    if ya_order(2) != [(1, 1), (0, 0)]:
        raise SystemExit(f"YA order {ya_order(2)}")
    if yb_order(2) != [(0, 1), (1, 0)]:
        raise SystemExit(f"YB order {yb_order(2)}")
    nets = spice_nets(2)
    expect = {
        (0, 0): ("XA0", "nx0_1", "ny0_0", "YB0", "FOLD", "nya0"),
        (0, 1): ("nx0_1", "XB0", "ny0_1", "YB1", "nyb0", "FOLD"),
        (1, 0): ("XA1", "nx1_1", "YA0", "ny0_0", "YB66", "nyb0"),
        (1, 1): ("nx1_1", "XB1", "YA1", "ny0_1", "nya0", "YA65"),
    }
    # ya mid index 0 is nya0; yb mid index 0 is nyb0. Confirm against link().
    got_ya = ya_order(2)
    # Recompute mids the same way link() does and compare to the hand deck's roles.
    if nets[(1, 1)][5] != "YA65" or nets[(1, 1)][4] == "YA65":
        raise SystemExit(f"MCE11 sense {nets[(1, 1)]}")
    if nets[(0, 0)][4] != "FOLD":
        raise SystemExit(f"MCE00 sense exit {nets[(0, 0)]}")
    if nets[(0, 1)][5] != "FOLD" or nets[(1, 0)][4] != "YB66":
        raise SystemExit(f"YB sense {nets[(0, 1)]} {nets[(1, 0)]}")
    if nets[(1, 1)][4] != nets[(0, 0)][5]:
        raise SystemExit("YA series is open")
    if nets[(0, 1)][4] != nets[(1, 0)][5]:
        raise SystemExit("YB series is open")
    for core, (x1, x2, y1, y2, _s1, _s2) in expect.items():
        g = nets[core]
        if g[0:4] != (x1, x2, y1, y2):
            raise SystemExit(f"{core} drive {g[0:4]} != {(x1, x2, y1, y2)}")
    if len(ya_order(64)) != 2048 or len(yb_order(64)) != 2048:
        raise SystemExit("64x64 loops are not 2048/2048")


def _us(t_us: float) -> str:
    text = f"{t_us:.4f}".rstrip("0").rstrip(".")
    return text + "u"


def half_select_xy(i: int, n: int) -> tuple[int, int]:
    """X half-select neighbor of diagonal core (i, i), as (x, y).

    Same X line, next row. The last address uses the row above, since
    row n does not exist.
    """
    if i + 1 < n:
        return (i, i + 1)
    return (i, i - 1)


def _m_node(x: int, y: int) -> str:
    """Remanence probe. Instance is Xr{row}c{col}."""
    return f"v(xr{y:02d}c{x:02d}.xcore.m)"


def diagonal_real_cores(n: int) -> set[tuple[int, int]]:
    """Diagonal cores, plus one X half-select neighbor for each address."""
    cores = {(i, i) for i in range(n)}
    for i in range(n):
        cores.add(half_select_xy(i, n))
    return cores


def _subset_nets(n: int, real: set[tuple[int, int]]) -> dict[tuple[int, int], tuple[str, str, str, str, str, str]]:
    """Series nets for the cores that are actually instantiated."""
    x1: dict[tuple[int, int], str] = {}
    x2: dict[tuple[int, int], str] = {}
    y1: dict[tuple[int, int], str] = {}
    y2: dict[tuple[int, int], str] = {}
    for x in range(n):
        col = sorted(y for y in range(n) if (x, y) in real)
        for i, y in enumerate(col):
            x1[(x, y)] = f"XA{x}" if i == 0 else f"nx{x}_{col[i - 1]}"
            x2[(x, y)] = f"XB{x}" if i == len(col) - 1 else f"nx{x}_{y}"
    for y in range(n):
        row = sorted(x for x in range(n) if (x, y) in real)
        for i, x in enumerate(row):
            y2[(x, y)] = f"YB{y}" if i == 0 else f"ny{row[i - 1]}_{y}"
            y1[(x, y)] = f"YA{y}" if i == len(row) - 1 else f"ny{x}_{y}"
    s1: dict[tuple[int, int], str] = {}
    s2: dict[tuple[int, int], str] = {}

    def link(order: list[tuple[int, int]], entry: str, exit_name: str, tag: str) -> None:
        kept = [c for c in order if c in real]
        for i, core in enumerate(kept):
            s2[core] = entry if i == 0 else f"n{tag}{i - 1}"
            s1[core] = exit_name if i == len(kept) - 1 else f"n{tag}{i}"

    link(ya_order(n), "YA65", "FOLD", "ya")
    link(yb_order(n), "FOLD", "YB66", "yb")
    return {c: (x1[c], x2[c], y1[c], y2[c], s1[c], s2[c]) for c in real}


def write_diagonal_deck(path: Path, n: int = 64, i0: int = 0, i1: int | None = None) -> None:
    """Write-1 smoke for diagonal addresses i0 .. i1-1.

    Lines are 0-based. There is no Xn. Each pulse is one coincident write.
    The addressed core must go to +Br; the next diagonal core and one
    X half-select neighbor must stay at -Br. A full 64-pulse transient of
    the behavioral cores does not finish in a reasonable time, so the smoke
    is two slices. The upper slice starts the lower diagonal at +Br.
    """
    if i1 is None:
        i1 = n
    assert_matches_2x2()
    lines: list[str] = []
    a = lines.append
    a("* Diagonal addressing smoke on the NxN MCE weave.")
    a("* Pin order matches magnetic_core_64x64.kicad_sch after Sim.Pins.")
    a(f"* Lines are 0-based: X0/Y0, X1/Y1, ... X{n - 1}/Y{n - 1}. There is no X{n}.")
    a(f"* This deck pulses X{i0}/Y{i0} through X{i1 - 1}/Y{i1 - 1}.")
    if i0:
        a(f"* X0/Y0 through X{i0 - 1}/Y{i0 - 1} start at +Br, the state after those writes.")
    a("*")
    a("* One CCS each for X, Y, and inhibit, 400 mA. Inhibit stays off.")
    a("* Each pulsed core gets one write 1 (1 us rise, 2 us flat, 1 us fall).")
    a("* The diagonal and one X half-select neighbor per address are the mce")
    a("* devices. Other positions are omitted; each driven line still")
    a("* series-connects the cores that sit on it. Sense is the early flat.")
    a("*")
    a("* Batch: kicad/core_element_sim/models/array64x64_cycle.sh")
    a("* Prints RESULT PASS or RESULT FAIL.")
    a("")
    a(".include coremem.cir")
    a(".include ccs.cir")
    a("")
    a(".param vdrive=12")
    a("")
    a("Vdrive vdrv 0 DC {vdrive}")
    a("Viccsx ccs_x ccs_xin 0")
    a("Viccsy ccs_y ccs_yin 0")
    a("Viccsi ccs_i ccs_iin 0")
    a("Xccs_x ccs_xin ccs ic_half=0.4")
    a("Xccs_y ccs_yin ccs ic_half=0.4")
    a("Xccs_i ccs_iin ccs ic_half=0.4")
    a("Rx ccs_x 0 10Meg")
    a("Ry ccs_y 0 10Meg")
    a("Ri ccs_i 0 10Meg")
    a("Rfold FOLD 0 10k")
    a("")
    for i in range(n):
        a(f"Rxa{i} xa{i}d 0 10Meg")
        a(f"Rya{i} ya{i}d 0 10Meg")
    a("")
    real = diagonal_real_cores(n)
    nets = _subset_nets(n, real)
    for y in range(n):
        for x in range(n):
            if (x, y) not in real:
                continue
            x1, x2, y1, y2, s1, s2 = nets[(x, y)]
            m0 = 1 if x == y and x < i0 else -1
            a(f"Xr{y:02d}c{x:02d} {x1} {x2} {y1} {y2} {s1} {s2} mce m0={m0}")
    a("")
    a("Bdiff DIFF 0 V = V(YA65)-V(YB66)")
    a("Vinh inhd YA65 0")
    a("Bpinh PINH 0 V = I(Vinh)")
    for i in range(n):
        a(f"Vixa{i} xa{i}d XA{i} 0")
        a(f"Viya{i} ya{i}d YA{i} 0")
        a(f"Bpxa{i} PXA{i} 0 V = I(Vixa{i})")
        a(f"Bpya{i} PYA{i} 0 V = I(Viya{i})")
    a("")
    a("* Ramps from a few hundred ohms down to 1 ohm across the 1 us edge.")
    a(".subckt drvsw a b ctl")
    a("Bsw a b I=(v(ctl)>0.02 ? v(a,b)/(1+400*(1-min(v(ctl),1))) : 0)")
    a(".ends")
    a("")
    for i in range(n):
        a(f"Xx{i}_ra xa{i}d ccs_x g_x{i}r drvsw")
        a(f"Xx{i}_rb vdrv XB{i} g_x{i}r drvsw")
        a(f"Xx{i}_wa vdrv xa{i}d g_x{i}w drvsw")
        a(f"Xx{i}_wb XB{i} ccs_x g_x{i}w drvsw")
        a(f"Xy{i}_ra ya{i}d ccs_y g_y{i}r drvsw")
        a(f"Xy{i}_rb vdrv YB{i} g_y{i}r drvsw")
        a(f"Xy{i}_wa vdrv ya{i}d g_y{i}w drvsw")
        a(f"Xy{i}_wb YB{i} ccs_y g_y{i}w drvsw")
        a(f"Vg_x{i}r g_x{i}r 0 DC 0")
        a(f"Vg_y{i}r g_y{i}r 0 DC 0")
    a("Xinh_a vdrv inhd g_inh drvsw")
    a("Xinh_b YB66 ccs_i g_inh drvsw")
    a("Vg_inh g_inh 0 DC 0")
    a("")
    # 4 us pulse, 2 us gap. Local t0 restarts at 2 us for this slice.
    for i in range(n):
        if i0 <= i < i1:
            t0 = 2 + (i - i0) * 6
            pw = " ".join(
                [
                    "0 0",
                    f"{_us(t0)} 0",
                    f"{_us(t0 + 1)} 1",
                    f"{_us(t0 + 3)} 1",
                    f"{_us(t0 + 4)} 0",
                ]
            )
            a(f"Vg_x{i}w g_x{i}w 0 PWL({pw})")
            a(f"Vg_y{i}w g_y{i}w 0 PWL({pw})")
        else:
            a(f"Vg_x{i}w g_x{i}w 0 DC 0")
            a(f"Vg_y{i}w g_y{i}w 0 DC 0")
    a("")
    stop = 2 + (i1 - i0) * 6 + 4
    a("* Trap holds the step while cores sit on the remanence rail.")
    a(".options reltol=1e-3 method=trap")
    # Saving every internal node makes the 390 us run quadratic in the plot.
    # Keep only the remanence, sense, and drive currents the checks read.
    save: list[str] = ["v(diff)"]
    for i in range(i0, i1):
        hx, hy = half_select_xy(i, n)
        save.append(_m_node(i, i))
        save.append(_m_node(hx, hy))
        if i + 1 < n:
            save.append(_m_node(i + 1, i + 1))
        if i > 0:
            save.append(_m_node(i - 1, i - 1))
        save.append(f"i(Vixa{i})")
        save.append(f"i(Viya{i})")
    kept: list[str] = []
    for item in save:
        if item not in kept:
            kept.append(item)
    chunk: list[str] = []
    width = 6
    for item in kept:
        chunk.append(item)
        if len(chunk) == width:
            a(".save " + " ".join(chunk))
            chunk = []
    if chunk:
        a(".save " + " ".join(chunk))
    a(f".tran 200n {_us(stop)} uic")
    a("")
    a(".control")
    a("set nobreak")
    a("set noaskquit")
    a("run")
    a("")
    for i in range(i0, i1):
        t0 = 2 + (i - i0) * 6
        hx, hy = half_select_xy(i, n)
        a(f"meas tran m_d{i} FIND {_m_node(i, i)} AT={_us(t0 + 4.5)}")
        a(f"meas tran m_n{i} FIND {_m_node(hx, hy)} AT={_us(t0 + 4.5)}")
        if i + 1 < n:
            a(f"meas tran m_x{i} FIND {_m_node(i + 1, i + 1)} AT={_us(t0 + 4.5)}")
        if i > 0:
            a(f"meas tran m_p{i} FIND {_m_node(i - 1, i - 1)} AT={_us(t0 + 4.5)}")
        a(f"meas tran smin_d{i} MIN v(diff) FROM={_us(t0 + 1.2)} TO={_us(t0 + 2.2)}")
        a(f"meas tran ix_d{i} AVG i(Vixa{i}) FROM={_us(t0 + 2.2)} TO={_us(t0 + 2.8)}")
        a(f"meas tran iy_d{i} AVG i(Viya{i}) FROM={_us(t0 + 2.2)} TO={_us(t0 + 2.8)}")
    a("")
    a("let fail = 0")
    for i in range(i0, i1):
        hx, hy = half_select_xy(i, n)
        a(f"if m_d{i} < 0.9")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} write 1 did not set the addressed core")
        a("end")
        a(f"if m_n{i} > -0.9")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} write 1 flipped half-select X{hx}/Y{hy}")
        a("end")
        if i + 1 < n:
            a(f"if m_x{i} > -0.9")
            a("  let fail = 1")
            a(f"  echo FAIL X{i}/Y{i} write 1 flipped X{i+1}/Y{i+1}")
            a("end")
        if i > 0:
            a(f"if m_p{i} < 0.9")
            a("  let fail = 1")
            a(f"  echo FAIL X{i}/Y{i} write 1 disturbed X{i-1}/Y{i-1}")
            a("end")
        a(f"if smin_d{i} > -15m")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} sense plateau above -15 mV")
        a("end")
        a(f"if smin_d{i} < -80m")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} sense plateau below -80 mV")
        a("end")
        a(f"if ix_d{i} < 0.34")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} X current low")
        a("end")
        a(f"if ix_d{i} > 0.46")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} X current high")
        a("end")
        a(f"if iy_d{i} < 0.34")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} Y current low")
        a("end")
        a(f"if iy_d{i} > 0.46")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} Y current high")
        a("end")
    a("if fail = 0")
    a("  echo RESULT PASS")
    a("else")
    a("  echo RESULT FAIL")
    a("end")
    a(".endc")
    a(".end")
    a("")
    path.write_text("\n".join(lines) + "\n")


def write_ideal_diagonal_deck(path: Path, n: int = 64) -> None:
    """L3 idealized diagonal write-1 smoke in one continuous transient.

    Uses ideal_mce instead of behavioral coremem so a full 0..n-1 run
    finishes in a runtime budget suitable for SIL scale gates.
    """
    assert_matches_2x2()
    lines: list[str] = []
    a = lines.append
    a("* L3 idealized diagonal addressing smoke (ideal_mce).")
    a(f"* One continuous transient: write-1 on X0/Y0 .. X{n - 1}/Y{n - 1}.")
    a("* Three CCS copies at 400 mA. Ideal drvsw. Inhibit off.")
    a("* Sparse plant: diagonal + one X half-select neighbor per address.")
    a("* Prints RESULT PASS or RESULT FAIL.")
    a("")
    a(".include ideal_core.cir")
    a(".include ccs.cir")
    a("")
    a(".param vdrive=12")
    a("")
    a("Vdrive vdrv 0 DC {vdrive}")
    a("Viccsx ccs_x ccs_xin 0")
    a("Viccsy ccs_y ccs_yin 0")
    a("Viccsi ccs_i ccs_iin 0")
    a("Xccs_x ccs_xin ccs ic_half=0.4")
    a("Xccs_y ccs_yin ccs ic_half=0.4")
    a("Xccs_i ccs_iin ccs ic_half=0.4")
    a("Rx ccs_x 0 10Meg")
    a("Ry ccs_y 0 10Meg")
    a("Ri ccs_i 0 10Meg")
    a("Rfold FOLD 0 10k")
    a("")
    for i in range(n):
        a(f"Rxa{i} xa{i}d 0 10Meg")
        a(f"Rya{i} ya{i}d 0 10Meg")
    a("")
    real = diagonal_real_cores(n)
    nets = _subset_nets(n, real)
    for y in range(n):
        for x in range(n):
            if (x, y) not in real:
                continue
            x1, x2, y1, y2, s1, s2 = nets[(x, y)]
            a(f"Xr{y:02d}c{x:02d} {x1} {x2} {y1} {y2} {s1} {s2} ideal_mce m0=-1")
    a("")
    a("Bdiff DIFF 0 V = V(YA65)-V(YB66)")
    a("Vinh inhd YA65 0")
    for i in range(n):
        a(f"Vixa{i} xa{i}d XA{i} 0")
        a(f"Viya{i} ya{i}d YA{i} 0")
    a("")
    a(".subckt drvsw a b ctl")
    a("Bsw a b I=(v(ctl)>0.02 ? v(a,b)/(1+400*(1-min(v(ctl),1))) : 0)")
    a(".ends")
    a("")
    for i in range(n):
        a(f"Xx{i}_ra xa{i}d ccs_x g_x{i}r drvsw")
        a(f"Xx{i}_rb vdrv XB{i} g_x{i}r drvsw")
        a(f"Xx{i}_wa vdrv xa{i}d g_x{i}w drvsw")
        a(f"Xx{i}_wb XB{i} ccs_x g_x{i}w drvsw")
        a(f"Xy{i}_ra ya{i}d ccs_y g_y{i}r drvsw")
        a(f"Xy{i}_rb vdrv YB{i} g_y{i}r drvsw")
        a(f"Xy{i}_wa vdrv ya{i}d g_y{i}w drvsw")
        a(f"Xy{i}_wb YB{i} ccs_y g_y{i}w drvsw")
        a(f"Vg_x{i}r g_x{i}r 0 DC 0")
        a(f"Vg_y{i}r g_y{i}r 0 DC 0")
    a("Xinh_a vdrv inhd g_inh drvsw")
    a("Xinh_b YB66 ccs_i g_inh drvsw")
    a("Vg_inh g_inh 0 DC 0")
    a("")
    for i in range(n):
        t0 = 2 + i * 6
        pw = " ".join(
            [
                "0 0",
                f"{_us(t0)} 0",
                f"{_us(t0 + 1)} 1",
                f"{_us(t0 + 3)} 1",
                f"{_us(t0 + 4)} 0",
            ]
        )
        a(f"Vg_x{i}w g_x{i}w 0 PWL({pw})")
        a(f"Vg_y{i}w g_y{i}w 0 PWL({pw})")
    a("")
    stop = 2 + n * 6 + 4
    a(".options reltol=1e-3 method=trap")
    save: list[str] = ["v(diff)"]
    for i in range(n):
        hx, hy = half_select_xy(i, n)
        save.append(_m_node(i, i))
        save.append(_m_node(hx, hy))
        if i + 1 < n:
            save.append(_m_node(i + 1, i + 1))
        if i > 0:
            save.append(_m_node(i - 1, i - 1))
        save.append(f"i(Vixa{i})")
        save.append(f"i(Viya{i})")
    kept: list[str] = []
    for item in save:
        if item not in kept:
            kept.append(item)
    chunk: list[str] = []
    for item in kept:
        chunk.append(item)
        if len(chunk) == 6:
            a(".save " + " ".join(chunk))
            chunk = []
    if chunk:
        a(".save " + " ".join(chunk))
    a(f".tran 200n {_us(stop)} uic")
    a("")
    a(".control")
    a("set nobreak")
    a("set noaskquit")
    a("run")
    a("")
    for i in range(n):
        t0 = 2 + i * 6
        hx, hy = half_select_xy(i, n)
        a(f"meas tran m_d{i} FIND {_m_node(i, i)} AT={_us(t0 + 4.5)}")
        a(f"meas tran m_n{i} FIND {_m_node(hx, hy)} AT={_us(t0 + 4.5)}")
        if i + 1 < n:
            a(f"meas tran m_x{i} FIND {_m_node(i + 1, i + 1)} AT={_us(t0 + 4.5)}")
        if i > 0:
            a(f"meas tran m_p{i} FIND {_m_node(i - 1, i - 1)} AT={_us(t0 + 4.5)}")
        a(f"meas tran smin_d{i} MIN v(diff) FROM={_us(t0 + 1.2)} TO={_us(t0 + 2.2)}")
        a(f"meas tran ix_d{i} AVG i(Vixa{i}) FROM={_us(t0 + 2.2)} TO={_us(t0 + 2.8)}")
        a(f"meas tran iy_d{i} AVG i(Viya{i}) FROM={_us(t0 + 2.2)} TO={_us(t0 + 2.8)}")
    a("")
    a("let fail = 0")
    for i in range(n):
        hx, hy = half_select_xy(i, n)
        a(f"if m_d{i} < 0.9")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} write 1 did not set the addressed core")
        a("end")
        a(f"if m_n{i} > -0.9")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} write 1 flipped half-select X{hx}/Y{hy}")
        a("end")
        if i + 1 < n:
            a(f"if m_x{i} > -0.9")
            a("  let fail = 1")
            a(f"  echo FAIL X{i}/Y{i} write 1 flipped X{i+1}/Y{i+1}")
            a("end")
        if i > 0:
            a(f"if m_p{i} < 0.9")
            a("  let fail = 1")
            a(f"  echo FAIL X{i}/Y{i} write 1 disturbed X{i-1}/Y{i-1}")
            a("end")
        a(f"if smin_d{i} > -15m")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} sense plateau above -15 mV")
        a("end")
        a(f"if smin_d{i} < -80m")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} sense plateau below -80 mV")
        a("end")
        a(f"if ix_d{i} < 0.34")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} X current low")
        a("end")
        a(f"if ix_d{i} > 0.46")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} X current high")
        a("end")
        a(f"if iy_d{i} < 0.34")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} Y current low")
        a("end")
        a(f"if iy_d{i} > 0.46")
        a("  let fail = 1")
        a(f"  echo FAIL X{i}/Y{i} Y current high")
        a("end")
    a("if fail = 0")
    a("  echo RESULT PASS")
    a("else")
    a("  echo RESULT FAIL")
    a("end")
    a(".endc")
    a(".end")
    a("")
    path.write_text("\n".join(lines) + "\n")


def write_ideal_nxn_deck(path: Path, n: int = 8) -> None:
    """L3 smoke for an n×n idealized weave (default n=8).

    Same sparse diagonal plant as the 64 deck, smaller for fast SIL loops.
    """
    write_ideal_diagonal_deck(path, n=n)
