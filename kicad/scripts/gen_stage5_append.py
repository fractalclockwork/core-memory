#!/usr/bin/env python3
"""Append Inhibit FETs + gate drive without touching Sense/CCS/Drive."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
SHEET_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
PROJECT = "core"


def uid() -> str:
    return str(uuid.uuid4())


def pin_xy(sx: float, sy: float, lx: float, ly: float, rot: int = 0) -> tuple[float, float]:
    if rot == 0:
        return round(sx + lx, 2), round(sy - ly, 2)
    if rot == 90:
        return round(sx - ly, 2), round(sy - lx, 2)
    if rot == 180:
        return round(sx - lx, 2), round(sy + ly, 2)
    if rot == 270:
        return round(sx + ly, 2), round(sy + lx, 2)
    raise ValueError(rot)


def prop(name: str, value: str, at: str, hide: bool = False) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    return f'''\t\t(property "{name}" "{value}"
\t\t\t(at {at}){hide_s}
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, *, unit=1, rot=0, footprint=""):
    pins_s = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit {unit})
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, f"{x + 2.54} {y - 12.7} 0")}
{prop("Value", value, f"{x + 2.54} {y - 10.16} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
{pins_s}
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{ref}") (unit {unit}))))
\t)'''


def power(lib_id, ref, value, x, y):
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, f"{x} {y + 2.54} 0", hide=True)}
{prop("Value", value, f"{x} {y + 5.08} 0")}
{prop("Footprint", "", f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{ref}") (unit 1))))
\t)'''


def wire(a, b):
    return f'''\t(wire
\t\t(pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]}))
\t\t(stroke (width 0) (type default))
\t\t(uuid "{uid()}")
\t)'''


def junction(p):
    return f'''\t(junction
\t\t(at {p[0]} {p[1]})
\t\t(diameter 0)
\t\t(color 0 0 0 0)
\t\t(uuid "{uid()}")
\t)'''


def label(name, p, rot=0):
    return f'''\t(label "{name}"
\t\t(at {p[0]} {p[1]} {rot})
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def no_connect(p):
    return f'''\t(no_connect
\t\t(at {p[0]} {p[1]})
\t\t(uuid "{uid()}")
\t)'''


def text(s, x, y, size=1.27):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def strip_stage5(sch: str) -> str:
    # Prefer stopping before hierarchical sheets so Drive xy_drive symbols survive.
    end = sch.find("\t(sheet\n")
    if end < 0:
        end = sch.find("(sheet\n")
    marker = "\t(sheet_instances"
    if end < 0:
        end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing")
    if "INHIBIT" not in sch and "STAGE 5" not in sch and '(property "Reference" "Q4"' not in sch:
        return sch
    starts = []
    for needle in (
        '\t(text "INHIBIT',
        '\t(text "STAGE 5',
        '\t(rectangle\n\t\t(start 12.70 205.00)',
        '(property "Reference" "Q4"',
        '(property "Reference" "U7"',
    ):
        i = sch.find(needle)
        if needle.startswith("(property") and i > 0:
            i = max(sch.rfind("\t(symbol\n", 0, i), sch.rfind("\n(symbol\n", 0, i))
        if 0 <= i < end:
            starts.append(i)
    if not starts:
        raise SystemExit("Inhibit present but cannot locate block")
    start = min(starts)
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def add_driver(
    o: list[str],
    *,
    uref: str,
    lib_id: str,
    value: str,
    ux: float,
    uy: float,
    out_net: str,
    c_lo: str,
    c_hi: str,
    pwr_suffix: str,
    inh_junc: tuple[float, float],
) -> tuple[float, float]:
    """Single-channel TC442x: IN_A ← INH_EN_n bus, OUT_A → out_net; IN_B tied +3V3."""
    FP_U = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"

    o.append(symbol_inst(lib_id, uref, value, ux, uy, ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_U))
    nc1 = pin_xy(ux, uy, -7.62, 0)
    ina = pin_xy(ux, uy, -10.16, 2.54)
    gnd = pin_xy(ux, uy, 0, -10.16)
    inb = pin_xy(ux, uy, -10.16, -2.54)
    outb = pin_xy(ux, uy, 10.16, -2.54)
    vdd = pin_xy(ux, uy, 0, 10.16)
    outa = pin_xy(ux, uy, 10.16, 2.54)
    nc8 = pin_xy(ux, uy, 7.62, 0)
    o += [no_connect(nc1), no_connect(nc8), no_connect(outb)]

    # OUT_A → gate net
    o += [
        wire(outa, (round(outa[0] + 10.16, 2), outa[1])),
        label(out_net, (round(outa[0] + 10.16, 2), outa[1])),
    ]

    # IN_A ← shared INH_EN_n junction (horizontal then vertical as needed)
    o += [
        wire(ina, (inh_junc[0], ina[1])),
        wire((inh_junc[0], ina[1]), inh_junc),
        junction((inh_junc[0], ina[1])),
    ]

    # IN_B hard HIGH (unused channel safe-off)
    o += [
        wire(inb, (round(inb[0] - 7.62, 2), inb[1])),
        power("power:+3V3", f"#PWR_{uref}_INB", "+3V3", round(inb[0] - 7.62, 2), round(inb[1] - 7.62, 2)),
        wire((round(inb[0] - 7.62, 2), inb[1]), (round(inb[0] - 7.62, 2), round(inb[1] - 7.62, 2))),
    ]

    # VDRIVE / GND + bypass
    vp = (vdd[0], round(vdd[1] - 5.08, 2))
    vm = (gnd[0], round(gnd[1] + 5.08, 2))
    o += [
        wire(vdd, vp),
        power("power:VDRIVE", f"#PWR_{pwr_suffix}_VDD", "VDRIVE", vp[0], round(vp[1] - 5.08, 2)),
        wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
        junction(vp),
        wire(gnd, vm),
        power("power:GND", f"#PWR_{pwr_suffix}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
        wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
        junction(vm),
    ]
    for cref, cval, cx in ((c_lo, "100n", round(ux + 22.86, 2)), (c_hi, "1u", round(ux + 38.1, 2))):
        cy = round((vp[1] + vm[1]) / 2, 2)
        o.append(symbol_inst("Device:C", cref, cval, cx, cy, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
        o += [
            wire(ct, (cx, vp[1])), wire((cx, vp[1]), vp), junction((cx, vp[1])),
            wire(cb, (cx, vm[1])), wire((cx, vm[1]), vm), junction((cx, vm[1])),
        ]
    return ina  # for reference


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")
    # Libs already embedded from Drive FWD (TC4427 only — no TC4426)
    for need in ("core_memory:FDS8958A", "Driver_FET:TC4427xOA", "Connector:Conn_01x01"):
        if f'(symbol "{need}"' not in sch:
            raise SystemExit(f"missing lib embed {need}")
    # Embed 2N7002 for INH_EN_n → INH_LS_en invert (reuse LED-buffer FET family)
    if '(symbol "Transistor_FET:2N7002"' not in sch:
        from pathlib import Path as _P
        import re as _re
        kicad = _P("/usr/share/kicad/symbols/Transistor_FET.kicad_sym")
        # resolve extends Q_NMOS_GSD
        raw = kicad.read_text()
        base_start = raw.find('(symbol "Q_NMOS_GSD"')
        depth = 0
        for i in range(base_start, len(raw)):
            if raw[i] == "(":
                depth += 1
            elif raw[i] == ")":
                depth -= 1
                if depth == 0:
                    base = raw[base_start : i + 1]
                    break
        emb = base.replace('(symbol "Q_NMOS_GSD"', '(symbol "Transistor_FET:2N7002"', 1)
        emb = emb.replace('(property "Value" "Q_NMOS_GSD"', '(property "Value" "2N7002"', 1)
        emb = emb.replace("Q_NMOS_GSD_", "2N7002_")
        emb = "\n".join("\t\t" + ln if ln else ln for ln in emb.splitlines())
        m = _re.search(r"\(lib_symbols\n", sch)
        start = m.end()
        depth = 1
        i = start
        while i < len(sch) and depth:
            if sch[i] == "(":
                depth += 1
            elif sch[i] == ")":
                depth -= 1
            i += 1
        sch = sch[: i - 1] + emb + "\n\t" + sch[i - 1 :]
    sch = strip_stage5(sch)

    o: list[str] = []
    FP_Q = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"

    # ---- Inhibit half-bridge Q4 (FDS8958A), no steering diodes ----
    # Below CCS; left side near YB plane labels
    qx, qy = 80.0, 260.0
    o.append(symbol_inst("core_memory:FDS8958A", "Q4", "FDS8958A", qx, qy,
                         ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_Q))
    s1 = pin_xy(qx, qy, -10.16, 5.08)
    g1 = pin_xy(qx, qy, -10.16, 2.54)
    s2 = pin_xy(qx, qy, -10.16, -2.54)
    g2 = pin_xy(qx, qy, -10.16, -5.08)
    d2_5 = pin_xy(qx, qy, 10.16, -5.08)
    d2_6 = pin_xy(qx, qy, 10.16, -2.54)
    d1_7 = pin_xy(qx, qy, 10.16, 2.54)
    d1_8 = pin_xy(qx, qy, 10.16, 5.08)
    o += [wire(d1_7, d1_8), junction(d1_7), junction(d1_8)]
    o += [wire(d2_5, d2_6), junction(d2_5), junction(d2_6)]

    # VDRIVE → S1
    o += [
        wire(s1, (round(s1[0] - 10.16, 2), s1[1])),
        label("VDRIVE", (round(s1[0] - 10.16, 2), s1[1]), 180),
    ]
    # G1 ← INH_HS
    o += [
        wire(g1, (round(g1[0] - 10.16, 2), g1[1])),
        label("INH_HS", (round(g1[0] - 10.16, 2), g1[1]), 180),
    ]
    # G2 ← INH_LS
    o += [
        wire(g2, (round(g2[0] - 10.16, 2), g2[1])),
        label("INH_LS", (round(g2[0] - 10.16, 2), g2[1]), 180),
    ]
    # S2 → CCS_RET
    o += [
        wire(s2, (round(s2[0] - 10.16, 2), s2[1])),
        label("CCS_RET", (round(s2[0] - 10.16, 2), s2[1]), 180),
    ]
    # D1 → YB65 (plane)
    dy_hs = round((d1_7[1] + d1_8[1]) / 2, 2)
    o += [
        wire(d1_7, (d1_7[0], dy_hs)),
        wire((d1_7[0], dy_hs), (round(d1_7[0] + 15.24, 2), dy_hs)),
        junction((d1_7[0], dy_hs)),
        label("YB65", (round(d1_7[0] + 15.24, 2), dy_hs)),
    ]
    # YB66 → D2
    dy_ls = round((d2_5[1] + d2_6[1]) / 2, 2)
    o += [
        wire(d2_6, (d2_6[0], dy_ls)),
        wire((d2_6[0], dy_ls), (round(d2_6[0] + 15.24, 2), dy_ls)),
        junction((d2_6[0], dy_ls)),
        label("YB66", (round(d2_6[0] + 15.24, 2), dy_ls)),
    ]

    # ---- Shared INH_EN_n: header + 10k pull-up ----
    inh_bus = (200.0, 240.0)  # vertical spine for both driver IN_A
    o += [
        label("INH_EN_n", (round(inh_bus[0] - 5.08, 2), inh_bus[1]), 180),
        wire((round(inh_bus[0] - 5.08, 2), inh_bus[1]), inh_bus),
        junction(inh_bus),
    ]
    # pull-up
    rx, ry = round(inh_bus[0] - 15.24, 2), round(inh_bus[1] - 12.7, 2)
    o.append(symbol_inst("Device:R", "R14", "10k", rx, ry, ["1", "2"], footprint=FP_R))
    rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
    o += [
        wire(rb, (rx, inh_bus[1])),
        wire((rx, inh_bus[1]), inh_bus),
        junction((rx, inh_bus[1])),
        power("power:+3V3", "#PWR_R14", "+3V3", rx, round(rt[1] - 7.62, 2)),
        wire(rt, (rx, round(rt[1] - 7.62, 2))),
    ]
    # header
    jx, jy = round(inh_bus[0] - 35.56, 2), inh_bus[1]
    o.append(symbol_inst("Connector:Conn_01x01", "J5", "INH_EN_n", jx, jy, ["1"], rot=180, footprint=FP_J))
    jp = pin_xy(jx, jy, -5.08, 0, 180)
    o.append(wire(jp, inh_bus))

    # ---- U7 TC4427 → INH_HS from INH_EN_n; U8 TC4427 → INH_LS via 2N7002 invert ----
    add_driver(
        o, uref="U7", lib_id="Driver_FET:TC4427xOA", value="TC4427A",
        ux=250.0, uy=230.0, out_net="INH_HS", c_lo="C11", c_hi="C12",
        pwr_suffix="U7", inh_junc=inh_bus,
    )

    # 2N7002 inverter: gate←INH_EN_n, source←GND, drain←INH_LS_en (10k→+3V3)
    qx7, qy7 = 200.0, 300.0
    o.append(
        symbol_inst(
            "Transistor_FET:2N7002",
            "Q7",
            "2N7002",
            qx7,
            qy7,
            ["1", "2", "3"],
            footprint="Package_TO_SOT_SMD:SOT-23",
        )
    )
    g = pin_xy(qx7, qy7, -2.54, 0)
    s = pin_xy(qx7, qy7, 2.54, -2.54)
    d = pin_xy(qx7, qy7, 2.54, 2.54)
    ls_bus = (200.0, 320.0)
    o += [
        wire(g, (inh_bus[0], g[1])),
        wire((inh_bus[0], g[1]), inh_bus),
        junction((inh_bus[0], g[1])),
        wire(s, (s[0], round(s[1] + 5.08, 2))),
        power("power:GND", "#PWR_Q7_S", "GND", s[0], round(s[1] + 7.62, 2)),
        wire((s[0], round(s[1] + 5.08, 2)), (s[0], round(s[1] + 7.62, 2))),
        wire(d, (ls_bus[0], d[1])),
        wire((ls_bus[0], d[1]), ls_bus),
        junction((ls_bus[0], d[1])),
        junction(ls_bus),
        label("INH_LS_en", (round(ls_bus[0] - 5.08, 2), ls_bus[1]), 180),
    ]
    rx, ry = round(ls_bus[0] - 15.24, 2), round(ls_bus[1] - 12.7, 2)
    o.append(symbol_inst("Device:R", "R25", "10k", rx, ry, ["1", "2"], footprint=FP_R))
    rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
    o += [
        wire(rb, (rx, ls_bus[1])),
        wire((rx, ls_bus[1]), ls_bus),
        junction((rx, ls_bus[1])),
        power("power:+3V3", "#PWR_R25", "+3V3", rx, round(rt[1] - 7.62, 2)),
        wire(rt, (rx, round(rt[1] - 7.62, 2))),
    ]

    add_driver(
        o, uref="U8", lib_id="Driver_FET:TC4427xOA", value="TC4427A",
        ux=250.0, uy=320.0, out_net="INH_LS", c_lo="C13", c_hi="C14",
        pwr_suffix="U8", inh_junc=ls_bus,
    )

    o += [
        f'''\t(rectangle
\t\t(start 12.70 205.00)
\t\t(end 360.00 380.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("INHIBIT — series YB65→fold→YB66→CCS", 15.24, 210.0, 1.524),
        text(
            "FDS8958A P→YB65 / N→YB66→CCS_RET. Both TC4427A: HS←INH_EN_n, "
            "LS←INH_LS_en (2N7002 invert of INH_EN_n). Do not dump into AGND or SENSE_*.",
            15.24, 372.0,
        ),
    ]

    sch = sch.replace("\t(sheet_instances", "\n".join(o) + "\n\t(sheet_instances", 1)
    SCH.write_text(sch)
    print(f"Appended Inhibit block to {SCH}")


if __name__ == "__main__":
    main()
