#!/usr/bin/env python3
"""Plot write, read, and write-back of a 1 and a 0 on all four cores.

Runs models/array2x2_cycle_tb.cir through libngspice and writes
plots/array2x2_cycle.png.

  python3 kicad/core_element_sim/plot_cycle.py
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_response import NgSpice

ROOT = Path(__file__).resolve().parent
DECK = ROOT / "models" / "array2x2_cycle_tb.cir"
OUT = ROOT / "plots" / "array2x2_cycle.png"

# (name, t0 seconds, color) — 4 µs pulses. One core color for its seven pulses.
_CORE_COLOR = {
    "X00": "#4c78a8",
    "X01": "#f58518",
    "X10": "#54a24b",
    "X11": "#e45756",
}
_STEPS = (
    ("write 1", 0),
    ("read 1", 6),
    ("write-back 1", 12),
    ("clear", 18),
    ("write 0", 24),
    ("read 0", 30),
    ("write-back 0", 36),
)
_START_US = (("X00", 2), ("X01", 44), ("X10", 86), ("X11", 128))
EVENTS = tuple(
    (f"{core} {step}", (t0 + off) * 1e-6, _CORE_COLOR[core])
    for core, t0 in _START_US
    for step, off in _STEPS
)
PULSE_US = 4.0
CORES = (
    ("X00", "x00.xcore.m", "#4c78a8"),
    ("X01", "x01.xcore.m", "#f58518"),
    ("X10", "x10.xcore.m", "#54a24b"),
    ("X11", "x11.xcore.m", "#e45756"),
)


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


def plot(data: dict[str, np.ndarray], path: Path) -> None:
    t_us = data["t"] * 1e6
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "axes.grid": True,
            "grid.alpha": 0.35,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(3, 1, figsize=(13.6, 8.4), sharex=True, constrained_layout=True)

    ax = axes[0]
    ax.plot(t_us, data["ixa0"] * 1e3, color="#4c78a8", label="XA0")
    ax.plot(t_us, data["ixa1"] * 1e3, color="#f58518", label="XA1")
    ax.plot(t_us, data["iya0"] * 1e3, color="#54a24b", label="YA0")
    ax.plot(t_us, data["iya1"] * 1e3, color="#e45756", label="YA1")
    ax.plot(t_us, data["iinh"] * 1e3, color="#b279a2", ls="--", label="Inhibit")
    ax.plot(t_us, data["iccsx"] * 1e3, color="#4c78a8", lw=1.2, ls=":", label="X CCS")
    ax.plot(t_us, data["iccsy"] * 1e3, color="#54a24b", lw=1.2, ls=":", label="Y CCS")
    ax.plot(t_us, data["iccsi"] * 1e3, color="#b279a2", lw=1.2, ls=":", label="Inhibit CCS")
    for _name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Current (mA)")
    ax.set_title("One 400 mA CCS per axis, one line at a time. A→B is positive")
    ax.legend(loc="upper right", ncol=4)
    ax.set_ylim(-550, 700)

    ax = axes[1]
    ax.axhspan(15, 80, color="#e45756", alpha=0.08)
    ax.axhspan(-80, -15, color="#e45756", alpha=0.08)
    ax.plot(t_us, data["vs"] * 1e3, color="0.1", lw=1.1, label="YA65 − YB66")
    for _name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Sense (mV)")
    ax.set_title("The wide pulse is the flip. Write 0 and its write-back have none")
    ax.legend(loc="upper right")

    ax = axes[2]
    for name, _vec, color in CORES:
        ax.plot(t_us, data[name], color=color, lw=1.3, label=name)
    for _name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Remanence m")
    ax.set_xlabel("Time (µs)")
    ax.set_title("Each core starts at 0, stores 1, then is cleared and left at 0")
    ax.set_ylim(-1.35, 1.35)
    ax.legend(loc="upper right", ncol=4)
    ax.set_xlim(0, 170)

    fig.suptitle("Write, read, and write-back of 1 and 0 on all four cores, ngspice", fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def report(data: dict[str, np.ndarray], path: Path = OUT) -> None:
    print(f"wrote {path}")
    print(f"{'event':<20} {'sense mV':>9}  cores after")
    for name, t0, _color in EVENTS:
        t = data["t"]
        mask = (t >= t0) & (t <= t0 + 4.2e-6)
        vs = data["vs"][mask] * 1e3
        peak = vs[np.argmax(np.abs(vs))]
        i_after = int(np.argmin(np.abs(t - (t0 + 4.5e-6))))
        states = " ".join(f"{core}={data[core][i_after]:+.2f}" for core, _v, _c in CORES)
        print(f"{name:<20} {peak:9.2f}  {states}")


def main() -> None:
    data = simulate()
    plot(data, OUT)
    report(data)


if __name__ == "__main__":
    main()
