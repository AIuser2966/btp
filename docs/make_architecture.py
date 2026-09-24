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
        "formula it computes.  $t$ = month,  $i$ = asset (Nifty 50, Gold, Liquid),  "
        "$w$ = weights,  $h$ = holdings.", fontsize=11.5, color=INK_2, va="top")

# ---------------------------------------------------------------- 1. raw data
y1 = 172
layer(1, y1, 98, 14, C_DATA, "① Raw data", "00_raw_data/raw/  (daily, 2000 → 2019, verified)")
raw = [("Nifty 50 (NSE)", "price index $P_t$ (no dividends)"),
       ("Gold", "US dollars per ounce $G_t$"),
       ("Liquid fund", "index $L_d$: grows by 91-day T-bill $y/365$ daily"),
       ("USD / INR (FRED)", "rupees per dollar $FX_t$")]
for k, (t, l) in enumerate(raw):
    box(2.5 + k * 24.2, y1 + 1.3, 22.8, 8.3, t, [l], colour=C_DATA, size=10.5)

# ---------------------------------------------------------------- 2. returns
y2 = 138
layer(1, y2, 98, 31, C_RET, "② Monthly rupee total returns", "sip/data.py  ·  load_returns()")
bw = 22.8
box(2.5, y2 + 8.2, bw, 18, "Nifty  (nifty_total_return)", [
    (r"$r_t=\dfrac{P_t}{P_{t-1}}-1+\dfrac{dy}{12}$", 2.2, 13),
    ("price change + 1/12 of yearly dividend", 0, 9.5, INK_2),
    ("dy = 1.3% a year (assumption)", 0, 9.5, INK_2)], colour=C_RET)
box(2.5 + 24.2, y2 + 8.2, bw, 18, "Gold in rupees  (gold_return)", [
    (r"$G^{INR}_t=G^{USD}_t\times FX_t$", 1.0, 12),
    (r"$r_t=\dfrac{G^{INR}_t}{G^{INR}_{t-1}}-1$", 3.4, 12),
    ("rupee fell 43.5 → 71.4 per $", 0, 9.5, INK_2)], colour=C_RET)
box(2.5 + 48.4, y2 + 8.2, bw, 18, "Liquid  (liquid_return)", [
    (r"$L_d=L_{d-1}\,(1+y_d/365)$", 1.6, 12),
    (r"$r_t=\dfrac{L_t}{L_{t-1}}-1$", 2.2, 12),
    ("91-day T-bill rate, 0.5% volatility", 0, 9.5, INK_2)], colour=C_RET)
box(2.5 + 72.6, y2 + 8.2, bw, 18, "Month end  (month_end)", [
    (r"$X_t=$ last daily value of month $t$", 1.8, 11),
    ("e.g. Feb 2010: Nifty 4,922.30,", 0, 9.5, INK_2),
    ("gold $1,118.9 × 46.05 = ₹51,525", 0, 9.5, INK_2)], colour=C_RET)
box(2.5, y2 + 1.3, 95, 5.4, None, [
    (r"Returns matrix  $R$  =  239 months (Feb 2000 → Dec 2019)  ×  {Nifty, Gold, Liquid}"
     "      ·      SIP months: Feb 2010 → Dec 2019 (119), after 120 months of history", 0, 11)],
    colour=C_RET, gap=0)
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
     "      (Feb 2010: 10.3% / 19.7% / 70%)", 0, 12)], colour=C_OPT, gap=0,
    fc=tint(C_OPT, 0.12))
arrow(15.75, y3 + 34.5, 15.75, y3 + 32.5, C_OPT, lw=1.3)
arrow(43.25, y3 + 34.5, 43.25, y3 + 32.5, C_OPT, lw=1.3)
arrow(15.75, y3 + 18.5, 15.75, y3 + 16.9, C_OPT, lw=1.3)
arrow(43.25, y3 + 18.5, 43.25, y3 + 16.9, C_OPT, lw=1.3)
arrow(29.5, y3 + 10.5, 29.5, y3 + 9.1, C_OPT, lw=1.3)

# ---------------------------------------------------------------- 3b. what the optimisers see
layer(60, y3, 39, 49, C_ML, "③b What the optimisers see", "Feb 2010, window 2000–2010")
box(61.5, y3 + 33.5, 36, 11.5, "Past 10 years (per year)", [
    ("Nifty:   return 16.8%,  volatility 28.0%", 0, 10.5),
    ("Gold:    return 15.3%,  volatility 16.8%", 0, 10.5),
    ("Liquid:  return   6.2%,  volatility   0.5%", 0, 10.5)], colour=C_ML, gap=2.4)
box(61.5, y3 + 21.5, 36, 10.5, "Without the 10–70% limits", [
    ("risk parity → 1.5% / 2.3% / 96.2%", 0, 10.5),
    ("max Sharpe  → 0.5% / 0.4% / 99.1%", 0, 10.5),
    ("(Nifty / Gold / Liquid)", 0, 9.5, INK_2)], colour=C_ML, gap=2.4)
box(61.5, y3 + 10.5, 36, 9.5, "With the limits", [
    ("Liquid pinned at the 70% cap every year;", 0, 10.5),
    ("Nifty + Gold share the remaining 30%", 0, 10.5)], colour=C_ML, gap=2.6)
box(61.5, y3 + 1.3, 36, 7.7, None, [
    (r"Fair score: Sharpe vs Liquid $=\dfrac{12\,\overline{(TWR-r_{Liq})}}{\sigma}$", 0, 10.5)],
    colour=C_ML, gap=0, fc=tint(C_ML, 0.12))
