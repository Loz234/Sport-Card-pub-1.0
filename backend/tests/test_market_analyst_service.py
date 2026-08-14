from app.ai.market_analyst_service import (
    MarketAnalystInput,
    MarketAnalystService,
    TemplateMarketAnalystProvider,
    get_market_analyst_provider,
)


def test_market_analyst_returns_structured_sections() -> None:
    service = MarketAnalystService(provider=TemplateMarketAnalystProvider())
    report = service.generate_report(
        MarketAnalystInput(
            card_name="2024 Panini Prizm #1",
            current_price=129.0,
            recent_prices=(138.0, 135.0, 132.0, 130.0, 128.0),
            predicted_movement=11.5,
            confidence=0.87,
            sales_volume=10,
            sales_velocity=0.33,
            momentum=22.0,
            trending_score=0.78,
            data_quality="high",
        )
    )

    assert report.summary
    assert len(report.positive_signals) > 0
    assert len(report.risks) > 0
    assert len(report.why_model_may_be_wrong) > 0
    assert "guaranteed" not in report.summary.lower()
    assert "certainty" in report.confidence.lower() or "probabilistic" in report.confidence.lower()


def test_market_analyst_handles_missing_values_without_fabrication() -> None:
    service = MarketAnalystService(provider=TemplateMarketAnalystProvider())
    report = service.generate_report(
        MarketAnalystInput(
            card_name="1990 Upper Deck #SP1",
            current_price=None,
            recent_prices=(),
            predicted_movement=None,
            confidence=None,
            sales_volume=0,
            sales_velocity=0.0,
            momentum=None,
            trending_score=None,
            data_quality="unknown",
        )
    )

    assert "N/A" in report.summary
    assert any("low" in risk.lower() or "unknown" in risk.lower() for risk in report.risks)
    assert any("prediction" in reason.lower() or "historical" in reason.lower() for reason in report.why_model_may_be_wrong)


def test_market_analyst_provider_factory_is_swappable() -> None:
    provider = get_market_analyst_provider("template")
    assert provider.provider_name == "template"

    fallback_provider = get_market_analyst_provider("future-provider")
    assert fallback_provider.provider_name == "template"
