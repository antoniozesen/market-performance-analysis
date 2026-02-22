from __future__ import annotations

from datetime import date, datetime, timedelta
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
st.caption("Cross-asset comparison, narrative reporting, and email delivery.")

universe = load_universe()
all_categories = ["INDICES", "EU SECTORS", "US SECTORS", "CURRENCIES", "COMMODITIES", "BOND ETFs", "STYLE ETFs", "YIELDS"]


def preset_dates(preset: str) -> tuple[date, date]:
    today = date.today()
    if preset == "MTD":
        return today.replace(day=1), today
    if preset == "1M":
        return today - timedelta(days=30), today
    if preset == "3M":
        return today - timedelta(days=90), today
    if preset == "YTD":
        return today.replace(month=1, day=1), today
    if preset == "1Y":
        return today - timedelta(days=365), today
    return today - timedelta(days=90), today


with st.sidebar:
    st.header("Controls")
    preset = st.selectbox("Quick preset", ["3M", "MTD", "1M", "YTD", "1Y", "Custom"], index=0)
    ps, pe = preset_dates(preset)
    default_start = ps if preset != "Custom" else date.today() - timedelta(days=90)
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=pe)

    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

    selected_categories = st.multiselect("Categories", options=all_categories, default=["INDICES", "EU SECTORS", "US SECTORS"])

    assets_by_category: Dict[str, List[str]] = {}
    for cat in selected_categories:
        labels = list(universe.get(cat, {}).keys())
        assets_by_category[cat] = st.multiselect(f"Assets in {cat}", labels, default=labels[: min(8, len(labels))])

    custom_csv = st.text_input("Custom yfinance tickers (CSV)", placeholder="AAPL,MSFT,EWJ")
    chart_mode = st.radio("Chart mode", ["Normalized (Base 100)", "Absolute Prices"], index=0)
    returns_basis = st.radio("Returns basis", ["Adj Close", "Close"], index=0)
    st.selectbox("Frequency", ["Daily"], index=0)
    forward_fill = st.toggle("Forward-fill missing data", value=True)

label_to_ticker = {}
fred_map = {}
for cat, selected_labels in assets_by_category.items():
    for label in selected_labels:
        ticker = universe.get(cat, {}).get(label)
        if ticker:
            if cat == "YIELDS":
                fred_map[label] = ticker
            else:
                label_to_ticker[label] = ticker

label_to_ticker.update(parse_custom_tickers(custom_csv))

price_res = fetch_prices(label_to_ticker, start_date, end_date, prefer_adj_close=(returns_basis == "Adj Close"))
prices = align_panel(price_res.prices, start_date, end_date, forward_fill=forward_fill)
returns = compute_returns(prices)
summary = performance_summary(prices, returns)
corr = correlation_matrix(returns)
drawdowns = drawdown_from_prices(prices)
normalized = normalize_base_100(prices)
roll_vol = rolling_volatility(returns, window=20)

fred_key = st.secrets.get("FRED_API_KEY", None)
yields = fetch_fred_series(fred_map, start_date, end_date, fred_key)
if not yields.empty and {"US 2Y Yield", "US 10Y Yield"}.issubset(yields.columns):
    yields["US 2s10s Slope (bps)"] = (yields["US 10Y Yield"] - yields["US 2Y Yield"]) * 100

if price_res.failed:
    st.warning(f"Some tickers failed and were skipped: {', '.join(price_res.failed)}")
if prices.empty:
    st.error("No price data available for the selection.")

spread_proxy = compute_spread_proxies(summary)


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Charts", "Report Builder", "Email", "Settings / About"])

with tab1:
    if not summary.empty:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Best Performer", summary.index[0], f"{summary.iloc[0]['Total Return %']:.2f}%")
        c2.metric("Worst Performer", summary.index[-1], f"{summary.iloc[-1]['Total Return %']:.2f}%")
        c3.metric("Average Return", f"{summary['Total Return %'].mean():.2f}%")
        c4.metric("Median Volatility", f"{summary['Volatility %'].median():.2f}%")
        c5.metric("Worst Max DD", f"{summary['Max Drawdown %'].min():.2f}%")

        bar = px.bar(summary.reset_index(), x="index", y="Total Return %", color="Total Return %", title="Total Return by Asset")
        bar.update_layout(xaxis_title="Asset", yaxis_title="Return %")
        st.plotly_chart(bar, use_container_width=True)

        if not corr.empty:
            heat = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation Matrix (Daily Returns)")
            st.plotly_chart(heat, use_container_width=True)

        styled = summary.style.format(
            {
                "Total Return %": "{:.2f}",
                "Annualized Return %": "{:.2f}",
                "Volatility %": "{:.2f}",
                "Max Drawdown %": "{:.2f}",
                "Best Day %": "{:.2f}",
                "Worst Day %": "{:.2f}",
            }
        ).background_gradient(cmap="RdYlGn", subset=["Total Return %"])
        st.dataframe(styled, use_container_width=True)

        if not spread_proxy.empty:
            st.caption("Credit spread change proxies using ETF total-return differentials.")
            st.dataframe(spread_proxy.style.format({"Value": "{:.2f}"}), use_container_width=True)

        st.download_button("Download summary CSV", data=summary.to_csv().encode("utf-8"), file_name="summary.csv")
        st.download_button("Download aligned prices CSV", data=prices.to_csv().encode("utf-8"), file_name="prices_panel.csv")