for top, bottom in ((33.5, 32.1), (21.5, 20.1), (10.5, 9.1)):
    arrow(79.5, y3 + top, 79.5, y3 + bottom, C_ML, lw=1.3)
arrow(50, y2 + 1.3, 50, y3 + 49, C_RET)
arrow(79.5, y2 + 1.3, 79.5, y3 + 49, C_RET)

# ---------------------------------------------------------------- 4. strategies
y4 = 72
layer(1, y4, 98, 11.5, C_STRAT, "④ Strategies = target weights + money rule + rebalance rule",
      "folders 01_ … 06_  ·  strategy.py")
chips = [("Equity SIP", "100% Nifty"), ("Equal-weight", "⅓ each, never rebal."),
         ("60/20/20", "pro-rata, yearly rebal."), ("Risk-parity SIP", r"$w^{RP}$, smart, 5% band"),
         ("Max-Sharpe SIP", r"$w^{MS}$, smart, 5% band"),
         ("★ Optimized SIP", r"$\frac{1}{2}w^{RP}+\frac{1}{2}w^{MS}$")]
cw = 95 / len(chips)
for k, (t, l) in enumerate(chips):
    box(2.5 + k * cw, y4 + 1.3, cw - 0.9, 6.3, t, [(l, 0, 9.8, INK_2)], colour=C_STRAT,
        title_size=10.5, gap=2.2, align="center",
        fc=tint(C_STRAT, 0.18) if t.startswith("★") else SURFACE)
arrow(48, y3, 48, y4 + 7.6, C_OPT)

# ---------------------------------------------------------------- 5. engine
y5 = 41
layer(1, y5, 98, 28, C_ENG, "⑤ SIP simulator: the same 5 steps every month  (×119 months, Feb 2010 → Dec 2019)",
      "sip/engine.py  ·  run_sip()")
steps = [
    ("1  Instalment", [(r"$C_t=A\,(1+g)^{\lfloor t/12\rfloor}$", 1.2, 12),
                       ("A = ₹10,000/month", 0, 9.5, INK_2),
                       ("g = yearly step-up (default 0)", 0, 9.5, INK_2)]),
    ("2  Smart split", [(r"$V=\sum_i h_i+C_t$", 0.3, 11),
                        (r"$gap_i=\max(w_iV-h_i,\,0)$", 0.3, 11),
                        ("fill gaps first, rest", 0, 9.5, INK_2),
                        (r"pro-rata $\propto w_i$  (no selling)", 0, 9.5, INK_2)]),
    ("3  Band rebalance", [(r"if $\max_i\left|\frac{h_i}{\sum h}-w_i\right|>5\%$", 0.9, 11),
                           (r"then $h\leftarrow w\cdot\sum_i h_i$", 0.3, 11),
                           ("(Optimized: fired 0 of 119 months)", 0, 9.5, INK_2)]),
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
ax.text(50, y_loop + 0.5, "next month  (repeat 119 times)", fontsize=10, color=C_ENG,
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
         (r"Max drawdown $=\min_t\left(\dfrac{G_t}{\max_{s\leq t}G_s}-1\right)$", 3.4, 11),
         (r"Sharpe vs Liquid $=\dfrac{12\,\overline{(TWR-r_{Liq})}}{\sigma}$", 3.2, 11),
         (r"Worst wealth drop: same on account value", 0.8, 10.5),
         (r"Sell turnover $=\dfrac{\sum sold}{\overline{V}\cdot years}$", 0, 11)]
box(2.5, y6 + 1.3, 26.5, 29.5, None, left, colour=C_MET, gap=2.6)
box(30, y6 + 1.3, 26.5, 29.5, None, right, colour=C_MET, gap=2.6)

# ---------------------------------------------------------------- 6b. analysis + outputs
layer(60, y6 + 11, 39, 24, C_ANA, "⑦ Robustness", "sip/analysis.py")
box(61.5, y6 + 12.3, 36, 17.5, None, [
    ("Rolling: 60 separate 5-year SIPs (every start month)", 0, 10),
    ("Train/test: best of 66 mixes on 2010–14 → 2015–19", 0, 10),
    ("Hindsight grid: all 66 mixes on a 10% grid", 0, 10),
    ("Sensitivity: look-back 60/90/120, band 3/5/10%", 0, 10),
    (r"Stress (2011, 2013, 2015–16, 2018):  $\prod(1+TWR_t)-1$", 0, 10)],
    colour=C_ANA, gap=3.2)
layer(60, y6, 39, 10, C_OUT, "⑧ Outputs", "")
ax.text(61.5, y6 + 5.6, "07_comparison/run.py · each folder's results/  (tables, charts)",
        fontsize=9.8, color=INK, va="top")
ax.text(61.5, y6 + 3.0, "06_optimized_sip/recommend.py → next split  ·  21 tests",
        fontsize=9.8, color=INK, va="top")
arrow(29.5, y5, 29.5, y6 + 35, C_ENG)
arrow(79.5, y5, 79.5, y6 + 35, C_ENG)
arrow(58, y6 + 20, 60, y6 + 20, C_MET, lw=1.4)

for ext in ("png", "svg", "pdf"):
    fig.savefig(OUT / f"architecture.{ext}", dpi=200 if ext == "png" else None,
                facecolor=fig.get_facecolor())
print("wrote", *(OUT / f"architecture.{e}" for e in ("png", "svg", "pdf")))
