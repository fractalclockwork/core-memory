#!/usr/bin/env python3
"""Append CCS (Ic/2 sink) block to core.kicad_sch without touching Sense."""
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
    # Nested unit names stay as Original_*; OK for KiCad
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
{prop("Reference", ref, f"{x + 3.81} {y - 2.54} 0")}
{prop("Value", value, f"{x + 3.81} {y} 0")}
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


def strip_stage2_instances(sch: str) -> str:
    """Remove prior CCS sheet objects (keep lib embeds)."""
    marker = "\t(sheet_instances"
    end = sch.find(marker)
    if end < 0:
        raise SystemExit("sheet_instances missing")
    # Prefer unique R7 placement; fall back to CCS / legacy STAGE 2 title
    starts = []
    for needle in (
        '\t(symbol\n\t\t(lib_id "Device:R")\n\t\t(at 40.64 122.0 0)',
        '\t(symbol\n\t\t(lib_id "Device:R")\n\t\t(at 40.64 130.0 0)',
        '\t(text "CCS —',
        '\t(text "STAGE 2',
    ):
        i = sch.find(needle)
        if 0 <= i < end:
            starts.append(i)
    if "CCS —" not in sch and "STAGE 2" not in sch and not starts:
        return sch
    if not starts:
        raise SystemExit("CCS block present but cannot locate instance block")
    start = min(starts)
    # Include any leading newline
    while start > 0 and sch[start - 1] == "\n":
        start -= 1
        break
    return sch[:start] + "\n" + sch[end:]


