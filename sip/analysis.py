"""Robustness checks: rolling SIP windows, in-sample grid search, train/test split."""

from __future__ import annotations

import pandas as pd

from .engine import Strategy, contribution_schedule, run_sip
from .metrics import max_drawdown, sip_xirr, summarise
from .optimize import fixed_weights, weight_grid


def rolling_windows(returns: pd.DataFrame, strategies: list[Strategy], start: str,
                    years: int = 10, step: int = 1, amount: float = 10_000.0,
                    cost_bps: float = 10.0) -> pd.DataFrame:
    """XIRR and worst wealth drop of every ``years``-long SIP starting each ``step`` months."""
    idx = returns.loc[start:].index
    n = years * 12
    rows = []
    for i in range(0, len(idx) - n + 1, step):
        window = idx[i:i + n]
        contrib = contribution_schedule(window, amount)
        for s in strategies:
            res = run_sip(returns, s, contrib, cost_bps)
            rows.append({"start": window[0], "Strategy": s.name,
                         "XIRR": sip_xirr(res),
                         "Worst wealth drop": max_drawdown(res.total)})
    return pd.DataFrame(rows)


def rolling_summary(roll: pd.DataFrame, benchmark: str = "Equity SIP") -> pd.DataFrame:
    xirr = roll.pivot(index="start", columns="Strategy", values="XIRR")
    dd = roll.pivot(index="start", columns="Strategy", values="Worst wealth drop")
    order = list(dict.fromkeys(roll["Strategy"]))
    out = pd.DataFrame({
        "Windows": xirr.count(),
        "Median XIRR": xirr.median(),
        "5th pct XIRR": xirr.quantile(0.05),
        "Worst XIRR": xirr.min(),
        "Best XIRR": xirr.max(),
        "XIRR std": xirr.std(),
        "% windows XIRR < 0": (xirr < 0).mean(),
        f"% windows beating {benchmark}": xirr.gt(xirr[benchmark], axis=0).mean(),
        "Median worst drop": dd.median(),
        "Worst drop (any window)": dd.min(),
    })
    return out.loc[order]


def static_grid(returns: pd.DataFrame, contrib: pd.Series, step: float = 0.10,
                cost_bps: float = 10.0) -> pd.DataFrame:
    """Every static mix on a grid, bought with pro-rata instalments + annual rebalancing."""
    rf = returns["Liquid"] if "Liquid" in returns else None
    rows = []
    for w in weight_grid(list(returns.columns), step):
        s = Strategy(str(w), fixed_weights(contrib.index, w), rebalance="calendar")
        m = summarise(run_sip(returns, s, contrib, cost_bps), rf_returns=rf)
        rows.append({**w, **{k: m[k] for k in
                             ("XIRR", "Volatility", "Sharpe", "Sharpe vs Liquid",
                              "Max drawdown", "Worst wealth drop") if k in m}})
    return pd.DataFrame(rows)


def best_static(grid: pd.DataFrame, assets: list[str], objective: str | None = None) -> dict:
    """Best fixed mix by Sharpe. With a cash-like Liquid asset, Sharpe must be measured
    against Liquid (otherwise 100% Liquid 'wins' with a near-zero denominator)."""
    if objective is None:
        objective = "Sharpe vs Liquid" if "Sharpe vs Liquid" in grid else "Sharpe"
    row = grid.loc[grid[objective].idxmax()]
    return {a: float(row[a]) for a in assets}


def train_test_split(returns: pd.DataFrame, strategies: list[Strategy],
                     train: tuple[str, str], test: tuple[str, str],
                     amount: float = 10_000.0, cost_bps: float = 10.0):
    """Pick the best static mix on the training SIP, then compare everyone on the test SIP.

    The static mix is the classic "optimise on history, hope it holds" approach; the
    walk-forward strategies re-estimate continuously using only past data.
    """
    assets = list(returns.columns)
    train_idx = returns.loc[train[0]:train[1]].index
    test_idx = returns.loc[test[0]:test[1]].index
    grid = static_grid(returns, contribution_schedule(train_idx, amount), cost_bps=cost_bps)
    w_star = best_static(grid, assets)
    tuned = Strategy("Best static (train-tuned)", fixed_weights(returns.index, w_star),
                     rebalance="calendar",
                     description=f"Grid-search best-Sharpe (vs Liquid) mix on {train[0]}..{train[1]}: {w_star}")
    contrib = contribution_schedule(test_idx, amount)
    results = [run_sip(returns, s, contrib, cost_bps) for s in [*strategies, tuned]]
    return w_star, results


def calendar_year_returns(results) -> pd.DataFrame:
    twr = pd.concat([r.twr for r in results], axis=1)
    return twr.groupby(twr.index.year).apply(lambda g: (1 + g).prod() - 1)


def crisis_table(results, periods: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Cumulative time-weighted return of each strategy through named stress periods."""
    rows = {}
    for label, (a, b) in periods.items():
        rows[label] = {r.name: float((1 + r.twr.loc[a:b]).prod() - 1) for r in results}
    return pd.DataFrame(rows).T


# Indian market stress periods inside the SIP window (Nifty peak-to-trough, month ends).
CRISES = {
    "2011 slowdown + euro crisis (Jan-Dec 2011)": ("2011-01", "2011-12"),
    "2013 taper tantrum, rupee crash (Jun-Aug 2013)": ("2013-06", "2013-08"),
    "2015-16 China/global sell-off (Mar 2015-Feb 2016)": ("2015-03", "2016-02"),
    "2018 IL&FS crisis (Sep-Oct 2018)": ("2018-09", "2018-10"),
}



def sensitivity(returns: pd.DataFrame, contrib: pd.Series, lookbacks=(60, 90, 120),
                bands=(0.03, 0.05, 0.10), cost_bps: float = 10.0) -> pd.DataFrame:
    """Optimized SIP under other look-backs / bands, plus an ablation of the smart instalments.

    All variants run over the months where the longest look-back has enough history.
    """
    from .optimize import walk_forward_weights

    targets = {lb: (walk_forward_weights(returns, "risk_parity", lb)
                    + walk_forward_weights(returns, "max_sharpe", lb)) / 2
               for lb in lookbacks}
    # Compare every variant over the same months: those where the longest look-back is ready.
    start = max(t.dropna().index[0] for t in targets.values())
    contrib = contrib.loc[max(start, contrib.index[0]):]
    rows = []
    for lb, target in targets.items():
        variants = [(f"band {b:.0%}", "smart", "band", b) for b in bands]
        variants += [("pro-rata + annual rebal", "pro_rata", "calendar", 0.0),
                     ("smart, never rebalance", "smart", "none", 0.0)]
        for label, contribution, rebalance, band in variants:
            s = Strategy(label, target, contribution=contribution, rebalance=rebalance,
                         band=band)
            m = summarise(run_sip(returns, s, contrib, cost_bps),
                          rf_returns=returns["Liquid"] if "Liquid" in returns else None)
            rows.append({"Look-back (months)": lb, "Execution": label,
                         **{k: m[k] for k in ("XIRR", "Volatility", "Sharpe", "Sharpe vs Liquid",
                                              "Worst wealth drop", "Annual sell turnover")
                            if k in m}})
    return pd.DataFrame(rows).set_index(["Look-back (months)", "Execution"])
