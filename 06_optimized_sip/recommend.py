"""What should this month's SIP instalment buy under the Optimized SIP rule?

    python 06_optimized_sip/recommend.py --amount 10000
    python 06_optimized_sip/recommend.py --amount 10000 --holdings 60000 40000 80000

``--holdings`` are your current rupee values in Nifty, Gold and Liquid; with them the
instalment is sent to the under-weight assets first (the Optimized SIP's "smart" rule).
Uses the latest 120 months in 00_raw_data (to Dec 2019). Educational, not investment advice.
"""

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


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--amount", type=float, default=10_000)
    p.add_argument("--holdings", type=float, nargs=3, metavar=("NIFTY", "GOLD", "LIQUID"))
    p.add_argument("--lookback", type=int, default=120)
    p.add_argument("--band", type=float, default=0.05)
    args = p.parse_args()

    rets = read_returns_table()
    window = rets.iloc[-args.lookback:]
    rp = risk_parity(window, 0.10, 0.70)
    ms = max_sharpe(window, 0.10, 0.70)
    mu = (1 + window).prod() ** (12 / len(window)) - 1     # trailing 10-year pace
    target = (rp + ms) / 2

    table = pd.DataFrame({"Past 10y return/yr": mu.values, "Risk parity": rp,
                          "Max Sharpe": ms, "Target": target}, index=rets.columns)
    if args.holdings:
        h = np.array(args.holdings)
        buy = _smart_split(h, target, args.amount)
        table["Current weight"] = h / h.sum()
        drift = np.abs(h / h.sum() - target).max()
    else:
        buy = target * args.amount
    table["Buy this month (Rs)"] = buy

    print(f"\nData up to {rets.index[-1]} | fitted on the last {args.lookback} months\n")
    shown = table.copy()
    for c in shown.columns:
        shown[c] = shown[c].map((lambda v: f"{v:,.0f}") if c.startswith("Buy")
                                else (lambda v: f"{v:.1%}"))
    print(shown.to_string())
    print(f"\nTotal to invest: Rs {args.amount:,.0f}")
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
