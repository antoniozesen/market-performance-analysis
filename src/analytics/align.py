from __future__ import annotations

from datetime import date

import pandas as pd


def align_panel(
    panel: pd.DataFrame,
    start_date: date,
    end_date: date,
    forward_fill: bool = True,
    business_days: bool = True,
) -> pd.DataFrame:
    if panel.empty:
        return panel

    freq = "B" if business_days else "D"
    idx = pd.date_range(start=start_date, end=end_date, freq=freq)
    aligned = panel.reindex(idx)
    if forward_fill:
        aligned = aligned.ffill()
    return aligned


def compute_returns(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel
    return panel.pct_change().replace([float("inf"), float("-inf")], pd.NA).dropna(how="all")
