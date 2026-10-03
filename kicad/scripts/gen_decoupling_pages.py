#!/usr/bin/env python3
"""Build Decoupling pages (logic + VDRIVE) for shared rails only.

Pages (global power nets — no hierarchical pins):
  decoupling_logic.kicad_sch  — +3V3 / +5V (Sense, Latch, CCS)
  decoupling_vdrive.kicad_sch — VDRIVE 100n+1u for Inhibit TC4427s

Drive Block / Decode Block carry their own per-IC bypass.

Also:
  - removes C1–C6 / C11–C14 from root
  - regenerates drive_block / decode_block (with local bypass)
  - places both sheets on root; updates .kicad_pro
"""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
SCH = CORE / "core.kicad_sch"
PRO = CORE / "core.kicad_pro"
LOGIC = CORE / "decoupling_logic.kicad_sch"
VDRIVE = CORE / "decoupling_vdrive.kicad_sch"
PROJECT = "core"

ROOT_UUID = "fabf9ba2-76e6-4325-a1a0-bc01b9516551"
LOGIC_UUID = "a1b2c3d4-e5f6-4789-a012-555555555555"
VDRIVE_UUID = "a1b2c3d4-e5f6-4789-a012-666666666666"
DRIVE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-111111111111"
DECODE_BLOCK_UUID = "a1b2c3d4-e5f6-4789-a012-333333333333"
SENSE_UUID = "a1b2c3d4-e5f6-4789-a012-777777777777"
CCS_UUID = "a1b2c3d4-e5f6-4789-a012-888888888888"
INH_UUID = "a1b2c3d4-e5f6-4789-a012-999999999999"
DEC_CTRL_UUID = "a1b2c3d4-e5f6-4789-a012-aaaaaaaaaaaa"
BEADS_UUID = "a1b2c3d4-e5f6-4789-a012-bbbbbbbbbbbb"

SHEET_ORDER = [
    (ROOT_UUID, "core"),
    (DRIVE_BLOCK_UUID, "Drive Block"),
    (DECODE_BLOCK_UUID, "Decode Block"),
    (LOGIC_UUID, "Decoupling Logic"),
    (VDRIVE_UUID, "Decoupling VDRIVE"),
    (SENSE_UUID, "Sense"),
    (BEADS_UUID, "Magnetic Cores"),
    (CCS_UUID, "CCS"),
    (INH_UUID, "Inhibit"),
    (DEC_CTRL_UUID, "Decode CTRL"),
]

FP_C = "Capacitor_SMD:C_0805_2012Metric"

# Caps removed from root when migrating to decoupling pages
ROOT_CAP_REFS = {f"C{n}" for n in (1, 2, 3, 4, 5, 6, 11, 12, 13, 14)}


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


def instances(ref: str, sheet_uuid: str) -> str:
    path = f"/{ROOT_UUID}/{sheet_uuid}"
    return f'''\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "{path}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, sheet_uuid, *, footprint=""):
    pins_s = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
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
{prop("Reference", ref, f"{x + 2.54} {y - 5.08} 0")}
{prop("Value", value, f"{x + 2.54} {y - 2.54} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
{pins_s}
{instances(ref, sheet_uuid)}
\t)'''


def power(lib_id, ref, value, x, y, sheet_uuid):
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
{instances(ref, sheet_uuid)}
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


def text(s, x, y, size=1.27):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def bypass_pair(
    o: list[str],
    *,
    sheet_uuid: str,
    rail_lib: str,
    rail_val: str,
    cref_lo: str,
    cref_hi: str,
    x: float,
    y: float,
    note: str,
) -> None:
    """One IC: 100n + 1u between rail and GND (no rail–GND short!)."""
    o.append(text(note, x - 5.08, y - 22.86, 1.016))
    rail_y = round(y - 15.24, 2)
    gnd_y = round(y + 15.24, 2)
    o.append(power(rail_lib, f"#PWR_{cref_lo}_V", rail_val, x, rail_y, sheet_uuid))
    o.append(power("power:GND", f"#PWR_{cref_lo}_G", "GND", x, gnd_y, sheet_uuid))
    top_j = (x, rail_y)
    bot_j = (x, gnd_y)
    for cref, cval, dx in ((cref_lo, "100n", -7.62), (cref_hi, "1u", 7.62)):
        cx = round(x + dx, 2)
        o.append(symbol_inst("Device:C", cref, cval, cx, y, ["1", "2"], sheet_uuid, footprint=FP_C))
        ct, cb = pin_xy(cx, y, 0, 3.81), pin_xy(cx, y, 0, -3.81)
        o += [
            wire(ct, (cx, rail_y)),
            wire((cx, rail_y), top_j),
            junction((cx, rail_y)),
            wire(cb, (cx, gnd_y)),
            wire((cx, gnd_y), bot_j),
            junction((cx, gnd_y)),
        ]
    o += [junction(top_j), junction(bot_j)]


