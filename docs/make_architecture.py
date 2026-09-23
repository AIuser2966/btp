"""Draw the project architecture flowchart, with the formula used at every step.

    python docs/make_architecture.py   ->  docs/architecture.png / .svg / .pdf
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent
plt.rcParams.update({"mathtext.fontset": "dejavusans", "font.family": "DejaVu Sans"})

INK, INK_2, MUTED, SURFACE, EDGE = "#0b0b0b", "#52514e", "#8a8984", "#ffffff", "#d6d4cc"
# one accent per layer (categorical order from the project's chart palette)
C_DATA, C_RET, C_OPT, C_ML, C_STRAT, C_ENG, C_MET, C_ANA, C_OUT = (
    "#2a78d6", "#1baf7a", "#eb6834", "#4a3aa7", "#eda100", "#e34948", "#008300",
    "#e87ba4", "#52514e")

W, H = 100, 196
fig = plt.figure(figsize=(17, 17 * H / W * 0.62))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor("#fbfaf7")


def tint(hex_colour, a):
    """Mix a colour with white (a = share of colour)."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(round(255 - (255 - c) * a) for c in (r, g, b))


def layer(x, y, w, h, colour, label, sub=""):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=tint(colour, 0.08), ec=tint(colour, 0.55), lw=1.4))
    ax.text(x + 1.2, y + h - 1.3, label, fontsize=13.5, fontweight="bold", color=colour,
            va="top")
    if sub:
        ax.text(x + w - 1.2, y + h - 1.4, sub, fontsize=10, color=INK_2, va="top", ha="right",
                family="DejaVu Sans Mono")


def box(x, y, w, h, title, lines=(), colour=INK_2, size=11.5, title_size=11.5, gap=2.6,
        align="left", title_colour=None, fc=SURFACE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=fc, ec=tint(colour, 0.6), lw=1.2))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.45), w, 0.45, boxstyle="square,pad=0",
                                fc=colour, ec="none"))
    tx = x + 1.0 if align == "left" else x + w / 2
    ha = "left" if align == "left" else "center"
    ty = y + h - 1.6
    if title:
        ax.text(tx, ty, title, fontsize=title_size, fontweight="bold",
                color=title_colour or INK, va="top", ha=ha)
        ty -= gap + 0.2
    for line in lines:
        if isinstance(line, tuple):            # (text, extra gap, fontsize, colour)
            text, extra, fs, col = list(line) + [0, size, INK][len(line) - 1:]
        else:
            text, extra, fs, col = line, 0, size, INK
        ax.text(tx, ty, text, fontsize=fs, color=col, va="top", ha=ha)
        ty -= gap + extra


def arrow(x1, y1, x2, y2, colour=MUTED, text=None, rad=0.0, lw=1.8, style="-|>",
          text_offset=(0.8, 0), ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                                 color=colour, lw=lw, connectionstyle=f"arc3,rad={rad}",
                                 linestyle=ls, shrinkA=0, shrinkB=0))
    if text:
        ax.text((x1 + x2) / 2 + text_offset[0], (y1 + y2) / 2 + text_offset[1], text,
                fontsize=10, color=colour, va="center", style="italic")


# ---------------------------------------------------------------- title
ax.text(2, H - 1.5, "A Simple Optimized SIP for Multi-Asset Allocation — architecture & formulas",
        fontsize=19, fontweight="bold", color=INK, va="top")
ax.text(2, H - 5.2, "Data flows top to bottom. Each box names the file / function and the exact "
        "formula it computes.  $t$ = month,  $i$ = asset (Equity, Bonds, Gold),  "
        "$w$ = weights,  $h$ = holdings.", fontsize=11.5, color=INK_2, va="top")

# ---------------------------------------------------------------- 1. raw data
y1 = 172
layer(1, y1, 98, 14, C_DATA, "① Raw data", "data/raw/*.csv  (bundled, 1973 → 2026, monthly)")
raw = [("S&P 500 (Shiller)", "price $P_t$,  dividend $D_t$ (annual)"),
       ("US 10-year Treasury (FRED)", "yield $y_t$"),
       ("Gold (USD / oz)", "price $P_t$"),
       ("USD / INR (FRED)", "rupees per dollar $FX_t$")]
