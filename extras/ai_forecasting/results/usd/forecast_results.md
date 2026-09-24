# Forecasting study (USD)
Out-of-sample forecasts of next-12-month returns, 1983-02..2025-07 (510 monthly forecasts, re-fitted yearly, walk-forward).

## A1. Out-of-sample R² vs the historical mean (positive = better than the average)

| Model             |   Bonds |   Equity |   Gold |
|:------------------|--------:|---------:|-------:|
| Historical mean   |   0     |    0     |  0     |
| Ridge             |   0.19  |   -0.381 | -0.873 |
| Random forest     |   0.245 |   -0.085 | -0.488 |
| Gradient boosting |   0.112 |   -0.233 | -0.16  |
| Trailing 10y mean |   0.123 |   -0.073 |  0.027 |

## A2. Correlation of forecast with actual

| Model             |   Bonds |   Equity |   Gold |
|:------------------|--------:|---------:|-------:|
| Historical mean   |    0.13 |    -0.13 |  -0.31 |
| Ridge             |    0.51 |    -0.08 |   0.08 |
| Random forest     |    0.47 |    -0.06 |  -0.04 |
| Gradient boosting |    0.34 |    -0.09 |   0.04 |
| Trailing 10y mean |    0.29 |    -0.01 |   0.04 |

## A3. Hit rates (direction of return; last column = picked next year's best asset)

| Model             | Bonds   | Equity   | Gold   | Pick best asset   |
|:------------------|:--------|:---------|:-------|:------------------|
| Historical mean   | 77.1%   | 82.0%    | 59.2%  | 46.5%             |
| Ridge             | 67.5%   | 75.5%    | 55.1%  | 37.5%             |
| Random forest     | 77.1%   | 83.7%    | 58.8%  | 43.3%             |
| Gradient boosting | 73.1%   | 75.7%    | 58.2%  | 41.6%             |
| Trailing 10y mean | 77.1%   | 77.5%    | 60.4%  | 44.5%             |

## B1. SIP back-test with forecasts plugged into the optimizer

SIP 1983-02..2026-07, 10,000/month, 10 bps.

| Strategy                               |   Invested |   Final value |   Wealth multiple | XIRR   | TWR CAGR   | Volatility   |   Sharpe |   Sortino | Max drawdown   |   Calmar | Worst wealth drop   | Annual sell turnover   | Annual cost drag   |
|:---------------------------------------|-----------:|--------------:|------------------:|:-------|:-----------|:-------------|---------:|----------:|:---------------|---------:|:--------------------|:-----------------------|:-------------------|
| Equity SIP                             |  5,220,000 |   119,106,074 |             22.82 | 11.3%  | 12.0%      | 12.3%        |     0.99 |      1.49 | -49.0%         |     0.24 | -48.3%              | 0.0%                   | 0.00%              |
| Equal-weight SIP                       |  5,220,000 |    58,470,676 |             11.2  | 9.0%   | 9.0%       | 6.9%         |     1.29 |      2.18 | -18.7%         |     0.48 | -18.2%              | 0.0%                   | 0.00%              |
| Optimized SIP                          |  5,220,000 |    40,653,139 |              7.79 | 7.8%   | 8.2%       | 5.7%         |     1.42 |      2.68 | -17.0%         |     0.48 | -16.6%              | 4.7%                   | 0.01%              |
| Optimized + Ridge                      |  5,220,000 |    43,343,120 |              8.3  | 8.0%   | 8.4%       | 6.2%         |     1.34 |      2.47 | -17.4%         |     0.48 | -16.8%              | 15.1%                  | 0.03%              |
| Optimized + Random forest              |  5,220,000 |    34,617,036 |              6.63 | 7.3%   | 7.9%       | 5.8%         |     1.33 |      2.41 | -16.3%         |     0.48 | -16.0%              | 14.0%                  | 0.03%              |
| Optimized + Gradient boosting          |  5,220,000 |    33,893,217 |              6.49 | 7.2%   | 7.8%       | 6.0%         |     1.29 |      2.26 | -17.0%         |     0.46 | -16.7%              | 14.3%                  | 0.03%              |
| Optimized + Oracle (perfect foresight) |  5,220,000 |   101,639,521 |             19.47 | 10.8%  | 11.0%      | 5.9%         |     1.82 |      3.93 | -14.5%         |     0.76 | -14.3%              | 21.9%                  | 0.04%              |

## B2. Rolling 10-year SIPs

| Strategy                               |   Windows | Median XIRR   | 5th pct XIRR   | Worst XIRR   | Best XIRR   | XIRR std   | % windows XIRR < 0   | % windows beating Equity SIP   | Median worst drop   | Worst drop (any window)   |
|:---------------------------------------|----------:|:--------------|:---------------|:-------------|:------------|:-----------|:---------------------|:-------------------------------|:--------------------|:--------------------------|
| Equity SIP                             |       403 | 11.8%         | 1.7%           | -7.2%        | 21.5%       | 5.6%       | 3.0%                 | 0.0%                           | -18.5%              | -41.2%                    |
| Equal-weight SIP                       |       403 | 8.3%          | 5.6%           | 4.8%         | 14.1%       | 2.0%       | 0.0%                 | 27.5%                          | -5.0%               | -13.9%                    |
| Optimized SIP                          |       403 | 7.0%          | 4.8%           | 3.5%         | 11.6%       | 1.8%       | 0.0%                 | 25.6%                          | -3.5%               | -11.5%                    |
| Optimized + Ridge                      |       403 | 8.0%          | 5.3%           | 4.4%         | 12.4%       | 1.8%       | 0.0%                 | 29.8%                          | -3.8%               | -13.4%                    |
| Optimized + Random forest              |       403 | 7.0%          | 4.5%           | 3.6%         | 11.2%       | 1.6%       | 0.0%                 | 25.1%                          | -4.1%               | -11.9%                    |
| Optimized + Gradient boosting          |       403 | 7.1%          | 4.4%           | 3.3%         | 11.5%       | 1.8%       | 0.0%                 | 22.1%                          | -4.6%               | -12.5%                    |
| Optimized + Oracle (perfect foresight) |       403 | 10.1%         | 7.2%           | 5.5%         | 14.6%       | 1.7%       | 0.0%                 | 37.2%                          | -3.1%               | -10.4%                    |

## B3. Stress periods

|                                             | Equity SIP   | Equal-weight SIP   | Optimized SIP   | Optimized + Ridge   | Optimized + Random forest   | Optimized + Gradient boosting   | Optimized + Oracle (perfect foresight)   |
|:--------------------------------------------|:-------------|:-------------------|:----------------|:--------------------|:----------------------------|:--------------------------------|:-----------------------------------------|
| 1987 crash (Sep-Nov 1987)                   | -25.0%       | -9.6%              | -9.2%           | -6.3%               | -12.6%                      | -4.9%                           | -4.7%                                    |
| Dot-com bust (Sep 2000-Sep 2002)            | -39.9%       | -16.5%             | 2.1%            | 0.2%                | 1.8%                        | -6.0%                           | 11.2%                                    |
| Global financial crisis (Nov 2007-Feb 2009) | -46.0%       | -12.8%             | 2.5%            | -2.5%               | -3.1%                       | -4.2%                           | 7.8%                                     |
| COVID crash (Feb-Mar 2020)                  | -18.8%       | -9.0%              | -3.2%           | -5.1%               | -3.9%                       | -6.9%                           | -2.2%                                    |
| 2022 rate shock (Jan-Sep 2022)              | -16.7%       | -14.7%             | -14.4%          | -14.0%              | -13.9%                      | -14.4%                          | -12.5%                                   |
