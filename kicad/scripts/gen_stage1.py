#!/usr/bin/env python3
"""Stage-1 bowtie + sense schematic — label-heavy to avoid wire-crossing shorts."""
from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "core" / "core.kicad_sch"
SYM_LIB = ROOT / "libs" / "core_memory.kicad_sym"
KICAD_SYMS = Path("/usr/share/kicad/symbols")
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


def extract_symbol(lib_path: Path, name: str) -> str:
    text = lib_path.read_text()
    needle = f'(symbol "{name}"'
    start = text.find(needle)
    if start < 0:
        raise KeyError(name)
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


def embed(lib_id: str, body: str) -> str:
    lib_name = lib_id.split(":", 1)[1]
    body = body.replace(f'(symbol "{lib_name}"', f'(symbol "{lib_id}"', 1)
    return "\n".join("\t\t" + line if line else line for line in body.splitlines())


CORE_BEAD = r'''	(symbol "CoreBead_3W"
		(pin_names (offset 1.016))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(in_pos_files yes)
		(duplicate_pin_numbers_are_jumpers no)
		(property "Reference" "FB" (at 0 8.89 0) (effects (font (size 1.27 1.27))))
		(property "Value" "CoreBead_3W" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "Inductor_SMD:L_1206_3216Metric" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Description" "Three isolated windings (X/Y/Sense) ferrite bead for bowtie core model" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "ki_keywords" "ferrite bead core memory bowtie" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "CoreBead_3W_0_1"
			(rectangle (start -5.08 6.35) (end 5.08 -6.35) (stroke (width 0.254) (type default)) (fill (type background)))
			(polyline (pts (xy -3.81 5.08) (xy -2.54 5.08) (xy -1.905 5.715) (xy -0.635 4.445) (xy 0.635 5.715) (xy 1.905 4.445) (xy 2.54 5.08) (xy 3.81 5.08)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy -3.81 0) (xy -2.54 0) (xy -1.905 0.635) (xy -0.635 -0.635) (xy 0.635 0.635) (xy 1.905 -0.635) (xy 2.54 0) (xy 3.81 0)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy -3.81 -5.08) (xy -2.54 -5.08) (xy -1.905 -4.445) (xy -0.635 -5.715) (xy 0.635 -4.445) (xy 1.905 -5.715) (xy 2.54 -5.08) (xy 3.81 -5.08)) (stroke (width 0) (type default)) (fill (type none)))
			(text "X" (at 0 6.985 0) (effects (font (size 1.016 1.016))))
			(text "Y" (at 0 1.905 0) (effects (font (size 1.016 1.016))))
			(text "S" (at 0 -3.175 0) (effects (font (size 1.016 1.016))))
		)
		(symbol "CoreBead_3W_1_1"
			(pin passive line (at -7.62 5.08 0) (length 2.54) (name "X1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 5.08 180) (length 2.54) (name "X2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -7.62 0 0) (length 2.54) (name "Y1" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 0 180) (length 2.54) (name "Y2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -7.62 -5.08 0) (length 2.54) (name "S1" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 -5.08 180) (length 2.54) (name "S2" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
		)
		(embedded_fonts no)
	)
'''


def ensure_core_bead() -> None:
    text = SYM_LIB.read_text()
    if '(symbol "CoreBead_3W"' not in text:
        SYM_LIB.write_text(text.rstrip()[:-1] + "\n" + CORE_BEAD + ")\n")


def prop(name: str, value: str, at: str, hide: bool = False, justify: str | None = "left") -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    just = f"\n\t\t\t\t(justify {justify})" if justify else ""
    return f'''\t\t(property "{name}" "{value}"
\t\t\t(at {at}){hide_s}
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)){just})
\t\t)'''


