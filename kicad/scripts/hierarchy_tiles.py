"""Octal / line steer tile ABI and pin-budget helpers.

See docs/hierarchy_abi.md. Used by gen_pipeline and future steer generators.
The live monolithic sheet is steer_64.kicad_sch (renamed from steer_2x2).
"""

from __future__ import annotations

from dataclasses import dataclass


AXES = ("X", "Y")
GROUPS = range(8)
LINES_PER_GROUP = 8
N_LINES = 64


@dataclass(frozen=True)
class OctalTile:
    """One HS group on one axis, FWD+REV diodes for eight lines."""

    axis: str
    group: int

    def __post_init__(self) -> None:
        if self.axis not in AXES:
            raise ValueError(self.axis)
        if self.group not in GROUPS:
            raise ValueError(self.group)

    @property
    def sheet_name(self) -> str:
        return f"steer_octal_{self.axis}_g{self.group}.kicad_sch"

    @property
    def lines(self) -> list[int]:
        base = self.group * LINES_PER_GROUP
        return list(range(base, base + LINES_PER_GROUP))

    def pin_nets(self) -> dict[str, str]:
        """Hierarchical pin name → parent net (XA/XB-style plane ends)."""
        a, g = self.axis, self.group
        a_name, b_name = f"{a}A", f"{a}B"
        pins: dict[str, str] = {
            "HS": f"{a}HS{g}",
            "HSR": f"{a}HS{g}R",
        }
        for k, line in enumerate(self.lines):
            ls = line % LINES_PER_GROUP
            pins[f"LS{k}"] = f"{a}LS{ls}"
            pins[f"LSR{k}"] = f"{a}LS{ls}R"
            pins[f"A{k}"] = f"{a_name}{line}"
            pins[f"B{k}"] = f"{b_name}{line}"
        return pins

    def diodes(self) -> list[tuple[str, str]]:
        """(anode, cathode) using XA/XB-style plane names (matches steer_64)."""
        a = self.axis
        a_name, b_name = f"{a}A", f"{a}B"
        g = self.group
        out: list[tuple[str, str]] = []
        for line in self.lines:
            ls = line % LINES_PER_GROUP
            out.append((f"{a}HS{g}", f"{b_name}{line}"))
            out.append((f"{a_name}{line}", f"{a}LS{ls}"))
            out.append((f"{a}HS{g}R", f"{a_name}{line}"))
            out.append((f"{b_name}{line}", f"{a}LS{ls}R"))
        return out


@dataclass(frozen=True)
class LineTile:
    """Single-line steer tile: four diodes, six pins."""

    axis: str
    line: int

    def __post_init__(self) -> None:
        if self.axis not in AXES:
            raise ValueError(self.axis)
        if not 0 <= self.line < N_LINES:
            raise ValueError(self.line)

    @property
    def group(self) -> int:
        return self.line // LINES_PER_GROUP

    @property
    def ls(self) -> int:
        return self.line % LINES_PER_GROUP

    def pin_nets(self) -> dict[str, str]:
        a, line, g, ls = self.axis, self.line, self.group, self.ls
        return {
            "HS": f"{a}HS{g}",
            "LS": f"{a}LS{ls}",
            "HSR": f"{a}HS{g}R",
            "LSR": f"{a}LS{ls}R",
            "A": f"{a}A{line}",
            "B": f"{a}B{line}",
        }

    def diodes(self) -> list[tuple[str, str]]:
        p = self.pin_nets()
        return [
            (p["HS"], p["B"]),
            (p["A"], p["LS"]),
            (p["HSR"], p["A"]),
            (p["B"], p["LSR"]),
        ]


def all_octal_tiles() -> list[OctalTile]:
    return [OctalTile(axis, g) for axis in AXES for g in GROUPS]


def pin_budget() -> dict[str, int]:
    """Documented budgets for coverage / ABI checks."""
    octal = OctalTile("X", 0)
    return {
        "monolithic_steer_pins": 64 + 256,
        "monolithic_magnetic_pins": 256 + 2,
        "root_plane_pin_instances_legacy": 512,
        "octal_tile_pins": len(octal.pin_nets()),
        "octal_tile_count": len(all_octal_tiles()),
        "octal_diodes_total": sum(len(t.diodes()) for t in all_octal_tiles()),
        "line_tile_pins": len(LineTile("X", 0).pin_nets()),
        "line_tile_count": N_LINES * len(AXES),
        "plane_drive_ends": 256,
    }


def monolithic_diode_set() -> set[tuple[str, str]]:
    """Same diode net pairs as gen_xy_drive_page._steer_nets (XA/XB naming)."""
    diodes: set[tuple[str, str]] = set()
    for axis, a_name, b_name in (("X", "XA", "XB"), ("Y", "YA", "YB")):
        for line in range(N_LINES):
            hs, ls = divmod(line, LINES_PER_GROUP)
            diodes.add((f"{axis}HS{hs}", f"{b_name}{line}"))
            diodes.add((f"{a_name}{line}", f"{axis}LS{ls}"))
            diodes.add((f"{axis}HS{hs}R", f"{a_name}{line}"))
            diodes.add((f"{b_name}{line}", f"{axis}LS{ls}R"))
    return diodes


def octal_diode_set() -> set[tuple[str, str]]:
    """Octal tiles use XA/XB-style names to match the monolithic sheet."""
    diodes: set[tuple[str, str]] = set()
    for axis, a_name, b_name in (("X", "XA", "XB"), ("Y", "YA", "YB")):
        for g in GROUPS:
            for k in range(LINES_PER_GROUP):
                line = g * LINES_PER_GROUP + k
                diodes.add((f"{axis}HS{g}", f"{b_name}{line}"))
                diodes.add((f"{a_name}{line}", f"{axis}LS{k}"))
                diodes.add((f"{axis}HS{g}R", f"{a_name}{line}"))
                diodes.add((f"{b_name}{line}", f"{axis}LS{k}R"))
    return diodes


def assert_octal_covers_monolithic() -> None:
    mono = monolithic_diode_set()
    tiled: set[tuple[str, str]] = set()
    for t in all_octal_tiles():
        tiled.update(t.diodes())
    if mono != tiled:
        raise SystemExit(
            f"octal mismatch missing={len(mono - tiled)} extra={len(tiled - mono)}"
        )


if __name__ == "__main__":
    b = pin_budget()
    for k, v in b.items():
        print(f"{k}={v}")
    assert b["octal_tile_pins"] == 34
    assert b["octal_diodes_total"] == 512
    assert_octal_covers_monolithic()
    print("hierarchy_tiles OK")