for k, (t, l) in enumerate(raw):
    box(2.5 + k * 24.2, y1 + 1.3, 22.8, 8.3, t, [l], colour=C_DATA)

# ---------------------------------------------------------------- 2. returns
y2 = 138
layer(1, y2, 98, 31, C_RET, "② Monthly total returns", "sip/data.py  ·  load_returns()")
bw = 22.8
box(2.5, y2 + 8.2, bw, 18, "Equity  (equity_total_return)", [
    (r"$r_t=\dfrac{P_t+D_{t-1}/12}{P_{t-1}}-1$", 2.2, 13),
    ("price change + 1/12 of annual dividend", 0, 9.5, INK_2),
    ("missing dividends: last yield carried fwd", 0, 9.5, INK_2)], colour=C_RET)
box(2.5 + 24.2, y2 + 8.2, bw, 18, "Bonds  (bond_total_return)", [
    (r"$\mathrm{Price}=\dfrac{c/2}{y/2}\,(1-(1+\frac{y}{2})^{-n})+(1+\frac{y}{2})^{-n}$", 2.6, 10.2),
    (r"$r_t=\mathrm{Price}(c{=}y_{t-1},\,y_t,\,n{=}2T)-1+\dfrac{y_{t-1}}{12}$", 2.0, 10.2),
    (r"buy 10-yr par bond, re-price with $T=9\frac{11}{12}$ yrs", 0, 9.5, INK_2)],
    colour=C_RET)
box(2.5 + 48.4, y2 + 8.2, bw, 18, "Gold  (gold_return)", [
    (r"$r_t=\dfrac{P_t}{P_{t-1}}-1$", 2.2, 13),
    ("no dividends or coupons:", 0, 9.5, INK_2),
    ("return = price change only", 0, 9.5, INK_2)], colour=C_RET)
box(2.5 + 72.6, y2 + 8.2, bw, 18, "Rupee investor  (--currency INR)", [
    (r"$r^{INR}_t=(1+r_t)\,\dfrac{FX_t}{FX_{t-1}}-1$", 2.2, 12),
    ("asset return × change in USD/INR", 0, 9.5, INK_2),
    ("(the rupee fell from 8 to 95 per $)", 0, 9.5, INK_2)], colour=C_RET)
box(2.5, y2 + 1.3, 95, 5.4, None, [
    (r"Returns matrix  $R$  =  642 months (Feb 1973 → Jul 2026)  ×  {Equity, Bonds, Gold}"
     "      ·      also load_macro(): bond yield, dividend yield $D/P$, USD/INR for the ML "
     "features", 0, 11)], colour=C_RET, gap=0)
for k in range(4):
    arrow(2.5 + k * 24.2 + bw / 2, y1 + 1.3, 2.5 + k * 24.2 + bw / 2, y2 + 26.2, C_DATA)
    arrow(2.5 + k * 24.2 + bw / 2, y2 + 8.2, 2.5 + k * 24.2 + bw / 2, y2 + 6.7, C_RET, lw=1.3)

# ---------------------------------------------------------------- 3a. optimiser
y3 = 86
layer(1, y3, 57, 49, C_OPT, "③ Target weights (walk-forward)", "sip/optimize.py")
box(2.5, y3 + 34.5, 54, 10, "Estimate from the PAST 120 months only  (t−120 … t−1)", [
    (r"$\mu_i=\dfrac{1}{120}\sum_{s=t-120}^{t-1} r_{i,s}$"
     r"        $\Sigma_{ij}=\mathrm{cov}(r_i,\,r_j)$", 0, 12.5)], colour=C_OPT)
box(2.5, y3 + 18.5, 26.5, 14, "Risk parity  (risk_parity)", [
    (r"risk contribution $RC_i=w_i\,(\Sigma w)_i$", 1.0, 10.5),
    (r"$\min_w\ \sum_i\,(RC_i-\overline{RC})^2$", 1.0, 12),
    ("equal risk from each asset", 0, 9.5, INK_2)], colour=C_OPT)
