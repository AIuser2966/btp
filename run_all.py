"""Rebuild everything in order: data -> six strategies -> comparison -> explainer READMEs.

    python run_all.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    ["00_raw_data/build_returns.py"],
    ["01_equity_sip/strategy.py"],
    ["02_equal_weight_sip/strategy.py"],
    ["03_fixed_60_20_20_sip/strategy.py"],
    ["04_risk_parity_sip/strategy.py"],
    ["05_max_sharpe_sip/strategy.py"],
    ["06_optimized_sip/strategy.py"],
    ["07_comparison/run.py"],
    ["docs/make_readmes.py"],
]

for step in STEPS:
    print(f"\n=== {' '.join(step)}")
    subprocess.run([sys.executable, str(ROOT / step[0]), *step[1:]], check=True,
                   stdout=subprocess.DEVNULL if step[0].startswith("07") else None)
print("\nDone. Results are in each folder's results/ directory.")
