"""Registry of the six strategies. Each one is defined in its own folder's strategy.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from .engine import Strategy

ROOT = Path(__file__).resolve().parent.parent
STRATEGY_FOLDERS = ["01_equity_sip", "02_equal_weight_sip", "03_fixed_60_20_20_sip",
                    "04_risk_parity_sip", "05_max_sharpe_sip", "06_optimized_sip"]


def load_strategy_module(folder: str):
    path = ROOT / folder / "strategy.py"
    spec = importlib.util.spec_from_file_location(f"strategy_{folder}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_strategies(returns: pd.DataFrame, lookback: int = 120) -> list[Strategy]:
    """All six strategies, in folder order, built from their own strategy.py files."""
    return [load_strategy_module(f).build(returns, lookback=lookback) for f in STRATEGY_FOLDERS]
