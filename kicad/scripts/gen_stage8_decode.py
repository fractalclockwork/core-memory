#!/usr/bin/env python3
"""Append Stage 8 address decode (74AHC138×4 + FWD/REV buffers) without touching 1–7."""
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
{prop("Reference", ref, f"{x + 2.54} {y - 15.24} 0")}
{prop("Value", value, f"{x + 2.54} {y - 12.7} 0")}
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


def strip_stage8(sch: str) -> str:
    marker = "\t(sheet_instances"
    end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing")
    if "STAGE 8" not in sch and '(property "Reference" "U11"' not in sch and '(property "Reference" "J10"' not in sch:
        return sch
    starts = []
    for needle in (
        '\t(text "STAGE 8',
        '\t(rectangle\n\t\t(start 230.00 210.00)',
        '(property "Reference" "J10"',
        '(property "Reference" "R19"',
        '(property "Reference" "U11"',
        '(property "Reference" "U15"',
        '(property "Reference" "U16"',
    ):
        i = sch.find(needle)
        if needle.startswith("(property") and i > 0:
            i = sch.rfind("\t(symbol\n", 0, i)
        if 0 <= i < end:
            starts.append(i)
    if not starts:
        raise SystemExit("STAGE 8 present but cannot locate block")
    start = min(starts)
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def ensure_lib(sch: str) -> str:
    needed = [
        ("74xx:74HC138", KICAD / "74xx.kicad_sym", "74HC138"),
        ("74xx:74LS125", KICAD / "74xx.kicad_sym", "74LS125"),
    ]
    embeds = []
    for lib_id, path, src in needed:
        if f'(symbol "{lib_id}"' in sch:
            continue
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


