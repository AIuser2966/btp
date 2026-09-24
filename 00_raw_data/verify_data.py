"""Check the raw data against independent public sources (needs internet).

    python 00_raw_data/verify_data.py

1. Nifty 50 closes  vs two NSE-sourced datasets on GitHub (every overlapping trading day).
2. Gold (USD)       vs the monthly gold-price dataset (datasets/gold-prices, monthly average).
3. USD/INR          is taken directly from FRED (DEXINUS), so it is the reference itself.
4. Liquid           implied annual rate (should step weekly like 91-day T-bill auctions).
"""

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sip.data import liquid_implied_rate, load_daily, month_end  # noqa: E402

SOURCES = {
    "nse_1990_2019": "https://raw.githubusercontent.com/Sdaas/nifty-analysis/master/NIFTY%2050_Data.csv",
    "nse_2015_2019": "https://raw.githubusercontent.com/abulbasar/data/master/nifty50-index.csv",
    "gold_monthly": "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv",
}


def fetch(url: str) -> pd.DataFrame:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return pd.read_csv(io.BytesIO(resp.read()))


def main():
    daily = load_daily()

    # 1. Nifty closes, day by day
    a = fetch(SOURCES["nse_1990_2019"])
    a.index = pd.to_datetime(a["Date"], format="%d %b %Y")
    b = fetch(SOURCES["nse_2015_2019"])
    b.index = pd.to_datetime(b["Date"], format="%d-%b-%y")
    for name, ref in (("NSE data 1990-2019", a["Close"]), ("NSE data 2015-2019", b["Close"])):
        both = pd.concat([daily["Nifty"], ref.astype(float).sort_index()], axis=1,
                         join="inner").loc["2000":"2019"]
        diff = (both.iloc[:, 0] / both.iloc[:, 1] - 1).abs()
        print(f"Nifty vs {name}: {len(both)} days, {(diff < 1e-9).mean():.2%} exact, "
              f"max difference {diff.max():.3%}")
        print("   days that differ:", [d.date().isoformat() for d in diff[diff > 1e-6].index])

    # 2. Gold, monthly average vs reference monthly average
    g = fetch(SOURCES["gold_monthly"])
    g.index = pd.PeriodIndex(pd.to_datetime(g["Date"]), freq="M")
    mine = daily["Gold"].resample("ME").mean()
    mine.index = mine.index.to_period("M")
    both = pd.concat([mine, g["Price"]], axis=1, join="inner").loc["2000":"2019"]
    diff = (both.iloc[:, 0] / both.iloc[:, 1] - 1).abs()
    print(f"Gold (USD) monthly average vs reference: {len(both)} months, "
          f"mean difference {diff.mean():.2%}, max {diff.max():.2%}")

    # 4. Liquid implied rate
    rate = liquid_implied_rate()
    by_year = rate.groupby(rate.index.year).mean()
    print("Liquid implied rate, yearly average:", (by_year * 100).round(2).to_dict())
    print("Month-end Liquid values used:", month_end(daily["Liquid"]).loc["2010-01":"2010-02"]
          .round(4).to_dict())


if __name__ == "__main__":
    main()
