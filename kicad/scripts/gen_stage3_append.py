#!/usr/bin/env python3
"""Append Stage 3 X/Y forward drive to core.kicad_sch without touching Stages 1–2."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
SYM_LIB = ROOT / "libs" / "core_memory.kicad_sym"
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


def symbol_inst(lib_id, ref, value, x, y, pins, *, unit=1, rot=0, dnp=False, footprint=""):
    pins_s = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit {unit})
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {"no" if dnp else "yes"})
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp {"yes" if dnp else "no"})
\t\t(uuid "{uid()}")
{prop("Reference", ref, f"{x + 2.54} {y - 10.16} 0")}
{prop("Value", value, f"{x + 2.54} {y - 7.62} 0")}
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


def text(s, x, y, size=1.27):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def strip_stage3_instances(sch: str) -> str:
    marker = "\t(sheet_instances"
    end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing")
    if "STAGE 3" not in sch and '(property "Reference" "Q2"' not in sch:
        return sch
    starts = []
    for needle in (
        '\t(symbol\n\t\t(lib_id "core_memory:FDS8958A")\n\t\t(at 420.0',
        '\t(text "STAGE 3',
        '\t(rectangle\n\t\t(start 370.00',
    ):
        i = sch.find(needle)
        if 0 <= i < end:
            starts.append(i)
    # also match Q2 wherever Stage 3 put it
    i = sch.find('(property "Reference" "Q2"')
    if i > 0:
        sym = sch.rfind("\t(symbol\n", 0, i)
        if 0 <= sym < end:
            starts.append(sym)
    if not starts:
        raise SystemExit("STAGE 3 present but cannot locate instance block")
    start = min(starts)
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def ensure_lib(sch: str) -> str:
    """Embed FDS8958A, SS14 (from SB120), power:VDRIVE if missing."""
    needed: list[tuple[str, Path, str, dict | None]] = [
        ("core_memory:FDS8958A", SYM_LIB, "FDS8958A", None),
        ("Diode:SS14", KICAD / "Diode.kicad_sym", "SB120", {"rename_nested": ("SB120_", "SS14_")}),
        ("power:VDRIVE", KICAD / "power.kicad_sym", "+12V", {"power_rename": ("+12V", "VDRIVE")}),
    ]
    embeds = []
    for lib_id, path, src_name, opts in needed:
        if f'(symbol "{lib_id}"' in sch:
            continue
        body = extract(path, src_name)
        emb = embed_as(lib_id, body, src_name)
        if opts and "rename_nested" in opts:
            a, b = opts["rename_nested"]
            emb = emb.replace(a, b)
        if opts and "power_rename" in opts:
            old, new = opts["power_rename"]
            emb = emb.replace(f'+12V_', "VDRIVE_")
            emb = emb.replace('(property "Value" "+12V"', f'(property "Value" "{new}"')
            # power global net follows Value on instances; lib default Value set above
        embeds.append(emb)
    if not embeds:
        return sch
    m = re.search(r"\t\(lib_symbols\n", sch)
    if not m:
        raise SystemExit("no lib_symbols")
    start = m.end()
    depth = 1
    i = start
    while i < len(sch) and depth:
        if sch[i] == "(":
            depth += 1
        elif sch[i] == ")":
            depth -= 1
        i += 1
    insert_at = i - 1
    return sch[:insert_at] + "\n".join(embeds) + "\n\t" + sch[insert_at:]


def half_bridge(o: list[str], *, qref: str, d_hs: str, d_ls: str, qx: float, qy: float,
                plane_a: str, plane_b: str, g_hs: str, g_ls: str) -> None:
    """One FDS8958A + two SS14 steering diodes + labels."""
    FP_Q = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    FP_D = "Diode_SMD:D_SMA"

    o.append(symbol_inst("core_memory:FDS8958A", qref, "FDS8958A", qx, qy,
                         ["1", "2", "3", "4", "5", "6", "7", "8"], footprint=FP_Q))

    s1 = pin_xy(qx, qy, -10.16, 5.08)
    g1 = pin_xy(qx, qy, -10.16, 2.54)
    s2 = pin_xy(qx, qy, -10.16, -2.54)
    g2 = pin_xy(qx, qy, -10.16, -5.08)
    d2_5 = pin_xy(qx, qy, 10.16, -5.08)
    d2_6 = pin_xy(qx, qy, 10.16, -2.54)
    d1_7 = pin_xy(qx, qy, 10.16, 2.54)
    d1_8 = pin_xy(qx, qy, 10.16, 5.08)

    # Tie dual drain pins
    o += [wire(d1_7, d1_8), junction(d1_7), junction(d1_8)]
    o += [wire(d2_5, d2_6), junction(d2_5), junction(d2_6)]

    # --- HS diode: D1 → A → K → plane_a (rot 180: A left, K right) ---
    dx = round(qx + 35.56, 2)
    dy_hs = round((d1_7[1] + d1_8[1]) / 2, 2)
    o.append(symbol_inst("Diode:SS14", d_hs, "SS14", dx, dy_hs, ["1", "2"], rot=180, footprint=FP_D))
    # rot180: K lib(-3.81,0)->(dx+3.81,dy), A lib(3.81,0)->(dx-3.81,dy)
    k_hs = pin_xy(dx, dy_hs, -3.81, 0, 180)
    a_hs = pin_xy(dx, dy_hs, 3.81, 0, 180)
    # D1 node to anode
    mid_d1 = (round(qx + 20.32, 2), dy_hs)
    o += [
        wire(d1_7, (d1_7[0], dy_hs)),
        wire((d1_7[0], dy_hs), mid_d1),
        wire(mid_d1, a_hs),
        junction((d1_7[0], dy_hs)),
        junction(mid_d1),
    ]
    # Cathode to plane label
    la = (round(k_hs[0] + 12.7, 2), k_hs[1])
    o += [wire(k_hs, la), label(plane_a, la)]

    # --- LS diode: plane_b → A → K → D2 (rot 0: K left, A right) ---
    dy_ls = round((d2_5[1] + d2_6[1]) / 2, 2)
    o.append(symbol_inst("Diode:SS14", d_ls, "SS14", dx, dy_ls, ["1", "2"], rot=0, footprint=FP_D))
    k_ls = pin_xy(dx, dy_ls, -3.81, 0, 0)
    a_ls = pin_xy(dx, dy_ls, 3.81, 0, 0)
    mid_d2 = (round(qx + 20.32, 2), dy_ls)
    o += [
        wire(d2_6, (d2_6[0], dy_ls)),
        wire((d2_6[0], dy_ls), mid_d2),
        wire(mid_d2, k_ls),
        junction((d2_6[0], dy_ls)),
        junction(mid_d2),
    ]
    lb = (round(a_ls[0] + 12.7, 2), a_ls[1])
    o += [wire(a_ls, lb), label(plane_b, lb)]

    # --- Gates (left) ---
    o += [
        wire(g1, (round(g1[0] - 10.16, 2), g1[1])),
        label(g_hs, (round(g1[0] - 10.16, 2), g1[1]), 180),
        wire(g2, (round(g2[0] - 10.16, 2), g2[1])),
        label(g_ls, (round(g2[0] - 10.16, 2), g2[1]), 180),
    ]

    # --- S1 ← VDRIVE label (power symbols placed once globally) ---
    o += [
        wire(s1, (round(s1[0] - 10.16, 2), s1[1])),
        label("VDRIVE", (round(s1[0] - 10.16, 2), s1[1]), 180),
    ]

    # --- S2 → CCS_RET ---
    o += [
        wire(s2, (round(s2[0] - 10.16, 2), s2[1])),
        label("CCS_RET", (round(s2[0] - 10.16, 2), s2[1]), 180),
    ]


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")
    sch = strip_stage3_instances(sch)
    sch = ensure_lib(sch)

    o: list[str] = []

    # Stage 3 region: right of Stage 1 (ends x≈355)
    # QX upper, QY lower — spaced for hand moves
    half_bridge(
        o, qref="Q2", d_hs="D3", d_ls="D4", qx=450.0, qy=50.0,
        plane_a="XA0", plane_b="XB0", g_hs="X_HS0", g_ls="X_LS0",
    )
    half_bridge(
        o, qref="Q3", d_hs="D5", d_ls="D6", qx=450.0, qy=140.0,
        plane_a="YA0", plane_b="YB0", g_hs="Y_HS0", g_ls="Y_LS0",
    )

    # VDRIVE rail + PWR_FLAG (vertical stack), left of QX
    vdx, vdy = 390.0, 30.0
    o += [
        power("power:VDRIVE", "#PWR_VDRIVE", "VDRIVE", vdx, vdy),
        power("power:PWR_FLAG", "#FLG_VDRIVE", "PWR_FLAG", vdx, round(vdy + 10.16, 2)),
        wire((vdx, vdy), (vdx, round(vdy + 10.16, 2))),
        # Tie power symbol into VDRIVE label net via short stub + label
        wire((vdx, vdy), (round(vdx + 7.62, 2), vdy)),
        label("VDRIVE", (round(vdx + 7.62, 2), vdy)),
    ]

    o += [
        f'''\t(rectangle
\t\t(start 370.00 15.00)
\t\t(end 720.00 200.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("STAGE 3 — X/Y forward drive", 375.0, 20.0, 1.524),
        text(
            "QX/QY FDS8958A + SS14 → XA0/XB0 & YA0/YB0; LS → CCS_RET; gates labeled for Stage 4",
            375.0, 195.0,
        ),
    ]

    marker = "\t(sheet_instances"
    sch = sch.replace(marker, "\n".join(o) + "\n" + marker, 1)
    SCH.write_text(sch)
    print(f"Appended Stage 3 drive to {SCH}")


if __name__ == "__main__":
    main()