def decoder_138(
    o: list[str],
    *,
    uref: str,
    ux: float,
    uy: float,
    y0_net: str,
    pwr_suffix: str,
) -> None:
    """One 74AHC138: Y0 → y0_net; Y1–Y7 NC; A[2:0]/E*/E2 shared labels; local bypass."""
    FP_U = "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"

    pins = [str(n) for n in range(1, 17)]
    o.append(symbol_inst("74xx:74HC138", uref, "74AHC138", ux, uy, pins, footprint=FP_U))

    # Pin map (lib coords)
    a0 = pin_xy(ux, uy, -10.16, 10.16)
    a1 = pin_xy(ux, uy, -10.16, 7.62)
    a2 = pin_xy(ux, uy, -10.16, 5.08)
    e0 = pin_xy(ux, uy, -10.16, -2.54)
    e1 = pin_xy(ux, uy, -10.16, -5.08)
    e2 = pin_xy(ux, uy, -10.16, -7.62)
    y7 = pin_xy(ux, uy, 10.16, -7.62)
    gnd = pin_xy(ux, uy, 0, -12.7)
    y6 = pin_xy(ux, uy, 10.16, -5.08)
    y5 = pin_xy(ux, uy, 10.16, -2.54)
    y4 = pin_xy(ux, uy, 10.16, 0)
    y3 = pin_xy(ux, uy, 10.16, 2.54)
    y2 = pin_xy(ux, uy, 10.16, 5.08)
    y1 = pin_xy(ux, uy, 10.16, 7.62)
    y0 = pin_xy(ux, uy, 10.16, 10.16)
    vcc = pin_xy(ux, uy, 0, 15.24)

    for p in (y1, y2, y3, y4, y5, y6, y7):
        o.append(no_connect(p))

    # Address via labels — stub column clear of ~E0/~E1 GND (those use pin_x-5.08)
    for pin, net in (
        (a0, "ADDR_A0"),
        (a1, "ADDR_A1"),
        (a2, "ADDR_A2"),
        (e2, "DEC_EN"),
    ):
        stub = (round(pin[0] - 15.24, 2), pin[1])
        o += [wire(pin, stub), label(net, stub, 180)]

    # ~E0, ~E1 → GND (short stubs; do not share X with address labels)
    for pin, sfx in ((e0, "E0"), (e1, "E1")):
        gx = round(pin[0] - 5.08, 2)
        gy = pin[1]
        o += [
            wire(pin, (gx, gy)),
            power("power:GND", f"#PWR_{uref}_{sfx}", "GND", gx, round(gy + 5.08, 2)),
            wire((gx, gy), (gx, round(gy + 5.08, 2))),
        ]

    # Y0 → decode net (stub must not sit on bypass column)
    yo = (round(y0[0] + 17.78, 2), y0[1])
    o += [wire(y0, yo), label(y0_net, yo)]

    # Power + bypass to the right of the Y0 stub
    vp = (vcc[0], round(vcc[1] - 5.08, 2))
    vm = (gnd[0], round(gnd[1] + 5.08, 2))
    o += [
        wire(vcc, vp),
        power("power:+3V3", f"#PWR_{pwr_suffix}_VCC", "+3V3", vp[0], round(vp[1] - 5.08, 2)),
        wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
        junction(vp),
        wire(gnd, vm),
        power("power:GND", f"#PWR_{pwr_suffix}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
        wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
        junction(vm),
    ]
    cx = round(ux + 30.48, 2)
    cy = round((vp[1] + vm[1]) / 2, 2)
    cref = f"C{19 + int(uref[1:]) - 11}"  # U11→C19 … U14→C22
    o.append(symbol_inst("Device:C", cref, "100n", cx, cy, ["1", "2"], footprint=FP_C))
    ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
    o += [
        wire(ct, (cx, vp[1])),
        wire((cx, vp[1]), vp),
        junction((cx, vp[1])),
        wire(cb, (cx, vm[1])),
        wire((cx, vm[1]), vm),
        junction((cx, vm[1])),
    ]


def buffer_125(
    o: list[str],
    *,
    uref: str,
    ox: float,
    oy: float,
    oe_net: str,
    channels: list[tuple[str, str]],
    pwr_suffix: str,
) -> None:
    """74AHC125 (74LS125): 4 gates + power. channels = [(in_net, out_net), …] len 4."""
    FP_U = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"

    # Gate units 1–4: OE, IN, OUT pin numbers
    gate_pins = [
        ("1", "2", "3"),
        ("4", "5", "6"),
        ("10", "9", "8"),
        ("13", "12", "11"),
    ]
    # Place gates in a row
    for ui, ((oe_p, in_p, out_p), (in_net, out_net)) in enumerate(zip(gate_pins, channels)):
        gx = round(ox + ui * 35.56, 2)
        gy = oy
        o.append(
            symbol_inst(
                "74xx:74LS125",
                uref,
                "74AHC125",
                gx,
                gy,
                [oe_p, in_p, out_p],
                unit=ui + 1,
                footprint=FP_U,
            )
        )
        # Lib: OE (0,-6.35), IN (-7.62,0), OUT (7.62,0) — units 3/4 swap OUT/IN side same coords
        oe = pin_xy(gx, gy, 0, -6.35)
        inp = pin_xy(gx, gy, -7.62, 0)
        outp = pin_xy(gx, gy, 7.62, 0)

        # OE → shared enable net
        o += [
            wire(oe, (oe[0], round(oe[1] + 7.62, 2))),
            label(oe_net, (oe[0], round(oe[1] + 7.62, 2))),
        ]
        # IN / OUT labels
        o += [
            wire(inp, (round(inp[0] - 7.62, 2), inp[1])),
            label(in_net, (round(inp[0] - 7.62, 2), inp[1]), 180),
            wire(outp, (round(outp[0] + 7.62, 2), outp[1])),
            label(out_net, (round(outp[0] + 7.62, 2), outp[1])),
        ]

    # Power unit 5
    px = round(ox + 4 * 35.56 + 10.16, 2)
    py = oy
    o.append(
        symbol_inst(
            "74xx:74LS125",
            uref,
            "74AHC125",
            px,
            py,
            ["7", "14"],
            unit=5,
            footprint=FP_U,
        )
    )
    gnd = pin_xy(px, py, 0, -12.7)
    vcc = pin_xy(px, py, 0, 12.7)
    vp = (vcc[0], round(vcc[1] - 5.08, 2))
    vm = (gnd[0], round(gnd[1] + 5.08, 2))
    o += [
        wire(vcc, vp),
        power("power:+3V3", f"#PWR_{pwr_suffix}_VCC", "+3V3", vp[0], round(vp[1] - 5.08, 2)),
        wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
        junction(vp),
        wire(gnd, vm),
        power("power:GND", f"#PWR_{pwr_suffix}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
        wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
        junction(vm),
    ]
    cx = round(px + 12.7, 2)
    cy = round((vp[1] + vm[1]) / 2, 2)
    cref = "C23" if uref == "U15" else "C24"
    o.append(symbol_inst("Device:C", cref, "100n", cx, cy, ["1", "2"], footprint=FP_C))
    ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
    o += [
        wire(ct, (cx, vp[1])),
        wire((cx, vp[1]), vp),
        junction((cx, vp[1])),
        wire(cb, (cx, vm[1])),
        wire((cx, vm[1]), vm),
        junction((cx, vm[1])),
    ]


def control_headers(o: list[str]) -> None:
    """ADDR_A[2:0] pull-down to 000; DEC_EN pull-down; FWD/REV_EN_n pull-up."""
    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"
    base_x, base_y = 245.0, 230.0

    # Conn_01x01 pin is on the left at lib (-5.08,0); place body left of net stub.
    def header_with_pulldown(jref: str, rref: str, net: str, x: float, y: float) -> None:
        nonlocal o
        o.append(symbol_inst("Connector:Conn_01x01", jref, net, x, y, ["1"], footprint=FP_J))
        jp = pin_xy(x, y, -5.08, 0, 0)
        junc = (round(jp[0] - 5.08, 2), y)
        o += [wire(jp, junc), junction(junc), label(net, (round(junc[0] - 5.08, 2), y), 180)]
        rx, ry = round(junc[0] - 12.7, 2), round(y + 12.7, 2)
        o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
        rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
        o += [
            wire(rt, (rx, junc[1])),
            wire((rx, junc[1]), junc),
            junction((rx, junc[1])),
            power("power:GND", f"#PWR_{rref}", "GND", rx, round(rb[1] + 7.62, 2)),
            wire(rb, (rx, round(rb[1] + 7.62, 2))),
        ]

    def header_with_pullup(jref: str, rref: str, net: str, x: float, y: float) -> None:
        nonlocal o
        o.append(symbol_inst("Connector:Conn_01x01", jref, net, x, y, ["1"], footprint=FP_J))
        jp = pin_xy(x, y, -5.08, 0, 0)
        junc = (round(jp[0] - 5.08, 2), y)
        o += [wire(jp, junc), junction(junc), label(net, (round(junc[0] - 5.08, 2), y), 180)]
        rx, ry = round(junc[0] - 12.7, 2), round(y - 12.7, 2)
        o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
        rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
        o += [
            wire(rb, (rx, junc[1])),
            wire((rx, junc[1]), junc),
            junction((rx, junc[1])),
            power("power:+3V3", f"#PWR_{rref}", "+3V3", rx, round(rt[1] - 7.62, 2)),
            wire(rt, (rx, round(rt[1] - 7.62, 2))),
        ]

    # Address: header + 10k to GND (default 000)
    for i, net in enumerate(("ADDR_A0", "ADDR_A1", "ADDR_A2")):
        header_with_pulldown(f"J{10 + i}", f"R{19 + i}", net, round(base_x + i * 25.4, 2), base_y)

    # DEC_EN: header + 10k to GND (disabled default)
    header_with_pulldown("J13", "R22", "DEC_EN", 245.0, 270.0)

    # FWD_EN_n / REV_EN_n: header + 10k to +3V3 (OE inactive = Hi-Z)
    header_with_pullup("J14", "R23", "FWD_EN_n", 245.0, 310.0)
    header_with_pullup("J15", "R24", "REV_EN_n", 290.0, 310.0)


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")
    sch = strip_stage8(sch)
    sch = ensure_lib(sch)

    o: list[str] = []
    control_headers(o)

    # Four decoders — Y0 only used (prototype 1×1)
    decoders = [
        ("U11", 380.0, 250.0, "DEC_XH0"),
        ("U12", 480.0, 250.0, "DEC_XL0"),
        ("U13", 580.0, 250.0, "DEC_YH0"),
        ("U14", 680.0, 250.0, "DEC_YL0"),
    ]
    for uref, ux, uy, y0 in decoders:
        decoder_138(o, uref=uref, ux=ux, uy=uy, y0_net=y0, pwr_suffix=uref)

    # FWD polarity buffers → Stage 4 *_n
    buffer_125(
        o,
        uref="U15",
        ox=360.0,
        oy=360.0,
        oe_net="FWD_EN_n",
        channels=[
            ("DEC_XH0", "X_HS0_n"),
            ("DEC_XL0", "X_LS0_n"),
            ("DEC_YH0", "Y_HS0_n"),
            ("DEC_YL0", "Y_LS0_n"),
        ],
        pwr_suffix="U15",
    )
    # REV polarity buffers → Stage 7 *r_n
    buffer_125(
        o,
        uref="U16",
        ox=360.0,
        oy=410.0,
        oe_net="REV_EN_n",
        channels=[
            ("DEC_XH0", "X_HS0r_n"),
            ("DEC_XL0", "X_LS0r_n"),
            ("DEC_YH0", "Y_HS0r_n"),
            ("DEC_YL0", "Y_LS0r_n"),
        ],
        pwr_suffix="U16",
    )

    o += [
        f'''\t(rectangle
\t\t(start 230.00 210.00)
\t\t(end 820.00 450.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("STAGE 8 — Address decode (1×1 / Y0 only)", 235.0, 215.0, 1.524),
        text(
            "74AHC138×4 → DEC_*0; 74AHC125×2 steer FWD_EN_n→*_n / REV_EN_n→*r_n; ADDR default 000; never assert both EN",
            235.0,
            445.0,
        ),
    ]

    sch = sch.replace("\t(sheet_instances", "\n".join(o) + "\n\t(sheet_instances", 1)
    SCH.write_text(sch)
    print(f"Appended Stage 8 decode to {SCH}")


if __name__ == "__main__":
    main()
