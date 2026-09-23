# A Simple Optimized SIP Strategy for Multi-Asset Allocation

Degree project (BTP). This project backtests a **Systematic Investment Plan (SIP)**, a fixed
amount invested every month. The SIP is split across **Equity, Bonds and Gold** and uses
a simple optimizer that relies only on past data (no look-ahead). Over 43 years of monthly
data it is compared with the usual alternatives: 100% equity, a naive 1/3 split and a
static 60/20/20 portfolio.

**The full explanation of the method, the results and their limitations is in
[`docs/REPORT.md`](docs/REPORT.md).**

## Quick start

```bash
pip install -r requirements.txt
python run_backtest.py                 # USD investor  -> results/usd/
python run_backtest.py --currency INR  # rupee SIP     -> results/inr/
python -m pytest -q                    # 15 unit tests
```

Useful options: `--amount 5000`, `--step-up 0.10` (raise the SIP 10% every year),
`--cost-bps 20`, `--lookback 60`, `--window-years 15`.

Each run writes `results.md` (all tables), CSVs and five charts:
`wealth.png`, `drawdown.png`, `weights.png`, `rolling_xirr.png` and `frontier.png`.

## The proposed "Optimized SIP" in one paragraph

Every January, fit two optimizers on the **previous 10 years** of monthly returns:
*risk parity* (each asset contributes equal risk) and *maximum Sharpe ratio*. Each
optimizer is limited to 10–70% per asset. Average the two sets of weights; that average
is the target for the year. Each month, invest the SIP instalment in whichever assets are
**below target** ("smart instalments"). Sell only when an asset drifts more than
**5 percentage points** from target.

## Headline results (Feb 1983 – Jul 2026, 522 monthly instalments, 10 bps costs)

| USD investor | XIRR | Volatility | Sharpe (rf=0) | Worst fall in account | Worst 10-yr SIP XIRR |
|---|---|---|---|---|---|
| Equity SIP | **11.3%** | 12.3% | 0.99 | −48.3% | −7.2% |
| Equal-weight SIP | 9.0% | 6.9% | 1.29 | −18.2% | 4.8% |
| 60/20/20 annual rebal | 9.8% | 7.6% | 1.29 | −23.4% | 1.7% |
| **Optimized SIP** | 7.8% | **5.7%** | **1.42** | **−16.6%** | 3.5% |

In short, the optimized SIP gives up about 3.5 points of XIRR a year compared with pure
equity. In exchange it cuts the worst fall in the account from about 48% to about 17%, and
it loses money in none of the 403 rolling 10-year windows (pure equity lost money in
3% of them). It also beats the classic approach of tuning a fixed mix on the first half of
the data and keeping it for the second half (8.0% vs 6.4% XIRR out of sample). A naive
1/3 split is a strong benchmark, as the finance literature on "1/N" portfolios predicts.
`docs/REPORT.md` covers this honestly.

## Project layout

```
data/raw/            bundled monthly data (Shiller S&P 500, US 10y yield, gold, USD/INR)
sip/data.py          builds total-return series (equity + dividends, synthetic bond fund, gold, INR option)
sip/optimize.py      min-variance / max-Sharpe / risk-parity optimizers + walk-forward scheduler
sip/engine.py        month-by-month SIP simulator (instalments, smart split, rebalancing, costs)
sip/strategies.py    the six strategies compared
sip/metrics.py       XIRR, CAGR, volatility, Sharpe, Sortino, drawdowns, turnover
sip/analysis.py      rolling windows, static-mix grid search, train/test split, sensitivity, crises
sip/plots.py         charts
run_backtest.py      runs everything and writes results/<currency>/
tests/test_sip.py    unit tests (XIRR, engine, optimizers, no look-ahead, data sanity)
docs/REPORT.md       the write-up
```

## Using Indian market data

The bundled data is US-market data, since it is the longest freely available multi-asset
history. With the INR option, it models a rupee investor holding those assets. If you have
internet access you can load Indian ETFs instead:

```python
from sip.data import load_yahoo
rets = load_yahoo({"Equity": "NIFTYBEES.NS", "Bonds": "LTGILTBEES.NS", "Gold": "GOLDBEES.NS"})
```

Then pass `rets` to `build_strategies` / `run_sip` in the same way as `run_backtest.py`
does. These ETFs only have about 10–15 years of history, so use `--lookback 36` or
`--lookback 60`.
