"""Strategy 6: Optimized SIP. Half risk parity + half max Sharpe.

Rule:
  1. Every 12 months, compute BOTH the risk-parity weights (strategy 4) and the
     max-Sharpe weights (strategy 5) from the previous 120 months, each within 10-70%.
  2. Target = 1/2 x risk-parity weights + 1/2 x max-Sharpe weights.
  3. Each month, send the instalment to the assets furthest below target first.
  4. Only sell (rebalance fully) if some asset drifts more than 5 points from target.

    python 06_optimized_sip/strategy.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # so the shared engine in sip/ can be imported

from sip.engine import Strategy  # noqa: E402
from sip.optimize import walk_forward_weights  # noqa: E402
from sip.report import LOOKBACK, run_strategy_folder  # noqa: E402

NAME = "Optimized SIP"
COLOUR = "#008300"
LOWER, UPPER, BAND = 0.10, 0.70, 0.05


def build(returns, lookback: int = LOOKBACK) -> Strategy:
    risk_parity = walk_forward_weights(returns, "risk_parity", lookback, lo=LOWER, hi=UPPER)
    max_sharpe = walk_forward_weights(returns, "max_sharpe", lookback, lo=LOWER, hi=UPPER)
    target = 0.5 * risk_parity + 0.5 * max_sharpe
    return Strategy(NAME, target, contribution="smart", rebalance="band", band=BAND,
                    description="1/2 risk parity + 1/2 max Sharpe, smart instalments, 5% band.")


if __name__ == "__main__":
    run_strategy_folder(build, HERE, COLOUR)
