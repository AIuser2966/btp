"""Forward-period data (Jan 2020 – Dec 2025) for the out-of-sample test in 08_forward_test/.

The original study's daily file ends in Dec 2019. For 2020–2025 the three assets come from the
month-end NAVs of real Indian funds that track them (AMFI daily NAV archive, mirrored at
github.com/captn3m0/historical-mf-data):

* Nifty  = average of two Nifty 50 index funds (UTI, HDFC; direct growth plans).
           These hold the 50 shares and reinvest dividends, i.e. the Nifty 50 total return
           less a small fund cost (~0.2%/yr).
* Gold   = average of two gold ETFs (HDFC Gold ETF, Nippon India ETF Gold BeES): the rupee
           price of gold an Indian investor actually pays.
* Liquid = average of two liquid funds (SBI, ICICI Prudential; direct growth): the rate on
           T-bills / money-market paper that the original Liquid index approximates.

The other funds in raw/ (a third Nifty tracker, two more gold ETFs, two more liquid funds) and
the published Nifty closes, international gold price and T-bill yields are used only to
cross-check these series (see 08_forward_test/verify_data.py).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import read_returns_table

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_forward_test" / "raw"
FORWARD_FILE = ROOT / "08_forward_test" / "forward_returns_2020_2025.csv"
COMBINED_FILE = ROOT / "08_forward_test" / "monthly_returns_2000_2025.csv"

FORWARD_START, FORWARD_END = "2020-01", "2025-12"

PRIMARY = {"Nifty": ["UTI_N50_IF", "HDFC_N50_IF"],
           "Gold": ["HDFC_GoldETF", "GoldBeES_new"],
           "Liquid": ["SBI_Liq", "ICICI_Liq"]}
CHECKS = {"Nifty": ["Kotak_N50ETF"],
          "Gold": ["Kotak_GoldETF", "ICICI_GoldETF"],
          "Liquid": ["Nippon_Liq", "HDFC_Liq"]}


def _undo_splits(r: pd.Series) -> pd.Series:
    """A unit split (e.g. 1:10) or face-value change shows up as a -90% / -99% / +9,900% 'return'.
    Undo it by the nearest power of ten; real monthly moves of these funds are far below 50%."""
    r = r.copy()
    for i, v in r.items():
        if pd.notna(v) and abs(v) > 0.5:
            factor = 10.0 ** round(np.log10(1.0 / (1.0 + v)))
            r[i] = (1.0 + v) * factor - 1.0
    return r


def fund_navs() -> pd.DataFrame:
    nav = pd.read_csv(RAW / "amfi_month_end_nav.csv", index_col="Month")
    nav.index = pd.PeriodIndex(nav.index, freq="M")
    return nav.astype(float)


def fund_returns() -> pd.DataFrame:
    """Monthly return of every fund in raw/, splits undone (month-end NAV to month-end NAV)."""
    return fund_navs().pct_change(fill_method=None).apply(_undo_splits)


def forward_returns(sources: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Jan 2020 – Dec 2025 monthly returns: the average of each asset's source funds."""
    sources = sources or PRIMARY
    fr = fund_returns().loc[FORWARD_START:FORWARD_END]
    out = pd.DataFrame({a: fr[cols].mean(axis=1) for a, cols in sources.items()})
    out.index.name = "Month"
    return out[["Nifty", "Gold", "Liquid"]]


def combined_returns(sources: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Original Feb 2000 – Dec 2019 table followed by the forward Jan 2020 – Dec 2025 table."""
    old = read_returns_table()
    new = forward_returns(sources)
    out = pd.concat([old.loc[:"2019-12"], new])
    out.index.name = "Month"
    return out


def read_combined() -> pd.DataFrame:
    df = pd.read_csv(COMBINED_FILE, index_col="Month")
    df.index = pd.PeriodIndex(df.index, freq="M")
    return df