def symbol_inst(lib_id, ref, value, x, y, pins, *, unit=1, rot=0, dnp=False, footprint=""):
    pin_block = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
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
{prop("Reference", ref, f"{x + 2.54} {y - 2.54} 0")}
{prop("Value", value, f"{x + 2.54} {y} 0")}
{prop("Footprint", footprint, f"{x} {y} 0", hide=True, justify=None)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True, justify=None)}
{prop("Description", "", f"{x} {y} 0", hide=True, justify=None)}
{pin_block}
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
{prop("Reference", ref, f"{x} {y + 2.54} 0", hide=True, justify=None)}
{prop("Value", value, f"{x} {y + 5.08} 0", justify=None)}
{prop("Footprint", "", f"{x} {y} 0", hide=True, justify=None)}
{prop("Datasheet", "", f"{x} {y} 0", hide=True, justify=None)}
{prop("Description", "", f"{x} {y} 0", hide=True, justify=None)}
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


def global_label(name, p, rot=0, shape="input"):
    return f'''\t(global_label "{name}"
\t\t(shape {shape})
\t\t(at {p[0]} {p[1]} {rot})
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def no_connect(p):
    return f'''\t(no_connect
\t\t(at {p[0]} {p[1]})
\t\t(uuid "{uid()}")
\t)'''


def text(s, x, y):
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t)'''


def stub_label(name, pin, *, rot=0, dx=0.0, dy=0.0):
    """Short wire from pin to a local label — no long routes."""
    end = (round(pin[0] + dx, 2), round(pin[1] + dy, 2))
    return [wire(pin, end), label(name, end, rot)]


def stub_gnd(pin, ref, *, dy=7.62):
    """GND below pin (vertical)."""
    end = (pin[0], round(pin[1] + dy, 2))
    return [wire(pin, end), power("power:GND", ref, "GND", end[0], end[1])]


def stub_v3(pin, ref, *, dy=-7.62):
    """+3V3 above pin (vertical)."""
    end = (pin[0], round(pin[1] + dy, 2))
    return [wire(pin, end), power("power:+3V3", ref, "+3V3", end[0], end[1])]


def pwr_flag_below(net_pt, ref, *, gap=7.62):
    """PWR_FLAG on same X, below the net attachment point."""
    fy = round(net_pt[1] + gap, 2)
    return [
        power("power:PWR_FLAG", ref, "PWR_FLAG", net_pt[0], fy),
        wire(net_pt, (net_pt[0], fy)),
    ]


def pwr_flag_above(net_pt, ref, *, gap=7.62):
    """PWR_FLAG on same X, above the net attachment point."""
    fy = round(net_pt[1] - gap, 2)
    return [
        power("power:PWR_FLAG", ref, "PWR_FLAG", net_pt[0], fy),
        wire((net_pt[0], fy), net_pt),
    ]


