"""Step 10: which approach maximises the investor's utility U?

    python 10_max_utility/run.py        -> results/

U = (yearly return above Liquid) - (lam / 2) * (yearly volatility)^2

Rules fixed BEFORE running:
* three investor profiles: lam = 2 (aggressive), 4 (moderate), 8 (conservative);
* candidates: the seven strategies of 01-06 and 08, plus Strategy 7 (Max-Utility SIP) for that lam;
* in-sample period Feb 2010 - Dec 2019 (only data to 2019 is loaded), out-of-sample Jan 2020 - Dec 2025;
* the tool uses, for each profile, the strategy with the highest U OUT OF SAMPLE.
Cross-check: the 2020-2025 ranking is rebuilt from the funds not used for the main data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "08_forward_test"))

import strategy as s7  # noqa: E402
from run_forward import all_strategies  # noqa: E402
from sip.engine import contribution_schedule, run_sip  # noqa: E402
from sip.forward_data import CHECKS, combined_returns, read_combined  # noqa: E402
from sip.metrics import sip_xirr, utility_score  # noqa: E402
from sip.report import AMOUNT, COST_BPS, LOOKBACK  # noqa: E402

OUT = HERE / "results"
PERIODS = {"2010-2019 (in-sample)": ("2010-02", "2019-12"),
           "2020-2025 (out-of-sample)": ("2020-01", "2025-12")}


def candidates(data: pd.DataFrame, lam: float):
    return all_strategies(data) + [s7.build(data, lam, LOOKBACK)]


def score(data: pd.DataFrame, start: str, end: str, lam: float) -> pd.DataFrame:
    idx = data.loc[start:end].index
    contrib = contribution_schedule(idx, AMOUNT)
    rows = []
    for st in candidates(data, lam):
        res = run_sip(data, st, contrib, COST_BPS)
        tw = res.twr
        excess = float((tw - data["Liquid"].reindex(tw.index)).mean() * 12)
        vol = float(tw.std() * np.sqrt(12))
        rows.append({"Strategy": st.name, "Return above Liquid": excess, "Volatility": vol,
                     "U": utility_score(res, data["Liquid"], lam), "XIRR": sip_xirr(res),
                     "Final value": float(res.total.iloc[-1])})
    return pd.DataFrame(rows).set_index("Strategy").sort_values("U", ascending=False)


def fmt(df: pd.DataFrame) -> str:
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map((lambda v: f"₹{v:,.0f}") if c == "Final value" else (lambda v: f"{v:.2%}"))
    return out.to_markdown()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(exist_ok=True)
    R = read_combined()
    R_old = R.loc[:"2019-12"]
    alt = combined_returns({"Nifty": CHECKS["Nifty"], "Gold": CHECKS["Gold"] + ["HDFC_GoldETF"],
                            "Liquid": CHECKS["Liquid"]})

    L = ["# Which approach maximises the investor's utility?\n",
         "U = (yearly return above Liquid) − (λ/2) × (yearly volatility)². "
         "Higher U = better balance of profit and risk for that investor.\n"]
    winners = []
    for profile, lam in s7.PROFILES.items():
        L.append(f"## {profile.capitalize()} investor (λ = {lam:g})\n")
        picks = {}
        for label, (a, b) in PERIODS.items():
            data = R_old if b <= "2019-12" else R
            t = score(data, a, b, lam)
            t.to_csv(OUT / f"utility_lam{lam:g}_{a[:4]}_{b[:4]}.csv")
            picks[label] = t.index[0]
            L += [f"### {label}\n", fmt(t), f"\nHighest U: **{t.index[0]}**.\n"]
        t_alt = score(alt, "2020-01", "2025-12", lam)
        L.append(f"Cross-check (2020-2025 rebuilt from other funds): highest U = **{t_alt.index[0]}**.\n")
        winners.append({"Profile": profile, "λ": lam,
                        "Best 2010-2019 (in-sample)": picks["2010-2019 (in-sample)"],
                        "Best 2020-2025 (out-of-sample)": picks["2020-2025 (out-of-sample)"],
                        "Best 2020-2025 (other funds)": t_alt.index[0]})

    # Strategy 7's own weights each February, so the λ effect is visible
    feb = [m for m in R.index if m.month == 2 and m >= pd.Period("2010-02", "M")]
    w = pd.DataFrame({f"λ={lam:g}": s7.target(R, lam).loc[feb].apply(
        lambda row: " / ".join(f"{v:.0%}" for v in row), axis=1) for lam in s7.PROFILES.values()})

    W = pd.DataFrame(winners).set_index("Profile")
    W.to_csv(OUT / "winners.csv")
    L = L[:2] + ["## Summary: the winner for each investor\n", W.to_markdown(), ""] + L[2:]
    L += ["## Strategy 7's targets each February (Nifty / Gold / Liquid)\n", w.to_markdown(), ""]
    (OUT / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
