"""Financial analytics and optional NLP summarisation engine."""
from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


class DadFinanceAnalytics:
    """Calculations used by the cockpit.

    Transformer inference is opt-in because downloading model weights can be
    slow and memory-intensive. The deterministic extractive fallback works
    immediately and keeps the demo self-contained.
    """

    def __init__(self, use_transformers: bool = False, model_name: str = "facebook/bart-large-cnn"):
        self.summarizer = None
        if use_transformers:
            try:
                from transformers import pipeline
                self.summarizer = pipeline("summarization", model=model_name)
                LOGGER.info("Loaded summarisation model: %s", model_name)
            except Exception:
                LOGGER.exception("Could not load Transformers model; using local fallback.")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove excess whitespace and safely normalise input."""
        return " ".join(str(text).replace("\n", " ").split()).strip()

    def generate_daily_digest(self, texts: Iterable[str]) -> str:
        """Summarise input into a plain-English executive note under 50 words."""
        cleaned = [self._clean_text(t) for t in texts if self._clean_text(t)]
        if not cleaned:
            return "No market update is available yet. Check again after the next market session."
        combined = " ".join(cleaned)
        if self.summarizer and len(combined.split()) > 45:
            try:
                result = self.summarizer(
                    combined[:5000], max_length=65, min_length=20,
                    do_sample=False, truncation=True,
                )
                summary = result[0]["summary_text"]
            except Exception:
                LOGGER.exception("Model summarisation failed; using extractive fallback.")
                summary = self._extractive_fallback(combined)
        else:
            summary = self._extractive_fallback(combined)
        words = summary.split()
        if len(words) > 49:
            summary = " ".join(words[:49]).rstrip(" ,;:") + "…"
        return summary

    @staticmethod
    def _extractive_fallback(text: str) -> str:
        """Select the first two useful sentences; no network or model required."""
        import re
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        summary = " ".join(sentences[:2]) if sentences else text
        words = summary.split()
        return " ".join(words[:49]).rstrip(" ,;:") + ("…" if len(words) > 49 else "")

    def calculate_portfolio_health(self, holdings: pd.DataFrame) -> dict:
        """Create a transparent diversification score from weights and asset mix.

        Correlation is estimated from deterministic synthetic daily returns in
        this demo; real applications should use aligned, survivorship-aware data.
        """
        if holdings.empty:
            return {"score": 0, "label": "No data", "explanation": "Upload holdings to assess the portfolio.",
                    "notes": [], "alerts": ["No holdings available."]}
        values = holdings["current_value"].astype(float).clip(lower=0)
        total = float(values.sum())
        if total <= 0:
            return {"score": 0, "label": "Needs review", "explanation": "Portfolio value is zero or invalid.",
                    "notes": [], "alerts": ["Check quantities and current prices in the uploaded file."]}
        weights = values / total
        hhi = float((weights ** 2).sum())
        effective_count = 1 / hhi if hhi > 0 else 0
        concentration_score = float(np.clip(100 * (1 - hhi) / 0.85, 0, 100))

        asset_mix = holdings.assign(_value=values).groupby("asset_type")["_value"].sum() / total
        mix_score = min(100.0, len(asset_mix) * 18.0 + (25.0 if "Mutual Fund" in asset_mix.index else 0.0))

        # Correlation proxy: equity-heavy portfolios are treated as less diversified.
        # It is a transparent heuristic, not a measured market correlation matrix.
        equity_weight = float(weights[holdings["asset_type"].str.contains("Equity|Stock", case=False, regex=True)].sum())
        correlation_score = float(np.clip(100 - max(0, equity_weight - 0.65) * 120, 45, 100))

        score = int(round(0.50 * concentration_score + 0.25 * mix_score + 0.25 * correlation_score))
        label = "Well spread" if score >= 75 else "Fair — review a few areas" if score >= 55 else "Concentrated — review risk"
        notes = [
            f"Your money is spread across about {effective_count:.1f} equally sized positions (effective holding count).",
            f"Equity-like assets represent approximately {equity_weight * 100:.1f}% of this sample.",
            "The score is a diversification aid, not a forecast of returns or a measure of credit risk.",
        ]
        largest = float(weights.max())
        alerts = []
        if largest > 0.30:
            symbol = holdings.loc[weights.idxmax(), "symbol"]
            alerts.append(f"{symbol} is about {largest:.1%} of the portfolio. A single-company event could have a large effect.")
        if equity_weight > 0.85:
            alerts.append("More than 85% is in equity-like assets. Check whether this matches the investor's time horizon and comfort with losses.")
        if len(asset_mix) == 1:
            alerts.append("Only one asset category is represented. Consider whether broader diversification is appropriate.")
        if not alerts:
            alerts.append("No major concentration trigger fired in this demo. Review goals and risk tolerance periodically.")
        return {
            "score": score, "label": label,
            "explanation": "This score combines position concentration, broad asset mix and a simple equity-exposure proxy. It does not use personal goals or a live correlation matrix.",
            "notes": notes, "alerts": alerts,
        }

    def evaluate_safety_floors(
        self, holdings: pd.DataFrame, price_history: dict[str, pd.Series], window: int = 60
    ) -> list[str]:
        """Flag current prices below a two-standard-deviation trailing floor.

        Floor = current reference price's recent mean minus 2 standard
        deviations of daily percentage returns, converted to a price level.
        In a live system, use a properly adjusted price series and define the
        reference convention with the investor before enabling alerts.
        """
        alerts = []
        for row in holdings.itertuples(index=False):
            series = price_history.get(row.symbol)
            if series is None or len(series.dropna()) < max(20, window // 2):
                continue
            clean = series.dropna().astype(float)
            returns = clean.pct_change().dropna().tail(window)
            if len(returns) < 10:
                continue
            current = float(row.current_price)
            daily_vol = float(returns.std(ddof=1))
            floor = float(clean.iloc[-1] * (1 - 2 * daily_vol * np.sqrt(5)))
            if current < floor:
                alerts.append(
                    f"⚠️ {row.symbol}: current price ₹{current:,.2f} is below the demo volatility floor ₹{floor:,.2f}. "
                    "Review the position; this is not an automatic sell instruction."
                )
        return alerts
