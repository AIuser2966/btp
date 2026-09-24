"""Strategy 1: Equity SIP (100% stocks). The benchmark most people follow.

Rule: every month, put the whole instalment into equity (S&P 500 with dividends).
Nothing is ever sold or rebalanced.

    python 01_equity_sip/strategy.py      ->  results/usd/, results/inr/
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # so the shared engine in sip/ can be imported

from sip.engine import Strategy  # noqa: E402
from sip.optimize import fixed_weights  # noqa: E402
from sip.report import LOOKBACK, run_strategy_folder  # noqa: E402

NAME = "Equity SIP"
COLOUR = "#2a78d6"
WEIGHTS = {"Equity": 1.0, "Bonds": 0.0, "Gold": 0.0}


def build(returns, lookback: int = LOOKBACK) -> Strategy:
    # Same target every month: 100 / 0 / 0.
    target = fixed_weights(returns.index, WEIGHTS)
    return Strategy(NAME, target, contribution="pro_rata", rebalance="none",
                    description="100% equity, never rebalanced.")


if __name__ == "__main__":
    run_strategy_folder(build, HERE, COLOUR)
