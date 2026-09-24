# 00 · Raw Data: From Market Prices to Monthly Returns

> **What this folder does:** it turns 50+ years of raw market data into **one clean table
> of monthly returns** for three assets. This table is the **only input** all six
> strategies use, so they are compared on exactly the same data.

```
raw/*.csv  ──►  build_returns.py  ──►  monthly_returns_usd.csv  (642 months × 3 assets)
                                  └─►  monthly_returns_inr.csv  (same, for a rupee investor)
```

## 1. The raw files (`raw/`)

| File | Source | What it contains | Used for |
|---|---|---|---|
| `sp500_shiller.csv` | Robert Shiller (Yale), S&P 500 dataset | Monthly index price **P**, annual dividend **D** | Equity return |
| `us10y_yield.csv` | FRED (US Federal Reserve) | 10-year government bond yield **y** (% per year) | Bond return |
| `gold_usd.csv` | Monthly gold price dataset | Gold price **G** (USD per ounce) | Gold return |
| `usdinr.csv` | FRED | Rupees per dollar **FX** | Rupee conversion |

All are public and bundled here, so anyone can rerun the project and get **identical
numbers** (reproducibility).

**Example rows (the first SIP month and the one before):**

| Month | S&P 500 (P) | Annual dividend (D) | Bond yield (y) | Gold (G) | ₹ per $ (FX) |
|---|---|---|---|---|---|
| Jan 1983 | 144.30 | 6.883 | 10.46% | 481 | 9.79 |
| Feb 1983 | 146.80 | 6.897 | 10.72% | 491 | 9.92 |

**Why these three assets?** They don't move together. Correlations of monthly returns,
Feb 1973 – Jan 1983:

    ρ(i, j) = Cov(r_i, r_j) / (σ_i × σ_j)

| Pair | Correlation |
|---|---|
| Equity – Bonds | 0.28 |
| Equity – Gold | 0.16 |
| Bonds – Gold | −0.03 |

Low correlations mean that when one falls, the others usually don't. That is
**diversification**, the reason a multi-asset SIP can reduce risk.

**Why start in 1973?** Gold only began trading at free-market prices after the Bretton
Woods system ended (1971–73), and the rupee series starts in January 1973.

## 2. The formulas: how each monthly return is built

A **return** is the growth of 1 unit of money over one month. We use returns rather than
prices because they are comparable across assets, and a portfolio's return is simply the
weighted average of its assets' returns:

    r_portfolio = w_Equity × r_Equity + w_Bonds × r_Bonds + w_Gold × r_Gold

### Equity: total return (price + dividend)

    r_Equity(t) = ( P(t) + D(t−1) / 12 ) / P(t−1) − 1

Shiller's dividend is per year, so one month's dividend is D/12.

**Feb 1983:**  (146.80 + 6.883/12) / 144.30 − 1 = 147.374 / 144.30 − 1 = **+2.13%**
(+1.73% from price, +0.40% from dividend)

Dividends matter: leaving them out would understate equity by about 2–4% a year.

### Gold: price return

    r_Gold(t) = G(t) / G(t−1) − 1

**Feb 1983:**  491 / 481 − 1 = **+2.08%**

### Bonds: built from the interest rate

We only have the bond **yield**, so we simulate a 10-year government bond fund:

1. At the start of month t, buy a new 10-year bond for 1.00 paying coupon **c = y(t−1)**.
2. At month end it has **T = 9 years 11 months** left; re-price it at the new yield **y(t)**.
3. Return = price change + one month of interest.

Bond price (coupons paid twice a year, n = 2T half-years):

    Price = (c/2) / (y/2) × [ 1 − (1 + y/2)^(−n) ] + (1 + y/2)^(−n)
            └── value of all coupons ──┘   └ value of the 1.00 back ┘

    r_Bonds(t) = Price( c = y(t−1), y = y(t), T = 10 − 1/12 ) − 1 + y(t−1) / 12

**Feb 1983:**

    c/2 = 0.05230,  y/2 = 0.05360,  n = 19.833
    (1.0536)^(−19.833) = 0.3551
    Price = (0.05230 / 0.05360) × (1 − 0.3551) + 0.3551 = 0.9844   →  −1.56%
    Interest = 10.46% / 12 = +0.87%
    r_Bonds = −1.56% + 0.87% = −0.69%

Check with duration (about 6 for this bond): −6 × (10.72% − 10.46%) ≈ −1.56% ✓.
Rates rose, so the bond lost value, exactly like a real bond fund (and like 2022).

### Optional: rupee investor

An Indian investor holding these assets also gains or loses on the dollar:

    r_INR(t) = (1 + r_USD(t)) × FX(t) / FX(t−1) − 1

**Feb 1983:** the dollar rose 9.9184 / 9.7938 = +1.27%, so equity in rupees =
1.0213 × 1.0127 − 1 = **+3.43%** (bonds +0.57%, gold +3.38%).

## 3. The output: `monthly_returns_usd.csv` / `monthly_returns_inr.csv`

**642 months (Feb 1973 – Jul 2026) × 3 assets**, in decimals (0.0213 = 2.13%):

| Month | Equity | Bonds | Gold |
|---|---|---|---|
| 1983-02 | 0.0213 | −0.0069 | 0.0208 |
| 1983-03 | 0.0387 | 0.0217 | −0.1446 |

**How the strategies use it:**

| Used for | How |
|---|---|
| Deciding the split (strategies 4–6) | The previous 120 months give the average return μ, volatility σ and covariance Σ |
| Running every SIP (all six) | Each month's holdings grow by (1 + r) |
| All results | XIRR, drawdowns and crash tests all come from the SIP values built on these returns |

The SIPs start in **Feb 1983**, the first month with 10 years of history before it, so
all six strategies use the same 522 months.

## How to rebuild

```bash
python 00_raw_data/build_returns.py
```

The code is `sip/data.py` (`equity_total_return`, `bond_total_return`, `gold_return`,
`load_returns`). A unit test checks that the saved tables match a fresh build from the
raw files.

## Limitations

- These are **US** assets (optionally viewed in rupees). Free Indian series (Nifty TRI,
  G-sec index, domestic gold) only go back about 15–20 years, which is too short for a
  strategy that needs 10 years of history before it starts.
- Shiller's S&P 500 prices are **monthly averages** of daily closes, which slightly smooths
  volatility.
- The bond fund is **simulated** from yields (no trading costs or credit risk).
- The latest dividends in Shiller's file are not yet published; the last known dividend
  yield is carried **forward** (never backward, so no look-ahead).
