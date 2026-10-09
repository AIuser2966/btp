"""Step 8a: build the Jan 2020 – Dec 2025 returns and join them to the 2000–2019 table.

    python 08_forward_test/build_data.py

Writes forward_returns_2020_2025.csv (72 months x Nifty, Gold, Liquid) and
monthly_returns_2000_2025.csv (311 months: the original 239 + the 72 new ones).
Sources and formulas: sip/forward_data.py and this folder's README.md.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sip.forward_data import COMBINED_FILE, FORWARD_FILE, combined_returns, forward_returns  # noqa: E402

fwd = forward_returns()
assert len(fwd) == 72 and fwd.notna().all().all(), "every month 2020-01..2025-12 must have data"
fwd.to_csv(FORWARD_FILE, float_format="%.8f")

comb = combined_returns()
assert comb.index.is_monotonic_increasing and comb.index.is_unique
comb.to_csv(COMBINED_FILE, float_format="%.8f")

ann = (1 + fwd).prod() ** (12 / len(fwd)) - 1
print(f"{len(fwd)} forward months ({fwd.index[0]} to {fwd.index[-1]}) -> {FORWARD_FILE.name}")
print(f"{len(comb)} months in total ({comb.index[0]} to {comb.index[-1]}) -> {COMBINED_FILE.name}")
print("2020-2025 return per year:", ann.round(4).to_dict())
print("2020-2025 volatility per year:", (fwd.std() * 12 ** 0.5).round(4).to_dict())
