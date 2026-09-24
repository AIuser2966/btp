# A Simple Optimized SIP Strategy for Multi-Asset Allocation, Based on Back-Tested Data

All numbers below come from `python run_all.py` (each strategy folder `01_`–`06_` plus
`07_comparison/`). Complete tables are in `07_comparison/results/usd/results.md`
and `07_comparison/results/inr/results.md`.

---

## 1. Problem statement

A **Systematic Investment Plan (SIP)** invests a fixed amount every month. It is the
standard way retail investors build wealth, but most SIPs go into a single equity fund,
which exposes the investor to deep falls (about 50% in 2008). The project asks:

> Can a *simple*, rule-based SIP that spreads each instalment across equity, bonds and gold,
> with weights set by an optimizer using only past data, give a better
> risk-adjusted outcome than a plain equity SIP or a fixed-mix SIP?

"Simple" means that an individual investor could run it with a spreadsheet: one
re-optimization per year, three assets and one rebalancing rule.

## 2. Data

| Asset | Source (bundled in `00_raw_data/raw/`) | How the monthly total return is built |
|---|---|---|
| **Equity** | Shiller S&P 500 price and dividends | price change + 1/12 of the annual dividend. The latest dividend yield is carried forward where the file shows 0 |
| **Bonds** | US 10-year Treasury yield (FRED) | a synthetic *constant-maturity bond fund*: buy a 10-year par bond at yield *y(t−1)*, re-price it a month later at *y(t)* with 9 11/12 years left, and add one month of coupon |
| **Gold** | Monthly gold price, USD/oz | price change |
| **USD/INR** | FRED | used only for `--currency INR`: *(1+r_USD)·(FX_t/FX_{t−1}) − 1* |

The sample is Feb 1973 to Jul 2026 (642 months). SIPs start in **Feb 1983**, because the
optimizer needs 10 years of history first. That gives **522 monthly instalments**.

Over the whole sample, annual returns (USD) were: Equity 11.0%, Bonds 6.3%, Gold 8.0%.
Volatilities were 12.6%, 7.0% and 17.2%. Pairwise correlations were close to 0, which is
the reason diversification helps.

## 3. Method

### 3.1 The SIP engine (`sip/engine.py`)

For every month *t*:

1. The instalment (default 10,000, optionally stepped up each year) arrives.
2. It is split across assets by the **contribution rule**:
   * `pro_rata`: split by the target weights.
   * `smart`: send money to the assets that are **below target** first, and split any
     remainder pro-rata. This rebalances with new money and **never sells**.
3. A **rebalancing rule** may fire: `none`, `calendar` (every 12 months) or `band`
   (when any weight is more than ±5 points off target). A rebalance sells and buys back
   to the targets.
4. Every rupee or dollar traded pays **10 bps** in transaction costs.
5. The month's returns are applied.

### 3.2 Optimizers (`sip/optimize.py`)

All optimizers are solved with SLSQP, with weights summing to 1 and each weight between
**10% and 70%**. The bounds stop any one asset from dominating and keep the portfolio
genuinely multi-asset.

* **Risk parity:** choose *w* so that each asset's risk contribution *wᵢ(Σw)ᵢ* is equal.
  It uses only the covariance matrix and ignores expected returns, which are notoriously
  hard to estimate.
* **Max Sharpe:** maximize *wᵀμ / √(wᵀΣw)*. It uses expected returns, so it is more
  return-seeking but also noisier.
* **Optimized SIP (proposed):** the **average of the two**. This was decided before
  running the results, as a form of shrinkage. The risk-parity half gives robustness and
  the max-Sharpe half adds a return tilt, and averaging two estimates reduces estimation
  error.

### 3.3 Walk-forward: why this is a fair back-test

The weights are re-fitted every 12 months (each February) using the **previous 120 months only**
(`walk_forward_weights`). A unit test (`test_walk_forward_has_no_look_ahead`) checks this:
it corrupts all data after month 200 and confirms that the weights before month 200
do not change. Many student back-tests quietly optimize over the whole period; §5.3 shows
how badly that approach does out of sample.

### 3.4 Strategies compared

