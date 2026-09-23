"""Portfolio weight optimisers and the walk-forward (no look-ahead) scheduler."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MONTHS = 12


def _solve(objective, n, lo, hi):
    x0 = np.full(n, 1.0 / n)
    res = minimize(objective, x0, method="SLSQP", bounds=[(lo, hi)] * n,
                   constraints=({"type": "eq", "fun": lambda w: w.sum() - 1.0},),
                   options={"ftol": 1e-12, "maxiter": 500})
    w = np.clip(res.x, lo, hi)
    return w / w.sum()


def min_variance(rets: pd.DataFrame, lo=0.0, hi=1.0) -> np.ndarray:
    cov = rets.cov().values
    return _solve(lambda w: w @ cov @ w, cov.shape[0], lo, hi)


def max_sharpe(rets: pd.DataFrame, lo=0.0, hi=1.0, rf: float = 0.0) -> np.ndarray:
    mu = rets.mean().values - rf / MONTHS
    cov = rets.cov().values
    return _solve(lambda w: -(w @ mu) / np.sqrt(w @ cov @ w), len(mu), lo, hi)


def risk_parity(rets: pd.DataFrame, lo=0.0, hi=1.0) -> np.ndarray:
    """Equal risk contribution: every asset adds the same share of portfolio variance."""
    cov = rets.cov().values
    n = cov.shape[0]

    def objective(w):
        rc = w * (cov @ w)
        return ((rc - rc.mean()) ** 2).sum() * 1e8

    return _solve(objective, n, lo, hi)


OPTIMISERS = {"min_variance": min_variance, "max_sharpe": max_sharpe,
              "risk_parity": risk_parity}


def fixed_weights(index: pd.PeriodIndex, weights: dict[str, float]) -> pd.DataFrame:
    """The same target weights every month."""
    return pd.DataFrame([weights] * len(index), index=index)


def walk_forward_weights(rets: pd.DataFrame, method: str, lookback: int = 120,
                         reoptimise_every: int = 12, lo: float = 0.10,
                         hi: float = 0.70) -> pd.DataFrame:
    """Target weights for every month using only data available before that month.

    Every ``reoptimise_every`` months the optimiser is fitted on the previous
    ``lookback`` months of returns. Months without a full look-back window
    get NaN weights (strategies must not start before then).
    """
    fn = OPTIMISERS[method]
    out = pd.DataFrame(np.nan, index=rets.index, columns=rets.columns)
    current = None
    for i in range(len(rets)):
        if i < lookback:
            continue
        if current is None or (i - lookback) % reoptimise_every == 0:
            current = fn(rets.iloc[i - lookback:i], lo=lo, hi=hi)
        out.iloc[i] = current
    return out


def weight_grid(assets: list[str], step: float = 0.10, lo: float = 0.0,
                hi: float = 1.0) -> list[dict[str, float]]:
    """All weight combinations on a grid that sum to 1 (used for the in-sample search)."""
    k = int(round(1 / step))
    grid = []
    for combo in itertools.product(range(k + 1), repeat=len(assets) - 1):
        last = k - sum(combo)
        if last < 0:
            continue
        w = [c * step for c in combo] + [last * step]
        if all(lo - 1e-9 <= x <= hi + 1e-9 for x in w):
            grid.append(dict(zip(assets, np.round(w, 4))))
    return grid
