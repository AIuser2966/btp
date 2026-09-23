import numpy as np
import pandas as pd
import pytest

from sip.data import load_returns, par_bond_price
from sip.engine import Strategy, _smart_split, contribution_schedule, run_sip
from sip.metrics import max_drawdown, sip_xirr, xirr
from sip.optimize import (fixed_weights, max_sharpe, min_variance, risk_parity,
                          walk_forward_weights, weight_grid)

IDX = pd.period_range("2000-01", periods=24, freq="M")


def flat_returns(rate=0.01):
    return pd.DataFrame(rate, index=IDX, columns=["Equity", "Bonds", "Gold"])


def test_xirr_matches_known_rate():
    # 100 invested, 110 back one year later -> 10%
    assert xirr(np.array([-100.0, 110.0]), np.array([0.0, 1.0])) == pytest.approx(0.10)


def test_sip_xirr_equals_constant_monthly_return():
    res = run_sip(flat_returns(0.01), Strategy("s", fixed_weights(IDX, {"Equity": 1,
                  "Bonds": 0, "Gold": 0})), contribution_schedule(IDX, 100), cost_bps=0)
    assert sip_xirr(res) == pytest.approx(1.01 ** 12 - 1, rel=1e-6)
    assert res.twr.values == pytest.approx(0.01)


def test_costs_reduce_value():
    w = fixed_weights(IDX, {"Equity": 0.5, "Bonds": 0.5, "Gold": 0.0})
    c = contribution_schedule(IDX, 100)
    free = run_sip(flat_returns(), Strategy("s", w), c, cost_bps=0).total.iloc[-1]
    paid = run_sip(flat_returns(), Strategy("s", w), c, cost_bps=50).total.iloc[-1]
    assert paid < free
    assert paid == pytest.approx(free * (1 - 0.005), rel=1e-9)


def test_smart_split_fills_underweight_first():
    holdings = np.array([80.0, 20.0, 0.0])
    split = _smart_split(holdings, np.array([0.5, 0.5, 0.0]), 20.0)
    assert split == pytest.approx([0.0, 20.0, 0.0])
    # enough cash to close the gap: gap first, then pro-rata
    split = _smart_split(holdings, np.array([0.5, 0.5, 0.0]), 100.0)
    assert split == pytest.approx([20.0, 80.0, 0.0])
    assert split.sum() == pytest.approx(100.0)


def test_calendar_rebalance_restores_target():
    rets = flat_returns(0.0)
    rets["Equity"] = 0.05
    s = Strategy("s", fixed_weights(IDX, {"Equity": 0.5, "Bonds": 0.5, "Gold": 0.0}),
                 rebalance="calendar", rebalance_every=12)
    res = run_sip(rets, s, contribution_schedule(IDX, 100), cost_bps=0)
    assert res.sold.iloc[11] > 0 and res.sold.iloc[:11].eq(0).all()


def test_step_up_schedule():
    c = contribution_schedule(IDX, 100, step_up=0.10)
    assert c.iloc[0] == 100 and c.iloc[12] == pytest.approx(110)


def test_par_bond_prices_at_par():
    assert par_bond_price(0.05, 0.05, 10) == pytest.approx(1.0)
    assert par_bond_price(0.05, 0.06, 10) < 1.0 < par_bond_price(0.05, 0.04, 10)


def test_max_drawdown():
    assert max_drawdown(pd.Series([1, 2, 1, 3])) == pytest.approx(-0.5)


@pytest.mark.parametrize("fn", [min_variance, max_sharpe, risk_parity])
def test_optimisers_respect_bounds(fn):
    rng = np.random.default_rng(0)
    rets = pd.DataFrame(rng.normal([0.008, 0.004, 0.005], [0.04, 0.02, 0.05], (240, 3)))
    w = fn(rets, lo=0.1, hi=0.7)
    assert w.sum() == pytest.approx(1.0)
    assert (w >= 0.1 - 1e-9).all() and (w <= 0.7 + 1e-9).all()


def test_risk_parity_equalises_risk():
    rng = np.random.default_rng(1)
    rets = pd.DataFrame(rng.normal(0, [0.01, 0.02, 0.04], (5000, 3)))
    w = risk_parity(rets)
    rc = w * (rets.cov().values @ w)
    assert rc / rc.sum() == pytest.approx([1 / 3] * 3, abs=0.01)


def test_walk_forward_has_no_look_ahead():
    rets = load_returns()
    w = walk_forward_weights(rets, "min_variance", lookback=60)
    # Changing the future must not change today's weights.
    shocked = rets.copy()
    shocked.iloc[200:] *= -5
    w2 = walk_forward_weights(shocked, "min_variance", lookback=60)
    pd.testing.assert_frame_equal(w.iloc[:200], w2.iloc[:200])
    assert w.iloc[:60].isna().all().all()


def test_weight_grid_sums_to_one():
    grid = weight_grid(["a", "b", "c"], 0.1)
    assert len(grid) == 66
    assert all(sum(g.values()) == pytest.approx(1.0) for g in grid)


def test_bundled_data_is_sane():
    rets = load_returns()
    assert list(rets.columns) == ["Equity", "Bonds", "Gold"]
    assert rets.index[0] == pd.Period("1973-02", "M")
    assert not rets.isna().any().any()
    ann = (1 + rets).prod() ** (12 / len(rets)) - 1
    assert 0.08 < ann["Equity"] < 0.14      # S&P 500 total return ~ 10-11%
    assert 0.04 < ann["Bonds"] < 0.09
    inr = load_returns("INR")
    assert (((1 + inr).prod() ** (12 / len(inr)) - 1) > ann).all()   # rupee depreciated