with tab2:
    if not prices.empty:
        plot_df = normalized if chart_mode.startswith("Normalized") else prices
        if chart_mode == "Absolute Prices":
            st.warning("Absolute prices can distort multi-asset comparison due to scale differences.")
        fig = go.Figure()
        for col in plot_df.columns:
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], mode="lines", name=col))
        fig.update_layout(title="Multi-Asset Comparison", yaxis_title="Base 100" if chart_mode.startswith("Normalized") else "Price")
        st.plotly_chart(fig, use_container_width=True)

        single_asset = st.selectbox("Single-asset detail", options=list(prices.columns))
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.line(prices[[single_asset]], title=f"{single_asset} Price"), use_container_width=True)
        with col2:
            st.plotly_chart(px.line(drawdowns[[single_asset]] * 100, title=f"{single_asset} Drawdown %"), use_container_width=True)

        if st.toggle("Show rolling 20D volatility", value=False):
            st.plotly_chart(px.line(roll_vol * 100, title="Rolling 20D Volatility (Annualized, %)"), use_container_width=True)

        st.plotly_chart(px.line(drawdowns * 100, title="Drawdown Comparison (%)"), use_container_width=True)

with tab3:
    style = st.selectbox("Style", ["English", "Spanish"], index=0)
    if "report_md" not in st.session_state:
        st.session_state.report_md = generate_report_markdown(start_date, end_date, summary, yields, universe, style)

    col_a, col_b = st.columns(2)
    if col_a.button("Regenerate"):
        st.session_state.report_md = generate_report_markdown(start_date, end_date, summary, yields, universe, style)
    if col_b.button("Reset"):
        st.session_state.report_md = ""

    st.session_state.report_md = st.text_area("Editable Markdown report", value=st.session_state.report_md, height=500)
    html_report = markdown_to_basic_html(st.session_state.report_md)
    st.session_state.report_html = html_report
    with st.expander("HTML Preview"):
        st.components.v1.html(html_report, height=400, scrolling=True)

with tab4:
    st.subheader("Email Delivery")
    recipients_default = st.secrets.get("DEFAULT_RECIPIENTS", "")
    recipients_text = st.text_input("Recipients (comma-separated)", value=recipients_default)
    subject_default = f"Global Market Monitor | {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}"
    subject = st.text_input("Subject", value=subject_default)
    send_html = st.checkbox("Send as HTML", value=True)

    preview_html = st.session_state.get("report_html", "<p>No report generated yet.</p>")
    st.caption("Email body preview")
    st.components.v1.html(preview_html, height=300, scrolling=True)

    if st.button("Send email"):
        smtp_host = st.secrets.get("SMTP_HOST")
        smtp_port = st.secrets.get("SMTP_PORT")
        smtp_user = st.secrets.get("SMTP_USERNAME")
        smtp_pass = st.secrets.get("SMTP_PASSWORD")
        smtp_sender = st.secrets.get("SMTP_SENDER")
        smtp_use_tls = bool(st.secrets.get("SMTP_USE_TLS", True))

        missing = [
            k
            for k, v in {
                "SMTP_HOST": smtp_host,
                "SMTP_PORT": smtp_port,
                "SMTP_USERNAME": smtp_user,
                "SMTP_PASSWORD": smtp_pass,
                "SMTP_SENDER": smtp_sender,
            }.items()
            if v in (None, "")
        ]
        if missing:
            st.info("SMTP is not fully configured. Please add required keys in Streamlit secrets.")
        else:
            recipients = [r.strip() for r in recipients_text.split(",") if r.strip()]
            if not recipients:
                st.warning("Please provide at least one recipient.")
            else:
                try:
                    send_email(
                        smtp_host=smtp_host,
                        smtp_port=int(smtp_port),
                        username=smtp_user,
                        password=smtp_pass,
                        sender=smtp_sender,
                        recipients=recipients,
                        subject=subject,
                        body_text=st.session_state.get("report_md", ""),
                        body_html=preview_html if send_html else None,
                        use_tls=smtp_use_tls,
                    )
                    st.success("Email sent successfully.")
                except Exception:
                    st.error("Email failed to send. Please verify SMTP settings and recipient list.")

with tab5:
    st.markdown(
        """
### Data Sources
- **yfinance** for market prices (daily history).
- **FRED** (fredapi) for macro yield series (optional if API key is available).

### Limitations
- Non-trading days can create gaps; optional forward-fill can smooth alignment.
- Bond and credit spread analysis includes ETF return-based proxies, not direct spread/OAS calculations.
- Data quality depends on external free providers.

### Version
- **v1.0.0**

### Changelog
- Initial public release with comparison dashboards, report builder, and SMTP email workflow.
"""
    )
