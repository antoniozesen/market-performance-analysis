from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.transforms import drawdown_from_prices


def performance_summary(prices: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    if prices.empty or returns.empty:
        return pd.DataFrame()

    n_days = max((prices.index.max() - prices.index.min()).days, 1)
    years = n_days / 365.25

    total_return = prices.iloc[-1] / prices.iloc[0] - 1
    annualized = (1 + total_return) ** (1 / years) - 1
    vol = returns.std() * np.sqrt(252)
    dd = drawdown_from_prices(prices)
    max_dd = dd.min()
    best_day = returns.max()
    worst_day = returns.min()

    df = pd.DataFrame(
        {
            "Total Return %": total_return * 100,
            "Annualized Return %": annualized * 100,
            "Volatility %": vol * 100,
            "Max Drawdown %": max_dd * 100,
            "Best Day %": best_day * 100,
            "Worst Day %": worst_day * 100,
        }
    )
    return df.replace([np.inf, -np.inf], np.nan).sort_values("Total Return %", ascending=False)


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    if returns.empty:
        return pd.DataFrame()
    return returns.corr()


def compute_spread_proxies(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    proxies = {}
    if {"US IG Corporate", "US Govt Bonds 7-10Y"}.issubset(summary_df.index):
        proxies["US IG Spread Proxy (ret diff %) "] = (
            summary_df.loc["US IG Corporate", "Total Return %"]
            - summary_df.loc["US Govt Bonds 7-10Y", "Total Return %"]
        )
    if {"US HY Corporate", "US Govt Bonds 7-10Y"}.issubset(summary_df.index):
        proxies["US HY Spread Proxy (ret diff %) "] = (
            summary_df.loc["US HY Corporate", "Total Return %"]
            - summary_df.loc["US Govt Bonds 7-10Y", "Total Return %"]
        )
    if {"EU IG Corporate", "EU Govt Bonds 7-10Y"}.issubset(summary_df.index):
        proxies["EU IG Spread Proxy (ret diff %) "] = (
            summary_df.loc["EU IG Corporate", "Total Return %"]
            - summary_df.loc["EU Govt Bonds 7-10Y", "Total Return %"]
        )
    if {"EU HY Corporate", "EU Govt Bonds 7-10Y"}.issubset(summary_df.index):
        proxies["EU HY Spread Proxy (ret diff %) "] = (
            summary_df.loc["EU HY Corporate", "Total Return %"]
            - summary_df.loc["EU Govt Bonds 7-10Y", "Total Return %"]
        )

    if not proxies:
        return pd.DataFrame()
    return pd.DataFrame.from_dict(proxies, orient="index", columns=["Value"])
