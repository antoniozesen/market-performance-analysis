from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

import pandas as pd
import streamlit as st
import yfinance as yf

from src.ticker_resolver import resolve_tickers


@dataclass
class PriceFetchResult:
    prices: pd.DataFrame
    failed: List[str]
    resolved: Dict[str, str]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_prices(
    label_to_tickers: Dict[str, List[str]],
    start_date: date,
    end_date: date,
    prefer_adj_close: bool = True,
) -> PriceFetchResult:
    if not label_to_tickers:
        return PriceFetchResult(prices=pd.DataFrame(), failed=[], resolved={})

    resolutions = resolve_tickers(label_to_tickers, start_date, end_date)
    series_map: Dict[str, pd.Series] = {}
    failed_labels: List[str] = []
    resolved_map: Dict[str, str] = {}

    for label, info in resolutions.items():
        if not info.ticker:
            failed_labels.append(label)
            continue
        try:
            data = yf.download(
                tickers=info.ticker,
                start=start_date,
                end=end_date + timedelta(days=1),
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            extracted = _extract_price_series(data, prefer_adj_close=prefer_adj_close)
            if extracted is None or extracted.empty:
                failed_labels.append(label)
                continue
            series_map[label] = extracted
            resolved_map[label] = info.ticker
        except Exception:
            failed_labels.append(label)

    if not series_map:
        return PriceFetchResult(prices=pd.DataFrame(), failed=sorted(set(failed_labels)), resolved=resolved_map)

    panel = pd.concat(series_map, axis=1).sort_index()
    panel.index = pd.to_datetime(panel.index).tz_localize(None)
    return PriceFetchResult(prices=panel, failed=sorted(set(failed_labels)), resolved=resolved_map)


def _extract_price_series(data: pd.DataFrame, prefer_adj_close: bool) -> pd.Series | None:
    if data is None or getattr(data, "empty", True):
        return None

    if isinstance(data.columns, pd.MultiIndex):
        field_pref = ["Adj Close", "Close"] if prefer_adj_close else ["Close", "Adj Close"]
        for field in field_pref:
            if field in data.columns.get_level_values(0):
                s = data[field]
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                s = pd.to_numeric(s, errors="coerce").dropna()
                return s if not s.empty else None

    col_order = ["Adj Close", "Close"] if prefer_adj_close else ["Close", "Adj Close"]
    chosen_col = next((c for c in col_order if c in data.columns), None)
    if chosen_col is not None:
        s = data[chosen_col]
    elif data.shape[1] == 1:
        s = data.iloc[:, 0]
    else:
        return None

    s = pd.to_numeric(s, errors="coerce").dropna()
    return s if not s.empty else None


def parse_custom_tickers(csv_text: str) -> Dict[str, List[str]]:
    raw = [x.strip().upper() for x in (csv_text or "").split(",") if x.strip()]
    return {f"Custom {tk}": [tk] for tk in raw}
