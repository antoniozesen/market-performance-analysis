from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

UniverseType = Dict[str, Dict[str, List[str]]]


def load_universe(config_path: str | Path = "src/data/universe.yaml") -> UniverseType:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Universe config not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("Universe configuration must be a dictionary of categories.")

    cleaned: UniverseType = {}
    for category, assets in data.items():
        if not isinstance(assets, dict):
            continue
        cleaned[str(category)] = {}
        for label, ticker_or_list in assets.items():
            if isinstance(ticker_or_list, list):
                tickers = [str(x).strip() for x in ticker_or_list if str(x).strip()]
            else:
                tickers = [str(ticker_or_list).strip()] if str(ticker_or_list).strip() else []
            cleaned[str(category)][str(label)] = tickers
    return cleaned
