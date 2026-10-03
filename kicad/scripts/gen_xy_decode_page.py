#!/usr/bin/env python3
"""Build Decode Block page (one axis: 74AHC138 HS + 74AHC238 LS).

Hierarchical pins use N = axis (X/Y) and n = HS/LS bank index (0..7):

  ADDR_NH[2:0] / ADDR_NL[2:0]   address into HS / LS decoders
  BANK_EN / DEC_EN               ~E0 / E2
  N_HS{0..7}_n                   HS outs (active-low)
  N_LS{0..7}_en                  LS outs (active-high)

line# = 8·HS + LS (full X0–63 / Y0–63 when both axes are instanced).

Baby step: one root sheet "Decode Block" wired to X FWD
(ADDR_XH/XL, BANK_EN←FWD_EN_n, outs → X_HS*_n / X_LS*_en).
Named decode_fwd_yn / decode_rev_* instances come later.
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
DECODE_BLOCK = CORE / "decode_block.kicad_sch"
OLD_XY = CORE / "xy_decode.kicad_sch"
KICAD = Path("/usr/share/kicad/symbols")
PROJECT = "core"

ROOT_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
DRIVE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-111111111111"
DECODE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-333333333333"
OLD_DEC_REV_UUID = "a1b2c3d4-e5f6-4789-a012-444444444444"

SHEET_ORDER = [
    (ROOT_UUID, "core"),
    (DRIVE_BLOCK_UUID, "Drive Block"),
    (DECODE_BLOCK_UUID, "Decode Block"),
    ("a1b2c3d4-e5f6-4789-a012-555555555555", "Decoupling Logic"),
    ("a1b2c3d4-e5f6-4789-a012-666666666666", "Decoupling VDRIVE"),
    ("a1b2c3d4-e5f6-4789-a012-777777777777", "Sense"),
    ("a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb", "Ferrite Beads"),
    ("a1b2c3d4-e5f6-4789-a012-888888888888", "CCS"),
    ("a1b2c3d4-e5f6-4789-a012-999999999999", "Inhibit"),
    ("a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaaa", "Decode CTRL"),
]

DEC_PATH = f"/{ROOT_UUID}/{DECODE_BLOCK_UUID}"

FP_U = "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"
FP_C = "Capacitor_SMD:C_0805_2012Metric"

# Block hierarchical pin names
ADDR_NH = ("ADDR_NH0", "ADDR_NH1", "ADDR_NH2")
ADDR_NL = ("ADDR_NL0", "ADDR_NL1", "ADDR_NL2")
HS_OUTS = [f"N_HS{i}_n" for i in range(8)]
LS_OUTS = [f"N_LS{i}_en" for i in range(8)]
IN_PINS = list(ADDR_NH) + list(ADDR_NL) + ["BANK_EN", "DEC_EN"]
OUT_PINS = HS_OUTS + LS_OUTS

# Parent nets for X FWD bring-up
PARENT_NETS = {
    "ADDR_NH0": "ADDR_XH0",
    "ADDR_NH1": "ADDR_XH1",
    "ADDR_NH2": "ADDR_XH2",
    "ADDR_NL0": "ADDR_XL0",
    "ADDR_NL1": "ADDR_XL1",
    "ADDR_NL2": "ADDR_XL2",
    "BANK_EN": "FWD_EN_n",
    "DEC_EN": "DEC_EN",
}
for i in range(8):
    PARENT_NETS[f"N_HS{i}_n"] = f"X_HS{i}_n"
    PARENT_NETS[f"N_LS{i}_en"] = f"X_LS{i}_en"

SHEET_X = 400.0
SHEET_Y = 190.0
SHEET_W = 70.0
SHEET_PAGE = "3"
TITLE = "DECODE — Decode Block (N=axis, n=HS/LS bank); X FWD wired for 1×1 bring-up"
OLD_TITLES = (
    "DECODE — 12-bit ADDR",
    "DECODE — Decode Block",
    "xy_decode",
)


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


def extract_from_file(path: Path, name: str) -> str:
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


def instances(ref: str, unit: int = 1) -> str:
    return f'''\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "{DEC_PATH}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, *, rot=0, footprint=""):
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
{instances(ref)}
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
{prop("Value", value, f"{x} {y - 2.54} 0")}
{prop("Footprint", "", f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
\t\t(pin "1"
\t\t\t(uuid "{uid()}")
\t\t)
{instances(ref)}
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


def text(s, x, y, size=1.27):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def decoder_chip(
    o: list[str],
    *,
    uref: str,
    cref: str,
    ux: float,
    uy: float,
    addr_nets: tuple[str, str, str],
    out_names: list[str],
    out_shape: str,
    lib_id: str,
    value: str,
) -> None:
    """~E0←BANK_EN, ~E1←GND, E2←DEC_EN; Y0–Y7 → out_names[0..7]; local +3V3 100n."""
    assert len(out_names) == 8
    pins = [str(n) for n in range(1, 17)]
    o.append(symbol_inst(lib_id, uref, value, ux, uy, pins, footprint=FP_U))

    a0 = pin_xy(ux, uy, -10.16, 10.16)
    a1 = pin_xy(ux, uy, -10.16, 7.62)
    a2 = pin_xy(ux, uy, -10.16, 5.08)
    e0 = pin_xy(ux, uy, -10.16, -2.54)
    e1 = pin_xy(ux, uy, -10.16, -5.08)
    e2 = pin_xy(ux, uy, -10.16, -7.62)
    gnd = pin_xy(ux, uy, 0, -12.7)
    y_pins = [
        pin_xy(ux, uy, 10.16, 10.16),
        pin_xy(ux, uy, 10.16, 7.62),
        pin_xy(ux, uy, 10.16, 5.08),
        pin_xy(ux, uy, 10.16, 2.54),
        pin_xy(ux, uy, 10.16, 0),
        pin_xy(ux, uy, 10.16, -2.54),
        pin_xy(ux, uy, 10.16, -5.08),
        pin_xy(ux, uy, 10.16, -7.62),
    ]
    vcc = pin_xy(ux, uy, 0, 15.24)

    for pin, net in (
        (a0, addr_nets[0]),
        (a1, addr_nets[1]),
        (a2, addr_nets[2]),
        (e0, "BANK_EN"),
        (e2, "DEC_EN"),
    ):
        stub = (round(pin[0] - 12.7, 2), pin[1])
        o += [wire(pin, stub), label(net, stub, 180)]

    gx = round(e1[0] - 5.08, 2)
    gy = e1[1]
    o += [
        wire(e1, (gx, gy)),
        power("power:GND", f"#PWR_{uref}_E1", "GND", gx, round(gy + 5.08, 2)),
        wire((gx, gy), (gx, round(gy + 5.08, 2))),
    ]

    for yp, name in zip(y_pins, out_names):
        yo = (round(yp[0] + 12.7, 2), yp[1])
        o += [wire(yp, yo), hier(name, out_shape, yo)]

    vp = (vcc[0], round(vcc[1] - 5.08, 2))
    vm = (gnd[0], round(gnd[1] + 5.08, 2))
    o += [
        wire(vcc, vp),
        power("power:+3V3", f"#PWR_{uref}_VCC", "+3V3", vp[0], round(vp[1] - 5.08, 2)),
        wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
        junction(vp),
        wire(gnd, vm),
        power("power:GND", f"#PWR_{uref}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
        wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
        junction(vm),
    ]

    # Local +3V3 100n (travels with each Decode Block instance)
    cx = round(ux + 20.32, 2)
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


def build_decode_block_page(lib_syms: str) -> str:
    o: list[str] = [
        text("Decode Block — one axis 8×8 (line# = 8·HS + LS)", 20, 10, 1.524),
        text(
            "N=axis X/Y; n=HS/LS bank 0..7. Local +3V3 100n per decoder on this page.",
            20,
            16,
        ),
    ]

    for i, name in enumerate(IN_PINS):
        y = round(30.0 + i * 5.08, 2)
        hp = (20.0, y)
        lp = (round(hp[0] + 10.16, 2), y)
        o.append(hier(name, "input", hp, 180))
        o.append(wire(hp, lp))
        o.append(label(name, lp))

    decoder_chip(
        o,
        uref="U11",
        cref="C19",
        ux=130.0,
        uy=55.0,
        addr_nets=ADDR_NH,
        out_names=HS_OUTS,
        out_shape="output",
        lib_id="74xx:74HC138",
        value="74AHC138",
    )
    decoder_chip(
        o,
        uref="U12",
        cref="C20",
        ux=250.0,
        uy=55.0,
        addr_nets=ADDR_NL,
        out_names=LS_OUTS,
        out_shape="output",
        lib_id="74xx:74HC238",
        value="74AHC238",
    )

    body = "\n".join(o)
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{uid()}")
\t(paper "A3")
\t(title_block
\t\t(title "Decode Block")
\t\t(comment 1 "N=axis; n=HS/LS bank 0..7; local +3V3 100n per IC")
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


def is_decode_sheet(block: str) -> bool:
    return bool(
        re.search(
            r'\(property "Sheetfile" "(?:xy_decode|decode_block)\.kicad_sch"',
            block,
        )
    )


def sheet_height() -> float:
    pitch_in = 3.81
    pitch_out = 2.54
    return round(max(len(IN_PINS) * pitch_in, len(OUT_PINS) * pitch_out) + 8.0, 2)


def sheet_pin(name: str, shape: str, x: float, y: float, rot: int) -> str:
    just = "right" if rot == 0 else "left"
    return f'''\t\t(pin "{name}" {shape}
\t\t\t(at {x} {y} {rot})
\t\t\t(uuid "{uid()}")
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(justify {just})
\t\t\t)
\t\t)'''


def sheet_block() -> str:
    sx, sy = SHEET_X, SHEET_Y
    w, h = SHEET_W, sheet_height()
    pitch_in = 3.81
    pitch_out = 2.54
    pins = []
    for i, name in enumerate(IN_PINS):
        py = round(sy + 4.0 + i * pitch_in, 2)
        pins.append(sheet_pin(name, "input", sx, py, 180))
    for i, name in enumerate(OUT_PINS):
        py = round(sy + 4.0 + i * pitch_out, 2)
        pins.append(sheet_pin(name, "output", sx + w, py, 0))
    pins_s = "\n".join(pins)
    return f'''\t(sheet
\t\t(at {sx} {sy})
\t\t(size {w} {h})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0))
\t\t(uuid "{DECODE_BLOCK_UUID}")
\t\t(property "Sheetname" "Decode Block"
\t\t\t(at {sx} {round(sy - 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27) (thickness 0.254) (bold yes)) (justify left bottom))
\t\t)
\t\t(property "Sheetfile" "decode_block.kicad_sch"
\t\t\t(at {sx} {round(sy + h + 1.27, 2)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t)
{pins_s}
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "{SHEET_PAGE}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def sheet_stubs() -> list[str]:
    sx, sy = SHEET_X, SHEET_Y
    w = SHEET_W
    pitch_in = 3.81
    pitch_out = 2.54
    o: list[str] = []
    for i, name in enumerate(IN_PINS):
        py = round(sy + 4.0 + i * pitch_in, 2)
        outer = (round(sx - 12.7, 2), py)
        o += [wire((sx, py), outer), label(PARENT_NETS[name], outer, 180)]
    for i, name in enumerate(OUT_PINS):
        py = round(sy + 4.0 + i * pitch_out, 2)
        outer = (round(sx + w + 12.7, 2), py)
        o += [wire((sx + w, py), outer), label(PARENT_NETS[name], outer)]
    return o


def drop_spans(text: str, spans: list[tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]
    return text


def renumber_after_decode_collapse(sch: str, multi_decode: bool) -> str:
    """Collapse Decode FWD+REV (pages 3–4) to Decode Block (page 3); shift later pages −1."""
    if not multi_decode:
        return sch
    spans = []
    for start, end, block in extract_blocks(sch, "sheet"):
        if is_decode_sheet(block) or "drive_block.kicad_sch" in block:
            continue

        def repl(m: re.Match[str]) -> str:
            n = int(m.group(1))
            return f'(page "{n - 1}")' if n >= 5 else m.group(0)

        new = re.sub(r'\(page "(\d+)"\)', repl, block, count=1)
        if new != block:
            spans.append((start, end, new))
    for start, end, new in sorted(spans, key=lambda t: t[0], reverse=True):
        sch = sch[:start] + new + sch[end:]
    return sch


def retarget_root(sch: str) -> str:
    decode_pins: set[tuple[float, float]] = set()
    remove: list[tuple[int, int]] = []
    multi = False
    for start, end, block in extract_blocks(sch, "sheet"):
        if not is_decode_sheet(block):
            continue
        name_m = re.search(r'\(property "Sheetname" "([^"]+)"', block)
        if name_m and name_m.group(1) != "Decode Block":
            multi = True
        for xm, ym in re.findall(r'\(pin "[^"]+" [^\s]+\s+\(at ([0-9.-]+) ([0-9.-]+)', block):
            decode_pins.add((round(float(xm), 2), round(float(ym), 2)))
        remove.append((start, end))

    # Also count if two decode sheets present
    if len(remove) > 1:
        multi = True

    sch = renumber_after_decode_collapse(sch, multi)

    remove = []
    decode_pins = set()
    for start, end, block in extract_blocks(sch, "sheet"):
        if not is_decode_sheet(block):
            continue
        for xm, ym in re.findall(r'\(pin "[^"]+" [^\s]+\s+\(at ([0-9.-]+) ([0-9.-]+)', block):
            decode_pins.add((round(float(xm), 2), round(float(ym), 2)))
        remove.append((start, end))

    stub_outers: set[tuple[float, float]] = set()
    for start, end, block in extract_blocks(sch, "wire"):
        pts = [
            (round(float(a), 2), round(float(b), 2))
            for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", block)
        ]
        if len(pts) == 2 and (pts[0] in decode_pins or pts[1] in decode_pins):
            remove.append((start, end))
            for p in pts:
                if p not in decode_pins:
                    stub_outers.add(p)

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

    # Drop prior Y/REV CTRL no_connect terminators (re-added below)
    for start, end, block in extract_blocks(sch, "no_connect"):
        if "(at 80.16 " in block:
            remove.append((start, end))

    sch = drop_spans(sch, remove)
    chunks = [text(TITLE, 400, 185, 1.524), sheet_block(), *sheet_stubs()]
    # Decode CTRL still emits Y ADDR + REV_EN_n; terminate until Y/REV instances exist
    for net, y in (
        ("ADDR_YH0", 265.56),
        ("ADDR_YH1", 270.64),
        ("ADDR_YH2", 275.72),
        ("ADDR_YL0", 280.80),
        ("ADDR_YL1", 285.88),
        ("ADDR_YL2", 290.96),
        ("REV_EN_n", 306.20),
    ):
        # NC at the existing CTRL stub label x≈80.16
        chunks.append(
            f'''\t(no_connect
\t\t(at 80.16 {y})
\t\t(uuid "{uid()}")
\t)'''
        )
    marker = "\t(sheet_instances"
    if marker not in sch:
        marker = "(sheet_instances"
    if marker not in sch:
        raise SystemExit("sheet_instances missing")
    return sch.replace(marker, "\n".join(chunks) + "\n" + marker, 1)


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")

    lib_parts: list[str] = []
    if '(symbol "74xx:74HC138"' in sch:
        lib_parts.append(extract_lib(sch, "74xx:74HC138"))
    else:
        lib_parts.append(
            embed_as("74xx:74HC138", extract_from_file(KICAD / "74xx.kicad_sym", "74HC138"), "74HC138")
        )
    if '(symbol "74xx:74HC238"' in sch:
        lib_parts.append(extract_lib(sch, "74xx:74HC238"))
    else:
        lib_parts.append(
            embed_as("74xx:74HC238", extract_from_file(KICAD / "74xx.kicad_sym", "74HC238"), "74HC238")
        )
    for lid in ("Device:C", "power:+3V3", "power:GND"):
        lib_parts.append(extract_lib(sch, lid))

    DECODE_BLOCK.write_text(build_decode_block_page("\n".join(lib_parts)))
    print(f"Wrote {DECODE_BLOCK}")

    if '(symbol "74xx:74HC238"' not in sch:
        emb = embed_as(
            "74xx:74HC238", extract_from_file(KICAD / "74xx.kicad_sym", "74HC238"), "74HC238"
        )
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
        sch = sch[: i - 1] + emb + "\n\t" + sch[i - 1 :]
        print("Embedded 74xx:74HC238 into root lib_symbols")

    sch = retarget_root(sch)
    SCH.write_text(sch)
    print(f"Updated {SCH}")

    if OLD_XY.exists():
        OLD_XY.unlink()
        print(f"Removed {OLD_XY.name}")

    pro = json.loads(PRO.read_text())
    pro["sheets"] = [[u, n] for u, n in SHEET_ORDER]
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    print("Updated core.kicad_pro sheets")


if __name__ == "__main__":
    main()