def main() -> None:
    ensure_core_bead()
    extracts = {
        "Device:R": extract_symbol(KICAD_SYMS / "Device.kicad_sym", "R"),
        "Device:C": extract_symbol(KICAD_SYMS / "Device.kicad_sym", "C"),
        "Diode:BAT54S": extract_symbol(KICAD_SYMS / "Diode.kicad_sym", "BAT54S"),
        "Comparator:TLV3501AID": extract_symbol(KICAD_SYMS / "Comparator.kicad_sym", "TLV3501AID"),
        "74xx:74LS74": extract_symbol(KICAD_SYMS / "74xx.kicad_sym", "74LS74"),
        "Connector:TestPoint": extract_symbol(KICAD_SYMS / "Connector.kicad_sym", "TestPoint"),
        "power:+3V3": extract_symbol(KICAD_SYMS / "power.kicad_sym", "+3V3"),
        "power:GND": extract_symbol(KICAD_SYMS / "power.kicad_sym", "GND"),
        "power:PWR_FLAG": extract_symbol(KICAD_SYMS / "power.kicad_sym", "PWR_FLAG"),
        "core_memory:CoreBead_3W": extract_symbol(SYM_LIB, "CoreBead_3W"),
    }
    lib_syms = "\n".join(embed(k, v) for k, v in extracts.items())
    o: list[str] = []
    FP_R = "Resistor_SMD:R_0805_2012Metric"
    FP_C = "Capacitor_SMD:C_0805_2012Metric"
    FP_FB = "Inductor_SMD:L_1206_3216Metric"

    # ========== BOWTIE (left) ==========
    ax, ay = 63.5, 80.0
    bx, by = 114.3, 80.0
    o += [
        symbol_inst("core_memory:CoreBead_3W", "FB1", "FB_A", ax, ay, list("123456"), footprint=FP_FB),
        symbol_inst("core_memory:CoreBead_3W", "FB2", "FB_B", bx, by, list("123456"), footprint=FP_FB),
    ]
    a = {n: pin_xy(ax, ay, x, y) for n, x, y in [
        ("x1", -7.62, 5.08), ("x2", 7.62, 5.08), ("y1", -7.62, 0), ("y2", 7.62, 0),
        ("s1", -7.62, -5.08), ("s2", 7.62, -5.08)]}
    b = {n: pin_xy(bx, by, x, y) for n, x, y in [
        ("x1", -7.62, 5.08), ("x2", 7.62, 5.08), ("y1", -7.62, 0), ("y2", 7.62, 0),
        ("s1", -7.62, -5.08), ("s2", 7.62, -5.08)]}

    o += [wire(a["x2"], b["x1"]), wire(a["y2"], b["y1"])]
    mid = (round((a["s2"][0] + b["s1"][0]) / 2, 2), a["s2"][1])
    o += [wire(a["s2"], mid), wire(mid, b["s1"]), junction(mid), label("YA65_66", mid)]

    # Soft mid 10k → AGND (flag stacked vertically below AGND)
    r1 = (mid[0], mid[1] + 20.32)
    o.append(symbol_inst("Device:R", "R1", "10k", r1[0], r1[1], ["1", "2"], footprint=FP_R))
    r1t, r1b = pin_xy(r1[0], r1[1], 0, 3.81), pin_xy(r1[0], r1[1], 0, -3.81)
    o += [wire(mid, r1t), wire(r1b, (r1b[0], r1b[1] + 5.08))]
    ag = (r1b[0], r1b[1] + 5.08)
    o += [power("power:GND", "#PWR_AGND", "AGND", ag[0], ag[1])]
    o += pwr_flag_below(ag, "#FLG_AGND", gap=10.16)

    # Terminal labels (stubs only)
    for name, pin, rot, dx in [
        ("XA0", a["x1"], 180, -7.62), ("YA0", a["y1"], 180, -7.62), ("YB65", a["s1"], 180, -7.62),
        ("XB0", b["x2"], 0, 7.62), ("YB0", b["y2"], 0, 7.62), ("YB66", b["s2"], 0, 7.62),
    ]:
        o += stub_label(name, pin, rot=rot, dx=dx)

    # R_term DNP across YB65–YB66 via labels (local wires into R only)
    r2 = (mid[0], mid[1] + 30.48)
    o.append(symbol_inst("Device:R", "R2", "DNP", r2[0], r2[1], ["1", "2"], rot=90, dnp=True, footprint=FP_R))
    r2l, r2r = pin_xy(r2[0], r2[1], 0, 3.81, 90), pin_xy(r2[0], r2[1], 0, -3.81, 90)
    o += stub_label("YB65", r2l, rot=180, dx=-2.54)
    o += stub_label("YB66", r2r, rot=0, dx=2.54)

    # ========== SENSE ISO + CLAMPS (center) — components spaced for hand-move ==========
    # Iso Rs well left of clamps; clamps spaced vertically so each is independently selectable
    r3 = (152.4, 45.72)
    r4 = (152.4, 101.6)
    o.append(symbol_inst("Device:R", "R3", "1k", r3[0], r3[1], ["1", "2"], rot=90, footprint=FP_R))
    o.append(symbol_inst("Device:R", "R4", "1k", r4[0], r4[1], ["1", "2"], rot=90, footprint=FP_R))
    r3l, r3r = pin_xy(r3[0], r3[1], 0, 3.81, 90), pin_xy(r3[0], r3[1], 0, -3.81, 90)
    r4l, r4r = pin_xy(r4[0], r4[1], 0, 3.81, 90), pin_xy(r4[0], r4[1], 0, -3.81, 90)
    o += stub_label("YB65", r3l, rot=180, dx=-5.08)
    o += stub_label("SENSE_P", r3r, rot=0, dx=5.08)
    o += stub_label("YB66", r4l, rot=180, dx=-5.08)
    o += stub_label("SENSE_N", r4r, rot=0, dx=5.08)

    # BAT54S rotated 90°: K (top)→+3V3, A (bottom)→GND, COM (right)→sense
    # Each clamp is its own vertical stack, physically clear of the other
    for ref, sense_name, dy in (("D1", "SENSE_P", 45.72), ("D2", "SENSE_N", 101.6)):
        dx = 190.5
        o.append(symbol_inst(
            "Diode:BAT54S", ref, "BAT54S", dx, dy, ["1", "2", "3"],
            rot=90, footprint="Package_TO_SOT_SMD:SOT-23",
        ))
        a_pin = pin_xy(dx, dy, -7.62, 0, 90)   # bottom → GND
        k_pin = pin_xy(dx, dy, 7.62, 0, 90)    # top → +3V3
        com = pin_xy(dx, dy, 0, -5.08, 90)     # right → sense
        # Sense stub from COM further right (clear of body)
        o += stub_label(sense_name, com, rot=0, dx=5.08)
        # Vertical +3V3 above K, GND below A (same X as diode)
        o += stub_v3(k_pin, f"#PWR_{ref}K", dy=-7.62)
        o += stub_gnd(a_pin, f"#PWR_{ref}A", dy=7.62)

    # ========== TLV3501 + FF — spaced so each block can be grabbed/moved ==========
    ux, uy = 228.6, 70.0
    fx, fy = 304.8, 70.0
    o.append(symbol_inst("Comparator:TLV3501AID", "U1", "TLV3501AID", ux, uy, list("12345678"),
                         footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"))
    o.append(symbol_inst("74xx:74LS74", "U2", "74AHC74", fx, fy, ["1", "2", "3", "4", "5", "6"], unit=1,
                         footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"))

    u_m = pin_xy(ux, uy, -7.62, -2.54)
    u_p = pin_xy(ux, uy, -7.62, 2.54)
    u_out = pin_xy(ux, uy, 7.62, 0)
    u_vp = pin_xy(ux, uy, -2.54, 7.62)
    u_vm = pin_xy(ux, uy, -2.54, -7.62)
    u_shdn = pin_xy(ux, uy, 0, -7.62)
    f_d = pin_xy(fx, fy, -7.62, 2.54)
    f_c = pin_xy(fx, fy, -7.62, 0)
    f_q = pin_xy(fx, fy, 7.62, 2.54)
    f_qn = pin_xy(fx, fy, 7.62, -2.54)
    f_s = pin_xy(fx, fy, 0, 7.62)
    f_r = pin_xy(fx, fy, 0, -7.62)

    o += stub_label("SENSE_P", u_p, rot=180, dx=-5.08)
    o += stub_label("SENSE_N", u_m, rot=180, dx=-5.08)

    # Direct CMP_OUT: U1.OUT → U2.D (visible wire, not label-only)
    mid_x = round((u_out[0] + f_d[0]) / 2, 2)
    o += [
        wire(u_out, (mid_x, u_out[1])),
        junction(u_out),
        wire((mid_x, u_out[1]), (mid_x, f_d[1])),
        wire((mid_x, f_d[1]), f_d),
        label("CMP_OUT", (mid_x, u_out[1])),
    ]

    # U1 power rails + C1/C2 tied directly to V+/V− pins
    vp_j = (u_vp[0], round(u_vp[1] - 2.54, 2))   # junction above V+
    vm_j = (u_vm[0], round(u_vm[1] + 2.54, 2))   # junction below V−
    o += [
        wire(u_vp, vp_j),
        wire(u_vm, vm_j),
        power("power:+3V3", "#PWR_U1V+", "+3V3", vp_j[0], round(vp_j[1] - 5.08, 2)),
        wire(vp_j, (vp_j[0], round(vp_j[1] - 5.08, 2))),
        power("power:GND", "#PWR_U1V-", "GND", vm_j[0], round(vm_j[1] + 5.08, 2)),
        wire(vm_j, (vm_j[0], round(vm_j[1] + 5.08, 2))),
        junction(vp_j),
        junction(vm_j),
    ]
    # SHDN → V+ junction via LEFT side (avoids crossing OUT wire to the right)
    o += [
        wire(u_shdn, (round(u_shdn[0] - 10.16, 2), u_shdn[1])),
        wire((round(u_shdn[0] - 10.16, 2), u_shdn[1]), (round(u_shdn[0] - 10.16, 2), vp_j[1])),
        wire((round(u_shdn[0] - 10.16, 2), vp_j[1]), vp_j),
        junction((round(u_shdn[0] - 10.16, 2), vp_j[1])),
    ]
    # C1/C2 across U1 V+/V− — spaced left of U1 for independent selection
    for ref, val, cx in (("C1", "100n", round(ux - 25.4, 2)), ("C2", "1u", round(ux - 40.64, 2))):
        cy = round((vp_j[1] + vm_j[1]) / 2, 2)
        o.append(symbol_inst("Device:C", ref, val, cx, cy, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
        o += [
            wire(ct, (cx, vp_j[1])),
            wire((cx, vp_j[1]), vp_j),
            junction((cx, vp_j[1])),
            wire(cb, (cx, vm_j[1])),
            wire((cx, vm_j[1]), vm_j),
            junction((cx, vm_j[1])),
        ]

    # Hysteresis DNP: branch from OUT down to R5, other end to SENSE_P
    rh = (round(u_out[0] + 5.08, 2), round(uy + 25.4, 2))
    o.append(symbol_inst("Device:R", "R5", "DNP", rh[0], rh[1], ["1", "2"], dnp=True, footprint=FP_R))
    rh1, rh2 = pin_xy(rh[0], rh[1], 0, 3.81), pin_xy(rh[0], rh[1], 0, -3.81)
    o += [
        wire(u_out, (u_out[0], rh1[1])),
        junction(u_out),
        wire((u_out[0], rh1[1]), rh1),
    ]
    o += stub_label("SENSE_P", rh2, rot=0, dy=2.54)

    # FF clock / Q / ~S / ~R
    o += [
        wire(f_c, (f_c[0] - 10.16, f_c[1])),
        global_label("SENSE_STROBE", (f_c[0] - 10.16, f_c[1]), 180),
        junction((f_c[0] - 10.16, f_c[1])),
    ]
    r6 = (f_c[0] - 10.16, round(f_c[1] + 15.24, 2))
    o.append(symbol_inst("Device:R", "R6", "10k", r6[0], r6[1], ["1", "2"], footprint=FP_R))
    r6t, r6b = pin_xy(r6[0], r6[1], 0, 3.81), pin_xy(r6[0], r6[1], 0, -3.81)
    o += [wire((f_c[0] - 10.16, f_c[1]), r6t)]
    o += stub_gnd(r6b, "#PWR_R6", dy=2.54)

    # ~S/~R pulled to +3V3 at top of FF (local, not through labels)
    v2_j = (f_s[0], round(f_s[1] - 2.54, 2))
    o += [
        wire(f_s, v2_j),
        power("power:+3V3", "#PWR_U2SR", "+3V3", v2_j[0], round(v2_j[1] - 5.08, 2)),
        wire(v2_j, (v2_j[0], round(v2_j[1] - 5.08, 2))),
        junction(v2_j),
        wire(f_r, (round(f_r[0] + 10.16, 2), f_r[1])),
        wire((round(f_r[0] + 10.16, 2), f_r[1]), (round(f_r[0] + 10.16, 2), v2_j[1])),
        wire((round(f_r[0] + 10.16, 2), v2_j[1]), v2_j),
        junction((round(f_r[0] + 10.16, 2), v2_j[1])),
        no_connect(f_qn),
        wire(f_q, (round(f_q[0] + 10.16, 2), f_q[1])),
        global_label("DOUT", (round(f_q[0] + 10.16, 2), f_q[1]), 0, "output"),
        junction((round(f_q[0] + 10.16, 2), f_q[1])),
    ]
    tp = (round(f_q[0] + 10.16, 2), round(f_q[1] + 12.7, 2))
    o.append(symbol_inst("Connector:TestPoint", "TP1", "DOUT", tp[0], tp[1], ["1"],
                         footprint="TestPoint:TestPoint_Pad_D1.5mm"))
    o.append(wire((round(f_q[0] + 10.16, 2), f_q[1]), tp))

    # Unit 2 NC — well below unit 1
    u2b = (fx, round(fy + 55.88, 2))
    o.append(symbol_inst("74xx:74LS74", "U2", "74AHC74", u2b[0], u2b[1],
                         ["8", "9", "10", "11", "12", "13"], unit=2,
                         footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"))
    for lx, ly in ((7.62, -2.54), (7.62, 2.54), (0, 7.62), (-7.62, 0), (-7.62, 2.54), (0, -7.62)):
        o.append(no_connect(pin_xy(u2b[0], u2b[1], lx, ly)))

    # Unit 3 power — C3/C4 wired to VCC/GND; caps spaced for selection
    u2c = (round(fx + 45.72, 2), round(fy + 55.88, 2))
    o.append(symbol_inst("74xx:74LS74", "U2", "74AHC74", u2c[0], u2c[1], ["7", "14"], unit=3,
                         footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"))
    vcc, gndp = pin_xy(u2c[0], u2c[1], 0, 10.16), pin_xy(u2c[0], u2c[1], 0, -10.16)
    vcc_j = (vcc[0], round(vcc[1] - 2.54, 2))
    gnd_j = (gndp[0], round(gndp[1] + 2.54, 2))
    o += [
        wire(vcc, vcc_j),
        wire(gndp, gnd_j),
        power("power:+3V3", "#PWR_U2VCC", "+3V3", vcc_j[0], round(vcc_j[1] - 7.62, 2)),
        wire(vcc_j, (vcc_j[0], round(vcc_j[1] - 7.62, 2))),
        power("power:GND", "#PWR_U2GND", "GND", gnd_j[0], round(gnd_j[1] + 7.62, 2)),
        wire(gnd_j, (gnd_j[0], round(gnd_j[1] + 7.62, 2))),
        junction(vcc_j),
        junction(gnd_j),
    ]
    for ref, val, cx in (("C3", "100n", round(u2c[0] + 17.78, 2)), ("C4", "1u", round(u2c[0] + 33.02, 2))):
        cy = u2c[1]
        o.append(symbol_inst("Device:C", ref, val, cx, cy, ["1", "2"], footprint=FP_C))
        ct, cb = pin_xy(cx, cy, 0, 3.81), pin_xy(cx, cy, 0, -3.81)
        o += [
            wire(ct, (cx, vcc_j[1])),
            wire((cx, vcc_j[1]), vcc_j),
            junction((cx, vcc_j[1])),
            wire(cb, (cx, gnd_j[1])),
            wire((cx, gnd_j[1]), gnd_j),
            junction((cx, gnd_j[1])),
        ]

    # Global power flags — vertical stacks (same X as rail symbol)
    main_3v3 = (25.4, 25.4)
    main_gnd = (45.72, 25.4)
    o += [
        power("power:+3V3", "#PWR_MAIN", "+3V3", main_3v3[0], main_3v3[1]),
        *pwr_flag_below(main_3v3, "#FLG_3V3", gap=10.16),
        power("power:GND", "#PWR_GNDMAIN", "GND", main_gnd[0], main_gnd[1]),
        *pwr_flag_below(main_gnd, "#FLG_GND", gap=10.16),
        text(
            "Stage 1 — Bowtie / split-sense + amp\\n"
            "Clamps: BAT54S rot90 — +3V3 (K) above, GND (A) below\\n"
            "C1/C2 at U1; C3/C4 at U2; blocks spaced for hand placement",
            25.4, 55.88,
        ),
        text("YA65≡YA66 mid-shunt (soft ground)", mid[0] - 10, mid[1] - 5.08),
    ]

    sch = f'''(kicad_sch
\t(version 20260306)
\t(generator "gen_stage1.py")
\t(generator_version "2.2")
\t(uuid "{SHEET_UUID}")
\t(paper "A1")
\t(title_block
\t\t(title "Core Memory Driver — Stage 1 Sense / Bowtie")
\t\t(comment 1 "Bowtie FB_A/FB_B; soft YA mid; iso + clamps; TLV3501; 74AHC74")
\t)
\t(lib_symbols
{lib_syms}
\t)
{chr(10).join(o)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
    SCH.write_text(sch)
    print(f"Wrote {SCH}")


if __name__ == "__main__":
    main()
