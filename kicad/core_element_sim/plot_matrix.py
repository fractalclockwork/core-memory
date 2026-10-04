#!/usr/bin/env python3
"""Plot the 2x2 diode-matrix cycle. Same figure as plot_cycle.py."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np

from plot_cycle import CORES, plot, report
from plot_response import NgSpice

ROOT = Path(__file__).resolve().parent
DECK = ROOT / "models" / "array2x2_matrix_tb.cir"
OUT = ROOT / "plots" / "array2x2_matrix.png"


def simulate() -> dict[str, np.ndarray]:
    os.chdir(DECK.parent)
    ng = NgSpice()
    ng.command(f"source {DECK}")
    data = {
        "t": ng.vector("time"),
        "vs": ng.vector("diff"),
        "ixa0": ng.vector("pxa0"),
        "ixa1": ng.vector("pxa1"),
        "iya0": ng.vector("pya0"),
        "iya1": ng.vector("pya1"),
        "iinh": ng.vector("pinh"),
        "iccsx": ng.vector("piccsx"),
        "iccsy": ng.vector("piccsy"),
        "iccsi": ng.vector("piccsi"),
    }
    for name, vec, _color in CORES:
        data[name] = ng.vector(vec)
    return data


def main() -> None:
    data = simulate()
    plot(data, OUT)
    report(data, OUT)


if __name__ == "__main__":
    main()
