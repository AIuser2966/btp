"""Step 0: turn the raw daily files in ./raw into the monthly returns table every strategy uses.

    python 00_raw_data/build_returns.py

Writes monthly_returns.csv (239 months, Feb 2000 - Dec 2019, x 3 assets: Nifty, Gold, Liquid)
and monthly_prices.csv (the month-end values the returns are computed from).
The formulas are explained in this folder's README.md and implemented in sip/data.py.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sip.data import (DATA_DIR, gold_inr_price, load_daily, load_returns,  # noqa: E402
                      load_usdinr_daily, month_end, returns_table_path)

daily = load_daily()
prices = pd.DataFrame({
    "Nifty (price index)": month_end(daily["Nifty"]),
    "Gold (USD/oz)": month_end(daily["Gold"]),
    "USD/INR": month_end(load_usdinr_daily()),
    "Gold (INR/oz)": gold_inr_price(),
    "Liquid (index)": month_end(daily["Liquid"]),
}).loc["2000-01":"2019-12"]
prices.rename_axis("Month").to_csv(DATA_DIR / "monthly_prices.csv", float_format="%.4f")

rets = load_returns()
rets.rename_axis("Month").to_csv(returns_table_path(), float_format="%.8f")

# Correlation of monthly returns: rho(i, j) = Cov(r_i, r_j) / (sigma_i * sigma_j)
first_window = rets.loc["2000-02":"2010-01"]        # the 120 months the optimisers first see
corr = first_window.corr()
corr.to_csv(DATA_DIR / "correlations_2000_2010.csv", float_format="%.4f")
print("Correlations Feb 2000 - Jan 2010:\n", corr.round(2))
print(f"{len(rets)} months ({rets.index[0]} to {rets.index[-1]}) -> {returns_table_path().name}")
print("Annual return:", ((1 + rets).prod() ** (12 / len(rets)) - 1).round(4).to_dict())
print("Annual volatility:", (rets.std() * 12 ** 0.5).round(4).to_dict())
