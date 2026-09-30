"""Build docs/SIP_Formulas_Guide.pdf: every formula of every strategy, step by step, with
real-number examples and a flowchart at the end.

    python docs/make_formulas_pdf.py        (run after run_all.py; needs Chromium or Chrome)

All numbers are taken from the engine itself (the traced months are re-computed and checked
against sip/engine.py), so the PDF always matches the code.
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_readmes as mr  # noqa: E402  (loads the data and runs all six strategies)

from sip.optimize import max_sharpe, risk_parity  # noqa: E402

OUT = HERE / "SIP_Formulas_Guide.pdf"
ASSETS = mr.ASSETS
R = mr.R
STRATS = mr.STRATS
RESULTS = mr.RESULTS
COLOURS = ["#2a78d6", "#7a5bd6", "#1a9e75", "#eda100", "#d6453d", "#0f6e8c"]
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["svg.fonttype"] = "path"


# --------------------------------------------------------------------------- helpers
def F(latex: str, size: int = 17) -> str:
    """A formula typeset by matplotlib and embedded as an SVG image."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=size)
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.03, transparent=True)
    plt.close(fig)
    data = base64.b64encode(buf.getvalue()).decode()
    return f'<img class="f" src="data:image/svg+xml;base64,{data}">'


def Rs(v: float, d: int = 2) -> str:
    s = f"₹{abs(v):,.{d}f}"
    return "−" + s if v < -1e-9 else s


def P(v: float, d: int = 2) -> str:
    return f"{v * 100:.{d}f}%".replace("-", "−")


def SP(v: float, d: int = 2) -> str:
    return ("+" if v >= 0 else "−") + f"{abs(v) * 100:.{d}f}%"


def month_name(p) -> str:
    return p.strftime("%b %Y")


def trace(i: int, t: int) -> dict:
    s = STRATS[i]
    return mr.trace_month(s, RESULTS[s.name], t)


def symbols(rows: list[tuple[str, str]]) -> str:
    return ('<table class="sym">' + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows)
            + "</table>")


def step(n: str, title: str, plain: str, formula: str, syms: list[tuple[str, str]],
         example: str) -> str:
    return f"""
<div class="step">
  <div class="stephead"><span class="num">{n}</span>{title}</div>
  <p class="plain">{plain}</p>
  <div class="formula">{formula}</div>
  {symbols(syms)}
  <div class="ex"><b>Example:</b> {example}</div>
</div>"""


def ledger(m: dict, cash_note: str = "") -> str:
    def row(label, v, total=True, cls=""):
        cells = "".join(f"<td>{Rs(x)}</td>" for x in v)
        tot = f"<td>{Rs(float(np.sum(v)))}</td>" if total else "<td></td>"
        return f'<tr class="{cls}"><th>{label}</th>{cells}{tot}</tr>'

    rows = [row("① Start of month (last month's end)", m["h0"]),
            row(f"② Instalment {Rs(m['cash'], 0)} split into{cash_note}", m["split"]),
            row("③ Jars after buying", m["h1"]),
            '<tr><th>③ Share of total after buying</th>'
            + "".join(f"<td>{P(x, 1)}</td>" for x in m["h1"] / m["h1"].sum()) + "<td>100%</td></tr>",
            '<tr><th>Target split w</th>' + "".join(f"<td>{P(x, 1)}</td>" for x in m["w"])
            + "<td>100%</td></tr>"]
    if m["rebal"]:
        rows += [row("④ Rebalance trades (− = sell)", m["trade"], total=False, cls="hl"),
                 row("④ Jars after rebalancing", m["h2"])]
    else:
        rows += ['<tr><th>④ Rebalance?</th><td colspan="4">No</td></tr>']
    rows += [f'<tr><th>⑤ Fee (0.1% of {Rs(m["cost"] * 1000)} traded)</th><td colspan="3">'
             f'taken from every jar in proportion</td><td>−{Rs(m["cost"])}</td></tr>',
             row("⑤ Jars after fee", m["h3"]),
             '<tr><th>⑥ Market return this month r</th>'
             + "".join(f"<td>{SP(x)}</td>" for x in m["r"]) + "<td></td></tr>",
             row("⑥ End of month", m["h4"], cls="bold")]
    head = "<tr><th></th>" + "".join(f"<th>{a}</th>" for a in ASSETS) + "<th>Total</th></tr>"
    return f'<table class="ledger">{head}{"".join(rows)}</table>'


# --------------------------------------------------------------------------- numbers
IDX = mr.IDX
FIRST = month_name(IDX[0])
LAST = month_name(IDX[-1])
N_MONTHS = len(IDX)
AMOUNT = mr.AMOUNT
INVESTED = AMOUNT * N_MONTHS
R0 = R.loc[str(IDX[0])].values
LIQ = R["Liquid"]


def score(i: int) -> dict:
    res = RESULTS[STRATS[i].name]
    tw = res.twr
    rl = LIQ.loc[tw.index]
    g = (1 + tw).cumprod()
    dd = g / g.cummax() - 1
    trough = dd.idxmin()
    peak = g.loc[:trough].idxmax()
    vol = tw.std() * np.sqrt(12)
    from sip.metrics import sip_xirr
    return dict(final=res.total.iloc[-1], xirr=sip_xirr(res), mean=tw.mean(), sd=tw.std(), vol=vol,
                ex=(tw - rl).mean(), shl=(tw - rl).mean() * 12 / vol, sh0=tw.mean() * 12 / vol,
                mdd=dd.min(), peak=peak, trough=trough, gpk=g[peak], gtr=g[trough],
                sold=res.sold.sum(), costs=res.costs.sum(),
                n_rebal=int((res.sold > 0).sum()))


SC = [score(i) for i in range(6)]
LIQ_XIRR = __import__("sip.metrics", fromlist=["sip_xirr"]).sip_xirr(mr.LIQUID_SIP)

# Optimiser inputs for the first decision (Feb 2010) and the Feb 2011 re-fit
WIN0 = R.loc["2000-02":"2010-01"]
MU0 = WIN0.mean().values
COV0 = WIN0.cov().values
W_RP0 = risk_parity(WIN0, 0.10, 0.70)
W_MS0 = max_sharpe(WIN0, 0.10, 0.70)
W_RP_FREE = risk_parity(WIN0, 0.0, 1.0)
WIN1 = R.loc["2001-02":"2011-01"]
W_RP1 = risk_parity(WIN1, 0.10, 0.70)
W_MS1 = max_sharpe(WIN1, 0.10, 0.70)


def port_stats(w):
    sp = float(np.sqrt(w @ COV0 @ w))
    rc = w * (COV0 @ w)
    return dict(sig=sp * np.sqrt(12), rc=rc / rc.sum(), ratio=float(w @ MU0) / sp * np.sqrt(12),
                ret=float(w @ MU0) * 12)


# --------------------------------------------------------------------------- shared steps
def instalment_step(n="2") -> str:
    return step(
        n, "The instalment arrives",
        "On the 1st of every month you pay in the same amount. The formula allows the amount to "
        "grow every year (a “step-up”), but in this project the growth rate is 0, so it is "
        "always ₹10,000.",
        F(r"C_t = A \times (1+g)^{\lfloor t/12 \rfloor}"),
        [(F(r"C_t", 13), "the instalment paid in month t"),
         (F(r"t", 13), f"the month number, counting from 0 ({FIRST} is t = 0, {LAST} is t = {N_MONTHS - 1})"),
         (F(r"A", 13), "the starting instalment = ₹10,000"),
         (F(r"g", 13), "yearly step-up of the instalment = 0 (no step-up)"),
         (F(r"\lfloor t/12 \rfloor", 13), "number of full years passed (t ÷ 12, rounded down)")],
        f"{FIRST}: C = 10,000 × (1 + 0)<sup>0</sup> = <b>₹10,000</b>. Because g = 0, every one of "
        f"the {N_MONTHS} months is ₹10,000, so the total paid in is {N_MONTHS} × ₹10,000 = "
        f"<b>{Rs(INVESTED, 0)}</b>.")


