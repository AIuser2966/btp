"""Machine-learning study: can forecasting future returns improve the Optimized SIP?

    python run_forecast.py                 # USD  -> results/usd/forecast/
    python run_forecast.py --currency INR  # INR  -> results/inr/forecast/

Part A grades the forecasts themselves; Part B plugs them into the SIP and compares.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from run_backtest import fmt
from sip import analysis, plots
from sip import forecast as fc
from sip.data import load_macro, load_returns
from sip.engine import Strategy, contribution_schedule, run_sip
from sip.metrics import summary_table
from sip.strategies import build_strategies

ORACLE = "Oracle (perfect foresight)"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--currency", default="USD", choices=["USD", "INR"])
    p.add_argument("--amount", type=float, default=10_000)
    p.add_argument("--cost-bps", type=float, default=10.0)
    p.add_argument("--window-years", type=int, default=10)
    p.add_argument("--out", default="results")
    args = p.parse_args()
    out = Path(args.out) / args.currency.lower() / "forecast"
    out.mkdir(parents=True, exist_ok=True)

    rets = load_returns(args.currency)
    X = fc.build_features(rets, load_macro())
    Y = fc.build_targets(rets)

    # ---- Part A: forecast accuracy -------------------------------------------------
    forecasts, importances = {}, {}
    for m in [fc.BENCHMARK, *fc.MODELS]:
        print("fitting", m)
        forecasts[m], importances[m] = fc.walk_forward_forecasts(X, Y, m)
    forecasts[fc.TRAILING] = fc.trailing_mean_forecast(rets)
    ev = fc.evaluate(forecasts, Y)
    ev.to_csv(out / "forecast_accuracy.csv", index=False)
    for m, f in forecasts.items():
        f.to_csv(out / f"forecasts_{m.lower().replace(' ', '_')}.csv")
    for m, imp in importances.items():
        if len(imp):
            imp.to_csv(out / f"importance_{m.lower().replace(' ', '_')}.csv", index=False)

    # ---- Part B: plug forecasts into the SIP ---------------------------------------
    base = build_strategies(rets)
    keep = {"Equity SIP", "Equal-weight SIP", "Optimized SIP"}
    strategies = [s for s in base if s.name in keep]
    ml_targets = {m: fc.forecast_weights(rets, forecasts[m]) for m in fc.MODELS}
    ml_targets[ORACLE] = fc.forecast_weights(rets, fc.build_targets(rets, partial=True))
    for m, target in ml_targets.items():
        strategies.append(Strategy(f"Optimized + {m}", target, contribution="smart",
                                   rebalance="band", band=0.05,
                                   description=f"Optimized SIP with {m} return forecasts"))

    start = base[-1].target.dropna().index[0]
    idx = rets.loc[start:].index
    contrib = contribution_schedule(idx, args.amount)
    results = [run_sip(rets, s, contrib, args.cost_bps) for s in strategies]
    table = summary_table(results)
    table.to_csv(out / "ml_strategies.csv")
    roll = analysis.rolling_windows(rets, strategies, str(start), args.window_years,
                                    amount=args.amount, cost_bps=args.cost_bps)
    rsum = analysis.rolling_summary(roll)
    rsum.to_csv(out / "ml_rolling_summary.csv")
    crisis = analysis.crisis_table(results, analysis.CRISES)
    crisis.to_csv(out / "ml_crisis.csv")

    # ---- Charts --------------------------------------------------------------------
    plots.forecast_r2_chart(ev, out / "forecast_r2.png")
    plots.forecast_vs_actual_chart(forecasts, Y.loc[start:], out / "forecast_vs_actual.png")
    plots.importance_chart(importances["Random forest"], out / "importance_rf.png",
                           "Random forest")
    plots.wealth_chart(results, out / "ml_wealth.png", args.currency)
    plots.rolling_chart(roll, out / "ml_rolling_xirr.png", args.window_years)

    acc = ev.pivot(index="Model", columns="Asset", values="OOS R2 vs hist mean")
    acc = acc.drop(columns="Pick best asset").loc[list(forecasts)]
    hits = ev.pivot(index="Model", columns="Asset", values="Direction hit rate").loc[list(forecasts)]
    corr = ev.pivot(index="Model", columns="Asset", values="Correlation")
    corr = corr.drop(columns="Pick best asset").loc[list(forecasts)]
    report = [
        f"# Forecasting study ({args.currency})",
        f"Out-of-sample forecasts of next-12-month returns, {ev.attrs['period']} "
        f"({ev.attrs['months']} monthly forecasts, re-fitted yearly, walk-forward).\n",
        "## A1. Out-of-sample R² vs the historical mean (positive = better than the average)\n",
        acc.round(3).to_markdown(), "",
        "## A2. Correlation of forecast with actual\n", corr.round(2).to_markdown(), "",
        "## A3. Hit rates (direction of return; last column = picked next year's best asset)\n",
        fmt(hits), "",
        "## B1. SIP back-test with forecasts plugged into the optimizer\n",
        f"SIP {idx[0]}..{idx[-1]}, {args.amount:,.0f}/month, {args.cost_bps:.0f} bps.\n",
        fmt(table), "",
        f"## B2. Rolling {args.window_years}-year SIPs\n", fmt(rsum), "",
        "## B3. Stress periods\n", fmt(crisis),
    ]
    (out / "forecast_results.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
