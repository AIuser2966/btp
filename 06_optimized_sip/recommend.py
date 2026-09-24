"""What should this month's SIP instalment buy?

    python 06_optimized_sip/recommend.py --amount 10000
    python 06_optimized_sip/recommend.py --currency INR --amount 10000 --holdings 250000 180000 120000

``--holdings`` are your current values in Equity, Bonds and Gold; with them the
instalment is sent to the under-weight assets first (the Optimized SIP's "smart" rule).
Educational tool built on the bundled back-test data, not investment advice.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sip.data import read_returns_table  # noqa: E402
from sip.engine import _smart_split  # noqa: E402
from sip.optimize import max_sharpe, risk_parity  # noqa: E402

ML_MODELS = ["Ridge", "Random forest", "Gradient boosting"]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--currency", default="USD", choices=["USD", "INR"])
    p.add_argument("--amount", type=float, default=10_000)
    p.add_argument("--holdings", type=float, nargs=3, metavar=("EQUITY", "BONDS", "GOLD"))
    p.add_argument("--model", default="none", choices=["none", *ML_MODELS],
                   help="optional (extras/ai_forecasting): ML forecast in the max-Sharpe half")
    p.add_argument("--lookback", type=int, default=120)
    p.add_argument("--band", type=float, default=0.05)
    args = p.parse_args()

    rets = read_returns_table(args.currency)
    window = rets.iloc[-args.lookback:]
    rp = risk_parity(window, 0.10, 0.70)
    if args.model == "none":
        mu = (1 + window).prod() ** (12 / len(window)) - 1   # trailing 10-year pace
        ms = max_sharpe(window, 0.10, 0.70)
    else:
        sys.path.insert(0, str(ROOT / "extras" / "ai_forecasting"))
        import forecast as fc
        from sip.data import load_macro
        from sip.optimize import max_sharpe_mu
        X = fc.build_features(rets, load_macro())
        mu = fc.latest_forecast(X, fc.build_targets(rets), args.model)
        ms = max_sharpe_mu(mu.values / 12, window.cov().values, 0.10, 0.70)
    target = (rp + ms) / 2

    table = pd.DataFrame({"Expected 12m return": mu.values, "Risk parity": rp,
                          "Max Sharpe": ms, "Target": target}, index=rets.columns)
    if args.holdings:
        h = np.array(args.holdings)
        buy = _smart_split(h, target, args.amount)
        table["Current weight"] = h / h.sum()
        drift = np.abs(h / h.sum() - target).max()
    else:
        buy = target * args.amount
    table["Buy this month"] = buy

    print(f"\nData up to {rets.index[-1]} | {args.currency} | fitted on the last "
          f"{args.lookback} months | forecast: "
          f"{'trailing 10y average' if args.model == 'none' else args.model}\n")
    shown = table.copy()
    for c in shown.columns:
        shown[c] = shown[c].map((lambda v: f"{v:,.0f}") if c == "Buy this month"
                                else (lambda v: f"{v:.1%}"))
    print(shown.to_string())
    print(f"\nTotal to invest: {args.amount:,.0f}")
    if args.holdings:
        after = h + buy
        drift_after = np.abs(after / after.sum() - target).max()
        if drift_after > args.band:
            trade = target * after.sum() - after
            moves = ", ".join(f"{'buy' if t > 0 else 'sell'} {abs(t):,.0f} {a}"
                              for a, t in zip(rets.columns, trade) if abs(t) >= 1)
            print(f"After this instalment the largest drift is still {drift_after:.1%} "
                  f"(> {args.band:.0%} band), so the rule rebalances: {moves}.")
        else:
            print(f"Largest drift from target was {drift:.1%}, {drift_after:.1%} after this "
                  f"instalment (band {args.band:.0%}): no selling needed.")
    print("\nEducational output from a back-test model, not investment advice.")


if __name__ == "__main__":
    main()
