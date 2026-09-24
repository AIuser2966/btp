# 00 · Raw Data: From Daily Prices to Monthly Rupee Returns

> **What this folder does:** it turns the daily market file (Nifty 50, gold, liquid fund,
> 2000–2019) into **one table of monthly rupee returns**. That table is the **only input**
> all six strategies use, so they are compared on exactly the same data.

```
raw/final_market_data_2000_2019.csv  ─┐
raw/usdinr_daily_fred.csv            ─┴─►  build_returns.py  ─►  monthly_returns.csv  (239 months × 3)
                                                              └─►  monthly_prices.csv  (month-end values used)
```

## 1. The raw files (`raw/`)

| File | Source | Columns | Notes |
|---|---|---|---|
| `final_market_data_2000_2019.csv` | Your compiled data (daily, every calendar day 2000-01-01 to 2019-12-31) | `Nifty`, `Gold`, `Liquid` | Weekends/holidays repeat the last value |
| `usdinr_daily_fred.csv` | FRED series DEXINUS (US Federal Reserve), via [datasets/exchange-rates](https://github.com/datasets/exchange-rates) | `USDINR` (rupees per US dollar) | Blank on US holidays; the last available rate is used |

**What each column really is (checked, see section 4):**

| Column | What it is | Unit |
|---|---|---|
| `Nifty` | Nifty 50 **price** index (NSE closing values). Does **not** include dividends | index points |
| `Gold` | International gold price | **US dollars** per troy ounce, not rupees |
| `Liquid` | A liquid-fund index that grows every day by the 91-day T-bill yield ÷ 365 | index (100 on 1 Jan 2000) |

## 2. The formulas: how each monthly return is built

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

## 3. The output: `monthly_returns.csv`

**239 months (Feb 2000 – Dec 2019) × 3 assets**, as decimals (0.0093 = 0.93%):

| Month | Nifty | Gold | Liquid |
|---|---|---|---|
| 2010-01 | -0.0603 | -0.0181 | 0.0032 |
| **2010-02 (first SIP month)** | **0.0093** | **0.0317** | **0.0031** |

| 2000–2019 | Nifty (with dividends) | Gold (₹) | Liquid |
|---|---|---|---|
| Return per year | 12.4% | 11.5% | 7.0% |
| Volatility per year | 22.6% | 16.7% | 0.5% |

**Why the SIP starts in Feb 2010.** Strategies 4–6 need the previous **120 months** of
returns before they can decide a split. The data starts in Feb 2000, so the first possible
decision is Feb 2010. All six strategies use the same **119 months (Feb 2010 – Dec 2019)**.

| Used for | How |
|---|---|
| Deciding the split (strategies 4–6) | The previous 120 months give μ (average return) and Σ (covariance) |
| Running every SIP (all six) | Each month the holdings grow by (1 + r) |
| All results | XIRR, drawdowns and stress tests come from the SIP values built on these returns |

## 4. Data verification

`python 00_raw_data/verify_data.py` re-runs these checks (it downloads the reference files):

| Check | Reference | Result |
|---|---|---|
| Nifty closes, every trading day | NSE-sourced data 1990–2019 ([Sdaas/nifty-analysis](https://github.com/Sdaas/nifty-analysis)) | 4,812 days, **99.94% identical**. The only 3 differences are special weekend sessions (28 Apr 2012, Muhurat trading 3 Nov 2013 and 7 Nov 2018), none at a month end |
| Nifty closes 2015–2019 | Second NSE download ([abulbasar/data](https://github.com/abulbasar/data)) | 1,233 days, **99.92% identical** (only 7 Nov 2018 differs) |
| Gold (USD) | Monthly gold price series ([datasets/gold-prices](https://github.com/datasets/gold-prices)) | Monthly averages within **0.33%** on average → confirms the column is **USD/oz** |
| USD/INR | FRED DEXINUS | Used directly (it is the reference) |
| Liquid | Implied daily rate × 365 | Steps weekly (like weekly 91-day T-bill auctions): 9.25% (Jan 2000), 3.3% (2009), a spike to 12% in Aug 2013 (rupee crisis), 5–6% in 2019. Consistent with 91-day T-bill history; no downloadable T-bill series was reachable to match it day by day |

## How to rebuild

```bash
python 00_raw_data/build_returns.py     # writes monthly_returns.csv, monthly_prices.csv, correlations_2000_2010.csv
python 00_raw_data/verify_data.py       # optional: re-check against the public sources (needs internet)
```

## Limitations

- **Nifty dividends are a constant 1.3% a year**, not the actual dividends paid.
- **Gold is international gold in rupees.** Indian domestic gold (e.g. Gold BeES) also carries
  import duty, which rose from about 2% to 12.5% during 2012–2019, so domestic gold did slightly
  better than this series.
- **Liquid is an index built from the T-bill yield**, not an actual fund, so it has no fund
  expenses or credit risk.
- **Month-end sampling:** the last calendar day of the month is used; on weekends that is the
  Friday close repeated in the file.
