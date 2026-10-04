#!/usr/bin/env python3
"""Build Drive Block page (TC4427A + FDS8958A) and the 2x2 steer sheet.

Hierarchical pins use N = axis (X/Y) and n = line index (0..63):

  N_HSn      HS gate input (active-low from 74AHC138)
  N_LSn      LS gate input (active-high from 74AHC238)
  N_HS_OUT   P-FET switch node (SS14s live on the steer sheet)
  N_LS_OUT   N-FET switch node
  VDRIVE / CCS_RET

Root places a drive_block call per group 0..7, axis, and direction (32),
and one steer sheet for lines 0..63. FWD sources B and sinks A. REV swaps
those ends. line = 8*HS + LS.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
SCH = CORE / "core.kicad_sch"
PRO = CORE / "core.kicad_pro"
DRIVE_BLOCK = CORE / "drive_block.kicad_sch"
STEER = CORE / "steer_2x2.kicad_sch"
OLD_DRIVE = CORE / "drive.kicad_sch"
OLD_XY = CORE / "xy_drive.kicad_sch"
SHORT = CORE / "xy_drive_short.kicad_sch"
PROJECT = "core"

ROOT_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
DRIVE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-111111111111"
STEER_UUID = "a1b2c3d4-e5f6-4789-a012-111111111119"
# Retired multi-instance UUIDs (strip if still on root)
OLD_DRIVE_UUIDS = {
    DRIVE_BLOCK_UUID,
    "a1b2c3d4-e5f6-4789-a012-222222222222",
    "a1b2c3d4-e5f6-4789-a012-cccccccccccc",
}

# name, uuid, page, x, y, hs gate, ls gate, ccs, hs node, ls node
# Groups 0 and 1 keep the original UUIDs and coordinates.
DRIVE_CALLS = [
    ("X0 FWD", DRIVE_BLOCK_UUID, "2", 510.0, 18.0, "X_HS0_n", "X_LS0_en", "CCS_X", "XHS0", "XLS0"),
    ("X1 FWD", "a1b2c3d4-e5f6-4789-a012-111111111112", "14", 572.0, 18.0, "X_HS1_n", "X_LS1_en", "CCS_X", "XHS1", "XLS1"),
    ("X0 REV", "a1b2c3d4-e5f6-4789-a012-111111111113", "15", 634.0, 18.0, "X_HS0r_n", "X_LS0r_en", "CCS_X", "XHS0R", "XLS0R"),
    ("X1 REV", "a1b2c3d4-e5f6-4789-a012-111111111114", "16", 696.0, 18.0, "X_HS1r_n", "X_LS1r_en", "CCS_X", "XHS1R", "XLS1R"),
    ("Y0 FWD", "a1b2c3d4-e5f6-4789-a012-111111111115", "17", 510.0, 58.0, "Y_HS0_n", "Y_LS0_en", "CCS_Y", "YHS0", "YLS0"),
    ("Y1 FWD", "a1b2c3d4-e5f6-4789-a012-111111111116", "18", 572.0, 58.0, "Y_HS1_n", "Y_LS1_en", "CCS_Y", "YHS1", "YLS1"),
    ("Y0 REV", "a1b2c3d4-e5f6-4789-a012-111111111117", "19", 634.0, 58.0, "Y_HS0r_n", "Y_LS0r_en", "CCS_Y", "YHS0R", "YLS0R"),
    ("Y1 REV", "a1b2c3d4-e5f6-4789-a012-111111111118", "20", 696.0, 58.0, "Y_HS1r_n", "Y_LS1r_en", "CCS_Y", "YHS1R", "YLS1R"),
]
# Groups 2..7. Same pin pattern. Placed below the 2x2 bring-up rows.
_EXTRA_BANKS = (
    ("X", "FWD", "", "CCS_X", 320.0),
    ("X", "REV", "r", "CCS_X", 360.0),
    ("Y", "FWD", "", "CCS_Y", 400.0),
    ("Y", "REV", "r", "CCS_Y", 440.0),
)
for _gi, _g in enumerate(range(2, 8)):
    for _bi, (_axis, _dir, _rev, _ccs, _y) in enumerate(_EXTRA_BANKS):
        _n = _gi * len(_EXTRA_BANKS) + _bi
        _tag = f"{_rev}"
        DRIVE_CALLS.append((
            f"{_axis}{_g} {_dir}",
            f"a1b2c3d4-e5f6-4789-a012-11111111{0x120 + _n:04x}",
            str(25 + _n),
            510.0 + _gi * 62.0,
            _y,
            f"{_axis}_HS{_g}{_tag}_n",
            f"{_axis}_LS{_g}{_tag}_en",
            _ccs,
            f"{_axis}HS{_g}{'R' if _rev else ''}",
            f"{_axis}LS{_g}{'R' if _rev else ''}",
        ))

SHEET_ORDER = [
    (ROOT_UUID, "core"),
    *[(c[1], c[0]) for c in DRIVE_CALLS],
    (STEER_UUID, "Steer 2x2"),
    ("a1b2c3d4-e5f6-4789-a012-333333333333", "X FWD"),
    ("a1b2c3d4-e5f6-4789-a012-333333333334", "Y FWD"),
    ("a1b2c3d4-e5f6-4789-a012-333333333335", "X REV"),
    ("a1b2c3d4-e5f6-4789-a012-333333333336", "Y REV"),
    ("a1b2c3d4-e5f6-4789-a012-555555555555", "Decoupling Logic"),
    ("a1b2c3d4-e5f6-4789-a012-666666666666", "Decoupling VDRIVE"),
    ("a1b2c3d4-e5f6-4789-a012-777777777777", "Sense"),
    ("a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb", "Magnetic Cores"),
    ("a1b2c3d4-e5f6-4789-a012-888888888888", "CCS X"),
    ("a1b2c3d4-e5f6-4789-a012-888888888889", "CCS Y"),
    ("a1b2c3d4-e5f6-4789-a012-88888888888a", "CCS INH"),
    ("a1b2c3d4-e5f6-4789-a012-999999999999", "Inhibit"),
    ("a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaaa", "Decode CTRL"),
    ("a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaab", "Decode CTRL Y"),
]

FP_Q = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
FP_D = "Diode_SMD:D_SMA"
FP_U = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"
FP_C = "Capacitor_SMD:C_0805_2012Metric"

SHEET_W = 50.0
SHEET_H = 32.0
SHEET_X = 400.0
SHEET_Y = 18.0
SHEET_PAGE = "2"

LEFT_PINS = (
    ("N_HSn", "input"),
    ("N_LSn", "input"),
    ("VDRIVE", "passive"),
    ("CCS_RET", "passive"),
)
RIGHT_PINS = (
    ("N_HS_OUT", "passive"),
    ("N_LS_OUT", "passive"),
)

REFS = {
    "Q": "Q10",
    "Dhs": "D20",
    "Dls": "D21",
    "U": "U20",
    "Rhs": "R30",
    "Rls": "R31",
    "Jhs": "J20",
    "Jls": "J21",
    "Clo": "C30",
    "Chi": "C31",
}

TITLE = "DRIVE — eight drive_block calls (groups 0 and 1, X and Y, FWD and REV) plus steer_2x2"
OLD_TITLES = (
    "xy_drive REV:",
    "xy_drive:",
    "DRIVE — XY hierarchy",
    "DRIVE — drive.kicad_sch",
    "DRIVE — Drive Block",
    "DRIVE — eight drive_block",
)

DRIVE_PATH = f"/{ROOT_UUID}/{DRIVE_BLOCK_UUID}"


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


def extract_lib(sch: str, lib_id: str) -> str:
    start = sch.find(f'(symbol "{lib_id}"')
    if start < 0:
        raise KeyError(lib_id)
    start = sch.rfind("\n", 0, start) + 1
    depth = 0
    for i in range(start, len(sch)):
        if sch[i] == "(":
            depth += 1
        elif sch[i] == ")":
            depth -= 1
            if depth == 0:
                return sch[start : i + 1]
    raise RuntimeError(lib_id)


def prop(name: str, value: str, at: str, hide: bool = False) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    return f'''\t\t(property "{name}" "{value}"
\t\t\t(at {at}){hide_s}
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)'''


def bump_ref(ref: str, i: int) -> str:
    if i == 0:
        return ref
    return re.sub(r"\d+", lambda m: str(int(m.group(0)) + i * 10), ref, count=1)


def instances(ref: str, paths: list[tuple[str, str]] | None = None) -> str:
    if paths is None:
        paths = [
            (f"/{ROOT_UUID}/{call[1]}", bump_ref(ref, i))
            for i, call in enumerate(DRIVE_CALLS)
        ]
    body = "\n".join(
        f'''\t\t\t\t(path "{path}"
\t\t\t\t\t(reference "{r}")
\t\t\t\t\t(unit 1)
\t\t\t\t)'''
        for path, r in paths
    )
    return f'''\t\t(instances
\t\t\t(project "{PROJECT}"
{body}
\t\t\t)
\t\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, *, rot=0, footprint="", paths=None):
    pins_s = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, f"{x + 2.54} {y - 10.16} 0")}
{prop("Value", value, f"{x + 2.54} {y - 7.62} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
{pins_s}
{instances(ref, paths)}
\t)'''


def power(lib_id, ref, value, x, y, *, paths=None):
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
{prop("Value", value, f"{x} {y - 2.54} 0")}
{prop("Footprint", "", f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
\t\t(pin "1"
\t\t\t(uuid "{uid()}")
\t\t)
{instances(ref, paths)}
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


def hier(name, shape, p, rot=0):
    just = "right" if rot == 180 else "left"
    return f'''\t(hierarchical_label "{name}"
\t\t(shape {shape})
\t\t(at {p[0]} {p[1]} {rot})
\t\t(effects
\t\t\t(font (size 1.27 1.27))
\t\t\t(justify {just})
\t\t)
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


def half_bridge(o: list[str], *, qx: float, qy: float, ux: float, uy: float) -> None:
    """One channel: FDS8958A + one TC4427A. Switch nodes leave the sheet; diodes are on steer_2x2."""
    o.append(symbol_inst("core_memory:FDS8958A", REFS["Q"], "FDS8958A", qx, qy, list("12345678"), footprint=FP_Q))
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

    dy_hs = round((d1_7[1] + d1_8[1]) / 2, 2)
    hs_out = (round(qx + 25.4, 2), dy_hs)
    o += [
        wire(d1_7, (d1_7[0], dy_hs)),
        wire((d1_7[0], dy_hs), hs_out),
        junction((d1_7[0], dy_hs)),
        hier("N_HS_OUT", "passive", hs_out),
    ]

    dy_ls = round((d2_5[1] + d2_6[1]) / 2, 2)
    ls_out = (round(qx + 25.4, 2), dy_ls)
    o += [
        wire(d2_6, (d2_6[0], dy_ls)),
        wire((d2_6[0], dy_ls), ls_out),
        junction((d2_6[0], dy_ls)),
        hier("N_LS_OUT", "passive", ls_out),
    ]

    o += [
        wire(s1, (round(s1[0] - 10.16, 2), s1[1])),
        hier("VDRIVE", "passive", (round(s1[0] - 10.16, 2), s1[1]), 180),
        wire(s2, (round(s2[0] - 10.16, 2), s2[1])),
        hier("CCS_RET", "passive", (round(s2[0] - 10.16, 2), s2[1]), 180),
        wire(g1, (round(g1[0] - 7.62, 2), g1[1])),
        label("GATE_HS", (round(g1[0] - 7.62, 2), g1[1]), 180),
        wire(g2, (round(g2[0] - 7.62, 2), g2[1])),
        label("GATE_LS", (round(g2[0] - 7.62, 2), g2[1]), 180),
    ]

    o.append(symbol_inst("Driver_FET:TC4427xOA", REFS["U"], "TC4427A", ux, uy, list("12345678"), footprint=FP_U))
    nc1 = pin_xy(ux, uy, -7.62, 0)
    ina = pin_xy(ux, uy, -10.16, 2.54)
    gnd = pin_xy(ux, uy, 0, -10.16)
    inb = pin_xy(ux, uy, -10.16, -2.54)
    outb = pin_xy(ux, uy, 10.16, -2.54)
    vdd = pin_xy(ux, uy, 0, 10.16)
    outa = pin_xy(ux, uy, 10.16, 2.54)
    nc8 = pin_xy(ux, uy, 7.62, 0)
    o += [no_connect(nc1), no_connect(nc8)]
    o += [
        wire(outa, (round(outa[0] + 10.16, 2), outa[1])),
        label("GATE_HS", (round(outa[0] + 10.16, 2), outa[1])),
        wire(outb, (round(outb[0] + 10.16, 2), outb[1])),
        label("GATE_LS", (round(outb[0] + 10.16, 2), outb[1])),
    ]

    vp = (vdd[0], round(vdd[1] - 7.62, 2))
    vm = (gnd[0], round(gnd[1] + 7.62, 2))
    o += [
        wire(vdd, vp),
        junction(vp),
        power("power:VDRIVE", f"#PWR_{REFS['U']}_VDD", "VDRIVE", vp[0], round(vp[1] - 5.08, 2)),
        wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
        wire(gnd, vm),
        junction(vm),
        power("power:GND", f"#PWR_{REFS['U']}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
        wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
    ]

    # Local VDRIVE bypass 100n + 1u (travels with each Drive Block instance)
    bx = round(ux + 22.86, 2)
    by = round((vp[1] + vm[1]) / 2, 2)
    for cref, cval, dx in ((REFS["Clo"], "100n", -5.08), (REFS["Chi"], "1u", 5.08)):
        cx = round(bx + dx, 2)
        o.append(symbol_inst("Device:C", cref, cval, cx, by, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, by, 0, 3.81), pin_xy(cx, by, 0, -3.81)
        o += [
            wire(ct, (cx, vp[1])),
            wire((cx, vp[1]), vp),
            junction((cx, vp[1])),
            wire(cb, (cx, vm[1])),
            wire((cx, vm[1]), vm),
            junction((cx, vm[1])),
        ]

    for in_pin, net, rref, jref, pull in (
        (ina, "N_HSn", REFS["Rhs"], REFS["Jhs"], "+3V3"),
        (inb, "N_LSn", REFS["Rls"], REFS["Jls"], "GND"),
    ):
        junc = (round(in_pin[0] - 10.16, 2), in_pin[1])
        o += [wire(in_pin, junc), junction(junc)]
        hp = (round(junc[0] - 15.24, 2), junc[1])
        o += [wire(junc, hp), hier(net, "input", hp, 180)]
        rx = round(junc[0] - 5.08, 2)
        if pull == "GND":
            ry = round(junc[1] + 12.7, 2)
            o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
            rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
            o += [
                wire(rt, (rx, junc[1])),
                wire((rx, junc[1]), junc),
                junction((rx, junc[1])),
                power("power:GND", f"#PWR_{rref}", "GND", rx, round(rb[1] + 7.62, 2)),
                wire(rb, (rx, round(rb[1] + 7.62, 2))),
            ]
        else:
            ry = round(junc[1] - 12.7, 2)
            o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
            rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
            o += [
                wire(rb, (rx, junc[1])),
                wire((rx, junc[1]), junc),
                junction((rx, junc[1])),
                power("power:+3V3", f"#PWR_{rref}", "+3V3", rx, round(rt[1] - 7.62, 2)),
                wire(rt, (rx, round(rt[1] - 7.62, 2))),
            ]
        jx, jy = round(junc[0] - 30.48, 2), junc[1]
        o.append(symbol_inst("Connector:Conn_01x01", jref, net, jx, jy, ["1"], rot=180, footprint=FP_J))
        o.append(wire(pin_xy(jx, jy, -5.08, 0, 180), junc))


def build_drive_block_page(lib_syms: str) -> str:
    o: list[str] = [
        text("Drive Block — TC4427A (HS+LS) + FDS8958A; switch nodes N_HS_OUT / N_LS_OUT", 20, 12, 1.524),
        text("N_HSn active-low (138); N_LSn active-high (238). SS14s are on steer_2x2.", 20, 18),
    ]
    half_bridge(o, qx=160.0, qy=70.0, ux=75.0, uy=70.0)
    body = "\n".join(o)
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{uid()}")
\t(paper "A3")
\t(title_block
\t\t(title "Drive Block")
\t\t(comment 1 "N=axis X/Y; n=group; N_HS_OUT/N_LS_OUT are the switch nodes")
\t)
\t(lib_symbols
{lib_syms}
\t)
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def extract_blocks(text: str, tag: str):
    pattern = re.compile(rf"^(?:\t)?\({tag}\b", re.M)
    for m in pattern.finditer(text):
        start = m.start()
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    yield start, i + 1, text[start : i + 1]
                    break


def is_drive_sheet(block: str) -> bool:
    return bool(
        re.search(
            r'\(property "Sheetfile" "(?:xy_drive(?:_short)?|drive|drive_block|steer_2x2)\.kicad_sch"',
            block,
        )
    )


def sheet_pin_at(sx: float, sy: float, index: int, side: str) -> tuple[float, float]:
    if side == "left":
        return sx, round(sy + 6.0 + index * 5.08, 2)
    return round(sx + SHEET_W, 2), round(sy + 10.0 + index * 8.0, 2)


def sheet_block(call: tuple) -> str:
    name, uuid_, page, sx, sy, hs, ls, ccs, hs_out, ls_out = call
    parent = {
        "N_HSn": hs,
        "N_LSn": ls,
        "VDRIVE": "VDRIVE",
        "CCS_RET": ccs,
        "N_HS_OUT": hs_out,
        "N_LS_OUT": ls_out,
    }
    pins = []
    for i, (pname, shape) in enumerate(LEFT_PINS):
        x, y = sheet_pin_at(sx, sy, i, "left")
        pins.append(
            f'''\t\t(pin "{pname}" {shape}
\t\t\t(at {x} {y} 180)
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)'''
        )
    for i, (pname, shape) in enumerate(RIGHT_PINS):
        x, y = sheet_pin_at(sx, sy, i, "right")
        pins.append(
            f'''\t\t(pin "{pname}" {shape}
\t\t\t(at {x} {y} 0)
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify right))
\t\t)'''
        )
    pins_s = "\n".join(pins)
    return f'''\t(sheet
\t\t(at {sx} {sy})
\t\t(size {SHEET_W} {SHEET_H})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0))
\t\t(uuid "{uuid_}")
\t\t(property "Sheetname" "{name}"
\t\t\t(at {sx} {round(sy - 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27) (thickness 0.254) (bold yes)) (justify left bottom))
\t\t)
\t\t(property "Sheetfile" "drive_block.kicad_sch"
\t\t\t(at {sx} {round(sy + SHEET_H + 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t)
{pins_s}
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)''', parent


def sheet_stubs(call: tuple, parent: dict[str, str]) -> list[str]:
    _name, _uuid, _page, sx, sy, *_rest = call
    o: list[str] = []
    for i, (name, _shape) in enumerate(LEFT_PINS):
        x, y = sheet_pin_at(sx, sy, i, "left")
        outer = (round(x - 12.7, 2), y)
        o += [wire(outer, (x, y)), label(parent[name], outer, 180)]
    for i, (name, _shape) in enumerate(RIGHT_PINS):
        x, y = sheet_pin_at(sx, sy, i, "right")
        outer = (round(x + 12.7, 2), y)
        o += [wire((x, y), outer), label(parent[name], outer)]
    return o


def drop_spans(text: str, spans: list[tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]
    return text


def renumber_pages_after_drive_collapse(sch: str, multi_drive: bool) -> str:
    """When collapsing 4 drive sheets (pages 2-5) to 1 (page 2), shift later pages down by 3."""
    if not multi_drive:
        return sch
    spans = []
    for start, end, block in extract_blocks(sch, "sheet"):
        if is_drive_sheet(block):
            continue

        def repl(m: re.Match[str]) -> str:
            n = int(m.group(1))
            # Prior layout: Drive 2-5, Decode 6+ → new Decode starts at 3
            return f'(page "{n - 3}")' if n >= 6 else m.group(0)

        new = re.sub(r'\(page "(\d+)"\)', repl, block, count=1)
        if new != block:
            spans.append((start, end, new))
    for start, end, new in sorted(spans, key=lambda t: t[0], reverse=True):
        sch = sch[:start] + new + sch[end:]
    return sch


def _steer_nets() -> tuple[list[tuple[str, str, str]], tuple[str, ...], tuple[str, ...]]:
    """SS14s for lines 0..63. FWD sources B / sinks A. REV swaps the ends."""
    diodes: list[tuple[str, str, str]] = []
    n = 20
    for axis, a_name, b_name in (("X", "XA", "XB"), ("Y", "YA", "YB")):
        for line in range(64):
            hs, ls = divmod(line, 8)
            diodes.append((f"D{n}", f"{axis}HS{hs}", f"{b_name}{line}"))
            n += 1
            diodes.append((f"D{n}", f"{a_name}{line}", f"{axis}LS{ls}"))
            n += 1
            diodes.append((f"D{n}", f"{axis}HS{hs}R", f"{a_name}{line}"))
            n += 1
            diodes.append((f"D{n}", f"{b_name}{line}", f"{axis}LS{ls}R"))
            n += 1
    left: list[str] = []
    for axis in ("X", "Y"):
        for rev in ("", "R"):
            left += [f"{axis}HS{g}{rev}" for g in range(8)]
            left += [f"{axis}LS{g}{rev}" for g in range(8)]
    right = tuple(
        f"{prefix}{i}" for prefix in ("XA", "XB", "YA", "YB") for i in range(64)
    )
    return diodes, tuple(left), right


STEER_DIODES, STEER_LEFT, STEER_RIGHT = _steer_nets()
STEER_X, STEER_Y = 1020.0, 18.0
STEER_W, STEER_H = 90.0, 830.0


def steer_symbol(ref: str, x: float, y: float) -> str:
    path = f"/{ROOT_UUID}/{STEER_UUID}"
    return symbol_inst(
        "Diode:SS14", ref, "SS14", x, y, ["1", "2"], rot=180, footprint=FP_D,
        paths=[(path, ref)],
    )


def build_steer_page(lib_syms: str) -> str:
    o = [
        text("Steer — SS14, lines 0..63. Group HS diode-ORs its eight lines. LS selects the line.", 20, 12, 1.524),
        text("FWD sources B / sinks A. REV swaps the ends. line = 8*HS + LS.", 20, 18),
    ]
    for i, (ref, anode, cathode) in enumerate(STEER_DIODES):
        col, row = divmod(i, 256)
        x, y = 90.0 + col * 160.0, 30.0 + row * 3.0
        o.append(steer_symbol(ref, x, y))
        left = pin_xy(x, y, 3.81, 0, 180)
        right = pin_xy(x, y, -3.81, 0, 180)
        o += [
            wire(left, (round(left[0] - 6.0, 2), left[1])),
            hier(anode, "passive", (round(left[0] - 6.0, 2), left[1]), 180),
            wire(right, (round(right[0] + 6.0, 2), right[1])),
            hier(cathode, "passive", (round(right[0] + 6.0, 2), right[1])),
        ]
    body = "\n".join(o)
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{uid()}")
\t(paper "A0")
\t(title_block
\t\t(title "Steer")
\t\t(comment 1 "SS14 matrix for lines 0..63")
\t)
\t(lib_symbols
{lib_syms}
\t)
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def steer_sheet_block() -> str:
    sx, sy = STEER_X, STEER_Y
    pins = []
    for i, name in enumerate(STEER_LEFT):
        x, y = sx, round(sy + 8.0 + i * 12.5, 2)
        pins.append(
            f'''\t\t(pin "{name}" passive
\t\t\t(at {x} {y} 180)
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)'''
        )
    for i, name in enumerate(STEER_RIGHT):
        x, y = round(sx + STEER_W, 2), round(sy + 6.0 + i * 3.15, 2)
        pins.append(
            f'''\t\t(pin "{name}" passive
\t\t\t(at {x} {y} 0)
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify right))
\t\t)'''
        )
    pins_s = "\n".join(pins)
    return f'''\t(sheet
\t\t(at {sx} {sy})
\t\t(size {STEER_W} {STEER_H})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0))
\t\t(uuid "{STEER_UUID}")
\t\t(property "Sheetname" "Steer 2x2"
\t\t\t(at {sx} {round(sy - 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27) (thickness 0.254) (bold yes)) (justify left bottom))
\t\t)
\t\t(property "Sheetfile" "steer_2x2.kicad_sch"
\t\t\t(at {sx} {round(sy + STEER_H + 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t)
{pins_s}
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "21")
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def steer_stubs() -> list[str]:
    sx, sy = STEER_X, STEER_Y
    o: list[str] = []
    for i, name in enumerate(STEER_LEFT):
        x, y = sx, round(sy + 8.0 + i * 12.5, 2)
        outer = (round(x - 12.7, 2), y)
        o += [wire(outer, (x, y)), label(name, outer, 180)]
    for i, name in enumerate(STEER_RIGHT):
        x, y = round(sx + STEER_W, 2), round(sy + 6.0 + i * 3.15, 2)
        outer = (round(x + 8.0, 2), y)
        o += [wire((x, y), outer), label(name, outer)]
        # Edge receptacle, one contact per plane net.
        jref = f"J{500 + i}"
        cx = round(x + 18.0, 2)
        o.append(symbol_inst(
            "Connector:Conn_01x01", jref, "Edge", cx, y, ["1"],
            rot=0, footprint=FP_J, paths=[(f"/{ROOT_UUID}", jref)],
        ))
        # Conn_01x01 pin 1 sits 5.08 mm left of the symbol origin.
        o += [wire(outer, (round(cx - 5.08, 2), y))]
    return o


PIO_NETS = (
    "ADDR_XH0", "ADDR_XH1", "ADDR_XH2", "ADDR_XL0", "ADDR_XL1", "ADDR_XL2",
    "ADDR_YH0", "ADDR_YH1", "ADDR_YH2", "ADDR_YL0", "ADDR_YL1", "ADDR_YL2",
    "DEC_EN", "FWD_EN_n", "REV_EN_n", "INH_EN_n", "SENSE_STROBE",
)


def pio_header() -> list[str]:
    o = [text("RP2040 timing header. These nets are the e2e stimulus.", 20, 200, 1.27)]
    for i, name in enumerate(PIO_NETS):
        x, y = 20.0, round(210.0 + i * 5.08, 2)
        ref = f"J{400 + i}"
        o.append(symbol_inst(
            "Connector:Conn_01x01", ref, "PIO", x, y, ["1"],
            rot=0, footprint=FP_J, paths=[(f"/{ROOT_UUID}", ref)],
        ))
        pin = (round(x - 5.08, 2), y)
        outer = (round(x + 7.62, 2), y)
        o += [wire(pin, outer), label(name, outer)]
    return o


def retarget_root(sch: str) -> str:
    drive_pins: set[tuple[float, float]] = set()
    remove: list[tuple[int, int]] = []
    multi_drive = False
    drive_sheet_count = 0
    for start, end, block in extract_blocks(sch, "sheet"):
        if not is_drive_sheet(block):
            continue
        drive_sheet_count += 1
        name_m = re.search(r'\(property "Sheetname" "([^"]+)"', block)
        if name_m and name_m.group(1) != "Drive Block":
            multi_drive = True
        for xm, ym in re.findall(r'\(pin "[^"]+" [^\s]+\s+\(at ([0-9.-]+) ([0-9.-]+)', block):
            drive_pins.add((round(float(xm), 2), round(float(ym), 2)))
        remove.append((start, end))

    del multi_drive, drive_sheet_count

    # Rescan (sheet removal is by file name; pages stay put)
    remove = []
    drive_pins = set()
    for start, end, block in extract_blocks(sch, "sheet"):
        if not is_drive_sheet(block):
            continue
        for xm, ym in re.findall(r'\(pin "[^"]+" [^\s]+\s+\(at ([0-9.-]+) ([0-9.-]+)', block):
            drive_pins.add((round(float(xm), 2), round(float(ym), 2)))
        remove.append((start, end))

    stub_outers: set[tuple[float, float]] = set()
    wire_spans: list[tuple[int, int]] = []
    for start, end, block in extract_blocks(sch, "wire"):
        pts = [
            (round(float(a), 2), round(float(b), 2))
            for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", block)
        ]
        if len(pts) == 2 and (pts[0] in drive_pins or pts[1] in drive_pins):
            wire_spans.append((start, end))
            for p in pts:
                if p not in drive_pins:
                    stub_outers.add(p)
    remove.extend(wire_spans)

    for start, end, block in extract_blocks(sch, "label"):
        m = re.search(r'\(at ([0-9.-]+) ([0-9.-]+)', block)
        if not m:
            continue
        p = (round(float(m.group(1)), 2), round(float(m.group(2)), 2))
        if p in stub_outers:
            remove.append((start, end))

    for start, end, block in extract_blocks(sch, "text"):
        tm = re.search(r'\(text "([^"]*)"', block)
        if tm and tm.group(1).startswith(OLD_TITLES):
            remove.append((start, end))

    sch = drop_spans(sch, remove)
    chunks = [text(TITLE, 510, 10, 1.524)]
    for call in DRIVE_CALLS:
        block, parent = sheet_block(call)
        chunks.append(block)
        chunks.extend(sheet_stubs(call, parent))
    chunks.append(steer_sheet_block())
    chunks.extend(steer_stubs())
    chunks.extend(pio_header())
    marker = "\t(sheet_instances"
    if marker not in sch:
        marker = "(sheet_instances"
    if marker not in sch:
        raise SystemExit("sheet_instances missing")
    return sch.replace(marker, "\n".join(chunks) + "\n" + marker, 1)


def main() -> None:
    sch = SCH.read_text()
    needed = [
        "core_memory:FDS8958A",
        "Diode:SS14",
        "Driver_FET:TC4427xOA",
        "Device:R",
        "Connector:Conn_01x01",
        "Device:C",
        "power:VDRIVE",
        "power:+3V3",
        "power:GND",
    ]
    lib_syms = "\n".join(extract_lib(sch, n) for n in needed)
    DRIVE_BLOCK.write_text(build_drive_block_page(lib_syms))
    print(f"Wrote {DRIVE_BLOCK}")
    diode_lib = extract_lib(sch, "Diode:SS14")
    STEER.write_text(build_steer_page(diode_lib))
    print(f"Wrote {STEER}")

    sch = retarget_root(sch)
    SCH.write_text(sch)
    print(f"Updated {SCH}")

    for old in (OLD_DRIVE, OLD_XY, SHORT):
        if old.exists():
            old.unlink()
            print(f"Removed {old.name}")

    pro = json.loads(PRO.read_text())
    pro["sheets"] = [[u, n] for u, n in SHEET_ORDER]
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    print("Updated core.kicad_pro sheets")


if __name__ == "__main__":
    main()
