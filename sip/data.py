"""Build the monthly returns table (Nifty, Gold, Liquid) for an Indian rupee SIP, 2000-2019.

Raw files in ``00_raw_data/raw/``:

* ``final_market_data_2000_2019.csv`` – the project's daily data (calendar days):
    - ``Nifty``  – Nifty 50 price index (NSE closing values; no dividends)
    - ``Gold``   – gold price in US dollars per troy ounce
    - ``Liquid`` – a liquid-fund index that accrues the 91-day T-bill yield daily
* ``usdinr_daily_fred.csv`` – rupees per US dollar, daily (FRED series DEXINUS).

From these we build three rupee total-return assets:

* ``Nifty``  – price return + dividend yield (NIFTY_DIVIDEND_YIELD / 12 per month)
* ``Gold``   – gold converted to rupees at the month-end exchange rate
* ``Liquid`` – the liquid-fund index as given
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "00_raw_data" / "raw"
DATA_DIR = RAW_DIR.parent
MARKET_FILE = "final_market_data_2000_2019.csv"
FX_FILE = "usdinr_daily_fred.csv"
ASSETS = ["Nifty", "Gold", "Liquid"]

# Nifty 50 dividend yield, per year. NSE does not include dividends in the price index;
# its published dividend yield has historically been 1-2% (1.35% in the May 2026
# factsheet). 1.3% is used for every month (assumption; see 00_raw_data/README.md).
NIFTY_DIVIDEND_YIELD = 0.013


def load_daily(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """The daily market file: Nifty, Gold (USD), Liquid."""
    return pd.read_csv(raw_dir / MARKET_FILE, index_col="Date", parse_dates=True)


def load_usdinr_daily(raw_dir: Path = RAW_DIR) -> pd.Series:
    fx = pd.read_csv(raw_dir / FX_FILE, index_col="Date", parse_dates=True)["USDINR"]
    return fx.dropna()                                     # US holidays have no quote


def month_end(series: pd.Series) -> pd.Series:
    """Last available value of each calendar month, indexed by month (e.g. 2010-02)."""
    out = series.dropna().resample("ME").last()
    out.index = out.index.to_period("M")
    return out


def nifty_total_return(raw_dir: Path = RAW_DIR,
                       dividend_yield: float = NIFTY_DIVIDEND_YIELD) -> pd.Series:
    """r_t = P_t / P_{t-1} - 1 + dy / 12   (price return + one month of dividend)."""
    price = month_end(load_daily(raw_dir)["Nifty"])
    ret = price / price.shift(1) - 1 + dividend_yield / 12
    return ret.rename("Nifty")


def gold_inr_price(raw_dir: Path = RAW_DIR) -> pd.Series:
    """Gold in rupees per ounce = gold in USD x rupees per USD (both at month end)."""
    gold_usd = month_end(load_daily(raw_dir)["Gold"])
    fx = month_end(load_usdinr_daily(raw_dir))
    return (gold_usd * fx).rename("Gold")


def gold_return(raw_dir: Path = RAW_DIR) -> pd.Series:
    """r_t = G_INR,t / G_INR,t-1 - 1  =  (1 + r_USD,t) x FX_t / FX_t-1 - 1."""
    g = gold_inr_price(raw_dir)
    return (g / g.shift(1) - 1).rename("Gold")


def liquid_return(raw_dir: Path = RAW_DIR) -> pd.Series:
    """r_t = L_t / L_{t-1} - 1, where the index grows daily by (1 + y / 365)."""
    level = month_end(load_daily(raw_dir)["Liquid"])
    return (level / level.shift(1) - 1).rename("Liquid")


def liquid_implied_rate(raw_dir: Path = RAW_DIR) -> pd.Series:
    """Annual rate implied by the daily Liquid index: y = (L_d / L_(d-1) - 1) x 365.

    Used to check the Liquid column: it moves in weekly steps, like 91-day T-bill auctions.
    """
    level = load_daily(raw_dir)["Liquid"]
    return ((level / level.shift(1) - 1) * 365).rename("Liquid implied rate")


def load_returns(start: str = "2000-02", end: str = "2019-12",
                 raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Monthly rupee total returns (decimal) for Nifty, Gold and Liquid."""
    rets = pd.concat([nifty_total_return(raw_dir), gold_return(raw_dir),
                      liquid_return(raw_dir)], axis=1)
    return rets.loc[start:end].dropna()[ASSETS]


def returns_table_path() -> Path:
    return DATA_DIR / "monthly_returns.csv"


def read_returns_table() -> pd.DataFrame:
    """The prepared returns table from ``00_raw_data/`` (built by build_returns.py).

    Every strategy reads this one file, so all six use exactly the same data.
    """
    df = pd.read_csv(returns_table_path(), index_col="Month")
    df.index = pd.PeriodIndex(df.index, freq="M")
    return df[ASSETS]
