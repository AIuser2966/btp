# Extra: Can Machine Learning Predict Future Returns and Improve the SIP?

> **Not part of the main six-strategy study.** This folder is an extension that tests
> whether ML return forecasts can improve the Optimized SIP (strategy 6).

This is an extension to the main study. Everything here comes from
`python extras/ai_forecasting/run_forecast.py` (USD) and the same with `--currency INR`.
The full tables are in `results/<currency>/forecast_results.md` in this folder.

---

## 1. The question

🧒 The Optimized SIP's "ambitious friend" (max Sharpe) needs a guess of **how much each
asset will return next year**. At the moment it guesses: *"the same as the last 10
years' average."* That's a lazy guess. Can a machine-learning model guess better, and
does a better guess make the SIP earn more?

We answer it in two parts:

* **Part A, forecast accuracy:** are the models' predictions closer to reality than a
  simple average?
* **Part B, SIP value:** if we feed the predictions into the optimizer, does the SIP
  actually do better?

A forecast can be "accurate" and still useless for investing (and the reverse), so we
test both.

---

## 2. How the forecasting works (`forecast.py` in this folder)

### 2.1 What we predict (the target)

📐 For every month *j* and each asset, the target is the **next 12 months' return**:

$$Y_j = \prod_{k=j+1}^{j+12} (1 + r_k) - 1$$

We use 12 months because the SIP re-fits its weights once a year.
(`build_targets`; checked by `test_targets_are_next_12_months`.)

### 2.2 What the model is allowed to look at (the features)

These are 13 inputs, all known **at the end of month j** (`build_features`):

| Feature | Formula | Intuition |
|---|---|---|
| `{asset} mom 3m`, `mom 12m` | growth over the last 3 or 12 months | **Momentum**: do winners keep winning? |
| `{asset} vol 12m` | std of the last 12 monthly returns × √12 | Is the asset in a calm or stormy phase? |
| `Bond yield` | 10-year Treasury yield | A bond's future return ≈ its yield today |
| `Bond yield chg 12m` | yield now − yield 12 months ago | Are rates rising (bad for bonds)? |
| `Dividend yield` | S&P 500 dividends ÷ price | **Valuation**: a high yield means stocks are cheap |
| `USDINR chg 12m` | change in rupees per dollar | Currency trend (matters for rupee investors) |

### 2.3 The models

| Model | In one line | Settings (fixed in advance, never tuned on test data) |
|---|---|---|
| **Historical mean** (benchmark) | "Next year = the average of all past years" | – |
| **Trailing 10y mean** | What the plain Optimized SIP already uses | 120 months |
| **Ridge regression** | A straight-line formula over the features, shrunk toward zero to avoid over-reacting | α = 10, standardized features |
| **Random forest** | 200 small decision trees ("if the yield > 6% and …"), averaged | depth 3, ≥ 20 samples per leaf |
| **Gradient boosting** | Trees built one after another, each fixing the last one's errors | 150 trees, depth 2, learning rate 0.03 |

🧒 Ridge is like drawing the best straight line through the dots. Trees are like playing
20 questions ("Is the bond yield above 6%? Is momentum positive?") and averaging many
games. The settings are deliberately **small and cautious**, because we have very little
data (see §5).

### 2.4 No cheating: walk-forward training (`walk_forward_forecasts`)

This is the most important part. A model making a forecast at the end of month *j* is
trained **only on rows k ≤ j − 12**. Those are the rows whose 12-month outcome had
already happened by month *j*. If we trained on row j − 5, its target would include
7 months that *haven't happened yet*. That is the classic look-ahead leak in ML
finance projects.

* The first model needs at least 96 training rows, so forecasts start in Jan 1983, just
  in time for the first SIP month.
* Models are **re-trained every 12 months**, and in between they make monthly
  predictions with the latest model.
* ✅ `test_forecasts_have_no_look_ahead` rewrites all returns after month 300, re-runs
  everything, and checks that every forecast before month 300 is unchanged.

### 2.5 How accuracy is scored (`evaluate`)

There are 510 monthly out-of-sample forecasts (Feb 1983 → Jul 2025; later months don't
have 12 months of future yet).

* 📐 **Out-of-sample R²** (Campbell & Thompson, 2008), the headline number:

