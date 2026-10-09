"""Step 8f: what could an investor who starts on 1 Jan 2026 expect?

    python 08_forward_test/outlook_2026.py      -> results/outlook_2026.md

Part 1, expectation (uses data to Dec 2025 only): every SIP of 3, 5 and 10 years that could be
started between Feb 2010 and Dec 2025, for each strategy. The spread of their outcomes is the
honest answer to "what kind of profit could I look at": a typical case, a bad case, a good case.

Part 2, live check (uses Jan-Sep 2026, published after the study's data cut-off and never used
to build or choose anything): what actually happened to a ₹10,000/month SIP started in Jan 2026.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from run_forward import all_strategies  # noqa: E402
from sip import analysis  # noqa: E402
from sip.engine import contribution_schedule, run_sip  # noqa: E402
from sip.forward_data import PRIMARY, RAW, _undo_splits, read_combined  # noqa: E402
from sip.report import AMOUNT, COST_BPS, LOOKBACK  # noqa: E402

SHOW = ["Equal-weight SIP", "Fixed Optimized SIP", "60/20/20 annual rebal", "Equity SIP", "Optimized SIP"]


def fv_from_xirr(x: float, n: int, amount: float = AMOUNT) -> float:
    """Value after n monthly instalments growing at XIRR x (instalments at month starts)."""
    return float(sum(amount * (1 + x) ** ((n - k) / 12) for k in range(n)))


def live_returns() -> pd.DataFrame:
    nav = pd.read_csv(RAW / "amfi_month_end_nav_2026_live.csv", index_col="Month")
    nav.index = pd.PeriodIndex(nav.index, freq="M")
    r = nav.astype(float).pct_change(fill_method=None).apply(_undo_splits).loc["2026-01":]
    return pd.DataFrame({a: r[c].mean(axis=1) for a, c in PRIMARY.items()})[["Nifty", "Gold", "Liquid"]]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    R = read_combined()
    strategies = all_strategies(R)
    L = ["# An investor starting on 1 January 2026\n"]

    # ------------------------------------------------------------- part 1: expectation
    L += ["## 1. What to expect (from every past SIP, Feb 2010 – Dec 2025)\n",
          "For each horizon, every SIP of that length that fits inside Feb 2010 – Dec 2025 was "
          "run (one starting each month). ₹ figures are what ₹10,000/month would have grown to "
          "at the typical (median), worst and best XIRR seen.\n"]
    for years in (3, 5, 10):
        roll = analysis.rolling_windows(R, strategies, "2010-02", years=years)
        n = years * 12
        g = roll.groupby("Strategy")["XIRR"]
        L.append(f"### {years}-year SIP (₹{AMOUNT * n:,.0f} paid in, {roll['start'].nunique()} start months)\n")
        L.append("| Strategy | Worst XIRR | Median XIRR | Best XIRR | Worst value | Median value | Best value | Windows that lost money |")
        L.append("|---|---|---|---|---|---|---|---|")
        for s in SHOW:
            x = g.get_group(s)
            lost = int((x < 0).sum())
            L.append(f"| {s} | {x.min():.1%} | {x.median():.1%} | {x.max():.1%} | "
                     f"₹{fv_from_xirr(x.min(), n):,.0f} | ₹{fv_from_xirr(x.median(), n):,.0f} | "
                     f"₹{fv_from_xirr(x.max(), n):,.0f} | {lost} of {len(x)} |")
        L.append("")

    # ------------------------------------------------------------- part 2: live check
    live = live_returns()
    R26 = pd.concat([R, live])
    strategies26 = all_strategies(R26)
    idx = live.index
    contrib = contribution_schedule(idx, AMOUNT)
    paid = contrib.sum()
    L += [f"## 2. Live check: what actually happened, Jan – {idx[-1].strftime('%b %Y')}\n",
          "Same funds as the 2020-2025 data, published after the study's cut-off. Nothing here "
          "was used to build or choose a strategy.\n",
          "| Month | Nifty | Gold | Liquid |", "|---|---|---|---|"]
    for m, row in live.iterrows():
        L.append(f"| {m.strftime('%b %Y')} | {row['Nifty']:+.1%} | {row['Gold']:+.1%} | {row['Liquid']:+.1%} |")
    L += ["", f"₹10,000 on the 1st of each month, Jan – {idx[-1].strftime('%b %Y')} (₹{paid:,.0f} paid in), "
          f"value on {idx[-1].to_timestamp(how='end').strftime('%d %b %Y')}:\n",
          "| Strategy | Value | Profit | Profit % of money paid in |", "|---|---|---|---|"]
    rows = []
    for s in strategies26:
        res = run_sip(R26, s, contrib, COST_BPS)
        v = float(res.total.iloc[-1])
        rows.append((s.name, v))
    for name, v in sorted(rows, key=lambda x: -x[1]):
        L.append(f"| {name} | ₹{v:,.0f} | {'+' if v >= paid else '−'}₹{abs(v - paid):,.0f} | {(v - paid) / paid:+.1%} |")
    L.append("")
    (HERE / "results" / "outlook_2026.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
