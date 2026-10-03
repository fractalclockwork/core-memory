#!/usr/bin/env python3
"""Plot the isolated core-element transient for comparison with published traces.

Runs models/coremem_tb.cir through libngspice (the same library KiCad uses)
and writes plots/coremem_response.png.

  python3 kicad/core_element_sim/plot_response.py

Literature markers on the figure are the usual single-core targets, not a
digitized scope photo: a read-1 of about 20–50 mV lasting about 1 µs, a much
smaller read-0 / half-select disturb, and a square loop with Br/Bs near 0.9.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
DECK = ROOT / "models" / "coremem_tb.cir"
OUT = ROOT / "plots" / "coremem_response.png"

# Published single-core sense amplitude for a full-select "1".
LIT_MV = (20.0, 50.0)
# Published peaking / switching time.
LIT_US = 1.0

EVENTS = (
    ("Half-select", 2.0e-6, "#4c78a8"),
    ("Read 1", 6.0e-6, "#e45756"),
    ("Read 0", 10.0e-6, "#54a24b"),
    ("Restore", 14.0e-6, "#f58518"),
)


class VectorInfo(ctypes.Structure):
    """ngspice sharedspice.h vector_info."""

    _fields_ = [
        ("v_name", ctypes.c_char_p),
        ("v_type", ctypes.c_int),
        ("v_flags", ctypes.c_short),
        ("v_realdata", ctypes.POINTER(ctypes.c_double)),
        ("v_compdata", ctypes.c_void_p),
        ("v_length", ctypes.c_int),
    ]


class NgSpice:
    def __init__(self) -> None:
        self.lib = ctypes.CDLL("libngspice.so.0")
        send_char = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
        send_stat = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
        ngexit = ctypes.CFUNCTYPE(
            ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p
        )
        send_data = ctypes.CFUNCTYPE(
            ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p
        )
        send_init = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
        bg = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
        self._keep = (
            send_char(lambda *args: 0),
            send_stat(lambda *args: 0),
            ngexit(lambda *args: 0),
            send_data(lambda *args: 0),
            send_init(lambda *args: 0),
            bg(lambda *args: 0),
        )
        self.lib.ngSpice_Init.argtypes = [
            send_char,
            send_stat,
            ngexit,
            send_data,
            send_init,
            bg,
            ctypes.c_void_p,
        ]
        self.lib.ngSpice_Init.restype = ctypes.c_int
        self.lib.ngSpice_Command.argtypes = [ctypes.c_char_p]
        self.lib.ngSpice_Command.restype = ctypes.c_int
        self.lib.ngGet_Vec_Info.argtypes = [ctypes.c_char_p]
        self.lib.ngGet_Vec_Info.restype = ctypes.POINTER(VectorInfo)
        if self.lib.ngSpice_Init(*self._keep, None) != 0:
            raise RuntimeError("ngSpice_Init failed")

    def command(self, text: str) -> None:
        if self.lib.ngSpice_Command(text.encode()) != 0:
            raise RuntimeError(text)

    def vector(self, name: str) -> np.ndarray:
        info = self.lib.ngGet_Vec_Info(name.encode())
        if not info:
            raise KeyError(name)
        n = info.contents.v_length
        raw = np.ctypeslib.as_array(info.contents.v_realdata, shape=(n,))
        return np.array(raw, dtype=float, copy=True)


def simulate() -> dict[str, np.ndarray]:
    ng = NgSpice()
    ng.command(f"source {DECK}")
    return {
        "t": ng.vector("time"),
        "vs": ng.vector("s1"),
        "b": ng.vector("b"),
        "h": ng.vector("xcore.h"),
        "m": ng.vector("xcore.m"),
        "ix": ng.vector("v.xcore.vx#branch"),
        "iy": ng.vector("v.xcore.vy#branch"),
    }


def _window(data: dict[str, np.ndarray], t0: float, span: float = 2.5e-6) -> tuple[np.ndarray, np.ndarray]:
    t = data["t"]
    mask = (t >= t0) & (t <= t0 + span)
    return (t[mask] - t0) * 1e6, data["vs"][mask] * 1e3


def plot(data: dict[str, np.ndarray], path: Path) -> None:
    t_us = data["t"] * 1e6
    vs_mv = data["vs"] * 1e3
    ix_ma = data["ix"] * 1e3
    iy_ma = data["iy"] * 1e3

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
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(10.2, 7.4),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 1.15]},
    )

    ax = axes[0, 0]
    ax.plot(t_us, ix_ma, color="#4c78a8", label="Ix winding")
    ax.plot(t_us, iy_ma, color="#f58518", label="Iy winding")
    ax.axhline(-400, color="0.45", lw=0.6, ls=":", alpha=0.8)
    ax.axhline(400, color="0.45", lw=0.6, ls=":", alpha=0.8)
    ax.set_xlim(0, 18)
    ax.set_ylim(-620, 620)
    ax.set_xlabel("Time (µs)")
    ax.set_ylabel("Winding current (mA)")
    ax.set_title("Each wire at ±400 mA; full-select is both")
    ax.legend(loc="upper right")

    ax = axes[0, 1]
    ax.axhspan(-LIT_MV[1], -LIT_MV[0], color="#e45756", alpha=0.12, label="Literature read-1, 20–50 mV")
    ax.axhspan(LIT_MV[0], LIT_MV[1], color="#e45756", alpha=0.12)
    ax.plot(t_us, vs_mv, color="0.1", lw=1.1)
    for name, t0, color in EVENTS:
        ax.axvspan(t0 * 1e6, t0 * 1e6 + 2.0, color=color, alpha=0.08)
    ax.set_xlim(0, 18)
    ax.set_xlabel("Time (µs)")
    ax.set_ylabel("Sense voltage (mV)")
    ax.set_title("Sense winding, one turn")
    ax.legend(loc="lower right")

    ax = axes[1, 0]
    ax.axhspan(-LIT_MV[1], -LIT_MV[0], color="#e45756", alpha=0.10)
    ax.axhspan(LIT_MV[0], LIT_MV[1], color="#e45756", alpha=0.10)
    ax.axvline(LIT_US, color="0.45", lw=0.8, ls="--", label="1 µs published width")
    for name, t0, color in EVENTS:
        tr, vr = _window(data, t0)
        ax.plot(tr, vr, color=color, lw=1.3, label=name)
    ax.set_xlim(0, 2.5)
    ax.set_xlabel("Time from drive edge (µs)")
    ax.set_ylabel("Sense voltage (mV)")
    ax.set_title("Pulses aligned to the current edge")
    ax.legend(loc="lower right")

    ax = axes[1, 1]
    ax.plot(data["h"], data["b"], color="#4c78a8", lw=1.2)
    for h in (-150, 150):
        ax.axvline(h, color="0.45", lw=0.7, ls="--")
    ax.axhline(0.18, color="#e45756", lw=0.7, ls=":")
    ax.axhline(-0.18, color="#e45756", lw=0.7, ls=":")
    ax.axhline(0.20, color="0.35", lw=0.6, ls=":")
    ax.axhline(-0.20, color="0.35", lw=0.6, ls=":")
    ax.set_xlabel("H (A/m)")
    ax.set_ylabel("B (T)")
    ax.set_title("B–H path, Br/Bs = 0.90")
    ax.set_xlim(-320, 320)
    ax.set_ylim(-0.25, 0.25)
    ax.text(160, 0.195, "Bs", fontsize=8, color="0.25")
    ax.text(160, 0.155, "Br", fontsize=8, color="#e45756")
    ax.text(155, 0.02, "Hc", fontsize=8, color="0.35")

    fig.suptitle("50-mil memory core, ngspice behavioral model", fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def report(data: dict[str, np.ndarray]) -> None:
    print(f"wrote {OUT}")
    print(f"{'event':<16} {'peak mV':>8} {'half-amp µs':>12} {'m after':>8}")
    for name, t0, _color in EVENTS:
        tr, vr = _window(data, t0, span=2.2e-6)
        peak = vr[np.argmax(np.abs(vr))]
        half = 0.5 * peak
        i_peak = int(np.argmax(np.abs(vr)))
        lo = i_peak
        while lo > 0 and abs(vr[lo]) >= abs(half):
            lo -= 1
        hi = i_peak
        while hi < len(vr) - 1 and abs(vr[hi]) >= abs(half):
            hi += 1
        width = tr[hi] - tr[lo]
        m_after = data["m"][np.argmin(np.abs(data["t"] - (t0 + 3e-6)))]
        print(f"{name:<16} {peak:8.2f} {width:12.2f} {m_after:8.3f}")


def main() -> None:
    data = simulate()
    plot(data, OUT)
    report(data)


if __name__ == "__main__":
    main()
