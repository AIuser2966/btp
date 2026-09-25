# How the SIP engine runs Strategy 1: Equity SIP (100% Nifty 50)

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
| Where the target split comes from | fixed: 100% Nifty / 0% Gold / 0% Liquid |
| How each instalment is split | pro-rata (split by the target) |
| When money is moved between jars | none (never sell) |

## 3. Where the target split comes from

**What it does in plain words:** the strategy writes down its fixed split once, and the
code copies that same split into every one of the 119 months. Nothing is ever recalculated.

```python
# 01_equity_sip/strategy.py, line 21
WEIGHTS = {"Nifty": 1.0, "Gold": 0.0, "Liquid": 0.0}
```
The split, written as fractions of 1 (1.0 = 100%).

```python
# 01_equity_sip/strategy.py, line 26
target = fixed_weights(returns.index, WEIGHTS)
```
Ask for a table with this split in every month…

```python
# sip/optimize.py, line 55
return pd.DataFrame([weights] * len(index), index=index)
```
…which is made by simply repeating the split once per month.

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
The rule is **pro-rata**, so the code takes the simple option after `else`: `w * cash`, i.e. each jar gets its target share of the ₹10,000.

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
Both tests are false because this strategy's rule is `"none"`, so `do_rebal` stays `False` and **nothing is ever sold**. The code jumps straight to the fee.

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

Target this month: Nifty 100.0% / Gold 0.0% / Liquid 0.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| ② Instalment ₹10,000 split into | ₹10,000.00 | ₹0.00 | ₹0.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹10,000.00 | ₹0.00 | ₹0.00 | ₹10,000.00 |
| ③ Split after buying (share of total) | 100.0% | 0.0% | 0.0% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹9,990.00 | ₹0.00 | ₹0.00 | ₹9,990.00 |
| ⑥ This month's market return | +0.93% | +3.17% | +0.31% | |
| ⑥ **End of month** | ₹10,083.18 | ₹0.00 | ₹0.00 | ₹10,083.18 |

Strategy's own return this month (TWR): ₹10,083.18 ÷ ₹10,000.00 − 1 = **+0.83%**. Money paid in so far: ₹10,000.

### Mar 2010 (month 2 of 119)

The second month: last month's money is still in the jars, so this month's market move applies to **both** instalments.

Target this month: Nifty 100.0% / Gold 0.0% / Liquid 0.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹10,083.18 | ₹0.00 | ₹0.00 | ₹10,083.18 |
| ② Instalment ₹10,000 split into | ₹10,000.00 | ₹0.00 | ₹0.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹20,083.18 | ₹0.00 | ₹0.00 | ₹20,083.18 |
| ③ Split after buying (share of total) | 100.0% | 0.0% | 0.0% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹20,073.18 | ₹0.00 | ₹0.00 | ₹20,073.18 |
| ⑥ This month's market return | +6.75% | -2.77% | +0.37% | |
| ⑥ **End of month** | ₹21,427.62 | ₹0.00 | ₹0.00 | ₹21,427.62 |

Strategy's own return this month (TWR): ₹21,427.62 ÷ ₹20,083.18 − 1 = **+6.69%**. Money paid in so far: ₹20,000.

### May 2010 (month 4 of 119)

A **falling** month: the market return is negative, so every rupee in the jar shrinks.

Target this month: Nifty 100.0% / Gold 0.0% / Liquid 0.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹31,624.64 | ₹0.00 | ₹0.00 | ₹31,624.64 |
| ② Instalment ₹10,000 split into | ₹10,000.00 | ₹0.00 | ₹0.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹41,624.64 | ₹0.00 | ₹0.00 | ₹41,624.64 |
| ③ Split after buying (share of total) | 100.0% | 0.0% | 0.0% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹41,614.64 | ₹0.00 | ₹0.00 | ₹41,614.64 |
| ⑥ This month's market return | -3.52% | +8.87% | +0.37% | |
| ⑥ **End of month** | ₹40,148.25 | ₹0.00 | ₹0.00 | ₹40,148.25 |

Strategy's own return this month (TWR): ₹40,148.25 ÷ ₹41,624.64 − 1 = **-3.55%**. Money paid in so far: ₹40,000.


## 6. After 119 months

Repeating this 119 times, **₹1,190,000** paid in became **₹2,176,119** by Dec 2019
(XIRR 11.7% a year). The jars ended at
Nifty ₹2,176,119 (100.0%), Gold ₹0 (0.0%), Liquid ₹0 (0.0%).

**Run it yourself:** `python 01_equity_sip/strategy.py` prints the final line and
rewrites `results/`. Open `results/monthly.csv` to check any month in this page.
