"""Regenerate every explainer README from the live code and results.

    python docs/make_readmes.py        (run after run_all.py)

Every formula block has: the formula, what each term means, a worked example from the
first SIP month (Feb 2010) or first SIP year, and a link to the exact line of code.
Numbers are read from the results files and recomputed from the engine, so the text
always matches the code.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sip.data import (NIFTY_DIVIDEND_YIELD, gold_inr_price, liquid_implied_rate,  # noqa: E402
                      load_daily, load_usdinr_daily, month_end, read_returns_table)
from sip.engine import Strategy, _smart_split, contribution_schedule, run_sip  # noqa: E402
from sip.metrics import max_drawdown, sip_xirr  # noqa: E402
from sip.optimize import fixed_weights, max_sharpe, risk_parity  # noqa: E402
from sip.report import AMOUNT, COST_BPS, LOOKBACK, WINDOW_YEARS, rolling_stats  # noqa: E402
from sip.strategies import STRATEGY_FOLDERS, build_strategies  # noqa: E402

ASSETS = ["Nifty", "Gold", "Liquid"]


# --------------------------------------------------------------------------- helpers
def P(v, d=1):
    return f"{v * 100:.{d}f}%"


def S(v, d=2):          # signed percent
    return f"{v * 100:+.{d}f}%"


def M(v, d=0):
    return f"−₹{abs(v):,.{d}f}" if v < 0 else f"₹{v:,.{d}f}"


def N(v, d=2):
    return f"{v:,.{d}f}"


def line_of(rel_file: str, snippet: str) -> int:
    lines = (ROOT / rel_file).read_text(encoding="utf-8").splitlines()
    hits = [i + 1 for i, text in enumerate(lines) if snippet in text]
    if len(hits) != 1:
        raise ValueError(f"{snippet!r} found {len(hits)} times in {rel_file}")
    return hits[0]


def code(rel_file: str, snippet: str, prefix: str) -> str:
    n = line_of(rel_file, snippet)
    text = (ROOT / rel_file).read_text(encoding="utf-8").splitlines()[n - 1].strip()
    return f"[`{rel_file}` line {n}]({prefix}{rel_file}#L{n}): `{text}`"


def formula(title: str, expr: str, terms: list[tuple[str, str]], example: str,
            refs: list[tuple[str, str]], prefix: str) -> str:
    rows = "\n".join(f"| `{t}` | {m} |" for t, m in terms)
    links = "<br>".join(code(f, s, prefix) for f, s in refs)
    return f"""**{title}**

```
{expr}
```

| Term | What it stands for |
|---|---|
{rows}

**Example:** {example}