| # | Strategy | Weights | Instalments | Rebalancing |
|---|---|---|---|---|
| 1 | Equity SIP (benchmark) | 100/0/0 | – | – |
| 2 | Equal-weight SIP | 1/3 each | pro-rata | never |
| 3 | 60/20/20 annual rebal | 60/20/20 | pro-rata | every 12 months |
| 4 | Risk-parity SIP | walk-forward RP | smart | 5% band |
| 5 | Max-Sharpe SIP | walk-forward MS | smart | 5% band |
| 6 | **Optimized SIP** | ½RP + ½MS | smart | 5% band |

### 3.5 Metrics (`sip/metrics.py`)

* **XIRR:** the money-weighted annual return, i.e. what the investor actually earned
  on their instalments. It is the standard SIP metric in India.
* **TWR CAGR, volatility, Sharpe and Sortino:** computed on time-weighted returns, so the
  timing of instalments does not distort them. Sharpe uses rf = 0; see §7.
* **Max drawdown** (time-weighted) and **worst wealth drop**: the largest fall in the
  account value the investor actually saw.
* **Annual sell turnover:** the share of the portfolio sold each year. It is a proxy for
  capital-gains tax events.

### 3.6 Robustness tests (`sip/analysis.py`)

1. **Rolling windows:** every 10-year SIP starting in each month from 1983 onwards
   (403 windows). This shows the spread of outcomes, not just one lucky path.
2. **Train/test split:** grid-search the best fixed mix (max Sharpe) on the first half,
   then test every strategy on the second half.
3. **Hindsight grid:** all 66 fixed mixes on a 10% grid over the full period. The result
   is the grey cloud in `frontier.png`, a look-ahead reference only.
4. **Sensitivity/ablation:** look-backs of 60, 120 and 180 months, bands of 3%, 5% and
   10%, and smart instalments vs pro-rata.
5. **Stress periods:** 1987, the dot-com bust, the GFC, COVID and 2022.

## 4. Results: full period (USD, Feb 1983 – Jul 2026)

| Strategy | Final value | XIRR | Volatility | Sharpe | Max DD | Worst wealth drop | Sell turnover/yr |
|---|---|---|---|---|---|---|---|
| Equity SIP | 119.1 M | **11.3%** | 12.3% | 0.99 | −49.0% | −48.3% | 0% |
| Equal-weight SIP | 58.5 M | 9.0% | 6.9% | 1.29 | −18.7% | −18.2% | 0% |
| 60/20/20 annual rebal | 73.3 M | 9.8% | 7.6% | 1.29 | −24.2% | −23.4% | 3.8% |
| Risk-parity SIP | 39.1 M | 7.7% | **5.5%** | **1.44** | **−16.6%** | **−16.3%** | 5.3% |
| Max-Sharpe SIP | 44.8 M | 8.1% | 6.1% | 1.37 | −17.5% | −17.2% | 8.8% |
| **Optimized SIP** | 40.7 M | 7.8% | 5.7% | 1.42 | −17.0% | −16.6% | 4.7% |

Total invested was 5.22 M in every strategy. Figures: `07_comparison/results/usd/wealth.png`,
`drawdown.png` and `weights.png`.

For an Indian investor running a rupee SIP (`07_comparison/results/inr/`), the ranking is the same.
All returns are higher because the rupee fell from 8 to 95 per USD. The Optimized SIP
earns 13.8% XIRR with a worst account fall of only −9.0%, against 16.9% and −38.4% for
pure equity.

## 5. Results: robustness

### 5.1 Rolling 10-year SIPs (403 windows, USD)

| Strategy | Median XIRR | 5th pct | Worst | % windows < 0 | Median worst drop | Worst drop (any window) |
|---|---|---|---|---|---|---|
| Equity SIP | **11.8%** | 1.7% | −7.2% | 3.0% | −18.5% | −41.2% |
| Equal-weight SIP | 8.3% | **5.6%** | **4.8%** | 0% | −5.0% | −13.9% |
| 60/20/20 annual rebal | 9.0% | **5.6%** | 1.7% | 0% | −8.6% | −21.4% |
| Optimized SIP | 7.0% | 4.8% | 3.5% | 0% | **−3.5%** | **−11.5%** |

The equity SIP has the best median outcome but a very wide spread: in 3% of 10-year SIPs
the investor ended with less than they put in. No diversified strategy ever lost money
over 10 years. Of the four shown, the Optimized SIP has the smallest typical drawdown.

