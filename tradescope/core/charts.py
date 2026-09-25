"""Matplotlib chart helpers with one consistent style.

Palette: validated categorical order (blue, orange, aqua, yellow, magenta, green,
violet, red). Diverging: blue <-> red with a neutral grey midpoint.
"""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SURFACE, TEXT, TEXT2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
GOOD, BAD, NEUTRAL = "#1c5cab", "#c62f2f", "#f0efec"
DIVERGING = LinearSegmentedColormap.from_list("div", ["#b3261e", "#e66767", NEUTRAL, "#6da7ec", "#1c5cab"])


THOUSANDS = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")


def _setup() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    latin = [f for f in ["Segoe UI", "Inter", "Helvetica Neue", "Arial"] if f in available]
    cjk = [f for f in ["Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "Noto Sans TC", "Noto Sans CJK JP",
                       "Heiti TC", "Microsoft YaHei", "Arial Unicode MS"] if f in available]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": latin + cjk + ["DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT2, "axes.titlecolor": TEXT,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "lines.linewidth": 2, "legend.frameon": False, "legend.fontsize": 9,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
    })


_setup()


def fig_ax(w: float = 10, h: float = 3.8):
    fig, ax = plt.subplots(figsize=(w, h), dpi=110)
    return fig, ax


def _date_axis(ax) -> None:
    loc = mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def fmt_num(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    a = abs(v)
    return f"{v:,.2f}" if a >= 100 else f"{v:,.4f}" if a >= 1 else f"{v:,.6f}"


def to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    return buf.getvalue()


def line(series: dict[str, pd.Series], title: str = "", ylabel: str = "", label_last: bool = True,
         styles: dict[str, dict] | None = None, markers: dict[str, pd.Series] | None = None,
         band: pd.DataFrame | None = None, h: float = 3.8, w: float = 10):
    """Multiple series on ONE axis. `styles` overrides per series (e.g. dashed)."""
    fig, ax = fig_ax(w=w, h=h)
    styles = styles or {}
    for i, (name, s) in enumerate(series.items()):
        s = s.dropna()
        if s.empty:
            continue
        st = {"color": PALETTE[i % len(PALETTE)], "label": name, **styles.get(name, {})}
        ax.plot(s.index, s.values, **st)
        if label_last and len(series) <= 4 and not st.get("linestyle"):
            ax.annotate(fmt_num(s.iloc[-1]), (s.index[-1], s.iloc[-1]), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=9, color=TEXT2)
    if band is not None and not band.empty:
        ax.fill_between(band.index, band["low"], band["high"], color=PALETTE[0], alpha=0.12, linewidth=0)
    for name, pts in (markers or {}).items():
        ax.scatter(pts.index, pts.values, s=60, zorder=5, color=PALETTE[3],
                   edgecolor=SURFACE, linewidth=2, label=name)
        for x, y in pts.items():
            ax.annotate(fmt_num(y), (x, y), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=8, color=TEXT2)
    _date_axis(ax)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if len(series) + len(markers or {}) > 1:
        ax.legend(loc="upper left", ncols=min(4, len(series) + len(markers or {})))
    ax.margins(x=0.06)
    fig.tight_layout()
    return fig


def grouped_bars(categories: list, groups: dict[str, list], title: str = "", ylabel: str = "", h: float = 3.8):
    fig, ax = fig_ax(h=h)
    n = len(groups)
    width = 0.8 / n
    x = np.arange(len(categories))
    for i, (name, vals) in enumerate(groups.items()):
        ax.bar(x + (i - (n - 1) / 2) * width, vals, width=width * 0.92, label=name,
               color=PALETTE[i], edgecolor=SURFACE, linewidth=1)
    ax.set_xticks(x, [str(c) for c in categories])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper left", ncols=n)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def signed_bars(categories: list, values: list, title: str = "", ylabel: str = "", h: float = 3.0):
    fig, ax = fig_ax(h=h)
    colors = [GOOD if v >= 0 else BAD for v in values]
    bars = ax.bar([str(c) for c in categories], values, color=colors, width=0.6)
    for b, v in zip(bars, values):
        ax.annotate(f"{v:,.0f}", (b.get_x() + b.get_width() / 2, v), xytext=(0, -12 if v < 0 else 4),
                    textcoords="offset points", ha="center", fontsize=8, color=TEXT2)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def hbar(labels: list[str], values: list[float], title: str = "", xlabel: str = "", color: str = PALETTE[0]):
    h = max(2.5, 0.38 * len(labels) + 1)
    fig, ax = fig_ax(h=h)
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=color, height=0.7)
    ax.set_yticks(y, labels)
    for yi, v in zip(y, values):
        ax.annotate(f"{v:,.1f}", (v, yi), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=8, color=TEXT2)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.margins(x=0.12)
    fig.tight_layout()
    return fig


def heatmap(df: pd.DataFrame, title: str = "", vlim: float | None = None, fmt: str = "{:+.1f}%", h: float | None = None):
    data = df.astype(float).values
    lim = vlim or max(np.nanmax(np.abs(data)), 0.01)
    fig, ax = fig_ax(w=max(5, 1.1 * df.shape[1] + 2.5), h=h or max(2.5, 0.45 * df.shape[0] + 1.2))
    ax.imshow(data, cmap=DIVERGING, vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(df.shape[1]), df.columns)
    ax.set_yticks(range(df.shape[0]), df.index)
    ax.grid(False)
    ax.tick_params(length=0)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            v = data[i, j]
            if np.isnan(v):
                txt, col = "—", MUTED
            else:
                txt, col = fmt.format(v), ("white" if abs(v) > lim * 0.6 else TEXT)
            ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=col)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title)
    fig.tight_layout()
    return fig


def cost_breakdown(parts: dict[str, float], title: str = ""):
    """Single horizontal stacked bar showing what makes up the landed cost."""
    fig, ax = fig_ax(h=2.2)
    left = 0.0
    total = sum(parts.values()) or 1
    for i, (k, v) in enumerate(parts.items()):
        if v <= 0:
            continue
        ax.barh([0], [v], left=left, color=PALETTE[i % len(PALETTE)], edgecolor=SURFACE, linewidth=2, label=k)
        if v / total > 0.07:
            ax.text(left + v / 2, 0, f"{v / total:.0%}", ha="center", va="center", fontsize=9, color="white")
        left += v
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title(title)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncols=min(7, len(parts)))
    fig.tight_layout()
    return fig
