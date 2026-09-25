# How the SIP engine runs Strategy 6: Optimized SIP (½ risk parity + ½ max Sharpe)

This page follows the computer, step by step, as it runs this strategy. No finance or coding
background is needed: every word is explained, every line of code is shown with what it does,
and the end of the page works through real months with real rupee amounts.

## 1. Words used on this page

| Word | Meaning |
|---|---|
| **SIP** | Investing a fixed amount every month (here ₹10,000 on the 1st, Feb 2010 – Dec 2019, 119 months) |
| **Instalment** | One monthly payment of ₹10,000 |
| **Jar / holding** | The rupees currently sitting in one asset (Nifty, Gold or Liquid). The code calls the three jars together `h` |
| **Target split** | The percentages the strategy wants in each jar, e.g. 60% / 20% / 20% |
| **Return** | How much an asset grew or shrank in a month, e.g. +0.93% |
| **Fee** | 0.1% of every rupee bought or sold (₹10 on ₹10,000) |
| **Rebalance** | Selling from jars that grew too big and buying the ones that shrank, to get back to the target |
| **Drift** | How far the actual split has wandered from the target (the biggest gap, in percentage points) |
| **TWR** | "Time-weighted return": the strategy's own return that month, not counting the new money you added |
| **Smart instalment** | Instead of splitting the ₹10,000 by the target, pour it into the jars that are **below** target first. Keeps the split right without selling |
| **Band (5%)** | Only rebalance if some jar is more than 5 percentage points away from its target |
| **Optimiser** | A calculation that picks the target split from the past 10 years of data. It is re-run every February |
| **Look-back window** | The 120 months of past data the optimiser is allowed to use (never the future) |

## 2. The big picture

Think of **three jars** (Nifty, Gold, Liquid). On the 1st of every month from Feb 2010 to
Dec 2019 the computer:

1. takes ₹10,000,
2. decides how much goes into each jar,
3. maybe moves money between jars,
4. pays a small fee,
5. lets the market make each jar grow or shrink for a month,
6. writes everything down,

and then does it again, 119 times. The same engine (`sip/engine.py`) runs all six strategies;
only three **switches** differ. For this strategy they are set like this:

| Switch | This strategy |
|---|---|
| Where the target split comes from | re-calculated every February as **½ risk parity + ½ max Sharpe** from the past 120 months |
| How each instalment is split | smart (fill the gaps first) |
| When money is moved between jars | band: only if drift > 5% |

## 3. Where the target split comes from

**What it does in plain words:** the strategy doesn't know its split in advance. Every
February, a calculator (the *optimiser*) looks at the **previous 120 months only** and works out
a split. That split is then used for the next 12 months.

```python
# 06_optimized_sip/strategy.py, line 29
risk_parity = walk_forward_weights(returns, "risk_parity", lookback, lo=LOWER, hi=UPPER)
```
```python
# 06_optimized_sip/strategy.py, line 30
max_sharpe = walk_forward_weights(returns, "max_sharpe", lookback, lo=LOWER, hi=UPPER)
```
Calculate both kinds of split, each recalculated every 12 months.

```python
# sip/optimize.py, line 73
if current is None or (i - lookback) % reoptimise_every == 0:
```
"Is this the first month, or have 12 months passed since the last calculation?" If yes, recalculate:

```python
# sip/optimize.py, line 74
current = fn(rets.iloc[i - lookback:i], lo=lo, hi=hi)
```
Run the optimiser on the 120 months **before** this month (`i - lookback` up to `i`, not
including month `i` itself), so it can never see the future. Otherwise keep last year's split.

```python
# sip/optimize.py, line 16
res = minimize(objective, x0, method="SLSQP", bounds=[(lo, hi)] * n,
```
```python
# sip/optimize.py, line 17
constraints=({"type": "eq", "fun": lambda w: w.sum() - 1.0},),
```
Rules every answer must obey: each jar between 10% and 70%, and the three add up to 100%.

**Risk parity** (the careful one):

```python
# sip/optimize.py, line 43
rc = w * (cov @ w)
```
For a candidate split, work out how much risk each jar contributes.

```python
# sip/optimize.py, line 44
return ((rc - rc.mean()) ** 2).sum() * 1e8
```
Score the split by how *unequal* those risk shares are. The solver keeps adjusting the split
to make this score as small as possible, i.e. to make every jar's risk share equal.

**Max Sharpe** (the ambitious one):

```python
# sip/optimize.py, line 29
return max_sharpe_mu(rets.mean().values - rf / MONTHS, rets.cov().values, lo, hi)
```
From the 120 months, measure each asset's average return (`mean`) and how the assets wobble
together (`cov`, the covariance).

```python
# sip/optimize.py, line 34
return _solve(lambda w: -(w @ mu) / np.sqrt(w @ cov @ w), len(mu), lo, hi)
```
Score a split by return ÷ risk. The solver searches for the split with the highest score (the
minus sign is there because the solver is built to find the *smallest* number).