**Code:** {links}
"""


# --------------------------------------------------------------------------- facts
R = read_returns_table()
STRATS = build_strategies(R)
IDX = R.index[LOOKBACK:]
CONTRIB = contribution_schedule(IDX, AMOUNT)
FIRST = IDX[0]                                   # Feb 2010
WINDOW = R.iloc[:LOOKBACK]                       # Feb 2000 - Jan 2010
COV = WINDOW.cov().values
FEB = R.loc[str(FIRST)]
DAILY = load_daily()
PN, PG, PL = (month_end(DAILY[c]) for c in ASSETS)
FX = month_end(load_usdinr_daily())
GINR = gold_inr_price()
RATE = liquid_implied_rate()
YEARS = len(IDX) / 12


def run(s):
    return run_sip(R, s, CONTRIB, COST_BPS)


RESULTS = {s.name: run(s) for s in STRATS}
LIQUID_SIP = run(Strategy("100% Liquid", fixed_weights(R.index, {"Nifty": 0, "Gold": 0,
                                                                   "Liquid": 1})))


def folder_results(folder):
    d = ROOT / folder / "results"
    m = pd.read_csv(d / "summary.csv", index_col=0)["Value"]
    roll = pd.read_csv(d / f"rolling_{WINDOW_YEARS}y_windows.csv")
    cr = pd.read_csv(d / "crises.csv", index_col=0)["Return"]
    return m, rolling_stats(roll), cr


def first_year(res):
    tw = res.twr.iloc[:12]
    rf = R["Liquid"].loc[tw.index]
    vol = tw.std() * np.sqrt(12)
    return {"twr": tw, "vol": vol, "mean": tw.mean(), "rf_mean": rf.mean(),
            "sharpe": tw.mean() * 12 / vol, "sharpe_liq": (tw - rf).mean() * 12 / vol,
            "mdd": max_drawdown((1 + tw).cumprod()), "worst": max_drawdown(res.total.iloc[:12]),
            "peak_month": ((1 + tw).cumprod()).idxmax(), "V12": res.total.iloc[11]}


def table(d: dict, fmt=lambda v: N(v)) -> str:
    return " / ".join(f"{a} {fmt(d[a])}" for a in ASSETS)


# --------------------------------------------------------------------------- shared blocks
def engine_formulas(s: Strategy, res, prefix: str) -> str:
    """The monthly SIP mechanics used by this strategy, each with a Feb 2010 example."""
    t = s.target.loc[str(FIRST)].values
    buy = t * AMOUNT
    h1 = res.values.iloc[0].values
    start = AMOUNT
    blocks = []
    blocks.append(formula(
        "Instalment",
        "C_t = A × (1 + g)^floor(t / 12)",
        [("C_t", "money invested in month t"), ("A", f"monthly amount = {M(AMOUNT)}"),
         ("g", "yearly step-up (0 in this study)"), ("t", "months since the SIP started")],
        f"Feb 2010 (t = 0): C = {M(AMOUNT)} × (1 + 0)^0 = **{M(AMOUNT)}**.",
        [("sip/engine.py", "amount * (1.0 + step_up) ** years")], prefix))
    if s.contribution == "pro_rata":
        blocks.append(formula(
            "Splitting the instalment (pro-rata)",
            "buy_i = w_i × C_t",
            [("buy_i", "money put into asset i this month"),
             ("w_i", "target weight of asset i"), ("C_t", "this month's instalment")],
            "Feb 2010: " + ", ".join(f"{a} {t[k]:.4f} × {M(AMOUNT)} = **{M(buy[k], 2)}**"
                                     for k, a in enumerate(ASSETS)) + ".",
            [("sip/engine.py", "else w * cash")], prefix))
    else:
        h = h1
        tw2 = s.target.loc[str(IDX[1])].values
        V = h.sum() + AMOUNT
        gap = np.maximum(tw2 * V - h, 0)
        split = _smart_split(h, tw2, AMOUNT)
        blocks.append(formula(
            "Splitting the instalment (smart: fill the gaps first, never sell)",
            "V     = Σ_i h_i + C_t\n"
            "gap_i = max(w_i × V − h_i, 0)\n"
            "need  = Σ_i gap_i\n"
            "buy_i = gap_i / need × C_t              if need ≥ C_t\n"
            "buy_i = gap_i + w_i × (C_t − need)      if need < C_t",
            [("h_i", "money currently held in asset i"), ("V", "portfolio value after adding the instalment"),
             ("w_i", "target weight of asset i"), ("gap_i", "how far asset i is below its target, in rupees"),
             ("need", "total of all gaps"), ("C_t", "this month's instalment"), ("buy_i", "money put into asset i")],
            f"Month 1 (Feb 2010) starts empty, so every gap equals w_i × {M(AMOUNT)}: "
            + ", ".join(f"{a} {M(buy[k], 2)}" for k, a in enumerate(ASSETS))
            + f". Month 2 (Mar 2010): holdings {table(dict(zip(ASSETS, h)), lambda v: M(v, 2))}, "
            f"V = {M(h.sum(), 2)} + {M(AMOUNT)} = {M(V, 2)}; gaps "
            f"{table(dict(zip(ASSETS, gap)), lambda v: M(v, 2))} (need = {M(gap.sum(), 2)}), so "
            f"the instalment buys **{table(dict(zip(ASSETS, split)), lambda v: M(v, 2))}**.",
            [("sip/engine.py", "total = holdings.sum() + cash"),
             ("sip/engine.py", "gap = np.maximum(target * total - holdings, 0.0)"),
             ("sip/engine.py", "return gap / need * cash"),
             ("sip/engine.py", "return gap + target * (cash - need)")], prefix))
    if s.rebalance == "calendar":
        reb = res.sold[res.sold > 0]
        m0 = reb.index[0]
        i = IDX.get_loc(m0)
        hp = res.values.iloc[i - 1].values
        t0 = s.target.loc[str(m0)].values
        h2 = hp + t0 * AMOUNT
        trade = t0 * h2.sum() - h2
        blocks.append(formula(
            "Rebalancing (every 12 months)",
            "every 12th month:  trade_i = w_i × Σ_j h_j − h_i\n"
            "(trade_i > 0 → buy, trade_i < 0 → sell)",
            [("trade_i", "rupees bought (+) or sold (−) of asset i"), ("w_i", "target weight"),
             ("h_i", "holding of asset i after this month's instalment"), ("Σ_j h_j", "total portfolio value")],
            f"First rebalance {m0}: after the instalment the split was "
            f"{table(dict(zip(ASSETS, h2 / h2.sum())), P)} of {M(h2.sum())}, so "
            f"**{table(dict(zip(ASSETS, trade)), lambda v: M(v))}** (sell Nifty and Gold, buy "
            f"Liquid) brings it back to 60 / 20 / 20. {len(reb)} rebalances in {len(IDX)} months.",
            [("sip/engine.py", "months_since_rebal >= strategy.rebalance_every"),
             ("sip/engine.py", "trade = w * h.sum() - h")], prefix))
    elif s.rebalance == "band":
        n_reb = int((res.sold > 0).sum())
        blocks.append(formula(
            "Rebalancing (only when the drift is too big)",
            "drift = max_i | h_i / Σ_j h_j − w_i |\n"
            "if drift > 5%:  trade_i = w_i × Σ_j h_j − h_i",
            [("drift", "largest gap between an asset's actual share and its target"),
             ("h_i", "holding of asset i"), ("w_i", "target weight"), ("5%", "the tolerance band"),
             ("trade_i", "rupees bought (+) or sold (−) of asset i")],
            f"After month 1 the actual split was {table(dict(zip(ASSETS, h1 / h1.sum())), P)} "
            f"against a target of {table(dict(zip(ASSETS, t)), P)}: drift "
            f"{P(np.abs(h1 / h1.sum() - t).max(), 2)}, well under 5%, so nothing is sold. "
            f"Over the whole SIP this rule fired **{n_reb} times** (the smart instalments kept the "
            "split on target).",
            [("sip/engine.py", "do_rebal = np.abs(h / h.sum() - w).max() > strategy.band"),
             ("sip/engine.py", "trade = w * h.sum() - h")], prefix))
    blocks.append(formula(
        "Trading cost",
        "cost_t = (Σ bought + Σ sold) × 0.10%",
        [("cost_t", "rupees lost to costs this month"), ("Σ bought", "all purchases this month"),
         ("Σ sold", "all sales this month"), ("0.10%", f"{COST_BPS} basis points per rupee traded")],
        f"Feb 2010: ({M(AMOUNT)} + ₹0) × 0.001 = **₹10**, taken from each asset in proportion, "
        f"leaving {table(dict(zip(ASSETS, buy * (1 - 0.001))), lambda v: M(v, 2))}.",
        [("sip/engine.py", "costs[t] = turnover * cost_rate"),
         ("sip/engine.py", "h = h * (1.0 - costs[t] / start_value)")], prefix))
    blocks.append(formula(
        "Market move",
        "h_i ← h_i × (1 + r_i,t)",
        [("h_i", "rupees held in asset i"), ("r_i,t", "asset i's return this month (from `00_raw_data/`)")],
        "Feb 2010 returns: " + ", ".join(f"{a} {S(FEB[a])}" for a in ASSETS) + ". So "
        + ", ".join(f"{a} {M(buy[k] * 0.999, 2)} × {1 + FEB[a]:.4f} = **{M(h1[k], 2)}**"
                    for k, a in enumerate(ASSETS) if buy[k] > 0)
        + f"; portfolio **{M(h1.sum(), 2)}**.",
        [("sip/engine.py", "h = h * (1.0 + rets[t])")], prefix))
    blocks.append(formula(
        "Monthly return of the strategy (time-weighted)",
        "TWR_t = V_end,t / V_start,t − 1",
        [("TWR_t", "the strategy's return in month t, ignoring the new money"),
         ("V_end,t", "value at the end of the month"),
         ("V_start,t", "value right after the instalment, before costs")],
        f"Feb 2010: {M(h1.sum(), 2)} / {M(start)} − 1 = **{S(h1.sum() / start - 1)}**.",
        [("sip/engine.py", "twr[t] = h.sum() / start_value - 1.0")], prefix))
    return "\n".join(blocks)


def scoring_formulas(res, prefix: str) -> str:
    fy = first_year(res)
    V1 = res.total.iloc[0]
    tw = fy["twr"]
    sold = res.sold.sum()
    return "\n".join([
        formula(
            "XIRR (the yearly return earned on your SIP money)",
            "Σ_k CF_k / (1 + XIRR)^(t_k) = 0",
            [("CF_k", "cash flow k: every instalment is negative (money in), the final value positive"),
             ("t_k", "time of cash flow k in years (0, 1/12, 2/12, …)"),
             ("XIRR", "the one yearly rate that makes all cash flows balance")],
            f"If the SIP stopped after month 1: −{M(AMOUNT)} at t = 0 and +{M(V1, 2)} at t = 1/12, "
            f"so XIRR = ({N(V1, 2)} / {N(AMOUNT)})^12 − 1 = **{P((V1 / AMOUNT) ** 12 - 1, 2)}**. "
            f"Over all {len(IDX)} instalments it is **{P(sip_xirr(res), 2)}**.",
            [("sip/metrics.py", "return np.sum(cashflows / (1.0 + r) ** years)"),
             ("sip/metrics.py", "cfs = np.append(-res.contributions.values, res.total.iloc[-1])")], prefix),
        formula(
            "Volatility (how bumpy the ride is)",
            "σ = std(TWR_1 … TWR_N) × √12",
            [("σ", "yearly volatility"), ("TWR_t", "monthly returns of the strategy"),
             ("√12", "turns a monthly spread into a yearly one")],
            f"First 12 months (Feb 2010 – Jan 2011): std of the 12 monthly returns "
            f"= {P(tw.std(), 3)} × 3.464 = **{P(fy['vol'], 2)}**.",
            [("sip/metrics.py", "ann_vol = r.std() * np.sqrt(MONTHS)")], prefix),
        formula(
            "Sharpe ratio (return per unit of bumpiness, against 0%)",
            "Sharpe = 12 × mean(TWR_t) / σ",
            [("mean(TWR_t)", "average monthly return"), ("12 ×", "turns it into a yearly return"),
             ("σ", "yearly volatility (above)")],
            f"First 12 months: 12 × {P(fy['mean'], 3)} / {P(fy['vol'], 2)} = **{fy['sharpe']:.2f}**.",
            [("sip/metrics.py", '"Sharpe": excess.mean() * MONTHS / ann_vol,')], prefix),
        formula(
            "Sharpe vs Liquid (return above the T-bill rate, per unit of bumpiness)",
            "Sharpe_vs_Liquid = 12 × mean(TWR_t − r_Liquid,t) / σ",
            [("r_Liquid,t", "the Liquid fund's return that month (≈ 91-day T-bill)"),
             ("TWR_t − r_Liquid,t", "what the strategy earned above simply holding Liquid"),
             ("σ", "yearly volatility of the strategy")],
            f"First 12 months: 12 × ({P(fy['mean'], 3)} − {P(fy['rf_mean'], 3)}) / {P(fy['vol'], 2)} "
            f"= **{fy['sharpe_liq']:.2f}**. This is the fair comparison when a near-cash asset is "
            "available (see `07_comparison/`).",
            [("sip/metrics.py", 'out["Sharpe vs Liquid"] = excess_vs_rf.mean() * MONTHS / ann_vol')], prefix),
        formula(
            "Max drawdown (worst fall of the strategy from a previous peak)",
            "G_t = Π_{s≤t} (1 + TWR_s)          MDD = min_t ( G_t / max_{s≤t} G_s − 1 )",
            [("G_t", "growth of ₹1 invested in the strategy"), ("max_{s≤t} G_s", "highest value so far"),
             ("MDD", "the deepest percentage fall from a peak")],
            f"First 12 months: deepest fall **{P(fy['mdd'], 2)}**. Whole SIP: see results below.",
            [("sip/metrics.py", "return float((series / peak - 1.0).min())")], prefix),
        formula(
            "Worst fall in the account (what you would actually have seen)",
            "Worst fall = min_t ( V_t / max_{s≤t} V_s − 1 )",
            [("V_t", "account value in rupees at the end of month t (includes new instalments)")],
            f"First 12 months: **{P(fy['worst'], 2)}** (new instalments hide small dips; "
            f"the account ended Jan 2011 at {M(fy['V12'])} on ₹1,20,000 invested).",
            [("sip/metrics.py", '"Worst wealth drop": max_drawdown(res.total),')], prefix),
        formula(
            "Selling per year (a proxy for tax events)",
            "Sell turnover = Σ_t sold_t / mean(V_t) / years",
            [("sold_t", "rupees sold in month t"), ("mean(V_t)", "average account value"),
             ("years", f"length of the SIP = {len(IDX)} / 12 = {YEARS:.2f}")],
            f"Whole SIP: {M(sold)} sold / {M(res.total.mean())} average / {YEARS:.2f} years "
            f"= **{P(sold / res.total.mean() / YEARS, 2)}** a year.",
            [("sip/metrics.py", '"Annual sell turnover": res.sold.sum() / res.total.mean() / (len(r) / MONTHS),')],
            prefix),
    ])


def results_block(folder: str) -> str:
    m, roll, cr = folder_results(folder)
    crisis_rows = "\n".join(f"| {k} | {P(v)} |" for k, v in cr.items())
    return f"""## Results

