from __future__ import annotations

from datetime import date
from typing import Dict, Optional

import pandas as pd
import streamlit as st

try:
    from fredapi import Fred
except Exception:  # pragma: no cover
    Fred = None


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_fred_series(
    fred_mapping: Dict[str, str], start_date: date, end_date: date, api_key: Optional[str]
) -> pd.DataFrame:
    if not api_key or Fred is None or not fred_mapping:
        return pd.DataFrame()

    client = Fred(api_key=api_key)
    out = {}
    for label, series_id in fred_mapping.items():
        try:
            s = client.get_series(series_id, observation_start=start_date, observation_end=end_date)
            s = pd.Series(s, name=label).dropna()
            if not s.empty:
                out[label] = s
        except Exception:
            continue

    if not out:
        return pd.DataFrame()

    df = pd.DataFrame(out).sort_index()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df
