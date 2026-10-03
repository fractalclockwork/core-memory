#!/usr/bin/env python3
"""Isolated KiCad project for the 3-wire memory-core SPICE model.

Does not touch kicad/core. The behavioral subcircuit lives in
kicad/core_element_sim/models/coremem.cir (also used by coremem_tb.cir).

  uv run python kicad/scripts/gen_core_element_sim.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / "core_element_sim"
KICAD_SYMS = Path("/usr/share/kicad/symbols")
DRIVER_PRO = ROOT / "core" / "core.kicad_pro"

PROJECT = "core_element_sim"
SHEET_UUID = "7f3c1a90-6e2d-4b7a-8c15-9d4e2f6a1b30"

# Same edges as models/coremem_tb.cir. Value is the current injected into
# pin 1 of the winding (Ix 0 X1 in the batch deck).
PWL_X = (
    "0 0 "
    "2u 0 2.1u -0.4 4u -0.4 4.1u 0 "
    "6u 0 6.1u -0.4 8u -0.4 8.1u 0 "
    "10u 0 10.1u -0.4 12u -0.4 12.1u 0 "
    "14u 0 14.1u 0.4 16u 0.4 16.1u 0"
)
PWL_Y = (
    "0 0 "
    "6u 0 6.1u -0.4 8u -0.4 8.1u 0 "
    "10u 0 10.1u -0.4 12u -0.4 12.1u 0 "
    "14u 0 14.1u 0.4 16u 0.4 16.1u 0"
)


def uid() -> str:
    return str(uuid.uuid4())


def fmt(n: float) -> str:
    return f"{n:.2f}"


def pin_xy(sx: float, sy: float, lx: float, ly: float, rot: int = 0) -> tuple[float, float]:
    if rot == 0:
        return (sx + lx, sy - ly)
    if rot == 90:
        return (sx - ly, sy - lx)
    if rot == 180:
        return (sx - lx, sy + ly)
    if rot == 270:
        return (sx + ly, sy + lx)
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
    return "\n".join("\t" + line if line else line for line in body.splitlines())


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def prop(name: str, value: str, x: float, y: float, rot: int = 0, hide: bool = False) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    return (
        f'\t\t(property "{name}" "{esc(value)}"\n'
        f"\t\t\t(at {fmt(x)} {fmt(y)} {rot}){hide_s}\n"
        "\t\t\t(show_name no)\n"
        "\t\t\t(do_not_autoplace no)\n"
        "\t\t\t(effects (font (size 1.27 1.27)))\n"
        "\t\t)"
    )


def inst(
    lib_id: str,
    ref: str,
    value: str,
    x: float,
    y: float,
    pins: list[str],
    *,
    rot: int = 0,
    extra: list[tuple[str, str]] | None = None,
) -> str:
    pin_block = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins)
    fields = [
        prop("Reference", ref, x + 2.54, y - 3.81),
        prop("Value", value, x + 2.54, y - 1.27),
        prop("Footprint", "", x, y, hide=True),
        prop("Datasheet", "", x, y, hide=True),
        prop("Description", "", x, y, hide=True),
    ]
    for name, val in extra or []:
        fields.append(prop(name, val, x, y, hide=True))
    field_block = "\n".join(fields)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {fmt(x)} {fmt(y)} {rot})
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(in_pos_files no)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{field_block}
{pin_block}
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{ref}") (unit 1))))
\t)'''


def pwr_flag(x: float, y: float) -> str:
    # ERC power-out marker. Kept out of the spice netlist.
    return f'''\t(symbol
\t\t(lib_id "power:PWR_FLAG")
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim yes)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(in_pos_files no)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", "#FLG01", x, y - 5.08, hide=True)}
{prop("Value", "PWR_FLAG", x, y + 5.08)}
{prop("Footprint", "", x, y, hide=True)}
{prop("Datasheet", "", x, y, hide=True)}
{prop("Description", "", x, y, hide=True)}
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "#FLG01") (unit 1))))
\t)'''


def power(x: float, y: float, ref: str, rot: int = 0) -> str:
    # Simulation_SPICE:0 exports as ngspice node 0. power:GND stays a net named GND.
    return f'''\t(symbol
\t\t(lib_id "Simulation_SPICE:0")
\t\t(at {fmt(x)} {fmt(y)} {rot})
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(in_pos_files no)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, x, y + 2.54, hide=True)}
{prop("Value", "0", x, y - 3.81)}
{prop("Footprint", "", x, y, hide=True)}
{prop("Datasheet", "", x, y, hide=True)}
{prop("Description", "", x, y, hide=True)}
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{ref}") (unit 1))))
\t)'''


def wire(a: tuple[float, float], b: tuple[float, float]) -> str:
    return f'''\t(wire
\t\t(pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])}))
\t\t(stroke (width 0) (type default))
\t\t(uuid "{uid()}")
\t)'''


def junction(p: tuple[float, float]) -> str:
    return f'''\t(junction
\t\t(at {fmt(p[0])} {fmt(p[1])})
\t\t(diameter 0)
\t\t(color 0 0 0 0)
\t\t(uuid "{uid()}")
\t)'''


def label(name: str, p: tuple[float, float], rot: int = 0) -> str:
    # Global, so the spice node is S1 / B and not a hierarchical /S1 path.
    return f'''\t(global_label "{name}"
\t\t(shape passive)
\t\t(at {fmt(p[0])} {fmt(p[1])} {rot})
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
\t\t\t(at {fmt(p[0])} {fmt(p[1])} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t)'''


def text_item(body: str, x: float, y: float, *, sim: bool) -> str:
    flag = "no" if sim else "yes"
    escaped = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'''\t(text "{escaped}"
\t\t(exclude_from_sim {flag})
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t(uuid "{uid()}")
\t)'''


CORE_SYMBOL = r'''	(symbol "CoreMem"
		(pin_names (offset 1.016))
		(exclude_from_sim no)
		(in_bom no)
		(on_board no)
		(in_pos_files no)
		(duplicate_pin_numbers_are_jumpers no)
		(property "Reference" "X" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
		(property "Value" "CoreMem" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Description" "Sim-only 3-wire memory core. SPICE model models/coremem.cir." (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Sim.Device" "SUBCKT" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Sim.Name" "coremem" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Sim.Library" "models/coremem.cir" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Sim.Pins" "1=X1 2=X2 3=Y1 4=Y2 5=S1 6=S2 7=B" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "CoreMem_0_1"
			(rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
			(polyline (pts (xy 0 3.81) (xy 0 2.54) (xy 0.635 1.905) (xy -0.635 0.635) (xy 0.635 -0.635) (xy -0.635 -1.905) (xy 0 -2.54) (xy 0 -3.81)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy -3.81 0) (xy -2.54 0) (xy -1.905 0.635) (xy -0.635 -0.635) (xy 0.635 0.635) (xy 1.905 -0.635) (xy 2.54 0) (xy 3.81 0)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy -3.81 -3.81) (xy 3.81 3.81)) (stroke (width 0) (type default)) (fill (type none)))
			(text "X" (at 2.032 0 0) (effects (font (size 1.016 1.016))))
			(text "Y" (at 0 2.286 0) (effects (font (size 1.016 1.016))))
			(text "S" (at -2.54 2.54 0) (effects (font (size 1.016 1.016))))
		)
		(symbol "CoreMem_1_1"
			(pin passive line (at 0 7.62 270) (length 2.54) (name "X1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 0 -7.62 90) (length 2.54) (name "X2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -7.62 0 0) (length 2.54) (name "Y1" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 0 180) (length 2.54) (name "Y2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -7.62 -5.08 0) (length 2.54) (name "S1" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 5.08 180) (length 2.54) (name "S2" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 7.62 -5.08 180) (length 2.54) (name "B" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
		)
		(embedded_fonts no)
	)'''


def core_lib_symbol() -> str:
    return (
        "(kicad_symbol_lib\n"
        "\t(version 20251024)\n"
        '\t(generator "gen_core_element_sim.py")\n'
        '\t(generator_version "1.0")\n'
        + CORE_SYMBOL
        + "\n)\n"
    )


def embedded_core() -> str:
    body = CORE_SYMBOL.replace('(symbol "CoreMem"', '(symbol "core_element_sim:CoreMem"', 1)
    return "\n".join("\t" + line if line else line for line in body.splitlines())


NOTE = """Isolated 50-mil core. Not part of the driver.
Plot V(S1) and V(B). V(B) is tesla.
2-4 us    Ix=-400 mA           half-select
6-8 us    Ix=Iy=-400 mA        flip +Br to -Br
10-12 us  Ix=Iy=-400 mA        already flipped
14-16 us  Ix=Iy=+400 mA        flip back
R1 and R2 are 20 ohm dampers. X2 Y2 S2 are ground.
Model: models/coremem.cir"""


def build_schematic() -> str:
    cx, cy = 152.40, 101.60
    x1 = pin_xy(cx, cy, 0, 7.62)
    x2 = pin_xy(cx, cy, 0, -7.62)
    y1 = pin_xy(cx, cy, -7.62, 0)
    y2 = pin_xy(cx, cy, 7.62, 0)
    s1 = pin_xy(cx, cy, -7.62, -5.08)
    s2 = pin_xy(cx, cy, 7.62, 5.08)
    bpin = pin_xy(cx, cy, 7.62, -5.08)

    # IPWL rot 0: pin 1 above center, pin 2 below. Pin 2 sits 5.08 mm above X1.
    ix = (cx, x1[1] - 5.08 - 5.08)
    ix_p1 = pin_xy(ix[0], ix[1], 0, 5.08, 0)
    ix_p2 = pin_xy(ix[0], ix[1], 0, -5.08, 0)
    # IPWL rot 90: pin 1 to the left, pin 2 to the right, 5.08 mm left of Y1.
    iy = (y1[0] - 5.08 - 5.08, y1[1])
    iy_p1 = pin_xy(iy[0], iy[1], 0, 5.08, 90)
    iy_p2 = pin_xy(iy[0], iy[1], 0, -5.08, 90)

    jx = (ix_p2[0], (ix_p2[1] + x1[1]) / 2)
    # Resistor above the tap so the body stays clear of the core.
    rx = (170.18, jx[1] - 3.81)
    rx_p1 = pin_xy(rx[0], rx[1], 0, 3.81, 0)
    rx_p2 = pin_xy(rx[0], rx[1], 0, -3.81, 0)

    jy = ((iy_p2[0] + y1[0]) / 2, y1[1])
    ry_top = (jy[0], jy[1] + 15.24)
    ry = (ry_top[0], ry_top[1] + 3.81)
    ry_p1 = pin_xy(ry[0], ry[1], 0, 3.81, 0)
    ry_p2 = pin_xy(ry[0], ry[1], 0, -3.81, 0)

    x2_gnd = (x2[0], x2[1] + 7.62)
    y2_gnd = (y2[0] + 12.70, y2[1])
    s2_gnd = (s2[0] + 20.32, s2[1])
    s1_lbl = (s1[0], s1[1] + 7.62)
    b_lbl = (bpin[0] + 12.70, bpin[1])

    parts = [
        inst(
            "core_element_sim:CoreMem",
            "X1",
            "CoreMem",
            cx,
            cy,
            ["1", "2", "3", "4", "5", "6", "7"],
            extra=[
                ("Sim.Device", "SUBCKT"),
                ("Sim.Name", "coremem"),
                ("Sim.Library", "models/coremem.cir"),
                ("Sim.Pins", "1=X1 2=X2 3=Y1 4=Y2 5=S1 6=S2 7=B"),
            ],
        ),
        inst(
            "Simulation_SPICE:IPWL",
            "I1",
            "IPWL",
            ix[0],
            ix[1],
            ["1", "2"],
            extra=[
                ("Sim.Device", "I"),
                ("Sim.Type", "PWL"),
                ("Sim.Pins", "1=+ 2=-"),
                ("Sim.Params", f'pwl="{PWL_X}"'),
            ],
        ),
        inst(
            "Simulation_SPICE:IPWL",
            "I2",
            "IPWL",
            iy[0],
            iy[1],
            ["1", "2"],
            rot=90,
            extra=[
                ("Sim.Device", "I"),
                ("Sim.Type", "PWL"),
                ("Sim.Pins", "1=+ 2=-"),
                ("Sim.Params", f'pwl="{PWL_Y}"'),
            ],
        ),
        inst("Device:R", "R1", "20", rx[0], rx[1], ["1", "2"]),
        inst("Device:R", "R2", "20", ry[0], ry[1], ["1", "2"]),
        power(ix_p1[0], ix_p1[1], "#PWR01", rot=180),
        power(iy_p1[0], iy_p1[1], "#PWR02", rot=270),
        power(rx_p1[0], rx_p1[1], "#PWR03", rot=180),
        power(ry_p2[0], ry_p2[1], "#PWR04", rot=0),
        power(x2_gnd[0], x2_gnd[1], "#PWR05", rot=0),
        power(y2_gnd[0], y2_gnd[1], "#PWR06", rot=0),
        power(s2_gnd[0], s2_gnd[1], "#PWR07", rot=0),
        pwr_flag(x2_gnd[0] + 7.62, x2_gnd[1]),
        wire(ix_p2, x1),
        junction(jx),
        wire(jx, rx_p2),
        wire(iy_p2, y1),
        junction(jy),
        wire(jy, ry_p1),
        wire(x2, x2_gnd),
        wire(x2_gnd, (x2_gnd[0] + 7.62, x2_gnd[1])),
        junction(x2_gnd),
        wire(y2, y2_gnd),
        wire(s2, s2_gnd),
        wire(s1, s1_lbl),
        label("S1", s1_lbl, rot=0),
        wire(bpin, b_lbl),
        label("B", b_lbl, rot=0),
        text_item(".tran 20n 18u uic\n", 25.4, 25.4, sim=True),
        text_item(NOTE, 25.4, 35.56, sim=False),
    ]

    libs = [
        embed("Device:R", extract_symbol(KICAD_SYMS / "Device.kicad_sym", "R")),
        embed("Simulation_SPICE:IPWL", extract_symbol(KICAD_SYMS / "Simulation_SPICE.kicad_sym", "IPWL")),
        embed("Simulation_SPICE:0", extract_symbol(KICAD_SYMS / "Simulation_SPICE.kicad_sym", "0")),
        embed("power:PWR_FLAG", extract_symbol(KICAD_SYMS / "power.kicad_sym", "PWR_FLAG")),
        embedded_core(),
    ]
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "gen_core_element_sim.py")
\t(generator_version "1.0")
\t(uuid "{SHEET_UUID}")
\t(paper "A3")
\t(title_block
\t\t(title "Core Element SPICE")
\t\t(comment 1 "Isolated 50-mil 3-wire memory core. Not the driver.")
\t\t(comment 2 "Plot V(S1) and V(B). Run with UIC.")
\t)
\t(lib_symbols
{chr(10).join(libs)}
\t)
{chr(10).join(parts)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def write_project() -> None:
    data = json.loads(DRIVER_PRO.read_text())
    data["meta"]["filename"] = "core_element_sim.kicad_pro"
    sch = data["schematic"]
    sch["top_level_sheets"] = [
        {"filename": "core_element_sim.kicad_sch", "name": "core_element_sim", "uuid": SHEET_UUID}
    ]
    sch["ngspice"] = {
        "fix_include_paths": True,
        "fix_passive_vals": False,
        "meta": {"version": 0},
        "model_mode": 4,
        "workbook_filename": "",
    }
    sch["spice_adjust_passive_values"] = False
    sch["spice_current_sheet_as_root"] = False
    sch["spice_external_command"] = 'spice "%I"'
    sch["spice_model_current_sheet_as_root"] = True
    sch["spice_save_all_currents"] = False
    sch["spice_save_all_dissipations"] = False
    sch["spice_save_all_voltages"] = True
    data["sheets"] = [[SHEET_UUID, "core_element_sim"]]
    (PROJ / "core_element_sim.kicad_pro").write_text(json.dumps(data, indent=2) + "\n")


def write_lib_table() -> None:
    (PROJ / "sym-lib-table").write_text(
        """(sym_lib_table
  (version 7)
  (lib (name "core_element_sim")(type "KiCad")(uri "${KIPRJMOD}/core_element_sim.kicad_sym")(options "")(descr "Sim-only 3-wire memory core"))
  (lib (name "Simulation_SPICE")(type "KiCad")(uri "${KICAD_SYMBOL_DIR}/Simulation_SPICE.kicad_sym")(options "")(descr ""))
  (lib (name "Device")(type "KiCad")(uri "${KICAD_SYMBOL_DIR}/Device.kicad_sym")(options "")(descr ""))
  (lib (name "power")(type "KiCad")(uri "${KICAD_SYMBOL_DIR}/power.kicad_sym")(options "")(descr ""))
)
"""
    )
    (PROJ / "fp-lib-table").write_text("(fp_lib_table\n  (version 7)\n)\n")


def main() -> None:
    PROJ.mkdir(parents=True, exist_ok=True)
    (PROJ / "core_element_sim.kicad_sym").write_text(core_lib_symbol())
    (PROJ / "core_element_sim.kicad_sch").write_text(build_schematic())
    write_project()
    write_lib_table()
    print(f"wrote {PROJ}")


if __name__ == "__main__":
    main()