**Setup (identical for all six strategies):** {M(AMOUNT)} on the 1st of every month from
**Feb 2010 to Dec 2019** ({len(IDX)} instalments, **{M(len(IDX) * AMOUNT)} invested**),
0.1% cost on every trade, rupee returns from `00_raw_data/`.

| Measure | Value | What it means |
|---|---|---|
| Final value | **{M(m['Final value'])}** | What {M(len(IDX) * AMOUNT)} grew into ({m['Wealth multiple']:.2f}×) |
| XIRR | **{P(m['XIRR'])}** | Yearly return earned on your SIP money |
| Volatility | {P(m['Volatility'])} | How bumpy the ride was (yearly) |
| Sharpe (vs 0%) | {m['Sharpe']:.2f} | Return per unit of bumpiness |
| **Sharpe vs Liquid** | **{m['Sharpe vs Liquid']:.2f}** | Return *above the T-bill rate* per unit of bumpiness (the fair one) |
| Max drawdown | {P(m['Max drawdown'])} | Worst fall of the strategy itself |
| Worst fall in account | {P(m['Worst wealth drop'])} | Biggest drop in rupees you would have seen |
| Selling per year | {P(m['Annual sell turnover'])} | Share of the portfolio sold yearly |

For reference, a SIP kept **100% in Liquid** earned an XIRR of **{P(sip_xirr(LIQUID_SIP))}**.

**Every possible {WINDOW_YEARS}-year SIP** ({int(roll['Windows'])} start dates from Feb 2010; only
{WINDOW_YEARS}-year windows fit in the 10-year SIP period):

| Median XIRR | Worst XIRR | Best XIRR | % that lost money | Typical worst fall | Worst fall (any) |
|---|---|---|---|---|---|
| {P(roll['Median XIRR'])} | {P(roll['Worst XIRR'])} | {P(roll['Best XIRR'])} | {P(roll['% windows losing money'])} | {P(roll['Median worst drop'])} | {P(roll['Worst drop (any window)'])} |

**Through Indian market stress periods** (return of the strategy over each period):

| Period | Return |
|---|---|
{crisis_rows}

### Charts

![Portfolio value vs amount invested](results/value.png)

![How the money is split over time](results/allocation.png)

![Fall from previous peak](results/drawdown.png)
"""


FILES = """## Files in this folder

| File | What it is |
|---|---|
| `strategy.py` | **The rule, in code.** Run it to regenerate `results/` |
| `results/summary.md` | All results on one page (also `summary.csv`) |
| `results/monthly.csv` | Month by month: instalment, rupees in each asset, target and actual split, bought/sold, costs |
| `results/rolling_{w}y_windows.csv` | XIRR and worst fall of every {w}-year SIP |
| `results/crises.csv` | Return in each stress period |
| `results/*.png` | The three charts above |

## How to run

```bash
python {folder}/strategy.py
```

