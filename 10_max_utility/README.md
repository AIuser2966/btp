# 10 · One Score for Profit and Risk: Mean-Variance Utility

> **What this folder does:** it defines a single number that balances profit against risk for a
> given investor, and asks **which approach maximises it**. All seven strategies so far compete,
> plus a new **Strategy 7 (Max-Utility SIP)** that maximises the score directly. The winner for
> each kind of investor is what the investor tool (`09_investor_tool/`) recommends.

## 1. The score: mean-variance utility

```
U = (yearly return above Liquid) − (λ / 2) × (yearly volatility)²
```

| Term | What it stands for |
|---|---|
| yearly return above Liquid | 12 × average(monthly TWR − Liquid's return that month): the profit for taking risk |
| yearly volatility | std(monthly TWR) × √12, the risk |
| **λ** | **risk aversion**: how much one unit of variance hurts this investor |

Three investor profiles were fixed before any test: **λ = 2 aggressive, λ = 4 moderate, λ = 8
conservative**.

**Example:** 60/20/20, 2010–2019, moderate investor: return above Liquid 2.91%, volatility 8.81%, so
U = 2.91% − (4/2) × 8.81%² = 2.91% − 2 × 0.78% = **1.36%**.

**Code:** [`sip/metrics.py`](../sip/metrics.py), `utility_score`.

**Reading U:** it is a *certainty-equivalent* return. U = 1.36% means this investor is as happy with
the risky strategy as with a sure 1.36% a year above the liquid fund.

## 2. Where Lagrange comes in

Markowitz's problem is "most return for a given risk":

```
maximise  w'μ   subject to   w'Σw = σ²   and   Σ wᵢ = 1
Lagrangian:  L = w'μ − (λ/2)(w'Σw − σ²) − γ(Σ wᵢ − 1)
```

The multiplier **λ** on the risk constraint is exactly the risk aversion in U, so maximising U *is*
solving Markowitz's constrained problem (Markowitz 1952). Without bounds the answer is closed-form,
w = (1/λ) Σ⁻¹(μ − γ1). With our 10–70% bounds it is solved numerically by SLSQP, which itself works
on the Lagrange / KKT conditions.

## 3. Strategy 7: Max-Utility SIP ([`strategy.py`](strategy.py))

Every February, on the previous 120 months:

```
maximise   U(w) = w'(μ − μ_Liquid) − (λ/2) w'Σw        (yearly μ and Σ)
subject to 10% ≤ wᵢ ≤ 70%,  Σ wᵢ = 1
```

then the same engine as Strategies 4–6 (smart instalments, 5% band).

Because returns are measured **above Liquid**, Liquid's share is no longer fixed by hand. **λ decides
it** (Tobin 1958). Feb 2010, on Feb 2000 – Jan 2010:

| λ | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| Nifty / Gold / Liquid | 37 / 53 / 10 | 30 / 60 / 10 | 26 / 64 / 10 | 15 / 38 / **47** | 10 / 20 / **70** |

**Code:** [`sip/optimize.py`](../sip/optimize.py), `max_utility`.

## 4. Results: [`results/results.md`](results/results.md)

| Investor | Highest U, 2010–2019 (in-sample) | Highest U, 2020–2025 (out-of-sample) | Same test, other funds |
|---|---|---|---|
| Aggressive (λ=2) | 60/20/20 (2.13%) | **Fixed Optimized (10.25%)** | Fixed Optimized |
| Moderate (λ=4) | 60/20/20 (1.36%) | **Fixed Optimized (9.18%)** | Fixed Optimized |
| Conservative (λ=8) | Risk parity (0.44%) | **Fixed Optimized (7.04%)** | Fixed Optimized |

Strategy 7's U, and its rank among the eight strategies:

| | λ=2 | λ=4 | λ=8 |
|---|---|---|---|
| 2010–2019 | 1.61% (4th) | 0.64% (4th) | −0.46% (6th) |
| 2020–2025 | 9.04% (2nd) | 7.63% (2nd) | 5.55% (3rd) |

**What this shows**

1. **The best strategy depends on the investor.** In 2010–2019 the answer changes with λ: 60/20/20
   for bold and moderate investors, risk parity for cautious ones. That is the point of having λ.
2. **Maximising U directly did not maximise the U actually achieved.** Strategy 7 optimises exactly
   the score it is judged on, yet it never came first. The optimiser trusts the past 10 years' average
   returns (μ), which are very noisy estimates, so it over-bets on whatever did well recently. This is
   the classic "estimation error" problem of mean-variance optimisation (Michaud 1989, *Financial
   Analysts Journal*; DeMiguel et al. 2009). Rules that rely less on μ (fixed mixes, risk parity, or
   the fixed optimiser's ½ risk parity + ½ max Sharpe blend) held up better.
3. **The fixed optimiser had the highest U for every investor in 2020–2025**, and the ranking held on
   the alternative-fund data. The caveat from `08_forward_test` applies: 2020–2025 was a strong
   period for gold, which it held a lot of. In 2010–2019 it ranked 3rd, 2nd and 7th.
4. **100% Nifty never wins.** Its variance (17.8% volatility in 2020–2025) costs more than its extra return.

**What the tool does with it.** The rule, fixed in advance, is that for each profile the tool uses
the strategy with the highest U **out of sample** (`results/winners.csv`). Today that is the Fixed
Optimized SIP for all three profiles. If the out-of-sample data changes the winner, the tool
follows automatically.

## How to run

```bash
python 10_max_utility/run.py                                    # the competition -> results/
python 09_investor_tool/invest.py --amount 10000 --risk conservative
python 09_investor_tool/invest.py --amount 10000 --strategy max-utility --risk conservative
```

## Limitations

- **Variance treats gains and losses alike** and does not capture crashes well. A drawdown term
  (U − κ × |max drawdown|) is a natural extension.
- **λ is a choice.** 2/4/8 are conventional low/medium/high values. A real tool would set λ from a
  risk questionnaire.
- **Differences in U are estimates.** Six years is short, so only large gaps should be trusted.
