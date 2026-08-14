from __future__ import annotations

from app.services.card_identification import (
    CardMatcher,
    CardNormalizer,
    CardParser,
    CardValidationProvider,
    ListingLLMProvider,
    ParsedCard,
    ValidationResult,
)


class StubLLMProvider(ListingLLMProvider):
    def parse_listing_title(self, title: str) -> dict[str, object] | None:
        if "chrome" not in title.lower():
            return None
        return {
            "player": "victor wembanyama",
            "year": 2024,
            "manufacturer": "topps",
            "set_name": "topps chrome",
            "is_rookie": True,
        }


class StubValidationProvider(CardValidationProvider):
    def validate(self, parsed: ParsedCard) -> ValidationResult:
        if parsed.player == "victor wembanyama":
            return ValidationResult(
                confidence_boost=0.1,
                canonical_updates={"sport": "basketball", "set_name": "topps chrome"},
            )
        return ValidationResult()


def test_card_parser_extracts_core_fields_from_messy_titles() -> None:
    parser = CardParser(normalizer=CardNormalizer())
    titles = [
        "2024 Topps Chrome Wemby RC Refractor PSA 10",
        "Victor Wembanyama Topps Chrome 24 Rookie Refractor Gem PSA10",
        "2024 TC WEMBY REF PSA10",
    ]

    parsed_cards = [parser.parse(title) for title in titles]

    for parsed in parsed_cards:
        assert parsed.player == "victor wembanyama"
        assert parsed.year == 2024
        assert parsed.manufacturer == "topps"
        assert parsed.set_name == "topps chrome"
        assert parsed.parallel == "refractor"
        assert parsed.grading_company == "PSA"
        assert parsed.grade == "10"
        assert parsed.confidence >= 0.66


def test_card_matcher_matches_equivalent_titles_above_threshold() -> None:
    parser = CardParser(normalizer=CardNormalizer())
    matcher = CardMatcher(threshold=0.70)

    left = parser.parse("2024 Topps Chrome Wemby RC Refractor PSA 10")
    right = parser.parse("2024 TC WEMBY REF PSA10")

    result = matcher.match(left, right)

    assert result.is_match is True
    assert result.confidence >= 0.70


def test_card_matcher_blocks_ambiguous_cards_below_threshold() -> None:
    parser = CardParser(normalizer=CardNormalizer())
    matcher = CardMatcher(threshold=0.80)

    ambiguous = parser.parse("Wemby refractor PSA10")

    assert matcher.should_auto_match(ambiguous) is False
    assert ambiguous.confidence < 0.80


def test_parser_uses_abstract_llm_provider_for_missing_fields() -> None:
    parser = CardParser(normalizer=CardNormalizer(), llm_provider=StubLLMProvider())

    parsed = parser.parse("Chrome rookie PSA10")

    assert parsed.player == "victor wembanyama"
    assert parsed.year == 2024
    assert parsed.manufacturer == "topps"
    assert parsed.set_name == "topps chrome"
    assert parsed.is_rookie is True
    assert parsed.confidence >= 0.55


def test_parser_applies_database_validation_updates_and_confidence_boost() -> None:
    parser = CardParser(
        normalizer=CardNormalizer(),
        validator=StubValidationProvider(),
    )

    parsed = parser.parse("2024 TC WEMBY REF PSA10")

    assert parsed.sport == "basketball"
    assert parsed.set_name == "topps chrome"
    assert parsed.confidence >= 0.75
