from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Union

import pandas as pd
import streamlit as st
import yfinance as yf

TickerValue = Union[str, List[str]]


@dataclass
class PriceFetchResult:
    prices: pd.DataFrame
    failed: List[str]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_prices(
    label_to_tickers: Dict[str, TickerValue],
    start_date: date,
    end_date: date,
    prefer_adj_close: bool = True,
) -> PriceFetchResult:
    if not label_to_tickers:
        return PriceFetchResult(prices=pd.DataFrame(), failed=[])

    series_map: Dict[str, pd.Series] = {}
    failed_labels: List[str] = []

    for label, tickers in label_to_tickers.items():
        candidates = [tickers] if isinstance(tickers, str) else tickers
        candidates = [x for x in candidates if x]

        found_series: pd.Series | None = None
        for ticker in candidates:
            try:
                data = yf.download(
                    tickers=ticker,
                    start=start_date,
                    end=end_date + timedelta(days=1),
                    auto_adjust=False,
                    progress=False,
                    threads=True,
                )
                if data is None or getattr(data, "empty", True):
                    continue

                extracted = _extract_price_series(data, prefer_adj_close=prefer_adj_close)
                if extracted is None or extracted.empty:
                    continue

                found_series = extracted
                break
            except Exception:
                continue

        if found_series is None:
            failed_labels.append(label)
        else:
            series_map[label] = found_series

    if not series_map:
        return PriceFetchResult(prices=pd.DataFrame(), failed=sorted(set(failed_labels)))

    panel = pd.concat(series_map, axis=1).sort_index()
    panel.index = pd.to_datetime(panel.index).tz_localize(None)
    return PriceFetchResult(prices=panel, failed=sorted(set(failed_labels)))


def _extract_price_series(data: pd.DataFrame, prefer_adj_close: bool) -> pd.Series | None:
    col_order = ["Adj Close", "Close"] if prefer_adj_close else ["Close", "Adj Close"]

    chosen_col = next((c for c in col_order if c in data.columns), None)
    if chosen_col is not None:
        s = data[chosen_col]
    else:
        # Fallback for unusual column structures
        if isinstance(data, pd.Series):
            s = data
        elif data.shape[1] == 1:
            s = data.iloc[:, 0]
        else:
            return None

    if not isinstance(s, pd.Series):
        try:
            s = pd.Series(s)
        except Exception:
            return None

    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return None

    # Guard against scalar-like accidental extraction
    if s.index.nlevels == 0 or len(s.index) == 0:
        return None

    return s


def parse_custom_tickers(csv_text: str) -> Dict[str, str]:
    raw = [x.strip() for x in (csv_text or "").split(",") if x.strip()]
    return {f"Custom {tk}": tk for tk in raw}