def prorata_step(i: int, n="3") -> str:
    m = trace(i, 0)
    parts = " , ".join(f"{a}: {P(w, 1)} × ₹10,000 = {Rs(x)}" for a, w, x in zip(ASSETS, m["w"], m["split"]))
    return step(
        n, "Split the instalment (pro-rata)",
        "The ₹10,000 is cut into pieces in exactly the target proportions, like cutting a cake "
        "using the same recipe every month. It does not look at what you already own.",
        F(r"x_i = w_i \times C_t"),
        [(F(r"x_i", 13), "rupees that go into jar i this month"),
         (F(r"w_i", 13), "target share of jar i (the shares add up to 100%)"),
         (F(r"C_t", 13), "this month's instalment (₹10,000)")],
        f"{FIRST}: {parts}.")


def smart_step(i: int, t: int, n="3") -> str:
    m = trace(i, t)
    h0, w, cash = m["h0"], m["w"], m["cash"]
    V = h0.sum() + cash
    gap = np.maximum(w * V - h0, 0)
    need = gap.sum()
    gap_rows = "<br>".join(
        f"{a}: max({P(wi, 2)} × {Rs(V)} − {Rs(hi)}, 0) = max({Rs(wi * V)} − {Rs(hi)}, 0) = <b>{Rs(g)}</b>"
        for a, wi, hi, g in zip(ASSETS, w, h0, gap))
    if abs(need - cash) < 0.005:
        case = (f"G = {Rs(need)}: all three jars were below target, so the gaps add up to exactly "
                f"the ₹10,000 available and each jar gets exactly its gap → "
                + ", ".join(f"{a} {Rs(x)}" for a, x in zip(ASSETS, m["split"])) + ".")
    elif need > cash:
        case = (f"G = {Rs(need)} is more than the ₹10,000 available, so each jar gets its share of "
                f"the gaps: x<sub>i</sub> = gap<sub>i</sub> ÷ G × 10,000 → "
                + ", ".join(f"{a} {Rs(x)}" for a, x in zip(ASSETS, m["split"])) + ".")
    else:
        left = cash - need
        case = (f"G = {Rs(need)} is less than ₹10,000, so every gap is filled and the other "
                f"{Rs(left)} is split by the target: x<sub>i</sub> = gap<sub>i</sub> + w<sub>i</sub> × {Rs(left)} → "
                + ", ".join(f"{a} {Rs(x)}" for a, x in zip(ASSETS, m["split"])) + ".")
    return step(
        n, "Split the instalment (smart)",
        "Instead of copying the recipe, the ₹10,000 is sent <i>first</i> to the jars that are "
        "below their target. Think of topping up the emptiest glasses first. This pulls the "
        "portfolio back towards the target <b>without selling anything</b>.",
        F(r"V = \sum_i h_i + C_t \qquad gap_i = \max(w_i V - h_i,\ 0) \qquad G = \sum_i gap_i")
        + "<br>" + F(r"\mathrm{If}\ G \geq C_t:\quad x_i = gap_i \times \frac{C_t}{G}")
        + "<br>" + F(r"\mathrm{If}\ G < C_t:\quad x_i = gap_i + w_i \times (C_t - G)"),
        [(F(r"h_i", 13), "rupees already in jar i before buying"),
         (F(r"V", 13), "total wealth after this month's instalment"),
         (F(r"w_i V", 13), "what jar i <i>should</i> hold"),
         (F(r"gap_i", 13), "how many rupees jar i is short of its target (0 if it is already above)"),
         (F(r"G", 13), "all the gaps added together"),
         (F(r"x_i", 13), "rupees that go into jar i this month")],
        f"{month_name(m['month'])}: jars hold "
        + ", ".join(f"{a} {Rs(x)}" for a, x in zip(ASSETS, h0))
        + f"; V = {Rs(h0.sum())} + ₹10,000 = <b>{Rs(V)}</b>.<br>{gap_rows}<br>{case}"
        + (" (In the very first month all jars are empty, so the gaps are exactly w × ₹10,000.)"
           if t == 0 else ""))


def buy_step(i: int, t: int, n="4") -> str:
    m = trace(i, t)
    parts = ", ".join(f"{a}: {Rs(a0)} + {Rs(x)} = {Rs(a1)}" for a, a0, x, a1 in
                      zip(ASSETS, m["h0"], m["split"], m["h1"]))
    return step(
        n, "Buy: put the money in the jars",
        "Each piece of the instalment is added to its jar.",
        F(r"h_i \leftarrow h_i + x_i"),
        [(F(r"h_i", 13), "rupees in jar i (Nifty, Gold or Liquid)"),
         (F(r"\leftarrow", 13), "“becomes”: the new value replaces the old one"),
         (F(r"x_i", 13), "rupees bought for jar i this month")],
        f"{month_name(m['month'])}: {parts}.")


def fee_step(i: int, t: int, n="6") -> str:
    m = trace(i, t)
    traded = m["cost"] * 1000
    extra = (f" = ₹10,000 bought + {Rs(float(np.maximum(m['trade'], 0).sum()))} rebalance buys + "
             f"{Rs(m['sold'])} sold" if m["rebal"] else " (only the instalment was bought)")
    return step(
        n, "Pay the trading fee",
        "Every rupee bought or sold costs 0.1% (10 paise per ₹100), like a broker's charge. "
        "The fee is taken from all jars in proportion to their size, so the split does not change.",
        F(r"Fee = c \times \left(\sum_i buys_i + \sum_i sells_i\right)")
        + "<br>" + F(r"h_i \leftarrow h_i \times \left(1 - \frac{Fee}{V_{start}}\right)"),
        [(F(r"c", 13), "cost rate = 0.1% = 0.001"),
         (F(r"buys_i,\ sells_i", 13), "rupees bought / sold in jar i this month"),
         (F(r"V_{start}", 13), "total of all jars just before the fee"),
         (F(r"1 - Fee/V_{start}", 13), "the fraction of each jar that is kept")],
        f"{month_name(m['month'])}: traded {Rs(traded)}{extra}. Fee = 0.001 × {Rs(traded)} = "
        f"<b>{Rs(m['cost'])}</b>. Each jar keeps 1 − {Rs(m['cost'])} ÷ {Rs(m['start'])} = "
        f"{1 - m['cost'] / m['start']:.6f} of its value → "
        + ", ".join(f"{a} {Rs(x)}" for a, x in zip(ASSETS, m["h3"])) + ".")


