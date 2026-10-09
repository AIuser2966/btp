# Cross-check of the 2020-2025 results

## A. Same test, built from different funds

Main: {'Nifty': ['UTI_N50_IF', 'HDFC_N50_IF'], 'Gold': ['HDFC_GoldETF', 'GoldBeES_new'], 'Liquid': ['SBI_Liq', 'ICICI_Liq']}. Other: {'Nifty': ['Kotak_N50ETF'], 'Gold': ['Kotak_GoldETF', 'ICICI_GoldETF', 'HDFC_GoldETF'], 'Liquid': ['Nippon_Liq', 'HDFC_Liq']}.

| Strategy              |   XIRR (main data) |   XIRR (other funds) |   Sharpe vs Liquid (main) |   Sharpe vs Liquid (other funds) |   Rank by Sharpe vs Liquid (main) |   Rank (other funds) |   Rank by XIRR (main) |   Rank by XIRR (other funds) |
|:----------------------|-------------------:|---------------------:|--------------------------:|---------------------------------:|----------------------------------:|---------------------:|----------------------:|-----------------------------:|
| Equity SIP            |             0.1514 |               0.1531 |                    0.5499 |                           0.5574 |                            7.0000 |               7.0000 |                4.0000 |                       4.0000 |
| Equal-weight SIP      |             0.1693 |               0.1705 |                    1.1831 |                           1.1947 |                            1.0000 |               1.0000 |                2.0000 |                       2.0000 |
| 60/20/20 annual rebal |             0.1600 |               0.1613 |                    0.8310 |                           0.8401 |                            6.0000 |               6.0000 |                3.0000 |                       3.0000 |
| Risk-parity SIP       |             0.1118 |               0.1124 |                    1.1568 |                           1.1658 |                            2.0000 |               2.0000 |                5.0000 |                       5.0000 |
| Max-Sharpe SIP        |             0.1110 |               0.1116 |                    1.1274 |                           1.1367 |                            4.0000 |               4.0000 |                7.0000 |                       7.0000 |
| Optimized SIP         |             0.1113 |               0.1119 |                    1.1405 |                           1.1497 |                            3.0000 |               3.0000 |                6.0000 |                       6.0000 |
| Fixed Optimized SIP   |             0.2028 |               0.2043 |                    1.0943 |                           1.1057 |                            5.0000 |               5.0000 |                1.0000 |                       1.0000 |

Largest XIRR difference: 0.17%. Winner by Sharpe vs Liquid: main = Equal-weight SIP, other funds = Equal-weight SIP. Highest XIRR: main = Fixed Optimized SIP, other funds = Fixed Optimized SIP.

## B. Fixed mixes recomputed without the project's engine

| Strategy              |   Final value (independent) |   Final value (engine) |   XIRR (independent) |   XIRR (engine) |
|:----------------------|----------------------------:|-----------------------:|---------------------:|----------------:|
| Equity SIP            |              1,138,663.0525 |         1,138,663.0525 |               0.1514 |          0.1514 |
| Equal-weight SIP      |              1,201,678.4493 |         1,201,678.4493 |               0.1693 |          0.1693 |
| 60/20/20 annual rebal |              1,168,630.9050 |         1,168,630.9050 |               0.1600 |          0.1600 |

Largest final-value difference: ₹0.00.

