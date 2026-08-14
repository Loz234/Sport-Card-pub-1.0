from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MarketAnalystInput:
    card_name: str
    current_price: float | None
    recent_prices: tuple[float, ...]
    predicted_movement: float | None
    confidence: float | None
    sales_volume: int
    sales_velocity: float
    momentum: float | None
    trending_score: float | None
    data_quality: str


@dataclass(frozen=True)
class MarketAnalystReport:
    summary: str
    positive_signals: tuple[str, ...]
    risks: tuple[str, ...]
    why_model_may_be_wrong: tuple[str, ...]
    confidence: str


class MarketAnalystProvider(Protocol):
    provider_name: str

    def generate(self, payload: MarketAnalystInput) -> MarketAnalystReport: ...


class TemplateMarketAnalystProvider:
    provider_name = "template"

    def generate(self, payload: MarketAnalystInput) -> MarketAnalystReport:
        summary = (
            f"{payload.card_name}: validated current price {self._currency(payload.current_price)}; "
            f"model-predicted movement {self._percent(payload.predicted_movement)}; "
            f"model confidence {self._confidence_pct(payload.confidence)}."
        )

        positive_signals: list[str] = []
        if payload.predicted_movement is not None and payload.predicted_movement > 0:
            positive_signals.append(
                f"Predicted movement is positive at {payload.predicted_movement:+.2f}% based on validated ML output."
            )
        if payload.momentum is not None and payload.momentum > 0:
            positive_signals.append(f"Validated momentum is positive at {payload.momentum:+.2f}%.")
        if payload.trending_score is not None and payload.trending_score > 0:
            positive_signals.append(f"Trending score is positive at {payload.trending_score:.2f}.")
        if payload.sales_volume > 0:
            positive_signals.append(
                f"Validated activity includes {payload.sales_volume} recent sales at {payload.sales_velocity:.2f} sales/day."
            )
        if not positive_signals:
            positive_signals.append("No strong positive signals were present in the provided validated data.")

        risks: list[str] = []
        if payload.predicted_movement is not None and payload.predicted_movement < 0:
            risks.append(f"Predicted movement is negative at {payload.predicted_movement:+.2f}%.")
        if payload.confidence is not None and payload.confidence < 0.6:
            risks.append(f"Model confidence is low at {(payload.confidence * 100):.2f}%.")
        if payload.sales_volume < 3:
            risks.append("Recent validated sales volume is low, which can increase noise.")
        if payload.data_quality.lower() in {"low", "unknown"}:
            risks.append(f"Data quality is {payload.data_quality.lower()}, reducing reliability.")
        if not risks:
            risks.append("No major risk flags were detected in the provided validated data, but outcomes remain uncertain.")

        reasons_model_wrong: list[str] = []
        if len(payload.recent_prices) < 4:
            reasons_model_wrong.append("Recent price history is limited, so the model may miss market regime changes.")
        reasons_model_wrong.append("Unexpected external events can invalidate historical patterns.")
        reasons_model_wrong.append("The prediction is probabilistic and should not be treated as a certain outcome.")
        if payload.trending_score is None:
            reasons_model_wrong.append("Trending score is unavailable, so demand context may be incomplete.")

        confidence = self._confidence_statement(payload=payload)

        return MarketAnalystReport(
            summary=summary,
            positive_signals=tuple(positive_signals),
            risks=tuple(risks),
            why_model_may_be_wrong=tuple(reasons_model_wrong),
            confidence=confidence,
        )

    def _confidence_statement(self, *, payload: MarketAnalystInput) -> str:
        if payload.confidence is None:
            return "Uncertain: model confidence is unavailable in validated data."
        if payload.confidence >= 0.8 and payload.data_quality.lower() == "high":
            return "Moderate-to-high confidence in signal quality, but not certainty."
        if payload.confidence >= 0.6:
            return "Moderate confidence; treat this as a probabilistic forecast."
        return "Low confidence; use caution and avoid treating this as a definitive outcome."

    def _currency(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"${value:.2f}"

    def _percent(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:+.2f}%"

    def _confidence_pct(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value * 100:.2f}%"


class MarketAnalystService:
    def __init__(self, provider: MarketAnalystProvider) -> None:
        self.provider = provider

    def generate_report(self, payload: MarketAnalystInput) -> MarketAnalystReport:
        return self.provider.generate(payload)


def get_market_analyst_provider(provider: str) -> MarketAnalystProvider:
    normalized = provider.strip().lower()
    if normalized in {"", "disabled", "template"}:
        return TemplateMarketAnalystProvider()
    return TemplateMarketAnalystProvider()


__all__ = [
    "MarketAnalystInput",
    "MarketAnalystReport",
    "MarketAnalystProvider",
    "TemplateMarketAnalystProvider",
    "MarketAnalystService",
    "get_market_analyst_provider",
]