box(30, y3 + 18.5, 26.5, 14, "Max Sharpe  (max_sharpe)", [
    (r"$\max_w\ \dfrac{w^{T}\mu}{\sqrt{w^{T}\Sigma\, w}}$", 3.3, 13),
    ("best return per unit of risk", 0, 9.5, INK_2)], colour=C_OPT)
box(2.5, y3 + 10.5, 54, 6.4, None, [
    (r"Constraints (SLSQP):   $\sum_i w_i=1$,     $0.10\leq w_i\leq 0.70$"
     "     ·     re-fitted every 12 months (each February)", 0, 11)], colour=C_OPT, gap=0)
box(2.5, y3 + 1.3, 54, 7.8, None, [
    (r"Optimized SIP target:    $w=\frac{1}{2}\,w^{RP}+\frac{1}{2}\,w^{MS}$"
     "      (e.g. Feb 1983: 21% / 59.5% / 19.6%)", 0, 12)], colour=C_OPT, gap=0,
    fc=tint(C_OPT, 0.12))
arrow(15.75, y3 + 34.5, 15.75, y3 + 32.5, C_OPT, lw=1.3)
arrow(43.25, y3 + 34.5, 43.25, y3 + 32.5, C_OPT, lw=1.3)
arrow(15.75, y3 + 18.5, 15.75, y3 + 16.9, C_OPT, lw=1.3)
arrow(43.25, y3 + 18.5, 43.25, y3 + 16.9, C_OPT, lw=1.3)
arrow(29.5, y3 + 10.5, 29.5, y3 + 9.1, C_OPT, lw=1.3)

# ---------------------------------------------------------------- 3b. ML extension
layer(60, y3, 39, 49, C_ML, "③b ML forecasts (extension)", "sip/forecast.py")
box(61.5, y3 + 35.5, 36, 9.5, "Features $X_j$  (build_features, 13 inputs)", [
    (r"momentum $\frac{G_j}{G_{j-3}}-1,\ \frac{G_j}{G_{j-12}}-1$    vol $\mathrm{std}_{12}\sqrt{12}$",
     0.6, 10.5),
    (r"bond yield, $\Delta$yield$_{12}$,  dividend yield $D/P$,  $\Delta FX_{12}$", 0, 10.5)],
    colour=C_ML)
box(61.5, y3 + 26, 36, 8.5, "Target  (build_targets)", [
    (r"$Y_j=\prod_{k=j+1}^{j+12}(1+r_k)-1$   (next 12 months)", 0, 11.5)], colour=C_ML)
box(61.5, y3 + 16.2, 36, 8.9, "Walk-forward training  (no look-ahead)", [
    (r"train only on rows $k\leq j-12$,  re-fit yearly", 0.2, 10.5),
    ("Ridge  |  Random forest  |  Gradient boosting", 0, 10.5)], colour=C_ML)
box(61.5, y3 + 7.1, 36, 8.3, "Score  (evaluate)", [
    (r"$R^2_{OS}=1-\dfrac{\sum(Y-\hat{Y})^2}{\sum(Y-\bar{Y}_{hist})^2}$   > 0 beats average",
     0, 11)], colour=C_ML)
box(61.5, y3 + 1.3, 36, 4.9, None, [
    (r"forecast_weights():   $\hat{\mu}=\hat{Y}/12$  replaces $\mu$ in max Sharpe", 0, 10.5)],
    colour=C_ML, gap=0, fc=tint(C_ML, 0.12))
for top, bottom in ((35.5, 34.5), (26, 25.1), (16.2, 15.4), (7.1, 6.2)):
    arrow(79.5, y3 + top, 79.5, y3 + bottom, C_ML, lw=1.3)
arrow(61.5, y3 + 3.6, 56.5, y3 + 25.5, C_ML, rad=-0.25, ls="--",
      text=r"$\hat{\mu}$", text_offset=(-1.2, 3))
