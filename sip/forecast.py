"""Machine-learning forecasts of each asset's next-12-month return.

Question: can a model predict future returns well enough to make the SIP better?

* **Features** (known at the end of month j): momentum and volatility of each asset,
  the bond yield and its 12-month change, the equity dividend yield (valuation) and the
  12-month change in USD/INR.
* **Target**: the asset's compounded return over months j+1 .. j+12.
* **Walk-forward training**: at month j the model is trained only on rows whose 12-month
  target had fully happened by then (rows k <= j - 12), and it is re-fitted every 12 months.
* **Benchmark**: the historical average (expanding mean of past 12-month returns).
  A forecast is only useful if it beats this, measured by out-of-sample R^2
  (Campbell & Thompson, 2008).

Hyper-parameters are fixed up front (not tuned on the test data) to avoid data snooping.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .optimize import max_sharpe_mu, risk_parity

HORIZON = 12


def build_features(returns: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """One row per month; every value uses data up to the end of that month only."""
    growth = (1 + returns).cumprod()
    feats = {}
    for a in returns.columns:
        feats[f"{a} mom 3m"] = growth[a] / growth[a].shift(3) - 1
        feats[f"{a} mom 12m"] = growth[a] / growth[a].shift(12) - 1
        feats[f"{a} vol 12m"] = returns[a].rolling(12).std() * np.sqrt(12)
    m = macro.reindex(returns.index)
    feats["Bond yield"] = m["bond_yield"]
    feats["Bond yield chg 12m"] = m["bond_yield"] - m["bond_yield"].shift(12)
    feats["Dividend yield"] = m["div_yield"]
    feats["USDINR chg 12m"] = m["usdinr"] / m["usdinr"].shift(12) - 1
    return pd.DataFrame(feats, index=returns.index)


def build_targets(returns: pd.DataFrame, horizon: int = HORIZON,
                  partial: bool = False) -> pd.DataFrame:
    """Row j = compounded return over months j+1 .. j+horizon.

    With ``partial=True`` the last rows use however many future months exist,
    scaled to a 12-month rate (only used for the perfect-foresight oracle).
    """
    log = np.log1p(returns)
    fwd = log[::-1].rolling(horizon, min_periods=1 if partial else horizon).sum()[::-1]
    fwd = fwd.shift(-1)
    if partial:
        n = log[::-1].rolling(horizon, min_periods=1).count()[::-1].shift(-1)
        fwd = fwd * horizon / n
    return np.expm1(fwd)


MODELS = {
    "Ridge": lambda: make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
    "Random forest": lambda: RandomForestRegressor(
        n_estimators=200, max_depth=3, min_samples_leaf=20, random_state=0),
    "Gradient boosting": lambda: GradientBoostingRegressor(
        n_estimators=150, max_depth=2, learning_rate=0.03, subsample=0.8, random_state=0),
}
BENCHMARK = "Historical mean"
TRAILING = "Trailing 10y mean"


def walk_forward_forecasts(X: pd.DataFrame, Y: pd.DataFrame, model: str,
                           min_train: int = 96, refit_every: int = 12,
                           horizon: int = HORIZON):
    """Out-of-sample forecasts for every month plus the fitted models' feature importances.

    Row j of the result is the forecast made at the end of month j for months j+1..j+12.
    A model fitted at month j only sees rows k <= j - horizon, whose targets were known by then.
    """
    valid = X.notna().all(axis=1).values
    out = pd.DataFrame(np.nan, index=X.index, columns=Y.columns)
    importances = []
    n_train = np.cumsum(valid)                    # valid rows among 0..j
    fit_points = [j for j in range(horizon, len(X))
                  if n_train[j - horizon] >= min_train and valid[j]]
    if not fit_points:
        return out, pd.DataFrame()
    first = fit_points[0]
    for j in range(first, len(X), refit_every):
        train_rows = np.where(valid[: j - horizon + 1])[0]
        block = np.arange(j, min(j + refit_every, len(X)))
        block = block[valid[block]]
        for a in Y.columns:
            y = Y[a].values[train_rows]
            if model == BENCHMARK:
                pred = np.full(len(block), y.mean())
            else:
                est = MODELS[model]()
                est.fit(X.values[train_rows], y)
                pred = est.predict(X.values[block])
                importances.append({"refit": X.index[j], "asset": a,
                                    **dict(zip(X.columns, _importance(est)))})
            out.iloc[block, out.columns.get_loc(a)] = pred
    return out, pd.DataFrame(importances)


def trailing_mean_forecast(returns: pd.DataFrame, lookback: int = 120) -> pd.DataFrame:
    """What the plain Optimized SIP implicitly assumes: next year = the last 10 years' pace."""
    growth = (1 + returns).cumprod()
    return (growth / growth.shift(lookback)) ** (12 / lookback) - 1


