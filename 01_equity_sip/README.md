# Strategy 1: Equity SIP (100% Nifty 50)

> **Idea:** Put the whole instalment into the Nifty 50 every month. This is the usual SIP, so it's the **main benchmark**.

## The rule

1. Every month, invest the full ₹10,000 in **Nifty 50** (dividends included).
2. Never sell, never rebalance.

## The formulas this strategy uses

Every example uses the first SIP month, **Feb 2010**, when the month's returns were
Nifty +0.93%, Gold +3.17%, Liquid +0.31% (built in `00_raw_data/`).

### 1. Deciding the split

**Target weights (fixed)**

```
w_t = (w_Nifty, w_Gold, w_Liquid) = 100% / 0% / 0%   for every month t
```

| Term | What it stands for |
|---|---|
| `w_t` | the split the strategy aims for in month t |
| `w_Nifty, w_Gold, w_Liquid` | shares of the portfolio for each asset (they add to 100%) |

**Example:** Feb 2010 (and every other month): Nifty 100.0% / Gold 0.0% / Liquid 0.0%.

**Code:** [`01_equity_sip/strategy.py` line 21](../01_equity_sip/strategy.py#L21): `WEIGHTS = {"Nifty": 1.0, "Gold": 0.0, "Liquid": 0.0}`<br>[`01_equity_sip/strategy.py` line 26](../01_equity_sip/strategy.py#L26): `target = fixed_weights(returns.index, WEIGHTS)`<br>[`sip/optimize.py` line 55](../sip/optimize.py#L55): `return pd.DataFrame([weights] * len(index), index=index)`

### 2. Investing each month (the shared SIP engine)

**Instalment**

```
C_t = A × (1 + g)^floor(t / 12)
```

| Term | What it stands for |
|---|---|
| `C_t` | money invested in month t |
| `A` | monthly amount = ₹10,000 |
| `g` | yearly step-up (0 in this study) |
| `t` | months since the SIP started |

**Example:** Feb 2010 (t = 0): C = ₹10,000 × (1 + 0)^0 = **₹10,000**.

**Code:** [`sip/engine.py` line 58](../sip/engine.py#L58): `return pd.Series(amount * (1.0 + step_up) ** years, index=index, name="contribution")`

**Splitting the instalment (pro-rata)**

```
buy_i = w_i × C_t
```

| Term | What it stands for |
|---|---|
| `buy_i` | money put into asset i this month |
| `w_i` | target weight of asset i |
| `C_t` | this month's instalment |

**Example:** Feb 2010: Nifty 1.0000 × ₹10,000 = **₹10,000.00**, Gold 0.0000 × ₹10,000 = **₹0.00**, Liquid 0.0000 × ₹10,000 = **₹0.00**.

**Code:** [`sip/engine.py` line 96](../sip/engine.py#L96): `split = _smart_split(h, w, cash) if strategy.contribution == "smart" else w * cash`

**Trading cost**

```
cost_t = (Σ bought + Σ sold) × 0.10%
```

| Term | What it stands for |
|---|---|
| `cost_t` | rupees lost to costs this month |
| `Σ bought` | all purchases this month |
| `Σ sold` | all sales this month |
| `0.10%` | 10 basis points per rupee traded |

**Example:** Feb 2010: (₹10,000 + ₹0) × 0.001 = **₹10**, taken from each asset in proportion, leaving Nifty ₹9,990.00 / Gold ₹0.00 / Liquid ₹0.00.

**Code:** [`sip/engine.py` line 116](../sip/engine.py#L116): `costs[t] = turnover * cost_rate`<br>[`sip/engine.py` line 118](../sip/engine.py#L118): `h = h * (1.0 - costs[t] / start_value)`

**Market move**

```
h_i ← h_i × (1 + r_i,t)
```

| Term | What it stands for |
|---|---|
| `h_i` | rupees held in asset i |
| `r_i,t` | asset i's return this month (from `00_raw_data/`) |

**Example:** Feb 2010 returns: Nifty +0.93%, Gold +3.17%, Liquid +0.31%. So Nifty ₹9,990.00 × 1.0093 = **₹10,083.18**; portfolio **₹10,083.18**.

**Code:** [`sip/engine.py` line 122](../sip/engine.py#L122): `h = h * (1.0 + rets[t])`

**Monthly return of the strategy (time-weighted)**

```
TWR_t = V_end,t / V_start,t − 1
```

| Term | What it stands for |
|---|---|
| `TWR_t` | the strategy's return in month t, ignoring the new money |
| `V_end,t` | value at the end of the month |
| `V_start,t` | value right after the instalment, before costs |

**Example:** Feb 2010: ₹10,083.18 / ₹10,000 − 1 = **+0.83%**.

**Code:** [`sip/engine.py` line 124](../sip/engine.py#L124): `twr[t] = h.sum() / start_value - 1.0`

## How it behaves over time

The allocation chart is one block: 100% Nifty for ten years. All the risk comes from one asset.

## Results

**Setup (identical for all six strategies):** ₹10,000 on the 1st of every month from
**Feb 2010 to Dec 2019** (119 instalments, **₹1,190,000 invested**),
0.1% cost on every trade, rupee returns from `00_raw_data/`.

| Measure | Value | What it means |
|---|---|---|
| Final value | **₹2,176,119** | What ₹1,190,000 grew into (1.83×) |
| XIRR | **11.7%** | Yearly return earned on your SIP money |
| Volatility | 15.3% | How bumpy the ride was (yearly) |
| Sharpe (vs 0%) | 0.76 | Return per unit of bumpiness |
| **Sharpe vs Liquid** | **0.29** | Return *above the T-bill rate* per unit of bumpiness (the fair one) |
| Max drawdown | -23.7% | Worst fall of the strategy itself |
| Worst fall in account | -11.2% | Biggest drop in rupees you would have seen |
| Selling per year | 0.0% | Share of the portfolio sold yearly |

For reference, a SIP kept **100% in Liquid** earned an XIRR of **7.3%**.

**Every possible 5-year SIP** (60 start dates from Feb 2010; only
5-year windows fit in the 10-year SIP period):

| Median XIRR | Worst XIRR | Best XIRR | % that lost money | Typical worst fall | Worst fall (any) |
|---|---|---|---|---|---|
| 12.2% | 5.6% | 18.3% | 0.0% | -8.0% | -9.5% |

**Through Indian market stress periods** (return of the strategy over each period):

| Period | Return |
|---|---|
| 2011 slowdown + euro crisis (Jan-Dec 2011) | -23.7% |
| 2013 taper tantrum, rupee crash (Jun-Aug 2013) | -8.3% |
| 2015-16 China/global sell-off (Mar 2015-Feb 2016) | -20.5% |
| 2018 IL&FS crisis (Sep-Oct 2018) | -10.9% |

### Charts

![Portfolio value vs amount invested](results/value.png)

![How the money is split over time](results/allocation.png)

![Fall from previous peak](results/drawdown.png)

### How each score is calculated

**XIRR (the yearly return earned on your SIP money)**

```
Σ_k CF_k / (1 + XIRR)^(t_k) = 0
```

| Term | What it stands for |
|---|---|
| `CF_k` | cash flow k: every instalment is negative (money in), the final value positive |
| `t_k` | time of cash flow k in years (0, 1/12, 2/12, …) |
| `XIRR` | the one yearly rate that makes all cash flows balance |

**Example:** If the SIP stopped after month 1: −₹10,000 at t = 0 and +₹10,083.18 at t = 1/12, so XIRR = (10,083.18 / 10,000.00)^12 − 1 = **10.45%**. Over all 119 instalments it is **11.71%**.

**Code:** [`sip/metrics.py` line 21](../sip/metrics.py#L21): `return np.sum(cashflows / (1.0 + r) ** years)`<br>[`sip/metrics.py` line 28](../sip/metrics.py#L28): `cfs = np.append(-res.contributions.values, res.total.iloc[-1])`

**Volatility (how bumpy the ride is)**

```
σ = std(TWR_1 … TWR_N) × √12
```

| Term | What it stands for |
|---|---|
| `σ` | yearly volatility |
| `TWR_t` | monthly returns of the strategy |
| `√12` | turns a monthly spread into a yearly one |

**Example:** First 12 months (Feb 2010 – Jan 2011): std of the 12 monthly returns = 5.489% × 3.464 = **19.01%**.

**Code:** [`sip/metrics.py` line 41](../sip/metrics.py#L41): `ann_vol = r.std() * np.sqrt(MONTHS)`

**Sharpe ratio (return per unit of bumpiness, against 0%)**

```
Sharpe = 12 × mean(TWR_t) / σ
```

| Term | What it stands for |
|---|---|
| `mean(TWR_t)` | average monthly return |
| `12 ×` | turns it into a yearly return |
| `σ` | yearly volatility (above) |

**Example:** First 12 months: 12 × 1.228% / 19.01% = **0.77**.

**Code:** [`sip/metrics.py` line 56](../sip/metrics.py#L56): `"Sharpe": excess.mean() * MONTHS / ann_vol,`

**Sharpe vs Liquid (return above the T-bill rate, per unit of bumpiness)**

```
Sharpe_vs_Liquid = 12 × mean(TWR_t − r_Liquid,t) / σ
```

| Term | What it stands for |
|---|---|
| `r_Liquid,t` | the Liquid fund's return that month (≈ 91-day T-bill) |
| `TWR_t − r_Liquid,t` | what the strategy earned above simply holding Liquid |
| `σ` | yearly volatility of the strategy |

**Example:** First 12 months: 12 × (1.228% − 0.471%) / 19.01% = **0.48**. This is the fair comparison when a near-cash asset is available (see `07_comparison/`).

**Code:** [`sip/metrics.py` line 71](../sip/metrics.py#L71): `out["Sharpe vs Liquid"] = excess_vs_rf.mean() * MONTHS / ann_vol`

**Max drawdown (worst fall of the strategy from a previous peak)**

```
G_t = Π_{s≤t} (1 + TWR_s)          MDD = min_t ( G_t / max_{s≤t} G_s − 1 )
```

| Term | What it stands for |
|---|---|
| `G_t` | growth of ₹1 invested in the strategy |
| `max_{s≤t} G_s` | highest value so far |
| `MDD` | the deepest percentage fall from a peak |

**Example:** First 12 months: deepest fall **-10.15%**. Whole SIP: see results below.

**Code:** [`sip/metrics.py` line 35](../sip/metrics.py#L35): `return float((series / peak - 1.0).min())`

**Worst fall in the account (what you would actually have seen)**

```
Worst fall = min_t ( V_t / max_{s≤t} V_s − 1 )
```

| Term | What it stands for |
|---|---|
| `V_t` | account value in rupees at the end of month t (includes new instalments) |

**Example:** First 12 months: **-3.03%** (new instalments hide small dips; the account ended Jan 2011 at ₹122,439 on ₹1,20,000 invested).

**Code:** [`sip/metrics.py` line 61](../sip/metrics.py#L61): `"Worst wealth drop": max_drawdown(res.total),`

**Selling per year (a proxy for tax events)**

```
Sell turnover = Σ_t sold_t / mean(V_t) / years
```

| Term | What it stands for |
|---|---|
| `sold_t` | rupees sold in month t |
| `mean(V_t)` | average account value |
| `years` | length of the SIP = 119 / 12 = 9.92 |

**Example:** Whole SIP: ₹0 sold / ₹897,208 average / 9.92 years = **0.00%** a year.

**Code:** [`sip/metrics.py` line 63](../sip/metrics.py#L63): `"Annual sell turnover": res.sold.sum() / res.total.mean() / (len(r) / MONTHS),`

## Strengths and weaknesses

**Strengths**
- **Highest return** of the six (XIRR 11.7%).
- Simplest rule; nothing is ever sold.

**Weaknesses**
- **Biggest falls**: the strategy fell -23.7% from its peak (during 2011), and -20.5% in the 2015-16 sell-off.
- Earned about 4.4% a year more than a 100% Liquid SIP (7.3%), but with 15.3% volatility against about 0.5% for Liquid.

## Files in this folder

| File | What it is |
|---|---|
| `strategy.py` | **The rule, in code.** Run it to regenerate `results/` |
| `results/summary.md` | All results on one page (also `summary.csv`) |
| `results/monthly.csv` | Month by month: instalment, rupees in each asset, target and actual split, bought/sold, costs |
| `results/rolling_5y_windows.csv` | XIRR and worst fall of every 5-year SIP |
| `results/crises.csv` | Return in each stress period |
| `results/*.png` | The three charts above |

## How to run

```bash
python 01_equity_sip/strategy.py
```

It reads the prepared returns table in `00_raw_data/`, runs the SIP month by month with the
shared engine in `sip/` (identical for all six strategies) and rewrites `results/`.