def market_step(i: int, t: int, n="7") -> str:
    m = trace(i, t)
    parts = ", ".join(f"{a}: {Rs(a0)} × (1 {'+' if r >= 0 else '−'} {abs(r):.4f}) = {Rs(a1)}"
                      for a, a0, r, a1 in zip(ASSETS, m["h3"], m["r"], m["h4"]) if a0 > 0)
    return step(
        n, "The market moves",
        "During the month each jar grows or shrinks by that asset's return. A +1% month turns "
        "₹100 into ₹101; a −2% month turns it into ₹98.",
        F(r"h_i \leftarrow h_i \times (1 + r_{i,t})"),
        [(F(r"r_{i,t}", 13), "the return of asset i in month t (from 00_raw_data/monthly_returns.csv)")],
        f"{month_name(m['month'])} returns: Nifty {SP(m['r'][0])}, Gold {SP(m['r'][1])}, Liquid "
        f"{SP(m['r'][2])}.<br>{parts}. End-of-month total <b>{Rs(m['h4'].sum())}</b>.")


def twr_step(i: int, t: int, n="8") -> str:
    m = trace(i, t)
    return step(
        n, "Measure this month's return (TWR)",
        "How well did the <i>strategy</i> do this month, ignoring the fact that you added new "
        "money? Compare the value at the end with the value right after the money went in.",
        F(r"TWR_t = \frac{V_{end}}{V_{start}} - 1"),
        [(F(r"V_{end}", 13), "total of all jars at the end of the month"),
         (F(r"V_{start}", 13), "total just after buying (and any rebalancing), before the fee"),
         (F(r"TWR_t", 13), "time-weighted return of month t (the fee counts as part of the loss)")],
        f"{month_name(m['month'])}: {Rs(m['h4'].sum())} ÷ {Rs(m['start'])} − 1 = <b>{SP(m['twr'])}</b>.")


def repeat_box(i: int) -> str:
    res = RESULTS[STRATS[i].name]
    return (f'<div class="repeat">↻ <b>Repeat steps 2–8 for every month</b>, {FIRST} → {LAST} '
            f"({N_MONTHS} times). Each month starts with last month's end-of-month jars. After the "
            f"last month the jars hold <b>{Rs(res.total.iloc[-1], 0)}</b>.</div>")


def score_steps(i: int, n0: int = 9) -> str:
    s = SC[i]
    return "".join([
        step(f"{n0}a", "Score 1: yearly return on your money (XIRR)",
             "Your instalments went in at different times, so a simple average is wrong. XIRR "
             "is the single yearly interest rate that, if a bank paid it on every instalment "
             "from the day you paid it, would give exactly your final value.",
             F(r"\sum_{k=0}^{%d} C_k \times (1 + XIRR)^{(%d - k)/12} = V_{final}"
               % (N_MONTHS - 1, N_MONTHS)),
             [(F(r"C_k", 13), "instalment paid at the start of month k (₹10,000)"),
              (F(r"(%d - k)/12" % N_MONTHS, 13), "years that instalment was invested until the end"),
              (F(r"V_{final}", 13), f"the value at the end of {LAST}")],
             f"{N_MONTHS} instalments of ₹10,000 grew to <b>{Rs(s['final'], 0)}</b>. The rate that "
             f"makes both sides equal (found by trial and error, <code>brentq</code>) is "
             f"<b>XIRR = {P(s['xirr'])}</b> a year. (For comparison, a 100% Liquid SIP gives "
             f"{P(LIQ_XIRR)}.)"),
        step(f"{n0}b", "Score 2: how bumpy is the ride (volatility)",
             "Volatility measures how much the monthly return jumps around its average. Bigger "
             "jumps mean a scarier ride.",
             F(r"\sigma = \mathrm{std}(TWR_1, \ldots, TWR_{%d}) \times \sqrt{12}" % N_MONTHS),
             [(F(r"\mathrm{std}", 13), "standard deviation: the typical distance from the average"),
              (F(r"\sqrt{12}", 13), "turns a monthly figure into a yearly one")],
             f"monthly std = {P(s['sd'])} → σ = {P(s['sd'])} × 3.464 = <b>{P(s['vol'])}</b> a year."),
        step(f"{n0}c", "Score 3: reward per unit of risk (Sharpe vs Liquid)",
             "Liquid (a T-bill fund) earns interest with almost no risk. So the fair question is: "
             "how much <i>extra</i> return did the strategy earn above Liquid, per unit of bumpiness?",
             F(r"Sharpe_{vs\ Liquid} = \frac{12 \times \mathrm{mean}(TWR_t - r_{Liquid,t})}{\sigma}"),
             [(F(r"r_{Liquid,t}", 13), "Liquid's return in month t (≈ the 91-day T-bill rate)"),
              (F(r"12 \times \mathrm{mean}(\ldots)", 13), "average extra return per year"),
              (F(r"\sigma", 13), "volatility from score 2")],
             f"average extra return = {P(s['ex'], 3)} a month → × 12 = {P(s['ex'] * 12)} a year; "
             f"{P(s['ex'] * 12)} ÷ {P(s['vol'])} = <b>{s['shl']:.2f}</b>. (Measured against 0% "
             f"instead of Liquid it would be {s['sh0']:.2f}.)"),
        step(f"{n0}d", "Score 4: worst fall (maximum drawdown)",
             "The biggest drop from a high point to a later low point, as if ₹1 had followed the "
             "strategy's monthly returns. It answers: “what is the worst loss I would have felt?”",
             F(r"G_t = \prod_{k \leq t} (1 + TWR_k) \qquad MDD = \min_t \left(\frac{G_t}{\max_{k \leq t} G_k} - 1\right)"),
             [(F(r"G_t", 13), "growth of ₹1 up to month t"),
              (F(r"\max_{k \leq t} G_k", 13), "the highest point reached so far"),
              (F(r"MDD", 13), "the deepest fall below a previous high")],
             f"₹1 grew to {Rs(s['gpk'], 4)} by {month_name(s['peak'])}, then fell to "
             f"{Rs(s['gtr'], 4)} by {month_name(s['trough'])}: {s['gtr']:.4f} ÷ {s['gpk']:.4f} − 1 = "
             f"<b>{P(s['mdd'], 1)}</b>."),
    ])


def result_strip(i: int) -> str:
    s = SC[i]
    cells = [("Paid in", Rs(INVESTED, 0)), ("Final value", Rs(s["final"], 0)),
             ("XIRR", P(s["xirr"], 1)), ("Volatility", P(s["vol"], 1)),
             ("Sharpe vs Liquid", f"{s['shl']:.2f}"), ("Max drawdown", P(s["mdd"], 1))]
    return '<div class="strip">' + "".join(
        f'<div><span>{a}</span><b>{b}</b></div>' for a, b in cells) + "</div>"


def switches(contribution: str, target: str, rebalance: str) -> str:
    return f"""<table class="switch">
<tr><th>Setting</th><th>This strategy</th></tr>
<tr><td>Where the target split w comes from</td><td>{target}</td></tr>
<tr><td>How each instalment is split</td><td>{contribution}</td></tr>
<tr><td>When the whole portfolio is rebalanced</td><td>{rebalance}</td></tr>
<tr><td>Instalment, fee, market move, TWR, scoring</td><td>Same for all six strategies</td></tr>
</table>"""


def section_head(i: int, title: str, idea: str) -> str:
    return (f'<section class="strat" style="--c:{COLOURS[i]}"><h1><span class="tag">Strategy '
            f'{i + 1}</span>{title}</h1><p class="idea">{idea}</p>')


# --------------------------------------------------------------------------- per strategy
def rebalance_none_step(i: int, t: int, why: str) -> str:
    m = trace(i, t)
    share = ", ".join(f"{a} {P(x, 1)}" for a, x in zip(ASSETS, m["h1"] / m["h1"].sum()))
    return step(
        "5", "Rebalance? Never",
        why,
        F(r"\mathrm{rebalance} = \mathrm{no}\quad(\mathrm{every\ month})"),
        [(F(r"\mathrm{rule}", 13), "<code>rebalance=\"none\"</code> in strategy.py")],
        f"{month_name(m['month'])}: split after buying = {share}. Nothing is sold, so no trades.")


