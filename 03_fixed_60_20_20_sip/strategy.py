"""Strategy 3: 60/20/20 SIP. The classic fixed mix, reset once a year.

Rule: every month, invest 60% in Nifty, 20% in gold, 20% in liquid. Every 12 months,
sell what has grown too big and buy what has shrunk, so the portfolio is back at
exactly 60/20/20 (annual rebalancing).

    python 03_fixed_60_20_20_sip/strategy.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # so the shared engine in sip/ can be imported

from sip.engine import Strategy  # noqa: E402
from sip.optimize import fixed_weights  # noqa: E402
from sip.report import LOOKBACK, run_strategy_folder  # noqa: E402

NAME = "60/20/20 annual rebal"
COLOUR = "#1baf7a"
WEIGHTS = {"Nifty": 0.60, "Gold": 0.20, "Liquid": 0.20}


def build(returns, lookback: int = LOOKBACK) -> Strategy:
    # Same target every month: 60 / 20 / 20, full rebalance back to it every 12 months.
    target = fixed_weights(returns.index, WEIGHTS)
    return Strategy(NAME, target, contribution="pro_rata", rebalance="calendar",
                    rebalance_every=12, description="60/20/20, rebalanced yearly.")


if __name__ == "__main__":
    run_strategy_folder(build, HERE, COLOUR)
