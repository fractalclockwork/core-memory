#!/usr/bin/env python3
"""Append Stage 4 gate drive (TC4427/TC4426) without touching Stages 1–3."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
KICAD = Path("/usr/share/kicad/symbols")
SHEET_UUID = "de7211a3-1219-4154-b2a8-36f4d2dfd28b"
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


def extract(path: Path, name: str) -> str:
    text = path.read_text()
    start = text.find(f'(symbol "{name}"')
    if start < 0:
        raise KeyError(f"{name} in {path}")
    start = text.rfind("\n", 0, start) + 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise RuntimeError(name)


def embed_as(lib_id: str, body: str, original_name: str) -> str:
    body = body.replace(f'(symbol "{original_name}"', f'(symbol "{lib_id}"', 1)
    return "\n".join("\t\t" + ln if ln else ln for ln in body.splitlines())


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


def strip_stage4(sch: str) -> str:
    marker = "\t(sheet_instances"
    end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing — schematic truncated?")
    if "STAGE 4" not in sch and '(property "Reference" "U5"' not in sch:
        return sch
    starts = []
    for needle in (
        '\t(text "STAGE 4',
        '\t(rectangle\n\t\t(start 370.00 110.00)',
        '(property "Reference" "U5"',
    ):
        i = sch.find(needle)
        if needle.startswith("(property"):
            if i > 0:
                i = sch.rfind("\t(symbol\n", 0, i)
        if 0 <= i < end:
            starts.append(i)
    if not starts:
        raise SystemExit("STAGE 4 present but cannot locate block")
    start = min(starts)
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def ensure_lib(sch: str) -> str:
    needed = [
        ("Driver_FET:TC4427xOA", KICAD / "Driver_FET.kicad_sym", "TC4427xOA"),
        ("Driver_FET:TC4426xOA", KICAD / "Driver_FET.kicad_sym", "TC4426xOA"),
        ("Connector:Conn_01x01", KICAD / "Connector_Generic.kicad_sym", "Conn_01x01"),
    ]
    embeds = []
    for lib_id, path, src in needed:
        if f'(symbol "{lib_id}"' in sch:
            continue
        # Connector_Generic uses library name Connector in projects often as Connector:Conn_01x01
        # KiCad lib file is Connector_Generic — lib_id conventionally Connector:Conn_01x01
        embeds.append(embed_as(lib_id, extract(path, src), src))
    if not embeds:
        return sch
    m = re.search(r"\t\(lib_symbols\n", sch)
    start = m.end()
    depth = 1
    i = start
    while i < len(sch) and depth:
        if sch[i] == "(":
            depth += 1
        elif sch[i] == ")":
            depth -= 1
        i += 1
    return sch[: i - 1] + "\n".join(embeds) + "\n\t" + sch[i - 1 :]


def driver_block(
    o: list[str],
    *,
    uref: str,
    lib_id: str,
    value: str,
    ux: float,
    uy: float,
    in_a: str,
    in_b: str,
    out_a: str,
    out_b: str,
    r_a: str,
    r_b: str,
    j_a: str,
    j_b: str,
    c_lo: str,
    c_hi: str,
    pwr_suffix: str,
) -> None:
    """One dual TC442x with pull-ups, headers, bypass."""
    FP_U = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"
    FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"

    o.append(symbol_inst(lib_id, uref, value, ux, uy, ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_U))

    # Pins (lib): NC1(-7.62,0), IN_A(-10.16,2.54), GND(0,-10.16), IN_B(-10.16,-2.54),
    # OUT_B(10.16,-2.54), VDD(0,10.16), OUT_A(10.16,2.54), NC8(7.62,0)
    nc1 = pin_xy(ux, uy, -7.62, 0)
    ina = pin_xy(ux, uy, -10.16, 2.54)
    gnd = pin_xy(ux, uy, 0, -10.16)
    inb = pin_xy(ux, uy, -10.16, -2.54)
    outb = pin_xy(ux, uy, 10.16, -2.54)
    vdd = pin_xy(ux, uy, 0, 10.16)
    outa = pin_xy(ux, uy, 10.16, 2.54)
    nc8 = pin_xy(ux, uy, 7.62, 0)
    o += [no_connect(nc1), no_connect(nc8)]

    # Outputs → gate labels (Stage 3)
    o += [
        wire(outa, (round(outa[0] + 10.16, 2), outa[1])),
        label(out_a, (round(outa[0] + 10.16, 2), outa[1])),
        wire(outb, (round(outb[0] + 10.16, 2), outb[1])),
        label(out_b, (round(outb[0] + 10.16, 2), outb[1])),
    ]

    # Power VDRIVE / GND on IC pins
    vp = (vdd[0], round(vdd[1] - 7.62, 2))
    vm = (gnd[0], round(gnd[1] + 7.62, 2))
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

    # Bypass caps to the right of IC, on VDRIVE/GND rails
    for cref, cval, cx in ((c_lo, "100n", round(ux + 25.4, 2)), (c_hi, "1u", round(ux + 40.64, 2))):
        cy = round((vp[1] + vm[1]) / 2, 2)
        o.append(symbol_inst("Device:C", cref, cval, cx, cy, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
        o += [
            wire(ct, (cx, vp[1])), wire((cx, vp[1]), vp), junction((cx, vp[1])),
            wire(cb, (cx, vm[1])), wire((cx, vm[1]), vm), junction((cx, vm[1])),
        ]

    # Input: IN ← junction ← label / 10k pull-up to +3V3 / header
    # Stagger pull-up X per channel so vertical R wires never share a column.
    for idx, (in_pin, net_n, rref, jref) in enumerate((
        (ina, in_a, r_a, j_a),
        (inb, in_b, r_b, j_b),
    )):
        junc = (round(in_pin[0] - 10.16, 2), in_pin[1])
        o += [wire(in_pin, junc), junction(junc)]
        o += [
            wire(junc, (round(junc[0] - 5.08, 2), junc[1])),
            label(net_n, (round(junc[0] - 5.08, 2), junc[1]), 180),
        ]
        # Unique X per channel (A left-er than B)
        rx = round(junc[0] - 12.7 - idx * 12.7, 2)
        ry = round(junc[1] - 12.7, 2)  # well above input row
        o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
        rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
        o += [
            wire(rb, (rx, junc[1])),
            wire((rx, junc[1]), junc),
            junction((rx, junc[1])),
            power("power:+3V3", f"#PWR_{rref}", "+3V3", rx, round(rt[1] - 7.62, 2)),
            wire(rt, (rx, round(rt[1] - 7.62, 2))),
        ]
        jx = round(junc[0] - 35.56 - idx * 2.54, 2)
        jy = junc[1]
        o.append(symbol_inst("Connector:Conn_01x01", jref, net_n, jx, jy, ["1"], rot=180, footprint=FP_J))
        jp = pin_xy(jx, jy, -5.08, 0, 180)
        o.append(wire(jp, junc))

def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")
    sch = strip_stage4(sch)
    sch = ensure_lib(sch)

    o: list[str] = []

    # Below Stage 3 box (ends y≈98)
    driver_block(
        o,
        uref="U5",
        lib_id="Driver_FET:TC4427xOA",
        value="TC4427A",
        ux=520.0,
        uy=155.0,
        in_a="X_HS0_n",
        in_b="Y_HS0_n",
        out_a="X_HS0",
        out_b="Y_HS0",
        r_a="R10",
        r_b="R11",
        j_a="J1",
        j_b="J2",
        c_lo="C7",
        c_hi="C8",
        pwr_suffix="U5",
    )
    driver_block(
        o,
        uref="U6",
        lib_id="Driver_FET:TC4426xOA",
        value="TC4426A",
        ux=520.0,
        uy=250.0,
        in_a="X_LS0_n",
        in_b="Y_LS0_n",
        out_a="X_LS0",
        out_b="Y_LS0",
        r_a="R12",
        r_b="R13",
        j_a="J3",
        j_b="J4",
        c_lo="C9",
        c_hi="C10",
        pwr_suffix="U6",
    )

    o += [
        f'''\t(rectangle
\t\t(start 370.00 110.00)
\t\t(end 680.00 310.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("STAGE 4 — Gate drive (fail-safe pull-ups)", 375.0, 115.0, 1.524),
        text(
            "TC4427A → X/Y_HS0; TC4426A → X/Y_LS0; 10k to +3V3 on *_n; VDRIVE power; headers J1–J4",
            375.0, 305.0,
        ),
    ]

    sch = sch.replace("\t(sheet_instances", "\n".join(o) + "\n\t(sheet_instances", 1)
    SCH.write_text(sch)
    print(f"Appended Stage 4 gate drive to {SCH}")


if __name__ == "__main__":
    main()