def calendar_step(i: int) -> str:
    m = trace(i, 11)
    V = m["h1"].sum()
    rows = "<br>".join(f"{a}: {P(w, 0)} × {Rs(V)} − {Rs(h)} = <b>{Rs(tr)}</b> "
                       f"({'sell' if tr < 0 else 'buy'})"
                       for a, w, h, tr in zip(ASSETS, m["w"], m["h1"], m["trade"]))
    return step(
        "5", "Rebalance? Once a year (calendar rule)",
        "Every 12 months the jars are put back to exactly 60/20/20: sell some of the jars that "
        "grew too big and buy the jars that fell behind. The total does not change, money only "
        "moves between jars. In the other 11 months nothing happens here.",
        F(r"\mathrm{rebalance\ if}\quad n_{since} \geq 12")
        + "<br>" + F(r"trade_i = w_i \times \sum_j h_j - h_i \qquad h_i \leftarrow w_i \times \sum_j h_j"),
        [(F(r"n_{since}", 13), "months since the last rebalance (counts 1, 2, … 12)"),
         (F(r"\sum_j h_j", 13), "total of all jars"),
         (F(r"trade_i", 13), "rupees to buy (+) or sell (−) in jar i")],
        f"{FIRST} is month 1, so the first rebalance is month 12 = {month_name(m['month'])}. After "
        f"buying, the total is {Rs(V)}:<br>{rows}.<br>Sold {Rs(m['sold'])}, bought the same "
        f"amount. It happened {SC[i]['n_rebal']} times in 10 years (every January 2011–2019).")


def band_step(i: int) -> str:
    m = trace(i, 12)
    share = m["h1"] / m["h1"].sum()
    diffs = ", ".join(f"{a} |{P(s, 2)} − {P(w, 2)}| = {P(abs(s - w), 2)}"
                      for a, s, w in zip(ASSETS, share, m["w"]))
    return step(
        "5", "Rebalance? Only if something drifts more than 5% (band rule)",
        "After buying, the engine measures how far each jar's share is from its target. If "
        "the biggest gap (the <i>drift</i>) is more than 5 percentage points, the jars are "
        "reset to the target exactly as in the calendar rule. Otherwise nothing is sold.",
        F(r"drift = \max_i \left| \frac{h_i}{\sum_j h_j} - w_i \right| \qquad "
          r"\mathrm{rebalance\ if}\ drift > 0.05")
        + "<br>" + F(r"trade_i = w_i \times \sum_j h_j - h_i"),
        [(F(r"h_i / \sum_j h_j", 13), "jar i's actual share of the total"),
         (F(r"|\ldots|", 13), "size of the gap, ignoring its sign"),
         (F(r"\max_i", 13), "the biggest of the three gaps"),
         (F(r"0.05", 13), "the 5% band")],
        f"{month_name(m['month'])}: {diffs}. Drift = {P(m['drift'], 2)}, below 5% → "
        f"<b>no rebalance</b>. The smart split already filled the gaps. Over 10 years the band "
        f"was never crossed (0 rebalances), so this strategy never sold anything.")


def target_fixed_step(i: int, weights: str, why: str) -> str:
    return step(
        "1", "Choose the target split (fixed)",
        why, F(weights),
        [(F(r"w_i", 13), "target share of jar i; the three shares add up to 1 (100%)")],
        "the same target is used in every one of the 119 months. Nothing is learned from data.")


def optimiser_steps(i: int) -> str:
    stats_rp, stats_ms = port_stats(W_RP0), port_stats(W_MS0)
    mu_txt = ", ".join(f"{a} {P(m * 12, 1)}" for a, m in zip(ASSETS, MU0))
    vol_txt = ", ".join(f"{a} {P(np.sqrt(v * 12), 1)}" for a, v in zip(ASSETS, np.diag(COV0)))
    wtxt = lambda w: " / ".join(f"{a} {P(x, 1)}" for a, x in zip(ASSETS, w))  # noqa: E731
    out = [step(
        "1a", "Look back 10 years: average return μ and covariance Σ",
        "Before each yearly decision the optimiser studies only the <b>past</b> 120 months. "
        "It never sees the future. For the first SIP month it uses Feb 2000 – Jan 2010.",
        F(r"\mu_i = \frac{1}{120}\sum_{k=1}^{120} r_{i,t-k} \qquad "
          r"\Sigma_{ij} = \frac{1}{119}\sum_{k=1}^{120}(r_{i,t-k}-\mu_i)(r_{j,t-k}-\mu_j)"),
        [(F(r"\mu_i", 13), "average monthly return of asset i over the last 120 months"),
         (F(r"\Sigma_{ij}", 13), "covariance: how assets i and j move together "
                                 "(Σ<sub>ii</sub> is asset i's variance = volatility²)"),
         (F(r"r_{i,t-k}", 13), "return of asset i, k months ago")],
        f"Feb 2000 – Jan 2010 (as yearly figures): average return {mu_txt}; volatility {vol_txt}. "
        f"Liquid barely moves (volatility {P(np.sqrt(COV0[2, 2] * 12), 1)}): it looks almost "
        f"risk-free to the optimiser.")]
    rules = step(
        "1c", "Limits every optimiser must obey",
        "To stop the optimiser putting everything in one asset, each weight is kept between "
        "10% and 70%, and the weights must add up to 100%. The best weights are found by a "
        "standard solver (SLSQP) that tries weights until the goal cannot be improved.",
        F(r"0.10 \leq w_i \leq 0.70 \qquad \sum_i w_i = 1"),
        [(F(r"0.10,\ 0.70", 13), "lowest / highest allowed share of any asset")],
        "Liquid ends up at the 70% cap in every year. Without the cap, risk parity would put "
        f"{P(W_RP_FREE[2], 1)} in Liquid.")
    refit = step(
        "1d", "Re-learn every year (walk-forward)",
        "Every 12 months (each February) the 10-year window moves forward one year and steps "
        "1a–1c are repeated. The new target is used for the next 12 months.",
        F(r"w^{(Feb\ Y)} = \mathrm{optimiser}(r_{Feb\,Y-10}, \ldots, r_{Jan\,Y})"),
        [(F(r"Y", 13), "the year of the decision (2010, 2011, …, 2019)")],
        "Feb 2011 uses Feb 2001 – Jan 2011, …, Feb 2019 uses Feb 2009 – Jan 2019. "
        "10 decisions in total.")
    if i == 3:
        out.append(step(
            "1b", "Risk parity: every asset adds the same amount of risk",
            "The idea: don't let one asset dominate the risk. Each asset's <i>risk "
            "contribution</i> (its weight × how much it moves the whole portfolio) should be equal. "
            "The optimiser picks the weights that make the three contributions as equal as possible.",
            F(r"RC_i = w_i \times (\Sigma w)_i \qquad \min_w \sum_i \left(RC_i - \overline{RC}\right)^2"),
            [(F(r"(\Sigma w)_i", 13), "how much asset i moves together with the whole portfolio"),
             (F(r"RC_i", 13), "risk contribution of asset i (they add up to the portfolio variance)"),
             (F(r"\overline{RC}", 13), "the average of the three contributions")],
            f"Feb 2010 result: <b>{wtxt(W_RP0)}</b>. Shares of risk: "
            + ", ".join(f"{a} {P(x, 0)}" for a, x in zip(ASSETS, stats_rp["rc"]))
            + ". Liquid can't reach an equal share because it hits the 70% cap (its share is "
            "slightly negative because it tends to rise when Nifty falls)."))
        out += [rules, refit]
    elif i == 4:
        r602 = port_stats(np.array([0.6, 0.2, 0.2]))
        out.append(step(
            "1b", "Max Sharpe: the most return per unit of risk",
            "The optimiser tries every allowed mix and keeps the one with the highest "
            "expected return divided by expected risk.",
            F(r"\max_w \ \frac{w^{\top}\mu}{\sqrt{w^{\top}\Sigma\, w}}"),
            [(F(r"w^{\top}\mu", 13), "expected monthly return of the mix = Σ w<sub>i</sub> μ<sub>i</sub>"),
             (F(r"\sqrt{w^{\top}\Sigma w}", 13), "expected monthly volatility of the mix"),
             (F(r"\max_w", 13), "choose the weights w that make this ratio largest")],
            f"Feb 2010 result: <b>{wtxt(W_MS0)}</b>, ratio (per year) = {P(stats_ms['ret'], 1)} ÷ "
            f"{P(stats_ms['sig'], 1)} = <b>{stats_ms['ratio']:.2f}</b>. Compare 60/20/20: "
            f"{P(r602['ret'], 1)} ÷ {P(r602['sig'], 1)} = {r602['ratio']:.2f}. The Liquid-heavy "
            f"mix wins because this ratio measures return against 0%, not against Liquid."))
        out += [rules, refit]
    else:
        w6 = 0.5 * W_RP0 + 0.5 * W_MS0
        out = out[:1] + [step(
            "1b", "Run both optimisers, then average them",
            "The Optimized SIP asks both experts from Strategies 4 and 5 and takes the middle "
            "of their answers. Averaging makes the target steadier than either on its own.",
            F(r"w^{RP} = \arg\min_w \sum_i (RC_i - \overline{RC})^2 \qquad "
              r"w^{MS} = \arg\max_w \frac{w^{\top}\mu}{\sqrt{w^{\top}\Sigma w}}")
            + "<br>" + F(r"w^{Opt}_i = \frac{1}{2}\,w^{RP}_i + \frac{1}{2}\,w^{MS}_i"),
            [(F(r"w^{RP}", 13), "risk-parity weights (Strategy 4, equal risk contributions)"),
             (F(r"w^{MS}", 13), "max-Sharpe weights (Strategy 5, best return per risk)"),
             (F(r"w^{Opt}", 13), "the Optimized SIP target")],
            "Feb 2010: " + ", ".join(
                f"{a}: ½ × {P(a1, 2)} + ½ × {P(a2, 2)} = <b>{P(a3, 2)}</b>"
                for a, a1, a2, a3 in zip(ASSETS, W_RP0, W_MS0, w6)) + "."), rules, refit]
    return "".join(out)


