from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

import yaml

TickerValue = Union[str, List[str]]
UniverseType = Dict[str, Dict[str, TickerValue]]


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
                cleaned[str(category)][str(label)] = [str(x) for x in ticker_or_list if str(x).strip()]
            else:
                cleaned[str(category)][str(label)] = str(ticker_or_list)

    return cleaned


def flatten_universe(universe: UniverseType) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for category_assets in universe.values():
        for label, ticker_or_list in category_assets.items():
            if isinstance(ticker_or_list, list) and ticker_or_list:
                flat[label] = ticker_or_list[0]
            elif isinstance(ticker_or_list, str):
                flat[label] = ticker_or_list
    return flat
