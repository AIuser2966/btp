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
    return max_sharpe_mu(rets.mean().values - rf / MONTHS, rets.cov().values, lo, hi)


def max_sharpe_mu(mu: np.ndarray, cov: np.ndarray, lo=0.0, hi=1.0) -> np.ndarray:
    """Max-Sharpe weights for given expected (excess) returns and covariance."""
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
    fn = OPTIMISERS[method] if isinstance(method, str) else method
    out = pd.DataFrame(np.nan, index=rets.index, columns=rets.columns)
    current = None
    for i in range(len(rets)):
        if i < lookback:
            continue
        if current is None or (i - lookback) % reoptimise_every == 0:
            current = fn(rets.iloc[i - lookback:i], lo=lo, hi=hi)
        out.iloc[i] = current
    return out


def optimized_cash_buffer(rets: pd.DataFrame, lo: float = 0.10, hi: float = 0.70,
                          liquid: float = 0.20, cash: str = "Liquid") -> np.ndarray:
    """Fixed Optimized SIP: Liquid is treated as cash, not as an asset to optimise.

    Liquid gets a fixed share ``liquid``. The rest is split between the risky assets by
    ½ risk parity + ½ max Sharpe, where max Sharpe uses returns ABOVE Liquid
    (mean(r_i - r_Liquid)), so cash can no longer look like a free lunch.
    Each risky asset stays between ``lo`` and ``hi`` of the WHOLE portfolio.
    """
    risky = [c for c in rets.columns if c != cash]
    sleeve = 1.0 - liquid
    lo_s, hi_s = lo / sleeve, min(hi / sleeve, 1.0 - lo / sleeve)
    excess_mu = (rets[risky].sub(rets[cash], axis=0)).mean().values
    rp = risk_parity(rets[risky], lo_s, hi_s)
    ms = max_sharpe_mu(excess_mu, rets[risky].cov().values, lo_s, hi_s)
    w = dict(zip(risky, sleeve * (0.5 * rp + 0.5 * ms)))
    w[cash] = liquid
    return np.array([w[c] for c in rets.columns])


def max_utility(rets: pd.DataFrame, lo: float = 0.10, hi: float = 0.70, lam: float = 4.0,
                cash: str = "Liquid") -> np.ndarray:
    """Mean-variance utility: maximise  U = w'(mu - mu_cash) - (lam / 2) w' Sigma w   (yearly).

    The Lagrangian form of Markowitz (1952): lam is the risk-aversion multiplier. Returns are
    measured ABOVE the cash asset (Liquid), so Liquid's share is decided by lam itself
    (Tobin 1958): a cautious investor (large lam) holds more of it, a bold one (small lam) less.
    """
    mu = (rets.sub(rets[cash], axis=0)).mean().values * MONTHS      # yearly excess returns
    cov = rets.cov().values * MONTHS                                 # yearly covariance
    return _solve(lambda w: -(w @ mu - 0.5 * lam * (w @ cov @ w)), len(mu), lo, hi)


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
