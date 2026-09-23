"""Build monthly total-return series for the asset universe.

Bundled data (``data/raw``) comes from the public "datasets" collection on GitHub:

* ``sp500_shiller.csv`` – Robert Shiller's monthly S&P 500 price and dividend series.
* ``us10y_yield.csv``   – US 10-year Treasury constant-maturity yield (FRED, monthly).
* ``gold_usd.csv``      – Monthly gold price in USD per troy ounce.
* ``usdinr.csv``        – Monthly INR per USD exchange rate (FRED).

From these we derive three investable, total-return assets:

* ``Equity`` – S&P 500 with dividends reinvested.
* ``Bonds``  – a synthetic constant-maturity 10-year Treasury fund (bought at par
  each month and re-priced one month later at the new yield, plus the coupon).
* ``Gold``   – spot gold.

Optionally the series are converted into Indian Rupees so the back-test
represents an Indian investor running a rupee SIP.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ASSETS = ["Equity", "Bonds", "Gold"]


def _to_month(index) -> pd.PeriodIndex:
    return pd.PeriodIndex(pd.to_datetime(index), freq="M")


def equity_total_return(raw_dir: Path = RAW_DIR) -> pd.Series:
    df = pd.read_csv(raw_dir / "sp500_shiller.csv")
    df.index = _to_month(df["Date"])
    price = df["SP500"].astype(float)
    # Shiller's dividend column is an annualised amount. The latest months are
    # published as 0 until the data is revised, so carry the last dividend yield forward.
    div_yield = (df["Dividend"] / price).replace(0.0, np.nan).ffill()
    monthly_div = div_yield.shift(1) * price.shift(1) / 12.0
    ret = (price + monthly_div) / price.shift(1) - 1.0
    return ret.rename("Equity")


def bond_total_return(raw_dir: Path = RAW_DIR, maturity: float = 10.0) -> pd.Series:
    """Monthly total return of a constant-maturity par bond fund.

    At the start of month t a new par bond is bought with coupon = yield(t-1).
    One month later it has ``maturity - 1/12`` years left and is priced at yield(t).
    Return = price change + one month of coupon accrual.
    """
    df = pd.read_csv(raw_dir / "us10y_yield.csv")
    df.index = _to_month(df["Date"])
    y = df["Rate"].astype(float) / 100.0
    coupon = y.shift(1)
    price = par_bond_price(coupon, y, maturity - 1.0 / 12.0)
    ret = price - 1.0 + coupon / 12.0
    return ret.rename("Bonds")


def par_bond_price(coupon, yld, years):
    """Price (per 1 face) of a semi-annual coupon bond."""
    n = 2.0 * years
    c = np.asarray(coupon) / 2.0
    r = np.asarray(yld) / 2.0
    disc = (1.0 + r) ** (-n)
    return c / r * (1.0 - disc) + disc


def gold_return(raw_dir: Path = RAW_DIR) -> pd.Series:
    df = pd.read_csv(raw_dir / "gold_usd.csv")
    df.index = _to_month(df["Date"])
    return df["Price"].astype(float).pct_change().rename("Gold")


def usdinr(raw_dir: Path = RAW_DIR) -> pd.Series:
    df = pd.read_csv(raw_dir / "usdinr.csv")
    df.index = _to_month(df["Date"])
    return df["Exchange rate"].astype(float).rename("USDINR")


def load_returns(currency: str = "USD", start: str = "1973-02",
                 end: str | None = None, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Monthly total returns (decimal) for Equity, Bonds and Gold."""
    rets = pd.concat([equity_total_return(raw_dir), bond_total_return(raw_dir),
                      gold_return(raw_dir)], axis=1)
    currency = currency.upper()
    if currency == "INR":
        # A USD asset held by a rupee investor also earns the change in USD/INR.
        fx = usdinr(raw_dir)
        rets = (1.0 + rets).mul(fx / fx.shift(1), axis=0) - 1.0
    elif currency != "USD":
        raise ValueError(f"unsupported currency {currency!r}")
    rets = rets.loc[start:end].dropna()
    return rets[ASSETS]


def load_yahoo(tickers: dict[str, str], start: str = "2005-01-01") -> pd.DataFrame:
    """Optional loader for users with internet access, e.g. Indian ETFs::

        load_yahoo({"Equity": "NIFTYBEES.NS", "Gold": "GOLDBEES.NS",
                    "Bonds": "LTGILTBEES.NS"})

    Returns monthly total returns built from adjusted month-end closes.
    """
    import yfinance as yf  # imported lazily: optional dependency

    px = yf.download(list(tickers.values()), start=start, auto_adjust=True,
                     progress=False)["Close"]
    px = px.rename(columns={v: k for k, v in tickers.items()})
    monthly = px.resample("ME").last()
    monthly.index = monthly.index.to_period("M")
    return monthly.pct_change().dropna()[list(tickers)]
