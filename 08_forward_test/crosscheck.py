"""Step 8e: cross-check the 2020-2025 results once, two independent ways.

    python 08_forward_test/crosscheck.py      -> results/crosscheck.md

A. Different data: rebuild 2020-2025 from the funds NOT used for the main series
   (Kotak Nifty 50 ETF; Kotak + ICICI gold ETFs; Nippon + HDFC liquid funds) and re-run all
   seven strategies. If the conclusions hold, they do not depend on which funds we picked.
B. Different code: recompute the three fixed-mix strategies (1-3) with a short independent
   loop and an independent XIRR (bisection), without sip/engine.py or sip/metrics.py.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from run_forward import COLS, all_strategies, run_period  # noqa: E402
from sip.forward_data import CHECKS, FORWARD_END, FORWARD_START, PRIMARY, combined_returns, read_combined  # noqa: E402
from sip.report import fmt  # noqa: E402

lines = ["# Cross-check of the 2020-2025 results\n"]

# ---------------------------------------------------------------- A: alternative funds
R = read_combined()
_, main_t, _, _ = run_period(R, all_strategies(R), FORWARD_START, FORWARD_END)
alt_sources = {"Nifty": CHECKS["Nifty"],
               # Kotak/ICICI gold lack Oct 2020; HDFC fills that one month
               "Gold": CHECKS["Gold"] + ["HDFC_GoldETF"],
               "Liquid": CHECKS["Liquid"]}
R2 = combined_returns(alt_sources)
_, alt_t, _, _ = run_period(R2, all_strategies(R2), FORWARD_START, FORWARD_END)
cmp = pd.DataFrame({"XIRR (main data)": main_t["XIRR"], "XIRR (other funds)": alt_t["XIRR"],
                    "Sharpe vs Liquid (main)": main_t["Sharpe vs Liquid"],
                    "Sharpe vs Liquid (other funds)": alt_t["Sharpe vs Liquid"]})
cmp["Rank by Sharpe vs Liquid (main)"] = main_t["Sharpe vs Liquid"].rank(ascending=False).astype(int)
cmp["Rank (other funds)"] = alt_t["Sharpe vs Liquid"].rank(ascending=False).astype(int)
cmp["Rank by XIRR (main)"] = main_t["XIRR"].rank(ascending=False).astype(int)
cmp["Rank by XIRR (other funds)"] = alt_t["XIRR"].rank(ascending=False).astype(int)
lines += ["## A. Same test, built from different funds\n",
          f"Main: {PRIMARY}. Other: {alt_sources}.\n",
          cmp.to_markdown(floatfmt=".4f"),
          f"\nLargest XIRR difference: {(cmp.iloc[:, 0] - cmp.iloc[:, 1]).abs().max():.2%}. "
          f"Winner by Sharpe vs Liquid: main = {main_t['Sharpe vs Liquid'].idxmax()}, "
          f"other funds = {alt_t['Sharpe vs Liquid'].idxmax()}. "
          f"Highest XIRR: main = {main_t['XIRR'].idxmax()}, other funds = {alt_t['XIRR'].idxmax()}.\n"]

# ---------------------------------------------------------------- B: independent code
r = R.loc[FORWARD_START:FORWARD_END].values           # Nifty, Gold, Liquid
mixes = {"Equity SIP": (np.array([1.0, 0, 0]), None),
         "Equal-weight SIP": (np.array([1, 1, 1]) / 3, None),
         "60/20/20 annual rebal": (np.array([0.6, 0.2, 0.2]), 12)}


def simulate(w, every):
    h = np.zeros(3)
    for t in range(len(r)):
        h = h + 10_000 * w
        traded = 10_000.0
        if every and (t + 1) % every == 0:          # yearly reset, counted from the first month
            new = w * h.sum()
            traded += np.abs(new - h).sum()
            h = new
        h = h * (1 - 0.001 * traded / h.sum())
        h = h * (1 + r[t])
    return h.sum()


def xirr_bisect(final, n):
    lo, hi = -0.5, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        fv = sum(10_000 * (1 + mid) ** ((n - k) / 12) for k in range(n))
        lo, hi = (mid, hi) if fv < final else (lo, mid)
    return mid


rows = []
for name, (w, every) in mixes.items():
    fv = simulate(w, every)
    rows.append({"Strategy": name, "Final value (independent)": fv,
                 "Final value (engine)": main_t.loc[name, "Final value"],
                 "XIRR (independent)": xirr_bisect(fv, len(r)), "XIRR (engine)": main_t.loc[name, "XIRR"]})
b = pd.DataFrame(rows).set_index("Strategy")
lines += ["## B. Fixed mixes recomputed without the project's engine\n", b.to_markdown(floatfmt=",.4f"),
          f"\nLargest final-value difference: ₹{(b.iloc[:, 0] - b.iloc[:, 1]).abs().max():,.2f}.\n"]
(HERE / "results" / "crosscheck.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