def _importance(est) -> np.ndarray:
    if hasattr(est, "feature_importances_"):
        return est.feature_importances_
    coef = np.abs(est[-1].coef_)              # ridge on standardised features
    return coef / coef.sum() if coef.sum() > 0 else coef


def evaluate(forecasts: dict[str, pd.DataFrame], Y: pd.DataFrame) -> pd.DataFrame:
    """Forecast accuracy on the months every model has a forecast and the truth is known."""
    bench = forecasts[BENCHMARK]
    mask = Y.notna().all(axis=1)
    for f in forecasts.values():
        mask &= f.notna().all(axis=1)
    y = Y[mask]
    rows = []
    for name, f in forecasts.items():
        f = f[mask]
        for a in Y.columns:
            err = y[a] - f[a]
            rows.append({
                "Model": name, "Asset": a,
                "OOS R2 vs hist mean": 1 - (err ** 2).sum() / ((y[a] - bench[a][mask]) ** 2).sum(),
                "RMSE": np.sqrt((err ** 2).mean()),
                "Correlation": np.corrcoef(f[a], y[a])[0, 1],
                "Direction hit rate": (np.sign(f[a]) == np.sign(y[a])).mean(),
            })
        # did the model rank the assets right? (which asset will do best next year)
        best_hit = (f.values.argmax(axis=1) == y.values.argmax(axis=1)).mean()
        rows.append({"Model": name, "Asset": "Pick best asset", "Direction hit rate": best_hit})
    out = pd.DataFrame(rows)
    out.attrs["months"] = int(mask.sum())
    out.attrs["period"] = f"{y.index[0]}..{y.index[-1]}"
    return out


def forecast_weights(returns: pd.DataFrame, forecasts: pd.DataFrame, lookback: int = 120,
                     reoptimise_every: int = 12, lo: float = 0.10, hi: float = 0.70,
                     blend: float = 0.5) -> pd.DataFrame:
    """Optimized-SIP targets where max-Sharpe uses model forecasts instead of past averages.

    target = blend * risk parity + (1 - blend) * max-Sharpe(mu = forecast, Sigma = past 10y).
    The forecast used at the start of month i is the one made at the end of month i-1.
    """
    out = pd.DataFrame(np.nan, index=returns.index, columns=returns.columns)
    current = None
    for i in range(lookback, len(returns)):
        if current is None or (i - lookback) % reoptimise_every == 0:
            window = returns.iloc[i - lookback:i]
            mu = forecasts.iloc[i - 1][returns.columns].values / 12.0
            if np.isnan(mu).any():
                raise ValueError(f"no forecast available for {returns.index[i]}")
            ms = max_sharpe_mu(mu, window.cov().values, lo, hi)
            current = blend * risk_parity(window, lo, hi) + (1 - blend) * ms
        out.iloc[i] = current
    return out


def latest_forecast(X: pd.DataFrame, Y: pd.DataFrame, model: str,
                    horizon: int = HORIZON) -> pd.Series:
    """Forecast for the next 12 months, trained on every row whose outcome is already known."""
    valid = X.notna().all(axis=1).values
    j = len(X) - 1
    train_rows = np.where(valid[: j - horizon + 1])[0]
    out = {}
    for a in Y.columns:
        y = Y[a].values[train_rows]
        if model == BENCHMARK:
            out[a] = y.mean()
            continue
        est = MODELS[model]()
        est.fit(X.values[train_rows], y)
        out[a] = est.predict(X.values[j:j + 1])[0]
    return pd.Series(out)
