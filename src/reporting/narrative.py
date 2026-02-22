from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

import pandas as pd


def _subset_rank(summary: pd.DataFrame, labels: List[str], n: int = 3) -> Tuple[pd.Series, pd.Series]:
    subset = summary.loc[summary.index.intersection(labels)]
    if subset.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    ranked = subset["Total Return %"].sort_values(ascending=False)
    return ranked.head(n), ranked.tail(n)


def _pairwise_sector_diffs(summary: pd.DataFrame) -> List[str]:
    pairs = [
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
    rows = []
    for eu, us in pairs:
        if eu in summary.index and us in summary.index:
            eu_ret = summary.at[eu, "Total Return %"]
            us_ret = summary.at[us, "Total Return %"]
            diff = us_ret - eu_ret
            leader = us if diff >= 0 else eu
            rows.append((abs(diff), f"- **{leader}** led {eu.replace('EU ', '')}/{us.replace('US ', '')} by {abs(diff):.2f}% ({eu}: {eu_ret:.2f}%, {us}: {us_ret:.2f}%)."))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in rows[:5]]


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
    eu_top, eu_bottom = _subset_rank(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _subset_rank(summary, list(universe.get("US SECTORS", {}).keys()))
    eu_idx, _ = _subset_rank(summary, ["EURO STOXX 600", "DAX", "CAC 40", "IBEX", "FTSE 100", "FTSE MIB"], n=2)
    us_idx, _ = _subset_rank(summary, ["S&P 500", "NASDAQ", "Dow Jones", "Russell 2000"], n=2)
    pairwise = _pairwise_sector_diffs(summary)

    slope_text = "2s10s slope unavailable"
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        slope = (yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100
        slope_text = f"US 2s10s closed at {slope:.1f} bps"

    eu_top_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in eu_top.items()]) if not eu_top.empty else "N/A"
    eu_bottom_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in eu_bottom.items()]) if not eu_bottom.empty else "N/A"
    us_top_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in us_top.items()]) if not us_top.empty else "N/A"
    us_bottom_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in us_bottom.items()]) if not us_bottom.empty else "N/A"

    return f"""# Global Market Monitor Report
**Period:** {start_date:%d %B %Y} to {end_date:%d %B %Y}

## EUROPEAN MARKETS
European benchmark leadership was concentrated in {', '.join([f'**{x}** ({eu_idx[x]:.2f}%)' for x in eu_idx.index]) if not eu_idx.empty else 'N/A'}. EU sector winners were {eu_top_txt}. Laggards were {eu_bottom_txt}. EU style performance (Value vs Growth) is detailed in the summary table.

## US MARKETS
US index leadership came from {', '.join([f'**{x}** ({us_idx[x]:.2f}%)' for x in us_idx.index]) if not us_idx.empty else 'N/A'}. Sector strength was concentrated in {us_top_txt}, while the weakest prints were {us_bottom_txt}. US value/growth dispersion is included in the summary table.

## EUROPE VS US COMPARATIVE SECTOR ANALYSIS
""" + ("\n".join(pairwise) if pairwise else "Pairwise comparisons were unavailable due to missing sector data.") + """

## ASIAN MARKETS
Asian benchmarks (Nikkei 225 and Hang Seng) are tracked in the dashboard and included in the performance table for direct cross-region comparison.

## FIXED INCOME MARKETS
Rates and bond ETF performance indicate duration and credit beta behavior. """ + slope_text + """. Corporate-vs-government return differentials are shown as spread-change proxies (ETF-based proxy, not direct OAS).

## CURRENCY MARKETS
Major FX pairs (EUR/USD, EUR/JPY, USD/JPY, GBP/USD) captured policy divergence and risk-appetite shifts during the selected period.

## COMMODITY MARKETS
Gold, Brent, WTI, natural gas, silver and copper displayed heterogeneous momentum, with implications for inflation and growth signals.

## PERFORMANCE SUMMARY
See the email table and on-screen summary for all tracked assets, total returns, annualized returns, volatility, max drawdown, and tail daily moves.
"""


def _report_es(start_date, end_date, summary, yields_df, universe) -> str:
    eu_top, eu_bottom = _subset_rank(summary, list(universe.get("EU SECTORS", {}).keys()))
    us_top, us_bottom = _subset_rank(summary, list(universe.get("US SECTORS", {}).keys()))
    pairwise = _pairwise_sector_diffs(summary)

    slope_text = "pendiente 2s10s no disponible"
    if {"US 2Y Yield", "US 10Y Yield"}.issubset(yields_df.columns):
        slope = (yields_df["US 10Y Yield"].iloc[-1] - yields_df["US 2Y Yield"].iloc[-1]) * 100
        slope_text = f"la pendiente 2s10s de EE.UU. cerró en {slope:.1f} pb"

    eu_top_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in eu_top.items()]) if not eu_top.empty else "N/D"
    eu_bottom_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in eu_bottom.items()]) if not eu_bottom.empty else "N/D"
    us_top_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in us_top.items()]) if not us_top.empty else "N/D"
    us_bottom_txt = ", ".join([f"**{k}** ({v:.2f}%)" for k, v in us_bottom.items()]) if not us_bottom.empty else "N/D"

    return f"""# Informe Global Market Monitor
**Periodo:** {start_date:%d %B %Y} a {end_date:%d %B %Y}

## MERCADOS EUROPEOS
En Europa, los líderes sectoriales fueron {eu_top_txt}. Los rezagados fueron {eu_bottom_txt}. La comparación value vs growth se incluye en la tabla de resumen.

## MERCADOS DE EE.UU.
En EE.UU., el liderazgo sectorial se concentró en {us_top_txt}, mientras que los más débiles fueron {us_bottom_txt}.

## ANÁLISIS SECTORIAL COMPARATIVO EUROPA VS EE.UU.
""" + ("\n".join(pairwise) if pairwise else "Comparativas no disponibles por falta de datos en algunos pares.") + """

## MERCADOS ASIÁTICOS
Nikkei 225 y Hang Seng se monitorizan en paralelo para comparar el pulso de riesgo global frente a Europa y EE.UU.

## MERCADOS DE RENTA FIJA
Los ETFs de bonos y la curva soberana reflejan sensibilidad a duración y crédito; """ + slope_text + """. Los cambios de spread corporativo frente a gobierno se muestran como proxy basado en retornos ETF.

## MERCADOS DE DIVISAS
Las principales divisas reflejaron divergencias de política monetaria y cambios en el sentimiento de riesgo.

## MERCADOS DE MATERIAS PRIMAS
Oro, crudo Brent/WTI, gas natural, plata y cobre mostraron trayectorias heterogéneas con señal macro relevante.

## RESUMEN DE DESEMPEÑO
Consulte la tabla de resumen para retornos, volatilidad, drawdown y extremos diarios de todos los activos seleccionados.
"""
