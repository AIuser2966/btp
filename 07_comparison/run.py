"""Compare all six strategies side by side and write tables + charts to ``results/``.

    python 07_comparison/run.py

Each strategy's rule lives in its own folder (01_ ... 06_); this script loads all six,
runs them on identical data, months, instalments and costs, and adds the robustness
tests that only make sense side by side (rolling windows, train/test split, the grid of
all fixed mixes, sensitivity of the Optimized SIP, stress periods).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sip import analysis, plots  # noqa: E402
from sip.data import read_returns_table  # noqa: E402
from sip.report import WINDOW_YEARS, fmt  # noqa: E402
from sip.engine import contribution_schedule, run_sip  # noqa: E402
from sip.metrics import summary_table  # noqa: E402
from sip.strategies import build_strategies  # noqa: E402

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--amount", type=float, default=10_000)
    p.add_argument("--step-up", type=float, default=0.0, help="yearly SIP increase, e.g. 0.1")
    p.add_argument("--cost-bps", type=float, default=10.0)
    p.add_argument("--lookback", type=int, default=120, help="months of history per fit")
    p.add_argument("--window-years", type=int, default=WINDOW_YEARS)
    p.add_argument("--out", default=str(HERE / "results"))
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rets = read_returns_table()
    liquid = rets["Liquid"]           # risk-free proxy for "Sharpe vs Liquid"
    strategies = build_strategies(rets, lookback=args.lookback)
    start = strategies[-1].target.dropna().index[0]   # first month with a full look-back
    idx = rets.loc[start:].index
    contrib = contribution_schedule(idx, args.amount, args.step_up)
    print(f"INR: SIP {idx[0]} .. {idx[-1]} ({len(idx)} instalments)")

    # 1. Full-period back-test
    results = [run_sip(rets, s, contrib, args.cost_bps) for s in strategies]
    table = summary_table(results, rf_returns=liquid)
    table.to_csv(out / "summary.csv")

    # 2. Rolling windows
    roll = analysis.rolling_windows(rets, strategies, str(start), args.window_years,
                                    amount=args.amount, cost_bps=args.cost_bps)
    roll.to_csv(out / "rolling_windows.csv", index=False)
    rsum = analysis.rolling_summary(roll)
    rsum.to_csv(out / "rolling_summary.csv")

    # 3. Look-ahead reference: every static mix over the whole period
    grid = analysis.static_grid(rets, contrib, cost_bps=args.cost_bps)
    grid.to_csv(out / "static_grid.csv", index=False)
    hindsight = analysis.best_static(grid, list(rets.columns))

    # 4. Train/test split
    mid = idx[len(idx) // 2]
    train, test = (str(idx[0]), str(mid - 1)), (str(mid), str(idx[-1]))
    w_star, tt_results = analysis.train_test_split(rets, strategies, train, test,
                                                   args.amount, args.cost_bps)
    tt_table = summary_table(tt_results, rf_returns=liquid)
    tt_table.to_csv(out / "train_test.csv")

    # 5. Sensitivity of the proposed strategy to its parameters
    sens = analysis.sensitivity(rets, contrib, cost_bps=args.cost_bps)
    sens.to_csv(out / "sensitivity.csv")

    # 6. Stress periods and annual returns
    crisis = analysis.crisis_table(results, analysis.CRISES)
    crisis.to_csv(out / "crisis.csv")
    analysis.calendar_year_returns(results).to_csv(out / "calendar_year_returns.csv")
    strategies[-1].target.loc[start:].to_csv(out / "optimized_target_weights.csv")

    # Charts
    plots.wealth_chart(results, out / "wealth.png", "INR")
    plots.drawdown_chart(results, out / "drawdown.png")
    plots.weights_chart(strategies[-1].target.loc[start:], out / "weights.png",
                        "Optimized SIP: target weights (re-fitted each year on past 10 years)")
    plots.rolling_chart(roll, out / "rolling_xirr.png", args.window_years)
    plots.frontier_chart(grid, table, out / "frontier.png")

    report = [
        "# Results (Nifty 50 / Gold / Liquid, rupee SIP)",
        f"SIP of ₹{args.amount:,.0f}/month, {idx[0]} to {idx[-1]}, "
        f"step-up {args.step_up:.0%}, costs {args.cost_bps:.0f} bps per trade.\n",
        "## Full-period back-test\n", fmt(table), "",
        f"## Rolling {args.window_years}-year SIPs\n", fmt(rsum), "",
        "## Train / test split\n",
        f"Train {train[0]}..{train[1]}, test {test[0]}..{test[1]}. "
        f"Best fixed mix on train (highest Sharpe vs Liquid): {w_star}\n", fmt(tt_table), "",
        "## Sensitivity / ablation of the Optimized SIP\n", fmt(sens.reset_index(), index=False), "",
        "## Stress periods (cumulative time-weighted return)\n", fmt(crisis), "",
        "## Hindsight reference\n",
        f"Best fixed mix with perfect hindsight over the full period (highest Sharpe vs Liquid): {hindsight}",
    ]
    (out / "results.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