def money_story(i: int, t: int, intro: str, outro: str) -> str:
    m = trace(i, t)
    return (f'<div class="money"><h2>Money example: {month_name(m["month"])}, all steps together</h2>'
            f"<p>{intro}</p>{ledger(m)}<p>{outro} The month's return: {Rs(m['h4'].sum())} ÷ "
            f"{Rs(m['start'])} − 1 = <b>{SP(m['twr'])}</b>. Paid in so far: "
            f"{Rs(m['invested'], 0)}.</p></div>")


def strategy1() -> str:
    i = 0
    m1 = trace(i, 1)
    return "".join([
        section_head(i, "Equity SIP: 100% Nifty 50",
                     "The usual SIP most people do: the whole ₹10,000 goes into a Nifty 50 index "
                     "fund every month. It is the benchmark the other five are compared with."),
        switches("Pro-rata (all of it to Nifty)", "Fixed: 100 / 0 / 0", "Never"),
        "<h2>The steps and their formulas</h2>",
        target_fixed_step(i, r"w = (w_{Nifty},\ w_{Gold},\ w_{Liquid}) = (1,\ 0,\ 0)",
                          "Everything goes to Nifty. Gold and Liquid get nothing."),
        instalment_step(), prorata_step(i), buy_step(i, 0),
        rebalance_none_step(i, 0, "There is only one jar with money in it, so there is nothing "
                                  "to rebalance."),
        fee_step(i, 0), market_step(i, 0), twr_step(i, 0), repeat_box(i),
        money_story(i, 1, "The second month, showing how the jar builds up: last month's "
                          "₹10,083.18 is still there, and the new ₹10,000 is added on top.",
                    f"Nifty rose {P(m1['r'][0])} in March 2010, and the <i>whole</i> "
                    f"{Rs(m1['h3'][0])} earned it, not only the new ₹10,000."),
        "<h2>Scoring after 119 months</h2>", score_steps(i), result_strip(i), "</section>"])


def strategy2() -> str:
    i = 1
    m1 = trace(i, 1)
    return "".join([
        section_head(i, "Equal-weight SIP: ⅓ each",
                     "The simplest way to diversify: split every ₹10,000 equally between Nifty, "
                     "Gold and Liquid, and never sell anything."),
        switches("Pro-rata (⅓ each)", "Fixed: ⅓ / ⅓ / ⅓", "Never"),
        "<h2>The steps and their formulas</h2>",
        target_fixed_step(i, r"w = (\frac{1}{3},\ \frac{1}{3},\ \frac{1}{3})",
                          "Each asset gets one third, a split that needs no forecasts at all."),
        instalment_step(), prorata_step(i), buy_step(i, 0),
        rebalance_none_step(i, 1, "The jars are allowed to drift. If Nifty booms, its share "
                                  "grows above ⅓ and stays there. The only thing that pulls it "
                                  "back is that each new instalment is split equally."),
        fee_step(i, 0), market_step(i, 0), twr_step(i, 0), repeat_box(i),
        money_story(i, 1, "The second month. After February, Gold's jar is the biggest because "
                          "gold rose most; the new ₹10,000 is still split equally.",
                    f"In March Nifty rose {P(m1['r'][0])} but gold fell {P(-m1['r'][1])}, so "
                    f"the jars moved in opposite directions. That is diversification at work."),
        "<h2>Scoring after 119 months</h2>", score_steps(i), result_strip(i), "</section>"])


def strategy3() -> str:
    i = 2
    m = trace(i, 11)
    return "".join([
        section_head(i, "Fixed 60/20/20 SIP, rebalanced every year",
                     "A classic balanced mix: 60% Nifty for growth, 20% Gold as a hedge and 20% "
                     "Liquid as a cushion. Once a year the jars are reset to 60/20/20."),
        switches("Pro-rata (60/20/20)", "Fixed: 60 / 20 / 20", "Every 12 months (calendar)"),
        "<h2>The steps and their formulas</h2>",
        target_fixed_step(i, r"w = (0.60,\ 0.20,\ 0.20)",
                          "A conventional balanced split chosen by hand, not fitted to the data."),
        instalment_step(), prorata_step(i), buy_step(i, 0), calendar_step(i),
        fee_step(i, 0), market_step(i, 0), twr_step(i, 0), repeat_box(i),
        money_story(i, 11, "The 12th month, the first yearly rebalance. Nifty had grown to "
                           "61.2% and Liquid had fallen to 18.5%, so money is moved from Nifty "
                           "and Gold into Liquid.",
                    f"Nifty then fell {P(-m['r'][0])} in January 2011. Because ₹1,582 had just "
                    f"been moved out of Nifty into Liquid, the fall hurt a little less. The fee was "
                    f"{Rs(m['cost'])} instead of ₹10, because the rebalance trades also pay 0.1%."),
        "<h2>Scoring after 119 months</h2>", score_steps(i), result_strip(i), "</section>"])