### 5.2 Stress periods (cumulative return, USD)

| Period | Equity SIP | 60/20/20 | Optimized SIP |
|---|---|---|---|
| 1987 crash | −25.0% | −15.8% | −9.2% |
| Dot-com bust 2000-02 | −39.9% | −17.9% | **+2.1%** |
| GFC 2007-09 | −46.0% | −21.2% | **+2.5%** |
| COVID 2020 | −18.8% | −9.2% | −3.2% |
| 2022 rate shock | −16.7% | −14.2% | −14.4% |

In 2022, stocks and bonds fell together, so a bond-heavy portfolio had no protection. This
is the strategy's main weakness (§7).

### 5.3 Train/test split: walk-forward vs "optimize once"

The best fixed mix fitted on 1983–2004 was **30/60/10**. It was tested on Nov 2004 – Jul 2026:

| Strategy (test period only) | XIRR | Sharpe | Worst wealth drop |
|---|---|---|---|
| Equity SIP | 13.1% | 0.91 | −29.3% |
| 60/20/20 annual rebal | 10.7% | 1.25 | −15.0% |
| Optimized SIP (walk-forward) | 8.0% | 1.30 | −14.8% |
| Best static, train-tuned | 6.4% | 1.25 | −15.0% |

A mix tuned on past data **under-performed the walk-forward Optimized SIP by 1.6 points
of XIRR a year**. The same happens in INR (10.9% vs 13.5%). One-shot optimization
over-fits the training period; re-estimating every year adapts to regime changes.

### 5.4 Sensitivity and ablation (USD, common window from 1988)

* **Look-back:** 60, 120 and 180 months give XIRR of 8.0%, 7.5% and 7.3%, with Sharpe
  between 1.34 and 1.42. The strategy is **not fragile** to this choice.
* **Band width:** 3%, 5% and 10% give almost identical returns. Sell turnover falls from
  7.5% to 2.3% a year, so a wider band costs nothing and cuts taxable sales.
* **Smart instalments without any rebalancing** match or beat the rebalanced versions on
  XIRR (7.7% vs 7.5%), with **zero sales**. The "rebalance with new money" idea is the most
  practical, tax-efficient piece of the design.

### 5.5 Frontier view (`frontier.png`)

The grey cloud shows every fixed mix over the full period. The Optimized SIP sits in the
low-drawdown part of the upper edge, i.e. it is close to *efficient*. It reaches that
position without hindsight, whereas the grey points need to know the future to pick.

### 5.6 Machine-learning return forecasts (extension)

Details are in `extras/ai_forecasting/README.md`. Ridge, random-forest and gradient-boosting models,
trained walk-forward on 13 market features, forecast each asset's next-12-month return.
The forecasts then replaced the trailing average in the max-Sharpe half of the
Optimized SIP.

| Strategy (USD) | XIRR | Sharpe | Sell turnover/yr |
|---|---|---|---|
| Optimized SIP | 7.8% | 1.42 | 4.7% |
| + Ridge | 8.0% | 1.34 | 15.1% |
| + Random forest | 7.3% | 1.33 | 14.0% |
| + Gradient boosting | 7.2% | 1.28 | 14.2% |
| + Oracle (perfect foresight) | 10.8% | 1.82 | 21.9% |

Bond returns were partly predictable (out-of-sample R² up to +0.25). Equity and gold
returns were not: all models were worse than the historical average. Perfect forecasts
would add about 3 points of XIRR, but real models add at most 0.2 points, at three
times the turnover. The simple Optimized SIP remains the recommendation.

## 6. Discussion: what the evidence says

1. **Diversification is the big win.** Moving from 100% equity to any three-asset SIP
   cuts the worst account fall from about 48% to about 17–23% and removes negative
   10-year outcomes.
2. **Optimization buys risk efficiency, not extra return.** The three optimizer-based SIPs
   (risk parity, max Sharpe and their blend) have the highest Sharpe ratios (1.37–1.44)
   and the smallest drawdowns (about −16% to −17%). Risk parity alone is marginally the
   best on risk (Sharpe 1.44 vs 1.42 for the blend); the blend earns slightly more (7.8%
   vs 7.7%) and trades less than max Sharpe. Its absolute XIRR is lower because the optimizer, looking at
   volatility, holds a lot of bonds (about 50%; see `weights.png`).
