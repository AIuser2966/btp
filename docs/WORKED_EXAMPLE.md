# Layer 1 in 20 Steps: One Investor, Real Numbers (Nifty 50 / Gold / Liquid)

**The example:** *you* start a SIP of **₹10,000 a month in February 2010** and keep it going
every month until **December 2019**: 119 instalments, **₹1,190,000 invested**.
You follow the **Optimized SIP** (strategy 6). Every number below is the project's actual
output; every formula shows what each term means, a Feb 2010 example and the line of code.

---

## Part A: Getting the data ready (folder `00_raw_data/`)

### Step 1: The question
You could put all ₹10,000 into a Nifty fund every month, or split it across Nifty, gold and a
liquid fund. **Is there a simple rule for splitting it that balances growth and safety better
than 100% Nifty or a fixed mix like 60/20/20?** We replay 2010–2019 month by month (a backtest).

### Step 2: The three assets
| Asset | What it is | Its personality |
|---|---|---|
| Nifty 50 | India's 50 largest companies | Grows fastest, falls hardest |
| Gold | Gold, priced in rupees | Rises when the rupee falls or markets panic |
| Liquid | A liquid fund earning the 91-day T-bill rate | Almost never falls; grows steadily |

### Steps 3–6: From daily prices to monthly rupee returns


The SIP invests once a month, so each series is sampled at **month end**, then turned into
a return (the growth of ₹1 over the month).

**Month-end value**

```
X_month = last available daily value of X in that calendar month
```

| Term | What it stands for |
|---|---|
| `X` | any daily series (Nifty, Gold, Liquid, USD/INR) |
| `X_month` | the value used for that month |

**Example:** Feb 2010: Nifty 4,922.30, Gold $1,118.9, USD/INR 46.05, Liquid 188.1263 (Jan 2010: 4,882.05, $1,083.8, 46.08, 187.5356).

