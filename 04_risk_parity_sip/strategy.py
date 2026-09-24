"""Strategy 4: Risk-parity SIP. Each asset contributes equal risk.

Rule:
  1. Every 12 months, look at the previous 120 months of returns only.
  2. Choose weights w so every asset's risk contribution  RC_i = w_i * (Sigma w)_i  is equal
     (Sigma = covariance matrix), with each weight between 10% and 70%.
  3. Each month, send the instalment to the assets furthest below target first.
  4. Only sell (rebalance fully) if some asset drifts more than 5 points from target.

    python 04_risk_parity_sip/strategy.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # so the shared engine in sip/ can be imported

from sip.engine import Strategy  # noqa: E402
from sip.optimize import walk_forward_weights  # noqa: E402
from sip.report import LOOKBACK, run_strategy_folder  # noqa: E402

NAME = "Risk-parity SIP"
COLOUR = "#eda100"
LOWER, UPPER, BAND = 0.10, 0.70, 0.05


def build(returns, lookback: int = LOOKBACK) -> Strategy:
    # Re-fitted every 12 months on the past `lookback` months only (no look-ahead).
    target = walk_forward_weights(returns, "risk_parity", lookback, lo=LOWER, hi=UPPER)
    return Strategy(NAME, target, contribution="smart", rebalance="band", band=BAND,
                    description="Walk-forward risk parity, smart instalments, 5% band.")


if __name__ == "__main__":
    run_strategy_folder(build, HERE, COLOUR)
