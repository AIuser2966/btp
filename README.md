# A Simple Optimized SIP Strategy for Multi-Asset Allocation

Degree project (BTP). A **SIP** (Systematic Investment Plan) invests a fixed amount every
month. This project asks: **how should each month's ₹10,000 be split between Nifty 50, gold and
a liquid fund?** It tests six ways of splitting it on Indian market data (2000–2019; SIPs run
**Feb 2010 – Dec 2019**) and compares them fairly.

## How the repository is organised

Read the folders in order. Each strategy folder is self-contained: **explanation at the top
of its README (every formula with its terms, a Feb 2010 example and the line of code), the
rule in `strategy.py`, and its own `results/`.**

| Folder | What's inside |
|---|---|
| [`00_raw_data/`](00_raw_data) | Daily Nifty / Gold / Liquid data + USD/INR, how they become monthly rupee returns, and the data verification. **Every strategy uses this one table.** |
| [`01_equity_sip/`](01_equity_sip) | Strategy 1: **100% Nifty 50**, the usual SIP (benchmark) |
| [`02_equal_weight_sip/`](02_equal_weight_sip) | Strategy 2: **⅓ each** in Nifty, gold and liquid, never rebalanced |
| [`03_fixed_60_20_20_sip/`](03_fixed_60_20_20_sip) | Strategy 3: **60/20/20** Nifty/Gold/Liquid, reset once a year |
| [`04_risk_parity_sip/`](04_risk_parity_sip) | Strategy 4: **risk parity**, an optimiser that gives each asset equal risk |
| [`05_max_sharpe_sip/`](05_max_sharpe_sip) | Strategy 5: **max Sharpe**, an optimiser that maximises return per unit of risk |
| [`06_optimized_sip/`](06_optimized_sip) | Strategy 6: **Optimized SIP**, the average of 4 and 5 |
| [`07_comparison/`](07_comparison) | **All six side by side**, robustness tests and the conclusion |
| [`08_forward_test/`](08_forward_test) | **Forward look:** data extended to Dec 2025 (cross-checked), all six + a **fixed optimiser** tested on 2020–2025, and what an investor starting in Jan 2026 could expect |
| [`09_investor_tool/`](09_investor_tool) | **Investor tool:** this month's split for a real investor (first version, command line) |
| [`10_max_utility/`](10_max_utility) | **One score for profit and risk:** mean-variance utility U = return above Liquid − (λ/2)·variance, Strategy 7 (Max-Utility SIP), and which approach maximises U for aggressive / moderate / conservative investors |
| [`sip/`](sip) | Shared engine used by all six: monthly SIP simulator, optimisers, scoring |
| [`tests/`](tests) | Automated checks (formulas, no look-ahead, data integrity) |
| [`docs/`](docs) | Architecture diagram and the 20-step worked example |
| [`extras/`](extras) | Not part of the main study: the earlier **US-data version** (1973–2026) and the **AI forecasting** extension |

Strategies 4–6 are **optimised but not AI**: every year they recalculate the split from the
**previous 10 years only** (no look-ahead).

## Headline results (₹10,000/month, Feb 2010 – Dec 2019, ₹11.9 lakh invested)

| Strategy | Final value | Return/yr (XIRR) | Max drawdown | Sharpe vs Liquid |
|---|---|---|---|---|
| 1 · 100% Nifty | ₹2,176,119 | 11.7% | -23.7% | 0.29 |
| 2 · ⅓ each | ₹1,850,460 | 8.6% | -6.5% | 0.28 |
| 3 · 60/20/20 | ₹1,990,520 | 10.0% | -8.9% | 0.33 |
| 4 · Risk parity | ₹1,778,154 | 7.9% | -1.7% | 0.26 |
| 5 · Max Sharpe | ₹1,770,116 | 7.8% | -1.8% | 0.24 |
| 6 · Optimized | ₹1,774,231 | 7.8% | -1.7% | 0.25 |

A SIP kept 100% in Liquid earned 7.3%.

