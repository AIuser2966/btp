"""Build docs/SIP_Formula_Sheet.pdf: a 7-page sheet with only the formulas.

    python docs/make_formula_sheet.py        (needs Chromium or Chrome)

Page 1 data · 2 SIP engine · 3 Strategies 1-3 · 4 Strategy 4 · 5 Strategy 5 · 6 Strategy 6 · 7 scoring.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_formulas_pdf import F, find_chrome  # noqa: E402

OUT = HERE / "SIP_Formula_Sheet.pdf"
COLOURS = ["#2a78d6", "#7a5bd6", "#1a9e75", "#eda100", "#d6453d", "#0f6e8c"]


def card(title: str, latex: str | list[str], where: str, size: int = 16) -> str:
    latex = [latex] if isinstance(latex, str) else latex
    body = "<br>".join(F(x, size) for x in latex)
    return (f'<div class="card"><div class="ct">{title}</div><div class="fx">{body}</div>'
            f'<div class="wh">{where}</div></div>')


def page(tag: str, title: str, sub: str, cards: list[str], colour: str = "#334",
         cols: int = 2) -> str:
    return (f'<section style="--c:{colour}"><h1><span class="tag">{tag}</span>{title}</h1>'
            f'<p class="sub">{sub}</p><div class="grid g{cols}">{"".join(cards)}</div></section>')


# --------------------------------------------------------------------------- shared pieces
INSTALMENT = card("Instalment", r"C_t = A\,(1+g)^{\lfloor t/12 \rfloor}",
                  "<i>A</i> = ₹10,000 · <i>g</i> = 0 (no step-up) · <i>t</i> = 0 (Feb 2010) … 118 (Dec 2019)")
PRORATA = card("Split the instalment: pro-rata", r"x_i = w_i\,C_t",
               "<i>x<sub>i</sub></i> = rupees into jar <i>i</i> · <i>w<sub>i</sub></i> = target share")
SMART = card("Split the instalment: smart (fill the gaps first)",
             [r"V = \sum_i h_i + C_t \qquad G = \sum_i gap_i",
              r"gap_i = \max(w_i V - h_i,\ 0)",
              r"x_i = gap_i \, C_t / G \quad \mathrm{if}\ G \geq C_t",
              r"x_i = gap_i + w_i\,(C_t - G) \quad \mathrm{if}\ G < C_t"],
             "<i>h<sub>i</sub></i> = rupees already in jar <i>i</i> · <i>V</i> = wealth after the "
             "instalment · <i>gap<sub>i</sub></i> = shortfall of jar <i>i</i> vs target", 15)
BUY = card("Buy", r"h_i \leftarrow h_i + x_i", "“←” = becomes")
NO_REBAL = card("Rebalance: none", r"\mathrm{never\ rebalance}", "jars drift freely")
CALENDAR = card("Rebalance: calendar (every 12 months)",
                [r"\mathrm{if}\ n_{since} \geq 12:\quad trade_i = w_i \sum_j h_j - h_i",
                 r"h_i \leftarrow w_i \sum_j h_j \qquad n_{since} \leftarrow 0"],
                "<i>n<sub>since</sub></i> = months since the last rebalance · <i>trade<sub>i</sub></i> &gt; 0 buy, &lt; 0 sell")
BAND = card("Rebalance: band (drift > 5%)",
            [r"drift = \max_i \left| \frac{h_i}{\sum_j h_j} - w_i \right|",
             r"\mathrm{if}\ drift > 0.05:\quad h_i \leftarrow w_i \sum_j h_j"],
            "drift = the largest gap between a jar's actual share and its target")
FEE = card("Trading fee",
           [r"Fee = c \left(\sum_i buys_i + \sum_i sells_i\right)",
            r"h_i \leftarrow h_i \left(1 - \frac{Fee}{V_{start}}\right)"],
           "<i>c</i> = 0.001 (0.1%) · <i>V<sub>start</sub></i> = total just before the fee")
BUY_MARKET = card("Buy, then market move", [r"h_i \leftarrow h_i + x_i", r"h_i \leftarrow h_i\,(1 + r_{i,t})"],
                  "<i>r<sub>i,t</sub></i> = return of asset <i>i</i> in month <i>t</i> (fee is taken in between)")
MARKET = card("Market move", r"h_i \leftarrow h_i\,(1 + r_{i,t})",
              "<i>r<sub>i,t</sub></i> = return of asset <i>i</i> in month <i>t</i>")
TWR = card("Month's return (time-weighted)", r"TWR_t = \frac{V_{end}}{V_{start}} - 1",
           "<i>V<sub>end</sub></i> = total at month end · <i>V<sub>start</sub></i> = total after buying/rebalancing, before the fee")

MU_SIGMA = card("Look-back statistics (previous 120 months only)",
                [r"\mu_i = \frac{1}{120} \sum_{k=1}^{120} r_{i,t-k}",
                 r"\Sigma_{ij} = \frac{1}{119} \sum_{k=1}^{120} (r_{i,t-k} - \mu_i)(r_{j,t-k} - \mu_j)"],
                "μ = average monthly returns · Σ = covariance matrix (Σ<sub>ii</sub> = variance)")
BOUNDS = card("Constraints (solver: SLSQP)",
              r"0.10 \leq w_i \leq 0.70 \qquad \sum_i w_i = 1",
              "every asset between 10% and 70%, fully invested")
WALK = card("Walk-forward re-fit (every February)",
            r"w^{(Feb\,Y)} = \mathrm{optimiser}\left(r_{Feb\,(Y-10)}, \ldots, r_{Jan\,Y}\right)",
            "<i>Y</i> = 2010 … 2019 · target held for 12 months · no look-ahead")
RP = card("Risk parity (equal risk contributions)",
          [r"RC_i = w_i\,(\Sigma w)_i \qquad \overline{RC} = \frac{1}{3}\sum_i RC_i",
           r"w^{RP} = \arg\min_w \ \sum_i \left(RC_i - \overline{RC}\right)^2"],
          "<i>RC<sub>i</sub></i> = asset <i>i</i>'s contribution to portfolio variance "
          "(Σ<sub>i</sub> RC<sub>i</sub> = w<sup>T</sup>Σw)")
MS = card("Max Sharpe (best return per unit of risk)",
          [r"\mu_p = w^{\top}\mu \qquad \sigma_p = \sqrt{w^{\top} \Sigma\, w}",
           r"w^{MS} = \arg\max_w \ \frac{w^{\top}\mu}{\sqrt{w^{\top}\Sigma\, w}}"],
          "μ<sub>p</sub>, σ<sub>p</sub> = expected monthly return and volatility of the mix (rf = 0)")
AVG = card("Optimized SIP target", r"w^{Opt}_i = \frac{1}{2}\,w^{RP}_i + \frac{1}{2}\,w^{MS}_i",
           "the average of the risk-parity and max-Sharpe weights, each fitted with the same μ, Σ, limits")


def fixed_target(latex: str, what: str) -> str:
    return card("Target (fixed, every month)", latex, what)


# --------------------------------------------------------------------------- pages
def p_data() -> str:
    cards = [
        card("Month-end value", r"X_{month} = \mathrm{last\ available\ daily\ value\ of}\ X",
             "applied to Nifty, gold (USD), USD/INR and the Liquid index"),
        card("Nifty 50 total return", r"r_{Nifty,t} = \frac{P_t}{P_{t-1}} - 1 + \frac{dy}{12}",
             "<i>P<sub>t</sub></i> = month-end Nifty close · <i>dy</i> = 1.3% dividend yield per year"),
        card("Gold price in rupees", r"G_{INR,t} = G_{USD,t} \times FX_t",
             "<i>G<sub>USD</sub></i> = $ per troy ounce · <i>FX</i> = ₹ per US$ (FRED DEXINUS)"),
        card("Gold return (Indian investor)",
             r"r_{Gold,t} = \frac{G_{INR,t}}{G_{INR,t-1}} - 1 = (1 + r_{USD,t}) \frac{FX_t}{FX_{t-1}} - 1",
             "<i>r<sub>USD</sub></i> = gold's dollar return · FX ratio = rupee depreciation", 15),
        card("Liquid index (daily accrual)", r"L_d = L_{d-1} \left(1 + \frac{y_d}{365}\right)",
             "<i>y<sub>d</sub></i> = 91-day T-bill yield on day <i>d</i>"),
        card("Liquid return", r"r_{Liquid,t} = \frac{L_t}{L_{t-1}} - 1",
             "<i>L<sub>t</sub></i> = index at month end"),
        card("Implied T-bill rate (check)", r"y_d = \left(\frac{L_d}{L_{d-1}} - 1\right) \times 365", ""),
        card("Correlation", r"\rho_{ij} = \frac{\mathrm{Cov}(r_i, r_j)}{\sigma_i\,\sigma_j}",
             "+1 move together · 0 unrelated · −1 opposite"),
        card("General monthly return", r"r_{i,t} = \frac{P_{i,t}}{P_{i,t-1}} - 1",
             "growth of ₹1 over the month · 239 months (Feb 2000 – Dec 2019)"),
    ]
    return page("Data", "From daily prices to monthly rupee returns",
                "00_raw_data/build_returns.py · sip/data.py", cards)


def p_engine() -> str:
    cards = [INSTALMENT, PRORATA, SMART, BUY, NO_REBAL, CALENDAR, BAND, FEE, MARKET, TWR,
             card("Order inside every month",
                  r"C_t \rightarrow x_i \rightarrow h_i + x_i \rightarrow \mathrm{rebalance?} "
                  r"\rightarrow Fee \rightarrow \times(1 + r_{i,t}) \rightarrow TWR_t",
                  "repeated for t = 0 … 118 (119 months); each month starts from last month's jars", 15)]
    return page("Engine", "The SIP engine (shared by all six strategies)",
                "sip/engine.py · each strategy chooses: target w, pro-rata or smart split, "
                "and none / calendar / band rebalancing", cards)


def p_fixed() -> str:
    def block(n, name, target_latex, target_txt, rebal, colour):
        return (f'<div class="sblock" style="--c:{colour}"><div class="sname">Strategy {n} · {name}</div>'
                f'<div class="grid g3">{fixed_target(target_latex, target_txt)}{PRORATA}{rebal}</div></div>')
    body = (block(1, "Equity SIP (100% Nifty)", r"w = (1,\ 0,\ 0)", "Nifty / Gold / Liquid", NO_REBAL, COLOURS[0])
            + block(2, "Equal-weight SIP", r"w = (\frac{1}{3},\ \frac{1}{3},\ \frac{1}{3})", "one third each",
                    NO_REBAL, COLOURS[1])
            + block(3, "60/20/20 SIP", r"w = (0.60,\ 0.20,\ 0.20)", "Nifty / Gold / Liquid",
                    card("Rebalance: calendar", [r"\mathrm{if}\ n_{since} \geq 12:",
                                                 r"h_i \leftarrow w_i \sum_j h_j"],
                         "every 12 months (each January)", 15), COLOURS[2]))
    common = (f'<div class="sname" style="margin-top:8px">Then, for all three, every month</div>'
              f'<div class="grid g2">{INSTALMENT}{BUY}{FEE}{MARKET}{TWR}</div>')
    return (f'<section><h1><span class="tag">S1–S3</span>Strategies 1–3: fixed targets</h1>'
            f'<p class="sub">01_equity_sip · 02_equal_weight_sip · 03_fixed_60_20_20_sip</p>{body}{common}</section>')


def p_opt(n: int, name: str, folder: str, objective: list[str]) -> str:
    cards = [MU_SIGMA, *objective, BOUNDS, WALK, INSTALMENT, SMART, BUY_MARKET, BAND, FEE, TWR]
    return page(f"S{n}", name, f"{folder}/strategy.py · target from "
                "sip/optimize.py, then the shared engine with smart split and 5% band", cards,
                COLOURS[n - 1])


def p_scoring() -> str:
    cards = [
        card("XIRR (money-weighted return per year)",
             r"\sum_{k=0}^{N-1} \frac{-C_k}{(1+XIRR)^{k/12}} + \frac{V_{final}}{(1+XIRR)^{N/12}} = 0",
             "solved for XIRR (brentq) · <i>N</i> = 119 instalments · <i>V<sub>final</sub></i> = value at Dec 2019", 15),
        card("TWR CAGR (strategy's own growth rate)",
             r"CAGR = \left[\prod_{t=1}^{N} (1 + TWR_t)\right]^{12/N} - 1", ""),
        card("Volatility (per year)", r"\sigma = \mathrm{std}(TWR_t) \times \sqrt{12}", ""),
        card("Sharpe (vs 0%)", r"Sharpe = \frac{12 \times \mathrm{mean}(TWR_t)}{\sigma}", "risk-free rate = 0"),
        card("Sharpe vs Liquid", r"Sharpe_{Liq} = \frac{12 \times \mathrm{mean}(TWR_t - r_{Liquid,t})}{\sigma}",
             "only the return above the T-bill (Liquid) counts"),
        card("Sortino", [r"DD = \sqrt{\mathrm{mean}\left(\min(TWR_t,\ 0)^2\right)} \times \sqrt{12}",
                         r"Sortino = \frac{12 \times \mathrm{mean}(TWR_t)}{DD}"], "only downside moves count as risk"),
        card("Maximum drawdown", [r"G_t = \prod_{k \leq t} (1 + TWR_k)",
                                  r"MDD = \min_t \left( \frac{G_t}{\max_{k \leq t} G_k} - 1 \right)"],
             "deepest fall of ₹1 from a previous high"),
        card("Calmar", r"Calmar = \frac{CAGR}{|MDD|}", ""),
        card("Worst wealth drop (account value)", r"WWD = \min_t \left( \frac{V_t}{\max_{k \leq t} V_k} - 1 \right)",
             "<i>V<sub>t</sub></i> = rupee value of the account (includes new instalments)"),
        card("Wealth multiple", r"\frac{V_{final}}{\sum_t C_t}", ""),
        card("Annual sell turnover", r"\frac{\sum_t sells_t}{\overline{V} \times N/12}",
             "<i>V̄</i> = average account value"),
        card("Annual cost drag", r"\frac{\sum_t Fee_t}{\overline{V} \times N/12}", ""),
    ]
    return page("Scoring", "Scoring every strategy", "sip/metrics.py · applied to each strategy's "
                "119 monthly results", cards)


CSS = """
@page { size: A4; margin: 12mm 12mm 13mm 12mm;
  @bottom-center { content: counter(page) " / 7"; font: 8.5pt 'DejaVu Sans', sans-serif; color: #888; } }
* { box-sizing: border-box; }
body { font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; color: #1d2330; margin: 0; line-height: 1.3; }
section { break-before: page; }
section:first-child { break-before: auto; }
h1 { font-size: 16pt; margin: 0 0 2px; }
.sub { color: #5a6477; margin: 0 0 8px; font-size: 8.5pt; }
.tag { display: inline-block; background: var(--c, #334); color: #fff; border-radius: 4px; font-size: 10pt;
  padding: 1px 8px; margin-right: 9px; vertical-align: middle; }
.grid { display: grid; gap: 6px; }
.g2 { grid-template-columns: 1fr 1fr; }
.g3 { grid-template-columns: 1fr 1fr 1fr; }
.card { border: 1px solid #dde2ea; border-top: 3px solid var(--c, #8793a8); border-radius: 5px;
  padding: 5px 8px 6px; break-inside: avoid; }
.ct { font-weight: 700; font-size: 8.8pt; margin-bottom: 3px; }
.fx { text-align: center; line-height: 1.75; margin: 2px 0; }
.fx img { max-width: 100%; vertical-align: middle; }
.wh { font-size: 7.8pt; color: #4a5468; }
.sblock { margin-bottom: 8px; }
.sname { font-weight: 700; font-size: 10.5pt; margin: 2px 0 5px; color: var(--c, #1d2330); }
.sblock .card { border-top-color: var(--c); }
"""


def main():
    pages = [p_data(), p_engine(), p_fixed(),
             p_opt(4, "Risk-parity SIP", "04_risk_parity_sip", [RP]),
             p_opt(5, "Max-Sharpe SIP", "05_max_sharpe_sip", [MS]),
             p_opt(6, "Optimized SIP (½ RP + ½ MS)", "06_optimized_sip", [RP, MS, AVG]),
             p_scoring()]
    html = (f'<!doctype html><html><head><meta charset="utf-8"><title>SIP Formula Sheet</title>'
            f'<style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "sheet.html"
        src.write_text(html, encoding="utf-8")
        if os.environ.get("KEEP_HTML"):
            shutil.copy(src, os.environ["KEEP_HTML"])
        subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                        "--no-pdf-header-footer", f"--print-to-pdf={OUT}", src.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Wrote {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
