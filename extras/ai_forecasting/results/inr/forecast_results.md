# Forecasting study (INR)
Out-of-sample forecasts of next-12-month returns, 1983-02..2025-07 (510 monthly forecasts, re-fitted yearly, walk-forward).

## A1. Out-of-sample R² vs the historical mean (positive = better than the average)

| Model             |   Bonds |   Equity |   Gold |
|:------------------|--------:|---------:|-------:|
| Historical mean   |   0     |    0     |  0     |
| Ridge             |   0.076 |   -0.502 | -0.674 |
| Random forest     |  -0.041 |   -0.162 | -0.135 |
| Gradient boosting |   0.036 |   -0.187 | -0.188 |
| Trailing 10y mean |   0.124 |   -0.016 | -0.087 |

## A2. Correlation of forecast with actual

| Model             |   Bonds |   Equity |   Gold |
|:------------------|--------:|---------:|-------:|
| Historical mean   |   -0.05 |    -0.11 |  -0.27 |
| Ridge             |    0.4  |    -0.05 |   0.13 |
| Random forest     |    0.04 |    -0.04 |  -0.07 |
| Gradient boosting |    0.22 |     0.05 |   0.08 |
| Trailing 10y mean |    0.29 |     0.15 |  -0.17 |

## A3. Hit rates (direction of return; last column = picked next year's best asset)

| Model             | Bonds   | Equity   | Gold   | Pick best asset   |
|:------------------|:--------|:---------|:-------|:------------------|
| Historical mean   | 79.6%   | 86.3%    | 77.1%  | 47.6%             |
| Ridge             | 70.0%   | 85.9%    | 65.9%  | 37.5%             |
| Random forest     | 79.2%   | 86.3%    | 74.1%  | 44.9%             |
| Gradient boosting | 77.5%   | 84.1%    | 73.9%  | 44.5%             |
| Trailing 10y mean | 79.6%   | 82.5%    | 77.1%  | 44.5%             |

## B1. SIP back-test with forecasts plugged into the optimizer

SIP 1983-02..2026-07, 10,000/month, 10 bps.

| Strategy                               |   Invested |   Final value |   Wealth multiple | XIRR   | TWR CAGR   | Volatility   |   Sharpe |   Sortino | Max drawdown   |   Calmar | Worst wealth drop   | Annual sell turnover   | Annual cost drag   |
|:---------------------------------------|-----------:|--------------:|------------------:|:-------|:-----------|:-------------|---------:|----------:|:---------------|---------:|:--------------------|:-----------------------|:-------------------|
| Equity SIP                             |  5,220,000 |   698,895,984 |            133.89 | 16.9%  | 18.0%      | 12.8%        |     1.36 |      2.4  | -39.0%         |     0.46 | -38.4%              | 0.0%                   | 0.00%              |
| Equal-weight SIP                       |  5,220,000 |   309,463,387 |             59.28 | 14.4%  | 14.9%      | 8.4%         |     1.7  |      3.82 | -14.5%         |     1.03 | -13.2%              | 0.0%                   | 0.00%              |
| Optimized SIP                          |  5,220,000 |   255,750,794 |             48.99 | 13.8%  | 14.5%      | 7.9%         |     1.77 |      4.47 | -9.1%          |     1.6  | -9.0%               | 7.9%                   | 0.02%              |
| Optimized + Ridge                      |  5,220,000 |   270,336,450 |             51.79 | 14.0%  | 14.8%      | 8.0%         |     1.77 |      4.37 | -8.7%          |     1.69 | -8.6%               | 11.8%                  | 0.02%              |
| Optimized + Random forest              |  5,220,000 |   223,526,093 |             42.82 | 13.4%  | 14.2%      | 7.9%         |     1.73 |      4.2  | -10.5%         |     1.36 | -8.9%               | 9.2%                   | 0.02%              |
| Optimized + Gradient boosting          |  5,220,000 |   236,419,678 |             45.29 | 13.5%  | 14.4%      | 7.9%         |     1.75 |      4.19 | -9.0%          |     1.6  | -8.9%               | 11.8%                  | 0.02%              |
| Optimized + Oracle (perfect foresight) |  5,220,000 |   735,360,967 |            140.87 | 17.1%  | 17.7%      | 7.9%         |     2.12 |      5.98 | -7.9%          |     2.24 | -7.8%               | 21.9%                  | 0.04%              |

## B2. Rolling 10-year SIPs

| Strategy                               |   Windows | Median XIRR   | 5th pct XIRR   | Worst XIRR   | Best XIRR   | XIRR std   | % windows XIRR < 0   | % windows beating Equity SIP   | Median worst drop   | Worst drop (any window)   |
|:---------------------------------------|----------:|:--------------|:---------------|:-------------|:------------|:-----------|:---------------------|:-------------------------------|:--------------------|:--------------------------|
| Equity SIP                             |       403 | 16.8%         | 1.6%           | -4.7%        | 32.8%       | 9.0%       | 2.5%                 | 0.0%                           | -16.3%              | -30.8%                    |
| Equal-weight SIP                       |       403 | 12.3%         | 8.0%           | 6.5%         | 26.0%       | 4.8%       | 0.0%                 | 25.6%                          | -4.3%               | -7.6%                     |
| Optimized SIP                          |       403 | 12.2%         | 6.6%           | 5.0%         | 26.6%       | 5.0%       | 0.0%                 | 23.3%                          | -4.3%               | -8.1%                     |
| Optimized + Ridge                      |       403 | 12.5%         | 7.8%           | 6.8%         | 26.4%       | 4.5%       | 0.0%                 | 26.3%                          | -4.3%               | -8.1%                     |
| Optimized + Random forest              |       403 | 12.1%         | 6.8%           | 5.8%         | 26.2%       | 4.8%       | 0.0%                 | 24.8%                          | -4.5%               | -7.5%                     |
| Optimized + Gradient boosting          |       403 | 12.4%         | 7.0%           | 5.7%         | 26.3%       | 4.7%       | 0.0%                 | 25.3%                          | -4.4%               | -7.7%                     |
| Optimized + Oracle (perfect foresight) |       403 | 14.9%         | 11.1%          | 9.1%         | 27.7%       | 4.2%       | 0.0%                 | 40.4%                          | -4.0%               | -7.4%                     |

## B3. Stress periods

|                                             | Equity SIP   | Equal-weight SIP   | Optimized SIP   | Optimized + Ridge   | Optimized + Random forest   | Optimized + Gradient boosting   | Optimized + Oracle (perfect foresight)   |
|:--------------------------------------------|:-------------|:-------------------|:----------------|:--------------------|:----------------------------|:--------------------------------|:-----------------------------------------|
| 1987 crash (Sep-Nov 1987)                   | -25.7%       | -10.4%             | -8.8%           | -6.6%               | -10.3%                      | -5.4%                           | -5.3%                                    |
| Dot-com bust (Sep 2000-Sep 2002)            | -36.3%       | -13.6%             | 0.1%            | 2.9%                | -0.3%                       | -2.6%                           | 16.1%                                    |
| Global financial crisis (Nov 2007-Feb 2009) | -32.4%       | 4.1%               | 25.5%           | 21.5%               | 15.1%                       | 20.1%                           | 35.3%                                    |
| COVID crash (Feb-Mar 2020)                  | -15.1%       | -6.2%              | -1.6%           | -2.3%               | -2.0%                       | -3.0%                           | -2.7%                                    |
| 2022 rate shock (Jan-Sep 2022)              | -11.3%       | -9.8%              | -8.7%           | -8.4%               | -8.6%                       | -8.6%                           | -6.7%                                    |
