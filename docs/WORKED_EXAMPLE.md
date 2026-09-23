# Layer 1 in 20 Steps: One Investor, Real Numbers

**The example:** *you* start a SIP of **10,000 a month in February 1983** and keep it
going every month until **July 2026**. That's 522 instalments, **5,220,000 invested** in
total. All numbers below are the project's actual outputs (the USD data series; the
rupee version gives different figures but works the same way).

---

## Part A: Getting the data ready

### Step 1: Define the question
You could put all 10,000 into a stock fund every month, or spread it across stocks,
bonds and gold. The project asks: **is there a simple rule for splitting the 10,000
that gives you a better balance of growth and safety than an all-stock SIP or a fixed
mix like 60/20/20?**

To answer it, we replay history: we pretend you followed each rule from 1983 to 2026
and see what would have happened to your money. This is called a **backtest**.

### Step 2: Choose the three assets
| Asset | What it is | Its personality |
|---|---|---|
| Equity | US S&P 500 (500 big companies) | Grows fastest, but crashes hard |
| Bonds | US 10-year government bonds | Slow and steady; pays interest |
| Gold | Gold price | Moves on its own, often rises in panics |

They were chosen because they **don't move together**. Over 1973–1983 the correlations
were: equity–bonds 0.28, equity–gold 0.16, bonds–gold −0.03 (1 = move identically,
0 = unrelated). When one falls, the others often don't, and that's what protects you.

### Step 3: Collect the raw data (1973–2026, monthly)
Here's what the files contain for your first two months:

| Month | S&P 500 price | Annual dividend | 10-yr bond yield | Gold ($/oz) | ₹ per $ |
|---|---|---|---|---|---|
| Jan 1983 | 144.30 | 6.883 | 10.46% | 481 | 9.79 |
| Feb 1983 | 146.80 | 6.897 | 10.72% | 491 | 9.92 |

These are stored in `data/raw/`, so anyone can rerun the project and get identical
numbers.

### Step 4: Turn prices into monthly returns (equity and gold)
A **return** is "how much did 1 unit of money grow this month?"

**Equity, Feb 1983.** You gain from the price rising **and** from the dividend. The
dividend is given per year, so one month's share is 6.883 / 12 = 0.574:

$$r = \frac{146.80 + 0.574}{144.30} - 1 = \frac{147.374}{144.30} - 1 = +2.13\%$$

**Gold, Feb 1983.** No dividend, just the price change:

$$r = \frac{491}{481} - 1 = +2.08\%$$

### Step 5: Build the bond return from interest rates
We only have the interest rate (yield), not a bond fund price, so we simulate one:

1. On 1 Feb you "buy" a new 10-year bond for 1.00 that pays **10.46% a year** (January's
   yield).
2. By the end of February, new bonds pay **10.72%**. Your bond pays less than new ones,
   so it's worth less. Using the bond price formula with 9 years 11 months left, its
   price is now **0.9844**, a loss of **−1.56%**.
3. But you also earned one month of interest: 10.46% / 12 = **+0.87%**.
4. February bond return = −1.56% + 0.87% = **−0.69%**.

This is why bonds can lose money when interest rates rise, as they did in 2022.

### Step 6: Put it in one table (and optionally convert to rupees)
Doing Steps 4–5 for every month gives a table of **642 months × 3 assets**. Its first
row is:

| Month | Equity | Bonds | Gold |
|---|---|---|---|
| Feb 1983 | +2.13% | −0.69% | +2.08% |

**Rupee version:** the dollar rose from ₹9.79 to ₹9.92 (+1.27%) that month, so for an
Indian investor, equity earned (1.0213 × 1.0127) − 1 = **+3.43%**.

---

## Part B: Deciding how to split your 10,000

### Step 7: Look only at the past, the last 10 years
It's 1 Feb 1983 and you need to decide your split. The rule is that you may only use
data you'd actually have had: the **120 months from Feb 1973 to Jan 1983**. Nothing
from February 1983 onwards is allowed. This "no peeking" rule is what makes the
backtest honest.

### Step 8: Measure each asset's return and risk over that window
| (Feb 1973 – Jan 1983) | Average return/yr (μ) | Volatility/yr (σ) |
|---|---|---|
| Equity | 7.6% | 14.1% |
| Bonds | 7.0% | 9.0% |
| Gold | **24.2%** | **29.5%** |

That was the 1970s: gold boomed (from about $65 to $480) while stocks struggled with
inflation. The optimizer only knows this history, and it will turn out to be a poor
guide to the 1980s, when stocks boomed. That's why we don't trust any single estimate
too much (Step 12).

We also compute the **covariance matrix** (Σ), which combines each asset's volatility
with the correlations from Step 2. It tells the optimizer how risky any *combination*
is.

### Step 9: The "careful" split (risk parity)
Rule: **each asset should contribute the same share of risk.**

For comparison, a simple ⅓ each would get **69% of its risk from gold alone**, because
gold is so jumpy. Risk parity fixes that by giving less money to jumpy assets:

