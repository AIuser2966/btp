"""Strategy 7: Max-Utility SIP.

Every February, on the previous 120 months, choose the weights that maximise the investor's
mean-variance utility
        U = w'(mu - mu_Liquid) - (lam / 2) w' Sigma w          (yearly figures)
subject to 10% <= w_i <= 70% and sum(w) = 1. lam is the investor's risk aversion; it is the
Lagrange multiplier on the risk constraint in Markowitz's problem. Returns are measured above
Liquid, so how much is kept in Liquid follows from lam itself (Tobin's separation).
Same engine as Strategies 4-6: smart instalments, 5% band.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sip.engine import Strategy  # noqa: E402
from sip.optimize import max_utility, walk_forward_weights  # noqa: E402
from sip.report import LOOKBACK  # noqa: E402

LOWER, UPPER, BAND = 0.10, 0.70, 0.05
PROFILES = {"aggressive": 2.0, "moderate": 4.0, "conservative": 8.0}   # fixed before any test


def name(lam: float) -> str:
    return f"Max-Utility SIP (λ={lam:g})"


def target(returns, lam: float, lookback: int = LOOKBACK):
    fit = lambda window, lo, hi: max_utility(window, lo, hi, lam=lam)  # noqa: E731
    return walk_forward_weights(returns, fit, lookback, lo=LOWER, hi=UPPER)


def build(returns, lam: float, lookback: int = LOOKBACK) -> Strategy:
    return Strategy(name(lam), target(returns, lam, lookback), contribution="smart",
                    rebalance="band", band=BAND,
                    description=f"Walk-forward max utility (λ={lam:g}), smart instalments, 5% band.")
