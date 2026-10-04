#!/usr/bin/env python3
"""Move Sense / CCS / Inhibit / Decode-ctrl onto hierarchical pages.

Creates:
  sense.kicad_sch       — comparator / latch (extracted from root; beads separate)
  ccs.kicad_sch         — Ic/2 sink (extracted)
  inhibit.kicad_sch     — series YA65/YB66 drive (regenerated, TC4427A×2 + 2N7002)
  decode_ctrl.kicad_sch   — one axis of ADDR_NH/NL + BANK_EN/DEC_EN/REV_EN_n (X + enables)
  decode_ctrl_y.kicad_sch — same address pins, Y binding (no second enable headers)

Root keeps Drive Block, Decode×2, Decoupling×2, Magnetic Cores as sheet stubs + bridging labels.
CCS is one sheet called three times (CCS X / Y / INH). Each instance carries its own +5V bypass.
Magnetic Cores page is owned by gen_ferrite_beads_page.py (do not re-extract cores here).
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
PROJECT = "core"

ROOT_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
SENSE_UUID = "a1b2c3d4-e5f6-4789-a012-777777777777"
CCS_UUID = "a1b2c3d4-e5f6-4789-a012-888888888888"
CCS_Y_UUID = "a1b2c3d4-e5f6-4789-a012-888888888889"
CCS_I_UUID = "a1b2c3d4-e5f6-4789-a012-88888888888a"
INH_UUID = "a1b2c3d4-e5f6-4789-a012-999999999999"
DEC_CTRL_UUID = "a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaaa"
DEC_CTRL_Y_UUID = "a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaab"
DRIVE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-111111111111"
DECODE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-333333333333"
LOGIC_UUID = "a1b2c3d4-e5f6-4789-a012-555555555555"
VDRIVE_UUID = "a1b2c3d4-e5f6-4789-a012-666666666666"

SENSE_BBOX = (12.0, 14.0, 356.0, 101.0)
CCS_BBOX = (12.0, 102.0, 301.0, 192.0)

SENSE_REFS = {
    "U1", "U2", "D1", "D2",
    "R3", "R4", "R5", "R6", "TP1",
}
SENSE_PWR = (
    "#PWR_MAIN", "#PWR_GNDMAIN", "#PWR_R6",
    "#PWR_D1", "#PWR_D2", "#PWR_U1", "#PWR_U2",
    "#FLG_3V3", "#FLG_GND",
)
SENSE_HIER = {"YA65", "YB66"}
BEADS_UUID = "a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb"

CCS_REFS = {"U3", "U4", "Q1", "R7", "R8", "R9", "RV1", "TP2"}
CCS_PWR = ("#PWR_5V", "#PWR_U3", "#PWR_GND_CCS", "#FLG_5V")
CCS_HIER = {"CCS_RET"}

DECODE_CTRL_REFS = {f"J{n}" for n in range(40, 55)} | {f"R{n}" for n in range(40, 55)}
DECODE_CTRL_PWR = tuple(f"#PWR_R{n}" for n in range(40, 55))

INH_FLAT_REFS = {"Q4", "U7", "U8", "Q7", "J5", "R14", "R25"}
INH_FLAT_PWR = ("#PWR_U7", "#PWR_U8", "#PWR_R14", "#PWR_R25", "#PWR_Q7")

# Block pins (N = axis). Parent nets are the root labels — same split as decode_block.
ADDR_NH = ("ADDR_NH0", "ADDR_NH1", "ADDR_NH2")
ADDR_NL = ("ADDR_NL0", "ADDR_NL1", "ADDR_NL2")
ADDR_PINS = ADDR_NH + ADDR_NL
# X sheet also carries the shared enables. Order matches decode_block inputs, then REV.
X_PIN_ORDER = ADDR_PINS + ("BANK_EN", "DEC_EN", "REV_EN_n")
Y_PIN_ORDER = ADDR_PINS
X_PARENT = {
    "ADDR_NH0": "ADDR_XH0",
    "ADDR_NH1": "ADDR_XH1",
    "ADDR_NH2": "ADDR_XH2",
    "ADDR_NL0": "ADDR_XL0",
    "ADDR_NL1": "ADDR_XL1",
    "ADDR_NL2": "ADDR_XL2",
    "BANK_EN": "FWD_EN_n",
    "DEC_EN": "DEC_EN",
    "REV_EN_n": "REV_EN_n",
}
Y_PARENT = {
    "ADDR_NH0": "ADDR_YH0",
    "ADDR_NH1": "ADDR_YH1",
    "ADDR_NH2": "ADDR_YH2",
    "ADDR_NL0": "ADDR_YL0",
    "ADDR_NL1": "ADDR_YL1",
    "ADDR_NL2": "ADDR_YL2",
}
# Root-label names (classify / legacy strip). Not sheet pin names.
ADDR_GROUPS = [
    ["ADDR_XH0", "ADDR_XH1", "ADDR_XH2"],
    ["ADDR_XL0", "ADDR_XL1", "ADDR_XL2"],
    ["ADDR_YH0", "ADDR_YH1", "ADDR_YH2"],
    ["ADDR_YL0", "ADDR_YL1", "ADDR_YL2"],
]
ADDR_NETS = [n for g in ADDR_GROUPS for n in g]
EN_NETS = ["DEC_EN", "FWD_EN_n", "REV_EN_n"]

# Root sheet geometry. gen_xy_decode_page.py no_connects use these coordinates.
DCTRL_X, DCTRL_W = 20.0, 50.0
DCTRL_SY = 230.0
DCTRL_Y_SY = 300.0
DCTRL_LABEL_X = round(DCTRL_X + DCTRL_W + 10.16, 2)  # 80.16


def dctrl_pin_y(sy: float, index: int) -> float:
    return round(sy + 5.08 + index * 5.08, 2)

FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_J = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"
FP_Q = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
FP_FET = "Package_TO_SOT_SMD:SOT-23"


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
        # top-level items are tab-prefixed in file; body may start mid-line
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


def in_bbox(x: float, y: float, box: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def item_coords(item: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", item)] + [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"\(at ([0-9.-]+) ([0-9.-]+)", item)
    ]


def symbol_ref(item: str) -> str | None:
    m = re.search(r'\(property "Reference" "([^"]+)"', item)
    return m.group(1) if m else None


def ref_matches(ref: str, exact: set[str], prefixes: tuple[str, ...]) -> bool:
    if ref in exact:
        return True
    return any(ref.startswith(p) for p in prefixes)


def new_uuid_item(item: str) -> str:
    return re.sub(r'\(uuid "[0-9a-fA-F-]{36}"\)', lambda _m: f'(uuid "{uid()}")', item)


def rewrite_path(item: str, sheet_uuid: str) -> str:
    """Root instance path → /root/sheet."""
    return item.replace(
        f'(path "/{ROOT_UUID}"',
        f'(path "/{ROOT_UUID}/{sheet_uuid}"',
    )


def label_to_hier(item: str, shape: str = "passive") -> str:
    """Convert a local label block into a hierarchical_label (same at/rot)."""
    m = re.match(
        r'\s*\(label "([^"]+)"\s*\n\s*\(at ([0-9.-]+) ([0-9.-]+)(?: ([0-9.-]+))?\)',
        item,
    )
    if not m:
        raise ValueError("not a label")
    name, x, y = m.group(1), m.group(2), m.group(3)
    rot = m.group(4) or "0"
    just = "left"
    if float(rot) in (180.0, 180):
        just = "right"
    return f'''\t(hierarchical_label "{name}"
\t\t(shape {shape})
\t\t(at {x} {y} {rot})
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify {just})
\t\t)
\t\t(uuid "{uid()}")
\t)'''


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


def symbol_inst(lib_id, ref, value, x, y, pins, *, unit=1, rot=0, footprint="", sheet_uuid=INH_UUID):
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
\t\t(instances (project "{PROJECT}" (path "/{ROOT_UUID}/{sheet_uuid}" (reference "{ref}") (unit {unit}))))
\t)'''


def power(lib_id, ref, value, x, y, sheet_uuid=INH_UUID):
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


def page_footer(page_uuid: str, page: str = "1") -> str:
    return f'''\t(sheet_instances
\t\t(path "/{ROOT_UUID}/{page_uuid}"
\t\t\t(page "{page}")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


# ----- classify / extract -----


def classify_region(item: str) -> str | None:
    """Return 'sense'|'ccs'|'inh_flat'|'decode_ctrl'|None."""
    head = item.lstrip()[:40]
    if head.startswith("(symbol"):
        ref = symbol_ref(item)
        if not ref:
            return None
        if ref_matches(ref, SENSE_REFS, SENSE_PWR):
            return "sense"
        if ref_matches(ref, CCS_REFS, CCS_PWR):
            return "ccs"
        if ref_matches(ref, INH_FLAT_REFS, INH_FLAT_PWR):
            return "inh_flat"
        if ref_matches(ref, DECODE_CTRL_REFS, DECODE_CTRL_PWR):
            return "decode_ctrl"
        return None

    if head.startswith("(sheet"):
        # never strip existing hierarchy here
        return None

    coords = item_coords(item)
    if not coords:
        return None

    if head.startswith("(text"):
        t = item
        if "SENSE" in t and "Bowtie" in t or t.startswith('\t(text "SENSE'):
            return "sense"
        if "CCS" in t and ("Ic/2" in t or "TL431" in t or t.startswith('\t(text "CCS')):
            return "ccs"
        if "INHIBIT" in t or "STAGE 5" in t:
            return "inh_flat"
        if "DECODE" in t or "control headers" in t or "74AHC138" in t:
            return "decode_ctrl"
        return None

    if head.startswith("(rectangle"):
        # sense / ccs dotted frames
        if "12.7 15.24" in item or "12.70 15.24" in item or "(start 12.7 15" in item:
            return "sense"
        if "12.7 103.11" in item or "12.70 103" in item or "(start 12.7 103" in item:
            return "ccs"
        if "12.70 205.00" in item or "12.7 205" in item:
            return "inh_flat"
        return None

    if head.startswith("(global_label"):
        m = re.match(r'\s*\(global_label "([^"]+)"', item)
        if not m:
            return None
        name = m.group(1)
        x, y = coords[0]
        if name in ("SENSE_STROBE", "DOUT") and in_bbox(x, y, SENSE_BBOX):
            return "sense"
        return None

    if head.startswith("(label"):
        m = re.match(r'\s*\(label "([^"]+)"', item)
        if not m:
            return None
        name = m.group(1)
        x, y = coords[0]
        if in_bbox(x, y, SENSE_BBOX):
            return "sense"
        if in_bbox(x, y, CCS_BBOX):
            return "ccs"
        # inhibit-ish labels left of decode headers
        if name in {"INH_EN_n", "INH_HS", "INH_LS", "INH_LS_en"} and x < 230:
            return "inh_flat"
        if name in {"YA65", "YB65", "YB66", "CCS_RET", "VDRIVE"} and 191 < y < 380 and x < 200:
            return "inh_flat"
        if name in ADDR_NETS + EN_NETS and y >= 190 and (x >= 200 or x < 150):
            return "decode_ctrl"
        return None

    if head.startswith(("(wire", "(junction", "(no_connect")):
        # exclusive membership by bbox
        if all(in_bbox(x, y, SENSE_BBOX) for x, y in coords):
            return "sense"
        if all(in_bbox(x, y, CCS_BBOX) for x, y in coords):
            return "ccs"
        # inhibit band: y>191, x<210 (avoid decode headers at x≈220+)
        if all(y > 191 and x < 210 for x, y in coords) and any(y < 380 for x, y in coords):
            # exclude pure decode-header column leftovers
            if all(x >= 200 and y > 300 for x, y in coords):
                return "decode_ctrl"
            return "inh_flat"
        # decode ctrl: headers cluster
        if all(200 <= x <= 320 and 190 <= y <= 420 for x, y in coords):
            return "decode_ctrl"
        return None

    return None


def prepare_child_items(items: list[str], sheet_uuid: str, hier_nets: set[str]) -> list[str]:
    out: list[str] = []
    seen_hier: set[str] = set()
    for it in items:
        head = it.lstrip()[:20]
        it2 = new_uuid_item(it)
        it2 = rewrite_path(it2, sheet_uuid)
        if head.startswith("(label"):
            m = re.match(r'\s*\(label "([^"]+)"', it2)
            if m and m.group(1) in hier_nets:
                name = m.group(1)
                # First occurrence → hierarchical pin; later copies stay as
                # local labels so mid-circuit attachment points are preserved.
                if name not in seen_hier:
                    seen_hier.add(name)
                    shape = "input" if name in {"INH_EN_n"} else "passive"
                    if name.endswith("_n") and name.startswith("ADDR"):
                        shape = "output"
                    out.append(label_to_hier(it2, shape=shape))
                    continue
        out.append(it2 if it2.startswith("\t") else "\t" + it2.lstrip())
    return out


def write_extracted_page(
    path: Path,
    title: str,
    comment: str,
    page_uuid: str,
    items: list[str],
    lib_ids: list[str],
    sch: str,
    hier_nets: set[str],
) -> None:
    libs = "\n".join(extract_lib(sch, lid) for lid in lib_ids)
    body = prepare_child_items(items, page_uuid, hier_nets)
    text_out = page_header(title, comment, page_uuid, libs) + "\n".join(body) + "\n" + page_footer(page_uuid)
    path.write_text(text_out)
    print(f"Wrote {path.name} ({len(body)} items)")


# ----- inhibit regenerate (no local caps) -----


def build_inhibit_page(sch: str) -> str:
    lib_ids = [
        "core_memory:FDS8958A",
        "Driver_FET:TC4427xOA",
        "Transistor_FET:2N7002",
        "Connector:Conn_01x01",
        "Device:R",
        "power:+3V3",
        "power:GND",
        "power:VDRIVE",
    ]
    libs = "\n".join(extract_lib(sch, lid) for lid in lib_ids)
    o: list[str] = [
        text("INHIBIT — series YA65→fold→YB66→CCS", 20, 20, 1.524),
        text(
            "FDS8958A P→YA65 / N→YB66→CCS_RET. Both TC4427A: HS←INH_EN_n, "
            "LS←INH_LS_en (2N7002 invert). Caps on Decoupling VDRIVE.",
            20,
            28,
        ),
    ]

    # Q4 half-bridge
    qx, qy = 80.0, 80.0
    o.append(
        symbol_inst(
            "core_memory:FDS8958A", "Q4", "FDS8958A", qx, qy,
            ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_Q,
        )
    )
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

    o += [
        wire(s1, (round(s1[0] - 12.7, 2), s1[1])),
        hier("VDRIVE", "passive", (round(s1[0] - 12.7, 2), s1[1]), 180),
        wire(g1, (round(g1[0] - 12.7, 2), g1[1])),
        label("INH_HS", (round(g1[0] - 12.7, 2), g1[1]), 180),
        wire(g2, (round(g2[0] - 12.7, 2), g2[1])),
        label("INH_LS", (round(g2[0] - 12.7, 2), g2[1]), 180),
        wire(s2, (round(s2[0] - 12.7, 2), s2[1])),
        hier("CCS_RET", "passive", (round(s2[0] - 12.7, 2), s2[1]), 180),
    ]
    dy_hs = round((d1_7[1] + d1_8[1]) / 2, 2)
    o += [
        wire(d1_7, (d1_7[0], dy_hs)),
        wire((d1_7[0], dy_hs), (round(d1_7[0] + 15.24, 2), dy_hs)),
        junction((d1_7[0], dy_hs)),
        hier("YA65", "passive", (round(d1_7[0] + 15.24, 2), dy_hs)),
    ]
    dy_ls = round((d2_5[1] + d2_6[1]) / 2, 2)
    o += [
        wire(d2_6, (d2_6[0], dy_ls)),
        wire((d2_6[0], dy_ls), (round(d2_6[0] + 15.24, 2), dy_ls)),
        junction((d2_6[0], dy_ls)),
        hier("YB66", "passive", (round(d2_6[0] + 15.24, 2), dy_ls)),
    ]

    # INH_EN_n bus
    inh_bus = (200.0, 70.0)
    o += [
        hier("INH_EN_n", "input", (round(inh_bus[0] - 5.08, 2), inh_bus[1]), 180),
        wire((round(inh_bus[0] - 5.08, 2), inh_bus[1]), inh_bus),
        junction(inh_bus),
    ]
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
    jx, jy = round(inh_bus[0] - 35.56, 2), inh_bus[1]
    o.append(
        symbol_inst(
            "Connector:Conn_01x01", "J5", "INH_EN_n", jx, jy, ["1"],
            rot=180, footprint=FP_J,
        )
    )
    jp = pin_xy(jx, jy, -5.08, 0, 180)
    o.append(wire(jp, inh_bus))

    def add_driver(uref: str, ux: float, uy: float, out_net: str, inh_junc: tuple[float, float]) -> None:
        o.append(
            symbol_inst(
                "Driver_FET:TC4427xOA", uref, "TC4427A", ux, uy,
                ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_Q,
            )
        )
        nc1 = pin_xy(ux, uy, -7.62, 0)
        ina = pin_xy(ux, uy, -10.16, 2.54)
        gnd = pin_xy(ux, uy, 0, -10.16)
        inb = pin_xy(ux, uy, -10.16, -2.54)
        outb = pin_xy(ux, uy, 10.16, -2.54)
        vdd = pin_xy(ux, uy, 0, 10.16)
        outa = pin_xy(ux, uy, 10.16, 2.54)
        nc8 = pin_xy(ux, uy, 7.62, 0)
        o.extend([no_connect(nc1), no_connect(nc8), no_connect(outb)])
        o.extend([
            wire(outa, (round(outa[0] + 10.16, 2), outa[1])),
            label(out_net, (round(outa[0] + 10.16, 2), outa[1])),
            wire(ina, (inh_junc[0], ina[1])),
            wire((inh_junc[0], ina[1]), inh_junc),
            junction((inh_junc[0], ina[1])),
            wire(inb, (round(inb[0] - 7.62, 2), inb[1])),
            power("power:+3V3", f"#PWR_{uref}_INB", "+3V3", round(inb[0] - 7.62, 2), round(inb[1] - 7.62, 2)),
            wire((round(inb[0] - 7.62, 2), inb[1]), (round(inb[0] - 7.62, 2), round(inb[1] - 7.62, 2))),
        ])
        vp = (vdd[0], round(vdd[1] - 5.08, 2))
        vm = (gnd[0], round(gnd[1] + 5.08, 2))
        o.extend([
            wire(vdd, vp),
            power("power:VDRIVE", f"#PWR_{uref}_VDD", "VDRIVE", vp[0], round(vp[1] - 5.08, 2)),
            wire(vp, (vp[0], round(vp[1] - 5.08, 2))),
            junction(vp),
            wire(gnd, vm),
            power("power:GND", f"#PWR_{uref}_GND", "GND", vm[0], round(vm[1] + 5.08, 2)),
            wire(vm, (vm[0], round(vm[1] + 5.08, 2))),
            junction(vm),
        ])

    add_driver("U7", 250.0, 60.0, "INH_HS", inh_bus)

    # 2N7002 invert → INH_LS_en
    qx7, qy7 = 200.0, 130.0
    o.append(
        symbol_inst(
            "Transistor_FET:2N7002", "Q7", "2N7002", qx7, qy7, ["1", "2", "3"],
            footprint=FP_FET,
        )
    )
    # 2N7002 lib: G(-5.08,0), S(2.54,-5.08), D(2.54,5.08)
    g = pin_xy(qx7, qy7, -5.08, 0)
    s = pin_xy(qx7, qy7, 2.54, -5.08)
    d = pin_xy(qx7, qy7, 2.54, 5.08)
    # Place LS bus off the INH_EN_n spine (x=200) so the buses cannot short
    ls_bus = (230.0, 150.0)
    gate_j = (round(g[0] - 5.08, 2), g[1])  # left of gate
    o.extend([
        wire(g, gate_j),
        wire(gate_j, (gate_j[0], inh_bus[1])),
        wire((gate_j[0], inh_bus[1]), inh_bus),
        junction((gate_j[0], inh_bus[1])),
        junction(inh_bus),
        wire(s, (s[0], round(s[1] + 5.08, 2))),
        power("power:GND", "#PWR_Q7_S", "GND", s[0], round(s[1] + 7.62, 2)),
        wire((s[0], round(s[1] + 5.08, 2)), (s[0], round(s[1] + 7.62, 2))),
        wire(d, (ls_bus[0], d[1])),
        wire((ls_bus[0], d[1]), ls_bus),
        junction((ls_bus[0], d[1])),
        junction(ls_bus),
        label("INH_LS_en", (round(ls_bus[0] - 5.08, 2), ls_bus[1]), 180),
    ])
    rx, ry = round(ls_bus[0] - 15.24, 2), round(ls_bus[1] - 12.7, 2)
    o.append(symbol_inst("Device:R", "R25", "10k", rx, ry, ["1", "2"], footprint=FP_R))
    rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
    o.extend([
        wire(rb, (rx, ls_bus[1])),
        wire((rx, ls_bus[1]), ls_bus),
        junction((rx, ls_bus[1])),
        power("power:+3V3", "#PWR_R25", "+3V3", rx, round(rt[1] - 7.62, 2)),
        wire(rt, (rx, round(rt[1] - 7.62, 2))),
    ])

    add_driver("U8", 250.0, 150.0, "INH_LS", ls_bus)

    return page_header(
        "Inhibit",
        "Series inhibit on folded sense; TC4427A×2",
        INH_UUID,
        libs,
    ) + "\n".join(o) + "\n" + page_footer(INH_UUID)


# ----- decode_ctrl page -----


def build_decode_ctrl_page(
    sch: str,
    *,
    sheet_uuid: str,
    page: str,
    channels: list[tuple[str, str, str, str]],
    comment: str,
) -> str:
    """channels: (pin, jref, rref, pull) pull is 'down' or 'up'.

    Hierarchical labels are the block pins (ADDR_NH0, BANK_EN, …).
    The parent net is a root label, not a name inside this sheet.
    """
    lib_ids = ["Connector:Conn_01x01", "Device:R", "power:GND", "power:+3V3"]
    libs = "\n".join(extract_lib(sch, lid) for lid in lib_ids)
    o: list[str] = [
        text("DECODE CTRL — address + bank enables", 20, 20, 1.524),
        text("Pins ADDR_NH/NL, BANK_EN, DEC_EN, REV_EN_n. Root binds the axis and FWD/REV.", 20, 28),
    ]
    su = sheet_uuid

    def sym(lib_id, ref, value, x, y, pins, *, rot=0, footprint=""):
        return symbol_inst(lib_id, ref, value, x, y, pins, rot=rot, footprint=footprint, sheet_uuid=su)

    def pwr(lib_id, ref, value, x, y):
        return power(lib_id, ref, value, x, y, sheet_uuid=su)

    def header(jref, rref, pin, x, y, pull):
        o.append(sym("Connector:Conn_01x01", jref, pin, x, y, ["1"], footprint=FP_J))
        jp = pin_xy(x, y, -5.08, 0, 0)
        junc = (round(jp[0] - 5.08, 2), y)
        hp = (round(junc[0] - 7.62, 2), y)
        o.extend([
            wire(jp, hp),
            junction(junc),
            hier(pin, "output", hp, 180),
        ])
        if pull == "down":
            rx, ry = round(junc[0] - 12.7, 2), round(y + 12.7, 2)
            o.append(sym("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
            rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
            o.extend([
                wire(rt, (rx, junc[1])), wire((rx, junc[1]), junc), junction((rx, junc[1])),
                pwr("power:GND", f"#PWR_{rref}", "GND", rx, round(rb[1] + 7.62, 2)),
                wire(rb, (rx, round(rb[1] + 7.62, 2))),
            ])
        else:
            rx, ry = round(junc[0] - 12.7, 2), round(y - 12.7, 2)
            o.append(sym("Device:R", rref, "10k", rx, ry, ["1", "2"], footprint=FP_R))
            rt, rb = pin_xy(rx, ry, 0, 3.81), pin_xy(rx, ry, 0, -3.81)
            o.extend([
                wire(rb, (rx, junc[1])), wire((rx, junc[1]), junc), junction((rx, junc[1])),
                pwr("power:+3V3", f"#PWR_{rref}", "+3V3", rx, round(rt[1] - 7.62, 2)),
                wire(rt, (rx, round(rt[1] - 7.62, 2))),
            ])

    addr = [c for c in channels if c[0].startswith("ADDR_")]
    enables = [c for c in channels if not c[0].startswith("ADDR_")]
    base_x, base_y, group_pitch = 80.0, 50.0, 38.1
    for gi in range(0, len(addr), 3):
        gy = round(base_y + (gi // 3) * group_pitch, 2)
        for bi, (pin, jref, rref, pull) in enumerate(addr[gi : gi + 3]):
            header(jref, rref, pin, round(base_x + bi * 22.86, 2), gy, pull)
    if enables:
        en_y = round(base_y + ((len(addr) + 2) // 3) * group_pitch, 2)
        for bi, (pin, jref, rref, pull) in enumerate(enables):
            header(jref, rref, pin, round(base_x + bi * 22.86, 2), en_y, pull)

    return page_header(
        "Decode Control",
        comment,
        sheet_uuid,
        libs,
    ) + "\n".join(o) + "\n" + page_footer(sheet_uuid, page)


# ----- root sheet boxes -----


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


def sheet_box(
    name: str,
    file: str,
    sheet_uuid: str,
    page: str,
    sx: float,
    sy: float,
    pins: list[tuple[str, str, str]],
    *,
    w: float = 55.0,
    h: float | None = None,
) -> str:
    """pins: list of (name, shape, side) side in {left,right}."""
    if h is None:
        h = max(25.0, 8.0 + 5.08 * max(1, len(pins)))
    pin_blocks = []
    left = [(n, sh) for n, sh, side in pins if side == "left"]
    right = [(n, sh) for n, sh, side in pins if side == "right"]
    for i, (n, sh) in enumerate(left):
        pin_blocks.append(sheet_pin(n, sh, sx, round(sy + 5.08 + i * 5.08, 2), 180))
    for i, (n, sh) in enumerate(right):
        pin_blocks.append(sheet_pin(n, sh, round(sx + w, 2), round(sy + 5.08 + i * 5.08, 2), 0))
    pins_s = "\n".join(pin_blocks)
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
{pins_s}
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def stub_pins(
    sx: float,
    sy: float,
    pins_left: list[str],
    pins_right: list[str],
    *,
    w: float = 55.0,
    label_of: dict[str, str] | None = None,
) -> list[str]:
    """Local labels + short wires on root for sheet pins.

    label_of maps a block pin name to the parent net on the root.
    """
    names = label_of or {}
    o: list[str] = []
    for i, name in enumerate(pins_left):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = sx
        o += [
            wire((round(px - 10.16, 2), py), (px, py)),
            label(names.get(name, name), (round(px - 10.16, 2), py), 180),
        ]
    for i, name in enumerate(pins_right):
        py = round(sy + 5.08 + i * 5.08, 2)
        px = round(sx + w, 2)
        o += [
            wire((px, py), (round(px + 10.16, 2), py)),
            label(names.get(name, name), (round(px + 10.16, 2), py)),
        ]
    return o


def strip_region_sheets(sch: str) -> str:
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)
    keep = []
    for it in items:
        if it.lstrip().startswith("(sheet") and any(
            f in it
            for f in (
                "sense.kicad_sch",
                "ccs.kicad_sch",
                "inhibit.kicad_sch",
                "decode_ctrl.kicad_sch",
                "decode_ctrl_y.kicad_sch",
            )
        ):
            continue
        keep.append(it)
    return sch[:body_start] + "\n".join(keep) + "\n" + sch[si:]


def alt_ccs_ref(ref: str, tag: str, delta: int) -> str:
    if ref.startswith("#"):
        return f"{ref}_{tag}"
    m = re.match(r"^([A-Z]+)(\d+)$", ref)
    if not m:
        return f"{ref}_{tag}"
    return f"{m.group(1)}{int(m.group(2)) + delta}"


def ccs_instance_paths(ref: str, unit: int = 1) -> str:
    rows = [
        (CCS_UUID, ref),
        (CCS_Y_UUID, alt_ccs_ref(ref, "Y", 100)),
        (CCS_I_UUID, alt_ccs_ref(ref, "I", 200)),
    ]
    body = "\n".join(
        f'\t\t\t\t(path "/{ROOT_UUID}/{uuid_}"\n'
        f'\t\t\t\t\t(reference "{r}")\n'
        f'\t\t\t\t\t(unit {unit})\n'
        f'\t\t\t\t)'
        for uuid_, r in rows
    )
    return f'''\t\t(instances
\t\t\t(project "{PROJECT}"
{body}
\t\t\t)
\t\t)'''


def expand_ccs_instances(text: str) -> str:
    """Give every CCS symbol a reference on the Y and inhibit sheet paths."""
    if CCS_Y_UUID in text:
        return text
    path_x = f"/{ROOT_UUID}/{CCS_UUID}"
    pat = re.compile(
        r'\(path "' + re.escape(path_x) + r'"\s*'
        r'\(reference "([^"]+)"\)\s*'
        r'\(unit (\d+)\)\s*'
        r'\)'
    )

    def repl(m: re.Match[str]) -> str:
        ref, unit = m.group(1), m.group(2)
        extra = []
        for uuid_, r in (
            (CCS_Y_UUID, alt_ccs_ref(ref, "Y", 100)),
            (CCS_I_UUID, alt_ccs_ref(ref, "I", 200)),
        ):
            extra.append(
                f'(path "/{ROOT_UUID}/{uuid_}"\n'
                f'\t\t\t\t\t(reference "{r}")\n'
                f'\t\t\t\t\t(unit {unit})\n'
                f'\t\t\t\t)'
            )
        return m.group(0) + "\n\t\t\t\t" + "\n\t\t\t\t".join(extra)

    return pat.sub(repl, text)


def add_ccs_bypass(page_text: str) -> str:
    if '(property "Reference" "C5"' in page_text:
        return page_text
    if '(symbol "Device:C"' not in page_text:
        host = (CORE / "decoupling_logic.kicad_sch").read_text()
        if '(symbol "Device:C"' not in host:
            host = SCH.read_text()
        lib = extract_lib(host, "Device:C")
        page_text = page_text.replace("(lib_symbols\n", "(lib_symbols\n" + lib + "\n", 1)
    o: list[str] = [
        text(
            "Local +5V bypass — clones with each CCS instance",
            210,
            28,
            1.016,
        )
    ]
    x, y = 240.0, 55.0
    rail_y, gnd_y = 39.76, 70.24
    for lib_id, ref, val, px, py in (
        ("power:+5V", "#PWR_C5_V", "+5V", x, rail_y),
        ("power:GND", "#PWR_C5_G", "GND", x, gnd_y),
    ):
        o.append(
            f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {px} {py} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, f"{px} {py + 2.54} 0", hide=True)}
{prop("Value", val, f"{px} {py - 2.54} 0")}
{prop("Footprint", "", f"{px} {py} 0", hide=True)}
{prop("Datasheet", "", f"{px} {py} 0", hide=True)}
{prop("Description", "", f"{px} {py} 0", hide=True)}
\t\t(pin "1" (uuid "{uid()}"))
{ccs_instance_paths(ref)}
\t)'''
        )
    for cref, cval, dx in (("C5", "100n", -7.62), ("C6", "1u", 7.62)):
        cx = round(x + dx, 2)
        ct, cb = pin_xy(cx, y, 0, 3.81), pin_xy(cx, y, 0, -3.81)
        o.append(
            f'''\t(symbol
\t\t(lib_id "Device:C")
\t\t(at {cx} {y} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", cref, f"{cx + 2.54} {y - 10.16} 0")}
{prop("Value", cval, f"{cx + 2.54} {y - 7.62} 0")}
{prop("Footprint", "Capacitor_SMD:C_0805_2012Metric", f"{cx} {y} 0", hide=True)}
{prop("Datasheet", "", f"{cx} {y} 0", hide=True)}
{prop("Description", "", f"{cx} {y} 0", hide=True)}
\t\t(pin "1" (uuid "{uid()}"))
\t\t(pin "2" (uuid "{uid()}"))
{ccs_instance_paths(cref)}
\t)'''
        )
        o += [
            wire(ct, (cx, rail_y)),
            wire((cx, rail_y), (x, rail_y)),
            junction((cx, rail_y)),
            wire(cb, (cx, gnd_y)),
            wire((cx, gnd_y), (x, gnd_y)),
            junction((cx, gnd_y)),
        ]
    o += [junction((x, rail_y)), junction((x, gnd_y))]
    page_text = page_text.replace(
        '(comment 1 "Ic/2 constant-current sink")',
        '(comment 1 "Ic/2 sink; local +5V 100n+1u; root binds CCS_X / CCS_Y / CCS_INH")',
        1,
    )
    block = "\n".join(o)
    marker = "\t(sheet_instances"
    if marker in page_text:
        return page_text.replace(marker, block + "\n" + marker, 1)
    stripped = page_text.rstrip()
    if not stripped.endswith(")"):
        raise SystemExit("ccs sheet has no closing paren")
    sheet_inst = (
        '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "7")\n\t\t)\n\t)\n'
    )
    return stripped[:-1] + block + "\n" + sheet_inst + ")\n"


def relabel_at(sch: str, old: str, at: str, new: str) -> str:
    needle = f'(label "{old}"\n\t\t(at {at}'
    done = f'(label "{new}"\n\t\t(at {at}'
    if done in sch:
        return sch
    if needle not in sch:
        raise SystemExit(f"missing label {old} at {at}")
    return sch.replace(needle, done, 1)


def ensure_three_ccs(sch: str) -> str:
    """One ccs.kicad_sch, three root calls: CCS_X, CCS_Y, CCS_INH."""
    page = CORE / "ccs.kicad_sch"
    page.write_text(add_ccs_bypass(expand_ccs_instances(page.read_text())))

    sch = relabel_at(sch, "CCS_RET", "387.3 39.24 180", "CCS_X")
    sch = relabel_at(sch, "CCS_RET", "9.84 100.08 180", "CCS_X")
    sch = relabel_at(sch, "CCS_RET", "9.84 155.24 180", "CCS_INH")

    sch = sch.replace(
        f'(uuid "{CCS_UUID}")\n\t\t(property "Sheetname" "CCS"',
        f'(uuid "{CCS_UUID}")\n\t\t(property "Sheetname" "CCS X"',
        1,
    )

    if f'(uuid "{CCS_Y_UUID}")' not in sch:
        extra = [
            sheet_box(
                "CCS Y",
                "ccs.kicad_sch",
                CCS_Y_UUID,
                "12",
                80.0,
                95.0,
                [("CCS_RET", "passive", "left")],
                w=45,
                h=20,
            ),
            *stub_pins(80.0, 95.0, ["CCS_RET"], [], w=45, label_of={"CCS_RET": "CCS_Y"}),
            sheet_box(
                "CCS INH",
                "ccs.kicad_sch",
                CCS_I_UUID,
                "13",
                140.0,
                95.0,
                [("CCS_RET", "passive", "left")],
                w=45,
                h=20,
            ),
            *stub_pins(140.0, 95.0, ["CCS_RET"], [], w=45, label_of={"CCS_RET": "CCS_INH"}),
        ]
        marker = "\t(sheet_instances"
        if marker not in sch:
            raise SystemExit("root sheet_instances missing")
        sch = sch.replace(marker, "\n".join(extra) + "\n" + marker, 1)

    pro = json.loads(PRO.read_text())
    rows = pro.get("sheets", [])
    out: list = []
    placed = False
    for row in rows:
        if row[0] in {CCS_UUID, CCS_Y_UUID, CCS_I_UUID}:
            continue
        out.append(row)
        if row[0] == "a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb":
            out.extend(
                [
                    [CCS_UUID, "CCS X"],
                    [CCS_Y_UUID, "CCS Y"],
                    [CCS_I_UUID, "CCS INH"],
                ]
            )
            placed = True
    if not placed:
        out.extend(
            [
                [CCS_UUID, "CCS X"],
                [CCS_Y_UUID, "CCS Y"],
                [CCS_I_UUID, "CCS INH"],
            ]
        )
    pro["sheets"] = out
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    return sch


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated")

    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)

    buckets: dict[str, list[str]] = {
        "sense": [],
        "ccs": [],
        "inh_flat": [],
        "decode_ctrl": [],
        "keep": [],
    }
    for it in items:
        # Drop prior region sheet boxes (re-placed below)
        if it.lstrip().startswith("(sheet") and any(
            f in it for f in (
                "sense.kicad_sch",
                "ccs.kicad_sch",
                "inhibit.kicad_sch",
                "decode_ctrl.kicad_sch",
                "decode_ctrl_y.kicad_sch",
            )
        ):
            continue
        reg = classify_region(it)
        if reg is None:
            buckets["keep"].append(it)
        else:
            buckets[reg].append(it)

    print(
        "Classified:",
        {k: len(v) for k, v in buckets.items()},
    )

    sense_libs = [
        "Comparator:TLV3501AID",
        "74xx:74LS74",
        "Diode:BAT54S",
        "Device:R",
        "Connector:TestPoint",
        "power:+3V3",
        "power:GND",
        "power:PWR_FLAG",
    ]
    ccs_libs = [
        "core_memory:OPA192",
        "Reference_Voltage:TL431LP",
        "Transistor_FET:IRLZ44N",
        "Device:R",
        "Device:R_Potentiometer_US",
        "Connector:TestPoint",
        "power:+5V",
        "power:GND",
        "power:PWR_FLAG",
    ]

    def bucket_has_ref(items: list[str], ref: str) -> bool:
        return any(f'Reference" "{ref}"' in it for it in items)

    # Re-running this migrator must not replace a finished hierarchical page
    # with the handful of root stubs that still mention those nets.
    if bucket_has_ref(buckets["sense"], "U1"):
        write_extracted_page(
            CORE / "sense.kicad_sch",
            "Sense",
            "TLV3501 / 74AHC74 latch (beads on ferrite_beads)",
            SENSE_UUID,
            buckets["sense"],
            sense_libs,
            sch,
            SENSE_HIER,
        )
    else:
        print("Sense already hierarchical; left sense.kicad_sch")
    if bucket_has_ref(buckets["ccs"], "U3"):
        write_extracted_page(
            CORE / "ccs.kicad_sch",
            "CCS",
            "Ic/2 constant-current sink",
            CCS_UUID,
            buckets["ccs"],
            ccs_libs,
            sch,
            CCS_HIER,
        )
    else:
        print("CCS already hierarchical; left ccs.kicad_sch")

    if bucket_has_ref(buckets["inh_flat"], "U7"):
        (CORE / "inhibit.kicad_sch").write_text(build_inhibit_page(sch))
        print("Wrote inhibit.kicad_sch")
    else:
        print("Inhibit already hierarchical; left inhibit.kicad_sch")

    # X instance carries address + the one set of enable headers.
    # Y instance is address only so J52–J54 are not cloned.
    x_channels = [
        ("ADDR_NH0", "J40", "R40", "down"),
        ("ADDR_NH1", "J41", "R41", "down"),
        ("ADDR_NH2", "J42", "R42", "down"),
        ("ADDR_NL0", "J43", "R43", "down"),
        ("ADDR_NL1", "J44", "R44", "down"),
        ("ADDR_NL2", "J45", "R45", "down"),
        ("BANK_EN", "J53", "R53", "up"),
        ("DEC_EN", "J52", "R52", "down"),
        ("REV_EN_n", "J54", "R54", "up"),
    ]
    y_channels = [
        ("ADDR_NH0", "J46", "R46", "down"),
        ("ADDR_NH1", "J47", "R47", "down"),
        ("ADDR_NH2", "J48", "R48", "down"),
        ("ADDR_NL0", "J49", "R49", "down"),
        ("ADDR_NL1", "J50", "R50", "down"),
        ("ADDR_NL2", "J51", "R51", "down"),
    ]
    (CORE / "decode_ctrl.kicad_sch").write_text(
        build_decode_ctrl_page(
            sch,
            sheet_uuid=DEC_CTRL_UUID,
            page="9",
            channels=x_channels,
            comment="ADDR_NH/NL + BANK_EN/DEC_EN/REV_EN_n; root binds X and FWD_EN_n",
        )
    )
    print("Wrote decode_ctrl.kicad_sch")
    (CORE / "decode_ctrl_y.kicad_sch").write_text(
        build_decode_ctrl_page(
            sch,
            sheet_uuid=DEC_CTRL_Y_UUID,
            page="11",
            channels=y_channels,
            comment="ADDR_NH/NL only; root binds Y. Enables stay on Decode CTRL",
        )
    )
    print("Wrote decode_ctrl_y.kicad_sch")

    if not bucket_has_ref(buckets["sense"], "U1"):
        # Pages already live in hierarchy. Rebuilding the root from classify()
        # drops sheet stubs. Only ensure the Y ctrl sheet is in the project index.
        pro = json.loads(PRO.read_text())
        sheets = pro.get("sheets", [])
        if not any(row[0] == DEC_CTRL_Y_UUID for row in sheets):
            updated: list = []
            placed = False
            for row in sheets:
                updated.append(row)
                if row[0] == DEC_CTRL_UUID:
                    updated.append([DEC_CTRL_Y_UUID, "Decode CTRL Y"])
                    placed = True
            if not placed:
                updated.append([DEC_CTRL_Y_UUID, "Decode CTRL Y"])
            pro["sheets"] = updated
            PRO.write_text(json.dumps(pro, indent=2) + "\n")
            print("Added Decode CTRL Y to core.kicad_pro")
        else:
            print("Root left intact; decode_ctrl pages refreshed")
        sch = ensure_three_ccs(SCH.read_text())
        SCH.write_text(sch)
        print("CCS X / CCS Y / CCS INH")
        return

    # Rebuild root body: keep + new sheets/stubs/titles (no flat sense/ccs/inh/decode_ctrl)
    sense_left = ["YA65", "YB66"]
    sense_right: list[str] = []
    ccs_left = ["CCS_RET"]
    inh_left = ["INH_EN_n", "VDRIVE", "CCS_RET"]
    inh_right = ["YA65", "YB66"]
    x_pins = list(X_PIN_ORDER)
    y_pins = list(Y_PIN_ORDER)

    # Layout: left column for Sense/CCS/Inhibit/DecodeCtrl; Drive/Decode stay
    sx_sense, sy_sense = 20.0, 25.0
    sx_ccs, sy_ccs = 20.0, 95.0
    sx_inh, sy_inh = 20.0, 140.0
    sx_dctrl, sy_dctrl = DCTRL_X, DCTRL_SY
    sy_dctrl_y = DCTRL_Y_SY

    o: list[str] = list(buckets["keep"])
    o += [
        text("SENSE / CCS / INHIBIT / DECODE CTRL — hierarchy", 20, 15, 1.524),
        sheet_box(
            "Sense",
            "sense.kicad_sch",
            SENSE_UUID,
            "6",
            sx_sense,
            sy_sense,
            [(n, "passive", "left") for n in sense_left]
            + [(n, "passive", "right") for n in sense_right],
            w=45,
            h=20,
        ),
        *stub_pins(sx_sense, sy_sense, sense_left, sense_right, w=45),
        sheet_box(
            "CCS X",
            "ccs.kicad_sch",
            CCS_UUID,
            "7",
            sx_ccs,
            sy_ccs,
            [(n, "passive", "left") for n in ccs_left],
            w=45,
            h=20,
        ),
        *stub_pins(sx_ccs, sy_ccs, ccs_left, [], w=45, label_of={"CCS_RET": "CCS_X"}),
        sheet_box(
            "Inhibit",
            "inhibit.kicad_sch",
            INH_UUID,
            "8",
            sx_inh,
            sy_inh,
            [(n, "input" if n == "INH_EN_n" else "passive", "left") for n in inh_left]
            + [(n, "passive", "right") for n in inh_right],
            w=55,
        ),
        *stub_pins(
            sx_inh,
            sy_inh,
            inh_left,
            inh_right,
            w=55,
            label_of={"CCS_RET": "CCS_INH"},
        ),
        sheet_box(
            "Decode CTRL",
            "decode_ctrl.kicad_sch",
            DEC_CTRL_UUID,
            "9",
            sx_dctrl,
            sy_dctrl,
            [(n, "output", "right") for n in x_pins],
            w=DCTRL_W,
            h=max(40.0, 8.0 + 5.08 * len(x_pins)),
        ),
        *stub_pins(sx_dctrl, sy_dctrl, [], x_pins, w=DCTRL_W, label_of=X_PARENT),
        sheet_box(
            "Decode CTRL Y",
            "decode_ctrl_y.kicad_sch",
            DEC_CTRL_Y_UUID,
            "11",
            sx_dctrl,
            sy_dctrl_y,
            [(n, "output", "right") for n in y_pins],
            w=DCTRL_W,
            h=max(40.0, 8.0 + 5.08 * len(y_pins)),
        ),
        *stub_pins(sx_dctrl, sy_dctrl_y, [], y_pins, w=DCTRL_W, label_of=Y_PARENT),
    ]
    new_sch = sch[:body_start] + "\n".join(o) + "\n" + sch[si:]

    # Ensure Decode Block still has ADDR/EN labels on sheet pins (not stolen by decode_ctrl strip)
    def ensure_decode_addr_stubs(sch_text: str) -> str:
        need = ADDR_NETS + EN_NETS
        extras = []
        for sheet_name, sx in (("X FWD", 400.0), ("Y FWD", 490.0), ("X REV", 400.0), ("Y REV", 490.0)):
            block_m = None
            for sm in re.finditer(r'\t\(sheet\n', sch_text):
                start = sm.start()
                depth = 0
                for i in range(start, len(sch_text)):
                    if sch_text[i] == "(":
                        depth += 1
                    elif sch_text[i] == ")":
                        depth -= 1
                        if depth == 0:
                            block = sch_text[start : i + 1]
                            break
                if f'Sheetname" "{sheet_name}"' in block:
                    block_m = block
                    break
            if not block_m:
                continue
            for pm in re.finditer(
                r'\(pin "([^"]+)" ([^\s]+)\s+\(at ([0-9.-]+) ([0-9.-]+)',
                block_m,
            ):
                pname, _shape, px, py = pm.group(1), pm.group(2), float(pm.group(3)), float(pm.group(4))
                # Parent nets are ADDR_XH* / FWD_EN_n mapped onto block pins — look for parent labels
                parent_names = need
                existing = False
                for lm in re.finditer(
                    rf'\(label "([^"]+)"\s+\(at ([0-9.-]+) ([0-9.-]+)',
                    sch_text,
                ):
                    lname, lx, ly = lm.group(1), float(lm.group(2)), float(lm.group(3))
                    if abs(ly - py) < 0.2 and abs(lx - px) < 20:
                        existing = True
                        break
                if existing:
                    continue
                # Only auto-stub if sheet pin name is itself a root net we care about
                if pname not in parent_names:
                    continue
                extras += [
                    wire((round(px - 10.16, 2), py), (px, py)),
                    label(pname, (round(px - 10.16, 2), py), 180),
                ]
        if not extras:
            return sch_text
        body = sch_text.rstrip()
        return body[:-1] + "\n".join(extras) + "\n)\n"

    new_sch = ensure_decode_addr_stubs(new_sch)

    SCH.write_text(new_sch)
    print(f"Updated {SCH}")

    pro = json.loads(PRO.read_text())
    pro["sheets"] = [
        [ROOT_UUID, "core"],
        [DRIVE_BLOCK_UUID, "X0 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111111112", "X1 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111111113", "X0 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111111114", "X1 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111111115", "Y0 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111111116", "Y1 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111111117", "Y0 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111111118", "Y1 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110120", "X2 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110121", "X2 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110122", "Y2 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110123", "Y2 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110124", "X3 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110125", "X3 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110126", "Y3 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110127", "Y3 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110128", "X4 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110129", "X4 REV"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012a", "Y4 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012b", "Y4 REV"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012c", "X5 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012d", "X5 REV"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012e", "Y5 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-11111111012f", "Y5 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110130", "X6 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110131", "X6 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110132", "Y6 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110133", "Y6 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110134", "X7 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110135", "X7 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111110136", "Y7 FWD"],
        ["a1b2c3d4-e5f6-4789-a012-111111110137", "Y7 REV"],
        ["a1b2c3d4-e5f6-4789-a012-111111111119", "Steer 2x2"],
        [DECODE_BLOCK_UUID, "X FWD"],
        ["a1b2c3d4-e5f6-4789-a012-333333333334", "Y FWD"],
        ["a1b2c3d4-e5f6-4789-a012-333333333335", "X REV"],
        ["a1b2c3d4-e5f6-4789-a012-333333333336", "Y REV"],
        [LOGIC_UUID, "Decoupling Logic"],
        [VDRIVE_UUID, "Decoupling VDRIVE"],
        [SENSE_UUID, "Sense"],
        [BEADS_UUID, "Magnetic Cores"],
        [CCS_UUID, "CCS X"],
        [CCS_Y_UUID, "CCS Y"],
        [CCS_I_UUID, "CCS INH"],
        [INH_UUID, "Inhibit"],
        [DEC_CTRL_UUID, "Decode CTRL"],
        [DEC_CTRL_Y_UUID, "Decode CTRL Y"],
    ]
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    print("Updated core.kicad_pro sheets")
    sch = ensure_three_ccs(SCH.read_text())
    SCH.write_text(sch)
    print("CCS X / CCS Y / CCS INH")


if __name__ == "__main__":
    main()