def optimiser_strategy(i: int, title: str, idea: str, target: str) -> str:
    m = trace(i, 12)
    return "".join([
        section_head(i, title, idea),
        switches("Smart (fill the gaps first)", target, "Only if drift > 5% (band)"),
        "<h2>The steps and their formulas</h2>",
        optimiser_steps(i),
        instalment_step(), smart_step(i, 0), buy_step(i, 0), band_step(i),
        fee_step(i, 0), market_step(i, 0), twr_step(i, 0), repeat_box(i),
        '<h2>The smart split in a later month (the jars are no longer empty)</h2>',
        smart_step(i, 12, n="3"),
        money_story(i, 12, "February 2011: the optimiser has just re-learned the target from "
                           "Feb 2001 – Jan 2011 and the smart split fills the gaps.",
                    f"The new money went mostly where it was needed, so the split after buying "
                    f"equals the target and no selling was necessary. In the market move Nifty "
                    f"fell {P(-m['r'][0])} while Gold rose {P(m['r'][1])}."),
        "<h2>Scoring after 119 months</h2>", score_steps(i), result_strip(i), "</section>"])


# --------------------------------------------------------------------------- intro + ending
def cover() -> str:
    return f"""
<section class="cover">
  <div class="kicker">BTP · A Simple Optimized SIP Strategy for Multi-Asset Allocation</div>
  <h1 class="title">The Formulas Behind Each Strategy</h1>
  <p class="sub">Six ways to invest ₹10,000 every month in Nifty 50, Gold and a Liquid fund,
  explained step by step with the maths, a plain-language example for every step and real
  rupee numbers from the back-test ({FIRST} – {LAST}).</p>
  <h2>How to read this document</h2>
  <ol>
    <li><b>Part A</b> explains the ideas and symbols used everywhere (read this first).</li>
    <li><b>Strategies 1–6</b> each go through the SIP engine from start to finish. Every step
      has: what happens in plain words → the formula → what each symbol means → an example with
      real numbers.</li>
    <li>Each strategy then shows <b>one full month in rupees</b>, and its <b>scores after 10 years</b>.</li>
    <li>The last pages compare all six and show the <b>flowchart</b> of the whole process.</li>
  </ol>
  <h2>The six strategies</h2>
  <table class="overview">
    <tr><th>#</th><th>Strategy</th><th>Target split</th><th>Instalment split</th><th>Rebalance</th></tr>
    <tr><td>1</td><td>Equity SIP</td><td>100% Nifty</td><td>pro-rata</td><td>never</td></tr>
    <tr><td>2</td><td>Equal-weight SIP</td><td>⅓ each</td><td>pro-rata</td><td>never</td></tr>
    <tr><td>3</td><td>60/20/20 SIP</td><td>60 / 20 / 20</td><td>pro-rata</td><td>every 12 months</td></tr>
    <tr><td>4</td><td>Risk-parity SIP</td><td>optimiser: equal risk</td><td>smart</td><td>drift &gt; 5%</td></tr>
    <tr><td>5</td><td>Max-Sharpe SIP</td><td>optimiser: best return/risk</td><td>smart</td><td>drift &gt; 5%</td></tr>
    <tr><td>6</td><td>Optimized SIP</td><td>average of 4 and 5</td><td>smart</td><td>drift &gt; 5%</td></tr>
  </table>
  <p class="note">All numbers in this document are produced by the project's code
  (<code>sip/engine.py</code>); the example months are recomputed step by step and checked
  against the engine's own output.</p>
</section>"""


def part_a() -> str:
    r0 = ", ".join(f"{a} {SP(x)}" for a, x in zip(ASSETS, R0))
    IMG = [F(r"r_{i,t} = \frac{P_{i,t}}{P_{i,t-1}} - 1"), F("t", 13), F("i", 13), F("C_t", 13), F("w_i", 13), F("h_i", 13), F("x_i", 13), F(r"\sum_i", 13), F(r"\leftarrow", 13), F(r"r_{i,t}", 13), F("c", 13), F(r"\mu,\ \Sigma", 13)]
    SYMS = symbols([(F(r"P_{i,t}", 13), "month-end price of asset i in month t (Nifty adds 1.3%/12 for dividends; "
                              "gold is converted to rupees: $ price × ₹ per $)"),
          (F(r"r_{i,t}", 13), "the return of asset i in month t, e.g. 0.0093 = +0.93%")])
    return f"""
<section class="parta">
<h1><span class="tag">Part A</span>The ideas and symbols used everywhere</h1>
<h2>The three jars</h2>
<p>Picture your SIP as <b>three jars of money</b>: a Nifty 50 jar (Indian shares), a Gold jar
(gold priced in rupees) and a Liquid jar (a fund that earns the 91-day Treasury-bill interest
rate). Every month:</p>
<ol class="tight">
<li>₹10,000 arrives and is <b>split</b> between the jars;</li>
<li>maybe the jars are <b>rebalanced</b> (money moved between them);</li>
<li>a small <b>fee</b> is paid on everything bought or sold;</li>
<li>the <b>market</b> makes each jar grow or shrink by that asset's return.</li>
</ol>
<p>This loop is the <b>SIP engine</b> (<code>sip/engine.py</code>). All six strategies use the
same engine. They differ only in <b>three settings</b>: the target split, how the instalment is
split, and when to rebalance.</p>

<h2>The input: monthly returns</h2>
<p>From the daily data (<code>00_raw_data/</code>) each asset gets one return per month, the
growth of ₹1 over that month:</p>
<div class="formula">{IMG[0]}</div>
{SYMS}
<div class="ex"><b>Example:</b> {FIRST}: {r0}. A ₹100 Nifty holding became ₹100.93.</div>

<h2>Symbols</h2>
<table class="sym big">
<tr><td>{IMG[1]}</td><td>month number: {FIRST} = 0, … , {LAST} = {N_MONTHS - 1}</td></tr>
<tr><td>{IMG[2]}</td><td>which jar: Nifty, Gold or Liquid</td></tr>
<tr><td>{IMG[3]}</td><td>the instalment paid at the start of month t (₹10,000)</td></tr>
<tr><td>{IMG[4]}</td><td>target share of jar i (e.g. 0.60 = 60%); the three add up to 1</td></tr>
<tr><td>{IMG[5]}</td><td>rupees currently in jar i (“holdings”)</td></tr>
<tr><td>{IMG[6]}</td><td>rupees of this month's instalment that go into jar i</td></tr>
<tr><td>{IMG[7]}</td><td>“add up over all jars”</td></tr>
<tr><td>{IMG[8]}</td><td>“becomes”: the jar's new value replaces the old one</td></tr>
<tr><td>{IMG[9]}</td><td>return of asset i in month t</td></tr>
<tr><td>{IMG[10]}</td><td>trading cost = 0.1% of every rupee bought or sold</td></tr>
<tr><td>{IMG[11]}</td><td>average returns and covariance (only used by the optimisers, Strategies 4–6)</td></tr>
</table>

<h2>The engine in one picture</h2>
<div class="loop">
<div>① Start with last month's jars</div><div>→</div>
<div>② ₹10,000 arrives, split into x<sub>i</sub></div><div>→</div>
<div>③ Buy: h<sub>i</sub> + x<sub>i</sub></div><div>→</div>
<div>④ Rebalance?</div><div>→</div>
<div>⑤ Fee 0.1%</div><div>→</div>
<div>⑥ Market: × (1 + r)</div>
</div>
<p class="center">↻ repeated {N_MONTHS} times ({FIRST} → {LAST}), then the strategy is scored.</p>
<p>In each strategy section the steps are numbered 1–9: step 1 sets the target, steps 2–8 are
one month of the engine (①–⑥ above, plus measuring the month's return), and step 9 scores the
result.</p>
</section>"""


