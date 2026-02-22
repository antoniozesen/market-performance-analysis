from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import streamlit as st
import yfinance as yf


@dataclass
class PriceFetchResult:
    prices: pd.DataFrame
    failed: List[str]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_prices(
    label_to_ticker: Dict[str, str],
    start_date: date,
    end_date: date,
    prefer_adj_close: bool = True,
) -> PriceFetchResult:
    if not label_to_ticker:
        return PriceFetchResult(prices=pd.DataFrame(), failed=[])

    tickers = list(label_to_ticker.values())
    ticker_to_labels = _reverse_mapping(label_to_ticker)

    data = yf.download(
        tickers=tickers,
        start=start_date,
        end=end_date + timedelta(days=1),
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    if data.empty:
        return PriceFetchResult(prices=pd.DataFrame(), failed=list(label_to_ticker.keys()))

    series = {}
    failed_labels: List[str] = []
    for ticker, labels in ticker_to_labels.items():
        try:
            ticker_df = data[ticker] if len(tickers) > 1 else data
            col_order = ["Adj Close", "Close"] if prefer_adj_close else ["Close", "Adj Close"]
            chosen = next((c for c in col_order if c in ticker_df.columns), None)
            if chosen is None:
                raise KeyError("No Close/Adj Close")
            s = ticker_df[chosen].dropna().copy()
            if s.empty:
                raise ValueError("Series empty")
            for label in labels:
                series[label] = s
        except Exception:
            failed_labels.extend(labels)

    panel = pd.DataFrame(series).sort_index()
    panel.index = pd.to_datetime(panel.index).tz_localize(None)
    return PriceFetchResult(prices=panel, failed=sorted(set(failed_labels)))


def _reverse_mapping(label_to_ticker: Dict[str, str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for label, ticker in label_to_ticker.items():
        out.setdefault(ticker, []).append(label)
    return out


def parse_custom_tickers(csv_text: str) -> Dict[str, str]:
    raw = [x.strip() for x in (csv_text or "").split(",") if x.strip()]
    return {f"Custom {tk}": tk for tk in raw}
