#!/usr/bin/env python3
"""Regenerate Decode block: FWD/REV 74AHC138 banks (no 74AHC125 mux).

Removes Decode by reference / bbox (elements are scattered in the .kicad_sch),
then appends a fresh contiguous Decode block before sheet_instances.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
KICAD = Path("/usr/share/kicad/symbols")
SHEET_UUID = "de7211a3-1219-4154-b2a8-36f4d2dfd28b"
PROJECT = "core"

# Decode placement bbox (generator + hand-moved titles nearby)
BBOX = (220.0, 195.0, 830.0, 460.0)

STAGE8_REFS = {
    *[f"U{n}" for n in range(11, 19)],
    *[f"J{n}" for n in range(10, 16)],
    *[f"R{n}" for n in range(19, 25)],
    *[f"C{n}" for n in range(19, 27)],
}
STAGE8_PWR_PREFIXES = tuple(
    f"#PWR_U{n}" for n in range(11, 19)
) + tuple(f"#PWR_R{n}" for n in range(19, 25)) + tuple(f"#PWR_C{n}" for n in range(19, 27))

STAGE8_CTRL_LABELS = {
    "DEC_XH0",
    "DEC_XL0",
    "DEC_YH0",
    "DEC_YL0",
    "ADDR_A0",
    "ADDR_A1",
    "ADDR_A2",
    "DEC_EN",
    "FWD_EN_n",
    "REV_EN_n",
}


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


def find_body_range(sch: str) -> tuple[int, int]:
    lib_start = sch.find("(lib_symbols")
    if lib_start < 0:
        raise SystemExit("lib_symbols missing")
    i = lib_start
    depth = 0
    started = False
    while i < len(sch):
        if sch[i] == "(":
            depth += 1
            started = True
        elif sch[i] == ")":
            depth -= 1
            if started and depth == 0:
                body_start = i + 1
                break
        i += 1
    else:
        raise SystemExit("lib_symbols unclosed")
    while body_start < len(sch) and sch[body_start] in "\n\r\t ":
        body_start += 1
    si = sch.find("(sheet_instances")
    if si < 0:
        raise SystemExit("sheet_instances missing")
    # include leading tab if present
    if si > 0 and sch[si - 1] == "\t":
        si -= 1
    return body_start, si


def extract_items(s: str, start: int, end: int) -> list[str]:
    items: list[str] = []
    i = start
    while i < end:
        while i < end and s[i] in "\n\r\t ":
            i += 1
        if i >= end:
            break
        if s[i] != "(":
            raise SystemExit(f"expected '(' at {i}: {s[i : i + 40]!r}")
        j = i
        depth = 0
        while j < end:
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        items.append(s[i:j])
        i = j
    return items


def in_bbox(x: float, y: float) -> bool:
    return BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3]


def item_coords(item: str) -> list[tuple[float, float]]:
    coords = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([0-9.]+) ([0-9.]+)\)", item)]
    coords += [(float(a), float(b)) for a, b in re.findall(r"\(at ([0-9.]+) ([0-9.]+)", item)]
    return coords


def is_stage8(item: str) -> bool:
    head = item.lstrip()
    if head.startswith("(symbol"):
        m = re.search(r'\(property "Reference" "([^"]+)"', item)
        if not m:
            return False
        ref = m.group(1)
        if ref in STAGE8_REFS:
            return True
        return any(ref.startswith(p) for p in STAGE8_PWR_PREFIXES)
    if head.startswith("(text"):
        return "DECODE" in item or "STAGE 8" in item or "74AHC138×4" in item or "74AHC125×2" in item
    if head.startswith("(rectangle"):
        return "230.00 210.00" in item or "(start 230 210)" in item
    if head.startswith("(label"):
        m = re.match(r'\s*\(label "([^"]+)"', item)
        if not m:
            return False
        name = m.group(1)
        coords = item_coords(item)
        if not coords:
            return False
        x, y = coords[0]
        if name in STAGE8_CTRL_LABELS:
            return True
        # Old mux outputs into *_n / *r_n lived in the Decode buffer band
        if name.endswith(("_n", "r_n")) and in_bbox(x, y) and y >= 280.0:
            return True
        return False
    if head.startswith(("(wire", "(junction", "(no_connect")):
        coords = item_coords(item)
        if not coords:
            return False
        return all(in_bbox(x, y) for x, y in coords)
    return False


def strip_stage8(sch: str) -> tuple[str, int]:
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)
    kept = [it for it in items if not is_stage8(it)]
    dropped = len(items) - len(kept)
    new_body = "\n".join(kept) + "\n"
    return sch[:body_start] + new_body + sch[si:], dropped


def ensure_lib(sch: str) -> str:
    needed = [
        ("74xx:74HC138", KICAD / "74xx.kicad_sym", "74HC138"),
    ]
    embeds = []
    for lib_id, path, src in needed:
        if f'(symbol "{lib_id}"' in sch:
            continue
        embeds.append(embed_as(lib_id, extract(path, src), src))
    if not embeds:
        return sch
    m = re.search(r"\(lib_symbols\n", sch)
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
    bank_en_n: str,
    pwr_suffix: str,
    cref: str,
) -> None:
    """~E0←bank_en_n, ~E1←GND, E2←DEC_EN; Y0→y0_net; Y1–Y7 NC."""
    FP_U = "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"

    pins = [str(n) for n in range(1, 17)]
    o.append(symbol_inst("74xx:74HC138", uref, "74AHC138", ux, uy, pins, footprint=FP_U))

    a0 = pin_xy(ux, uy, -10.16, 10.16)
    a1 = pin_xy(ux, uy, -10.16, 7.62)
    a2 = pin_xy(ux, uy, -10.16, 5.08)
    e0 = pin_xy(ux, uy, -10.16, -2.54)
    e1 = pin_xy(ux, uy, -10.16, -5.08)
    e2 = pin_xy(ux, uy, -10.16, -7.62)
    gnd = pin_xy(ux, uy, 0, -12.7)
    y7 = pin_xy(ux, uy, 10.16, -7.62)
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

    for pin, net in (
        (a0, "ADDR_A0"),
        (a1, "ADDR_A1"),
        (a2, "ADDR_A2"),
        (e0, bank_en_n),
        (e2, "DEC_EN"),
    ):
        stub = (round(pin[0] - 15.24, 2), pin[1])
        o += [wire(pin, stub), label(net, stub, 180)]

    gx = round(e1[0] - 5.08, 2)
    gy = e1[1]
    o += [
        wire(e1, (gx, gy)),
        power("power:GND", f"#PWR_{uref}_E1", "GND", gx, round(gy + 5.08, 2)),
        wire((gx, gy), (gx, round(gy + 5.08, 2))),
    ]

    yo = (round(y0[0] + 17.78, 2), y0[1])
    o += [wire(y0, yo), label(y0_net, yo)]

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
    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"
    base_x, base_y = 245.0, 230.0

    def header_with_pulldown(jref: str, rref: str, net: str, x: float, y: float) -> None:
        o.append(symbol_inst("Connector:Conn_01x01", jref, net, x, y, ["1"], footprint=FP_J))
        jp = pin_xy(x, y, -5.08, 0, 0)
        junc = (round(jp[0] - 5.08, 2), y)
        o.extend([wire(jp, junc), junction(junc), label(net, (round(junc[0] - 5.08, 2), y), 180)])
        rx, ry = round(junc[0] - 12.7, 2), round(y + 12.7, 2)
        o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
        rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
        o.extend(
            [
                wire(rt, (rx, junc[1])),
                wire((rx, junc[1]), junc),
                junction((rx, junc[1])),
                power("power:GND", f"#PWR_{rref}", "GND", rx, round(rb[1] + 7.62, 2)),
                wire(rb, (rx, round(rb[1] + 7.62, 2))),
            ]
        )

    def header_with_pullup(jref: str, rref: str, net: str, x: float, y: float) -> None:
        o.append(symbol_inst("Connector:Conn_01x01", jref, net, x, y, ["1"], footprint=FP_J))
        jp = pin_xy(x, y, -5.08, 0, 0)
        junc = (round(jp[0] - 5.08, 2), y)
        o.extend([wire(jp, junc), junction(junc), label(net, (round(junc[0] - 5.08, 2), y), 180)])
        rx, ry = round(junc[0] - 12.7, 2), round(y - 12.7, 2)
        o.append(symbol_inst("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
        rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
        o.extend(
            [
                wire(rb, (rx, junc[1])),
                wire((rx, junc[1]), junc),
                junction((rx, junc[1])),
                power("power:+3V3", f"#PWR_{rref}", "+3V3", rx, round(rt[1] - 7.62, 2)),
                wire(rt, (rx, round(rt[1] - 7.62, 2))),
            ]
        )

    for i, net in enumerate(("ADDR_A0", "ADDR_A1", "ADDR_A2")):
        header_with_pulldown(f"J{10 + i}", f"R{19 + i}", net, round(base_x + i * 25.4, 2), base_y)

    header_with_pulldown("J13", "R22", "DEC_EN", 245.0, 270.0)
    header_with_pullup("J14", "R23", "FWD_EN_n", 245.0, 310.0)
    header_with_pullup("J15", "R24", "REV_EN_n", 290.0, 310.0)


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")

    sch, dropped = strip_stage8(sch)
    print(f"Removed {dropped} Decode items")
    sch = ensure_lib(sch)

    o: list[str] = []
    control_headers(o)

    fwd = [
        ("U11", 380.0, 250.0, "X_HS0_n", "C19"),
        ("U12", 480.0, 250.0, "X_LS0_n", "C20"),
        ("U13", 580.0, 250.0, "Y_HS0_n", "C21"),
        ("U14", 680.0, 250.0, "Y_LS0_n", "C22"),
    ]
    for uref, ux, uy, y0, cref in fwd:
        decoder_138(
            o,
            uref=uref,
            ux=ux,
            uy=uy,
            y0_net=y0,
            bank_en_n="FWD_EN_n",
            pwr_suffix=uref,
            cref=cref,
        )

    rev = [
        ("U15", 380.0, 360.0, "X_HS0r_n", "C23"),
        ("U16", 480.0, 360.0, "X_LS0r_n", "C24"),
        ("U17", 580.0, 360.0, "Y_HS0r_n", "C25"),
        ("U18", 680.0, 360.0, "Y_LS0r_n", "C26"),
    ]
    for uref, ux, uy, y0, cref in rev:
        decoder_138(
            o,
            uref=uref,
            ux=ux,
            uy=uy,
            y0_net=y0,
            bank_en_n="REV_EN_n",
            pwr_suffix=uref,
            cref=cref,
        )

    o += [
        f'''\t(rectangle
\t\t(start 230.00 210.00)
\t\t(end 820.00 420.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("DECODE — FWD/REV 138 banks (1×1 / Y0)", 235.0, 215.0, 1.524),
        text(
            "DECODE: 74AHC138×4 FWD + ×4 REV; ~E0←FWD/REV_EN_n, ~E1←GND, E2←DEC_EN; ~Y0→*_n/*r_n; never assert both EN",
            235.0,
            415.0,
        ),
    ]

    # Insert before sheet_instances
    marker = "\t(sheet_instances"
    if marker not in sch:
        marker = "(sheet_instances"
    sch = sch.replace(marker, "\n".join(o) + "\n" + marker, 1)
    SCH.write_text(sch)
    print(f"Appended Decode bank-enable block to {SCH}")


if __name__ == "__main__":
    main()