def comparison() -> str:
    names = ["Equity (100% Nifty)", "Equal-weight ⅓ each", "60/20/20 annual", "Risk parity",
             "Max Sharpe", "Optimized (½ + ½)"]
    rows = "".join(
        f'<tr><td><span class="dot" style="background:{COLOURS[i]}"></span>{i + 1} · {n}</td>'
        f"<td>{Rs(s['final'], 0)}</td><td>{P(s['xirr'], 1)}</td><td>{P(s['vol'], 1)}</td>"
        f"<td>{s['shl']:.2f}</td><td>{P(s['mdd'], 1)}</td></tr>"
        for i, (n, s) in enumerate(zip(names, SC)))
    best = max(range(6), key=lambda k: SC[k]["shl"])
    return f"""
<section class="compare">
<h1><span class="tag">Summary</span>All six side by side</h1>
<p>Same data, same {N_MONTHS} months, same ₹10,000 instalments ({Rs(INVESTED, 0)} paid in),
same 0.1% fee.</p>
<table class="cmp">
<tr><th>Strategy</th><th>Final value</th><th>XIRR</th><th>Volatility</th><th>Sharpe vs Liquid</th><th>Max drawdown</th></tr>
{rows}
<tr class="ref"><td>Reference: 100% Liquid SIP</td><td></td><td>{P(LIQ_XIRR, 1)}</td><td></td><td></td><td></td></tr>
</table>
<ul>
<li><b>Most money:</b> Strategy 1, 100% Nifty ({P(SC[0]['xirr'], 1)} a year), but with the deepest fall ({P(SC[0]['mdd'], 1)}).</li>
<li><b>Best reward per unit of risk, measured fairly against Liquid:</b> Strategy {best + 1},
60/20/20 (Sharpe vs Liquid {SC[best]['shl']:.2f}).</li>
<li><b>Smallest falls:</b> Strategies 4–6 (about {P(SC[5]['mdd'], 1)}), because the optimisers put
70% in Liquid. They earned only about {P(SC[5]['xirr'] - LIQ_XIRR, 1)} a year more than a 100% Liquid SIP.</li>
</ul>
</section>"""


def flowchart() -> str:
    def box(title, body, cls=""):
        return f'<div class="fbox {cls}"><div class="ft">{title}</div>{body}</div>'

    arrow = '<div class="farrow">▼</div>'
    parts = [
        '<section class="flow"><h1><span class="tag">Flowchart</span>The whole process, formula at each step</h1><div class="fgrid"><div class="fmain">',
        box("DATA: monthly returns (00_raw_data)", F(r"r_{i,t} = P_{i,t}/P_{i,t-1} - 1", 14)
            + "<small>Nifty (+ dividends) · Gold in ₹ = $ price × USD/INR · Liquid (T-bill index), Feb 2000 – Dec 2019</small>", "data"),
        arrow,
        box("STEP 1: TARGET SPLIT w (each strategy's own rule)",
            '<div class="tsplit"><div><b>1–3 · fixed</b><br>(1,0,0) · (⅓,⅓,⅓) · (0.6,0.2,0.2)</div>'
            '<div><b>4 · risk parity</b><br>' + F(r"\min \sum (RC_i - \overline{RC})^2", 13) + '</div>'
            '<div><b>5 · max Sharpe</b><br>' + F(r"\max\ w^{\top}\mu / \sqrt{w^{\top}\Sigma w}", 13) + '</div>'
            '<div><b>6 · optimized</b><br>' + F(r"\frac{1}{2}w^{RP} + \frac{1}{2}w^{MS}", 13) + '</div></div>'
            + "<small>4–6: μ, Σ from the previous 120 months only · 10% ≤ w ≤ 70% · re-fit every February</small>",
            "target"),
        arrow,
        '<div class="floop"><div class="looplabel">MONTHLY SIP ENGINE · repeated %d times (%s → %s)</div>' % (N_MONTHS, FIRST, LAST),
        box("2 · Instalment", F(r"C_t = A(1+g)^{\lfloor t/12 \rfloor}", 14) + "<small>A = ₹10,000, g = 0 → always ₹10,000</small>"),
        arrow,
        box("3 · Split the instalment", '<div class="two"><div><b>pro-rata</b> (1–3)<br>'
            + F(r"x_i = w_i C_t", 14) + '</div><div><b>smart</b> (4–6)<br>'
            + F(r"gap_i = \max(w_i V - h_i, 0)", 13) + "<br>fill gaps first, rest by w</div></div>"),
        arrow,
        box("4 · Buy", F(r"h_i \leftarrow h_i + x_i", 14)),
        arrow,
        box("5 · Rebalance?", '<div class="three"><div><b>none</b> (1, 2)</div><div><b>calendar</b> (3)<br>every 12 months</div>'
            '<div><b>band</b> (4–6)<br>' + F(r"\max_i |h_i/\sum h - w_i| > 5\%", 13) + "</div></div>"
            + "if yes: " + F(r"h_i \leftarrow w_i \sum_j h_j", 13)),
        arrow,
        box("6 · Fee", F(r"Fee = 0.001 \times (buys + sells) \qquad h_i \leftarrow h_i (1 - Fee/V_{start})", 13)),
        arrow,
        box("7 · Market move", F(r"h_i \leftarrow h_i\,(1 + r_{i,t})", 14)),
        arrow,
        box("8 · Month's return", F(r"TWR_t = V_{end}/V_{start} - 1", 14)),
        '<div class="loopback">↺ next month: t → t + 1</div></div>',
        arrow,
        box("STEP 9: SCORE EACH STRATEGY",
            '<div class="two"><div>' + F(r"\sum_k C_k (1+XIRR)^{(%d-k)/12} = V_{final}" % N_MONTHS, 13)
            + "<br>" + F(r"\sigma = \mathrm{std}(TWR) \sqrt{12}", 13) + "</div><div>"
            + F(r"Sharpe_{Liq} = 12\,\mathrm{mean}(TWR - r_{Liq}) / \sigma", 13) + "<br>"
            + F(r"MDD = \min (G_t / \max G - 1)", 13) + "</div></div>", "score"),
        arrow,
        box("COMPARE ALL SIX (07_comparison)", "<small>same data, months, instalments and fees → "
            "final value, XIRR, volatility, Sharpe vs Liquid, max drawdown</small>", "data"),
        "</div></div></section>",
    ]
    return "".join(parts)