arrow(50, y2 + 1.3, 50, y3 + 49, C_RET)
arrow(79.5, y2 + 1.3, 79.5, y3 + 49, C_RET)

# ---------------------------------------------------------------- 4. strategies
y4 = 72
layer(1, y4, 98, 11.5, C_STRAT, "④ Strategies = target weights + money rule + rebalance rule",
      "sip/strategies.py")
chips = [("Equity SIP", "100/0/0"), ("Equal-weight", "⅓ each, never rebal."),
         ("60/20/20", "pro-rata, yearly rebal."), ("Risk-parity SIP", r"$w^{RP}$, smart, 5% band"),
         ("Max-Sharpe SIP", r"$w^{MS}$, smart, 5% band"),
         ("★ Optimized SIP", r"$\frac{1}{2}w^{RP}+\frac{1}{2}w^{MS}$"),
         ("Optimized + ML / Oracle", r"$\mu\rightarrow\hat{\mu}$")]
cw = 95 / len(chips)
for k, (t, l) in enumerate(chips):
    box(2.5 + k * cw, y4 + 1.3, cw - 0.9, 6.3, t, [(l, 0, 9.8, INK_2)], colour=C_STRAT,
        title_size=10.5, gap=2.2, align="center",
        fc=tint(C_STRAT, 0.18) if t.startswith("★") else SURFACE)
arrow(48, y3, 48, y4 + 7.6, C_OPT)
arrow(79.5, y3, 79.5, y4 + 7.6, C_ML)

# ---------------------------------------------------------------- 5. engine
y5 = 41
layer(1, y5, 98, 28, C_ENG, "⑤ SIP simulator: the same 5 steps every month  (×522 months, Feb 1983 → Jul 2026)",
      "sip/engine.py  ·  run_sip()")
steps = [
    ("1  Instalment", [(r"$C_t=A\,(1+g)^{\lfloor t/12\rfloor}$", 1.2, 12),
                       ("A = 10,000/month", 0, 9.5, INK_2),
                       ("g = yearly step-up (default 0)", 0, 9.5, INK_2)]),
    ("2  Smart split", [(r"$V=\sum_i h_i+C_t$", 0.3, 11),
                        (r"$gap_i=\max(w_iV-h_i,\,0)$", 0.3, 11),
                        ("fill gaps first, rest", 0, 9.5, INK_2),
                        (r"pro-rata $\propto w_i$  (no selling)", 0, 9.5, INK_2)]),
    ("3  Band rebalance", [(r"if $\max_i\left|\frac{h_i}{\sum h}-w_i\right|>5\%$", 0.9, 11),
                           (r"then $h\leftarrow w\cdot\sum_i h_i$", 0.3, 11),
                           ("(fired 23 of 522 months)", 0, 9.5, INK_2)]),
    ("4  Costs", [(r"$cost=(buy+sell)\times0.1\%$", 1.2, 11),
                  ("10 bps per trade, taken", 0, 9.5, INK_2),
                  ("pro-rata from holdings", 0, 9.5, INK_2)]),
    ("5  Market moves", [(r"$h_i\leftarrow h_i\,(1+r_{i,t})$", 0.6, 11.5),
                         (r"$TWR_t=\dfrac{V_{end}}{V_{start}}-1$", 1.6, 11.5),
                         (r"($r_{i,t}$ from step ②)", 0, 9.5, INK_2)]),
]
sw, sg = 17.4, 1.9
for k, (t, lines) in enumerate(steps):
    box(2.5 + k * (sw + sg), y5 + 7.2, sw, 15.8, t, lines, colour=C_ENG)
    if k < len(steps) - 1:
        x = 2.5 + k * (sw + sg) + sw
        arrow(x, y5 + 15, x + sg, y5 + 15, C_ENG, lw=1.6)
