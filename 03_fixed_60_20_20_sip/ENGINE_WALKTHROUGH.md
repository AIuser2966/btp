# How the SIP engine runs Strategy 3: 60/20/20 SIP (Nifty / Gold / Liquid, reset yearly)

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
| Where the target split comes from | fixed: 60% Nifty / 20% Gold / 20% Liquid |
| How each instalment is split | pro-rata (split by the target) |
| When money is moved between jars | calendar: every 12 months |

## 3. Where the target split comes from

**What it does in plain words:** the strategy writes down its fixed split once, and the
code copies that same split into every one of the 119 months. Nothing is ever recalculated.

```python
# 03_fixed_60_20_20_sip/strategy.py, line 22
WEIGHTS = {"Nifty": 0.60, "Gold": 0.20, "Liquid": 0.20}
```
The split, written as fractions of 1 (1.0 = 100%).

```python
# 03_fixed_60_20_20_sip/strategy.py, line 27
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
The rule is `"calendar"`: the first test is true in every 12th month (Jan 2011, Jan 2012, …). In those months the code works out the trades below; in the other 11 months it skips them.

```python
# sip/engine.py, line 108
trade = w * h.sum() - h
```
For each jar: (what it *should* hold) − (what it holds). Positive = buy that much, negative = sell that much.

```python
# sip/engine.py, line 110
sold[t] = np.maximum(-trade, 0.0).sum()
```
Add up everything sold (for the fee, and as a record of tax events).

```python
# sip/engine.py, line 111
h = w * h.sum()
```
After the trades every jar is exactly at its target share.

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

Target this month: Nifty 60.0% / Gold 20.0% / Liquid 20.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| ② Instalment ₹10,000 split into | ₹6,000.00 | ₹2,000.00 | ₹2,000.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹6,000.00 | ₹2,000.00 | ₹2,000.00 | ₹10,000.00 |
| ③ Split after buying (share of total) | 60.0% | 20.0% | 20.0% | 100% |
| ④ Rebalance? | no, not the 12th month | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹5,994.00 | ₹1,998.00 | ₹1,998.00 | ₹9,990.00 |
| ⑥ This month's market return | +0.93% | +3.17% | +0.31% | |
| ⑥ **End of month** | ₹6,049.91 | ₹2,061.36 | ₹2,004.29 | ₹10,115.57 |

Strategy's own return this month (TWR): ₹10,115.57 ÷ ₹10,000.00 − 1 = **+1.16%**. Money paid in so far: ₹10,000.

### Mar 2010 (month 2 of 119)

The second month: last month's money is still in the jars, so this month's market move applies to **both** instalments.

Target this month: Nifty 60.0% / Gold 20.0% / Liquid 20.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹6,049.91 | ₹2,061.36 | ₹2,004.29 | ₹10,115.57 |
| ② Instalment ₹10,000 split into | ₹6,000.00 | ₹2,000.00 | ₹2,000.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹12,049.91 | ₹4,061.36 | ₹4,004.29 | ₹20,115.57 |
| ③ Split after buying (share of total) | 59.9% | 20.2% | 19.9% | 100% |
| ④ Rebalance? | no, not the 12th month | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹12,043.92 | ₹4,059.35 | ₹4,002.30 | ₹20,105.57 |
| ⑥ This month's market return | +6.75% | -2.77% | +0.37% | |
| ⑥ **End of month** | ₹12,856.58 | ₹3,946.80 | ₹4,017.03 | ₹20,820.42 |

Strategy's own return this month (TWR): ₹20,820.42 ÷ ₹20,115.57 − 1 = **+3.50%**. Money paid in so far: ₹20,000.

### Jan 2011 (month 12 of 119)

The **12th month**, so the yearly rebalance happens: jars that grew too big are trimmed and the money moved into the jars that fell behind.

Target this month: Nifty 60.0% / Gold 20.0% / Liquid 20.0%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹75,757.59 | ₹25,208.57 | ₹22,659.18 | ₹123,625.34 |
| ② Instalment ₹10,000 split into | ₹6,000.00 | ₹2,000.00 | ₹2,000.00 | ₹10,000.00 |
| ③ Holdings after buying | ₹81,757.59 | ₹27,208.57 | ₹24,659.18 | ₹133,625.34 |
| ③ Split after buying (share of total) | 61.2% | 20.4% | 18.5% | 100% |
| ④ Rebalance? | **yes**, 12th month | | | |
| ④ Trades to get back to target (− = sell) | −₹1,582.39 | −₹483.50 | ₹2,065.88 |  |
| ④ Holdings after rebalancing | ₹80,175.20 | ₹26,725.07 | ₹26,725.07 | ₹133,625.34 |
| ⑤ Fee: ₹14.13 (0.1% of ₹14,131.77 traded = ₹10,000 instalment + ₹2,065.88 rebalance buys + ₹2,065.88 sales) | taken from all jars in proportion | | | −₹14.13 |
| ⑤ Holdings after fee | ₹80,166.72 | ₹26,722.24 | ₹26,722.24 | ₹133,611.21 |
| ⑥ This month's market return | -10.14% | -3.77% | +0.61% | |
| ⑥ **End of month** | ₹72,038.91 | ₹25,715.74 | ₹26,885.35 | ₹124,640.01 |

Strategy's own return this month (TWR): ₹124,640.01 ÷ ₹133,625.34 − 1 = **-6.72%**. Money paid in so far: ₹120,000.


## 6. After 119 months

Repeating this 119 times, **₹1,190,000** paid in became **₹1,990,520** by Dec 2019
(XIRR 10.0% a year). The jars ended at
Nifty ₹1,192,650 (59.9%), Gold ₹425,810 (21.4%), Liquid ₹372,059 (18.7%).

**Run it yourself:** `python 03_fixed_60_20_20_sip/strategy.py` prints the final line and
rewrites `results/`. Open `results/monthly.csv` to check any month in this page.