**Bottom line:** 100% Nifty earned the most but fell hardest. **60/20/20 gave the best
return above the T-bill rate per unit of risk.** The optimiser SIPs (4–6) turned into ~70%
cash: Liquid barely moves, so the optimisers, which measure risk against a 0% rate, push it
to the 70% cap. They had tiny falls but earned only a little more than cash. Details:
[`07_comparison/`](07_comparison).

## Forward look: 2020–2025, data the rules never saw ([`08_forward_test/`](08_forward_test))

₹10,000/month, Jan 2020 – Dec 2025 (₹7.2 lakh invested). 6b fixes the optimiser's flaw (Liquid
held at a fixed 10%, chosen on 2010–2019 only):

| Strategy | Final value | Return/yr (XIRR) | Max drawdown | Sharpe vs Liquid |
|---|---|---|---|---|
| 1 · 100% Nifty | ₹1,138,663 | 15.1% | -28.2% | 0.55 |
| 2 · ⅓ each | ₹1,201,678 | 16.9% | -6.8% | 1.18 |
| 3 · 60/20/20 | ₹1,168,631 | 16.0% | -15.4% | 0.83 |
| 4 · Risk parity | ₹1,010,664 | 11.2% | -3.0% | 1.16 |
| 5 · Max Sharpe | ₹1,008,323 | 11.1% | -3.2% | 1.13 |
| 6 · Optimized | ₹1,009,149 | 11.1% | -3.1% | 1.14 |
| 6b · Fixed Optimized | ₹1,328,220 | 20.3% | -12.2% | 1.09 |

**Out-of-sample winner (rule set in advance: best Sharpe vs Liquid): Equal-weight SIP.** Highest
return: Fixed Optimized SIP. Gold's 2020–2025 boom (+21%/yr in rupees) helped every gold-holding mix.
## Which strategy for which investor? ([`10_max_utility/`](10_max_utility))

Each strategy is scored with one number that balances profit and risk, the mean-variance utility
U = (return above Liquid) − (λ/2) × variance, where λ is the investor's risk aversion (the Lagrange
multiplier in Markowitz's problem). Out of sample (2020–2025) the Fixed Optimized SIP had the highest U
for aggressive (λ=2), moderate (λ=4) and conservative (λ=8) investors. Strategy 7, which maximises U
directly, came 2nd–3rd: optimising on noisy past returns does not guarantee the best realised U.
The investor tool ([`09_investor_tool/`](09_investor_tool)) asks for the investor's risk profile and
uses that winner.

## Run it

```bash
pip install -r requirements.txt
python run_all.py            # rebuilds data, all six strategies, the comparison and these READMEs
python -m pytest -q          # automated checks
```

`python 09_investor_tool/invest.py --amount 10000 --holdings NIFTY GOLD LIQUID --risk moderate` prints this
month's split for an investor today (data to Dec 2025). See [`09_investor_tool/`](09_investor_tool).

## Architecture

![Architecture and formulas](docs/architecture.png)

## Further reading

- [`docs/WORKED_EXAMPLE.md`](docs/WORKED_EXAMPLE.md): one investor followed through all 20 steps with real numbers
- `ENGINE_WALKTHROUGH.md` in each strategy folder (e.g. [`01_equity_sip/ENGINE_WALKTHROUGH.md`](01_equity_sip/ENGINE_WALKTHROUGH.md)): plain-language, line-by-line walk through the engine for that strategy, ending with real-number examples
- [`docs/SIP_Formulas_Guide.pdf`](docs/SIP_Formulas_Guide.pdf): every strategy's formulas step by step, with rupee examples and a flowchart (rebuild: `python docs/make_formulas_pdf.py`)
- [`docs/SIP_Formula_Sheet.pdf`](docs/SIP_Formula_Sheet.pdf): the formulas only, 7 pages (rebuild: `python docs/make_formula_sheet.py`)
- [`extras/us_data/`](extras/us_data): the same study on US data 1973–2026 (earlier version, with its own report)