**Code:** [`sip/data.py` line 48](../sip/data.py#L48): `out = series.dropna().resample("ME").last()`

**Nifty 50 total return (price + dividends)**

```
r_Nifty,t = P_t / P_(t−1) − 1 + dy / 12
```

| Term | What it stands for |
|---|---|
| `P_t` | Nifty 50 month-end close this month |
| `P_(t−1)` | Nifty 50 month-end close last month |
| `dy` | Nifty dividend yield per year = 1.3% (assumption, see below) |
| `dy / 12` | one month of dividends |

**Example:** Feb 2010: 4,922.30 / 4,882.05 − 1 + 0.013 / 12 = +0.824% + +0.108% = **+0.933%**.

**Code:** [`sip/data.py` line 57](../sip/data.py#L57): `ret = price / price.shift(1) - 1 + dividend_yield / 12`

**Why add dividends?** An index fund investor receives the dividends of the 50 companies
(reinvested in the fund). The price index leaves them out, which would understate Nifty by
about 1–2% a year. NSE publishes a separate Total Return Index, but no source reachable from
this project had its history, so a constant **1.3%** a year is added. The
Nifty 50 dividend yield has historically been **1–2%** (1.35% in the May 2026 NSE factsheet;
[Bajaj AMC](https://www.bajajamc.com/knowledge-centre/nifty-50-dividend-yield)). It is one
constant in `sip/data.py` (`NIFTY_DIVIDEND_YIELD`) and easy to change.

**Gold in rupees**

```
G_INR,t = G_USD,t × FX_t
```

| Term | What it stands for |
|---|---|
| `G_USD,t` | gold price in US dollars per ounce at month end |
| `FX_t` | rupees per US dollar at month end |
| `G_INR,t` | gold price in rupees per ounce |

**Example:** Feb 2010: $1,118.9 × 46.05 = **₹51,525.35** per ounce (Jan 2010: $1,083.8 × 46.08 = ₹49,941.50).

**Code:** [`sip/data.py` line 65](../sip/data.py#L65): `return (gold_usd * fx).rename("Gold")`

**Gold return (for an Indian investor)**

```
r_Gold,t = G_INR,t / G_INR,(t−1) − 1   =   (1 + r_USD,t) × FX_t / FX_(t−1) − 1
```

| Term | What it stands for |
|---|---|
| `r_Gold,t` | gold's return in rupees |
| `r_USD,t` | gold's return in dollars |
| `FX_t / FX_(t−1)` | how much the dollar rose against the rupee |

**Example:** Feb 2010: ₹51,525.35 / ₹49,941.50 − 1 = **+3.171%**; equivalently (1 +3.239%) × (46.05 / 46.08) − 1.

**Code:** [`sip/data.py` line 71](../sip/data.py#L71): `return (g / g.shift(1) - 1).rename("Gold")`

**Why convert?** An Indian buys gold in rupees. Over 2000–2019 the rupee fell from about 43.5
to 71.4 per dollar, so rupee gold grew about **2.5% a year faster** than dollar gold. Using
dollar gold for an Indian SIP (as the earlier Gemini version did) understates gold.

**Liquid return**

```
L_d = L_(d−1) × (1 + y_d / 365)        r_Liquid,t = L_t / L_(t−1) − 1
```

| Term | What it stands for |
|---|---|
| `L_d` | liquid index on day d |
| `y_d` | 91-day T-bill yield that applies on day d |
| `L_t` | liquid index at month end |
| `r_Liquid,t` | the month's return |

**Example:** Feb 2010: the implied yield was 4.01% a year, so the index grew a little each day; month end 188.1263 / 187.5356 − 1 = **+0.315%**.

**Code:** [`sip/data.py` line 77](../sip/data.py#L77): `return (level / level.shift(1) - 1).rename("Liquid")`<br>[`sip/data.py` line 86](../sip/data.py#L86): `return ((level / level.shift(1) - 1) * 365).rename("Liquid implied rate")`

**Correlation (why these three assets)**

```
ρ(i, j) = Cov(r_i, r_j) / (σ_i × σ_j)
```

| Term | What it stands for |
|---|---|
| `ρ(i, j)` | correlation of assets i and j: +1 move together, 0 unrelated, −1 opposite |
| `Cov(r_i, r_j)` | how the two monthly returns move together |
| `σ_i` | volatility of asset i |

**Example:** Feb 2000 – Jan 2010 (the first window the optimisers see): Nifty–Gold **0.09**, Nifty–Liquid **-0.27**, Gold–Liquid **-0.09**. All low or negative: when Nifty falls, the other two usually don't (diversification).

**Code:** [`00_raw_data/build_returns.py` line 35](../00_raw_data/build_returns.py#L35): `corr = first_window.corr()`


**Result:** one table of 239 monthly returns (Feb 2000 – Dec 2019). Feb 2010, your first SIP
month: Nifty +0.93%, Gold +3.17%, Liquid +0.31%.

---

## Part B: Deciding how to split your ₹10,000 (folders `04_`, `05_`, `06_`)

### Steps 7–12: Look back 10 years, run two optimisers, average them
**Estimates from the past 120 months only (no look-ahead)**

```
μ_i  = (1/120) × Σ_{s=t−120}^{t−1} r_i,s
Σ_ij = (1/119) × Σ_s (r_i,s − μ_i)(r_j,s − μ_j)
```

| Term | What it stands for |
|---|---|
| `μ_i` | average monthly return of asset i over the last 120 months |
| `Σ_ij` | covariance of assets i and j (Σ_ii = variance; √(12·Σ_ii) = yearly volatility) |
| `r_i,s` | return of asset i in month s |
| `t` | the month being decided (re-fitted every 12 months) |

**Example:** For Feb 2010 the window is Feb 2000 – Jan 2010. Average return per year (12 × μ): Nifty 16.8% / Gold 15.3% / Liquid 6.2%; yearly volatility: Nifty 28.0% / Gold 16.8% / Liquid 0.5%. Liquid barely moves (volatility under 0.5%), which is what drives the result below.

**Code:** [`sip/optimize.py` line 74](../sip/optimize.py#L74): `current = fn(rets.iloc[i - lookback:i], lo=lo, hi=hi)`<br>[`sip/optimize.py` line 29](../sip/optimize.py#L29): `return max_sharpe_mu(rets.mean().values - rf / MONTHS, rets.cov().values, lo, hi)`

**Risk parity**

```
RC_i = w_i × (Σ w)_i          minimise  Σ_i (RC_i − mean(RC))²
```

| Term | What it stands for |
|---|---|
| `RC_i` | risk contribution of asset i (its share of portfolio variance) |
| `(Σ w)_i` | row i of the covariance matrix times the weights |
| `mean(RC)` | the average contribution; the goal is to make all RC_i equal |

**Example:** Feb 2010: weights Nifty 10.7% / Gold 19.3% / Liquid 70.0%. Liquid is capped at 70%, so the risk shares cannot be made equal: Nifty 46.3%, Gold 54.9%, Liquid -1.3% (Liquid adds almost no risk, and it is slightly negatively correlated with Nifty).

**Code:** [`sip/optimize.py` line 43](../sip/optimize.py#L43): `rc = w * (cov @ w)`<br>[`sip/optimize.py` line 44](../sip/optimize.py#L44): `return ((rc - rc.mean()) ** 2).sum() * 1e8`

**Max Sharpe**

```
maximise  (w · μ) / √(wᵀ Σ w)
```

| Term | What it stands for |
|---|---|
| `w · μ` | expected monthly return of the portfolio |
| `√(wᵀ Σ w)` | monthly volatility of the portfolio |
| `ratio` | return per unit of risk, measured against 0% (no risk-free rate subtracted) |

**Example:** Feb 2010: weights Nifty 10.0% / Gold 20.0% / Liquid 70.0% (Nifty at its 10% floor, Liquid at its 70% cap): expected 9.1% a year with 4.5% volatility, ratio 2.03. Because the ratio is measured against 0%, Liquid's steady ~6% with almost no volatility looks extremely attractive.

**Code:** [`sip/optimize.py` line 34](../sip/optimize.py#L34): `return _solve(lambda w: -(w @ mu) / np.sqrt(w @ cov @ w), len(mu), lo, hi)`

**Constraints (both optimisers)**

```
Σ_i w_i = 1        0.10 ≤ w_i ≤ 0.70
```

| Term | What it stands for |
|---|---|
| `w_i` | weight of asset i |
| `0.10 / 0.70` | every asset gets at least 10% and at most 70% |

**Example:** Without these limits the optimisers would put almost everything in Liquid: risk parity Nifty 1.5% / Gold 2.3% / Liquid 96.2%, max Sharpe Nifty 0.5% / Gold 0.4% / Liquid 99.1% (Feb 2010). The 70% cap is what keeps any Nifty and Gold in the portfolio.

**Code:** [`sip/optimize.py` line 16](../sip/optimize.py#L16): `res = minimize(objective, x0, method="SLSQP", bounds=[(lo, hi)] * n,`<br>[`sip/optimize.py` line 17](../sip/optimize.py#L17): `constraints=({"type": "eq", "fun": lambda w: w.sum() - 1.0},),`

**Optimized target (average of the two)**

```
w = ½ × w_RiskParity + ½ × w_MaxSharpe
```

| Term | What it stands for |
|---|---|
| `w_RiskParity` | weights from strategy 4 |
| `w_MaxSharpe` | weights from strategy 5 |

**Example:** Feb 2010: ½ × (Nifty 10.7% / Gold 19.3% / Liquid 70.0%) + ½ × (Nifty 10.0% / Gold 20.0% / Liquid 70.0%) = **Nifty 10.3% / Gold 19.7% / Liquid 70.0%**.

**Code:** [`06_optimized_sip/strategy.py` line 31](../06_optimized_sip/strategy.py#L31): `target = 0.5 * risk_parity + 0.5 * max_sharpe`

### Step 13: Update every February
The 120-month window moves forward a year each time:

| Re-fit | Nifty | Gold | Liquid |
|---|---|---|---|
| 2010-02 | 10.3% | 19.7% | 70.0% |
| 2011-02 | 10.5% | 19.5% | 70.0% |
| 2012-02 | 10.8% | 19.2% | 70.0% |
| 2013-02 | 11.0% | 19.0% | 70.0% |
| 2014-02 | 11.8% | 18.2% | 70.0% |
| 2015-02 | 12.4% | 17.6% | 70.0% |
| 2016-02 | 12.7% | 17.3% | 70.0% |
| 2017-02 | 12.8% | 17.2% | 70.0% |
| 2018-02 | 13.5% | 16.5% | 70.0% |
| 2019-02 | 14.7% | 15.3% | 70.0% |

Liquid stays pinned at the 70% cap every year; only the Nifty/Gold split moves.

---

## Part C: Running your SIP month by month (`sip/engine.py`)

### Step 14: What happens to your money each month
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

**Splitting the instalment (smart: fill the gaps first, never sell)**

```
V     = Σ_i h_i + C_t
gap_i = max(w_i × V − h_i, 0)
need  = Σ_i gap_i
buy_i = gap_i / need × C_t              if need ≥ C_t
buy_i = gap_i + w_i × (C_t − need)      if need < C_t
```

| Term | What it stands for |
|---|---|
| `h_i` | money currently held in asset i |
| `V` | portfolio value after adding the instalment |
| `w_i` | target weight of asset i |
| `gap_i` | how far asset i is below its target, in rupees |
| `need` | total of all gaps |
| `C_t` | this month's instalment |
| `buy_i` | money put into asset i |

**Example:** Month 1 (Feb 2010) starts empty, so every gap equals w_i × ₹10,000: Nifty ₹1,033.06, Gold ₹1,966.94, Liquid ₹7,000.00. Month 2 (Mar 2010): holdings Nifty ₹1,041.65 / Gold ₹2,027.29 / Liquid ₹7,015.03, V = ₹10,083.97 + ₹10,000 = ₹20,083.97; gaps Nifty ₹1,033.14 / Gold ₹1,923.11 / Liquid ₹7,043.75 (need = ₹10,000.00), so the instalment buys **Nifty ₹1,033.14 / Gold ₹1,923.11 / Liquid ₹7,043.75**.

**Code:** [`sip/engine.py` line 63](../sip/engine.py#L63): `total = holdings.sum() + cash`<br>[`sip/engine.py` line 64](../sip/engine.py#L64): `gap = np.maximum(target * total - holdings, 0.0)`<br>[`sip/engine.py` line 69](../sip/engine.py#L69): `return gap / need * cash`<br>[`sip/engine.py` line 70](../sip/engine.py#L70): `return gap + target * (cash - need)`

**Rebalancing (only when the drift is too big)**

```
drift = max_i | h_i / Σ_j h_j − w_i |
if drift > 5%:  trade_i = w_i × Σ_j h_j − h_i
```

| Term | What it stands for |
|---|---|
| `drift` | largest gap between an asset's actual share and its target |
| `h_i` | holding of asset i |
| `w_i` | target weight |
| `5%` | the tolerance band |
| `trade_i` | rupees bought (+) or sold (−) of asset i |

**Example:** After month 1 the actual split was Nifty 10.3% / Gold 20.1% / Liquid 69.6% against a target of Nifty 10.3% / Gold 19.7% / Liquid 70.0%: drift 0.43%, well under 5%, so nothing is sold. Over the whole SIP this rule fired **0 times** (the smart instalments kept the split on target).

**Code:** [`sip/engine.py` line 106](../sip/engine.py#L106): `do_rebal = np.abs(h / h.sum() - w).max() > strategy.band`<br>[`sip/engine.py` line 108](../sip/engine.py#L108): `trade = w * h.sum() - h`

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

**Example:** Feb 2010: (₹10,000 + ₹0) × 0.001 = **₹10**, taken from each asset in proportion, leaving Nifty ₹1,032.03 / Gold ₹1,964.97 / Liquid ₹6,993.00.

**Code:** [`sip/engine.py` line 116](../sip/engine.py#L116): `costs[t] = turnover * cost_rate`<br>[`sip/engine.py` line 118](../sip/engine.py#L118): `h = h * (1.0 - costs[t] / start_value)`

**Market move**

```
h_i ← h_i × (1 + r_i,t)
```

| Term | What it stands for |
|---|---|
| `h_i` | rupees held in asset i |
| `r_i,t` | asset i's return this month (from `00_raw_data/`) |

**Example:** Feb 2010 returns: Nifty +0.93%, Gold +3.17%, Liquid +0.31%. So Nifty ₹1,032.03 × 1.0093 = **₹1,041.65**, Gold ₹1,964.97 × 1.0317 = **₹2,027.29**, Liquid ₹6,993.00 × 1.0031 = **₹7,015.03**; portfolio **₹10,083.97**.

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

**Example:** Feb 2010: ₹10,083.97 / ₹10,000 − 1 = **+0.84%**.

**Code:** [`sip/engine.py` line 124](../sip/engine.py#L124): `twr[t] = h.sum() / start_value - 1.0`

### Step 15: Five other versions of you
Same ₹10,000, same 119 months, same costs: 100% Nifty, ⅓ each, 60/20/20, risk parity only,
max Sharpe only (folders `01_`–`05_`).

---

## Part D: Checking the result (`sip/metrics.py`, `07_comparison/`)

### Step 16: How your SIP is scored
**XIRR (the yearly return earned on your SIP money)**

```
Σ_k CF_k / (1 + XIRR)^(t_k) = 0
```

| Term | What it stands for |
|---|---|
| `CF_k` | cash flow k: every instalment is negative (money in), the final value positive |
| `t_k` | time of cash flow k in years (0, 1/12, 2/12, …) |
| `XIRR` | the one yearly rate that makes all cash flows balance |

**Example:** If the SIP stopped after month 1: −₹10,000 at t = 0 and +₹10,083.97 at t = 1/12, so XIRR = (10,083.97 / 10,000.00)^12 − 1 = **10.56%**. Over all 119 instalments it is **7.82%**.

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

**Example:** First 12 months (Feb 2010 – Jan 2011): std of the 12 monthly returns = 0.918% × 3.464 = **3.18%**.

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

**Example:** First 12 months: 12 × 0.789% / 3.18% = **2.98**.

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

**Example:** First 12 months: 12 × (0.789% − 0.471%) / 3.18% = **1.20**. This is the fair comparison when a near-cash asset is available (see `07_comparison/`).

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

**Example:** First 12 months: deepest fall **-1.37%**. Whole SIP: see results below.

**Code:** [`sip/metrics.py` line 35](../sip/metrics.py#L35): `return float((series / peak - 1.0).min())`

**Worst fall in the account (what you would actually have seen)**

```
Worst fall = min_t ( V_t / max_{s≤t} V_s − 1 )
```

| Term | What it stands for |
|---|---|
| `V_t` | account value in rupees at the end of month t (includes new instalments) |

**Example:** First 12 months: **0.00%** (new instalments hide small dips; the account ended Jan 2011 at ₹125,384 on ₹1,20,000 invested).

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

**Example:** Whole SIP: ₹0 sold / ₹784,830 average / 9.92 years = **0.00%** a year.

**Code:** [`sip/metrics.py` line 63](../sip/metrics.py#L63): `"Annual sell turnover": res.sold.sum() / res.total.mean() / (len(r) / MONTHS),`

**Everyone's scores (Feb 2010 – Dec 2019):**

| Strategy | Final value | XIRR | Max drawdown | Sharpe vs Liquid |
|---|---|---|---|---|
| Equity SIP | ₹2,176,119 | 11.7% | -23.7% | 0.29 |
| Equal-weight SIP | ₹1,850,460 | 8.6% | -6.5% | 0.28 |
| 60/20/20 annual rebal | ₹1,990,520 | 10.0% | -8.9% | 0.33 |
| Risk-parity SIP | ₹1,778,154 | 7.9% | -1.7% | 0.26 |
| Max-Sharpe SIP | ₹1,770,116 | 7.8% | -1.8% | 0.24 |
| Optimized SIP | ₹1,774,231 | 7.8% | -1.7% | 0.25 |

A 100% Liquid SIP earned 7.3%.

### Step 17: Every 5-year SIP (60 start dates)
Median XIRR: 100% Nifty 12.2%, 60/20/20
9.7%, Optimized 7.4%.
No strategy lost money over any 5-year window in this decade.

### Step 18: Optimise once vs re-learn every year
The best fixed mix on 2010–2014 was **{'Nifty': 0.6, 'Gold': 0.3, 'Liquid': 0.1}**. On the unseen years 2015–2019 it earned
10.8% (Sharpe vs Liquid 0.27),
versus 7.9% (0.23) for the Optimized SIP.

### Step 19: Stress periods
| Period | 100% Nifty | Optimized SIP |
|---|---|---|
| 2011 slowdown + euro crisis (Jan-Dec 2011) | -23.7% | 8.8% |
| 2013 taper tantrum, rupee crash (Jun-Aug 2013) | -8.3% | 4.0% |
| 2015-16 China/global sell-off (Mar 2015-Feb 2016) | -20.5% | 5.1% |
| 2018 IL&FS crisis (Sep-Oct 2018) | -10.9% | 0.4% |

Changing the look-back (60 / 90 / 120 months) or the band (3 / 5 / 10%) moved the Optimized
SIP's XIRR by less than 0.2 percentage points.

### Step 20: Verdict for you
- **100% Nifty** would have made the most (₹2,176,119, 11.7%) but fell
  -23.7% from its peak in 2011.
- **Your Optimized SIP** made ₹1,774,231 (7.8%) and never fell more than
  1.7%, because it was about **70% Liquid**. That is only
  0.5% a year more than a 100% Liquid SIP.
- **60/20/20** gave the best return above the T-bill rate per unit of risk (Sharpe vs Liquid
  0.33).

**Bottom line:** with the mechanics kept identical, the optimisers turn a cash-like Liquid
fund into a 70% cash portfolio. Very safe, but not better per unit of risk than a simple 60/20/20.
