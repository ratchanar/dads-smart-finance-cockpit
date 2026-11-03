"""Deterministic demo data and CSV validation helpers."""
from __future__ import annotations

import io
import numpy as np
import pandas as pd


def generate_demo_portfolio() -> pd.DataFrame:
    """Return a plausible Indian long-term sample portfolio."""
    rows = [
        ("RELIANCE", "Reliance Industries", "Equity", 35, 2450, 2910),
        ("HDFCBANK", "HDFC Bank", "Equity", 80, 1510, 1685),
        ("TCS", "Tata Consultancy Services", "Equity", 22, 3520, 3980),
        ("INFY", "Infosys", "Equity", 45, 1420, 1585),
        ("ICICIBANK", "ICICI Bank", "Equity", 40, 980, 1260),
        ("NIFTY50MF", "Nifty 50 Index Fund", "Mutual Fund", 1200, 185, 224),
        ("FLEXICAPMF", "Flexi Cap Mutual Fund", "Mutual Fund", 950, 92, 108),
        ("GOLDETF", "Gold ETF", "ETF", 300, 48, 61),
    ]
    df = pd.DataFrame(rows, columns=["symbol", "name", "asset_type", "quantity", "avg_cost", "current_price"])
    return enrich_holdings(df)


def enrich_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate market value, cost basis, weights and P&L from core columns."""
    data = df.copy()
    data["quantity"] = pd.to_numeric(data["quantity"], errors="raise")
    data["avg_cost"] = pd.to_numeric(data["avg_cost"], errors="raise")
    data["current_price"] = pd.to_numeric(data["current_price"], errors="raise")
    if (data[["quantity", "avg_cost", "current_price"]] < 0).any().any():
        raise ValueError("Quantity, average cost and current price must be non-negative.")
    data["invested_value"] = data["quantity"] * data["avg_cost"]
    data["current_value"] = data["quantity"] * data["current_price"]
    total = float(data["current_value"].sum())
    data["weight_pct"] = data["current_value"] / total * 100 if total else 0.0
    data["pnl_pct"] = np.where(data["invested_value"] > 0,
                              (data["current_value"] / data["invested_value"] - 1) * 100, 0.0)
    return data


def load_portfolio_csv(uploaded_file) -> pd.DataFrame:
    """Read and validate user CSV; accept a small set of common aliases."""
    df = pd.read_csv(uploaded_file)
    aliases = {
        "ticker": "symbol", "stock": "symbol", "holding": "symbol",
        "type": "asset_type", "category": "asset_type",
        "units": "quantity", "qty": "quantity",
        "average_cost": "avg_cost", "buy_price": "avg_cost",
        "ltp": "current_price", "price": "current_price",
    }
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    required = {"symbol", "quantity", "avg_cost", "current_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if "name" not in df:
        df["name"] = df["symbol"]
    if "asset_type" not in df:
        df["asset_type"] = "Equity"
    df = df[["symbol", "name", "asset_type", "quantity", "avg_cost", "current_price"]].dropna(subset=["symbol"])
    if df.empty:
        raise ValueError("The CSV contains no usable holdings.")
    return enrich_holdings(df)


def generate_demo_headlines() -> list[dict]:
    return [
        {
            "source": "Market Desk", "time": "08:45 AM",
            "headline": "Banks and IT shares support a steady start for Indian equities",
            "body": "Large private banks and technology companies gained in early trade as investors reacted to stable global cues and steady domestic institutional flows. Traders continued to monitor interest-rate expectations and quarterly earnings.",
            "impact": "A broad advance can support index performance, but the move may not be shared by every company.",
        },
        {
            "source": "Business Bulletin", "time": "11:20 AM",
            "headline": "Crude oil eases; energy and airline investors assess the impact",
            "body": "Oil prices softened in the simulated session after supply concerns eased. Lower crude can reduce input costs for some businesses, while upstream producers may face pressure if lower prices persist.",
            "impact": "The effect differs across companies; input costs and selling prices both matter.",
        },
        {
            "source": "IPO Watch", "time": "01:10 PM",
            "headline": "Primary market activity remains selective as investors compare valuations",
            "body": "Investors are paying close attention to issue pricing, profitability, cash generation and the use of IPO proceeds. A popular subscription number alone does not establish whether an offer is attractively valued.",
            "impact": "Reading the offer document and comparing peers is more useful than relying on hype.",
        },
    ]


def generate_demo_ipo_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"Company": "Aarohan Consumer Ltd. (Demo)", "Issue window": "12–14 Nov 2026",
         "Price band": "₹210–₹225", "Issue size": "₹1,250 Cr", "Status": "Upcoming",
         "Illustrative bucket": "🛡️ Safe Long-Term Bet", "Key check": "Profitable growth; verify valuation and debt"},
        {"Company": "NavaGrid Energy Ltd. (Demo)", "Issue window": "05–07 Nov 2026",
         "Price band": "₹145–₹155", "Issue size": "₹820 Cr", "Status": "Open",
         "Illustrative bucket": "🔥 High Listing Gain Potential", "Key check": "High demand assumption; listing gains uncertain"},
        {"Company": "MetroNova Tech Ltd. (Demo)", "Issue window": "Closed — demo",
         "Price band": "₹480–₹510", "Issue size": "₹2,100 Cr", "Status": "Closed",
         "Illustrative bucket": "❌ Avoid/Overvalued", "Key check": "Rich peer multiple; growth must justify price"},
    ])


def generate_deep_value_watchlist() -> pd.DataFrame:
    return pd.DataFrame([
        {"Nifty company": "HDFC Bank", "Illustrative discount": "12%", "Business quality note": "Large diversified lender",
         "What to verify": "Loan growth, deposit mix, asset quality"},
        {"Nifty company": "ITC", "Illustrative discount": "9%", "Business quality note": "Consumer and staples exposure",
         "What to verify": "Volume growth, margins, capital allocation"},
        {"Nifty company": "Infosys", "Illustrative discount": "15%", "Business quality note": "Established IT services franchise",
         "What to verify": "Deal wins, guidance, client spending"},
        {"Nifty company": "Larsen & Toubro", "Illustrative discount": "8%", "Business quality note": "Engineering and infrastructure exposure",
         "What to verify": "Order execution, working capital, project margins"},
    ])


def generate_price_history(holdings: pd.DataFrame, days: int = 100) -> dict[str, pd.Series]:
    """Create reproducible synthetic daily prices for safety-floor UI testing."""
    rng = np.random.default_rng(20261103)
    history = {}
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    for row in holdings.itertuples(index=False):
        drift = 0.00025
        volatility = 0.012 if row.asset_type == "Equity" else 0.006
        returns = rng.normal(drift, volatility, days)
        prices = float(row.current_price) * np.exp(np.cumsum(returns - drift))
        history[row.symbol] = pd.Series(prices, index=dates, name=row.symbol)
    return history
