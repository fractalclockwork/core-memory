#!/usr/bin/env python3
"""Append Stage 6 reverse WRITE X0/Y0 drive without touching Stages 1–5."""
from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
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
{prop("Reference", ref, f"{x + 2.54} {y - 10.16} 0")}
{prop("Value", value, f"{x + 2.54} {y - 7.62} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True)}
{prop("Description", "", f"{x} {y} 0", hide=True)}
{pins_s}
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{ref}") (unit {unit}))))
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


def strip_stage6(sch: str) -> str:
    marker = "\t(sheet_instances"
    end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing")
    if "STAGE 6" not in sch and '(property "Reference" "Q5"' not in sch:
        return sch
    starts = []
    for needle in (
        '\t(text "STAGE 6',
        '\t(rectangle\n\t\t(start 540.00',
        '(property "Reference" "Q5"',
        '(property "Reference" "Q6"',
    ):
        i = sch.find(needle)
        if needle.startswith("(property") and i > 0:
            i = sch.rfind("\t(symbol\n", 0, i)
        if 0 <= i < end:
            starts.append(i)
    if not starts:
        raise SystemExit("STAGE 6 present but cannot locate block")
    start = min(starts)
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def half_bridge_rev(
    o: list[str],
    *,
    qref: str,
    d_hs: str,
    d_ls: str,
    qx: float,
    qy: float,
    plane_hs: str,
    plane_ls: str,
    g_hs: str,
    g_ls: str,
) -> None:
    """Reverse polarity: HS steers to plane_hs (XB/YB), LS from plane_ls (XA/YA)."""
    FP_Q = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    FP_D = "Diode_SMD:D_SMA"

    o.append(
        symbol_inst(
            "core_memory:FDS8958A",
            qref,
            "FDS8958A",
            qx,
            qy,
            ["1", "2", "3", "4", "5", "6", "7", "8"],
            footprint=FP_Q,
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

    # HS diode: D1 → A → K → plane_hs (XB0 / YB0)
    dx = round(qx + 35.56, 2)
    dy_hs = round((d1_7[1] + d1_8[1]) / 2, 2)
    o.append(symbol_inst("Diode:SS14", d_hs, "SS14", dx, dy_hs, ["1", "2"], rot=180, footprint=FP_D))
    k_hs = pin_xy(dx, dy_hs, -3.81, 0, 180)
    a_hs = pin_xy(dx, dy_hs, 3.81, 0, 180)
    mid_d1 = (round(qx + 20.32, 2), dy_hs)
    o += [
        wire(d1_7, (d1_7[0], dy_hs)),
        wire((d1_7[0], dy_hs), mid_d1),
        wire(mid_d1, a_hs),
        junction((d1_7[0], dy_hs)),
        junction(mid_d1),
    ]
    la = (round(k_hs[0] + 12.7, 2), k_hs[1])
    o += [wire(k_hs, la), label(plane_hs, la)]

    # LS diode: plane_ls → A → K → D2 (XA0 / YA0)
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
    o += [wire(a_ls, lb), label(plane_ls, lb)]

    o += [
        wire(g1, (round(g1[0] - 10.16, 2), g1[1])),
        label(g_hs, (round(g1[0] - 10.16, 2), g1[1]), 180),
        wire(g2, (round(g2[0] - 10.16, 2), g2[1])),
        label(g_ls, (round(g2[0] - 10.16, 2), g2[1]), 180),
        wire(s1, (round(s1[0] - 10.16, 2), s1[1])),
        label("VDRIVE", (round(s1[0] - 10.16, 2), s1[1]), 180),
        wire(s2, (round(s2[0] - 10.16, 2), s2[1])),
        label("CCS_RET", (round(s2[0] - 10.16, 2), s2[1]), 180),
    ]


def main() -> None:
    sch = SCH.read_text()
    if "sheet_instances" not in sch:
        raise SystemExit("schematic truncated — abort")
    sch = strip_stage6(sch)

    o: list[str] = []

    # Right of Stage 3 (ends ~x=527)
    half_bridge_rev(
        o,
        qref="Q5",
        d_hs="D7",
        d_ls="D8",
        qx=600.0,
        qy=37.30,
        plane_hs="XB0",
        plane_ls="XA0",
        g_hs="X_HS0r",
        g_ls="X_LS0r",
    )
    half_bridge_rev(
        o,
        qref="Q6",
        d_hs="D9",
        d_ls="D10",
        qx=600.0,
        qy=58.42,
        plane_hs="YB0",
        plane_ls="YA0",
        g_hs="Y_HS0r",
        g_ls="Y_LS0r",
    )

    o += [
        f'''\t(rectangle
\t\t(start 540.00 15.00)
\t\t(end 780.00 100.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("STAGE 6 — X/Y reverse WRITE drive", 545.0, 20.0, 1.524),
        text(
            "QX0r/QY0r FDS8958A + SS14 swapped ends (HS→XB0/YB0, LS←XA0/YA0); LS→CCS_RET; gates for Stage 7",
            545.0,
            95.0,
        ),
    ]

    sch = sch.replace("\t(sheet_instances", "\n".join(o) + "\n\t(sheet_instances", 1)
    SCH.write_text(sch)
    print(f"Appended Stage 6 reverse drive to {SCH}")


if __name__ == "__main__":
    main()
