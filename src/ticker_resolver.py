from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

import pandas as pd
import yfinance as yf


@dataclass
class ResolvedTicker:
    label: str
    ticker: str | None
    attempted: List[str]


def _probe_ticker(ticker: str, start_date: date, end_date: date, probe_days: int = 45) -> pd.DataFrame:
    probe_start = start_date - timedelta(days=probe_days)
    return yf.download(
        tickers=ticker,
        start=probe_start,
        end=end_date + timedelta(days=1),
        auto_adjust=False,
        progress=False,
        threads=True,
    )


def resolve_tickers(label_to_candidates: Dict[str, List[str]], start_date: date, end_date: date) -> Dict[str, ResolvedTicker]:
    resolved: Dict[str, ResolvedTicker] = {}
    for label, candidates in label_to_candidates.items():
        attempted: List[str] = []
        selected = None
        for ticker in [x for x in candidates if x]:
            attempted.append(ticker)
            try:
                data = _probe_ticker(ticker, start_date, end_date)
            except Exception:
                continue
            if data is None or getattr(data, "empty", True):
                continue
            selected = ticker
            break
        resolved[label] = ResolvedTicker(label=label, ticker=selected, attempted=attempted)
    return resolved
