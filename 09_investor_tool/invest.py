"""This month's SIP instruction for an investor today.

    python 09_investor_tool/invest.py --amount 10000
    python 09_investor_tool/invest.py --amount 10000 --holdings 120000 95000 40000
    python 09_investor_tool/invest.py --amount 10000 --holdings 120000 95000 40000 --risk conservative
    python 09_investor_tool/invest.py --amount 10000 --holdings 120000 95000 40000 --strategy equal-weight

--holdings are what your Nifty, Gold and Liquid investments are worth today (in rupees).
--risk (aggressive / moderate / conservative, default moderate) sets your risk aversion λ = 2 / 4 / 8;
the tool then uses the strategy with the highest utility U = return above Liquid − (λ/2)·variance
on the out-of-sample years 2020-2025 (10_max_utility/results/winners.csv).
--strategy overrides that choice.

It applies exactly the rules that were back-tested in folders 01-06 and 08: the same target,
the same way of splitting the instalment, the same rebalancing rule. The data currently ends
in Dec 2025, so the plan is for the instalment after that (Jan 2026).

First version: a command-line tool. It will later be refined into a website.
Educational output from a back-test, not investment advice.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sip.engine import _smart_split  # noqa: E402
from sip.forward_data import read_combined  # noqa: E402
from sip.optimize import max_sharpe, max_utility, optimized_cash_buffer, risk_parity  # noqa: E402

ASSETS = ["Nifty", "Gold", "Liquid"]
LOOKBACK, BAND, LO, HI = 120, 0.05, 0.10, 0.70
FIXED_LIQUID = 0.10        # frozen in 08_forward_test/fixed_optimizer.py

STRATEGIES = {
    # name: (description, how the target is set, instalment rule, rebalance rule)
    "equal-weight": ("Equal-weight SIP (Strategy 2): ⅓ each, never sell",
                     lambda win: np.array([1, 1, 1]) / 3, "pro_rata", "none"),
    "fixed-optimized": ("Fixed Optimized SIP (08): Liquid 10%, Nifty/Gold by ½ risk parity + ½ max Sharpe",
                        lambda win: optimized_cash_buffer(win, LO, HI, liquid=FIXED_LIQUID), "smart", "band"),
    "optimized": ("Original Optimized SIP (Strategy 6): ½ risk parity + ½ max Sharpe",
                  lambda win: 0.5 * risk_parity(win, LO, HI) + 0.5 * max_sharpe(win, LO, HI), "smart", "band"),
    "equity": ("Equity SIP (Strategy 1): 100% Nifty", lambda win: np.array([1.0, 0, 0]), "pro_rata", "none"),
    "60-20-20": ("60/20/20 SIP (Strategy 3)", lambda win: np.array([0.6, 0.2, 0.2]), "pro_rata", "calendar"),
    "risk-parity": ("Risk-parity SIP (Strategy 4)", lambda win: risk_parity(win, LO, HI), "smart", "band"),
    "max-sharpe": ("Max-Sharpe SIP (Strategy 5)", lambda win: max_sharpe(win, LO, HI), "smart", "band"),
}
RISK_LAMBDA = {"aggressive": 2.0, "moderate": 4.0, "conservative": 8.0}
WINNERS = ROOT / "10_max_utility" / "results" / "winners.csv"
# names used in the back-test results -> tool keys
RESULT_NAMES = {"Equal-weight SIP": "equal-weight", "Fixed Optimized SIP": "fixed-optimized",
                "Optimized SIP": "optimized", "Equity SIP": "equity", "60/20/20 annual rebal": "60-20-20",
                "Risk-parity SIP": "risk-parity", "Max-Sharpe SIP": "max-sharpe"}


def max_utility_entry(lam: float):
    return (f"Max-Utility SIP (Strategy 7, λ={lam:g})", lambda win: max_utility(win, LO, HI, lam=lam),
            "smart", "band")


def strategy_for_risk(risk: str) -> str:
    """The out-of-sample utility winner for this risk profile (key into STRATEGIES or 'max-utility')."""
    w = pd.read_csv(WINNERS, index_col="Profile")
    name = w.loc[risk, "Best 2020-2025 (out-of-sample)"]
    return "max-utility" if name.startswith("Max-Utility") else RESULT_NAMES[name]


WHAT_TO_BUY = {"Nifty": "a Nifty 50 index fund or ETF",
               "Gold": "a gold ETF (or gold fund)",
               "Liquid": "a liquid mutual fund"}


def target_for(month: pd.Period, rets: pd.DataFrame, fit) -> tuple[np.ndarray, pd.Period]:
    """Target in force in `month`: fitted each February on the 120 months before it."""
    fit_month = pd.Period(year=month.year if month.month >= 2 else month.year - 1, month=2, freq="M")
    window = rets.loc[:fit_month - 1].iloc[-LOOKBACK:]
    assert len(window) == LOOKBACK and window.index[-1] == fit_month - 1
    return np.asarray(fit(window), dtype=float), fit_month


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--amount", type=float, default=10_000, help="this month's SIP amount (₹)")
    p.add_argument("--holdings", type=float, nargs=3, metavar=("NIFTY", "GOLD", "LIQUID"),
                   help="current value of your three investments (₹); leave out if starting fresh")
    p.add_argument("--risk", choices=list(RISK_LAMBDA), default="moderate",
                   help="your risk profile; picks the strategy with the best utility for it")
    p.add_argument("--strategy", choices=list(STRATEGIES) + ["max-utility"],
                   help="use this strategy instead of the one chosen for your risk profile")
    args = p.parse_args()

    rets = read_combined()
    month = rets.index[-1] + 1                       # the instalment we are planning
    lam = RISK_LAMBDA[args.risk]
    key = args.strategy or strategy_for_risk(args.risk)
    label, fit, contribution, rebalance = max_utility_entry(lam) if key == "max-utility" else STRATEGIES[key]
    w, fit_month = target_for(month, rets, fit)

    h = np.array(args.holdings) if args.holdings else np.zeros(3)
    buy = _smart_split(h, w, args.amount) if contribution == "smart" else w * args.amount
    after = h + buy

    table = pd.DataFrame({"Target": w}, index=ASSETS)
    if h.sum() > 0:
        table["You hold now"] = h / h.sum()
    table["Buy this month (₹)"] = buy
    table["After buying"] = after / after.sum()
    shown = table.copy()
    for c in shown.columns:
        shown[c] = shown[c].map((lambda v: f"{v:,.0f}") if "₹" in c else (lambda v: f"{v:.1%}"))

    why = ("your choice (--strategy)" if args.strategy else
           f"highest utility for {'an' if args.risk[0] in 'aeiou' else 'a'} {args.risk} investor (λ={lam:g}) on 2020-2025, 10_max_utility")
    print(f"\nStrategy : {label}")
    print(f"Chosen as: {why}")
    print(f"Plan for : {month.strftime('%b %Y')} instalment of ₹{args.amount:,.0f}")
    print(f"Data     : month-end returns up to {rets.index[-1].strftime('%b %Y')}"
          + (f"; target fitted in {fit_month.strftime('%b %Y')} on the previous 120 months"
             if key in ("fixed-optimized", "optimized", "risk-parity", "max-sharpe", "max-utility") else ""))
    print()
    print(shown.to_string())
    print()

    drift = float(np.abs(after / after.sum() - w).max()) if after.sum() > 0 else 0.0
    net = buy.copy()                                 # what to actually trade this month
    if rebalance == "band" and drift > BAND:
        net = w * after.sum() - h                    # instalment + rebalance in one go
        print(f"Rebalance: after buying, the largest gap from target is {drift:.1%} (> 5%), so the rule "
              f"also resets the whole portfolio to the target (selling what is above it).")
    elif rebalance == "band":
        print(f"Rebalance: largest gap from target after buying is {drift:.1%} (≤ 5%): no selling needed.")
    elif rebalance == "calendar":
        print("Rebalance: this strategy resets every jar to target once a year, in January "
              "(sell what is above target, buy what is below).")
    else:
        print("Rebalance: this strategy never sells; only the new instalment is split.")

    print("\nHow to place it:")
    for a, x in zip(ASSETS, net):
        if x >= 1:
            print(f"  • buy ₹{x:,.0f} of {WHAT_TO_BUY[a]}")
        elif x <= -1:
            print(f"  • sell ₹{-x:,.0f} of {WHAT_TO_BUY[a]}")
    gap_months = (pd.Timestamp.today().to_period("M") - month).n
    if gap_months > 0:
        print(f"\nNote: today is {gap_months} month(s) after {month.strftime('%b %Y')}. The data needs "
              "updating to plan later instalments (planned for the next version / website).")
    print("\nEducational output from a back-test model, not investment advice.")


if __name__ == "__main__":
    main()
