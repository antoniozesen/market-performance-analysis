from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


def load_universe(config_path: str | Path = "src/data/universe.yaml") -> Dict[str, Dict[str, str]]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Universe config not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("Universe configuration must be a dictionary of categories.")

    cleaned: Dict[str, Dict[str, str]] = {}
    for category, assets in data.items():
        if isinstance(assets, dict):
            cleaned[str(category)] = {str(label): str(ticker) for label, ticker in assets.items()}

    return cleaned


def flatten_universe(universe: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for category_assets in universe.values():
        flat.update(category_assets)
    return flat