| | Equity | Bonds | Gold |
|---|---|---|---|
| Risk-parity weights | 30.5% | 52.6% | 16.9% |
| Share of total risk | 33.3% | 33.3% | 33.3% ✓ |

It ignores the average returns entirely. It only needs the risk numbers, which are much
more reliable than return estimates.

### Step 10: The "ambitious" split (max Sharpe)
Rule: **get the most return per unit of risk**, i.e. maximize
(expected return) ÷ (volatility).

| | Equity | Bonds | Gold | Return/risk (1973–83) |
|---|---|---|---|---|
| Max-Sharpe weights | 11.4% | 66.4% | 22.2% | 1.16 |
| Risk parity (for comparison) | 30.5% | 52.6% | 16.9% | 1.10 |
| ⅓ each (for comparison) | 33.3% | 33.3% | 33.3% | 1.06 |

It likes gold (great past returns) and dislikes equity (poor past returns). It's
"ambitious" because it chases what did well in the past, which is exactly what can go
wrong.

### Step 11: Apply the limits
Both optimizers must obey two rules:
- The weights add up to 100% (all 10,000 is invested).
- **Each asset gets between 10% and 70%.**

In Feb 1983 max Sharpe happened to land inside the limits already (11.4% / 66.4% /
22.2%), so they changed nothing that year. But in **about two-thirds of years** the
unrestricted answer breaks them. For example, it would have put **0% in gold in 2023**
and only 3% in 1998, betting everything on the recent past. The limits keep every asset
in your SIP. A computer solver (SLSQP) finds the best weights that respect the rules.

### Step 12: Blend the two, which gives your target
$$\text{Target} = \tfrac12 \times \text{Risk parity} + \tfrac12 \times \text{Max Sharpe}$$

| | Equity | Bonds | Gold |
|---|---|---|---|
| Risk parity | 30.5% | 52.6% | 16.9% |
| Max Sharpe | 11.4% | 66.4% | 22.2% |
| **Your target (average)** | **21.0%** | **59.5%** | **19.6%** |
| **Of your 10,000** | **2,095** | **5,949** | **1,956** |

Averaging a careful estimate with an ambitious one reduces the damage if either is
wrong.

### Step 13: Update the target every year
Every February, the 10-year window moves forward one year and Steps 7–12 are repeated:

| Re-fit | Window used | Equity | Bonds | Gold |
|---|---|---|---|---|
| Feb 1983 | 1973–1983 | 21.0% | 59.5% | 19.6% |
| Feb 1984 | 1974–1984 | 31.9% | 53.6% | 14.5% |
| Feb 1985 | 1975–1985 | 41.0% | 45.0% | 14.0% |
| Feb 1986 | 1976–1986 | 37.7% | 48.4% | 13.9% |

As stocks recovered in the 1980s, the data showed it, and the target moved toward
equity automatically. The whole history of targets is in `weights.png`.

---

## Part C: Running your SIP month by month

### Step 14: What happens to your money each month
**Month 1 (Feb 1983).** You have nothing yet, so the 10,000 is split by the target:

| | Equity | Bonds | Gold | Total |
|---|---|---|---|---|
| Invested | 2,095 | 5,949 | 1,956 | 10,000 |
| After 0.1% cost | 2,093 | 5,943 | 1,954 | 9,990 |
| × Feb return | +2.13% | −0.69% | +2.08% | |
| **End of Feb** | **2,138** | **5,902** | **1,994** | **10,034** |

**Month 2 (Mar 1983): the "smart split".** The new 10,000 arrives, and the portfolio
would be worth 20,034. How much *should* each asset hold, and how much is it *short*?

| | Equity | Bonds | Gold |
|---|---|---|---|
| Should hold (target × 20,034) | 4,197 | 11,919 | 3,918 |
| Actually holds | 2,138 | 5,902 | 1,994 |
| **Short by (gets the new money)** | **2,060** | **6,017** | **1,924** |

The new money fills the gaps first. That month gold then fell **−14.5%**, but because
only about 20% of your money was in gold, and stocks (+3.9%) and bonds (+2.2%) rose,
your whole portfolio dipped by **less than 1%** that month. It ended March at
4,357 + 12,171 + 3,350 = 19,878 on 20,000 invested. An all-gold investor would have lost
14.5%. This is diversification working.

**Band rebalancing: the first time it happens (Feb 1985).** The yearly re-fit moved the
target to 41% / 45% / 14%. Your holdings (85,136 / 139,188 / 35,013) were 33% / 54% /
13%. Even after the smart instalment, bonds were **6.7 points over target**, which is
more than the 5-point limit. So the rule **rebalanced**: it sold 17,936 of bonds and
bought 16,255 of equity and 1,682 of gold. Over all 522 months this happened only
**23 times**. The rest of the time, the smart instalments alone kept things close to
target, with no selling.

**Costs:** every trade pays 0.1% (for example, 10 on a 10,000 purchase).

### Step 15: Run the comparison strategies with the same money
Five other versions of *you* invest the same 10,000 every month, over the same 522
months, with the same costs:

