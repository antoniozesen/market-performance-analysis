from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.align import align_panel, compute_returns
from src.analytics.metrics import compute_spread_proxies, correlation_matrix, performance_summary
from src.analytics.transforms import drawdown_from_prices, normalize_base_100, rolling_volatility
from src.config_loader import load_universe
from src.data_sources.fred_client import fetch_fred_series
from src.data_sources.yfinance_client import fetch_prices, parse_custom_tickers
from src.email.smtp_sender import send_email
from src.reporting.html_builder import markdown_to_basic_html
from src.reporting.narrative import generate_report_markdown

st.set_page_config(page_title="Global Market Monitor", layout="wide")
st.title("🌍 Global Market Monitor")
st.caption("Cross-asset comparison + narrative report + email.")

CATS = ["INDICES", "STYLE ETFs", "EU SECTORS", "US SECTORS", "CURRENCIES", "COMMODITIES", "BOND ETFs", "YIELDS"]


def secret_get(key: str, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def cumulative_return_pct(prices_df: pd.DataFrame) -> pd.DataFrame:
    if prices_df.empty:
        return prices_df
    base = prices_df.ffill().bfill().iloc[0]
    return prices_df.divide(base).subtract(1.0).multiply(100)


def preset_dates(preset: str) -> tuple[date, date]:
    today = date.today()
    return {
        "MTD": (today.replace(day=1), today),
        "1M": (today - timedelta(days=30), today),
        "3M": (today - timedelta(days=90), today),
        "YTD": (today.replace(month=1, day=1), today),
        "1Y": (today - timedelta(days=365), today),
    }.get(preset, (today - timedelta(days=90), today))


def autoscale_groups(ret_pct: pd.DataFrame, threshold: float = 120.0) -> tuple[list[str], list[str]]:
    if ret_pct.empty:
        return [], []
    last_abs = ret_pct.ffill().iloc[-1].abs().sort_values(ascending=False)
    if len(last_abs) < 2 or (last_abs.iloc[0] - last_abs.iloc[1]) <= threshold:
        return list(ret_pct.columns), []
    split_count = max(1, len(last_abs) // 4)
    outliers = list(last_abs.head(split_count).index)
    main = [c for c in ret_pct.columns if c not in outliers]
    return main, outliers


universe = load_universe()
with st.sidebar:
    st.header("Controls")
    preset = st.selectbox("Quick preset", ["MTD", "1M", "3M", "YTD", "1Y", "Custom"], index=2)
    ps, pe = preset_dates(preset)
    start_date = st.date_input("Start date", value=ps)
    end_date = st.date_input("End date", value=pe)
    if start_date >= end_date:
        st.error("Start date must be before end date")
        st.stop()

    selected_categories = st.multiselect("Categories", options=CATS, default=["INDICES", "EU SECTORS", "US SECTORS"])
    selection: Dict[str, List[str]] = {}
    for cat in selected_categories:
        labels = list(universe.get(cat, {}).keys())
        selection[cat] = st.multiselect(f"Assets in {cat}", labels, default=labels[: min(8, len(labels))])

    custom_csv = st.text_input("Custom yfinance tickers (CSV)", placeholder="AAPL,MSFT")
    chart_mode = st.radio("Chart mode", ["Cumulative return %", "Normalized price index (start=100)", "Absolute prices"], index=0)
    prefer_adj = st.toggle("Use Adj Close (fallback Close)", value=True)
    forward_fill = st.toggle("Forward-fill missing data", value=True)
    auto_scale = st.toggle("Auto-scale handling", value=True)
    log_scale = st.toggle("Log scale (normalized/absolute only)", value=False)

label_to_tickers: Dict[str, List[str]] = {}
fred_map: Dict[str, List[str]] = {}
for cat, labels in selection.items():
    for label in labels:
        tickers = universe.get(cat, {}).get(label, [])
        if cat == "YIELDS":
            fred_map[label] = tickers
        else:
            label_to_tickers[label] = tickers
label_to_tickers.update(parse_custom_tickers(custom_csv))

price_res = fetch_prices(label_to_tickers, start_date, end_date, prefer_adj_close=prefer_adj)
prices = align_panel(price_res.prices, start_date, end_date, forward_fill=forward_fill)
returns = compute_returns(prices)
summary = performance_summary(prices, returns)
corr = correlation_matrix(returns)
drawdowns = drawdown_from_prices(prices)
normalized = normalize_base_100(prices)
roll_vol = rolling_volatility(returns, window=20)
ret_pct = cumulative_return_pct(prices)

fred_key = secret_get("FRED_API_KEY", None)
yields = fetch_fred_series(fred_map, start_date, end_date, fred_key)
if not yields.empty and {"US 2Y Yield", "US 10Y Yield"}.issubset(yields.columns):
    yields["US 2s10s slope (bps)"] = (yields["US 10Y Yield"] - yields["US 2Y Yield"]) * 100

if price_res.failed:
    st.warning(f"Skipped assets with no usable data: {', '.join(price_res.failed)}")
if price_res.resolved:
    with st.expander("Resolved tickers"):
        st.json(price_res.resolved)

spread_proxy = compute_spread_proxies(summary)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Charts", "Report Builder", "Email", "Settings / About"])

with tab1:
    if not summary.empty:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Best performer", summary.index[0], f"{summary.iloc[0]['Total Return %']:.2f}%")
        c2.metric("Worst performer", summary.index[-1], f"{summary.iloc[-1]['Total Return %']:.2f}%")
        c3.metric("Average return", f"{summary['Total Return %'].mean():.2f}%")
        c4.metric("Median vol", f"{summary['Volatility %'].median():.2f}%")
        c5.metric("Worst max drawdown", f"{summary['Max Drawdown %'].min():.2f}%")

        st.plotly_chart(px.bar(summary.reset_index(), x="index", y="Total Return %", color="Total Return %", title="Total returns"), use_container_width=True)
        if not corr.empty:
            st.plotly_chart(px.imshow(corr, text_auto=".2f", title="Correlation matrix"), use_container_width=True)
        st.dataframe(summary.style.format("{:.2f}"), use_container_width=True)

        st.download_button("Download summary table CSV", data=summary.to_csv().encode(), file_name="summary.csv")
        st.download_button("Download aligned panel CSV", data=prices.to_csv().encode(), file_name="aligned_panel.csv")
        if not spread_proxy.empty:
            st.caption("Spread-change proxy via ETF return differentials.")
            st.dataframe(spread_proxy.style.format("{:.2f}"), use_container_width=True)

with tab2:
    if prices.empty:
        st.info("No chart data for this selection.")
    else:
        panel = ret_pct if chart_mode == "Cumulative return %" else normalized if chart_mode.startswith("Normalized") else prices
        y_title = "Return %" if chart_mode == "Cumulative return %" else "Index (start=100)" if chart_mode.startswith("Normalized") else "Price"

        if auto_scale and chart_mode == "Cumulative return %":
            main, outliers = autoscale_groups(panel)
            if outliers:
                st.warning("Auto-scale active: assets split into two charts due to extreme dispersion.")
            for title, cols in [("Main group", main), ("Outliers", outliers)]:
                if cols:
                    fig = go.Figure()
                    for col in cols:
                        fig.add_trace(go.Scatter(x=panel.index, y=panel[col], name=col, mode="lines"))
                    fig.update_layout(title=f"{chart_mode} - {title}", yaxis_title=y_title)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            fig = go.Figure()
            for col in panel.columns:
                fig.add_trace(go.Scatter(x=panel.index, y=panel[col], name=col, mode="lines"))
            if log_scale and chart_mode != "Cumulative return %":
                fig.update_yaxes(type="log")
            fig.update_layout(title=chart_mode, yaxis_title=y_title)
            st.plotly_chart(fig, use_container_width=True)

        single = st.selectbox("Single-asset drilldown", list(prices.columns))
        st.plotly_chart(px.line(prices[[single]], title=f"{single} price"), use_container_width=True)
        st.plotly_chart(px.line(drawdowns[[single]] * 100, title=f"{single} drawdown %"), use_container_width=True)
        if st.toggle("Show rolling volatility (20D)", value=False):
            st.plotly_chart(px.line(roll_vol[[single]] * 100, title=f"{single} rolling vol %"), use_container_width=True)

with tab3:
    style = st.selectbox("Style", ["English", "Spanish"], index=0)
    if "report_md" not in st.session_state:
        st.session_state.report_md = generate_report_markdown(start_date, end_date, summary, yields, universe, style)

    c1, c2 = st.columns(2)
    if c1.button("Regenerate"):
        st.session_state.report_md = generate_report_markdown(start_date, end_date, summary, yields, universe, style)
    if c2.button("Reset"):
        st.session_state.report_md = ""

    st.session_state.report_md = st.text_area("Editable report (Markdown)", st.session_state.report_md, height=500)
    st.session_state.report_html = markdown_to_basic_html(st.session_state.report_md, summary_df=summary, universe=universe)
    st.components.v1.html(st.session_state.report_html, height=350, scrolling=True)

with tab4:
    st.subheader("Email")
    recipients_text = st.text_input("Recipients", secret_get("DEFAULT_RECIPIENTS", ""))
    subject = st.text_input("Subject", f"Global Market Monitor | {start_date} to {end_date}")
    send_html = st.checkbox("Send as HTML", value=True)
    body_html = st.session_state.get("report_html", "<p>No report generated.</p>")
    st.components.v1.html(body_html, height=280, scrolling=True)

    if st.button("Send email"):
        keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_SENDER"]
        cfg = {k: secret_get(k) for k in keys}
        missing = [k for k, v in cfg.items() if not v]
        if missing:
            st.info("SMTP is not fully configured in Streamlit secrets.")
        else:
            recipients = [r.strip() for r in recipients_text.split(",") if r.strip()]
            if not recipients:
                st.warning("Please enter at least one recipient.")
            else:
                try:
                    send_email(
                        smtp_host=str(cfg["SMTP_HOST"]),
                        smtp_port=int(cfg["SMTP_PORT"]),
                        username=str(cfg["SMTP_USERNAME"]),
                        password=str(cfg["SMTP_PASSWORD"]),
                        sender=str(cfg["SMTP_SENDER"]),
                        recipients=recipients,
                        subject=subject,
                        body_text=st.session_state.get("report_md", ""),
                        body_html=body_html if send_html else None,
                        use_tls=bool(secret_get("SMTP_USE_TLS", True)),
                    )
                    st.success("Email sent successfully.")
                except Exception:
                    st.error("Email failed to send. Please verify SMTP settings.")

with tab5:
    st.markdown(
        """
### Data Sources
- yfinance (daily history)
- FRED via fredapi (optional)

### Limitations
- Non-trading days and symbol quirks can produce gaps.
- Some spread measures are ETF-return proxies, not true OAS.
- Ticker resolver uses fallback lists from `universe.yaml`.

### Version
v1.1.0
"""
    )