$$R^2_{OS} = 1 - \frac{\sum (Y - \hat{Y}_{\text{model}})^2}{\sum (Y - \hat{Y}_{\text{hist. mean}})^2}$$

  **> 0** means the model beats "just use the historical average". **< 0** means it's
  *worse* than the lazy average.
* **Correlation** between forecast and actual.
* **Direction hit rate**: did it get the sign (up or down) right?
* **Pick best asset**: did the asset with the highest forecast really do best next
  year? Random guessing scores 33%.

### 2.6 Plugging forecasts into the SIP (`forecast_weights`)

Nothing else changes from the Optimized SIP. It still uses the same half risk parity,
the same 10–70% bounds, smart instalments and the 5% band. The **only** difference is
the max-Sharpe half:

$$w = \tfrac12\, w^{RP} + \tfrac12\, \arg\max_w \frac{w^\top \hat\mu_{\text{model}}}{\sqrt{w^\top \Sigma_{10y} w}}$$

where $\hat\mu$ is the model's 12-month forecast ÷ 12, made at the end of the month
before.

We also add an **Oracle**, which is given the *true* future returns. It's impossible in
real life, but it shows the **maximum** any forecast could ever add. It's the "perfect
exam score" to compare against.

---

## 3. Results (USD)

### Part A: forecast accuracy

**Out-of-sample R² vs historical mean** (`forecast_r2.png`):

| Model | Equity | Bonds | Gold |
|---|---|---|---|
| Ridge | −0.38 | **+0.19** | −0.87 |
| Random forest | −0.09 | **+0.25** | −0.49 |
| Gradient boosting | −0.23 | **+0.12** | −0.16 |
| Trailing 10y mean | −0.07 | +0.12 | +0.03 |

**Pick next year's best asset** (random = 33%): historical mean 46.5%, Ridge 37.5%,
random forest 43.1%, gradient boosting 41.2%.

What this says:

1. **Bonds are predictable.** All models beat the average, with correlations up to 0.5.
   The random forest's most-used input for bonds is the **bond yield** (39%), which
   makes economic sense: a bond bought at a 7% yield will earn roughly 7%.
2. **Equity and gold are not.** Every ML model is *worse* than the plain average. This
   matches decades of research (e.g. Welch & Goyal, 2008): stock returns one year ahead
   are close to unpredictable.
3. **Warning signs of overfitting** (`importance_rf.png`). The random forest predicts
   *gold* mainly from *bond volatility* (63%) and *bonds* partly from *gold momentum*
   (48%). There's no economic reason for either. The model has found patterns in noise
   that don't repeat, which is exactly why its gold R² is negative. (For equity it
   leans on the dividend yield, which is sensible.)
4. `forecast_vs_actual.png` shows it visually. The black line (reality) swings wildly,
   and none of the forecasts catch the 2001 or 2008 crashes in advance.

### Part B: does it improve the SIP? (Feb 1983 – Jul 2026)

| Strategy | XIRR | Sharpe | Worst wealth drop | Sell turnover/yr | Median 10-yr XIRR |
|---|---|---|---|---|---|
| Equity SIP | 11.3% | 0.99 | −48.3% | 0% | 11.8% |
| Equal-weight SIP | 9.0% | 1.29 | −18.2% | 0% | 8.3% |
| **Optimized SIP** (trailing mean) | 7.8% | **1.42** | −16.6% | 4.7% | 7.0% |
| Optimized + Ridge | **8.0%** | 1.34 | −16.8% | 15.1% | **8.0%** |
| Optimized + Random forest | 7.3% | 1.33 | −16.0% | 14.0% | 7.0% |
| Optimized + Gradient boosting | 7.2% | 1.28 | −16.7% | 14.2% | 7.1% |
| *Optimized + Oracle (perfect foresight)* | *10.8%* | *1.82* | *−14.3%* | *21.9%* | *10.1%* |

For rupee investors the pattern is the same: Optimized 13.8%, + Ridge 14.0%, + RF
13.4%, + GB 13.5%, Oracle 17.1%.

What this says:

1. **Perfect forecasts would be worth about 3 points of XIRR a year** (7.8% → 10.8%),
   with a Sharpe of 1.82 and a smaller drawdown. So forecasting is *worth trying*.
