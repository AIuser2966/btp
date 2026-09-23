"""The strategies compared in the study."""

from __future__ import annotations

import pandas as pd

from .engine import Strategy
from .optimize import fixed_weights, walk_forward_weights

EQUITY_ONLY = {"Equity": 1.0, "Bonds": 0.0, "Gold": 0.0}
EQUAL = {"Equity": 1 / 3, "Bonds": 1 / 3, "Gold": 1 / 3}
BALANCED = {"Equity": 0.60, "Bonds": 0.20, "Gold": 0.20}


def build_strategies(returns: pd.DataFrame, lookback: int = 120, lo: float = 0.10,
                     hi: float = 0.70, band: float = 0.05) -> list[Strategy]:
    idx = returns.index
    rp = walk_forward_weights(returns, "risk_parity", lookback, lo=lo, hi=hi)
    ms = walk_forward_weights(returns, "max_sharpe", lookback, lo=lo, hi=hi)
    return [
        Strategy("Equity SIP", fixed_weights(idx, EQUITY_ONLY),
                 description="Benchmark: 100% equity, the default single-fund SIP."),
        Strategy("Equal-weight SIP", fixed_weights(idx, EQUAL),
                 description="Naive 1/3 each; instalment split equally, never rebalanced."),
        Strategy("60/20/20 annual rebal", fixed_weights(idx, BALANCED), rebalance="calendar",
                 description="Classic static mix, sold back to target every 12 months."),
        Strategy("Risk-parity SIP", rp, contribution="smart", rebalance="band", band=band,
                 description="Walk-forward equal-risk weights, smart instalments, 5% band."),
        Strategy("Max-Sharpe SIP", ms, contribution="smart", rebalance="band", band=band,
                 description="Walk-forward max-Sharpe weights (10-70%), smart instalments, 5% band."),
        Strategy("Optimized SIP", (rp + ms) / 2, contribution="smart", rebalance="band",
                 band=band,
                 description="PROPOSED: average of risk-parity and max-Sharpe targets "
                             "(10-70%), smart instalments, 5% band."),
    ]
