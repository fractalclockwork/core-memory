#!/usr/bin/env python3
"""Place MCE cores on magnetic_core_2x2.kicad_sch; build a 2×2 grid.

Phase 1: strip FB1/FB2 + soft mid from sense; recreate bowtie topology on
         magnetic_core_2x2; rewire root Sense pins; add Magnetic Cores sheet.
Phase 2: replace bowtie with physically oriented 2×2 (XA→XB top→bottom,
         YA→YB right→left). Sense: YA loop is the TL–BR diagonal (MCE00 and
         MCE11 mirrored), YB loop is the BL–TR diagonal; both loop ends leave
         at the XB end of that Y edge. Center tap YA66=YB65 after two cores.

Usage:
  uv run python kicad/scripts/gen_ferrite_beads_page.py --phase 1
  uv run python kicad/scripts/gen_ferrite_beads_page.py --phase 2
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
SCH = CORE / "core.kicad_sch"
PRO = CORE / "core.kicad_pro"
SENSE = CORE / "sense.kicad_sch"
BEADS = CORE / "magnetic_core_2x2.kicad_sch"
SYM_LIB = ROOT / "libs" / "core_memory.kicad_sym"
PROJECT = "core"

ROOT_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
SENSE_UUID = "a1b2c3d4-e5f6-4789-a012-777777777777"
CCS_UUID = "a1b2c3d4-e5f6-4789-a012-888888888888"
INH_UUID = "a1b2c3d4-e5f6-4789-a012-999999999999"
DEC_CTRL_UUID = "a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaaa"
BEADS_UUID = "a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb"
DRIVE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-111111111111"
DECODE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-333333333333"
LOGIC_UUID = "a1b2c3d4-e5f6-4789-a012-555555555555"
VDRIVE_UUID = "a1b2c3d4-e5f6-4789-a012-666666666666"

SHEET_ORDER = [
    (ROOT_UUID, "core"),
    (DRIVE_BLOCK_UUID, "X0 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111111112", "X1 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111111113", "X0 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111111114", "X1 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111111115", "Y0 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111111116", "Y1 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111111117", "Y0 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111111118", "Y1 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110120", "X2 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110121", "X2 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110122", "Y2 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110123", "Y2 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110124", "X3 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110125", "X3 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110126", "Y3 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110127", "Y3 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110128", "X4 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110129", "X4 REV"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012a", "Y4 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012b", "Y4 REV"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012c", "X5 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012d", "X5 REV"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012e", "Y5 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-11111111012f", "Y5 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110130", "X6 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110131", "X6 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110132", "Y6 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110133", "Y6 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110134", "X7 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110135", "X7 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111110136", "Y7 FWD"),
    ("a1b2c3d4-e5f6-4789-a012-111111110137", "Y7 REV"),
    ("a1b2c3d4-e5f6-4789-a012-111111111119", "Steer 2x2"),
    (DECODE_BLOCK_UUID, "X FWD"),
    ("a1b2c3d4-e5f6-4789-a012-333333333334", "Y FWD"),
    ("a1b2c3d4-e5f6-4789-a012-333333333335", "X REV"),
    ("a1b2c3d4-e5f6-4789-a012-333333333336", "Y REV"),
    (LOGIC_UUID, "Decoupling Logic"),
    (VDRIVE_UUID, "Decoupling VDRIVE"),
    (SENSE_UUID, "Sense"),
    (BEADS_UUID, "Magnetic Cores"),
    (CCS_UUID, "CCS X"),
    ("a1b2c3d4-e5f6-4789-a012-888888888889", "CCS Y"),
    ("a1b2c3d4-e5f6-4789-a012-88888888888a", "CCS INH"),
    (INH_UUID, "Inhibit"),
    (DEC_CTRL_UUID, "Decode CTRL"),
    ("a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaab", "Decode CTRL Y"),
]

BEAD_REFS = {"FB1", "FB2", "R1", "R2", "#PWR_AGND", "#FLG_AGND"}
PLANE_HIER = {"XA0", "XB0", "YA0", "YB0"}
FP_R = "Resistor_SMD:R_0805_2012Metric"
MCE_SPICE = [
    ("Sim.Device", "SUBCKT"),
    ("Sim.Name", "mce"),
    ("Sim.Library", "../core_element_sim/models/coremem.cir"),
    ("Sim.Pins", "1=X1 2=X2 3=Y1 4=Y2 5=S1 6=S2"),
]


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
        # fall back to project symbol lib for CoreBead
        if lib_id.startswith("core_memory:"):
            name = lib_id.split(":", 1)[1]
            text = SYM_LIB.read_text()
            needle = f'(symbol "{name}"'
            start = text.find(needle)
            if start < 0:
                raise KeyError(lib_id)
            start = text.rfind("\n", 0, start) + 1
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        body = text[start : i + 1]
                        body = body.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
                        return "\n".join("\t\t" + ln if ln else ln for ln in body.splitlines())
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


def find_body_range(sch: str) -> tuple[int, int]:
    m = re.search(r"\(lib_symbols\n", sch)
    if not m:
        raise SystemExit("lib_symbols missing")
    i = m.end()
    depth = 1
    while i < len(sch) and depth:
        if sch[i] == "(":
            depth += 1
        elif sch[i] == ")":
            depth -= 1
        i += 1
    body_start = i
    while body_start < len(sch) and sch[body_start] in "\n\t ":
        body_start += 1
    si = sch.find("\t(sheet_instances")
    if si < 0:
        si = sch.find("(sheet_instances")
    if si < 0:
        raise SystemExit("sheet_instances missing")
    return body_start, si


def extract_items(sch: str, body_start: int, si: int) -> list[str]:
    body = sch[body_start:si]
    items: list[str] = []
    i = 0
    while i < len(body):
        if body[i] != "(":
            i += 1
            continue
        start = i
        depth = 0
        for j in range(i, len(body)):
            if body[j] == "(":
                depth += 1
            elif body[j] == ")":
                depth -= 1
                if depth == 0:
                    items.append(body[start : j + 1])
                    i = j + 1
                    break
        else:
            break
    return items


def symbol_ref(item: str) -> str | None:
    m = re.search(r'\(property "Reference" "([^"]+)"', item)
    return m.group(1) if m else None


def prop(name: str, value: str, at: str, hide: bool = False) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    return f'''\t\t(property "{name}" "{value}"
\t\t\t(at {at}){hide_s}
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)'''


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
    just = "right" if rot == 180 else "left"
    return f'''\t(label "{name}"
\t\t(at {p[0]} {p[1]} {rot})
\t\t(effects (font (size 1.27 1.27)) (justify {just}))
\t\t(uuid "{uid()}")
\t)'''


def hier(name, shape, p, rot=0):
    just = "right" if rot == 180 else "left"
    return f'''\t(hierarchical_label "{name}"
\t\t(shape {shape})
\t\t(at {p[0]} {p[1]} {rot})
\t\t(effects (font (size 1.27 1.27)) (justify {just}))
\t\t(uuid "{uid()}")
\t)'''


def text(s, x, y, size=1.27):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def no_connect(p):
    return f'''\t(no_connect
\t\t(at {p[0]} {p[1]})
\t\t(uuid "{uid()}")
\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, *, unit=1, rot=0, dnp=False, footprint="", sheet_uuid=BEADS_UUID, mirror_y=False, bom=None, on_board=True, extra=None):
    pins_s = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
    mirror_s = "\n\t\t(mirror y)" if mirror_y else ""
    if bom is None:
        bom = not dnp
    extra_s = ""
    if extra:
        extra_s = "\n" + "\n".join(prop(n, v, f"{x} {y} 0", hide=True) for n, v in extra)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit {unit})
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {"yes" if bom else "no"})
\t\t(on_board {"yes" if on_board else "no"})
\t\t(in_pos_files {"yes" if on_board else "no"})
\t\t(dnp {"yes" if dnp else "no"})
\t\t(uuid "{uid()}"){mirror_s}
{prop("Reference", ref, f"{x + 2.54} {y - 12.7} 0")}
{prop("Value", value, f"{x + 2.54} {y - 10.16} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}{extra_s}
{pins_s}
\t\t(instances (project "{PROJECT}" (path "/{ROOT_UUID}/{sheet_uuid}" (reference "{ref}") (unit {unit}))))
\t)'''


def power(lib_id, ref, value, x, y, sheet_uuid=BEADS_UUID):
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
\t\t(instances (project "{PROJECT}" (path "/{ROOT_UUID}/{sheet_uuid}" (reference "{ref}") (unit 1))))
\t)'''


def page_header(title: str, comment: str, page_uuid: str, libs: str) -> str:
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{page_uuid}")
\t(paper "A3")
\t(title_block
\t\t(title "{title}")
\t\t(comment 1 "{comment}")
\t)
\t(lib_symbols
{libs}
\t)
'''


def page_footer(page_uuid: str) -> str:
    return f'''\t(sheet_instances
\t\t(path "/{ROOT_UUID}/{page_uuid}"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def y_edge(pins: dict[str, tuple[float, float]], mirrored: bool, side: str) -> tuple[float, float]:
    """Y pin on the left or right side of the symbol.

    Unmirrored, Y1 is left and Y2 is right. mirror_y swaps those sides.
    Callers attach YA to the right pin and YB to the left pin.
    """
    if side == "right":
        return pins["y1"] if mirrored else pins["y2"]
    if side == "left":
        return pins["y2"] if mirrored else pins["y1"]
    raise ValueError(side)


def mce_spice(*, y_swap: bool) -> list[tuple[str, str]]:
    """SPICE pin map so XA→XB and YA→YB both add +H, and YA65→YB66 is −Is.

    The subcircuit treats pin1→pin2 as +H. A mirrored core already has its
    right-hand Y pin as Y1, so YA→YB is +H. An unmirrored core needs Y1/Y2
    swapped. Every core in this weave is entered at symbol S1; mapping that
    pin to subckt S2 makes the documented inhibit direction oppose a +H write.
    """
    y_pins = "3=Y2 4=Y1" if y_swap else "3=Y1 4=Y2"
    return [
        ("Sim.Device", "SUBCKT"),
        ("Sim.Name", "mce"),
        ("Sim.Library", "../core_element_sim/models/coremem.cir"),
        ("Sim.Pins", f"1=X1 2=X2 {y_pins} 5=S2 6=S1"),
    ]


def bead_pins(sx: float, sy: float, *, mirror_y: bool = False) -> dict[str, tuple[float, float]]:
    """Pin positions for MCE: X top/bot, Y L/R, S on LL→UR diagonal.

    mirror_y flips about the Y axis (left↔right): S diagonal becomes LR↔UL.
    """
    locs = {
        "x1": (0.0, 7.62),
        "x2": (0.0, -7.62),
        "y1": (-7.62, 0.0),
        "y2": (7.62, 0.0),
        "s1": (-7.62, -5.08),
        "s2": (7.62, 5.08),
    }
    out = {}
    for name, (lx, ly) in locs.items():
        if mirror_y:
            lx = -lx
        out[name] = pin_xy(sx, sy, lx, ly)
    return out


def libs_block(sch_src: str, lib_ids: list[str]) -> str:
    out = []
    for lid in lib_ids:
        # Always take project symbols from the lib so pin geometry stays current.
        if lid.startswith("core_memory:"):
            out.append(extract_lib("", lid))
        elif f'(symbol "{lid}"' in sch_src:
            out.append(extract_lib(sch_src, lid))
        else:
            out.append(extract_lib("", lid))
    return "\n".join(out)


# ----- phase 1 bowtie page -----


def build_bowtie_page(sch_src: str) -> str:
    libs = libs_block(sch_src, [
        "core_memory:MCE",
        "Device:R",
        "power:GND",
        "power:PWR_FLAG",
    ])
    o: list[str] = []
    ax, ay = 100.0, 60.0
    bx, by = 150.8, 60.0
    o += [
        text("MAGNETIC CORES — bowtie (phase 1)\\nX/Y/Sense series both cores — corrected in phase 2", 20, 20, 1.524),
        symbol_inst("core_memory:MCE", "MCE1", "MCE", ax, ay, list("123456"), footprint="", bom=False, on_board=False, extra=MCE_SPICE),
        symbol_inst("core_memory:MCE", "MCE2", "MCE", bx, by, list("123456"), footprint="", bom=False, on_board=False, extra=MCE_SPICE),
    ]
    a, b = bead_pins(ax, ay), bead_pins(bx, by)
    o += [wire(a["x2"], b["x1"]), wire(a["y2"], b["y1"])]
    mid = (round((a["s2"][0] + b["s1"][0]) / 2, 2), a["s2"][1])
    # Center tap is YA66═YB65 (SENSE_FOLD), not an on-plane YA65 shunt.
    o += [
        wire(a["s2"], mid),
        wire(mid, b["s1"]),
        junction(mid),
        label("SENSE_FOLD", mid),
        label("YA66", (round(mid[0] + 2.54, 2), mid[1])),
        label("YB65", (round(mid[0] + 5.08, 2), mid[1])),
    ]

    r1 = (mid[0], mid[1] + 20.32)
    o.append(symbol_inst("Device:R", "R1", "10k", r1[0], r1[1], ["1", "2"], footprint=FP_R))
    r1t, r1b = pin_xy(r1[0], r1[1], 0, 3.81), pin_xy(r1[0], r1[1], 0, -3.81)
    o += [wire(mid, r1t), wire(r1b, (r1b[0], r1b[1] + 5.08))]
    ag = (r1b[0], r1b[1] + 5.08)
    o += [power("power:GND", "#PWR_AGND", "AGND", ag[0], ag[1])]
    flg = (ag[0], ag[1] + 10.16)
    o += [wire(ag, flg), power("power:PWR_FLAG", "#FLG_AGND", "PWR_FLAG", flg[0], flg[1])]

    for name, pin, rot, dx in [
        ("XA0", a["x1"], 180, -7.62), ("YA0", a["y1"], 180, -7.62), ("YA65", a["s1"], 180, -7.62),
        ("XB0", b["x2"], 0, 7.62), ("YB0", b["y2"], 0, 7.62), ("YB66", b["s2"], 0, 7.62),
    ]:
        end = (round(pin[0] + dx, 2), pin[1])
        o += [wire(pin, end), hier(name, "passive", end, rot)]

    r2 = (mid[0], mid[1] + 35.56)
    o.append(symbol_inst("Device:R", "R2", "DNP", r2[0], r2[1], ["1", "2"], rot=90, dnp=True, footprint=FP_R))
    r2l, r2r = pin_xy(r2[0], r2[1], 0, 3.81, 90), pin_xy(r2[0], r2[1], 0, -3.81, 90)
    o += [
        wire(r2l, (round(r2l[0] - 5.08, 2), r2l[1])),
        label("YA65", (round(r2l[0] - 5.08, 2), r2l[1]), 180),
        wire(r2r, (round(r2r[0] + 5.08, 2), r2r[1])),
        label("YB66", (round(r2r[0] + 5.08, 2), r2r[1]), 0),
    ]

    return page_header(
        "Magnetic Cores",
        "Bowtie MCE1/MCE2 (phase 1)",
        BEADS_UUID,
        libs,
    ) + "\n".join(o) + "\n" + page_footer(BEADS_UUID)


# ----- phase 2 2x2 page -----


def build_grid_page(sch_src: str) -> str:
    libs = libs_block(sch_src, [
        "core_memory:MCE",
        "Device:R",
        "power:GND",
        "power:PWR_FLAG",
    ])
    o: list[str] = [
        text(
            "MAGNETIC CORES — 2×2 MCE\\n"
            "XA→XB top→bottom; YA→YB right→left\\n"
            "YA loop TL–BR (MCE00/MCE11 mirrored): YA65–MCE11–MCE00–YA66 at YA–XB\\n"
            "YB loop BL–TR: YB65–MCE10–MCE01–YB66 at YB–XB; center tap YA66=YB65",
            20, 12, 1.524,
        ),
    ]

    # Grid centers (row-major screen coords; Y down)
    gap_x, gap_y = 60.96, 50.8
    c0x, c0y = 100.0, 55.0
    positions = {
        "MCE00": (c0x, c0y),
        "MCE01": (c0x + gap_x, c0y),
        "MCE10": (c0x, c0y + gap_y),
        "MCE11": (c0x + gap_x, c0y + gap_y),
    }
    # Photo: the TL–BR sense pass (\\) is the YA loop, so those cores are
    # mirrored (S on UL–LR). The return pass (/) is the YB loop, unmirrored.
    mirror = {"MCE00": True, "MCE01": False, "MCE10": False, "MCE11": True}
    pins = {}
    for ref, (sx, sy) in positions.items():
        my = mirror[ref]
        o.append(symbol_inst(
            "core_memory:MCE", ref, "MCE", sx, sy, list("123456"),
            footprint="", mirror_y=my, bom=False, on_board=False,
            extra=mce_spice(y_swap=not my),
        ))
        pins[ref] = bead_pins(sx, sy, mirror_y=my)

    p00, p01, p10, p11 = pins["MCE00"], pins["MCE01"], pins["MCE10"], pins["MCE11"]

    def chain(pts: list[tuple[float, float]]) -> list[str]:
        return [wire(a, b) for a, b in zip(pts, pts[1:])]

    # --- X columns (top → bottom via X1/X2; mirror does not move X) ---
    # XA0 → MCE00.X1 → MCE00.X2 → MCE10.X1 → MCE10.X2 → XB0
    o += stub_hier_v("XA0", p00["x1"], dy=-10.16)
    o += [wire(p00["x2"], p10["x1"])]
    o += stub_hier_v("XB0", p10["x2"], dy=10.16)

    # XA1 → MCE01.X1 → MCE01.X2 → MCE11.X1 → MCE11.X2 → XB1
    o += stub_hier_v("XA1", p01["x1"], dy=-10.16)
    o += [wire(p01["x2"], p11["x1"])]
    o += stub_hier_v("XB1", p11["x2"], dy=10.16)

    # --- Y rows (right → left). YA on the right-hand pin, YB on the left. ---
    o += stub_hier("YA0", y_edge(p01, mirror["MCE01"], "right"), rot=0, dx=10.16)
    o += [wire(y_edge(p01, mirror["MCE01"], "left"), y_edge(p00, mirror["MCE00"], "right"))]
    o += stub_hier("YB0", y_edge(p00, mirror["MCE00"], "left"), rot=180, dx=-10.16)

    o += stub_hier("YA1", y_edge(p11, mirror["MCE11"], "right"), rot=0, dx=10.16)
    o += [wire(y_edge(p11, mirror["MCE11"], "left"), y_edge(p10, mirror["MCE10"], "right"))]
    o += stub_hier("YB1", y_edge(p10, mirror["MCE10"], "left"), rot=180, dx=-10.16)

    # --- Sense diagonals. Both ends of a loop sit at the XB end of its Y edge. ---
    # YA (mirrored, \\): YA65 → MCE11.S1 → MCE11.S2 → MCE00.S1 → MCE00.S2 → YA66
    # YB (unmirrored, /): YB65 → MCE10.S1 → MCE10.S2 → MCE01.S1 → MCE01.S2 → YB66
    # YA66 and YB65 meet at SENSE_FOLD (driver jumper, 10k to AGND).
    o += stub_hier("YA65", p11["s1"], rot=0, dx=12.7)
    o += [wire(p11["s2"], p00["s1"])]
    o += [wire(p10["s2"], p01["s1"])]

    # Loop-A return and the fold run under the array, between the two XB corners.
    left_x = round(p10["s1"][0] - 20.32, 2)
    bus_y = round(p10["x2"][1] + 22.86, 2)
    fold = (round((positions["MCE00"][0] + positions["MCE01"][0]) / 2, 2), bus_y)
    ya66 = (round(p11["s1"][0] + 16.0, 2), bus_y)
    yb_tee = (left_x, p10["s1"][1])
    o += chain([
        p00["s2"],
        (left_x, p00["s2"][1]),
        yb_tee,
        (left_x, bus_y),
        fold,
        ya66,
    ])
    o += chain([p10["s1"], yb_tee])
    o += [
        junction((left_x, bus_y)),
        junction(fold),
        junction(yb_tee),
        label("YA66", ya66, 0),
        label("SENSE_FOLD", (fold[0] + 2.54, fold[1])),
        label("YB65", yb_tee, 180),
    ]

    # Loop-B return comes back over the top to the YB–XB corner.
    top_y = round(p01["x1"][1] - 16.0, 2)
    yb66 = (round(left_x - 8.0, 2), round(p10["s1"][1] + 6.0, 2))
    o += chain([
        p01["s2"],
        (p01["s2"][0], top_y),
        (yb66[0], top_y),
        yb66,
    ])
    o += [hier("YB66", "passive", yb66, 180)]

    # Soft mid R1 on the fold.
    r1 = (fold[0], round(bus_y + 20.32, 2))
    o.append(symbol_inst("Device:R", "R1", "10k", r1[0], r1[1], ["1", "2"], footprint=FP_R))
    r1t, r1b = pin_xy(r1[0], r1[1], 0, 3.81), pin_xy(r1[0], r1[1], 0, -3.81)
    o += [wire(fold, r1t)]
    ag = (r1b[0], round(r1b[1] + 5.08, 2))
    o += [wire(r1b, ag), power("power:GND", "#PWR_AGND", "AGND", ag[0], ag[1])]
    flg = (ag[0], round(ag[1] + 10.16, 2))
    o += [wire(ag, flg), power("power:PWR_FLAG", "#FLG_AGND", "PWR_FLAG", flg[0], flg[1])]

    # R2 DNP across outer ends YA65/YB66
    r2 = (round(ya66[0] + 25.4, 2), round((p11["s1"][1] + bus_y) / 2, 2))
    o.append(symbol_inst("Device:R", "R2", "DNP", r2[0], r2[1], ["1", "2"], rot=90, dnp=True, footprint=FP_R))
    r2l, r2r = pin_xy(r2[0], r2[1], 0, 3.81, 90), pin_xy(r2[0], r2[1], 0, -3.81, 90)
    o += [
        wire(r2l, (round(r2l[0] - 5.08, 2), r2l[1])),
        label("YA65", (round(r2l[0] - 5.08, 2), r2l[1]), 180),
        wire(r2r, (round(r2r[0] + 5.08, 2), r2r[1])),
        label("YB66", (round(r2r[0] + 5.08, 2), r2r[1]), 0),
    ]

    return page_header(
        "Magnetic Cores",
        "2x2 MCE; YA loop mirrored TL-BR; YB loop BL-TR; 65/66 at XB end",
        BEADS_UUID,
        libs,
    ) + "\n".join(o) + "\n" + page_footer(BEADS_UUID)


def stub_hier(name: str, pin: tuple[float, float], *, rot: int, dx: float) -> list[str]:
    end = (round(pin[0] + dx, 2), pin[1])
    return [wire(pin, end), hier(name, "passive", end, rot)]


def stub_hier_v(name: str, pin: tuple[float, float], *, dy: float) -> list[str]:
    """Vertical stub: dy < 0 goes up (label above), dy > 0 goes down."""
    end = (pin[0], round(pin[1] + dy, 2))
    rot = 90 if dy < 0 else 270
    return [wire(pin, end), hier(name, "passive", end, rot)]


# ----- strip beads from sense -----


def item_coords(item: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", item)] + [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"\(at ([0-9.-]+) ([0-9.-]+)", item)
    ]


def is_bead_connectivity(item: str) -> bool:
    """Wires/junctions/no_connects that belong to the bowtie stand-in."""
    head = item.lstrip()
    if not head.startswith(("(wire", "(junction", "(no_connect")):
        return False
    coords = item_coords(item)
    if not coords:
        return False

    def in_core(x, y):
        return 88.0 <= x <= 165.0 and 25.0 <= y <= 72.0

    def is_fb_stub(x, y):
        # left stubs FB1→hier and right stubs FB2→hier/labels
        if abs(x - 81.28) < 0.2 and y in (27.79, 32.87, 37.95):
            return True
        if abs(x - 88.9) < 0.2 and y in (27.79, 32.87, 37.95):
            return True
        if abs(x - 154.94) < 0.2 and y in (27.79, 32.87, 37.95):
            return True
        if abs(x - 162.56) < 0.2 and y in (27.79, 32.87, 37.95):
            return True
        return False

    # Keep R4↔YB66 hier: (76.2, 63.5)-(81.28, 63.5)
    if all(abs(y - 63.5) < 0.2 for _, y in coords) and all(75.0 <= x <= 82.0 for x, _ in coords):
        return False

    if all(in_core(x, y) for x, y in coords):
        return True
    if all(is_fb_stub(x, y) or in_core(x, y) for x, y in coords) and any(is_fb_stub(x, y) for x, y in coords):
        return True
    return False


def strip_beads_from_sense() -> None:
    sch = SENSE.read_text()
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)
    keep: list[str] = []
    for it in items:
        head = it.lstrip()
        if head.startswith("(symbol"):
            ref = symbol_ref(it)
            if ref in BEAD_REFS:
                continue
            keep.append(it)
            continue
        if head.startswith("(hierarchical_label"):
            m = re.match(r'\s*\(hierarchical_label "([^"]+)"', it)
            if m and m.group(1) in PLANE_HIER:
                continue
            keep.append(it)
            continue
        if head.startswith("(label"):
            m = re.match(r'\s*\(label "([^"]+)"', it)
            # Drop legacy / fold mid labels if left on Sense after bead move.
            if m and m.group(1) in ("YA65_66", "SENSE_FOLD"):
                continue
            # bead-side YB66 stub only
            if m and m.group(1) == "YB66":
                coords = item_coords(it)
                if coords and abs(coords[0][0] - 162.56) < 0.5:
                    continue
            keep.append(it)
            continue
        if head.startswith("(text"):
            it2 = it.replace("Bowtie / split-sense + amp", "Sense amp / latch")
            it2 = it2.replace("SENSE — Bowtie / latch", "SENSE — amp / latch")
            keep.append(it2)
            continue
        if is_bead_connectivity(it):
            continue
        keep.append(it)

    # Drop CoreBead from lib_symbols
    lib_start = sch.find("\t(lib_symbols\n")
    if lib_start < 0:
        lib_start = sch.find("(lib_symbols\n")
    # find end of lib_symbols already in body_start
    lib_body = sch[lib_start:body_start]
    if '(symbol "core_memory:CoreBead_3W"' in lib_body:
        start = lib_body.find('(symbol "core_memory:CoreBead_3W"')
        start = lib_body.rfind("\n", 0, start) + 1
        depth = 0
        end = start
        for i in range(start, len(lib_body)):
            if lib_body[i] == "(":
                depth += 1
            elif lib_body[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        lib_body = lib_body[:start] + lib_body[end:]
        while "\n\n\n" in lib_body:
            lib_body = lib_body.replace("\n\n\n", "\n\n")

    # Update title comment
    header = sch[:lib_start]
    header = header.replace(
        "Bowtie / TLV3501 / 74AHC74 latch",
        "TLV3501 / 74AHC74 latch (beads on ferrite_beads)",
    )

    new_sch = header + lib_body + "\n".join(keep) + "\n" + sch[si:]
    SENSE.write_text(new_sch)
    print(f"Stripped beads from {SENSE.name} ({len(items)} → {len(keep)} items)")


# ----- root sheet wiring -----


def sheet_box(name, file, sheet_uuid, page, sx, sy, pins, *, w=55.0, h=None):
    if h is None:
        h = max(25.0, 8.0 + 5.08 * max(1, len(pins)))
    pins_s = ""
    left = [p for p in pins if p[2] == "left"]
    right = [p for p in pins if p[2] == "right"]
    for i, (pname, shape, side) in enumerate(left):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = sx
        rot = 180
        just = "left"
        pins_s += f'''\t\t(pin "{pname}" {shape}
\t\t\t(at {px} {py} {rot})
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify {just}))
\t\t)
'''
    for i, (pname, shape, side) in enumerate(right):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = round(sx + w, 2)
        rot = 0
        just = "right"
        pins_s += f'''\t\t(pin "{pname}" {shape}
\t\t\t(at {px} {py} {rot})
\t\t\t(uuid "{uid()}")
\t\t\t(effects (font (size 1.27 1.27)) (justify {just}))
\t\t)
'''
    return f'''\t(sheet
\t\t(at {sx} {sy})
\t\t(size {w} {h})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0))
\t\t(uuid "{sheet_uuid}")
\t\t(property "Sheetname" "{name}"
\t\t\t(at {sx} {sy - 1.27} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27) (thickness 0.254) (bold yes)) (justify left bottom))
\t\t)
\t\t(property "Sheetfile" "{file}"
\t\t\t(at {sx} {sy + h + 1.27} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t)
{pins_s}\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def stub_pins(sx: float, sy: float, pins_left: list[str], pins_right: list[str], *, w: float = 55.0) -> list[str]:
    o: list[str] = []
    for i, name in enumerate(pins_left):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = sx
        o += [
            wire((round(px - 10.16, 2), py), (px, py)),
            label(name, (round(px - 10.16, 2), py), 180),
        ]
    for i, name in enumerate(pins_right):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = round(sx + w, 2)
        o += [
            wire((px, py), (round(px + 10.16, 2), py)),
            label(name, (round(px + 10.16, 2), py)),
        ]
    return o


def strip_sheet_and_stubs(sch: str, sheet_files: set[str], pin_nets_near: set[tuple[str, float, float]] | None = None) -> str:
    """Remove sheet boxes for given files and nearby stub wires/labels for those sheets."""
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)
    drop_rects: list[tuple[float, float, float, float]] = []
    keep: list[str] = []
    for it in items:
        if it.lstrip().startswith("(sheet"):
            if any(f'Sheetfile" "{f}"' in it or f'Sheetfile" {f}' in it for f in sheet_files):
                m = re.search(r"\(at ([0-9.-]+) ([0-9.-]+)\)", it)
                sm = re.search(r"\(size ([0-9.-]+) ([0-9.-]+)\)", it)
                if m and sm:
                    sx, sy = float(m.group(1)), float(m.group(2))
                    w, h = float(sm.group(1)), float(sm.group(2))
                    drop_rects.append((sx - 15, sy - 2, sx + w + 15, sy + h + 2))
                continue
        keep.append(it)

    def in_any_rect(x, y):
        return any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in drop_rects)

    final: list[str] = []
    for it in keep:
        head = it.lstrip()
        if head.startswith(("(wire", "(label")):
            coords = item_coords(it)
            if coords and all(in_any_rect(x, y) for x, y in coords):
                # Only drop if it's a stub for sheets we removed (plane/sense nets near Sense)
                if head.startswith("(label"):
                    m = re.match(r'\s*\(label "([^"]+)"', it)
                    if m and m.group(1) in {
                        "YA65", "YB65", "YB66", "XA0", "XB0", "YA0", "YB0",
                        "XA1", "XB1", "YA1", "YB1",
                    }:
                        continue
                elif head.startswith("(wire"):
                    # drop wires that only serve those stubs
                    if all(in_any_rect(x, y) for x, y in coords):
                        # check proximity to sense sheet area
                        if any(y < 90 for _, y in coords) and any(x < 100 for x, _ in coords):
                            continue
        final.append(it)

    return sch[:body_start] + "\n".join(final) + "\n" + sch[si:]


def update_root(phase: int) -> None:
    sch = SCH.read_text()
    # Remove existing Sense sheet box + stubs in sense region, and any Ferrite Beads sheet
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)

    sense_rect = (5.0, 20.0, 100.0, 80.0)
    beads_rect = (95.0, 20.0, 220.0, 100.0)

    def in_rect(x, y, rect):
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    keep: list[str] = []
    for it in items:
        head = it.lstrip()
        if head.startswith("(sheet"):
            if 'Sheetfile" "sense.kicad_sch"' in it or 'Sheetfile" "magnetic_core_2x2.kicad_sch"' in it:
                continue
            keep.append(it)
            continue
        if head.startswith("(text") and "SENSE / CCS / INHIBIT" in it:
            keep.append(
                text("SENSE / FERRITE BEADS / CCS / INHIBIT / DECODE CTRL — hierarchy", 20, 15, 1.524)
            )
            continue
        if head.startswith(("(wire", "(label")):
            coords = item_coords(it)
            if not coords:
                keep.append(it)
                continue
            # Drop old Sense right-side plane stubs and left YB stubs in sense box;
            # also drop prior ferrite beads stubs
            if all(in_rect(x, y, sense_rect) for x, y in coords):
                if head.startswith("(label"):
                    m = re.match(r'\s*\(label "([^"]+)"', it)
                    if m and m.group(1) in {
                        "YA65", "YB65", "YB66", "XA0", "XB0", "YA0", "YB0",
                        "XA1", "XB1", "YA1", "YB1",
                    }:
                        continue
                if head.startswith("(wire") and all(in_rect(x, y, sense_rect) for x, y in coords):
                    # keep wires that aren't the sheet stubs (heuristic: stub wires are short horizontal)
                    xs = [x for x, _ in coords]
                    ys = [y for _, y in coords]
                    if max(xs) - min(xs) <= 12 and max(ys) - min(ys) < 0.5:
                        continue
            if all(in_rect(x, y, beads_rect) for x, y in coords):
                if head.startswith("(label"):
                    m = re.match(r'\s*\(label "([^"]+)"', it)
                    if m and m.group(1) in {
                        "YA65", "YB65", "YB66", "XA0", "XB0", "YA0", "YB0",
                        "XA1", "XB1", "YA1", "YB1",
                    }:
                        continue
                if head.startswith("(wire"):
                    xs = [x for x, _ in coords]
                    ys = [y for _, y in coords]
                    if max(xs) - min(xs) <= 12 and max(ys) - min(ys) < 0.5:
                        continue
        keep.append(it)

    # Place Sense (YA65/YB66 outer ends) and Magnetic Cores
    sx_sense, sy_sense = 20.0, 25.0
    sx_beads, sy_beads = 100.0, 25.0

    sense_pins = [("YA65", "passive", "left"), ("YB66", "passive", "left")]
    if phase == 1:
        beads_left = ["YA65", "YB66"]
        beads_right = ["XA0", "XB0", "YA0", "YB0"]
    else:
        beads_left = ["YA65", "YB66", "YB0", "YB1"]
        beads_right = ["XA0", "XA1", "XB0", "XB1", "YA0", "YA1"]

    beads_pins = (
        [(n, "passive", "left") for n in beads_left]
        + [(n, "passive", "right") for n in beads_right]
    )

    o = list(keep)
    # Ensure hierarchy title once
    if not any("FERRITE BEADS" in it and "hierarchy" in it for it in o):
        o.insert(0, text("SENSE / FERRITE BEADS / CCS / INHIBIT / DECODE CTRL — hierarchy", 20, 15, 1.524))

    o += [
        sheet_box("Sense", "sense.kicad_sch", SENSE_UUID, "6", sx_sense, sy_sense, sense_pins, w=45, h=20),
        *stub_pins(sx_sense, sy_sense, ["YA65", "YB66"], [], w=45),
        sheet_box(
            "Magnetic Cores",
            "magnetic_core_2x2.kicad_sch",
            BEADS_UUID,
            "10",
            sx_beads,
            sy_beads,
            beads_pins,
            w=70,
            h=max(30.0, 8.0 + 5.08 * max(len(beads_left), len(beads_right))),
        ),
        *stub_pins(sx_beads, sy_beads, beads_left, beads_right, w=70),
    ]

    new_sch = sch[:body_start] + "\n".join(o) + "\n" + sch[si:]
    SCH.write_text(new_sch)
    print(f"Updated {SCH.name} root sheets (phase {phase})")

    pro = json.loads(PRO.read_text())
    pro["sheets"] = [[u, n] for u, n in SHEET_ORDER]
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    print("Updated core.kicad_pro sheets")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=(1, 2), required=True)
    args = ap.parse_args()

    sch_src = SCH.read_text()
    if args.phase == 1:
        if "FB1" in SENSE.read_text():
            strip_beads_from_sense()
        BEADS.write_text(build_bowtie_page(sch_src))
        print(f"Wrote {BEADS.name} (bowtie)")
        update_root(phase=1)
    else:
        # Ensure beads already off sense (idempotent)
        if "FB1" in SENSE.read_text() or "FB2" in SENSE.read_text():
            strip_beads_from_sense()
        BEADS.write_text(build_grid_page(sch_src))
        print(f"Wrote {BEADS.name} (2x2 grid)")
        update_root(phase=2)


if __name__ == "__main__":
    main()
