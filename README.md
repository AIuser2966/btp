# A Simple Optimized SIP Strategy for Multi-Asset Allocation

Degree project (BTP). A **SIP** (Systematic Investment Plan) invests a fixed amount every
month. This project asks: **how should each month's 10,000 be split between stocks,
bonds and gold?** It tests six ways of splitting it on 43 years of real market data
(Feb 1983 – Jul 2026) and compares them fairly.

## How the repository is organised

Read the folders in order. Each strategy folder is self-contained: **explanation at the
top of its README, the rule in `strategy.py`, and its own `results/`.**

| Folder | What's inside |
|---|---|
| [`00_raw_data/`](00_raw_data) | The raw market data and how it becomes monthly returns (formulas + worked example). **Every strategy uses this one table.** |
| [`01_equity_sip/`](01_equity_sip) | Strategy 1: **100% stocks**, the usual SIP (benchmark) |
| [`02_equal_weight_sip/`](02_equal_weight_sip) | Strategy 2: **⅓ each** in stocks, bonds and gold, never rebalanced |
| [`03_fixed_60_20_20_sip/`](03_fixed_60_20_20_sip) | Strategy 3: **60/20/20**, reset once a year |
| [`04_risk_parity_sip/`](04_risk_parity_sip) | Strategy 4: **risk parity**, an optimizer that gives each asset equal risk |
| [`05_max_sharpe_sip/`](05_max_sharpe_sip) | Strategy 5: **max Sharpe**, an optimizer that maximizes return per unit of risk |
| [`06_optimized_sip/`](06_optimized_sip) | Strategy 6: **Optimized SIP**, the average of 4 and 5 |
| [`07_comparison/`](07_comparison) | **All six side by side**, robustness tests and the conclusion |
| [`sip/`](sip) | Shared engine used by all six: monthly SIP simulator, optimizers, scoring |
| [`tests/`](tests) | 20 automated checks (formulas, no look-ahead, data integrity) |
| [`docs/`](docs) | Architecture diagram, full report, ground-up explanations |
| [`extras/ai_forecasting/`](extras/ai_forecasting) | Extension (not part of the main study): can ML forecasts improve the SIP? |

Strategies 4–6 are **optimized but not AI**: every year they re-calculate the split from
the **previous 10 years only** (no look-ahead).

## Headline results (USD, 10,000/month, Feb 1983 – Jul 2026, 5.22 M invested)

| Strategy | Final value | Return/yr (XIRR) | Worst fall | Sharpe | 10-yr SIPs that lost money |
|---|---|---|---|---|---|
| 1 · 100% stocks | 119.1 M | **11.3%** | −48.3% | 0.99 | 3.0% |
| 2 · ⅓ each | 58.5 M | 9.0% | −18.2% | 1.29 | 0% |
| 3 · 60/20/20 | 73.3 M | 9.8% | −23.4% | 1.29 | 0% |
| 4 · Risk parity | 39.1 M | 7.7% | **−16.3%** | **1.44** | 0% |
| 5 · Max Sharpe | 44.8 M | 8.1% | −17.2% | 1.37 | 0% |
| 6 · Optimized | 40.7 M | 7.8% | −16.6% | 1.42 | 0% |

**Bottom line:** 100% stocks makes the most money but can fall by half. The optimizer
SIPs (4–6) give the best return per unit of risk and the smallest falls, at the cost of
lower return. Risk parity alone is marginally the best on risk. A simple ⅓ split is a
strong benchmark. Details: [`07_comparison/`](07_comparison).

## Run it

```bash
pip install -r requirements.txt
python run_all.py            # rebuilds data, all six strategies and the comparison
python -m pytest -q          # 20 tests
```

Or run one piece at a time, e.g. `python 04_risk_parity_sip/strategy.py`.
`python 06_optimized_sip/recommend.py --currency INR --amount 10000` prints this month's
split for the Optimized SIP.

## Architecture

![Architecture and formulas](docs/architecture.png)

## Further reading

- [`docs/WORKED_EXAMPLE.md`](docs/WORKED_EXAMPLE.md): one investor followed through all 20 steps with real numbers
- [`docs/EXPLAINED.md`](docs/EXPLAINED.md): every formula explained from the ground up
- [`docs/REPORT.md`](docs/REPORT.md): the full project report
