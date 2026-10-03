#!/usr/bin/env python3
"""Remove leftover flat-drive wires/labels inside Drive FWD/REV root boxes.

Keeps: Drive sheet symbols, sheet-pin labels + fanout wires, VDRIVE power/flag,
U2 power unit wiring, and updated legend texts.

Idempotent. Run after hierarchy moves leave orphan stubs in the Drive rectangles.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

SCH = Path(__file__).resolve().parents[1] / "core" / "core.kicad_sch"

FWD = (305.0, 15.0, 540.0, 188.0)
REV = (536.0, 15.0, 789.0, 188.0)
BOXES = (FWD, REV)

OBSOLETE_TEXT_SNIPS = (
    "TC4427A → X/Y_HS0; TC4426A",
    "TC4427A → X/Y_HS0r; TC4426A",
    "QX/QY FDS8958A + SS14",
    "QX0r/QY0r FDS8958A",
    "DRIVE FWD — X0/Y0 matrix + gate",
    "DRIVE REV — X0/Y0 matrix + gate",
)

LEGEND_FWD = "DRIVE — Drive Block (N=axis, n=line); X0 FWD wired for 1×1 bring-up"


def extract_blocks(text: str, tag: str):
    pattern = re.compile(rf"^\t\({tag}\b", re.M)
    for m in pattern.finditer(text):
        start = m.start()
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    yield start, i + 1, text[start : i + 1]
                    break


def in_any_box(x: float, y: float, margin: float = 1.0) -> bool:
    for x1, y1, x2, y2 in BOXES:
        if x1 - margin <= x <= x2 + margin and y1 - margin <= y <= y2 + margin:
            return True
    return False


def at_of(block: str):
    m = re.search(r"\(at ([0-9.-]+) ([0-9.-]+)", block)
    return (float(m.group(1)), float(m.group(2))) if m else None


def main() -> None:
    sch = SCH.read_text()

    pin_pts: set[tuple[float, float]] = set()
    for _, _, block in extract_blocks(sch, "sheet"):
        name = re.search(r'\(property "Sheetname" "([^"]+)"', block)
        if not name or "Drive" not in name.group(1):
            continue
        for pm in re.finditer(r'\(pin "[^"]+" [^\s]+\s+\(at ([0-9.-]+) ([0-9.-]+)', block):
            pin_pts.add((round(float(pm.group(1)), 2), round(float(pm.group(2)), 2)))

    keep_label_keys: set[tuple[float, float, str]] = set()
    for _, _, block in extract_blocks(sch, "label"):
        m = re.search(r'\(label "([^"]+)"\s+\(at ([0-9.-]+) ([0-9.-]+)', block)
        if not m:
            continue
        name, x, y = m.group(1), float(m.group(2)), float(m.group(3))
        if not in_any_box(x, y):
            continue
        for px, py in pin_pts:
            if abs(y - py) < 0.51 and abs(x - px) < 30:
                keep_label_keys.add((round(x, 2), round(y, 2), name))
                break
        if name == "VDRIVE" and y < 35:
            keep_label_keys.add((round(x, 2), round(y, 2), name))

    pwr_pts: set[tuple[float, float]] = set()
    for _, _, block in extract_blocks(sch, "symbol"):
        refm = re.search(r'\(property "Reference" "([^"]+)"', block)
        if not refm or refm.group(1) not in {"#PWR_VDRIVE", "#FLG_VDRIVE"}:
            continue
        at = at_of(block)
        if at:
            pwr_pts.add((round(at[0], 2), round(at[1], 2)))

    # U2 power unit + rails (must survive box cleanup)
    u2_pwr = {
        (311.15, 32.87),
        (311.15, 30.33),
        (311.15, 22.71),
        (311.15, 53.19),
        (311.15, 55.73),
        (311.15, 63.35),
    }

    keep_pts: set[tuple[float, float]] = (
        set(pin_pts) | pwr_pts | {(x, y) for x, y, _ in keep_label_keys} | u2_pwr
    )

    def near_keep(p: tuple[float, float], tol: float = 0.2) -> bool:
        x, y = p
        return any(abs(x - kx) <= tol and abs(y - ky) <= tol for kx, ky in keep_pts)

    for _ in range(4):
        added = False
        for _, _, block in extract_blocks(sch, "wire"):
            pts = [
                (round(float(a), 2), round(float(b), 2))
                for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", block)
            ]
            if not pts or not any(in_any_box(x, y) for x, y in pts):
                continue
            if any(near_keep(p) for p in pts):
                for p in pts:
                    if p not in keep_pts:
                        keep_pts.add(p)
                        added = True
        for _, _, block in extract_blocks(sch, "junction"):
            at = at_of(block)
            if not at or not in_any_box(*at):
                continue
            p = (round(at[0], 2), round(at[1], 2))
            if near_keep(p) and p not in keep_pts:
                keep_pts.add(p)
                added = True
        if not added:
            break

    to_remove: list[tuple[int, int, str]] = []

    def mark(start: int, end: int, reason: str) -> None:
        to_remove.append((start, end, reason))

    for start, end, block in extract_blocks(sch, "wire"):
        pts = [
            (round(float(a), 2), round(float(b), 2))
            for a, b in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", block)
        ]
        if not pts or not any(in_any_box(x, y) for x, y in pts):
            continue
        if any(near_keep(p) for p in pts):
            continue
        mark(start, end, "orphan_wire")

    for start, end, block in extract_blocks(sch, "junction"):
        at = at_of(block)
        if not at or not in_any_box(*at):
            continue
        if near_keep((round(at[0], 2), round(at[1], 2))):
            continue
        mark(start, end, "orphan_junction")

    for start, end, block in extract_blocks(sch, "no_connect"):
        at = at_of(block)
        if at and in_any_box(*at):
            mark(start, end, "orphan_nc")

    for start, end, block in extract_blocks(sch, "label"):
        m = re.search(r'\(label "([^"]+)"\s+\(at ([0-9.-]+) ([0-9.-]+)', block)
        if not m:
            continue
        name, x, y = m.group(1), float(m.group(2)), float(m.group(3))
        if not in_any_box(x, y):
            continue
        key = (round(x, 2), round(y, 2), name)
        if key in keep_label_keys:
            continue
        if name == "VDRIVE" and near_keep((round(x, 2), round(y, 2))):
            continue
        mark(start, end, f"orphan_label:{name}")

    for start, end, block in extract_blocks(sch, "text"):
        tm = re.search(r'\(text "([^"]*)"', block)
        if tm and any(s in tm.group(1) for s in OBSOLETE_TEXT_SNIPS):
            mark(start, end, "obsolete_text")

    to_remove.sort(key=lambda t: t[0], reverse=True)
    seen: set[tuple[int, int]] = set()
    new_sch = sch
    removed = 0
    for start, end, _reason in to_remove:
        if (start, end) in seen:
            continue
        seen.add((start, end))
        if end < len(new_sch) and new_sch[end] == "\n":
            end += 1
        new_sch = new_sch[:start] + new_sch[end:]
        removed += 1

    def ensure_legend(text: str, at: tuple[float, float], body: str) -> str:
        if text in body:
            return body
        block = f'''\t(text "{text}"
\t\t(exclude_from_sim no)
\t\t(at {at[0]} {at[1]} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t\t(uuid "{uuid.uuid4()}")
\t)
'''
        if body.rstrip().endswith(")"):
            return body.rstrip()[:-1] + block + ")\n"
        return body + block

    new_sch = ensure_legend(LEGEND_FWD, (400.0, 10.0), new_sch)

    # Ensure U2 power verticals exist
    need_segs = {
        ((311.15, 32.87), (311.15, 30.33)),
        ((311.15, 30.33), (311.15, 22.71)),
        ((311.15, 53.19), (311.15, 55.73)),
        ((311.15, 55.73), (311.15, 63.35)),
    }

    def has_seg(a, b) -> bool:
        for _, _, block in extract_blocks(new_sch, "wire"):
            pts = [
                (round(float(x), 2), round(float(y), 2))
                for x, y in re.findall(r"\(xy ([0-9.-]+) ([0-9.-]+)\)", block)
            ]
            if len(pts) == 2 and (pts[0], pts[1]) in {(a, b), (b, a)}:
                return True
        return False

    def wire(a, b) -> str:
        return f'''\t(wire
\t\t(pts
\t\t\t(xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{uuid.uuid4()}")
\t)
'''

    def junction(p) -> str:
        return f'''\t(junction
\t\t(at {p[0]} {p[1]})
\t\t(diameter 0)
\t\t(color 0 0 0 0)
\t\t(uuid "{uuid.uuid4()}")
\t)
'''

    extras = []
    for a, b in need_segs:
        if not has_seg(a, b):
            extras.append(wire(a, b))
    for p in ((311.15, 30.33), (311.15, 55.73)):
        if not any(
            at_of(block) and abs(at_of(block)[0] - p[0]) < 0.01 and abs(at_of(block)[1] - p[1]) < 0.01
            for _, _, block in extract_blocks(new_sch, "junction")
        ):
            extras.append(junction(p))

    # SENSE_P label stub (label y=35.41 → net y=35.56)
    sense_stub = ((210.82, 35.41), (210.82, 35.56))
    if not has_seg(*sense_stub):
        extras.append(wire(*sense_stub))

    if extras:
        body = new_sch.rstrip()
        new_sch = body[:-1] + "\n".join(extras) + "\n)\n"

    SCH.write_text(new_sch)
    print(f"Removed {removed} orphan blocks; wrote {SCH}")


if __name__ == "__main__":
    main()
