from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_base_100(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel
    first = panel.ffill().bfill().iloc[0]
    return panel.divide(first).multiply(100)


def drawdown_from_prices(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel
    rolling_max = panel.cummax()
    return panel.divide(rolling_max).subtract(1.0)


def rolling_volatility(returns: pd.DataFrame, window: int = 20, annualization: int = 252) -> pd.DataFrame:
    if returns.empty:
        return returns
    return returns.rolling(window=window).std() * np.sqrt(annualization)
