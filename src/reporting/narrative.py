from __future__ import annotations

from datetime import date
from typing import Dict

import pandas as pd


def _top_bottom(summary: pd.DataFrame, labels: list[str]) -> tuple[str, str]:
    subset = summary.loc[summary.index.intersection(labels)]
    if subset.empty:
        return "N/A", "N/A"
    top = subset["Total Return %"].idxmax()
    bottom = subset["Total Return %"].idxmin()
    return top, bottom


def generate_report_markdown(
    start_date: date,
    end_date: date,
    summary: pd.DataFrame,
    yields_df: pd.DataFrame,
    universe: Dict[str, Dict[str, str]],
    style: str = "English",
) -> str:
    if style == "Spanish":
        return _report_es(start_date, end_date, summary, yields_df, universe)
    return _report_en(start_date, end_date, summary, yields_df, universe)


def _report_en(start_date, end_date, summary, yields_df, universe) -> str:
    eu_top, eu_bottom = _top_bottom(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _top_bottom(summary, list(universe.get("US SECTORS", {}).keys()))
    eu_idx_top, eu_idx_bottom = _top_bottom(summary, ["EURO STOXX 600", "DAX", "CAC 40", "IBEX", "FTSE 100", "FTSE MIB"])
    us_idx_top, us_idx_bottom = _top_bottom(summary, ["S&P 500", "NASDAQ", "Dow Jones", "Russell 2000"])

    slope_text = "2s10s slope unavailable"
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        slope = (yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100
        slope_text = f"US 2s10s closed at {slope:.1f} bps"

    return f"""# Global Market Monitor Report
**Period:** {start_date:%d %B %Y} to {end_date:%d %B %Y}

## EUROPEAN MARKETS
European indices showed mixed performance, led by **{eu_idx_top}**, while **{eu_idx_bottom}** lagged in the period. In EU sectors, leadership came from **{eu_top}** and the weakest pocket was **{eu_bottom}**. EU value vs growth dynamics are captured via CV9.PA and CG9.PA in the summary table.

## US MARKETS
US indices were headed by **{us_idx_top}**, whereas **{us_idx_bottom}** underperformed. Sector breadth favored **{us_top}** while **{us_bottom}** remained the main drag. US value/growth relative performance is proxied by IVE vs IVW.

## EUROPE VS US COMPARATIVE SECTOR ANALYSIS
Cross-region comparison indicates rotating leadership by sector. Focus on relative winners in technology, financials, and defensives across both geographies to identify convergence/divergence trends.

## ASIAN MARKETS
Asian benchmarks (Nikkei 225 and Hang Seng) contributed to global risk sentiment with divergent trajectories over the selected window.

## FIXED INCOME MARKETS
Rates and bond ETF performance indicate duration sensitivity and credit beta behavior. {slope_text}. Corporate-vs-government return differentials are shown as spread-change proxies and should be interpreted as indicative, not direct OAS measures.

## CURRENCY MARKETS
Major FX pairs reflected policy divergence and risk appetite shifts, especially across EUR/USD, USD/JPY, and GBP/USD.

## COMMODITY MARKETS
Commodities displayed heterogeneous moves across precious metals, energy, and industrial metals, with implications for inflation narratives and cyclicality.

## PERFORMANCE SUMMARY
Refer to the table for total return, annualized return, volatility, max drawdown, and tail daily moves for each selected asset.
"""


def _report_es(start_date, end_date, summary, yields_df, universe) -> str:
    eu_top, eu_bottom = _top_bottom(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _top_bottom(summary, list(universe.get("US SECTORS", {}).keys()))
    slope_text = "pendiente 2s10s no disponible"
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        slope = (yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100
        slope_text = f"la pendiente 2s10s de EE.UU. cerró en {slope:.1f} pb"

    return f"""# Informe Global Market Monitor
**Periodo:** {start_date:%d %B %Y} a {end_date:%d %B %Y}

## MERCADOS EUROPEOS
En Europa, los sectores mostraron dispersión: **{eu_top}** lideró y **{eu_bottom}** quedó rezagado. La comparación value vs growth se resume en el cuadro de resultados.

## MERCADOS DE EE.UU.
En EE.UU., la amplitud sectorial favoreció **{us_top}**, mientras **{us_bottom}** fue el principal lastre. La dinámica value/growth se aproxima con IVE frente a IVW.

## ANÁLISIS SECTORIAL COMPARATIVO EUROPA VS EE.UU.
La comparación relativa entre regiones muestra rotación sectorial. Conviene monitorizar tecnología, financieras y sectores defensivos para detectar convergencias y divergencias.

## MERCADOS ASIÁTICOS
Nikkei 225 y Hang Seng aportaron señales mixtas de apetito por riesgo durante la ventana analizada.

## MERCADOS DE RENTA FIJA
El comportamiento de ETFs de bonos y curvas soberanas refleja sensibilidad a duración y crédito; {slope_text}. Los proxies de spread corporativo vs soberano son aproximaciones y no sustituyen medidas directas de spread.

## MERCADOS DE DIVISAS
Las principales divisas recogieron divergencias de política monetaria y cambios en el sentimiento de riesgo.

## MERCADOS DE MATERIAS PRIMAS
Metales preciosos, energía y metales industriales mostraron trayectorias distintas con impacto sobre inflación esperada y ciclo económico.

## RESUMEN DE DESEMPEÑO
Consulte la tabla para retorno total, retorno anualizado, volatilidad, drawdown máximo y extremos diarios.
"""
