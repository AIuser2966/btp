"""Strategy 2: Equal-weight SIP (1/3 each). The "no brain" diversified benchmark.

Rule: every month, split the instalment equally, 1/3 each into equity, bonds and gold.
Nothing is ever sold, so over time the portfolio drifts toward whatever grew fastest.

    python 02_equal_weight_sip/strategy.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # so the shared engine in sip/ can be imported

from sip.engine import Strategy  # noqa: E402
from sip.optimize import fixed_weights  # noqa: E402
from sip.report import LOOKBACK, run_strategy_folder  # noqa: E402

NAME = "Equal-weight SIP"
COLOUR = "#eb6834"
WEIGHTS = {"Equity": 1 / 3, "Bonds": 1 / 3, "Gold": 1 / 3}


def build(returns, lookback: int = LOOKBACK) -> Strategy:
    # Same target every month: 33.3 / 33.3 / 33.3, instalment split pro-rata, never rebalanced.
    target = fixed_weights(returns.index, WEIGHTS)
    return Strategy(NAME, target, contribution="pro_rata", rebalance="none",
                    description="1/3 each, never rebalanced.")


if __name__ == "__main__":
    run_strategy_folder(build, HERE, COLOUR)
