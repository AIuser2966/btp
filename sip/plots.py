"""Report charts (matplotlib, saved as PNG)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

# Fixed categorical order: a strategy keeps its colour in every chart.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
ASSET_COLORS = {"Nifty": "#2a78d6", "Gold": "#eda100", "Liquid": "#1baf7a"}


def _style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
        "xtick.color": INK_2, "ytick.color": INK_2, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
        "lines.linewidth": 2,
    })


def colour_map(names: list[str]) -> dict[str, str]:
    return {n: SERIES[i % len(SERIES)] for i, n in enumerate(names)}


def _ts(index: pd.PeriodIndex):
    return index.to_timestamp()


def wealth_chart(results, path: Path, currency: str):
    _style()
    cmap = colour_map([r.name for r in results])
    fig, ax = plt.subplots(figsize=(10, 5.5))
    invested = results[0].contributions.cumsum()
    ax.plot(_ts(invested.index), invested, color=MUTED, lw=1.5, ls="--", label="Amount invested")
    for r in results:
        ax.plot(_ts(r.total.index), r.total, color=cmap[r.name], label=r.name,
                lw=2.6 if r.name == "Optimized SIP" else 1.6)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_title(f"Portfolio value of a {currency} 10,000/month SIP (log scale)")
    ax.set_ylabel(f"Value ({currency})")
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def drawdown_chart(results, path: Path, names=("Equity SIP", "60/20/20 annual rebal",
                                                "Optimized SIP")):
    _style()
    cmap = colour_map([r.name for r in results])
    fig, ax = plt.subplots(figsize=(10, 4))
    for r in results:
        if r.name not in names:
            continue
        g = (1 + r.twr).cumprod()
        dd = g / g.cummax() - 1
        ax.plot(_ts(dd.index), dd, color=cmap[r.name], label=r.name, lw=1.6)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title("Drawdown from previous peak (time-weighted returns)")
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def weights_chart(target: pd.DataFrame, path: Path, title: str):
    _style()
    fig, ax = plt.subplots(figsize=(10, 3.8))
    t = target.dropna()
    ax.stackplot(_ts(t.index), *[t[c] for c in t.columns],
                 colors=[ASSET_COLORS.get(c, MUTED) for c in t.columns],
                 labels=list(t.columns), edgecolor=SURFACE, linewidth=0.8)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title(title)
    ax.legend(loc="upper left", ncol=3, fontsize=9)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def rolling_chart(roll: pd.DataFrame, path: Path, years: int):
    _style()
    names = list(dict.fromkeys(roll["Strategy"]))
    cmap = colour_map(names)
    data = [roll.loc[roll["Strategy"] == n, "XIRR"].values for n in names]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    bp = ax.boxplot(data, vert=False, patch_artist=True, widths=0.55,
                    medianprops={"color": INK, "lw": 2}, whis=(5, 95),
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": MUTED,
                                "markeredgecolor": "none"})
    for patch, n in zip(bp["boxes"], names):
        patch.set_facecolor(cmap[n])
        patch.set_alpha(0.85)
        patch.set_edgecolor(SURFACE)
    ax.set_yticks(range(1, len(names) + 1), names)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title(f"XIRR of every {years}-year SIP window (box = 25-75%, whiskers = 5-95%)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def frontier_chart(grid: pd.DataFrame, table: pd.DataFrame, path: Path):
    """All static mixes (grey) vs the strategies: return against worst loss."""
    _style()
    cmap = colour_map(list(table.index))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(-grid["Worst wealth drop"], grid["XIRR"], s=14, color=GRID,
               edgecolor=MUTED, lw=0.4, label="Every static mix (10% grid, annual rebal)")
    for name, row in table.iterrows():
        ax.scatter(-row["Worst wealth drop"], row["XIRR"], s=70, color=cmap[name],
                   edgecolor=SURFACE, lw=2, zorder=3)
    _place_labels(fig, ax, [(n, -r["Worst wealth drop"], r["XIRR"])
                            for n, r in table.iterrows()])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlabel("Worst fall in account value (lower is better)")
    ax.set_ylabel("XIRR (higher is better)")
    ax.set_title("Return vs pain: strategies against every fixed mix")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _place_labels(fig, ax, points):
    """Direct-label points, trying a few offsets so no two labels overlap."""
    candidates = [(7, -3, "left"), (-7, -3, "right"), (7, 8, "left"), (7, -14, "left"),
                  (-7, 8, "right"), (-7, -14, "right")]
    renderer = fig.canvas.get_renderer()
    boxes = []
    for name, x, y in points:
        for dx, dy, ha in candidates:
            label = ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                                ha=ha, fontsize=9, color=INK)
            box = label.get_window_extent(renderer).expanded(1.05, 1.15)
            if not any(box.overlaps(b) for b in boxes):
                boxes.append(box)
                break
            label.remove()
        else:
            boxes.append(ax.annotate(name, (x, y), xytext=(7, -3), textcoords="offset points",
                                     fontsize=9, color=INK).get_window_extent(renderer))


MODEL_COLORS = {"Ridge": SERIES[0], "Random forest": SERIES[1],
                "Gradient boosting": SERIES[2], "Trailing 10y mean": SERIES[3]}


def forecast_r2_chart(ev: pd.DataFrame, path: Path):
    """Out-of-sample R^2 of each model per asset (0 = no better than the historical mean)."""
    _style()
    ev = ev[ev["Model"].isin(MODEL_COLORS) & (ev["Asset"] != "Pick best asset")]
    assets = list(dict.fromkeys(ev["Asset"]))
    models = [m for m in MODEL_COLORS if m in set(ev["Model"])]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    h = 0.8 / len(models)
    for k, m in enumerate(models):
        vals = [ev[(ev["Model"] == m) & (ev["Asset"] == a)]["OOS R2 vs hist mean"].iloc[0]
                for a in assets]
        ys = [i + (k - (len(models) - 1) / 2) * h for i in range(len(assets))]
        ax.barh(ys, vals, height=h * 0.9, color=MODEL_COLORS[m], label=m,
                edgecolor=SURFACE, linewidth=1)
        for y, v in zip(ys, vals):
            ax.annotate(f"{v:+.2f}", (v, y), xytext=(4 if v >= 0 else -4, 0),
                        textcoords="offset points", va="center",
                        ha="left" if v >= 0 else "right", fontsize=8, color=INK_2)
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(range(len(assets)), assets)
    ax.invert_yaxis()
    ax.set_xlabel("Out-of-sample R² vs historical mean (right of 0 = better forecast)")
    ax.set_title("Can models predict next-12-month returns?")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def forecast_vs_actual_chart(forecasts: dict, actual: pd.DataFrame, path: Path,
                             models=("Ridge", "Random forest")):
    _style()
    assets = list(actual.columns)
    fig, axes = plt.subplots(len(assets), 1, figsize=(10, 2.6 * len(assets)), sharex=True)
    for ax, a in zip(axes, assets):
        y = actual[a].dropna()
        ax.plot(_ts(y.index), y, color=INK, lw=1.4, label="Actual next-12m return")
        hm = forecasts["Historical mean"][a].reindex(y.index)
        ax.plot(_ts(y.index), hm, color=MUTED, lw=1.4, ls="--", label="Historical mean")
        for m in models:
            f = forecasts[m][a].reindex(y.index)
            ax.plot(_ts(y.index), f, color=MODEL_COLORS[m], lw=1.4, label=m)
        ax.axhline(0, color=GRID, lw=1)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        ax.set_title(a, fontsize=11)
    axes[0].legend(loc="upper right", ncol=4, fontsize=8)
    fig.suptitle("Forecast vs what actually happened (walk-forward, out of sample)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def importance_chart(imp: pd.DataFrame, path: Path, model: str):
    """Average feature importance over all yearly re-fits, one panel per asset."""
    _style()
    assets = list(dict.fromkeys(imp["asset"]))
    feats = [c for c in imp.columns if c not in ("refit", "asset")]
    fig, axes = plt.subplots(1, len(assets), figsize=(12, 4.6), sharey=True)
    for ax, a in zip(axes, assets):
        v = imp[imp["asset"] == a][feats].mean()
        ax.barh(range(len(feats)), v.values, color=MODEL_COLORS.get(model, SERIES[0]),
                height=0.7)
        ax.set_yticks(range(len(feats)), feats)
        ax.invert_yaxis()
        ax.set_title(f"Predicting {a}", fontsize=11)
        ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        ax.grid(axis="y", visible=False)
    fig.suptitle(f"{model}: which inputs mattered most (average over yearly re-fits)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---- single-strategy charts (used by each strategy folder) ----------------------

def strategy_value_chart(res, path: Path, colour: str, currency: str):
    _style()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    invested = res.contributions.cumsum()
    ax.plot(_ts(invested.index), invested, color=MUTED, lw=1.5, ls="--", label="Amount invested")
    ax.plot(_ts(res.total.index), res.total, color=colour, lw=2.2, label="Portfolio value")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_title(f"{res.name}: value of a {currency} 10,000/month SIP (log scale)")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def strategy_drawdown_chart(res, path: Path, colour: str):
    _style()
    g = (1 + res.twr).cumprod()
    dd = g / g.cummax() - 1
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.fill_between(_ts(dd.index), dd, 0, color=colour, alpha=0.25, lw=0)
    ax.plot(_ts(dd.index), dd, color=colour, lw=1.4)
    worst = dd.idxmin()
    ax.annotate(f"worst {dd.min():.1%} ({worst})", (_ts(pd.PeriodIndex([worst]))[0], dd.min()),
                xytext=(8, 0), textcoords="offset points", fontsize=9, color=INK, va="center")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title(f"{res.name}: fall from previous peak")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def allocation_chart(res, target: pd.DataFrame, path: Path):
    """Actual share of each asset in the portfolio (area) with the target (dashed)."""
    _style()
    w = res.weights
    t = target.reindex(w.index)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.stackplot(_ts(w.index), *[w[c] for c in w.columns],
                 colors=[ASSET_COLORS.get(c, MUTED) for c in w.columns],
                 labels=[f"{c} (actual)" for c in w.columns], edgecolor=SURFACE,
                 linewidth=0.6, alpha=0.9)
    cum = t.cumsum(axis=1)
    for c in list(t.columns)[:-1]:
        ax.plot(_ts(cum.index), cum[c], color=INK, lw=1, ls="--")
    ax.plot([], [], color=INK, lw=1, ls="--", label="Target split")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title(f"{res.name}: how the money is split over time")
    ax.legend(loc="upper left", ncol=4, fontsize=8.5)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