2. **Real models capture almost none of it.** Only Ridge improves XIRR, by +0.2 points
   over the full period and +1.0 point in the median 10-year window. Even Ridge has a
   *lower* Sharpe (1.34 vs 1.42) and **triples the selling** (15% vs 5% a year), which
   means more tax in real life. The tree models make the SIP *worse*.
3. **Accuracy ≠ profit.** The random forest had the *best* bond R², yet it produced the
   *worst* SIP result of the three models. Ridge was the *worst* at picking the best
   asset (37.5%), yet it produced the best SIP. What matters to the optimizer is the
   *relative* forecasts across assets at the right moments, not the accuracy of one
   asset in isolation.
4. **Be careful with the Ridge "win".** We tried three models and one did slightly
   better. With three tries, one modest win can easily be luck (the *multiple-testing*
   problem). It also appears in INR, but that uses the same underlying market history, so
   it isn't independent evidence.

---

## 4. Conclusion for the report

> Machine-learning forecasts of next-year returns were tested honestly (walk-forward,
> fixed hyper-parameters, no look-ahead). They can predict **bond** returns, mainly from
> the current bond yield, but **not equity or gold** returns, where they do worse than a
> simple average and show signs of overfitting. Perfect foresight would add about 3
> points of XIRR a year, but the real models capture at most a small fraction of that,
> at the cost of three times more trading. The **simple Optimized SIP remains the
> recommended strategy**. This result supports the project's theme: in portfolio
> allocation, *simple and robust beats complex and fragile*.

This is a **positive result for the project**, not a failure. Showing, with a fair
test, *that* and *why* the complex approach doesn't help is exactly what a good
research project does.

---

## 5. Limitations

* **Little independent data.** 43 years of 12-month targets means only about 43
  *non-overlapping* outcomes. Monthly rows overlap by 11 months, so the 510 scored
  forecasts are far from 510 independent tests, and ML models need much more data than
  that.
* **Few features.** Features like inflation, earnings, credit spreads and CAPE were
  left out (the bundled file has gaps in recent months). More features on this little
  data would likely overfit even more.
* **Hyper-parameters were fixed, not tuned.** This is deliberate, to avoid snooping.
  Tuning with a proper nested walk-forward might help a little, but it adds complexity.
* **Blending with risk parity** halves the impact of any forecast, good or bad. That's
  a safety feature, but it also limits upside (the Oracle only reaches 10.8%, below
  100% equity, for this reason plus the 70% cap).

## 6. Viva questions this raises

* **Why not a neural network or LSTM?** With about 43 independent yearly outcomes, a
  deep model would memorize noise. The trees already show overfitting, and bigger
  models make that worse.
* **Why out-of-sample R² and not ordinary R²?** In-sample R² always rises as you add
  features, even useless ones. Only out-of-sample performance against a naive benchmark
  shows real predictive power.
* **Why a 12-month gap in training?** Row k's label needs returns up to k + 12. To
  train at month j without peeking, every label must be complete, so k + 12 ≤ j.
* **What is the Oracle for?** It's the upper bound: "if forecasting were perfect, how
  much would it be worth?" It separates "forecasting is useless" (not true: it's worth
  about 3%) from "our forecasts aren't good enough" (true).

## 7. Using it: `06_optimized_sip/recommend.py`

```bash
python 06_optimized_sip/recommend.py --currency INR --amount 10000
python 06_optimized_sip/recommend.py --currency INR --amount 10000 --holdings 250000 180000 120000
python 06_optimized_sip/recommend.py --currency INR --amount 10000 --model Ridge
```

It fits the strategy on the latest 10 years of data and prints the target split and how
much of this month's instalment to put into each asset. If you give your current
holdings, it applies the smart rule and says whether a rebalance is due. It's an
educational tool on back-test data, not investment advice.

## References

* Campbell, J. Y., & Thompson, S. B. (2008). *Predicting excess stock returns out of
  sample: Can anything beat the historical average?* Review of Financial Studies, 21(4).
* Welch, I., & Goyal, A. (2008). *A comprehensive look at the empirical performance of
  equity premium prediction.* Review of Financial Studies, 21(4).
* Gu, S., Kelly, B., & Xiu, D. (2020). *Empirical asset pricing via machine learning.*
  Review of Financial Studies, 33(5).