It reads the prepared returns table in `00_raw_data/`, runs the SIP month by month with the
shared engine in `sip/` (identical for all six strategies) and rewrites `results/`.
"""


# --------------------------------------------------------------------------- strategy texts
def target_formulas(key: str, s: Strategy, prefix: str) -> str:
    t = s.target.loc[str(FIRST)].values
    folder = STRATEGY_FOLDERS[key]
    if key in (0, 1, 2):
        w = {0: "100% / 0% / 0%", 1: "33.3% / 33.3% / 33.3%", 2: "60% / 20% / 20%"}[key]
        return formula(
            "Target weights (fixed)",
            "w_t = (w_Nifty, w_Gold, w_Liquid) = " + w + "   for every month t",
            [("w_t", "the split the strategy aims for in month t"),
             ("w_Nifty, w_Gold, w_Liquid", "shares of the portfolio for each asset (they add to 100%)")],
            f"Feb 2010 (and every other month): {table(dict(zip(ASSETS, t)), P)}.",
            [(f"{folder}/strategy.py", "WEIGHTS = {"),
             (f"{folder}/strategy.py", "target = fixed_weights(returns.index, WEIGHTS)"),
             ("sip/optimize.py", "return pd.DataFrame([weights] * len(index), index=index)")], prefix)
    mu, mu_m = WINDOW.mean() * 12, WINDOW.mean()
    vol = WINDOW.std() * np.sqrt(12)
    est = formula(
        "Estimates from the past 120 months only (no look-ahead)",
        "μ_i  = (1/120) × Σ_{s=t−120}^{t−1} r_i,s\n"
        "Σ_ij = (1/119) × Σ_s (r_i,s − μ_i)(r_j,s − μ_j)",
        [("μ_i", "average monthly return of asset i over the last 120 months"),
         ("Σ_ij", "covariance of assets i and j (Σ_ii = variance; √(12·Σ_ii) = yearly volatility)"),
         ("r_i,s", "return of asset i in month s"), ("t", "the month being decided (re-fitted every 12 months)")],
        f"For Feb 2010 the window is Feb 2000 – Jan 2010. Average return per year (12 × μ): "
        f"{table(mu.to_dict(), P)}; yearly volatility: {table(vol.to_dict(), P)}. "
        "Liquid barely moves (volatility under 0.5%), which is what drives the result below.",
        [("sip/optimize.py", "current = fn(rets.iloc[i - lookback:i], lo=lo, hi=hi)"),
         ("sip/optimize.py", "return max_sharpe_mu(rets.mean().values - rf / MONTHS, rets.cov().values, lo, hi)")],
        prefix)
    cons = formula(
        "Constraints (both optimisers)",
        "Σ_i w_i = 1        0.10 ≤ w_i ≤ 0.70",
        [("w_i", "weight of asset i"), ("0.10 / 0.70", "every asset gets at least 10% and at most 70%")],
        "Without these limits the optimisers would put almost everything in Liquid: risk parity "
        f"{table(dict(zip(ASSETS, risk_parity(WINDOW, 0, 1))), P)}, max Sharpe "
        f"{table(dict(zip(ASSETS, max_sharpe(WINDOW, 0, 1))), P)} (Feb 2010). The 70% cap is what "
        "keeps any Nifty and Gold in the portfolio.",
        [("sip/optimize.py", "bounds=[(lo, hi)] * n"),
         ("sip/optimize.py", 'constraints=({"type": "eq", "fun": lambda w: w.sum() - 1.0},),')], prefix)
    rp_w = risk_parity(WINDOW, 0.10, 0.70)
    rc = rp_w * (COV @ rp_w)
    rp = formula(
        "Risk parity",
        "RC_i = w_i × (Σ w)_i          minimise  Σ_i (RC_i − mean(RC))²",
        [("RC_i", "risk contribution of asset i (its share of portfolio variance)"),
         ("(Σ w)_i", "row i of the covariance matrix times the weights"),
         ("mean(RC)", "the average contribution; the goal is to make all RC_i equal")],
        f"Feb 2010: weights {table(dict(zip(ASSETS, rp_w)), P)}. Liquid is capped at 70%, so the risk "
        f"shares cannot be made equal: Nifty {P(rc[0] / rc.sum())}, Gold {P(rc[1] / rc.sum())}, "
        f"Liquid {P(rc[2] / rc.sum())} (Liquid adds almost no risk, and it is slightly negatively "
        "correlated with Nifty).",
        [("sip/optimize.py", "rc = w * (cov @ w)"),
         ("sip/optimize.py", "return ((rc - rc.mean()) ** 2).sum() * 1e8")], prefix)
    ms_w = max_sharpe(WINDOW, 0.10, 0.70)
    port = lambda w: (w @ mu_m.values * 12, np.sqrt(w @ COV @ w * 12))  # noqa: E731
    pm, pv = port(ms_w)
    ms = formula(
        "Max Sharpe",
        "maximise  (w · μ) / √(wᵀ Σ w)",
        [("w · μ", "expected monthly return of the portfolio"),
         ("√(wᵀ Σ w)", "monthly volatility of the portfolio"),
         ("ratio", "return per unit of risk, measured against 0% (no risk-free rate subtracted)")],
        f"Feb 2010: weights {table(dict(zip(ASSETS, ms_w)), P)} (Nifty at its 10% floor, Liquid at its "
        f"70% cap): expected {P(pm)} a year with {P(pv)} volatility, ratio {pm / pv:.2f}. Because the "
        "ratio is measured against 0%, Liquid's steady ~6% with almost no volatility looks "
        "extremely attractive.",
        [("sip/optimize.py", "return _solve(lambda w: -(w @ mu) / np.sqrt(w @ cov @ w), len(mu), lo, hi)")],
        prefix)
    blend = formula(
        "Optimized target (average of the two)",
        "w = ½ × w_RiskParity + ½ × w_MaxSharpe",
        [("w_RiskParity", "weights from strategy 4"), ("w_MaxSharpe", "weights from strategy 5")],
        f"Feb 2010: ½ × ({table(dict(zip(ASSETS, rp_w)), P)}) + ½ × ({table(dict(zip(ASSETS, ms_w)), P)}) "
        f"= **{table(dict(zip(ASSETS, (rp_w + ms_w) / 2)), P)}**.",
        [("06_optimized_sip/strategy.py", "target = 0.5 * risk_parity + 0.5 * max_sharpe")], prefix)
    body = {3: [est, rp, cons], 4: [est, ms, cons], 5: [est, rp, ms, cons, blend]}[key]
    return "\n".join(body)


STRATEGY_TEXT = [
    dict(title="Equity SIP (100% Nifty 50)",
         idea="Put the whole instalment into the Nifty 50 every month. This is the usual SIP, so it's the **main benchmark**.",
         rule="1. Every month, invest the full ₹10,000 in **Nifty 50** (dividends included).\n2. Never sell, never rebalance.",
         behaviour="The allocation chart is one block: 100% Nifty for ten years. All the risk comes from one asset.",
         good="- **Highest return** of the six (XIRR {xirr}).\n- Simplest rule; nothing is ever sold.",
         bad="- **Biggest falls**: the strategy fell {mdd} from its peak (during 2011), and {c2015} in the "
             "2015-16 sell-off.\n"
             "- Earned about {extra} a year more than a 100% Liquid SIP ({liq}), but with {vol} volatility "
             "against about 0.5% for Liquid."),
    dict(title="Equal-weight SIP (⅓ each)",
         idea="Split every instalment equally between Nifty, gold and liquid and never touch it.",
         rule="1. Every month, invest **₹3,333 in each** of Nifty, Gold and Liquid.\n2. Never sell, never rebalance.",
         behaviour="New money always goes in ⅓ each and nothing is sold, so the split **drifts** toward whatever "
                   "grew fastest. By Dec 2019 it was {end}. The drift was mild here because Liquid grows "
                   "steadily and Nifty had a modest decade.",
         good="- Small falls (worst account fall {worst}) for a respectable {xirr} a year.\n- No selling at all.",
         bad="- The split is uncontrolled and drifts over time.\n- Sharpe vs Liquid ({shl}) slightly below 100% Nifty and 60/20/20."),
    dict(title="60/20/20 SIP (Nifty / Gold / Liquid, reset yearly)",
         idea="The classic fixed mix: 60% equity for growth, 20% gold and 20% liquid for protection, reset to exactly 60/20/20 once a year.",
         rule="1. Every month, invest **₹6,000 in Nifty, ₹2,000 in Gold, ₹2,000 in Liquid**.\n"
              "2. Every 12 months, sell what has grown above its share and buy what has fallen below it.",
         behaviour="The allocation chart shows the split drifting during each year and snapping back to 60/20/20 "
                   "every January ({nreb} rebalances).",
         good="- **Best Sharpe vs Liquid of all six ({shl})**: the most return above the T-bill rate per unit of risk.\n"
              "- Second-highest return ({xirr}), with a worst account fall of only {worst}.",
         bad="- Still equity-heavy: it fell {c2011} in 2011 and {c2015} in 2015-16.\n"
             "- Sells every year (about {turn} of the portfolio), so there are tax events."),
    dict(title="Risk-parity SIP",
         idea="Let a formula decide the split so that each asset contributes equal risk. Calm assets get more money.",
         rule="1. Every 12 months, look at **only the previous 120 months** of returns.\n"
              "2. Choose weights so every asset contributes equal risk, with each asset between **10% and 70%**.\n"
              "3. Each month, send the instalment to the assets **below target** first (no selling).\n"
              "4. Only rebalance if an asset drifts **more than 5 points** from target.",
         behaviour="Liquid is so calm that risk parity always wants more of it than allowed: the target sat at the "
                   "**70% Liquid cap every year** ({years}). In practice this is a ~70% cash portfolio with "
                   "10-15% each in Nifty and Gold.",
         good="- Tiny falls (worst account fall {worst}) and positive returns in every stress period.\n"
              "- No selling needed at all over ten years.",
         bad="- Earned {xirr}, only about {vsliq} a year more than a 100% Liquid SIP ({liq}).\n"
             "- Its high Sharpe (vs 0%) is an artefact of holding cash; measured against Liquid it is {shl}, "
             "below 60/20/20 ({shl3})."),
    dict(title="Max-Sharpe SIP",
         idea="Let a formula choose the split with the most return per unit of risk over the last 10 years (Markowitz).",
         rule="1. Every 12 months, look at **only the previous 120 months**.\n"
              "2. Estimate average returns (μ) and covariance (Σ); choose weights that maximise return ÷ risk, "
              "each between **10% and 70%**.\n"
              "3. Each month, send the instalment to the assets **below target** first.\n"
              "4. Only rebalance if an asset drifts **more than 5 points** from target.",
         behaviour="Measured against 0%, Liquid's steady return with almost no volatility dominates, so the "
                   "target pinned Liquid at the 70% cap and Nifty near its 10% floor ({years}).",
         good="- Tiny falls (worst account fall {worst}); positive in every stress period.",
         bad="- Lowest Sharpe vs Liquid of the six ({shl}) and lowest XIRR ({xirr}).\n"
             "- Its answer is driven by the choice of 0% as the benchmark rate (see `07_comparison/`)."),
    dict(title="Optimized SIP (½ risk parity + ½ max Sharpe)",
         idea="Average the careful optimiser (risk parity, strategy 4) and the ambitious one (max Sharpe, strategy 5).",
         rule="1. Every 12 months, from **only the previous 120 months**, compute both the risk-parity and the "
              "max-Sharpe weights (each within 10–70%).\n"
              "2. **Target = average of the two.**\n"
              "3. Each month, send the instalment to the assets **below target** first.\n"
              "4. Only rebalance if an asset drifts **more than 5 points** from target.",
         behaviour="Both optimisers pinned Liquid at 70%, so their average does too ({years}). The blend only "
                   "changes how the remaining 30% is split between Nifty and Gold.",
         good="- Tiny falls (worst account fall {worst}); positive in every stress period.\n"
              "- No selling needed over ten years.",
         bad="- XIRR {xirr}, about {vsliq} a year above a 100% Liquid SIP ({liq}).\n"
             "- Sharpe vs Liquid {shl}, below 60/20/20 ({shl3}) and 100% Nifty ({shl1}). On this Indian data "
             "the optimisation does not add value because the safe asset is cash-like."),
]


def strategy_readme(key: int) -> str:
    s = STRATS[key]
    folder = STRATEGY_FOLDERS[key]
    res = RESULTS[s.name]
    m, roll, cr = folder_results(folder)
    m3 = folder_results(STRATEGY_FOLDERS[2])[0]
    m1 = folder_results(STRATEGY_FOLDERS[0])[0]
    liq = sip_xirr(LIQUID_SIP)
    yrs = ", ".join(f"{str(p)[:4]}: " + "/".join(f"{v:.0%}" for v in s.target.loc[p].values)
                    for p in IDX[::12][:3]) + " …"
    fmt = dict(xirr=P(m["XIRR"]), mdd=P(m["Max drawdown"]), vol=P(m["Volatility"]), worst=P(m["Worst wealth drop"]),
               shl=f"{m['Sharpe vs Liquid']:.2f}", shl3=f"{m3['Sharpe vs Liquid']:.2f}",
               shl1=f"{m1['Sharpe vs Liquid']:.2f}", turn=P(m["Annual sell turnover"]),
               nreb=int((res.sold > 0).sum()), liq=P(liq), vsliq=P(m["XIRR"] - liq),
               extra=P(m["XIRR"] - liq), years=yrs,
               end=table(res.weights.iloc[-1].to_dict(), P),
               c2011=P(cr.iloc[0]), c2015=P(cr.iloc[2]))
    tx = STRATEGY_TEXT[key]
    prefix = "../"
    return f"""# Strategy {key + 1}: {tx['title']}

