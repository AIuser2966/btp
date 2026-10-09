"""Step 8c: choose the fixed optimiser's Liquid share using 2010-2019 ONLY.

    python 08_forward_test/select_liquid_share.py   -> results/selection_2010_2019.md

Candidates 10%, 20%, 30%. Rule (decided before running): highest Sharpe vs Liquid on the
original Feb 2010 - Dec 2019 SIP. Data after 2019 is never loaded here.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from fixed_optimizer import build  # noqa: E402
from sip.data import read_returns_table  # noqa: E402
from sip.engine import contribution_schedule, run_sip  # noqa: E402
from sip.metrics import summarise  # noqa: E402
from sip.report import AMOUNT, COST_BPS, LOOKBACK, sip_months  # noqa: E402

rets = read_returns_table()                       # Feb 2000 - Dec 2019 only
assert str(rets.index[-1]) == "2019-12"
idx = sip_months(rets)
contrib = contribution_schedule(idx, AMOUNT)
rows = []
for liquid in (0.10, 0.20, 0.30):
    res = run_sip(rets, build(rets, LOOKBACK, liquid), contrib, COST_BPS)
    m = summarise(res, rf_returns=rets["Liquid"])
    rows.append((liquid, m))
best = max(rows, key=lambda x: x[1]["Sharpe vs Liquid"])[0]
lines = ["# Choosing the fixed optimiser's Liquid share (2010-2019 data only)\n",
         f"SIP {idx[0]} - {idx[-1]}, ₹{AMOUNT:,}/month. Rule fixed in advance: highest Sharpe vs Liquid.\n",
         "| Liquid share | Final value | XIRR | Volatility | Sharpe vs Liquid | Max drawdown |",
         "|---|---|---|---|---|---|"]
for liquid, m in rows:
    lines.append(f"| {liquid:.0%} | ₹{m['Final value']:,.0f} | {m['XIRR']:.2%} | {m['Volatility']:.2%} | "
                 f"{m['Sharpe vs Liquid']:.3f} | {m['Max drawdown']:.2%} |")
lines.append(f"\n**Chosen: {best:.0%}** (frozen in fixed_optimizer.py before the 2020-2025 test).")
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / "selection_2010_2019.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
