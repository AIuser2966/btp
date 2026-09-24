"""Step 0: turn the raw files in ./raw into the monthly returns table every strategy uses.

    python 00_raw_data/build_returns.py

Writes monthly_returns_usd.csv and monthly_returns_inr.csv (642 months x 3 assets).
The formulas are explained in this folder's README.md and implemented in sip/data.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sip.data import load_returns, returns_table_path  # noqa: E402

for currency in ("USD", "INR"):
    rets = load_returns(currency)
    out = returns_table_path(currency)
    rets.rename_axis("Month").to_csv(out, float_format="%.8f")
    print(f"{currency}: {len(rets)} months ({rets.index[0]} to {rets.index[-1]}) -> {out.name}")
