"""Performance metrics for SIP back-tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .engine import SIPResult

MONTHS = 12


def xirr(cashflows: np.ndarray, years: np.ndarray) -> float:
    """Annualised money-weighted return: the rate r with sum(cf / (1+r)^t) = 0.

    ``cashflows`` are from the investor's view (instalments negative, final value positive)
    and ``years`` is the time of each flow in years from the first one.
    """
    def npv(r):
        return np.sum(cashflows / (1.0 + r) ** years)
    return brentq(npv, -0.99, 10.0, xtol=1e-10)


def sip_xirr(res: SIPResult) -> float:
    n = len(res.contributions)
    # instalments at the start of each month, final value at the end of the last month
    cfs = np.append(-res.contributions.values, res.total.iloc[-1])
    years = np.append(np.arange(n), n) / MONTHS
    return xirr(cfs, years)


def max_drawdown(series: pd.Series) -> float:
    peak = series.cummax()
    return float((series / peak - 1.0).min())


def summarise(res: SIPResult, rf: float = 0.0) -> dict:
    r = res.twr
    ann_ret = (1.0 + r).prod() ** (MONTHS / len(r)) - 1.0
    ann_vol = r.std() * np.sqrt(MONTHS)
    excess = r - rf / MONTHS
    downside = np.sqrt((np.minimum(excess, 0.0) ** 2).mean()) * np.sqrt(MONTHS)
    growth = (1.0 + r).cumprod()
    mdd = max_drawdown(growth)
    invested = res.contributions.sum()
    final = res.total.iloc[-1]
    return {
        "Strategy": res.name,
        "Invested": invested,
        "Final value": final,
        "Wealth multiple": final / invested,
        "XIRR": sip_xirr(res),
        "TWR CAGR": ann_ret,
        "Volatility": ann_vol,
        "Sharpe": excess.mean() * MONTHS / ann_vol,
        "Sortino": excess.mean() * MONTHS / downside,
        "Max drawdown": mdd,
        "Calmar": ann_ret / abs(mdd),
        # Largest fall in rupee/dollar wealth an investor actually saw in the account
        "Worst wealth drop": max_drawdown(res.total),
        # Share of the average portfolio sold per year (a proxy for capital-gains tax events)
        "Annual sell turnover": res.sold.sum() / res.total.mean() / (len(r) / MONTHS),
        # Trading costs as a yearly drag on the average portfolio
        "Annual cost drag": res.costs.sum() / res.total.mean() / (len(r) / MONTHS),
    }


def summary_table(results: list[SIPResult], rf: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame([summarise(r, rf) for r in results]).set_index("Strategy")