3. **A naive 1/3 split is hard to beat.** Equal-weight earned 1.2 points more XIRR at a
   slightly higher drawdown. This matches DeMiguel, Garlappi & Uppal (2009): estimation
   error often eats the theoretical gains of optimization. The project confirms this
   honestly rather than hiding it, and shows that walk-forward optimization at least
   **beats "optimize once"** out of sample.
4. **Choosing a strategy depends on the investor.** A young investor with a 20+ year
   horizon who can stomach −50% will get more from pure equity. An investor near a goal
   (a house or retirement), or one likely to panic-sell in a crash, benefits most from the
   Optimized SIP, because it keeps them invested.

## 7. Limitations (state these in the viva)

* **Sharpe with rf = 0** flatters low-risk, bond-heavy portfolios, because part of the
  bond return is really the risk-free rate. With a T-bill rate the Sharpe gap would
  narrow. XIRR and drawdown comparisons are unaffected.
* **Shiller equity prices are monthly averages,** which smooths volatility and drawdowns
  a little. The real month-end S&P 500 total return fell roughly 51% in 2008–09, compared with 49% here.
* **The bond series is synthetic.** It is a constant-maturity bond fund, not a traded ETF,
  and it ignores credit and roll costs.
* **1983–2020 was a 40-year bond bull market** (yields fell from 11% to 1%). That
  flatters any bond-heavy strategy, and 2022 shows what happens when it reverses.
* **The data is US assets** (optionally viewed in INR), not Nifty, Indian G-secs or
  Indian gold, because freely downloadable Indian series are much shorter. `load_yahoo()`
  lets you re-run with Indian ETFs.
* **Taxes, exit loads and fund expense ratios are not modelled.** Sell turnover is
  reported as a proxy for tax.
* **Only 10 bps per trade** is charged; `--cost-bps` lets you stress this.

## 8. Possible extensions

* ~~Machine-learning return forecasts~~: done, see §5.6 and `extras/ai_forecasting/`.
* A volatility-target or "risk-profile" version (conservative, moderate or aggressive)
  that maximizes return for a chosen risk budget.
* Adding a cash/T-bill asset and computing a proper excess-return Sharpe.
* Shrinkage estimators for μ and Σ (Ledoit–Wolf), or a Black–Litterman prior.
* Real Indian data: Nifty 50 TRI, a gilt index and domestic gold.
* Monte-Carlo or bootstrap resampling of returns to get confidence intervals on XIRR.

## 9. Likely viva questions

* **Why XIRR and not CAGR?** An SIP has many cash flows at different dates. XIRR is
  the single rate that makes the net present value of all of them zero. CAGR only works
  for one lump sum.
* **How do you avoid look-ahead bias?** Weights at month *t* use only months *t−120*
  to *t−1*. This is enforced by a unit test.
* **Why the 10–70% bounds?** Unconstrained mean-variance optimization produces corner
  solutions (for example 100% bonds) and flips weights sharply. The bounds keep the
  portfolio diversified and stable.
* **Why average risk parity and max Sharpe?** Risk parity ignores noisy return forecasts.
  Max Sharpe uses them. Averaging is a simple shrinkage that trades a little return for
  much more robustness.
* **What are "smart instalments"?** Each month's instalment goes to the under-weight
  assets. This keeps the portfolio near target without selling, so there are no tax
  events and no exit loads.

## References

* DeMiguel, V., Garlappi, L., & Uppal, R. (2009). *Optimal versus naive diversification:
  How inefficient is the 1/N portfolio strategy?* Review of Financial Studies, 22(5).
* Markowitz, H. (1952). *Portfolio Selection.* Journal of Finance, 7(1).
* Maillard, S., Roncalli, T., & Teïletche, J. (2010). *The properties of equally weighted
  risk contribution portfolios.* Journal of Portfolio Management, 36(4).
* Sharpe, W. F. (1966). *Mutual Fund Performance.* Journal of Business, 39(1).
* Shiller, R. J. *Online data: U.S. stock markets 1871–present.* Yale University.