| Strategy | Rule |
|---|---|
| Equity SIP | All 10,000 into stocks |
| Equal-weight | 3,333 into each, never rebalanced |
| 60/20/20 | 6,000 / 2,000 / 2,000, reset to that mix every year |
| Risk-parity SIP | Only Step 9's split |
| Max-Sharpe SIP | Only Step 10's split |
| **Optimized SIP** | Step 12's blend (this is you) |

---

## Part D: Checking the result

### Step 16: Score each strategy
**Your Optimized SIP:**

| Date | Invested so far | Portfolio value |
|---|---|---|
| Jan 1993 (10 years) | 1,200,000 | 2,086,677 |
| Oct 2007 (before the crash) | 2,970,000 | 9,254,142 |
| Jul 2026 (the end) | **5,220,000** | **40,653,137** (7.8×) |

**XIRR = 7.8%.** That means your SIP grew as if every instalment had been in a bank
paying 7.8% a year. XIRR is the right measure for a SIP because each of the 522
instalments was invested for a different length of time.

**Everyone's score:**

| Strategy | Final value | XIRR | Worst fall in account | Return per risk (Sharpe) |
|---|---|---|---|---|
| Equity SIP | 119.1 M | **11.3%** | −48.3% | 0.99 |
| 60/20/20 | 73.3 M | 9.8% | −23.4% | 1.29 |
| Equal-weight | 58.5 M | 9.0% | −18.2% | 1.29 |
| Max-Sharpe SIP | 44.8 M | 8.1% | −17.2% | 1.37 |
| **Optimized SIP** | 40.7 M | 7.8% | **−16.6%** | **1.42** |
| Risk-parity SIP | 39.1 M | 7.7% | −16.3% | 1.44 |

- **Worst fall:** the largest drop from a peak in your account value. It's the moment
  investors panic.
- **Sharpe:** yearly return ÷ yearly bumpiness. Higher means a smoother ride for the
  same growth.

### Step 17: Was it luck? Try 403 different start dates
Maybe 1983 was a lucky start. So we run a separate 10-year SIP starting in **every month**
from Feb 1983 onwards (403 of them) and compare:

| If you had started in… | Equity SIP XIRR (10 yrs) | Optimized SIP XIRR (10 yrs) |
|---|---|---|
| Jan 1990 (great decade) | 21.2% | 8.5% |
| Jan 2000 (dot-com + 2008) | 1.2% | 7.4% |
| Apr 1999 (worst start) | **−7.2%** (lost money) | **6.1%** |

Across all 403 start dates:
- The Equity SIP's typical return was higher (11.8% vs 7.0%), but it **lost money in 3%
  of them**.
- The Optimized SIP **never** lost money, and its worst case was +3.5% a year.

### Step 18: Does re-learning every year beat "optimize once"?
A common shortcut is to find the best fixed mix from history and stick to it. We tested
that fairly:
1. Using only 1983–2004, try all 66 fixed mixes (0/0/100, 10/0/90, … 100/0/0) and pick
   the best: **30% / 60% / 10%**.
2. Run it on the **unseen** years 2004–2026.

| 2004–2026 (unseen) | XIRR |
|---|---|
| Best fixed mix from 1983–2004 | 6.4% |
| **Optimized SIP (re-fits every year)** | **8.0%** |

The fixed mix was "perfect" for the past, but the world changed. Re-learning every year
adapted.

### Step 19: Crash tests and "what if we'd picked other settings?"
**The 2008 crash, for you:**

| | Oct 2007 | Feb 2009 | Change |
|---|---|---|---|
| Equity SIP account | 15.70 M | 8.59 M | **−7.1 M** (even with new instalments) |
| **Optimized SIP account** | 9.25 M | 9.65 M | **+0.4 M** |

Similar pattern in other crashes (time-weighted returns): 1987 −25% vs −9%,
2000–02 −40% vs +2%, COVID 2020 −19% vs −3%. In **2022**, stocks *and* bonds fell
together, and the Optimized SIP fell −14% (vs −17% for equity). This is its weak spot.

**Sensitivity:** we reran with 5, 10 and 15-year windows and 3, 5 and 10% bands. XIRR
stayed between **7.2% and 8.1%** every time, so the result doesn't depend on lucky
settings.

### Step 20: Conclusion
For you, investing 10,000 a month from 1983 to 2026:

- **All in stocks** would have made you the most money (119 M, 11.3% a year). But you'd
  have watched the account fall almost **in half**, including losing 7 M in 2008, and in
  3% of 10-year periods you'd have ended with less than you put in.
- **The Optimized SIP** made less (40.7 M, 7.8% a year), but its worst fall was only
  **17%**. It went *up* during 2008, never lost money over any 10-year period, and had the
  **best return per unit of risk** of the strategies you could actually have followed at
  the time.
- **Honest caveat:** a plain ⅓-each split made more (58.5 M, 9.0%) with a similar worst
  fall (18%). Simple diversification is a very strong benchmark; the finance research
  says the same.

**Bottom line:** the Optimized SIP is a **safety-first** SIP. It trades some growth for
a much smoother ride, which matters most for someone near a goal (a house or
retirement), or who might panic and stop their SIP in a crash.
