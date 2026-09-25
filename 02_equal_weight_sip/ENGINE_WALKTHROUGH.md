# How the SIP engine runs Strategy 2: Equal-weight SIP (⅓ each)

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
| Where the target split comes from | fixed: ⅓ / ⅓ / ⅓ |
| How each instalment is split | pro-rata (split by the target) |
| When money is moved between jars | none (never sell) |

## 3. Where the target split comes from

**What it does in plain words:** the strategy writes down its fixed split once, and the
code copies that same split into every one of the 119 months. Nothing is ever recalculated.

```python
# 02_equal_weight_sip/strategy.py, line 21
WEIGHTS = {"Nifty": 1 / 3, "Gold": 1 / 3, "Liquid": 1 / 3}
```
The split, written as fractions of 1 (1.0 = 100%).

```python
# 02_equal_weight_sip/strategy.py, line 26
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

Target this month: Nifty 33.3% / Gold 33.3% / Liquid 33.3%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| ② Instalment ₹10,000 split into | ₹3,333.33 | ₹3,333.33 | ₹3,333.33 | ₹10,000.00 |
| ③ Holdings after buying | ₹3,333.33 | ₹3,333.33 | ₹3,333.33 | ₹10,000.00 |
| ③ Split after buying (share of total) | 33.3% | 33.3% | 33.3% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹3,330.00 | ₹3,330.00 | ₹3,330.00 | ₹9,990.00 |
| ⑥ This month's market return | +0.93% | +3.17% | +0.31% | |
| ⑥ **End of month** | ₹3,361.06 | ₹3,435.61 | ₹3,340.49 | ₹10,137.16 |

Strategy's own return this month (TWR): ₹10,137.16 ÷ ₹10,000.00 − 1 = **+1.37%**. Money paid in so far: ₹10,000.

### Mar 2010 (month 2 of 119)

The second month: last month's money is still in the jars, so this month's market move applies to **both** instalments.

Target this month: Nifty 33.3% / Gold 33.3% / Liquid 33.3%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹3,361.06 | ₹3,435.61 | ₹3,340.49 | ₹10,137.16 |
| ② Instalment ₹10,000 split into | ₹3,333.33 | ₹3,333.33 | ₹3,333.33 | ₹10,000.00 |
| ③ Holdings after buying | ₹6,694.39 | ₹6,768.94 | ₹6,673.82 | ₹20,137.16 |
| ③ Split after buying (share of total) | 33.2% | 33.6% | 33.1% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹6,691.07 | ₹6,765.58 | ₹6,670.51 | ₹20,127.16 |
| ⑥ This month's market return | +6.75% | -2.77% | +0.37% | |
| ⑥ **End of month** | ₹7,142.55 | ₹6,578.00 | ₹6,695.06 | ₹20,415.61 |

Strategy's own return this month (TWR): ₹20,415.61 ÷ ₹20,137.16 − 1 = **+1.38%**. Money paid in so far: ₹20,000.

### Nov 2011 (month 22 of 119)

The month the split had **drifted furthest** from ⅓ each. There is no rebalancing rule, so nothing is done about it: new money keeps going in ⅓ each.

Target this month: Nifty 33.3% / Gold 33.3% / Liquid 33.3%.

| Step | Nifty | Gold | Liquid | Total |
|---|---|---|---|---|
| ① Start of month (last month's end) | ₹69,406.42 | ₹96,096.53 | ₹74,893.68 | ₹240,396.63 |
| ② Instalment ₹10,000 split into | ₹3,333.33 | ₹3,333.33 | ₹3,333.33 | ₹10,000.00 |
| ③ Holdings after buying | ₹72,739.75 | ₹99,429.87 | ₹78,227.01 | ₹250,396.63 |
| ③ Split after buying (share of total) | 29.0% | 39.7% | 31.2% | 100% |
| ④ Rebalance? | rule is "none": skipped | | | |
| ⑤ Fee: ₹10.00 (0.1% of the ₹10,000.00 bought) | taken from all jars in proportion | | | −₹10.00 |
| ⑤ Holdings after fee | ₹72,736.85 | ₹99,425.90 | ₹78,223.89 | ₹250,386.63 |
| ⑥ This month's market return | -9.18% | +8.65% | +0.73% | |
| ⑥ **End of month** | ₹66,062.37 | ₹108,022.85 | ₹78,791.78 | ₹252,876.99 |

Strategy's own return this month (TWR): ₹252,876.99 ÷ ₹250,396.63 − 1 = **+0.99%**. Money paid in so far: ₹220,000.


## 6. After 119 months

Repeating this 119 times, **₹1,190,000** paid in became **₹1,850,460** by Dec 2019
(XIRR 8.6% a year). The jars ended at
Nifty ₹725,346 (39.2%), Gold ₹549,995 (29.7%), Liquid ₹575,119 (31.1%).

**Run it yourself:** `python 02_equal_weight_sip/strategy.py` prints the final line and
rewrites `results/`. Open `results/monthly.csv` to check any month in this page.
