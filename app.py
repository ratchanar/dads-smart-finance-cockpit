"""Dad's Smart Finance Cockpit — Streamlit entry point.

Run locally:
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

All market, portfolio and IPO data are clearly labelled DEMO data. No live
prices, investment recommendations, or external notifications are provided.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from analytics import DadFinanceAnalytics
from data import (
    generate_demo_headlines,
    generate_demo_ipo_data,
    generate_demo_portfolio,
    generate_deep_value_watchlist,
    generate_price_history,
    load_portfolio_csv,
)
from notifications import send_non_intrusive_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("dad_finance_cockpit")
IST = ZoneInfo("Asia/Kolkata")


def money(value: float) -> str:
    """Format INR values in a compact, readable way."""
    value = float(value)
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:,.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:,.2f} L"
    return f"₹{value:,.0f}"


def apply_styles() -> None:
    """Small CSS layer; Streamlit's own theme setting controls light/dark mode."""
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.35rem; padding-bottom: 2rem;}
        .hero {
          padding: 1.2rem 1.35rem; border-radius: 16px;
          background: linear-gradient(120deg, rgba(28,83,116,.16), rgba(30,145,120,.10));
          border: 1px solid rgba(128,128,128,.22); margin-bottom: 1rem;
        }
        .muted {opacity: .72; font-size: .88rem;}
        .metric-card {
          padding: 1rem; border: 1px solid rgba(128,128,128,.25);
          border-radius: 14px; min-height: 105px;
        }
        div[data-testid="stMetric"] {
          border: 1px solid rgba(128,128,128,.22);
          padding: 12px 14px; border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_daily_tea(analytics: DadFinanceAnalytics) -> None:
    st.subheader("The Daily Tea")
    st.caption("A calm, plain-English snapshot. All figures and headlines below are simulated demo data.")
    market = st.session_state.market_demo

    col1, col2, col3 = st.columns([1.25, 1, 1])
    with col1:
        st.markdown("#### Market mood")
        st.metric("Sentiment gauge", f'{market["sentiment"]}/100', market["sentiment_label"])
        st.progress(market["sentiment"] / 100)
        st.caption("0 = Extreme Fear · 50 = Neutral · 100 = Extreme Greed")
    with col2:
        st.markdown("#### NIFTY VIX regime")
        st.metric("Demo India VIX", f'{market["vix"]:.2f}', market["vix_change"])
        if market["vix"] < 15:
            st.success("🟢 Low volatility — relatively calm conditions")
        elif market["vix"] < 22:
            st.warning("🟡 Moderate volatility — expect normal swings")
        else:
            st.error("🔴 Elevated volatility — protect against sharp moves")
    with col3:
        st.markdown("#### Market snapshot")
        st.metric("NIFTY 50", f'{market["nifty"]:,.0f}', f'{market["nifty_change"]:+.2f}%')
        st.metric("SENSEX", f'{market["sensex"]:,.0f}', f'{market["sensex_change"]:+.2f}%')

    st.markdown("---")
    st.markdown("#### What happened today?")
    headlines = generate_demo_headlines()
    for item in headlines:
        with st.container(border=True):
            st.markdown(f"**{item['headline']}**")
            st.caption(f"{item['source']} · {item['time']} · DEMO HEADLINE")
            summary = analytics.generate_daily_digest([item["body"]])
            st.write(summary)
            st.caption(f"Why it may matter: {item['impact']}")


def render_portfolio(analytics: DadFinanceAnalytics) -> None:
    st.subheader("My Portfolio Auditor")
    st.caption("Start with the sample portfolio or upload a CSV statement. Uploaded data is processed in this session only.")
    uploaded = st.file_uploader(
        "Upload holdings CSV",
        type=["csv"],
        help="Expected columns: symbol, asset_type, quantity, avg_cost, current_price. Optional: name.",
        key="portfolio_upload",
    )

    if uploaded is not None:
        try:
            holdings = load_portfolio_csv(uploaded)
            st.success(f"Loaded {len(holdings)} holdings from your CSV.")
        except Exception as exc:
            LOGGER.exception("Portfolio CSV parsing failed")
            st.error(f"Could not read this file: {exc}")
            st.info("Showing the sample portfolio instead. Check the required column names and try again.")
            holdings = generate_demo_portfolio()
    else:
        holdings = generate_demo_portfolio()
        st.info("No file uploaded — showing a realistic sample portfolio.")

    health = analytics.calculate_portfolio_health(holdings)
    total_value = float(holdings["current_value"].sum())
    invested = float(holdings["invested_value"].sum())
    pnl = total_value - invested
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", money(total_value))
    c2.metric("Invested amount", money(invested))
    c3.metric("Unrealised P&L", money(pnl), f"{pnl / invested * 100:+.2f}%" if invested else "—")
    c4.metric("Health score", f'{health["score"]}/100', health["label"])

    st.markdown("#### Portfolio health")
    score_col, detail_col = st.columns([1, 2])
    with score_col:
        st.markdown(
            f"<div class='metric-card'><div class='muted'>PORTFOLIO HEALTH SCORE</div>"
            f"<div style='font-size:3rem;font-weight:750;line-height:1.2'>{health['score']}<span style='font-size:1rem'>/100</span></div>"
            f"<b>{health['label']}</b></div>",
            unsafe_allow_html=True,
        )
        st.progress(health["score"] / 100)
    with detail_col:
        st.write(health["explanation"])
        for note in health["notes"]:
            st.write(f"• {note}")

    st.markdown("#### Your holdings")
    display = holdings.copy()
    display["current_value"] = display["current_value"].map(money)
    display["invested_value"] = display["invested_value"].map(money)
    display["weight_pct"] = display["weight_pct"].map(lambda x: f"{x:.1f}%")
    display["pnl_pct"] = display["pnl_pct"].map(lambda x: f"{x:+.2f}%")
    st.dataframe(
        display[["symbol", "name", "asset_type", "quantity", "avg_cost", "current_price",
                 "invested_value", "current_value", "weight_pct", "pnl_pct"]],
        use_container_width=True, hide_index=True,
    )

    st.markdown("#### Allocation at a glance")
    allocation = holdings.groupby("asset_type", as_index=False)["current_value"].sum()
    left, right = st.columns([1, 1])
    with left:
        st.bar_chart(allocation.set_index("asset_type"))
    with right:
        st.markdown("#### Action alerts")
        for alert in health["alerts"]:
            st.warning(alert)
        if not health["alerts"]:
            st.success("No major concentration warning detected in this sample.")


def render_allocator() -> None:
    st.subheader("Smart Allocator & IPO Tracker")
    st.caption("IPO classifications and valuation indicators are illustrative research labels, not advice or live offers.")
    ipo = generate_demo_ipo_data()
    st.markdown("#### NSE Mainboard IPO tracker")
    st.dataframe(ipo, use_container_width=True, hide_index=True)
    st.caption("IPO dates, issue sizes, subscription figures and labels are mock values for interface demonstration.")
    st.markdown("#### AI Deep Value Discount — watchlist")
    watch = generate_deep_value_watchlist()
    st.dataframe(watch, use_container_width=True, hide_index=True)
    st.caption("Discount to estimated fair value is a hypothetical model output. It is not a target price.")


def render_alerts(analytics: DadFinanceAnalytics) -> None:
    st.subheader("Quiet Alert Central")
    st.caption("Choose what a future connected notification service should send. This demo only logs messages; it does not contact anyone.")
    with st.form("alert_preferences"):
        eod = st.toggle("End-of-Day WhatsApp / Email Capsule", value=True)
        st.caption("One concise digest around 4:00 PM IST. No intraday noise.")
        emergency = st.toggle("Emergency Shield Guard", value=True)
        st.caption("A notification only when NIFTY falls more than 2% or a holding breaches its modelled safety floor.")
        channel = st.radio("Preferred delivery channel", ["Email (mock)", "WhatsApp (mock)", "Both (mock)"], horizontal=True)
        save = st.form_submit_button("Save alert preferences", type="primary")
    if save:
        st.session_state.alert_preferences = {
            "eod": eod, "emergency": emergency, "channel": channel
        }
        st.success("Preferences saved for this browser session.")

    prefs = st.session_state.get("alert_preferences", {"eod": True, "emergency": True, "channel": "Email (mock)"})
    st.markdown("#### Current settings")
    st.write(f"- Daily capsule: **{'On' if prefs['eod'] else 'Off'}** at **4:00 PM IST**")
    st.write(f"- Emergency shield: **{'On' if prefs['emergency'] else 'Off'}**")
    st.write(f"- Channel: **{prefs['channel']}**")

    st.markdown("#### Safety-floor monitor (demo)")
    holdings = generate_demo_portfolio()
    prices = generate_price_history(holdings)
    alerts = analytics.evaluate_safety_floors(holdings, prices)
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("No sample holding has breached its modelled volatility floor.")

    if st.button("Send a test notification to application log"):
        result = send_non_intrusive_alert(
            "Dad's Smart Finance Cockpit: this is a test summary. No action is required.",
            prefs["channel"],
        )
        st.info(result)
        st.caption("For privacy and safety, real messaging credentials and delivery are intentionally not configured.")


def main() -> None:
    st.set_page_config(
        page_title="Dad's Smart Finance Cockpit",
        page_icon="☕",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_styles()
    st.title("☕ Dad's Smart Finance Cockpit")
    st.markdown(
        "<div class='hero'><h3 style='margin:0'>Invest calmly. Understand clearly. Stay informed.</h3>"
        "<p style='margin:.35rem 0 0 0'>A simple home for long-term investing, market context and IPO research.</p></div>",
        unsafe_allow_html=True,
    )
    now = datetime.now(IST)
    st.caption(f"Demo workspace · {now.strftime('%A, %d %B %Y · %I:%M %p IST')} · Not connected to live exchanges")

    if "market_demo" not in st.session_state:
        st.session_state.market_demo = {
            "sentiment": 61, "sentiment_label": "Mild optimism",
            "vix": 13.8, "vix_change": "-0.6 vs previous close",
            "nifty": 24865.4, "nifty_change": 0.62,
            "sensex": 81420.7, "sensex_change": 0.55,
        }

    analytics = DadFinanceAnalytics(use_transformers=False)
    tabs = st.tabs([
        "☕ The Daily Tea",
        "📁 My Portfolio Auditor",
        "🧭 Smart Allocator & IPO Tracker",
        "🔔 Quiet Alert Central",
    ])
    with tabs[0]:
        render_daily_tea(analytics)
    with tabs[1]:
        render_portfolio(analytics)
    with tabs[2]:
        render_allocator()
    with tabs[3]:
        render_alerts(analytics)

    st.markdown("---")
    st.caption(
        "Important: This is an educational demo with simulated data. It is not investment, tax or legal advice. "
        "Verify prices, filings, IPO details and suitability independently before making financial decisions."
    )


if __name__ == "__main__":
    main()
