"""Step 8d: the out-of-sample test. Every strategy runs on Jan 2020 – Dec 2025, data that played
no part in building or choosing it.

    python 08_forward_test/run_forward.py      -> results/

Rules are exactly as in folders 01-06, plus the Fixed Optimized SIP (fixed_optimizer.py, frozen
on 2010-2019 data). The optimisers keep re-fitting every February on the previous 120 months,
so in 2020-2025 they also learn from the new data as it arrives — as a real investor would.

Winner rule, fixed before running: highest Sharpe vs Liquid over 2020-2025 (the project's
fair risk-adjusted measure); XIRR and the worst fall are reported alongside.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import fixed_optimizer  # noqa: E402
from sip import analysis, plots  # noqa: E402
from sip.engine import Strategy, contribution_schedule, run_sip  # noqa: E402
from sip.forward_data import FORWARD_END, FORWARD_START, read_combined  # noqa: E402
from sip.metrics import sip_xirr, summary_table  # noqa: E402
from sip.optimize import fixed_weights  # noqa: E402
from sip.report import AMOUNT, COST_BPS, LOOKBACK, fmt  # noqa: E402
from sip.strategies import build_strategies  # noqa: E402

OUT = HERE / "results"
STRESS = {
    "COVID crash (Feb-Mar 2020)": ("2020-02", "2020-03"),
    "2022 rate-hike sell-off (Jan-Jun 2022)": ("2022-01", "2022-06"),
    "2024-25 Nifty correction (Oct 2024-Feb 2025)": ("2024-10", "2025-02"),
}
COLS = ["Final value", "XIRR", "Volatility", "Sharpe vs Liquid", "Max drawdown",
        "Worst wealth drop", "Annual sell turnover"]


def all_strategies(returns: pd.DataFrame) -> list[Strategy]:
    return build_strategies(returns, LOOKBACK) + [fixed_optimizer.build(returns, LOOKBACK)]


def run_period(returns, strategies, start, end):
    idx = returns.loc[start:end].index
    contrib = contribution_schedule(idx, AMOUNT)
    results = [run_sip(returns, s, contrib, COST_BPS) for s in strategies]
    liquid = run_sip(returns, Strategy("100% Liquid", fixed_weights(
        returns.index, {"Nifty": 0, "Gold": 0, "Liquid": 1})), contrib, COST_BPS)
    table = summary_table(results, rf_returns=returns["Liquid"])
    return results, table, liquid, contrib


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(exist_ok=True)
    R = read_combined()
    strategies = all_strategies(R)

    # ---------------------------------------------------------------- 2020-2025 (out of sample)
    res, table, liquid, contrib = run_period(R, strategies, FORWARD_START, FORWARD_END)
    table.to_csv(OUT / "summary_2020_2025.csv")
    winner = table["Sharpe vs Liquid"].idxmax()

    # ---------------------------------------------------------------- full 2010-2025 run
    res_full, table_full, liquid_full, _ = run_period(R, strategies, "2010-02", FORWARD_END)
    table_full.to_csv(OUT / "summary_2010_2025.csv")

    # in-sample 2010-2019 for the same seven (old data only -> same numbers as 07 for 1-6)
    res_old, table_old, _, _ = run_period(R.loc[:"2019-12"], all_strategies(R.loc[:"2019-12"]),
                                          "2010-02", "2019-12")
    table_old.to_csv(OUT / "summary_2010_2019.csv")

    years = analysis.calendar_year_returns(res)
    years.columns = [r.name for r in res]
    years.to_csv(OUT / "calendar_years_2020_2025.csv")
    stress = analysis.crisis_table(res, STRESS)
    stress.to_csv(OUT / "stress_2020_2025.csv")

    # rolling 3-year SIPs inside 2020-2025 (37 start months)
    roll = analysis.rolling_windows(R, strategies, FORWARD_START, years=3)
    roll.to_csv(OUT / "rolling_3y_2020_2025.csv", index=False)
    roll_s = roll.groupby("Strategy", sort=False)["XIRR"].agg(["median", "min", "max"])

    # targets the optimisers chose each February
    feb = [m for m in R.loc[FORWARD_START:FORWARD_END].index if m.month == 2]
    tgt = pd.DataFrame({s.name: s.target.loc[feb].apply(
        lambda row: " / ".join(f"{v:.0%}" for v in row), axis=1) for s in strategies[3:]})

    plots.wealth_chart(res, OUT / "wealth_2020_2025.png", "INR")
    plots.wealth_chart(res_full, OUT / "wealth_2010_2025.png", "INR")
    plots.drawdown_chart(res, OUT / "drawdown_2020_2025.png",
                         names=("Equity SIP", "60/20/20 annual rebal", "Fixed Optimized SIP"))

    # ---------------------------------------------------------------- write results.md
    L = [f"# Out-of-sample results: {FORWARD_START} – {FORWARD_END}\n",
         f"₹{AMOUNT:,}/month for {len(contrib)} months (₹{contrib.sum():,.0f} paid in), 0.1% cost per trade. "
         "Rules unchanged from 2010-2019; optimisers keep re-fitting every February on the "
         "previous 120 months.\n",
         "## 2020-2025 (never seen when the rules were made)\n",
         fmt(table[COLS]),
         f"\nReference: 100% Liquid SIP XIRR {sip_xirr(liquid):.2%}.\n",
         f"**Winner by the pre-set rule (highest Sharpe vs Liquid): {winner}.**\n",
         "## Same seven strategies, 2010-2019 (in-sample, original data)\n", fmt(table_old[COLS]),
         "\n## Whole period Feb 2010 – Dec 2025 (191 months)\n", fmt(table_full[COLS]),
         f"\nReference: 100% Liquid SIP XIRR {sip_xirr(liquid_full):.2%}.\n",
         "## Calendar-year returns (time-weighted)\n", fmt(years.T),
         "\n## Stress periods (strategy return over the period)\n", fmt(stress),
         "\n## Every 3-year SIP started Jan 2020 – Jan 2023 (37 windows): XIRR\n", fmt(roll_s),
         "\n## Targets chosen each February (Nifty / Gold / Liquid)\n", tgt.to_markdown(),
         ]
    (OUT / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