> **Idea:** {tx['idea']}

## The rule

{tx['rule']}

## The formulas this strategy uses

Every example uses the first SIP month, **Feb 2010**, when the month's returns were
{', '.join(f'{a} {S(FEB[a])}' for a in ASSETS)} (built in `00_raw_data/`).

### 1. Deciding the split

{target_formulas(key, s, prefix)}
### 2. Investing each month (the shared SIP engine)

{engine_formulas(s, res, prefix)}
## How it behaves over time

{tx['behaviour'].format(**fmt)}

{results_block(folder)}
### How each score is calculated

{scoring_formulas(res, prefix)}
## Strengths and weaknesses

**Strengths**
{tx['good'].format(**fmt)}

**Weaknesses**
{tx['bad'].format(**fmt)}

{FILES.format(folder=folder, w=WINDOW_YEARS)}"""


# --------------------------------------------------------------------------- 00_raw_data
def data_readme() -> str:
    prefix = "../"
    p0, p1 = PN[str(IDX[0] - 1)], PN[str(FIRST)]
    g0, g1 = PG[str(IDX[0] - 1)], PG[str(FIRST)]
    f0, f1 = FX[str(IDX[0] - 1)], FX[str(FIRST)]
    gi0, gi1 = GINR[str(IDX[0] - 1)], GINR[str(FIRST)]
    l0, l1 = PL[str(IDX[0] - 1)], PL[str(FIRST)]
    corr = WINDOW.corr()
    y_feb = RATE.loc["2010-02-01"]
    ann = (1 + R).prod() ** (12 / len(R)) - 1
    vol = R.std() * np.sqrt(12)
    return f"""# 00 · Raw Data: From Daily Prices to Monthly Rupee Returns

> **What this folder does:** it turns the daily market file (Nifty 50, gold, liquid fund,
> 2000–2019) into **one table of monthly rupee returns**. That table is the **only input**
> all six strategies use, so they are compared on exactly the same data.

```
raw/final_market_data_2000_2019.csv  ─┐
raw/usdinr_daily_fred.csv            ─┴─►  build_returns.py  ─►  monthly_returns.csv  (239 months × 3)
                                                              └─►  monthly_prices.csv  (month-end values used)
```

## 1. The raw files (`raw/`)

