# 08 · Forward Test: 2020–2025, and an Investor Starting Today

> **What this folder does:** the main study (folders 00–07) ends in Dec 2019. Here the data is
> extended to **Dec 2025** from public sources and cross-checked. Every strategy is then run,
> **with its rules unchanged**, on Jan 2020 – Dec 2025. Those six years played no part in
> building any rule, so this is an *out-of-sample* test. A fixed version of the optimiser is
> added, and the folder ends with what an investor starting on **1 Jan 2026** could expect,
> plus a live check of what actually happened in Jan–Sep 2026.

```
raw/ (AMFI fund NAVs, FRED USD/INR, World Bank gold, Nifty closes, RBI T-bills)
  └─ build_data.py ─► forward_returns_2020_2025.csv + monthly_returns_2000_2025.csv
  └─ verify_data.py ─► verification.md                       (cross-check ×2 per asset)
select_liquid_share.py (2010–2019 only) ─► fixed_optimizer.py (frozen)
run_forward.py ─► results/results.md        crosscheck.py ─► results/crosscheck.md
outlook_2026.py ─► results/outlook_2026.md
```

## 1. The data, Jan 2020 – Dec 2025

Only GitHub-hosted public data was reachable from the build machine, so each asset comes from the
**month-end NAVs of real Indian funds that track it**. The source is the AMFI daily NAV
archive, mirrored at [captn3m0/historical-mf-data](https://github.com/captn3m0/historical-mf-data).

| Asset | Built from (average of) | What it is |
|---|---|---|
| Nifty | UTI Nifty 50 Index Fund, HDFC Nifty 50 Index Fund (direct, growth) | Nifty 50 **total return** (dividends reinvested) less ~0.2%/yr fund cost |
| Gold | HDFC Gold ETF, Nippon India ETF Gold BeES | the **rupee gold price an Indian investor pays** (includes import duty) |
| Liquid | SBI Liquid Fund, ICICI Prudential Liquid Fund (direct, growth) | the T-bill / money-market rate |

**Monthly return of a fund**

```
r_t = NAV_t / NAV_(t−1) − 1          asset return = average of its two funds' r_t
```

| Term | What it stands for |
|---|---|
| `NAV_t` | the fund's net asset value on the last business day of month t |
| `r_t` | the fund's return that month (dividends are already inside a growth NAV) |

**Example:** Dec 2025: UTI 182.5506 / 183.0920 − 1 = −0.296%; HDFC 253.8755 / 254.6400 − 1 = −0.300%; Nifty = average = **−0.298%**. Over 2020–2025 the Nifty series returned **14.6%/yr**, gold **21.3%/yr**, Liquid **5.6%/yr**.

**Code:** [`sip/forward_data.py`](../sip/forward_data.py) (`fund_returns`, `forward_returns`). ETF unit splits (e.g. 1:10, which looks like a −90% month) are undone in `_undo_splits`.

## 2. Cross-checks (twice per asset): [`verification.md`](verification.md)

| Asset | Check 1: other funds (not used to build it) | Check 2: independent published figures |
|---|---|---|
| Nifty | Kotak Nifty 50 ETF: correlation **1.0000**, largest monthly gap 0.10% | Published year-end Nifty closes (12,168 → 26,130): our series = price change **+0.6% to +1.2% a year** every year, which is the dividends less fund costs. 2025: price +10.51%, ours +11.64% |
| Gold | Kotak and ICICI gold ETFs: correlation **0.997–0.998** | International gold (World Bank, USD) × USD/INR (FRED): the same trend; the gaps match India's **import-duty changes** (raised Jul 2022, cut Jul 2024 from 15% to 6%) |
| Liquid | Nippon and HDFC liquid funds: correlation **0.998–0.999**, gap ≤ 0.05%/month | RBI 91-day T-bill cut-offs: e.g. 2021 fund 3.36% vs T-bill 3.5–3.7%; 2023 fund 7.05% vs 6.92% |

An overlap check on Feb 2013 – Dec 2019 also compares the new kind of source with the
original series. Nifty: correlation **0.999**; the funds trail by 0.3–0.5%/yr because of costs
and slightly lower dividends than the 1.3% assumed. Gold: 0.97. Liquid: the funds earn about
0.4%/yr more. So switching sources in 2020 does not change what each asset is.

## 3. The fixed optimiser (Strategy 6b): [`fixed_optimizer.py`](fixed_optimizer.py)

The original optimisers measure risk against **0%**. A liquid fund (0.5% volatility) therefore
looks almost perfect, and it was pushed to the **70% cap**. The fix treats Liquid as **cash**:

```
w_Liquid = L (fixed)
Nifty / Gold sleeve = ½ · risk parity + ½ · max Sharpe on returns ABOVE Liquid:  max  w'(μ − μ_Liquid) / √(w'Σw)
```

| Term | What it stands for |
|---|---|
| `L` | the fixed Liquid share |
| `μ − μ_Liquid` | each asset's average return **above** the liquid fund, so cash is no longer a free lunch |
| `w'Σw` | the variance of the Nifty/Gold mix |

Everything else is the same as Strategy 6: re-fit every February on the previous 120 months, each
asset 10–70%, smart instalments, 5% band.

**Code:** [`sip/optimize.py`](../sip/optimize.py), `optimized_cash_buffer`.

**Choosing L without peeking** ([`results/selection_2010_2019.md`](results/selection_2010_2019.md)).
The candidates were 10%, 20% and 30%, and the rule was fixed in advance: highest Sharpe vs Liquid
on the **2010–2019 SIP only**. 10% won (0.291 vs 0.278 and 0.276), and it was frozen before any
2020–2025 result was run.

## 4. Results, Jan 2020 – Dec 2025: [`results/results.md`](results/results.md)

₹10,000/month, 72 months, ₹7,20,000 paid in. The **winner rule was set before running**: the
highest Sharpe vs Liquid.

| Strategy | Final value | XIRR | Volatility | Sharpe vs Liquid | Max drawdown |
|---|---|---|---|---|---|
| 1 · Equity (100% Nifty) | ₹11,38,663 | 15.1% | 17.8% | 0.55 | −28.2% |
| 2 · **Equal-weight (⅓ each)** | ₹12,01,678 | 16.9% | 7.3% | **1.18** | −6.8% |
| 3 · 60/20/20 | ₹11,68,631 | 16.0% | 10.7% | 0.83 | −15.4% |
| 4 · Risk parity | ₹10,10,664 | 11.2% | 3.4% | 1.16 | −3.0% |
| 5 · Max Sharpe | ₹10,08,323 | 11.1% | 3.4% | 1.13 | −3.2% |
| 6 · Optimized | ₹10,09,149 | 11.1% | 3.4% | 1.14 | −3.1% |
| 6b · **Fixed Optimized** | **₹13,28,220** | **20.3%** | 10.3% | 1.09 | −12.2% |

A 100% Liquid SIP earned 6.2%.

- **Winner by the pre-set rule: Equal-weight SIP**, with the best return per unit of risk. It
  also had the second-highest return and a −6.8% worst fall in the COVID crash, against −28.2%
  for 100% Nifty.
- **Highest return: the Fixed Optimized SIP**, at 20.3% a year. It turned ₹7.2 lakh into ₹13.3
  lakh, and over the whole 2010–2025 period it also ends with the most money (₹62.5 lakh vs
  ₹60.6 lakh for 100% Nifty).
- **The fix worked out of sample.** The original Optimized SIP stayed ~70% in Liquid and earned
  11.1%. The fixed version earned 20.3%.
- **Big caveat: 2020–2025 was a gold boom.** Rupee gold rose 21%/yr, including +72% in 2025.
  Mixes that hold a lot of gold (equal-weight at ⅓, the fixed optimiser at 33–49%) benefited most.
  In 2010–2019, when rupee gold rose only ~3%/yr, neither was the best: 60/20/20 led (Sharpe vs
  Liquid 0.33), with the fixed optimiser 0.29 and equal-weight 0.28.

## 5. Cross-check of the results: [`results/crosscheck.md`](results/crosscheck.md)

- **Different funds:** rebuilt from the funds *not* used above, every strategy's rank is
  identical, and XIRR differs by at most 0.17%.
- **Different code:** Strategies 1–3 were recomputed with a short independent loop and XIRR
  solver. The final values match the engine to the paisa.

## 6. An investor starting on 1 Jan 2026: [`results/outlook_2026.md`](results/outlook_2026.md)

**What to expect:** every past SIP of each length in Feb 2010 – Dec 2025, ₹10,000/month.

| 5-year SIP (₹6 lakh in) | Bad case (worst) | Typical (median) | Good case (best) |
|---|---|---|---|
| Equal-weight | ₹6.90 lakh (5.5%/yr) | ₹7.63 lakh (9.5%/yr) | ₹9.39 lakh (17.9%/yr) |
| Fixed Optimized | ₹6.45 lakh (2.9%/yr) | ₹7.85 lakh (10.7%/yr) | ₹10.18 lakh (21.3%/yr) |
| 100% Nifty | ₹5.56 lakh (−3.0%/yr) | ₹8.47 lakh (13.7%/yr) | ₹10.23 lakh (21.5%/yr) |

| 10-year SIP (₹12 lakh in) | Bad case | Typical | Good case |
|---|---|---|---|
| Equal-weight | ₹16.9 lakh (6.7%/yr) | ₹20.0 lakh (9.9%/yr) | ₹25.6 lakh (14.5%/yr) |
| Fixed Optimized | ₹16.4 lakh (6.1%/yr) | ₹21.4 lakh (11.1%/yr) | ₹29.0 lakh (16.8%/yr) |
| 100% Nifty | ₹15.2 lakh (4.6%/yr) | ₹24.8 lakh (13.9%/yr) | ₹28.3 lakh (16.4%/yr) |

No equal-weight or fixed-optimiser SIP of 3, 5 or 10 years in this history ever lost money.
100% Nifty earned the most in the typical case but had losing 3- and 5-year windows.

**Live check, Jan–Sep 2026** (published after the data cut-off, never used for any choice).
Nifty fell (−11.3% in March, −6.1% in September). Gold jumped +23.5% in January and then
swung. With ₹90,000 paid in, by 30 Sep 2026:

| Strategy | Value | Profit |
|---|---|---|
| Optimized (≈70% Liquid) | ₹90,810 | +₹810 (+0.9%) |
| Equal-weight | ₹88,479 | −₹1,521 (−1.7%) |
| Fixed Optimized | ₹87,532 | −₹2,468 (−2.7%) |
| 60/20/20 | ₹86,774 | −₹3,226 (−3.6%) |
| 100% Nifty | ₹84,216 | −₹5,784 (−6.4%) |

Nine months is far too short to judge a SIP; the 3- to 10-year tables above are the meaningful
guide. It does show the trade-off clearly. In a falling market the cautious, cash-heavy mix
loses least, the diversified mixes lose a little, and 100% equity loses most.

## How to run

```bash
python 08_forward_test/build_data.py           # 2020-2025 returns + joined 2000-2025 table
python 08_forward_test/verify_data.py          # cross-checks -> verification.md
python 08_forward_test/select_liquid_share.py  # chooses L on 2010-2019 only
python 08_forward_test/run_forward.py          # out-of-sample results
python 08_forward_test/crosscheck.py           # results cross-check
python 08_forward_test/outlook_2026.py         # expectation + live 2026 check
```

## Limitations

- **Different sources from 2020.** Real funds replace the price index + 1.3% dividend
  assumption, international gold and the T-bill index. The overlap check shows they behave
  alike, but fund costs (~0.2–0.5%/yr) and import duty are now included.
- **Six years, one regime.** 2020–2025 included a gold boom. The winner on these six years
  is not guaranteed to win the next six.
- **Taxes are not modelled.** Strategies that sell (60/20/20, fixed optimiser) would pay some
  capital-gains tax.
