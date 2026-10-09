"""Strategy 6b: the FIXED Optimized SIP (Liquid treated as cash).

Same engine and same ½ risk parity + ½ max Sharpe idea as Strategy 6, with one change:
Liquid is held at a fixed share (LIQUID) instead of being optimised, and max Sharpe is
measured on returns ABOVE Liquid. The original optimisers measured risk against 0%, so the
almost risk-free Liquid fund looked perfect and was pushed to the 70% cap.

LIQUID was chosen with 2010-2019 data only (select_liquid_share.py), before any 2020-2025
result was looked at, and then frozen.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sip.engine import Strategy  # noqa: E402
from sip.optimize import optimized_cash_buffer, walk_forward_weights  # noqa: E402
from sip.report import LOOKBACK  # noqa: E402

NAME = "Fixed Optimized SIP"
COLOUR = "#c2185b"
LIQUID = 0.10            # frozen after select_liquid_share.py (2010-2019 data only)
LOWER, UPPER, BAND = 0.10, 0.70, 0.05


def target(returns, lookback: int = LOOKBACK, liquid: float = LIQUID):
    fit = lambda window, lo, hi: optimized_cash_buffer(window, lo, hi, liquid=liquid)  # noqa: E731
    return walk_forward_weights(returns, fit, lookback, lo=LOWER, hi=UPPER)


def build(returns, lookback: int = LOOKBACK, liquid: float = LIQUID) -> Strategy:
    return Strategy(NAME, target(returns, lookback, liquid), contribution="smart",
                    rebalance="band", band=BAND,
                    description=f"Liquid fixed at {liquid:.0%}; Nifty/Gold by ½ RP + ½ max Sharpe "
                                "(vs Liquid); smart instalments; 5% band.")