| File | Source | Columns | Notes |
|---|---|---|---|
| `final_market_data_2000_2019.csv` | Your compiled data (daily, every calendar day 2000-01-01 to 2019-12-31) | `Nifty`, `Gold`, `Liquid` | Weekends/holidays repeat the last value |
| `usdinr_daily_fred.csv` | FRED series DEXINUS (US Federal Reserve), via [datasets/exchange-rates](https://github.com/datasets/exchange-rates) | `USDINR` (rupees per US dollar) | Blank on US holidays; the last available rate is used |

**What each column really is (checked, see section 4):**

| Column | What it is | Unit |
|---|---|---|
| `Nifty` | Nifty 50 **price** index (NSE closing values). Does **not** include dividends | index points |
| `Gold` | International gold price | **US dollars** per troy ounce, not rupees |
| `Liquid` | A liquid-fund index that grows every day by the 91-day T-bill yield ÷ 365 | index (100 on 1 Jan 2000) |

## 2. The formulas: how each monthly return is built

The SIP invests once a month, so each series is sampled at **month end**, then turned into
a return (the growth of ₹1 over the month).

{formula(
    "Month-end value",
    "X_month = last available daily value of X in that calendar month",
    [("X", "any daily series (Nifty, Gold, Liquid, USD/INR)"), ("X_month", "the value used for that month")],
    f"Feb 2010: Nifty {N(p1)}, Gold ${N(g1, 1)}, USD/INR {N(f1)}, Liquid {N(l1, 4)} (Jan 2010: "
    f"{N(p0)}, ${N(g0, 1)}, {N(f0)}, {N(l0, 4)}).",
    [("sip/data.py", 'out = series.dropna().resample("ME").last()')], prefix)}
{formula(
    "Nifty 50 total return (price + dividends)",
    "r_Nifty,t = P_t / P_(t−1) − 1 + dy / 12",
    [("P_t", "Nifty 50 month-end close this month"), ("P_(t−1)", "Nifty 50 month-end close last month"),
     ("dy", f"Nifty dividend yield per year = {P(NIFTY_DIVIDEND_YIELD)} (assumption, see below)"),
     ("dy / 12", "one month of dividends")],
    f"Feb 2010: {N(p1)} / {N(p0)} − 1 + {NIFTY_DIVIDEND_YIELD} / 12 = {S(p1 / p0 - 1, 3)} + "
    f"{S(NIFTY_DIVIDEND_YIELD / 12, 3)} = **{S(FEB['Nifty'], 3)}**.",
    [("sip/data.py", "ret = price / price.shift(1) - 1 + dividend_yield / 12")], prefix)}
**Why add dividends?** An index fund investor receives the dividends of the 50 companies
(reinvested in the fund). The price index leaves them out, which would understate Nifty by
about 1–2% a year. NSE publishes a separate Total Return Index, but no source reachable from
this project had its history, so a constant **{P(NIFTY_DIVIDEND_YIELD)}** a year is added. The
Nifty 50 dividend yield has historically been **1–2%** (1.35% in the May 2026 NSE factsheet;
[Bajaj AMC](https://www.bajajamc.com/knowledge-centre/nifty-50-dividend-yield)). It is one
constant in `sip/data.py` (`NIFTY_DIVIDEND_YIELD`) and easy to change.

{formula(
    "Gold in rupees",
    "G_INR,t = G_USD,t × FX_t",
    [("G_USD,t", "gold price in US dollars per ounce at month end"),
     ("FX_t", "rupees per US dollar at month end"), ("G_INR,t", "gold price in rupees per ounce")],
    f"Feb 2010: ${N(g1, 1)} × {N(f1)} = **₹{N(gi1)}** per ounce (Jan 2010: ${N(g0, 1)} × {N(f0)} = ₹{N(gi0)}).",
    [("sip/data.py", 'return (gold_usd * fx).rename("Gold")')], prefix)}
{formula(
    "Gold return (for an Indian investor)",
    "r_Gold,t = G_INR,t / G_INR,(t−1) − 1   =   (1 + r_USD,t) × FX_t / FX_(t−1) − 1",
    [("r_Gold,t", "gold's return in rupees"), ("r_USD,t", "gold's return in dollars"),
     ("FX_t / FX_(t−1)", "how much the dollar rose against the rupee")],
    f"Feb 2010: ₹{N(gi1)} / ₹{N(gi0)} − 1 = **{S(FEB['Gold'], 3)}**; equivalently "
    f"(1 {S(g1 / g0 - 1, 3)}) × ({N(f1)} / {N(f0)}) − 1.",
    [("sip/data.py", 'return (g / g.shift(1) - 1).rename("Gold")')], prefix)}
**Why convert?** An Indian buys gold in rupees. Over 2000–2019 the rupee fell from about 43.5
to 71.4 per dollar, so rupee gold grew about **2.5% a year faster** than dollar gold. Using
dollar gold for an Indian SIP (as the earlier Gemini version did) understates gold.

{formula(
    "Liquid return",
    "L_d = L_(d−1) × (1 + y_d / 365)        r_Liquid,t = L_t / L_(t−1) − 1",
    [("L_d", "liquid index on day d"), ("y_d", "91-day T-bill yield that applies on day d"),
     ("L_t", "liquid index at month end"), ("r_Liquid,t", "the month's return")],
    f"Feb 2010: the implied yield was {P(y_feb, 2)} a year, so the index grew a little each day; month "
    f"end {N(l1, 4)} / {N(l0, 4)} − 1 = **{S(FEB['Liquid'], 3)}**.",
    [("sip/data.py", 'return (level / level.shift(1) - 1).rename("Liquid")'),
     ("sip/data.py", 'return ((level / level.shift(1) - 1) * 365).rename("Liquid implied rate")')],
    prefix)}
{formula(
    "Correlation (why these three assets)",
    "ρ(i, j) = Cov(r_i, r_j) / (σ_i × σ_j)",
    [("ρ(i, j)", "correlation of assets i and j: +1 move together, 0 unrelated, −1 opposite"),
     ("Cov(r_i, r_j)", "how the two monthly returns move together"), ("σ_i", "volatility of asset i")],
    f"Feb 2000 – Jan 2010 (the first window the optimisers see): Nifty–Gold "
    f"**{corr.loc['Nifty', 'Gold']:.2f}**, Nifty–Liquid **{corr.loc['Nifty', 'Liquid']:.2f}**, "
    f"Gold–Liquid **{corr.loc['Gold', 'Liquid']:.2f}**. All low or negative: when Nifty falls, the "
    "other two usually don't (diversification).",
    [("00_raw_data/build_returns.py", "corr = first_window.corr()")], prefix)}
## 3. The output: `monthly_returns.csv`

**239 months (Feb 2000 – Dec 2019) × 3 assets**, as decimals (0.0093 = 0.93%):

| Month | Nifty | Gold | Liquid |
|---|---|---|---|
| 2010-01 | {R.loc['2010-01', 'Nifty']:.4f} | {R.loc['2010-01', 'Gold']:.4f} | {R.loc['2010-01', 'Liquid']:.4f} |
| **2010-02 (first SIP month)** | **{FEB['Nifty']:.4f}** | **{FEB['Gold']:.4f}** | **{FEB['Liquid']:.4f}** |

| 2000–2019 | Nifty (with dividends) | Gold (₹) | Liquid |
|---|---|---|---|
| Return per year | {P(ann['Nifty'])} | {P(ann['Gold'])} | {P(ann['Liquid'])} |
| Volatility per year | {P(vol['Nifty'])} | {P(vol['Gold'])} | {P(vol['Liquid'])} |

**Why the SIP starts in Feb 2010.** Strategies 4–6 need the previous **120 months** of
returns before they can decide a split. The data starts in Feb 2000, so the first possible
decision is Feb 2010. All six strategies use the same **{len(IDX)} months (Feb 2010 – Dec 2019)**.

| Used for | How |
|---|---|
| Deciding the split (strategies 4–6) | The previous 120 months give μ (average return) and Σ (covariance) |
| Running every SIP (all six) | Each month the holdings grow by (1 + r) |
| All results | XIRR, drawdowns and stress tests come from the SIP values built on these returns |

## 4. Data verification

`python 00_raw_data/verify_data.py` re-runs these checks (it downloads the reference files):

| Check | Reference | Result |
|---|---|---|
| Nifty closes, every trading day | NSE-sourced data 1990–2019 ([Sdaas/nifty-analysis](https://github.com/Sdaas/nifty-analysis)) | 4,812 days, **99.94% identical**. The only 3 differences are special weekend sessions (28 Apr 2012, Muhurat trading 3 Nov 2013 and 7 Nov 2018), none at a month end |
| Nifty closes 2015–2019 | Second NSE download ([abulbasar/data](https://github.com/abulbasar/data)) | 1,233 days, **99.92% identical** (only 7 Nov 2018 differs) |
| Gold (USD) | Monthly gold price series ([datasets/gold-prices](https://github.com/datasets/gold-prices)) | Monthly averages within **0.33%** on average → confirms the column is **USD/oz** |
| USD/INR | FRED DEXINUS | Used directly (it is the reference) |
| Liquid | Implied daily rate × 365 | Steps weekly (like weekly 91-day T-bill auctions): 9.25% (Jan 2000), 3.3% (2009), a spike to 12% in Aug 2013 (rupee crisis), 5–6% in 2019. Consistent with 91-day T-bill history; no downloadable T-bill series was reachable to match it day by day |

## How to rebuild

```bash
python 00_raw_data/build_returns.py     # writes monthly_returns.csv, monthly_prices.csv, correlations_2000_2010.csv
python 00_raw_data/verify_data.py       # optional: re-check against the public sources (needs internet)
```

## Limitations

- **Nifty dividends are a constant {P(NIFTY_DIVIDEND_YIELD)} a year**, not the actual dividends paid.
- **Gold is international gold in rupees.** Indian domestic gold (e.g. Gold BeES) also carries
  import duty, which rose from about 2% to 12.5% during 2012–2019, so domestic gold did slightly
  better than this series.
- **Liquid is an index built from the T-bill yield**, not an actual fund, so it has no fund
  expenses or credit risk.
- **Month-end sampling:** the last calendar day of the month is used; on weekends that is the
  Friday close repeated in the file.
"""


# --------------------------------------------------------------------------- 07 and top README
TRAIN_TEST_EXPR = ("train: pick the fixed mix (10% grid, 66 mixes) with the highest Sharpe vs Liquid on the first half\n"
                   "test:  run every strategy, and that fixed mix, on the unseen second half")

def comparison_readme() -> str:
    d = ROOT / "07_comparison" / "results"
    t = pd.read_csv(d / "summary.csv", index_col=0)
    rs = pd.read_csv(d / "rolling_summary.csv", index_col=0)
    tt = pd.read_csv(d / "train_test.csv", index_col=0)
    cr = pd.read_csv(d / "crisis.csv", index_col=0)
    sens = pd.read_csv(d / "sensitivity.csv")
    md = (d / "results.md").read_text(encoding="utf-8")
    best = md.split("Best fixed mix on train (highest Sharpe vs Liquid): ")[1].split("\n")[0]
    hind = md.split("over the full period (highest Sharpe vs Liquid): ")[1].split("\n")[0]
    liq = sip_xirr(LIQUID_SIP)
    names = list(t.index)
    links = [f"[{n}](../{f})" for n, f in zip(["Equity (100% Nifty)", "Equal-weight ⅓ each", "60/20/20",
                                               "Risk parity", "Max Sharpe", "Optimized (½ + ½)"],
                                              STRATEGY_FOLDERS)]
    rows = "\n".join(
        f"| {k + 1} | {links[k]} | {M(t.loc[n, 'Final value'])} | {P(t.loc[n, 'XIRR'])} | "
        f"{P(t.loc[n, 'Volatility'])} | {t.loc[n, 'Sharpe']:.2f} | **{t.loc[n, 'Sharpe vs Liquid']:.2f}** | "
        f"{P(t.loc[n, 'Max drawdown'])} | {P(t.loc[n, 'Worst wealth drop'])} |" for k, n in enumerate(names))
    rrows = "\n".join(
        f"| {n} | {P(rs.loc[n, 'Median XIRR'])} | {P(rs.loc[n, 'Worst XIRR'])} | {P(rs.loc[n, 'Best XIRR'])} | "
        f"{P(rs.loc[n, 'Median worst drop'])} |" for n in names)
    trows = "\n".join(
        f"| {n} | {P(tt.loc[n, 'XIRR'])} | {tt.loc[n, 'Sharpe vs Liquid']:.2f} | {P(tt.loc[n, 'Worst wealth drop'])} |"
        for n in tt.index)
    crows = "\n".join(f"| {p} | " + " | ".join(P(cr.loc[p, n]) for n in names) + " |" for p in cr.index)
    sx = sens[sens["Execution"] == "band 5%"]
    sens_line = ", ".join(f"{int(r['Look-back (months)'])} months → {P(r['XIRR'])}" for _, r in sx.iterrows())
    prefix = "../"
    best_shl = t["Sharpe vs Liquid"].idxmax()
    return f"""# 07 · Comparison: All Six Strategies Side by Side

> **What this folder does:** loads the six strategies from folders `01_` to `06_`, runs them
> on **identical** data, months, instalments and costs, and adds the tests that only make
> sense side by side. This is where the project's conclusion comes from.

**Setup:** {M(AMOUNT)} on the 1st of every month, **Feb 2010 – Dec 2019** ({len(IDX)} instalments,
{M(len(IDX) * AMOUNT)} invested), 0.1% cost per trade, Nifty 50 / Gold (₹) / Liquid returns from
`00_raw_data/`.

## 1. Full-period results

| # | Strategy | Final value | XIRR | Volatility | Sharpe (vs 0%) | **Sharpe vs Liquid** | Max drawdown | Worst account fall |
|---|---|---|---|---|---|---|---|---|
{rows}

Reference: a SIP kept **100% in Liquid** earned **{P(liq)}**.

![Portfolio value of all six](results/wealth.png)

### Why two Sharpe ratios?

{formula(
    "Sharpe vs Liquid",
    "Sharpe_vs_Liquid = 12 × mean(TWR_t − r_Liquid,t) / σ",
    [("TWR_t", "the strategy's monthly return"), ("r_Liquid,t", "Liquid's return that month (≈ 91-day T-bill)"),
     ("σ", "the strategy's yearly volatility")],
    f"Optimized SIP: Sharpe vs 0% = {t.loc['Optimized SIP', 'Sharpe']:.2f} but Sharpe vs Liquid = "
    f"{t.loc['Optimized SIP', 'Sharpe vs Liquid']:.2f}. Most of its return is simply the T-bill rate earned "
    "by its 70% Liquid holding.",
    [("sip/metrics.py", 'out["Sharpe vs Liquid"] = excess_vs_rf.mean() * MONTHS / ann_vol')], prefix)}
The usual Sharpe ratio subtracts a **risk-free rate**. The original design used 0%, which was
harmless with US bonds (7% volatility). Here **Liquid is almost risk-free** (0.5% volatility),
so measured against 0% anything holding a lot of Liquid looks brilliant (Sharpe ≈ 2.5). That's
also why the optimisers chose the maximum 70% Liquid. Measured against Liquid, the strategies
are close, and **{best_shl}** is the best.

## 2. Every {WINDOW_YEARS}-year SIP ({int(rs.iloc[0]['Windows'])} start dates, Feb 2010 onwards)

Only {WINDOW_YEARS}-year windows fit inside the 10-year SIP period (the US version used 10-year windows over 43 years).

{formula(
    "Rolling windows",
    "for every start month s:  run a fresh {w}-year SIP from s,  record its XIRR and worst fall".format(w=WINDOW_YEARS),
    [("s", f"each month from Feb 2010 to {IDX[-WINDOW_YEARS * 12]}")],
    f"The first window runs Feb 2010 – Jan 2015; the last {IDX[-WINDOW_YEARS * 12]} – Dec 2019.",
    [("sip/analysis.py", "for i in range(0, len(idx) - n + 1, step):")], prefix)}
| Strategy | Median XIRR | Worst XIRR | Best XIRR | Typical worst fall |
|---|---|---|---|---|
{rrows}

No window lost money for any strategy: 2010–2019 was a steady decade for Indian SIPs.

![Spread of outcomes](results/rolling_xirr.png)

## 3. Optimise once vs re-learn every year (train/test split)

{formula(
    "Train / test",
    TRAIN_TEST_EXPR,
    [("first half", "Feb 2010 – Dec 2014"), ("second half", "Jan 2015 – Dec 2019")],
    f"Best mix on 2010–2014: **{best}**.",
    [("sip/analysis.py", "w_star = best_static(grid, assets)")], prefix)}
| Strategy (Jan 2015 – Dec 2019) | XIRR | Sharpe vs Liquid | Worst account fall |
|---|---|---|---|
{trows}

Here the fixed mix tuned on 2010–2014 did **well** on 2015–2019. That's the opposite of the
US result, where "optimise once" did worst. With the optimisers stuck at 70% Liquid,
re-learning every year did not help on this data.

Best fixed mix with perfect hindsight over the whole period: **{hind}**.

![Return vs worst fall](results/frontier.png)

## 4. Indian market stress periods (strategy return over each period)

| Period | 100% Nifty | ⅓ each | 60/20/20 | Risk parity | Max Sharpe | Optimized |
|---|---|---|---|---|---|---|
{crows}

The gold + Liquid heavy strategies rose in every stress period: gold in rupees jumped when the
rupee fell (2011, 2013), and Liquid never falls.

## 5. Do the Optimized SIP's settings matter? (sensitivity)

With look-backs of {sens_line} (5% band), the result barely changes. Band width and smart vs
pro-rata instalments also make almost no difference. Full table: `results/results.md`.

## 6. Conclusion (Nifty 50 / Gold / Liquid, 2010–2019)

1. **100% Nifty earned the most** ({P(t.loc['Equity SIP', 'XIRR'])} a year) with the biggest falls
   ({P(t.loc['Equity SIP', 'Max drawdown'])} in 2011).
2. **60/20/20 had the best return above the T-bill rate per unit of risk** (Sharpe vs Liquid
   {t.loc['60/20/20 annual rebal', 'Sharpe vs Liquid']:.2f}) and the second-highest return
   ({P(t.loc['60/20/20 annual rebal', 'XIRR'])}).
3. **The optimiser strategies (4–6) became ~70% cash.** Liquid barely moves, so both risk
   parity and max Sharpe (measured against 0%) push it to the 70% cap. They had tiny falls,
   but earned only about {P(t.loc['Optimized SIP', 'XIRR'] - liq)} a year more than a 100% Liquid SIP,
   and their Sharpe vs Liquid ({t.loc['Optimized SIP', 'Sharpe vs Liquid']:.2f}) is below 60/20/20.
4. **The mechanics are identical to the US study; the data changes the answer.** With US
   bonds (a risky asset) the optimisers gave the best risk-adjusted result. With a cash-like
   Liquid fund, measuring risk against 0% makes them simply hold cash.
5. **What would fix it (not applied, to keep the mechanics identical):** treat Liquid as the
   risk-free rate inside the optimiser (maximise Sharpe *vs Liquid*), or lower the cap on Liquid.

## Files and how to run

```bash
python 07_comparison/run.py
```

`results/results.md` has every table (including sensitivity and the hindsight best mix); the
CSVs hold the raw numbers; the PNGs are the charts.
"""


def top_readme() -> str:
    t = pd.read_csv(ROOT / "07_comparison" / "results" / "summary.csv", index_col=0)
    names = list(t.index)
    labels = ["1 · 100% Nifty", "2 · ⅓ each", "3 · 60/20/20", "4 · Risk parity", "5 · Max Sharpe",
              "6 · Optimized"]
    rows = "\n".join(
        f"| {labels[k]} | {M(t.loc[n, 'Final value'])} | {P(t.loc[n, 'XIRR'])} | "
        f"{P(t.loc[n, 'Max drawdown'])} | {t.loc[n, 'Sharpe vs Liquid']:.2f} |" for k, n in enumerate(names))
    return f"""# A Simple Optimized SIP Strategy for Multi-Asset Allocation

Degree project (BTP). A **SIP** (Systematic Investment Plan) invests a fixed amount every
month. This project asks: **how should each month's ₹10,000 be split between Nifty 50, gold and
a liquid fund?** It tests six ways of splitting it on Indian market data (2000–2019; SIPs run
**Feb 2010 – Dec 2019**) and compares them fairly.

## How the repository is organised

Read the folders in order. Each strategy folder is self-contained: **explanation at the top
of its README (every formula with its terms, a Feb 2010 example and the line of code), the
rule in `strategy.py`, and its own `results/`.**

| Folder | What's inside |
|---|---|
| [`00_raw_data/`](00_raw_data) | Daily Nifty / Gold / Liquid data + USD/INR, how they become monthly rupee returns, and the data verification. **Every strategy uses this one table.** |
| [`01_equity_sip/`](01_equity_sip) | Strategy 1: **100% Nifty 50**, the usual SIP (benchmark) |
| [`02_equal_weight_sip/`](02_equal_weight_sip) | Strategy 2: **⅓ each** in Nifty, gold and liquid, never rebalanced |
| [`03_fixed_60_20_20_sip/`](03_fixed_60_20_20_sip) | Strategy 3: **60/20/20** Nifty/Gold/Liquid, reset once a year |
| [`04_risk_parity_sip/`](04_risk_parity_sip) | Strategy 4: **risk parity**, an optimiser that gives each asset equal risk |
| [`05_max_sharpe_sip/`](05_max_sharpe_sip) | Strategy 5: **max Sharpe**, an optimiser that maximises return per unit of risk |
| [`06_optimized_sip/`](06_optimized_sip) | Strategy 6: **Optimized SIP**, the average of 4 and 5 |
| [`07_comparison/`](07_comparison) | **All six side by side**, robustness tests and the conclusion |
| [`sip/`](sip) | Shared engine used by all six: monthly SIP simulator, optimisers, scoring |
| [`tests/`](tests) | Automated checks (formulas, no look-ahead, data integrity) |
| [`docs/`](docs) | Architecture diagram and the 20-step worked example |
| [`extras/`](extras) | Not part of the main study: the earlier **US-data version** (1973–2026) and the **AI forecasting** extension |

Strategies 4–6 are **optimised but not AI**: every year they recalculate the split from the
**previous 10 years only** (no look-ahead).

## Headline results (₹10,000/month, Feb 2010 – Dec 2019, ₹11.9 lakh invested)

| Strategy | Final value | Return/yr (XIRR) | Max drawdown | Sharpe vs Liquid |
|---|---|---|---|---|
{rows}

A SIP kept 100% in Liquid earned {P(sip_xirr(LIQUID_SIP))}.

**Bottom line:** 100% Nifty earned the most but fell hardest. **60/20/20 gave the best
return above the T-bill rate per unit of risk.** The optimiser SIPs (4–6) turned into ~70%
cash: Liquid barely moves, so the optimisers, which measure risk against a 0% rate, push it
to the 70% cap. They had tiny falls but earned only a little more than cash. Details:
[`07_comparison/`](07_comparison).

## Run it

```bash
pip install -r requirements.txt
python run_all.py            # rebuilds data, all six strategies, the comparison and these READMEs
python -m pytest -q          # automated checks
```

`python 06_optimized_sip/recommend.py --amount 10000` prints the Optimized SIP's split for the
next instalment (from the latest data, Dec 2019).

## Architecture

![Architecture and formulas](docs/architecture.png)

## Further reading

- [`docs/WORKED_EXAMPLE.md`](docs/WORKED_EXAMPLE.md): one investor followed through all 20 steps with real numbers
- [`extras/us_data/`](extras/us_data): the same study on US data 1973–2026 (earlier version, with its own report)
"""


# --------------------------------------------------------------------------- docs/WORKED_EXAMPLE.md
def worked_example() -> str:
    prefix = "../"
    opt = STRATS[5]
    res = RESULTS["Optimized SIP"]
    t = pd.read_csv(ROOT / "07_comparison" / "results" / "summary.csv", index_col=0)
    rs = pd.read_csv(ROOT / "07_comparison" / "results" / "rolling_summary.csv", index_col=0)
    tt = pd.read_csv(ROOT / "07_comparison" / "results" / "train_test.csv", index_col=0)
    cr = pd.read_csv(ROOT / "07_comparison" / "results" / "crisis.csv", index_col=0)
    md = (ROOT / "07_comparison" / "results" / "results.md").read_text(encoding="utf-8")
    best = md.split("Best fixed mix on train (highest Sharpe vs Liquid): ")[1].split("\n")[0]
    data = data_readme()
    part_a = data.split("## 2. The formulas: how each monthly return is built")[1].split("## 3. The output")[0]
    targets = target_formulas(5, opt, prefix)
    engine = engine_formulas(opt, res, prefix)
    scores = scoring_formulas(res, prefix)
    yearly = "\n".join(f"| {p} | " + " | ".join(P(v) for v in opt.target.loc[p].values) + " |"
                       for p in IDX[::12])
    six = "\n".join(f"| {n} | {M(t.loc[n, 'Final value'])} | {P(t.loc[n, 'XIRR'])} | "
                     f"{P(t.loc[n, 'Max drawdown'])} | {t.loc[n, 'Sharpe vs Liquid']:.2f} |" for n in t.index)
    liq = sip_xirr(LIQUID_SIP)
    return f"""# Layer 1 in 20 Steps: One Investor, Real Numbers (Nifty 50 / Gold / Liquid)

**The example:** *you* start a SIP of **₹10,000 a month in February 2010** and keep it going
every month until **December 2019**: {len(IDX)} instalments, **{M(len(IDX) * AMOUNT)} invested**.
You follow the **Optimized SIP** (strategy 6). Every number below is the project's actual
output; every formula shows what each term means, a Feb 2010 example and the line of code.

---

## Part A: Getting the data ready (folder `00_raw_data/`)

### Step 1: The question
You could put all ₹10,000 into a Nifty fund every month, or split it across Nifty, gold and a
liquid fund. **Is there a simple rule for splitting it that balances growth and safety better
than 100% Nifty or a fixed mix like 60/20/20?** We replay 2010–2019 month by month (a backtest).

### Step 2: The three assets
| Asset | What it is | Its personality |
|---|---|---|
| Nifty 50 | India's 50 largest companies | Grows fastest, falls hardest |
| Gold | Gold, priced in rupees | Rises when the rupee falls or markets panic |
| Liquid | A liquid fund earning the 91-day T-bill rate | Almost never falls; grows steadily |

### Steps 3–6: From daily prices to monthly rupee returns
{part_a}
**Result:** one table of 239 monthly returns (Feb 2000 – Dec 2019). Feb 2010, your first SIP
month: Nifty {S(FEB['Nifty'])}, Gold {S(FEB['Gold'])}, Liquid {S(FEB['Liquid'])}.

---

## Part B: Deciding how to split your ₹10,000 (folders `04_`, `05_`, `06_`)

### Steps 7–12: Look back 10 years, run two optimisers, average them
{targets}
### Step 13: Update every February
The 120-month window moves forward a year each time:

| Re-fit | Nifty | Gold | Liquid |
|---|---|---|---|
{yearly}

Liquid stays pinned at the 70% cap every year; only the Nifty/Gold split moves.

---

## Part C: Running your SIP month by month (`sip/engine.py`)

### Step 14: What happens to your money each month
{engine}
### Step 15: Five other versions of you
Same ₹10,000, same {len(IDX)} months, same costs: 100% Nifty, ⅓ each, 60/20/20, risk parity only,
max Sharpe only (folders `01_`–`05_`).

---

## Part D: Checking the result (`sip/metrics.py`, `07_comparison/`)

### Step 16: How your SIP is scored
{scores}
**Everyone's scores (Feb 2010 – Dec 2019):**

| Strategy | Final value | XIRR | Max drawdown | Sharpe vs Liquid |
|---|---|---|---|---|
{six}

A 100% Liquid SIP earned {P(liq)}.

### Step 17: Every 5-year SIP ({int(rs.iloc[0]['Windows'])} start dates)
Median XIRR: 100% Nifty {P(rs.loc['Equity SIP', 'Median XIRR'])}, 60/20/20
{P(rs.loc['60/20/20 annual rebal', 'Median XIRR'])}, Optimized {P(rs.loc['Optimized SIP', 'Median XIRR'])}.
No strategy lost money over any 5-year window in this decade.

### Step 18: Optimise once vs re-learn every year
The best fixed mix on 2010–2014 was **{best}**. On the unseen years 2015–2019 it earned
{P(tt.loc['Best static (train-tuned)', 'XIRR'])} (Sharpe vs Liquid {tt.loc['Best static (train-tuned)', 'Sharpe vs Liquid']:.2f}),
versus {P(tt.loc['Optimized SIP', 'XIRR'])} ({tt.loc['Optimized SIP', 'Sharpe vs Liquid']:.2f}) for the Optimized SIP.

### Step 19: Stress periods
| Period | 100% Nifty | Optimized SIP |
|---|---|---|
""" + "\n".join(f"| {p} | {P(cr.loc[p, 'Equity SIP'])} | {P(cr.loc[p, 'Optimized SIP'])} |" for p in cr.index) + f"""

Changing the look-back (60 / 90 / 120 months) or the band (3 / 5 / 10%) moved the Optimized
SIP's XIRR by less than 0.2 percentage points.

### Step 20: Verdict for you
- **100% Nifty** would have made the most ({M(t.loc['Equity SIP', 'Final value'])}, {P(t.loc['Equity SIP', 'XIRR'])}) but fell
  {P(t.loc['Equity SIP', 'Max drawdown'])} from its peak in 2011.
- **Your Optimized SIP** made {M(t.loc['Optimized SIP', 'Final value'])} ({P(t.loc['Optimized SIP', 'XIRR'])}) and never fell more than
  {P(abs(t.loc['Optimized SIP', 'Max drawdown']))}, because it was about **70% Liquid**. That is only
  {P(t.loc['Optimized SIP', 'XIRR'] - liq)} a year more than a 100% Liquid SIP.
- **60/20/20** gave the best return above the T-bill rate per unit of risk (Sharpe vs Liquid
  {t.loc['60/20/20 annual rebal', 'Sharpe vs Liquid']:.2f}).

**Bottom line:** with the mechanics kept identical, the optimisers turn a cash-like Liquid
fund into a 70% cash portfolio. Very safe, but not better per unit of risk than a simple 60/20/20.
"""


def main():
    (ROOT / "00_raw_data" / "README.md").write_text(data_readme(), encoding="utf-8")
    (ROOT / "docs" / "WORKED_EXAMPLE.md").write_text(worked_example(), encoding="utf-8")
    for k, folder in enumerate(STRATEGY_FOLDERS):
        (ROOT / folder / "README.md").write_text(strategy_readme(k), encoding="utf-8")
    (ROOT / "07_comparison" / "README.md").write_text(comparison_readme(), encoding="utf-8")
    (ROOT / "README.md").write_text(top_readme(), encoding="utf-8")
    print("READMEs regenerated.")


if __name__ == "__main__":
    main()
