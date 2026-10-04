#!/usr/bin/env python3
"""Plot the 2×2 addressing transient.

Runs models/array2x2_tb.cir through libngspice and writes
plots/array2x2_response.png.

  python3 kicad/core_element_sim/plot_array.py
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
DECK = ROOT / "models" / "array2x2_tb.cir"
OUT = ROOT / "plots" / "array2x2_response.png"

# (name, t0 seconds, color) — 4 µs pulses in the deck (1 µs rise, 2 µs flat, 1 µs fall).
EVENTS = (
    ("Half-select", 2.0e-6, "#9e9ac8"),
    ("Read 00", 8.0e-6, "#4c78a8"),
    ("Read 01", 14.0e-6, "#f58518"),
    ("Read 10", 20.0e-6, "#54a24b"),
    ("Read 11", 26.0e-6, "#e45756"),
    ("Restore 00", 32.0e-6, "#72b7b2"),
    ("Inhibit 01", 38.0e-6, "#b279a2"),
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
        "iccs": ng.vector("piccs"),
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
    fig, axes = plt.subplots(3, 1, figsize=(10.2, 8.2), sharex=True, constrained_layout=True)

    ax = axes[0]
    ax.plot(t_us, data["ixa0"] * 1e3, color="#4c78a8", label="XA0")
    ax.plot(t_us, data["ixa1"] * 1e3, color="#f58518", label="XA1")
    ax.plot(t_us, data["iya0"] * 1e3, color="#54a24b", label="YA0")
    ax.plot(t_us, data["iya1"] * 1e3, color="#e45756", label="YA1")
    ax.plot(t_us, data["iinh"] * 1e3, color="#b279a2", ls="--", label="Inhibit")
    ax.plot(t_us, data["iccs"] * 1e3, color="0.15", lw=1.4, label="CCS")
    for _name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Current (mA)")
    ax.set_title("CCS holds the sum at 400 mA. One line takes it; two lines share it")
    ax.legend(loc="upper right", ncol=4)
    ax.set_ylim(-550, 700)

    ax = axes[1]
    ax.plot(t_us, data["vs"] * 1e3, color="0.1", lw=1.1, label="YA65 − YB66")
    for name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Sense (mV)")
    ax.set_title("Half-select edge is the tall spike. Coincident windows stay small; nothing flips")
    ax.legend(loc="upper right")

    ax = axes[2]
    for name, _vec, color in CORES:
        ax.plot(t_us, data[name], color=color, lw=1.3, label=name)
    for name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + PULSE_US, color=color, alpha=0.10)
    ax.set_ylabel("Remanence m")
    ax.set_xlabel("Time (µs)")
    ax.set_title("The shared sink stays under Hc, so every core remains +Br")
    ax.set_ylim(-1.35, 1.35)
    ax.legend(loc="upper right", ncol=4)
    ax.set_xlim(0, 46)

    fig.suptitle("2×2 MCE with the CCS on the return, ngspice", fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def report(data: dict[str, np.ndarray]) -> None:
    print(f"wrote {OUT}")
    print(f"{'event':<14} {'sense mV':>9}  cores after")
    for name, t0, _color in EVENTS:
        t = data["t"]
        mask = (t >= t0) & (t <= t0 + 4.2e-6)
        vs = data["vs"][mask] * 1e3
        peak = vs[np.argmax(np.abs(vs))]
        i_after = int(np.argmin(np.abs(t - (t0 + 4.5e-6))))
        states = " ".join(f"{core}={data[core][i_after]:+.2f}" for core, _v, _c in CORES)
        print(f"{name:<14} {peak:9.2f}  {states}")


def main() -> None:
    data = simulate()
    plot(data, OUT)
    report(data)


if __name__ == "__main__":
    main()