def bypass_single_100n(
    o: list[str],
    *,
    sheet_uuid: str,
    cref: str,
    x: float,
    y: float,
    note: str,
) -> None:
    """Single 100n +3V3–GND (decoder ICs)."""
    o.append(text(note, x - 2.54, y - 17.78, 1.016))
    rail_y = round(y - 12.7, 2)
    gnd_y = round(y + 12.7, 2)
    o.append(power("power:+3V3", f"#PWR_{cref}_V", "+3V3", x, rail_y, sheet_uuid))
    o.append(power("power:GND", f"#PWR_{cref}_G", "GND", x, gnd_y, sheet_uuid))
    o.append(symbol_inst("Device:C", cref, "100n", x, y, ["1", "2"], sheet_uuid, footprint=FP_C))
    ct, cb = pin_xy(x, y, 0, 3.81), pin_xy(x, y, 0, -3.81)
    o += [
        wire(ct, (x, rail_y)),
        wire(cb, (x, gnd_y)),
    ]


def build_sch(title: str, comment: str, sheet_uuid: str, lib_syms: str, body: list[str]) -> str:
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{uid()}")
\t(paper "A3")
\t(title_block
\t\t(title "{title}")
\t\t(comment 1 "{comment}")
\t)
\t(lib_symbols
{lib_syms}
\t)
{chr(10).join(body)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def build_logic_page(lib_syms: str) -> str:
    o: list[str] = [
        text("Logic decoupling — +3V3 / +5V (shared Sense / Latch / CCS)", 20, 12, 1.524),
        text("Decode Block carries its own +3V3 100n per IC", 20, 18),
    ]
    # Sense + Latch + CCS
    bypass_pair(
        o, sheet_uuid=LOGIC_UUID, rail_lib="power:+3V3", rail_val="+3V3",
        cref_lo="C1", cref_hi="C2", x=40.0, y=50.0, note="Sense U1 (TLV3501)",
    )
    bypass_pair(
        o, sheet_uuid=LOGIC_UUID, rail_lib="power:+3V3", rail_val="+3V3",
        cref_lo="C3", cref_hi="C4", x=90.0, y=50.0, note="Latch U2 (74AHC74)",
    )
    bypass_pair(
        o, sheet_uuid=LOGIC_UUID, rail_lib="power:+5V", rail_val="+5V",
        cref_lo="C5", cref_hi="C6", x=140.0, y=50.0, note="CCS U3 (OPA192) +5V",
    )
    return build_sch(
        "Decoupling Logic",
        "+3V3 / +5V bypass for Sense / Latch / CCS",
        LOGIC_UUID,
        lib_syms,
        o,
    )


def build_vdrive_page(lib_syms: str) -> str:
    o: list[str] = [
        text("VDRIVE decoupling — Inhibit gate drivers", 20, 12, 1.524),
        text("Drive Block carries its own VDRIVE 100n+1u per TC4427", 20, 18),
    ]
    pairs = [
        ("C11", "C12", 40.0, 55.0, "Inhibit U7 (HS)"),
        ("C13", "C14", 100.0, 55.0, "Inhibit U8 (LS)"),
    ]
    for clo, chi, x, y, note in pairs:
        bypass_pair(
            o,
            sheet_uuid=VDRIVE_UUID,
            rail_lib="power:VDRIVE",
            rail_val="VDRIVE",
            cref_lo=clo,
            cref_hi=chi,
            x=x,
            y=y,
            note=note,
        )
    return build_sch(
        "Decoupling VDRIVE",
        "Inhibit gate-drive bypass on VDRIVE; Drive Block is self-contained",
        VDRIVE_UUID,
        lib_syms,
        o,
    )


def find_body_range(sch: str) -> tuple[int, int]:
    lib_start = sch.find("(lib_symbols")
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
            raise SystemExit(f"expected '(' at {i}")
        depth = 0
        j = i
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


def item_coords(item: str) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", item)] + [
        (float(x), float(y)) for x, y in re.findall(r"\(at ([-\d.]+) ([-\d.]+)", item)
    ]