def main() -> None:
    sch = SCH.read_text()
    sch = strip_stage2_instances(sch)

    # --- ensure lib_symbols ---
    needed = {
        "Reference_Voltage:TL431LP": (KICAD / "Reference_Voltage.kicad_sym", "TL431LP"),
        "Device:R_Potentiometer_US": (KICAD / "Device.kicad_sym", "R_Potentiometer_US"),
        "Transistor_FET:IRLZ44N": (KICAD / "Transistor_FET.kicad_sym", "BUZ11"),  # resolve extends
        "core_memory:OPA192": (SYM_LIB, "OPA192"),
        "power:+5V": (KICAD / "power.kicad_sym", "+5V"),
    }
    embeds = []
    for lib_id, (path, src_name) in needed.items():
        if f'(symbol "{lib_id}"' in sch:
            continue
        body = extract(path, src_name)
        emb = embed_as(lib_id, body, src_name)
        if lib_id.endswith("IRLZ44N"):
            emb = emb.replace("BUZ11_", "IRLZ44N_")
        embeds.append(emb)

    if embeds:
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
        block = "\n".join(embeds) + "\n\t"
        sch = sch[:insert_at] + block + sch[insert_at:]

    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"
    FP_RS = "Resistor_SMD:R_2512_6332Metric"
    FP_POT = "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical"
    o: list[str] = []

    # ========== CCS region below Sense box (ends y=100.33) ==========
    y0 = 130.0

    # --- Reference: TL431 2.5V shunt + pot divider → VSET ---
    # Bias R above TL431 so cathode bus (y=K) never shares Y with GND bus.
    r7 = (40.64, 122.0)  # 1k cathode bias
    u4 = (55.88, y0)     # TL431
    rv1 = (85.09, y0)    # pot divider

    o.append(symbol_inst("Device:R", "R7", "1k", r7[0], r7[1], ["1", "2"], footprint=FP_R))
    o.append(symbol_inst("Reference_Voltage:TL431LP", "U4", "TL431LP", u4[0], u4[1], ["1", "2", "3"],
                         footprint="Package_TO_SOT_THT:TO-92_Inline"))
    o.append(symbol_inst("Device:R_Potentiometer_US", "RV1", "10k", rv1[0], rv1[1], ["1", "2", "3"],
                         footprint=FP_POT))

    r7t, r7b = pin_xy(r7[0], r7[1], 0, 3.81), pin_xy(r7[0], r7[1], 0, -3.81)
    # TL431LP: REF(0,2.54), A(-2.54,0), K(2.54,0)
    k = pin_xy(u4[0], u4[1], 2.54, 0)
    a = pin_xy(u4[0], u4[1], -2.54, 0)
    refp = pin_xy(u4[0], u4[1], 0, 2.54)
    # Pot: 1 top, 2 wiper, 3 bottom
    p1 = pin_xy(rv1[0], rv1[1], 0, 3.81)
    p2 = pin_xy(rv1[0], rv1[1], 3.81, 0)
    p3 = pin_xy(rv1[0], rv1[1], 0, -3.81)

    cath_y = k[1]  # horizontal cathode / VREF bus at TL431 pin height only
    gnd_y = round(p3[1] + 10.16, 2)  # GND bus well below pot bottom

    # +5V -> R7 top
    v5 = (r7[0], round(r7t[1] - 7.62, 2))
    o += [power("power:+5V", "#PWR_5V_CCS", "+5V", v5[0], v5[1]), wire(v5, r7t)]

    # R7 bottom -> cathode bus -> K
    o += [
        wire(r7b, (r7[0], cath_y)),
        wire((r7[0], cath_y), k),
        junction(k),
        junction((r7[0], cath_y)),
    ]
    # Shunt mode: REF tied to K (2.5V)
    o += [
        wire(refp, (k[0], refp[1])),
        wire((k[0], refp[1]), k),
        junction((k[0], refp[1])),
    ]
    # Cathode bus -> pot top (divider against TL431 output)
    o += [
        wire(k, (p1[0], cath_y)),
        wire((p1[0], cath_y), p1),
        junction((p1[0], cath_y)),
    ]
    # Anode + pot bottom -> GND bus (separate Y from cathode)
    o += [
        wire(a, (a[0], gnd_y)),
        wire(p3, (p3[0], gnd_y)),
        wire((a[0], gnd_y), (p3[0], gnd_y)),
        junction((a[0], gnd_y)),
        junction((p3[0], gnd_y)),
        power("power:GND", "#PWR_GND_CCS1", "GND", a[0], gnd_y),
    ]
    # Wiper = VSET
    o += [wire(p2, (round(p2[0] + 7.62, 2), p2[1])), label("VSET", (round(p2[0] + 7.62, 2), p2[1]))]

    # +5V PWR_FLAG
    o += [
        power("power:+5V", "#PWR_5V_MAIN", "+5V", 25.4, y0 - 15.24),
        power("power:PWR_FLAG", "#FLG_5V", "PWR_FLAG", 25.4, y0 - 5.08),
        wire((25.4, y0 - 15.24), (25.4, y0 - 5.08)),
    ]

    # --- OPA192 ---
    u3 = (160.0, y0)
    o.append(symbol_inst("core_memory:OPA192", "U3", "OPA192", u3[0], u3[1],
                         ["1", "2", "3", "4", "5", "6", "7", "8"],
                         footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"))
    up = pin_xy(u3[0], u3[1], -7.62, 2.54)
    um = pin_xy(u3[0], u3[1], -7.62, -2.54)
    uout = pin_xy(u3[0], u3[1], 7.62, 0)
    uvp = pin_xy(u3[0], u3[1], 0, 7.62)
    uvm = pin_xy(u3[0], u3[1], 0, -7.62)
    for lx, ly in ((-2.54, 7.62), (2.54, 7.62), (2.54, -7.62)):
        o.append(no_connect(pin_xy(u3[0], u3[1], lx, ly)))

    o += [wire(up, (round(up[0] - 5.08, 2), up[1])), label("VSET", (round(up[0] - 5.08, 2), up[1]), 180)]
    o += [wire(um, (round(um[0] - 5.08, 2), um[1])), label("ISENSE", (round(um[0] - 5.08, 2), um[1]), 180)]

    # Power + bypass to the RIGHT of OPA (avoid pot region)
    vp_j = (uvp[0], round(uvp[1] - 2.54, 2))
    vm_j = (uvm[0], round(uvm[1] + 2.54, 2))
    o += [
        wire(uvp, vp_j),
        wire(uvm, vm_j),
        power("power:+5V", "#PWR_U3V+", "+5V", vp_j[0], round(vp_j[1] - 7.62, 2)),
        wire(vp_j, (vp_j[0], round(vp_j[1] - 7.62, 2))),
        power("power:GND", "#PWR_U3V-", "GND", vm_j[0], round(vm_j[1] + 7.62, 2)),
        wire(vm_j, (vm_j[0], round(vm_j[1] + 7.62, 2))),
        junction(vp_j),
        junction(vm_j),
    ]
    for cref, val, cx in (("C5", "100n", round(u3[0] + 20.32, 2)), ("C6", "1u", round(u3[0] + 35.56, 2))):
        cy = round((vp_j[1] + vm_j[1]) / 2, 2)
        o.append(symbol_inst("Device:C", cref, val, cx, cy, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
        o += [
            wire(ct, (cx, vp_j[1])), wire((cx, vp_j[1]), vp_j), junction((cx, vp_j[1])),
            wire(cb, (cx, vm_j[1])), wire((cx, vm_j[1]), vm_j), junction((cx, vm_j[1])),
        ]

    # Gate resistor R8 100Ω (horizontal between OPA out and FET gate)
    r8 = (round(uout[0] + 25.4, 2), y0)
    o.append(symbol_inst("Device:R", "R8", "100", r8[0], r8[1], ["1", "2"], rot=90, footprint=FP_R))
    r8l, r8r = pin_xy(r8[0], r8[1], 0, 3.81, 90), pin_xy(r8[0], r8[1], 0, -3.81, 90)
    o += [wire(uout, (r8l[0], uout[1])), wire((r8l[0], uout[1]), r8l)]

    # --- IRLZ44N + sense R ---
    q1 = (240.0, y0)
    o.append(symbol_inst("Transistor_FET:IRLZ44N", "Q1", "IRLZ44N", q1[0], q1[1], ["1", "2", "3"],
                         footprint="Package_TO_SOT_THT:TO-220-3_Vertical"))
    g = pin_xy(q1[0], q1[1], -5.08, 0)
    d = pin_xy(q1[0], q1[1], 2.54, 5.08)
    s = pin_xy(q1[0], q1[1], 2.54, -5.08)
    o += [wire(r8r, (r8r[0], g[1])), wire((r8r[0], g[1]), g)]

    o += [wire(d, (round(d[0] + 10.16, 2), d[1])), label("CCS_RET", (round(d[0] + 10.16, 2), d[1]))]

    r9 = (round(s[0] + 20.32, 2), round(s[1] + 12.7, 2))
    o.append(symbol_inst("Device:R", "R9", "1", r9[0], r9[1], ["1", "2"], footprint=FP_RS))
    r9t, r9b = pin_xy(r9[0], r9[1], 0, 3.81), pin_xy(r9[0], r9[1], 0, -3.81)
    isense = (r9t[0], s[1])
    o += [
        wire(s, isense),
        wire(isense, r9t),
        junction(isense),
        label("ISENSE", (round(isense[0] - 10.16, 2), isense[1]), 180),
        wire(isense, (round(isense[0] - 10.16, 2), isense[1])),
    ]
    o += [
        wire(r9b, (r9b[0], round(r9b[1] + 5.08, 2))),
        power("power:GND", "#PWR_GND_CCS2", "GND", r9b[0], round(r9b[1] + 5.08, 2)),
    ]
    tp = (round(isense[0] + 12.7, 2), isense[1])
    o.append(symbol_inst("Connector:TestPoint", "TP2", "Isense", tp[0], tp[1], ["1"],
                         footprint="TestPoint:TestPoint_Pad_D1.5mm"))
    o.append(wire(isense, tp))
    o.append(junction(isense))

    o += [
        f'''\t(rectangle
\t\t(start 12.70 112.00)
\t\t(end 300.00 200.00)
\t\t(stroke (width 0.254) (type dot))
\t\t(fill (type none))
\t\t(uuid "{uid()}")
\t)''',
        text("CCS — Ic/2 sink", 15.24, 115.0, 1.524),
        text(
            "TL431 2.5V + pot divider → VSET; OPA192 drives IRLZ44N via R8; R9=1Ω; CCS_RET → Drive FWD/REV + Inhibit",
            15.24, 195.0,
        ),
    ]

    marker = "\t(sheet_instances"
    if marker not in sch:
        raise SystemExit("sheet_instances missing")
    sch = sch.replace(marker, "\n".join(o) + "\n" + marker, 1)
    SCH.write_text(sch)
    print(f"Appended CCS block to {SCH}")


if __name__ == "__main__":
    main()
