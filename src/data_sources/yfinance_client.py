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

    series: Dict[str, pd.Series] = {}
    failed_labels: List[str] = []

    for label, tickers in label_to_tickers.items():
        candidates = [tickers] if isinstance(tickers, str) else tickers
        candidates = [x for x in candidates if x]
        found = None
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
                if data.empty:
                    continue
                col_order = ["Adj Close", "Close"] if prefer_adj_close else ["Close", "Adj Close"]
                chosen = next((c for c in col_order if c in data.columns), None)
                if not chosen:
                    continue
                s = data[chosen].dropna().copy()
                if s.empty:
                    continue
                found = s
                break
            except Exception:
                continue

        if found is None:
            failed_labels.append(label)
        else:
            series[label] = found

    panel = pd.DataFrame(series).sort_index() if series else pd.DataFrame()
    if not panel.empty:
        panel.index = pd.to_datetime(panel.index).tz_localize(None)
    return PriceFetchResult(prices=panel, failed=sorted(set(failed_labels)))


def parse_custom_tickers(csv_text: str) -> Dict[str, str]:
    raw = [x.strip() for x in (csv_text or "").split(",") if x.strip()]
    return {f"Custom {tk}": tk for tk in raw}