CSS = """
@page { size: A4; margin: 15mm 14mm 16mm 14mm;
  @bottom-center { content: counter(page); font: 9pt 'DejaVu Sans', sans-serif; color: #888; } }
* { box-sizing: border-box; }
body { font-family: 'DejaVu Sans', 'Noto Sans', sans-serif; font-size: 10pt; line-height: 1.45;
  color: #1d2330; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 6px; color: #10172a; }
h2 { break-after: avoid; font-size: 13pt; margin: 16px 0 6px; color: #10172a; border-bottom: 1.5px solid #e3e7ef; padding-bottom: 3px; }
section { break-before: page; }
section.cover { break-before: auto; }
.tag { display: inline-block; font-size: 9pt; font-weight: 700; color: #fff; background: var(--c, #334);
  border-radius: 4px; padding: 2px 8px; margin-right: 10px; vertical-align: middle; letter-spacing: .4px; }
.cover .kicker { color: #5a6477; font-size: 10pt; letter-spacing: .5px; margin-top: 30px; }
.cover .title { font-size: 30pt; line-height: 1.15; margin: 10px 0 12px; }
.cover .sub { font-size: 12pt; color: #3a4356; max-width: 165mm; }
.note { color: #5a6477; font-size: 9pt; margin-top: 18px; }
.idea { font-size: 11pt; background: #f5f7fb; border-left: 4px solid var(--c); padding: 8px 12px; margin: 6px 0 10px; }
table { border-collapse: collapse; }
.overview, .switch, .cmp { width: 100%; font-size: 9.5pt; margin: 6px 0; }
.overview th, .overview td, .switch th, .switch td, .cmp th, .cmp td { border: 1px solid #dde2ea; padding: 4px 7px; text-align: left; }
.overview th, .switch th, .cmp th { background: #eef1f6; }
.switch td:first-child { width: 48%; color: #3a4356; }
.step { border: 1px solid #dde2ea; border-left: 4px solid var(--c, #556); border-radius: 5px; padding: 7px 11px 8px;
  margin: 9px 0; break-inside: avoid; }
.stephead { font-weight: 700; font-size: 11pt; margin-bottom: 3px; }
.num { display: inline-block; min-width: 26px; text-align: center; background: var(--c, #556); color: #fff;
  border-radius: 11px; font-size: 9pt; padding: 1px 6px; margin-right: 8px; }
.plain { margin: 2px 0 5px; }
.formula { background: #fbfcfe; border: 1px dashed #cfd6e2; border-radius: 4px; padding: 6px 10px; margin: 4px 0 5px;
  text-align: center; line-height: 2.1; }
img.f { vertical-align: middle; max-width: 100%; }
.sym { font-size: 9pt; margin: 2px 0 4px; }
.sym td { padding: 1px 8px 1px 0; vertical-align: middle; }
.sym td:first-child { white-space: nowrap; text-align: right; min-width: 70px; }
.sym.big td { padding: 2px 10px 2px 0; }
.ex { background: #f4f8f1; border-radius: 4px; padding: 5px 9px; font-size: 9.3pt; }
.repeat { background: #fff8e6; border: 1px solid #f0d99a; border-radius: 5px; padding: 7px 11px; margin: 10px 0; break-inside: avoid; }
.money { break-inside: avoid; }
.ledger { width: 100%; font-size: 8.8pt; margin: 6px 0; }
.ledger th, .ledger td { border: 1px solid #dde2ea; padding: 3px 6px; text-align: right; }
.ledger th:first-child { text-align: left; font-weight: 600; background: #f6f8fb; width: 36%; }
.ledger tr:first-child th { background: #eef1f6; text-align: center; }
.ledger td[colspan] { text-align: center; color: #5a6477; }
.ledger tr.hl td { background: #fff4d9; font-weight: 600; }
.ledger tr.bold td { font-weight: 700; background: #eef6ee; }
.strip { display: flex; gap: 6px; margin: 10px 0; break-inside: avoid; }
.strip div { flex: 1; border: 1px solid #dde2ea; border-top: 3px solid var(--c); border-radius: 4px; padding: 5px 7px; }
.strip span { display: block; font-size: 8pt; color: #5a6477; }
.strip b { font-size: 11pt; }
.tight li { margin: 1px 0; }
.loop { display: flex; align-items: center; gap: 5px; margin: 8px 0 2px; font-size: 9pt; }
.loop div:nth-child(odd) { flex: 1; border: 1.5px solid #8793a8; border-radius: 6px; padding: 6px; text-align: center; background: #f7f9fc; }
.center { text-align: center; color: #3a4356; }
.cmp td:not(:first-child), .cmp th:not(:first-child) { text-align: right; }
.cmp tr.ref td { color: #5a6477; font-style: italic; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; }
.flow h1 { font-size: 15pt; }
.fgrid { display: flex; justify-content: center; }
.fmain { width: 100%; }
.fbox { border: 1.6px solid #6b778c; border-radius: 7px; padding: 4px 9px; text-align: center; background: #fff; font-size: 8.6pt; }
.fbox .ft { font-weight: 700; font-size: 9pt; margin-bottom: 1px; }
.fbox small { display: block; color: #5a6477; font-size: 7.8pt; }
.fbox.data { background: #eef3fb; border-color: #2a78d6; }
.fbox.target { background: #f3effc; border-color: #7a5bd6; }
.fbox.score { background: #eef8f3; border-color: #1a9e75; }
.farrow { text-align: center; color: #6b778c; font-size: 9pt; line-height: 1.1; }
.floop { border: 2px dashed #eda100; border-radius: 10px; padding: 5px 12px 4px; background: #fffaf0; }
.looplabel { font-weight: 700; text-align: center; color: #9a6a00; font-size: 9pt; margin-bottom: 3px; }
.loopback { text-align: right; color: #9a6a00; font-weight: 700; font-size: 9pt; }
.tsplit, .two, .three { display: flex; gap: 6px; justify-content: center; align-items: center; }
.tsplit div, .two div, .three div { flex: 1; font-size: 8pt; }
.flow { line-height: 1.25; }
.flow .fbox { padding: 4px 10px; font-size: 9pt; }
.flow .tsplit div, .flow .two div, .flow .three div { font-size: 8.6pt; }
.farrow { font-size: 9pt; line-height: 1; }
"""


def build_html() -> str:
    body = "".join([
        cover(), part_a(), strategy1(), strategy2(), strategy3(),
        optimiser_strategy(3, "Risk-parity SIP",
                           "An optimiser chooses the split so that each asset contributes the "
                           "same amount of risk. It re-learns the split every year from the "
                           "previous 10 years.", "Optimiser: risk parity (re-fit yearly)"),
        optimiser_strategy(4, "Max-Sharpe SIP",
                           "An optimiser chooses the split with the highest expected return per "
                           "unit of risk, re-learned every year from the previous 10 years.",
                           "Optimiser: max Sharpe (re-fit yearly)"),
        optimiser_strategy(5, "Optimized SIP (average of 4 and 5)",
                           "The project's proposed strategy: every year take the average of the "
                           "risk-parity and max-Sharpe splits, send each instalment to the jars "
                           "that are below target, and sell only if something drifts more than 5%.",
                           "½ risk parity + ½ max Sharpe (re-fit yearly)"),
        comparison(), flowchart()])
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>SIP Formulas Guide</title>'
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def find_chrome() -> str:
    for c in [os.environ.get("CHROME"), "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              shutil.which("chromium"), shutil.which("chromium-browser"),
              shutil.which("google-chrome"), shutil.which("chrome")]:
        if c and Path(c).exists():
            return c
    found = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if found:
        return str(found[-1])
    raise SystemExit("Chromium/Chrome not found: set the CHROME environment variable.")


def main():
    html = build_html()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "guide.html"
        src.write_text(html, encoding="utf-8")
        if os.environ.get("KEEP_HTML"):
            shutil.copy(src, os.environ["KEEP_HTML"])
        subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                        "--no-pdf-header-footer", f"--print-to-pdf={OUT}", src.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Wrote {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
