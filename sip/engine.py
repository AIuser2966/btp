"""Month-by-month SIP simulator.

Timeline for each month t:

1. The SIP instalment arrives at the start of the month.
2. It is invested according to the strategy's *contribution rule*:
   ``pro_rata`` splits it by the target weights, ``smart`` sends it to the
   assets that are furthest below target (rebalancing with new money, no selling).
3. Optionally the whole portfolio is rebalanced back to target
   (``calendar`` every N months, or ``band`` when any weight drifts too far).
4. Every trade pays ``cost_bps`` of the traded amount.
5. The month's asset returns are applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Strategy:
    name: str
    target: pd.DataFrame            # target weights per month (rows sum to 1)
    contribution: str = "pro_rata"  # "pro_rata" | "smart"
    rebalance: str = "none"         # "none" | "calendar" | "band"
    rebalance_every: int = 12       # months, for "calendar"
    band: float = 0.05              # absolute weight drift, for "band"
    description: str = ""


@dataclass
class SIPResult:
    name: str
    values: pd.DataFrame            # end-of-month value held in each asset
    contributions: pd.Series        # instalment paid at the start of each month
    twr: pd.Series                  # monthly time-weighted portfolio return
    bought: pd.Series               # gross purchases each month
    sold: pd.Series                 # gross sales each month (taxable events)
    costs: pd.Series
    meta: dict = field(default_factory=dict)

    @property
    def total(self) -> pd.Series:
        return self.values.sum(axis=1)

    @property
    def weights(self) -> pd.DataFrame:
        return self.values.div(self.total, axis=0)


def contribution_schedule(index: pd.PeriodIndex, amount: float = 10_000.0,
                          step_up: float = 0.0) -> pd.Series:
    """Monthly instalments; ``step_up`` raises the instalment every 12 months (e.g. 0.10)."""
    years = np.arange(len(index)) // 12
    return pd.Series(amount * (1.0 + step_up) ** years, index=index, name="contribution")


def _smart_split(holdings: np.ndarray, target: np.ndarray, cash: float) -> np.ndarray:
    """Allocate new cash to under-weight assets first, then pro-rata to target."""
    total = holdings.sum() + cash
    gap = np.maximum(target * total - holdings, 0.0)
    need = gap.sum()
    if need <= 1e-12:
        return target * cash
    if need >= cash:
        return gap / need * cash
    return gap + target * (cash - need)


def run_sip(returns: pd.DataFrame, strategy: Strategy, contributions: pd.Series,
            cost_bps: float = 10.0) -> SIPResult:
    idx = contributions.index
    rets = returns.loc[idx].values
    targets = strategy.target.reindex(idx)[returns.columns].values
    if np.isnan(targets).any():
        raise ValueError(f"{strategy.name}: target weights missing inside the SIP window")
    cost_rate = cost_bps / 1e4
    n_t, n_a = rets.shape

    h = np.zeros(n_a)
    values = np.empty((n_t, n_a))
    twr = np.empty(n_t)
    bought = np.zeros(n_t)
    sold = np.zeros(n_t)
    costs = np.zeros(n_t)
    months_since_rebal = 0

    for t in range(n_t):
        w = targets[t]
        cash = contributions.iloc[t]

        # 1-2. invest the instalment
        split = _smart_split(h, w, cash) if strategy.contribution == "smart" else w * cash
        buys = split.copy()
        h = h + split

        # 3. full rebalance if the rule fires
        months_since_rebal += 1
        do_rebal = False
        if strategy.rebalance == "calendar" and months_since_rebal >= strategy.rebalance_every:
            do_rebal = True
        elif strategy.rebalance == "band" and h.sum() > 0:
            do_rebal = np.abs(h / h.sum() - w).max() > strategy.band
        if do_rebal:
            trade = w * h.sum() - h
            buys += np.maximum(trade, 0.0)
            sold[t] = np.maximum(-trade, 0.0).sum()
            h = w * h.sum()
            months_since_rebal = 0

        # 4. transaction costs, charged pro-rata to holdings
        turnover = np.maximum(buys, 0.0).sum() + sold[t]
        costs[t] = turnover * cost_rate
        start_value = h.sum()
        h = h * (1.0 - costs[t] / start_value)
        bought[t] = np.maximum(buys, 0.0).sum()

        # 5. market moves
        h = h * (1.0 + rets[t])
        values[t] = h
        twr[t] = h.sum() / start_value - 1.0

    return SIPResult(
        name=strategy.name,
        values=pd.DataFrame(values, index=idx, columns=returns.columns),
        contributions=contributions,
        twr=pd.Series(twr, index=idx, name=strategy.name),
        bought=pd.Series(bought, index=idx),
        sold=pd.Series(sold, index=idx),
        costs=pd.Series(costs, index=idx),
        meta={"description": strategy.description},
    )
