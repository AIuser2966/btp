# 09 · Investor Tool (first version)

> **What this is:** the back-tested rules turned into a monthly instruction for a real investor:
> *"this month, put ₹X in Nifty, ₹Y in gold, ₹Z in a liquid fund (and sell nothing / sell this)"*.
> This first version is a command-line tool. It will later be refined into a website.

## How an investor uses it

**Once:** open three investments.

| Jar | What to buy |
|---|---|
| Nifty | a Nifty 50 index fund or ETF |
| Gold | a gold ETF (or gold fund) |
| Liquid | a liquid mutual fund |

**Every month:**

1. Note what your three investments are worth today (from your app or statement).
2. Run:
   ```bash
   python 09_investor_tool/invest.py --amount 10000 --holdings 120000 95000 40000 --risk moderate
   ```
   If you are starting from zero, leave out `--holdings`. `--risk` is `aggressive`, `moderate`
   (default) or `conservative`.
3. Place the buys (and any sells) it prints.

## Which strategy

**By default the tool picks the strategy for your risk profile.** Each profile has a risk aversion
λ (aggressive 2, moderate 4, conservative 8). The tool uses the strategy with the highest
mean-variance utility U = return above Liquid − (λ/2) × variance **on the out-of-sample years
2020–2025**, read from [`10_max_utility/results/winners.csv`](../10_max_utility/results/winners.csv).
Today that is the **Fixed Optimized SIP** for all three profiles (see [`10_max_utility/`](../10_max_utility)).

`--strategy` overrides the choice:

| `--strategy` | Rule | 2020–2025 result |
|---|---|---|
| `fixed-optimized` | Liquid 10%; Nifty/Gold re-fitted every February (½ risk parity + ½ max Sharpe vs Liquid); new money fills gaps first; full reset only if drift > 5% | highest U for every profile; XIRR 20.3%, worst fall −12.2% |
| `equal-weight` | ⅓ each, never sell | best Sharpe vs Liquid (1.18); XIRR 16.9%, worst fall −6.8% |
| `max-utility` | Strategy 7: maximises U for your λ each February | XIRR 16.2–18.6% depending on λ |
| `60-20-20` | 60/20/20, reset every January | XIRR 16.0%, worst fall −15.4% |
| `risk-parity`, `max-sharpe`, `optimized` | Strategies 4–6 (~70% Liquid) | XIRR about 11.1%, worst fall about −3% |
| `equity` | 100% Nifty | XIRR 15.1%, worst fall −28.2% |

## Example output

`python 09_investor_tool/invest.py --amount 10000 --holdings 100000 110000 25000 --strategy fixed-optimized`

```
Strategy : Fixed Optimized SIP (08): Liquid 10%, Nifty/Gold by ½ risk parity + ½ max Sharpe
Plan for : Jan 2026 instalment of ₹10,000
Data     : month-end returns up to Dec 2025; target fitted in Feb 2025 on the previous 120 months

       Target You hold now Buy this month (₹) After buying
Nifty   41.2%        42.6%                879        41.2%
Gold    48.8%        46.8%              9,121        48.6%
Liquid  10.0%        10.6%                  0        10.2%

Rebalance: largest gap from target after buying is 0.2% (≤ 5%): no selling needed.

How to place it:
  • buy ₹879 of a Nifty 50 index fund or ETF
  • buy ₹9,121 of a gold ETF (or gold fund)
```

## How it works

These are the same functions the back-test used. The tool's Jan 2026 target is the one the
back-test would use (checked in `tests/`).

```
month   = last data month + 1                                  (Jan 2026)
target  = fitted in the most recent February on the 120 months before it
buy     = pro-rata (w × amount)  or  smart split (fill gaps first)   ← sip/engine.py _smart_split
if band rule and max |share − target| > 5%:  trade everything back to target
```

## Planned refinements (next version / website)

- Fetch the latest month's data automatically, so it plans the current month and not Jan 2026.
- A web page: enter your holdings, see the split, keep a history.
- Taxes and exit loads when deciding whether to rebalance.

Educational output from a back-test model, not investment advice.
