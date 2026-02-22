from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

import pandas as pd


EU_INDEXES = ["EURO STOXX 600", "DAX", "CAC 40", "IBEX", "FTSE 100", "FTSE MIB"]
US_INDEXES = ["S&P 500", "NASDAQ", "Dow Jones", "Russell 2000"]
ASIA_INDEXES = ["Nikkei 225", "Hang Seng"]

SECTOR_PAIRS = [
    ("EU Technology", "US Technology"),
    ("EU Health Care", "US Health Care"),
    ("EU Financials", "US Financials"),
    ("EU Consumer Discretionary", "US Consumer Discretionary"),
    ("EU Energy", "US Energy"),
    ("EU Communication Services", "US Communication Services"),
    ("EU Materials", "US Materials"),
    ("EU Utilities", "US Utilities"),
    ("EU Consumer Staples", "US Consumer Staples"),
    ("EU Industrials", "US Industrials"),
]


def _rank(summary: pd.DataFrame, labels: List[str], top_n: int = 3) -> Tuple[pd.Series, pd.Series]:
    subset = summary.loc[summary.index.intersection(labels)]
    if subset.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    ordered = subset["Total Return %"].sort_values(ascending=False)
    return ordered.head(top_n), ordered.tail(top_n)


def _fmt_rank(series: pd.Series, bold: bool = True) -> str:
    if series.empty:
        return "N/A"
    chunks = []
    for k, v in series.items():
        label = f"**{k}**" if bold else k
        chunks.append(f"{label} ({v:.2f}%)")
    return ", ".join(chunks)


def _single_perf(summary: pd.DataFrame, label: str) -> str:
    if label not in summary.index:
        return "N/A"
    return f"{summary.at[label, 'Total Return %']:.2f}%"


def _pairwise_sector_lines(summary: pd.DataFrame) -> List[str]:
    lines: List[Tuple[float, str]] = []
    for eu, us in SECTOR_PAIRS:
        if eu in summary.index and us in summary.index:
            eu_ret = float(summary.at[eu, "Total Return %"])
            us_ret = float(summary.at[us, "Total Return %"])
            diff = us_ret - eu_ret
            if diff >= 0:
                sentence = (
                    f"- **{us}** outperformed **{eu}** by {abs(diff):.2f}% "
                    f"({us}: {us_ret:.2f}% vs {eu}: {eu_ret:.2f}%)."
                )
            else:
                sentence = (
                    f"- **{eu}** outperformed **{us}** by {abs(diff):.2f}% "
                    f"({eu}: {eu_ret:.2f}% vs {us}: {us_ret:.2f}%)."
                )
            lines.append((abs(diff), sentence))

    lines.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in lines[:5]]