x_last, x_first, y_loop = 2.5 + 4 * (sw + sg) + sw / 2, 2.5 + sw / 2, y5 + 4.9
ax.plot([x_last, x_last, x_first], [y5 + 7.2, y_loop, y_loop], color=C_ENG, lw=1.4, ls="--")
arrow(x_first, y_loop, x_first, y5 + 7.2, C_ENG, lw=1.4)
ax.text(50, y_loop + 0.5, "next month  (repeat 522 times)", fontsize=10, color=C_ENG,
        style="italic", ha="center", va="bottom")
ax.text(50, y5 + 1.3, r"Output per month: value in each asset, instalment, $TWR_t$, bought, sold, costs"
        "   (SIPResult)", fontsize=10.5, color=INK_2, ha="center")
arrow(50, y4 + 1.3, 50, y5 + 28, C_STRAT)

# ---------------------------------------------------------------- 6a. metrics
y6 = 3
layer(1, y6, 57, 35, C_MET, "⑥ Scoring", "sip/metrics.py")
left = [(r"XIRR:  $\sum_k \dfrac{CF_k}{(1+r)^{t_k}}=0$", 3.4, 12),
        ("instalments −, final value +  (Brent's method)", 1.4, 9.5, INK_2),
        (r"CAGR $=\left(\prod_t(1+TWR_t)\right)^{12/N}-1$", 3.0, 11),
        (r"Volatility  $\sigma=\mathrm{std}(TWR_t)\sqrt{12}$", 1.4, 11),
        (r"Sharpe $=\dfrac{12\,\overline{TWR}-r_f}{\sigma}$,   $r_f=0$", 0, 11)]
right = [(r"Sortino $=\dfrac{12\,\overline{TWR}}{\sqrt{12\cdot\overline{\min(TWR,0)^2}}}$", 4.2, 11),
         (r"Max drawdown $=\min_t\left(\dfrac{G_t}{\max_{s\leq t}G_s}-1\right)$", 4.0, 11),
         (r"Calmar $=\mathrm{CAGR}\,/\,|\mathrm{MDD}|$", 1.0, 11),
         (r"Worst wealth drop: same on account value", 1.4, 10.5),
         (r"Sell turnover $=\dfrac{\sum sold}{\overline{V}\cdot years}$", 0, 11)]
box(2.5, y6 + 1.3, 26.5, 29.5, None, left, colour=C_MET, gap=2.6)
box(30, y6 + 1.3, 26.5, 29.5, None, right, colour=C_MET, gap=2.6)

# ---------------------------------------------------------------- 6b. analysis + outputs
layer(60, y6 + 11, 39, 24, C_ANA, "⑦ Robustness", "sip/analysis.py")
box(61.5, y6 + 12.3, 36, 17.5, None, [
    ("Rolling: 403 separate 10-year SIPs (every start month)", 0, 10),
    ("Train/test: best of 66 fixed mixes on 1983–2004 → 2004–26", 0, 10),
    ("Hindsight grid: all 66 mixes on a 10% grid", 0, 10),
    ("Sensitivity: look-back 60/120/180, band 3/5/10%", 0, 10),
    (r"Crises (1987, 2000, 2008, 2020, 2022):  $\prod(1+TWR_t)-1$", 0, 10)],
    colour=C_ANA, gap=3.2)
layer(60, y6, 39, 10, C_OUT, "⑧ Outputs", "")
ax.text(61.5, y6 + 5.6, "run_backtest.py · run_forecast.py → results/*  (tables, charts)",
        fontsize=9.8, color=INK, va="top")
ax.text(61.5, y6 + 3.0, "recommend.py → this month's split  ·  tests/ 18 checks",
        fontsize=9.8, color=INK, va="top")
arrow(29.5, y5, 29.5, y6 + 35, C_ENG)
arrow(79.5, y5, 79.5, y6 + 35, C_ENG)
arrow(58, y6 + 20, 60, y6 + 20, C_MET, lw=1.4)

for ext in ("png", "svg", "pdf"):
    fig.savefig(OUT / f"architecture.{ext}", dpi=200 if ext == "png" else None,
                facecolor=fig.get_facecolor())
print("wrote", *(OUT / f"architecture.{e}" for e in ("png", "svg", "pdf")))