```python
# 06_optimized_sip/strategy.py, line 31
target = 0.5 * risk_parity + 0.5 * max_sharpe
```
The target is simply the average of the two splits.

## 4. What the engine does every month, line by line

Each numbered block is one or more lines of `sip/engine.py`, in the order they run.

**Before the first month (set-up):**

```python
# sip/engine.py, line 77
targets = strategy.target.reindex(idx)[returns.columns].values
```
Line up this strategy's target split for every SIP month.

```python
# sip/engine.py, line 83
h = np.zeros(n_a)
```
Start with three empty jars: `h = [0, 0, 0]` (Nifty, Gold, Liquid).

```python
# sip/engine.py, line 91
for t in range(n_t):
```
Now repeat everything below once per month, 119 times (`t` = 0 is Feb 2010, `t` = 118 is Dec 2019).

**① Read this month's plan**

```python
# sip/engine.py, line 92
w = targets[t]
```
```python
# sip/engine.py, line 93
cash = contributions.iloc[t]
```
`w` is this month's target split; `cash` is this month's instalment (₹10,000).

**② Decide how to split the instalment**

```python
# sip/engine.py, line 96
split = _smart_split(h, w, cash) if strategy.contribution == "smart" else w * cash
```
The rule is **smart**, so the code calls the smart splitter instead:

```python
# sip/engine.py, line 63
total = holdings.sum() + cash
```
Pretend the new money is already in: what would the whole pot be worth?

```python
# sip/engine.py, line 64
gap = np.maximum(target * total - holdings, 0.0)
```
For each jar: how many rupees short of its target share is it? (A jar that is already over target counts as 0 short.)

```python
# sip/engine.py, line 69
return gap / need * cash
```
If the jars are short by more than ₹10,000 in total, share the ₹10,000 out in proportion to how short each one is…

```python
# sip/engine.py, line 70
return gap + target * (cash - need)
```
…otherwise fill every gap completely and split whatever is left by the target.

**③ Put the money in the jars**

```python
# sip/engine.py, line 98
h = h + split
```
Each jar gets its share of the instalment added.

**④ Rebalance?**

```python
# sip/engine.py, line 103
if strategy.rebalance == "calendar" and months_since_rebal >= strategy.rebalance_every:
```
```python
# sip/engine.py, line 105
elif strategy.rebalance == "band" and h.sum() > 0:
```
The rule is `"band"`, so the second test runs every month:

```python
# sip/engine.py, line 106
do_rebal = np.abs(h / h.sum() - w).max() > strategy.band
```
Work out each jar's actual share (`h / h.sum()`), subtract its target (`w`), ignore the sign (`abs`) and take the biggest gap (`max`). Only if that gap is more than 5 percentage points does the code sell and rebuy to the target (the same trade lines as a yearly rebalance). In this strategy the smart instalments kept every jar close enough that this **never happened** in 119 months.

**⑤ Pay the fee**

```python
# sip/engine.py, line 115
turnover = np.maximum(buys, 0.0).sum() + sold[t]
```
```python
# sip/engine.py, line 116
costs[t] = turnover * cost_rate
```
Add up every rupee bought or sold this month and charge 0.1% of it.

```python
# sip/engine.py, line 117
start_value = h.sum()
```
Remember the pot's value *before* the fee: it is the starting point for this month's return.

```python
# sip/engine.py, line 118
h = h * (1.0 - costs[t] / start_value)
```
Take the fee out of all jars in proportion to their size.

**⑥ Let the market move, then write it down**