def _slope_text(yields_df: pd.DataFrame, lang: str) -> str:
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        slope = float((yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100)
        return f"US 2s10s closed at {slope:.1f} bps" if lang == "en" else f"la pendiente 2s10s de EE.UU. cerró en {slope:.1f} pb"
    return "US 2s10s slope unavailable" if lang == "en" else "pendiente 2s10s no disponible"


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


def _report_en(start_date: date, end_date: date, summary: pd.DataFrame, yields_df: pd.DataFrame, universe: Dict[str, Dict[str, str]]) -> str:
    eu_top, eu_bottom = _rank(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _rank(summary, list(universe.get("US SECTORS", {}).keys()))
    eu_idx_top, eu_idx_bottom = _rank(summary, EU_INDEXES, top_n=2)
    us_idx_top, us_idx_bottom = _rank(summary, US_INDEXES, top_n=2)
    asia_top, asia_bottom = _rank(summary, ASIA_INDEXES, top_n=2)
    pairwise = _pairwise_sector_lines(summary)

    us_value = _single_perf(summary, "US Value")
    us_growth = _single_perf(summary, "US Growth")
    eu_value = _single_perf(summary, "EU Value")
    eu_growth = _single_perf(summary, "EU Growth")
    slope_text = _slope_text(yields_df, "en")

    return f"""# Global Market Monitor Report
**Period:** {start_date:%d %B %Y} to {end_date:%d %B %Y}

## EUROPEAN MARKETS
European equities showed dispersion across benchmarks. Leaders were {_fmt_rank(eu_idx_top)}; laggards were {_fmt_rank(eu_idx_bottom)}.

EU sector leadership was concentrated in {_fmt_rank(eu_top)}. The weakest pockets were {_fmt_rank(eu_bottom)}.

In style factors, **EU Value** returned {eu_value}, while **EU Growth** returned {eu_growth}.

## US MARKETS
US benchmarks were led by {_fmt_rank(us_idx_top)}, while relative underperformers were {_fmt_rank(us_idx_bottom)}.

Sector breadth favored {_fmt_rank(us_top)}. The weakest US sectors were {_fmt_rank(us_bottom)}.

In style factors, **US Value** returned {us_value}, while **US Growth** returned {us_growth}.

## EUROPE VS US COMPARATIVE SECTOR ANALYSIS
A direct transatlantic sector comparison highlights relative winners and losers:
{chr(10).join(pairwise) if pairwise else '- Pairwise sector comparisons were unavailable due to missing data.'}

## ASIAN MARKETS
Asian benchmarks are included for global context: top prints {_fmt_rank(asia_top)}; weakest prints {_fmt_rank(asia_bottom)}.

## FIXED INCOME MARKETS
Rates and fixed income ETFs reflected duration and credit-beta repricing over the period. {slope_text}.

US and EU corporate-vs-government differentials are presented as **spread-change proxies** based on ETF returns (proxy only, not direct OAS).

## CURRENCY MARKETS
FX performance is tracked across **EUR/USD, EUR/GBP, EUR/JPY, USD/JPY, GBP/USD, USD/CHF** with return-based cross-comparison.

## COMMODITY MARKETS
Commodity performance is detailed for **Gold, Silver, Brent Crude, WTI Crude, Natural Gas, Copper**, with return ranking in the summary table.

## PERFORMANCE SUMMARY
The performance table reports total return, annualized return, volatility, max drawdown, and best/worst day for all selected assets.
"""


def _report_es(start_date: date, end_date: date, summary: pd.DataFrame, yields_df: pd.DataFrame, universe: Dict[str, Dict[str, str]]) -> str:
    eu_top, eu_bottom = _rank(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _rank(summary, list(universe.get("US SECTORS", {}).keys()))
    eu_idx_top, eu_idx_bottom = _rank(summary, EU_INDEXES, top_n=2)
    us_idx_top, us_idx_bottom = _rank(summary, US_INDEXES, top_n=2)
    asia_top, asia_bottom = _rank(summary, ASIA_INDEXES, top_n=2)
    pairwise = _pairwise_sector_lines(summary)

    us_value = _single_perf(summary, "US Value")
    us_growth = _single_perf(summary, "US Growth")
    eu_value = _single_perf(summary, "EU Value")
    eu_growth = _single_perf(summary, "EU Growth")
    slope_text = _slope_text(yields_df, "es")

    return f"""# Informe Global Market Monitor
**Periodo:** {start_date:%d %B %Y} a {end_date:%d %B %Y}

## MERCADOS EUROPEOS
La renta variable europea mostró dispersión entre índices. Los líderes fueron {_fmt_rank(eu_idx_top)}; los rezagados {_fmt_rank(eu_idx_bottom)}.

El liderazgo sectorial europeo se concentró en {_fmt_rank(eu_top)}. Los sectores más débiles fueron {_fmt_rank(eu_bottom)}.

En estilos, **EU Value** registró {eu_value} y **EU Growth** {eu_growth}.

## MERCADOS DE EE.UU.
En EE.UU., los índices líderes fueron {_fmt_rank(us_idx_top)}, mientras que los más débiles fueron {_fmt_rank(us_idx_bottom)}.

A nivel sectorial, destacaron {_fmt_rank(us_top)}; los peores sectores fueron {_fmt_rank(us_bottom)}.

En estilos, **US Value** registró {us_value} y **US Growth** {us_growth}.

## ANÁLISIS SECTORIAL COMPARATIVO EUROPA VS EE.UU.
La comparación directa entre sectores muestra los siguientes diferenciales:
{chr(10).join(pairwise) if pairwise else '- Comparativas sectoriales no disponibles por falta de datos.'}

## MERCADOS ASIÁTICOS
Los índices asiáticos aportan contexto global: mejores registros {_fmt_rank(asia_top)}; más débiles {_fmt_rank(asia_bottom)}.

## MERCADOS DE RENTA FIJA
La renta fija reflejó reajuste de duración y crédito en el periodo; {slope_text}.

Los diferenciales corporativo-vs-soberano se muestran como **proxies de spread** basados en retornos ETF (aproximación, no OAS directo).

## MERCADOS DE DIVISAS
Se monitoriza la performance relativa de **EUR/USD, EUR/GBP, EUR/JPY, USD/JPY, GBP/USD, USD/CHF**.

## MERCADOS DE MATERIAS PRIMAS
Se detalla la evolución de **Gold, Silver, Brent Crude, WTI Crude, Natural Gas, Copper** con ranking de rendimiento en la tabla.

## RESUMEN DE DESEMPEÑO
La tabla de performance incluye retorno total, retorno anualizado, volatilidad, drawdown máximo y mejor/peor sesión para cada activo seleccionado.
"""
