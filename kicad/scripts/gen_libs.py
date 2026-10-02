#!/usr/bin/env python3
"""Generate core-memory KiCad symbol + footprint libraries from docs/design_spec.md geometry."""

from __future__ import annotations

import math
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT / "libs"
PRETTY = LIB_DIR / "core_memory.pretty"
SYM_PATH = LIB_DIR / "core_memory.kicad_sym"

# docs/design_spec.md — inches → mm
IN = 25.4
PITCH = 0.1875 * IN  # 4.7625 mm, same-face center-to-center
STAGGER = 0.0625 * IN  # 1.5875 mm face-to-face offset
CONTACT_W = 0.125 * IN  # 3.175 mm (card finger width; for docs)
ROW_SEP = 5.08  # solder-tail row separation (typical card-edge receptacle)
PAD_SIZE = 1.9
PAD_DRILL = 1.0
PIN1_FROM_RIGHT_IN = 1.3125  # documented on plane; noted in footprint descr


def uid() -> str:
    return str(uuid.uuid4())


def fmt(x: float) -> str:
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def gen_receptacle(positions: int, name: str, axis: str) -> str:
    """
    Dual-readout staggered card-edge receptacle footprint.

    Pin numbering matches the plane:
      odd pins 1,3,5,... on row A (plane top face)
      even pins 2,4,6,... on row B (plane bottom face), staggered by STAGGER

    `positions` = contact positions per face (32 for X, 33 for Y).
    Total pins = 2 * positions.
    """
    n_pins = 2 * positions
    # Place pin 1 at y=0; subsequent odd pins along +Y at PITCH
    # Even pins at x=ROW_SEP, y = STAGGER + k*PITCH
    ys_odd = [i * PITCH for i in range(positions)]
    length = (positions - 1) * PITCH
    body_x0, body_x1 = -2.5, ROW_SEP + 2.5
    body_y0, body_y1 = -2.5, length + 2.5
    crt = 0.25

    lines: list[str] = []
    lines.append(f'(footprint "{name}"')
    lines.append("\t(version 20260206)")
    lines.append('\t(generator "gen_libs.py")')
    lines.append('\t(generator_version "1.0")')
    lines.append('\t(layer "F.Cu")')
    lines.append(
        f'\t(descr "Dual-readout staggered card-edge receptacle, {positions}-pos '
        f'({n_pins} pins), {PITCH:.4f}mm ({0.1875}\\") same-face pitch, '
        f'{STAGGER:.4f}mm stagger. Mates core-plane {axis} edge per docs/design_spec.md. '
        f"Plane Pin1 is {PIN1_FROM_RIGHT_IN}\\\" from right edge of 9\\\" board. "
        f'Contact finger width {CONTACT_W:.3f}mm (0.125\\"). '
        f'Solder-tail row pitch {ROW_SEP}mm assumed — verify against chosen receptacle.")'
    )
    lines.append(
        f'\t(tags "card-edge dual-readout staggered core-memory {axis} {positions}pos")'
    )
    lines.append('\t(property "Reference" "J"')
    lines.append(f"\t\t(at {fmt(ROW_SEP / 2)} {fmt(body_y0 - 1.5)} 0)")
    lines.append('\t\t(layer "F.SilkS")')
    lines.append(f'\t\t(uuid "{uid()}")')
    lines.append("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    lines.append("\t)")
    lines.append(f'\t(property "Value" "{name}"')
    lines.append(f"\t\t(at {fmt(ROW_SEP / 2)} {fmt(body_y1 + 1.5)} 0)")
    lines.append('\t\t(layer "F.Fab")')
    lines.append(f'\t\t(uuid "{uid()}")')
    lines.append("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    lines.append("\t)")
    for prop, val in (
        ("Datasheet", "docs/design_spec.md"),
        ("Description", f"Core plane {axis} mate, {n_pins} pins"),
    ):
        lines.append(f'\t(property "{prop}" "{val}"')
        lines.append("\t\t(at 0 0 0)")
        lines.append("\t\t(unlocked yes)")
        lines.append('\t\t(layer "F.Fab")')
        lines.append("\t\t(hide yes)")
        lines.append(f'\t\t(uuid "{uid()}")')
        lines.append("\t\t(effects (font (size 1.27 1.27) (thickness 0.15)))")
        lines.append("\t)")
    lines.append("\t(attr through_hole)")
    lines.append("\t(duplicate_pad_numbers_are_jumpers no)")

    # Fab / silk / courtyard outline
    def rect(layer: str, x0, y0, x1, y1, w: float = 0.12):
        lines.append("\t(fp_rect")
        lines.append(f"\t\t(start {fmt(x0)} {fmt(y0)})")
        lines.append(f"\t\t(end {fmt(x1)} {fmt(y1)})")
        lines.append(f"\t\t(stroke (width {w}) (type solid))")
        lines.append("\t\t(fill no)")
        lines.append(f'\t\t(layer "{layer}")')
        lines.append(f'\t\t(uuid "{uid()}")')
        lines.append("\t)")

    rect("F.Fab", body_x0, body_y0, body_x1, body_y1, 0.1)
    rect("F.SilkS", body_x0 - 0.15, body_y0 - 0.15, body_x1 + 0.15, body_y1 + 0.15)
    rect(
        "F.CrtYd",
        body_x0 - crt,
        body_y0 - crt,
        body_x1 + crt,
        body_y1 + crt,
        0.05,
    )

    # Pin-1 marker
    lines.append("\t(fp_line")
    lines.append(f"\t\t(start {fmt(-1.2)} {fmt(-1.2)})")
    lines.append(f"\t\t(end {fmt(0)} {fmt(-1.2)})")
    lines.append("\t\t(stroke (width 0.12) (type solid))")
    lines.append('\t\t(layer "F.SilkS")')
    lines.append(f'\t\t(uuid "{uid()}")')
    lines.append("\t)")

    lines.append('\t(fp_text user "${REFERENCE}"')
    lines.append(f"\t\t(at {fmt(ROW_SEP / 2)} {fmt(length / 2)} 90)")
    lines.append('\t\t(layer "F.Fab")')
    lines.append(f'\t\t(uuid "{uid()}")')
    lines.append("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    lines.append("\t)")

    # Pads: odd on left (x=0), even on right (x=ROW_SEP) with stagger
    for i in range(positions):
        odd = 2 * i + 1
        even = 2 * i + 2
        y_odd = ys_odd[i]
        y_even = ys_odd[i] + STAGGER
        shape = "rect" if odd == 1 else "circle"
        lines.append(f'\t(pad "{odd}" thru_hole {shape}')
        lines.append(f"\t\t(at {fmt(0)} {fmt(y_odd)})")
        lines.append(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        lines.append(f"\t\t(drill {PAD_DRILL})")
        lines.append('\t\t(layers "*.Cu" "*.Mask")')
        lines.append("\t\t(remove_unused_layers no)")
        lines.append(f'\t\t(uuid "{uid()}")')
        lines.append("\t)")
        lines.append(f'\t(pad "{even}" thru_hole circle')
        lines.append(f"\t\t(at {fmt(ROW_SEP)} {fmt(y_even)})")
        lines.append(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        lines.append(f"\t\t(drill {PAD_DRILL})")
        lines.append('\t\t(layers "*.Cu" "*.Mask")')
        lines.append("\t\t(remove_unused_layers no)")
        lines.append(f'\t\t(uuid "{uid()}")')
        lines.append("\t)")

    lines.append(")")
    return "\n".join(lines) + "\n"


def prop(name: str, value: str, x: float, y: float, hide: bool = False, justify: str | None = None) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    just = f"\n\t\t\t\t(justify {justify})" if justify else ""
    return f"""\t\t(property "{name}" "{value}"
\t\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no){hide_s}
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t){just}
\t\t\t)
\t\t)"""


def edge_symbol(name: str, n_pins: int, footprint: str, descr: str) -> str:
    """Passive connector symbol: pins on left, numbered 1..n, names matching plane."""
    # Split into two columns of pins if large: left = all pins stacked
    pitch = 2.54
    height = (n_pins - 1) * pitch
    y0 = height / 2
    body_w = 12.7
    lines = [
        f'\t(symbol "{name}"',
        "\t\t(pin_names (offset 1.016))",
        "\t\t(exclude_from_sim no)",
        "\t\t(in_bom yes)",
        "\t\t(on_board yes)",
        "\t\t(in_pos_files yes)",
        "\t\t(duplicate_pin_numbers_are_jumpers no)",
        prop("Reference", "J", body_w / 2, y0 + 2.54),
        prop("Value", name, body_w / 2, -y0 - 2.54),
        prop("Footprint", footprint, 0, 0, hide=True),
        prop("Datasheet", "docs/design_spec.md", 0, 0, hide=True),
        prop("Description", descr, 0, 0, hide=True),
        prop("ki_keywords", "core memory edge connector dual-readout", 0, 0, hide=True),
        prop("ki_fp_filters", "core_memory:*", 0, 0, hide=True),
        f'\t\t(symbol "{name}_1_1"',
        "\t\t\t(rectangle",
        f"\t\t\t\t(start 0 {fmt(y0 + 1.27)})",
        f"\t\t\t\t(end {fmt(body_w)} {fmt(-y0 - 1.27)})",
        "\t\t\t\t(stroke (width 0.254) (type default))",
        "\t\t\t\t(fill (type background))",
        "\t\t\t)",
    ]
    # Label inside body
    lines.append(
        f'\t\t\t(text "{name.split("_")[-1]}"\n'
        f"\t\t\t\t(at {fmt(body_w / 2)} 0 0)\n"
        f"\t\t\t\t(effects (font (size 2.54 2.54) (thickness 0.3))))"
    )
    for i in range(1, n_pins + 1):
        y = y0 - (i - 1) * pitch
        pname = str(i)
        lines.append(
            f'\t\t\t(pin passive line\n'
            f"\t\t\t\t(at {-5.08} {fmt(y)} 0)\n"
            f"\t\t\t\t(length 5.08)\n"
            f'\t\t\t\t(name "{pname}"\n'
            f"\t\t\t\t\t(effects (font (size 1.27 1.27))))\n"
            f'\t\t\t\t(number "{i}"\n'
            f"\t\t\t\t\t(effects (font (size 1.27 1.27))))\n"
            f"\t\t\t)"
        )
    lines.append("\t\t)")
    lines.append("\t\t(embedded_fonts no)")
    lines.append("\t)")
    return "\n".join(lines)


def fds8958a_symbol() -> str:
    """Onsemi FDS8958A dual P+N MOSFET, SOIC-8."""
    name = "FDS8958A"
    return f"""\t(symbol "{name}"
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(duplicate_pin_numbers_are_jumpers no)
{prop("Reference", "Q", 5.08, 8.89)}
{prop("Value", name, 5.08, 6.35)}
{prop("Footprint", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 0, 0, hide=True)}
{prop("Datasheet", "https://www.onsemi.com/pdf/datasheet/fds8958a-d.pdf", 0, 0, hide=True)}
{prop("Description", "Dual P & N-Channel PowerTrench MOSFET, SOIC-8", 0, 0, hide=True)}
{prop("ki_keywords", "MOSFET dual N P PowerTrench", 0, 0, hide=True)}
{prop("ki_fp_filters", "SOIC*3.9x4.9mm*P1.27mm*", 0, 0, hide=True)}
\t\t(symbol "{name}_1_1"
\t\t\t(rectangle
\t\t\t\t(start -7.62 7.62)
\t\t\t\t(end 7.62 -7.62)
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t\t(text "P"
\t\t\t\t(at -3.81 5.08 0)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(text "N"
\t\t\t\t(at 3.81 5.08 0)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(pin passive line (at -10.16 5.08 0) (length 2.54)
\t\t\t\t(name "S1" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "1" (effects (font (size 1.27 1.27)))))
\t\t\t(pin input line (at -10.16 2.54 0) (length 2.54)
\t\t\t\t(name "G1" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "2" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at -10.16 -2.54 0) (length 2.54)
\t\t\t\t(name "S2" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "3" (effects (font (size 1.27 1.27)))))
\t\t\t(pin input line (at -10.16 -5.08 0) (length 2.54)
\t\t\t\t(name "G2" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "4" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at 10.16 -5.08 180) (length 2.54)
\t\t\t\t(name "D2" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "5" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at 10.16 -2.54 180) (length 2.54)
\t\t\t\t(name "D2" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "6" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at 10.16 2.54 180) (length 2.54)
\t\t\t\t(name "D1" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "7" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at 10.16 5.08 180) (length 2.54)
\t\t\t\t(name "D1" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "8" (effects (font (size 1.27 1.27)))))
\t\t)
\t\t(embedded_fonts no)
\t)"""


def opa192_symbol() -> str:
    name = "OPA192"
    return f"""\t(symbol "{name}"
\t\t(pin_names (offset 0.254))
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(duplicate_pin_numbers_are_jumpers no)
{prop("Reference", "U", 0, 5.08)}
{prop("Value", name, 0, -5.08)}
{prop("Footprint", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 0, 0, hide=True)}
{prop("Datasheet", "https://www.ti.com/lit/ds/symlink/opa192.pdf", 0, 0, hide=True)}
{prop("Description", "36V precision rail-to-rail op amp, SOIC-8", 0, 0, hide=True)}
{prop("ki_keywords", "opamp precision rtor", 0, 0, hide=True)}
{prop("ki_fp_filters", "SOIC*3.9x4.9mm*P1.27mm*", 0, 0, hide=True)}
\t\t(symbol "{name}_0_1"
\t\t\t(polyline
\t\t\t\t(pts (xy -5.08 5.08) (xy 5.08 0) (xy -5.08 -5.08) (xy -5.08 5.08))
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
\t\t(symbol "{name}_1_1"
\t\t\t(pin input line (at -7.62 2.54 0) (length 2.54)
\t\t\t\t(name "+" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "3" (effects (font (size 1.27 1.27)))))
\t\t\t(pin input line (at -7.62 -2.54 0) (length 2.54)
\t\t\t\t(name "-" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "2" (effects (font (size 1.27 1.27)))))
\t\t\t(pin power_in line (at 0 7.62 270) (length 2.54)
\t\t\t\t(name "V+" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "7" (effects (font (size 1.27 1.27)))))
\t\t\t(pin power_in line (at 0 -7.62 90) (length 2.54)
\t\t\t\t(name "V-" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "4" (effects (font (size 1.27 1.27)))))
\t\t\t(pin output line (at 7.62 0 180) (length 2.54)
\t\t\t\t(name "~" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "6" (effects (font (size 1.27 1.27)))))
\t\t\t(pin no_connect line (at -2.54 7.62 270) (length 2.54)
\t\t\t\t(name "NC" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "1" (effects (font (size 1.27 1.27)))))
\t\t\t(pin no_connect line (at 2.54 7.62 270) (length 2.54)
\t\t\t\t(name "NC" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "5" (effects (font (size 1.27 1.27)))))
\t\t\t(pin no_connect line (at 2.54 -7.62 90) (length 2.54)
\t\t\t\t(name "NC" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "8" (effects (font (size 1.27 1.27)))))
\t\t)
\t\t(embedded_fonts no)
\t)"""


def main() -> None:
    PRETTY.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)

    footprints = [
        (32, "CardEdge_DualReadout_32pos_P4.76mm_Stagger1.59mm", "XA/XB"),
        (33, "CardEdge_DualReadout_33pos_P4.76mm_Stagger1.59mm", "YA/YB"),
    ]
    for pos, name, axis in footprints:
        path = PRETTY / f"{name}.kicad_mod"
        path.write_text(gen_receptacle(pos, name, axis))
        print(f"wrote {path}")

    symbols = [
        edge_symbol(
            "CoreEdge_XA_64",
            64,
            "core_memory:CardEdge_DualReadout_32pos_P4.76mm_Stagger1.59mm",
            "Core plane XA mate — 32-pos dual-readout (64 pins), odd=top even=bottom",
        ),
        edge_symbol(
            "CoreEdge_XB_64",
            64,
            "core_memory:CardEdge_DualReadout_32pos_P4.76mm_Stagger1.59mm",
            "Core plane XB mate — 32-pos dual-readout (64 pins)",
        ),
        edge_symbol(
            "CoreEdge_YA_66",
            66,
            "core_memory:CardEdge_DualReadout_33pos_P4.76mm_Stagger1.59mm",
            "Core plane YA mate — 33-pos dual-readout (66 pins); 65/66 sense shunt to AGND",
        ),
        edge_symbol(
            "CoreEdge_YB_66",
            66,
            "core_memory:CardEdge_DualReadout_33pos_P4.76mm_Stagger1.59mm",
            "Core plane YB mate — 33-pos dual-readout (66 pins); 65/66 differential sense / inhibit",
        ),
        fds8958a_symbol(),
        opa192_symbol(),
    ]

    header = """(kicad_symbol_lib
\t(version 2025.11.26)
\t(generator "gen_libs.py")
\t(generator_version "1.0")
"""
    SYM_PATH.write_text(header + "\n".join(symbols) + "\n)\n")
    print(f"wrote {SYM_PATH}")


if __name__ == "__main__":
    main()