```python
# sip/engine.py, line 122
h = h * (1.0 + rets[t])
```
Every jar is multiplied by (1 + that asset's return this month). A +3% month turns ₹100 into
₹103; a −3% month turns it into ₹97. The *whole* jar moves, old money and new money alike.

```python
# sip/engine.py, line 124
twr[t] = h.sum() / start_value - 1.0
```
The strategy's own return this month = value at the end ÷ value at the start − 1.

Then the loop goes back to ① for the next month.

## 5. Real numbers, month by month

Each table follows one month through the steps above. Columns are the three jars; each row is
what the jars look like after that step. Every number comes from the engine itself (the same
values are in `results/monthly.csv`, which opens in Excel).

### Feb 2010 (month 1 of 119)

The very first month: all three jars start empty.

Target this month: Nifty 10.3% / Gold 19.7% / Liquid 70.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| ② Instalment ₹10,000 split into | ₹1,033.06 | ₹1,966.94 | ₹7,000.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹1,033.06 | ₹1,966.94 | ₹7,000.00 | ₹10,000.00 |
| ③ Split after buying (share of total) | 10.3% | 19.7% | 70.0% | 100% |
| ④ Rebalance? | biggest gap from target (drift) 0.00% (the smart instalment filled the gaps exactly): not more than 5% → no | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹1,032.03 | ₹1,964.97 | ₹6,993.00 | ₹9,990.00 |
| ⑥ This month's market return | +0.93% | +3.17% | +0.31% | |
| ⑥ **End of month** | ₹1,041.65 | ₹2,027.29 | ₹7,015.03 | ₹10,083.97 |

Strategy's own return this month (TWR): ₹10,083.97 ÷ ₹10,000.00 − 1 = **+0.84%**. Money paid in so far: ₹10,000.

### Mar 2010 (month 2 of 119)

The second month: last month's money is still in the jars, so this month's market move applies to **both** instalments.

Target this month: Nifty 10.3% / Gold 19.7% / Liquid 70.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹1,041.65 | ₹2,027.29 | ₹7,015.03 | ₹10,083.97 |
| ② Instalment ₹10,000 split into | ₹1,033.14 | ₹1,923.11 | ₹7,043.75 | ₹10,000.00 |
| ③ Holdings after buying | ₹2,074.79 | ₹3,950.40 | ₹14,058.78 | ₹20,083.97 |
| ③ Split after buying (share of total) | 10.3% | 19.7% | 70.0% | 100% |
| ④ Rebalance? | biggest gap from target (drift) 0.00% (the smart instalment filled the gaps exactly): not more than 5% → no | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹2,073.76 | ₹3,948.43 | ₹14,051.78 | ₹20,073.97 |
| ⑥ This month's market return | +6.75% | -2.77% | +0.37% | |
| ⑥ **End of month** | ₹2,213.69 | ₹3,838.96 | ₹14,103.50 | ₹20,156.15 |

Strategy's own return this month (TWR): ₹20,156.15 ÷ ₹20,083.97 − 1 = **+0.36%**. Money paid in so far: ₹20,000.

### Feb 2011 (month 13 of 119)

**February**: the optimiser recalculates the target from the 120 months Feb 2001 – Jan 2011. Last year's target was Nifty 10.3% / Gold 19.7% / Liquid 70.0%; the new one is Nifty 10.5% / Gold 19.5% / Liquid 70.0%. The smart instalment then sends more money to whichever jar is now below the new target, so no selling is needed.

Target this month: Nifty 10.5% / Gold 19.5% / Liquid 70.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹11,800.23 | ₹24,060.79 | ₹89,522.71 | ₹125,383.73 |
| ② Instalment ₹10,000 split into | ₹2,425.63 | ₹2,328.47 | ₹5,245.90 | ₹10,000.00 |
| ③ Holdings after buying | ₹14,225.85 | ₹26,389.27 | ₹94,768.61 | ₹135,383.73 |
| ③ Split after buying (share of total) | 10.5% | 19.5% | 70.0% | 100% |
| ④ Rebalance? | biggest gap from target (drift) 0.00% (the smart instalment filled the gaps exactly): not more than 5% → no | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹14,224.80 | ₹26,387.32 | ₹94,761.61 | ₹135,373.73 |
| ⑥ This month's market return | -3.03% | +3.95% | +0.55% | |
| ⑥ **End of month** | ₹13,794.16 | ₹27,428.96 | ₹95,283.52 | ₹136,506.64 |

Strategy's own return this month (TWR): ₹136,506.64 ÷ ₹135,383.73 − 1 = **+0.83%**. Money paid in so far: ₹130,000.

### Aug 2013 (month 43 of 119)

The month the split drifted **furthest** from target (the 2013 rupee crash: gold jumped, Nifty fell). Drift was still under 5%, so the band rule did **not** sell anything.

Target this month: Nifty 11.0% / Gold 19.0% / Liquid 70.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹50,985.85 | ₹98,085.27 | ₹332,150.30 | ₹481,221.42 |
| ② Instalment ₹10,000 split into | ₹2,060.30 | ₹0.00 | ₹7,939.70 | ₹10,000.00 |
| ③ Holdings after buying | ₹53,046.15 | ₹98,085.27 | ₹340,090.00 | ₹491,221.42 |
| ③ Split after buying (share of total) | 10.8% | 20.0% | 69.2% | 100% |
| ④ Rebalance? | biggest gap from target (drift) 0.97%: not more than 5% → no | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹53,045.07 | ₹98,083.28 | ₹340,083.08 | ₹491,211.42 |
| ⑥ This month's market return | -4.60% | +14.97% | +0.96% | |
| ⑥ **End of month** | ₹50,606.40 | ₹112,768.81 | ₹343,346.19 | ₹506,721.40 |

Strategy's own return this month (TWR): ₹506,721.40 ÷ ₹491,221.42 − 1 = **+3.16%**. Money paid in so far: ₹430,000.


## 6. After 119 months

Repeating this 119 times, **₹1,190,000** paid in became **₹1,774,231** by Dec 2019
(XIRR 7.8% a year). The jars ended at
Nifty ₹260,236 (14.7%), Gold ₹309,690 (17.5%), Liquid ₹1,204,305 (67.9%).

**Run it yourself:** `python 06_optimized_sip/strategy.py` prints the final line and
rewrites `results/`. Open `results/monthly.csv` to check any month in this page.
