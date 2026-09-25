import numpy as np
import pandas as pd
import pytest

import sys
from pathlib import Path

from sip.data import (NIFTY_DIVIDEND_YIELD, gold_inr_price, load_daily, load_returns,
                      load_usdinr_daily, month_end, read_returns_table)
from sip.engine import Strategy, _smart_split, contribution_schedule, run_sip
from sip.metrics import max_drawdown, sip_xirr, xirr
from sip.optimize import (fixed_weights, max_sharpe, min_variance, risk_parity,
                          walk_forward_weights, weight_grid)

IDX = pd.period_range("2000-01", periods=24, freq="M")


def flat_returns(rate=0.01):
    return pd.DataFrame(rate, index=IDX, columns=["Nifty", "Gold", "Liquid"])


def test_xirr_matches_known_rate():
    # 100 invested, 110 back one year later -> 10%
    assert xirr(np.array([-100.0, 110.0]), np.array([0.0, 1.0])) == pytest.approx(0.10)


def test_sip_xirr_equals_constant_monthly_return():
    res = run_sip(flat_returns(0.01), Strategy("s", fixed_weights(IDX, {"Nifty": 1,
                  "Gold": 0, "Liquid": 0})), contribution_schedule(IDX, 100), cost_bps=0)
    assert sip_xirr(res) == pytest.approx(1.01 ** 12 - 1, rel=1e-6)
    assert res.twr.values == pytest.approx(0.01)


def test_costs_reduce_value():
    w = fixed_weights(IDX, {"Nifty": 0.5, "Gold": 0.5, "Liquid": 0.0})
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
    rets["Nifty"] = 0.05
    s = Strategy("s", fixed_weights(IDX, {"Nifty": 0.5, "Gold": 0.5, "Liquid": 0.0}),
                 rebalance="calendar", rebalance_every=12)
    res = run_sip(rets, s, contribution_schedule(IDX, 100), cost_bps=0)
    assert res.sold.iloc[11] > 0 and res.sold.iloc[:11].eq(0).all()


def test_step_up_schedule():
    c = contribution_schedule(IDX, 100, step_up=0.10)
    assert c.iloc[0] == 100 and c.iloc[12] == pytest.approx(110)


def test_nifty_return_formula_feb_2010():
    # r = P_t / P_(t-1) - 1 + dividend_yield / 12, with the month-end closes from the raw file
    p = month_end(load_daily()["Nifty"])
    expected = p["2010-02"] / p["2010-01"] - 1 + NIFTY_DIVIDEND_YIELD / 12
    assert load_returns().loc["2010-02", "Nifty"] == pytest.approx(expected)
    assert p["2010-01"] == pytest.approx(4882.05) and p["2010-02"] == pytest.approx(4922.30)


def test_gold_is_converted_to_rupees():
    # gold (INR) = gold (USD) x rupees per dollar, both at month end
    gold_usd = month_end(load_daily()["Gold"])
    fx = month_end(load_usdinr_daily())
    assert gold_inr_price()["2010-02"] == pytest.approx(gold_usd["2010-02"] * fx["2010-02"])
    r = load_returns().loc["2010-02", "Gold"]
    assert r == pytest.approx((gold_usd["2010-02"] / gold_usd["2010-01"])
                              * (fx["2010-02"] / fx["2010-01"]) - 1)


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
    shocked.iloc[150:] *= -5
    w2 = walk_forward_weights(shocked, "min_variance", lookback=60)
    pd.testing.assert_frame_equal(w.iloc[:150], w2.iloc[:150])
    assert w.iloc[:60].isna().all().all()


def test_weight_grid_sums_to_one():
    grid = weight_grid(["a", "b", "c"], 0.1)
    assert len(grid) == 66
    assert all(sum(g.values()) == pytest.approx(1.0) for g in grid)


def test_bundled_data_is_sane():
    rets = load_returns()
    assert list(rets.columns) == ["Nifty", "Gold", "Liquid"]
    assert rets.index[0] == pd.Period("2000-02", "M")
    assert rets.index[-1] == pd.Period("2019-12", "M") and len(rets) == 239
    assert not rets.isna().any().any()
    ann = (1 + rets).prod() ** (12 / len(rets)) - 1
    assert 0.10 < ann["Nifty"] < 0.14        # Nifty 50 incl. dividends, 2000-2019
    assert 0.09 < ann["Gold"] < 0.14         # gold in rupees
    assert 0.06 < ann["Liquid"] < 0.08       # 91-day T-bill level
    assert rets["Liquid"].std() < 0.005      # cash-like


# ---------- forecasting ----------

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# The ML extension runs on the archived US data (extras/us_data).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extras" / "ai_forecasting"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extras" / "us_data"))
import forecast as fc  # noqa: E402
from us_data import load_macro  # noqa: E402
from us_data import load_returns as load_us_returns  # noqa: E402


def test_targets_are_next_12_months():
    rets = load_us_returns()
    Y = fc.build_targets(rets)
    j = 100
    expected = (1 + rets.iloc[j + 1:j + 13]).prod() - 1
    assert Y.iloc[j].values == pytest.approx(expected.values)
    assert Y.iloc[-12:].isna().all().all() and Y.iloc[-13].notna().all()


def test_forecasts_have_no_look_ahead():
    rets = load_us_returns()
    macro = load_macro()
    f1, _ = fc.walk_forward_forecasts(fc.build_features(rets, macro),
                                      fc.build_targets(rets), "Ridge")
    shocked = rets.copy()
    shocked.iloc[300:] = shocked.iloc[300:] * -3 + 0.05   # rewrite the future
    f2, _ = fc.walk_forward_forecasts(fc.build_features(shocked, macro),
                                      fc.build_targets(shocked), "Ridge")
    pd.testing.assert_frame_equal(f1.iloc[:300], f2.iloc[:300])
    assert not f1.iloc[300:].equals(f2.iloc[300:])


def test_forecast_weights_are_valid():
    rets = load_us_returns()
    w = fc.forecast_weights(rets, fc.build_targets(rets, partial=True))
    w = w.dropna()
    assert np.allclose(w.sum(axis=1), 1.0)
    assert (w.values >= 0.10 - 1e-6).all() and (w.values <= 0.70 + 1e-6).all()


# ---------- repository layout ----------

def test_returns_table_matches_raw_data():
    built = load_returns()
    table = read_returns_table()
    assert (built.index == table.index).all()
    assert np.abs(built.values - table.values).max() < 1e-7


def test_six_strategy_folders_load():
    from sip.strategies import build_strategies
    names = [s.name for s in build_strategies(read_returns_table())]
    assert names == ["Equity SIP", "Equal-weight SIP", "60/20/20 annual rebal",
                     "Risk-parity SIP", "Max-Sharpe SIP", "Optimized SIP"]


def test_text_files_are_read_and_written_as_utf8():
    # Windows defaults to cp1252, which cannot store the rupee sign; every text read/write
    # in the project must name the encoding explicitly.
    import re
    root = Path(__file__).resolve().parents[1]
    bad = []
    for f in root.rglob("*.py"):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.(write_text|read_text)\(", line) and "encoding=" not in line:
                bad.append(f"{f.relative_to(root)}:{n}")
    assert not bad, bad
