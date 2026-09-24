# Extras (not part of the main study)

| Folder | What it is |
|---|---|
| [`us_data/`](us_data) | The **earlier version** of the whole study on US data, 1973–2026 (S&P 500, US 10-year bonds, gold; optionally in rupees). Same mechanics as the main study. Its raw data, loaders (`us_data.py`), returns tables and the original report, explainer and worked example (`docs/`) are kept here as an archive and as a long-history robustness check. |
| [`ai_forecasting/`](ai_forecasting) | Extension: can machine-learning forecasts (Ridge, random forest, gradient boosting) of next-12-month returns improve the Optimized SIP? Runs on the US data above. |

The main study (folders `00_` to `07_` at the top level) uses **Nifty 50, gold and a liquid fund, 2000–2019**.