def strip_root_caps(sch: str) -> tuple[str, int]:
    """Remove C1–C6 / C11–C14 symbols only (no proximity wire wipe)."""
    body_start, si = find_body_range(sch)
    items = extract_items(sch, body_start, si)

    kept = []
    dropped = 0
    for it in items:
        head = it.lstrip()[:30]
        if head.startswith("(symbol"):
            m = re.search(r'\(property "Reference" "([^"]+)"', it)
            if m and m.group(1) in ROOT_CAP_REFS:
                dropped += 1
                continue
            if m and any(
                m.group(1).startswith(f"#PWR_C{n}")
                for n in (1, 2, 3, 4, 5, 6, 11, 12, 13, 14)
            ):
                dropped += 1
                continue
        if head.startswith("(sheet") and (
            "decoupling_logic.kicad_sch" in it or "decoupling_vdrive.kicad_sch" in it
        ):
            dropped += 1
            continue
        kept.append(it)

    return sch[:body_start] + "\n".join(kept) + "\n" + sch[si:], dropped


def sheet_box(name: str, file: str, sheet_uuid: str, page: str, sx: float, sy: float) -> str:
    w, h = 50.0, 20.0
    return f'''\t(sheet
\t\t(at {sx} {sy})
\t\t(size {w} {h})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0)
\t\t)
\t\t(uuid "{sheet_uuid}")
\t\t(property "Sheetname" "{name}"
\t\t\t(at {sx} {sy - 1.27} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t(thickness 0.254)
\t\t\t\t\t(bold yes)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{file}"
\t\t\t(at {sx} {sy + h + 1.27} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")

    # Libs for pages
    needed_logic = ["Device:C", "power:+3V3", "power:+5V", "power:GND"]
    needed_vdrive = ["Device:C", "power:VDRIVE", "power:GND"]
    logic_libs = "\n".join(extract_lib(sch, n) for n in needed_logic)
    vdrive_libs = "\n".join(extract_lib(sch, n) for n in needed_vdrive)

    LOGIC.write_text(build_logic_page(logic_libs))
    VDRIVE.write_text(build_vdrive_page(vdrive_libs))
    print(f"Wrote {LOGIC.name}")
    print(f"Wrote {VDRIVE.name}")

    # Regen drive / decode blocks (each carries its own per-IC bypass)
    subprocess.check_call(["python3", str(ROOT / "scripts" / "gen_xy_drive_page.py")])
    subprocess.check_call(["python3", str(ROOT / "scripts" / "gen_xy_decode_page.py")])

    sch = SCH.read_text()
    sch, dropped = strip_root_caps(sch)
    print(f"Removed {dropped} root cap-related items")

    # Place decoupling sheets (idempotent strip already removed prior boxes)
    o = [
        text("Decoupling (global power) — caps off the signal pages", 20, 470, 1.524),
        sheet_box("Decoupling Logic", "decoupling_logic.kicad_sch", LOGIC_UUID, "4", 20.0, 480.0),
        sheet_box("Decoupling VDRIVE", "decoupling_vdrive.kicad_sch", VDRIVE_UUID, "5", 90.0, 480.0),
    ]
    marker = "\t(sheet_instances"
    if marker not in sch:
        marker = "(sheet_instances"
    sch = sch.replace(marker, "\n".join(o) + "\n" + marker, 1)
    SCH.write_text(sch)
    print(f"Updated {SCH}")

    pro = json.loads(PRO.read_text())
    pro["sheets"] = [[u, n] for u, n in SHEET_ORDER]
    PRO.write_text(json.dumps(pro, indent=2) + "\n")
    print("Updated core.kicad_pro sheets")


if __name__ == "__main__":
    main()
