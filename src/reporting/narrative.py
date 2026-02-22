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


def _fmt(series: pd.Series) -> str:
    if series.empty:
        return "N/A"
    return ", ".join([f"**{k}** ({v:.2f}%)" for k, v in series.items()])


def _perf(summary: pd.DataFrame, name: str) -> str:
    if name not in summary.index:
        return "N/A"
    return f"{summary.at[name, 'Total Return %']:.2f}%"


def _pair_lines(summary: pd.DataFrame) -> List[str]:
    lines: List[Tuple[float, str]] = []
    for eu, us in SECTOR_PAIRS:
        if eu in summary.index and us in summary.index:
            eu_ret = float(summary.at[eu, "Total Return %"])
            us_ret = float(summary.at[us, "Total Return %"])
            diff = us_ret - eu_ret
            if diff >= 0:
                txt = f"- **{us}** outperformed **{eu}** by {abs(diff):.2f}% ({us}: {us_ret:.2f}% vs {eu}: {eu_ret:.2f}%)."
            else:
                txt = f"- **{eu}** outperformed **{us}** by {abs(diff):.2f}% ({eu}: {eu_ret:.2f}% vs {us}: {us_ret:.2f}%)."
            lines.append((abs(diff), txt))
    lines.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in lines[:5]]


def _slope(yields_df: pd.DataFrame, lang: str) -> str:
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        v = float((yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100)
        return f"US 2s10s closed at {v:.1f} bps" if lang == "en" else f"la pendiente 2s10s de EE.UU. cerró en {v:.1f} pb"
    return "US 2s10s slope unavailable" if lang == "en" else "pendiente 2s10s no disponible"


def generate_report_markdown(
    start_date: date,
    end_date: date,
    summary: pd.DataFrame,
    yields_df: pd.DataFrame,
    universe: Dict[str, Dict[str, str]],
    style: str = "English",
) -> str:
    return _report_es(start_date, end_date, summary, yields_df, universe) if style == "Spanish" else _report_en(start_date, end_date, summary, yields_df, universe)


def _report_en(start_date: date, end_date: date, summary: pd.DataFrame, yields_df: pd.DataFrame, universe: Dict[str, Dict[str, str]]) -> str:
    eu_idx_top, eu_idx_bottom = _rank(summary, EU_INDEXES, top_n=2)
    us_idx_top, us_idx_bottom = _rank(summary, US_INDEXES, top_n=2)
    asia_top, asia_bottom = _rank(summary, ASIA_INDEXES, top_n=2)
    eu_sec_top, eu_sec_bottom = _rank(summary, list(universe.get("EU SECTORS", {}).keys()), top_n=3)
    us_sec_top, us_sec_bottom = _rank(summary, list(universe.get("US SECTORS", {}).keys()), top_n=3)
    pairs = _pair_lines(summary)

    return f"""# Global Market Monitor Report
**Period:** {start_date:%d %B %Y} to {end_date:%d %B %Y}

## EUROPEAN MARKETS
European markets showed differentiated performance over the selected window. The strongest benchmarks were {_fmt(eu_idx_top)}, while the weakest prints were {_fmt(eu_idx_bottom)}.

At sector level, leadership concentrated in {_fmt(eu_sec_top)}. The weakest sectors were {_fmt(eu_sec_bottom)}.

In style allocation, **EU Value** returned {_perf(summary, 'EU Value')} and **EU Growth** returned {_perf(summary, 'EU Growth')}.

## US MARKETS
US equities also displayed dispersion. The leading US benchmarks were {_fmt(us_idx_top)}, while laggards were {_fmt(us_idx_bottom)}.

Sector leadership was concentrated in {_fmt(us_sec_top)}. The weakest sector performance came from {_fmt(us_sec_bottom)}.

In style allocation, **US Value** returned {_perf(summary, 'US Value')} and **US Growth** returned {_perf(summary, 'US Growth')}.

## EUROPE VS US COMPARATIVE SECTOR ANALYSIS
Direct sector comparison highlights the largest transatlantic relative-value gaps:
{chr(10).join(pairs) if pairs else '- Pairwise sector comparison unavailable due to missing data.'}

## ASIAN MARKETS
Asian benchmarks provided mixed signals during the period. Top prints were {_fmt(asia_top)} while weaker performance came from {_fmt(asia_bottom)}.

## FIXED INCOME MARKETS
Fixed income performance reflected duration and credit repricing. {_slope(yields_df, 'en')}.

Corporate vs government differential metrics shown in the dashboard are ETF-based **spread proxies** and should be interpreted as indicative, not direct OAS measurements.

## CURRENCY MARKETS
Currency performance was tracked across **EUR/USD, EUR/GBP, EUR/JPY, USD/JPY, GBP/USD, USD/CHF**, with percentage returns used for direct cross-pair comparability.

## COMMODITY MARKETS
Commodities were monitored through **Gold, Silver, Brent Crude, WTI Crude, Natural Gas, Copper** with relative ranking based on period return.

## PERFORMANCE SUMMARY
The summary table reports total return, annualized return, volatility, max drawdown, and best/worst daily move for each selected asset.
"""


def _report_es(start_date: date, end_date: date, summary: pd.DataFrame, yields_df: pd.DataFrame, universe: Dict[str, Dict[str, str]]) -> str:
    eu_idx_top, eu_idx_bottom = _rank(summary, EU_INDEXES, top_n=2)
    us_idx_top, us_idx_bottom = _rank(summary, US_INDEXES, top_n=2)
    asia_top, asia_bottom = _rank(summary, ASIA_INDEXES, top_n=2)
    eu_sec_top, eu_sec_bottom = _rank(summary, list(universe.get("EU SECTORS", {}).keys()), top_n=3)
    us_sec_top, us_sec_bottom = _rank(summary, list(universe.get("US SECTORS", {}).keys()), top_n=3)
    pairs = _pair_lines(summary)

    return f"""# Informe Global Market Monitor
**Periodo:** {start_date:%d %B %Y} a {end_date:%d %B %Y}

## MERCADOS EUROPEOS
Los mercados europeos mostraron evolución diferenciada en el periodo. Los índices líderes fueron {_fmt(eu_idx_top)}, mientras que los más débiles fueron {_fmt(eu_idx_bottom)}.

A nivel sectorial, el liderazgo se concentró en {_fmt(eu_sec_top)}. Los sectores más rezagados fueron {_fmt(eu_sec_bottom)}.

En estilos, **EU Value** registró {_perf(summary, 'EU Value')} y **EU Growth** {_perf(summary, 'EU Growth')}.

## MERCADOS DE EE.UU.
La renta variable estadounidense también mostró dispersión. Los índices líderes fueron {_fmt(us_idx_top)}, mientras que los más débiles fueron {_fmt(us_idx_bottom)}.

En sectores, destacaron {_fmt(us_sec_top)} y los peores comportamientos fueron {_fmt(us_sec_bottom)}.

En estilos, **US Value** registró {_perf(summary, 'US Value')} y **US Growth** {_perf(summary, 'US Growth')}.

## ANÁLISIS SECTORIAL COMPARATIVO EUROPA VS EE.UU.
La comparación sectorial directa refleja los mayores diferenciales relativos:
{chr(10).join(pairs) if pairs else '- Comparativa por pares no disponible por datos insuficientes.'}

## MERCADOS ASIÁTICOS
Los índices asiáticos aportaron señales mixtas en el periodo. Los mejores registros fueron {_fmt(asia_top)} y los más débiles {_fmt(asia_bottom)}.

## MERCADOS DE RENTA FIJA
La renta fija reflejó reajuste de duración y crédito. {_slope(yields_df, 'es')}.

Los diferenciales corporativo vs soberano mostrados son **proxies de spread** basados en ETFs; deben interpretarse como aproximaciones y no como OAS directo.

## MERCADOS DE DIVISAS
Se monitorizó la performance de **EUR/USD, EUR/GBP, EUR/JPY, USD/JPY, GBP/USD, USD/CHF** en términos porcentuales para comparación homogénea.

## MERCADOS DE MATERIAS PRIMAS
Se siguió la evolución de **Gold, Silver, Brent Crude, WTI Crude, Natural Gas, Copper** con ranking por retorno acumulado.

## RESUMEN DE DESEMPEÑO
La tabla de resumen incluye retorno total, retorno anualizado, volatilidad, drawdown máximo y mejor/peor sesión diaria por activo.
"""
