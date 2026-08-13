from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.domain import Card, Player, Sport


@dataclass(frozen=True)
class CardIdentifier:
    athlete_name: str
    brand: str
    set_name: str
    year: int
    card_number: str

    @property
    def slug(self) -> str:
        parts = [
            str(self.year),
            self.brand,
            self.set_name,
            self.athlete_name,
            self.card_number,
        ]
        return "-".join(_normalize_part(part) for part in parts)


@dataclass(frozen=True)
class ParsedCard:
    raw_title: str
    sport: str | None = None
    player: str | None = None
    year: int | None = None
    manufacturer: str | None = None
    set_name: str | None = None
    card_number: str | None = None
    is_rookie: bool = False
    parallel: str | None = None
    serial_number: str | None = None
    is_autograph: bool = False
    is_memorabilia: bool = False
    grading_company: str | None = None
    grade: str | None = None
    confidence: float = 0.0
    extraction_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatchResult:
    is_match: bool
    confidence: float
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    confidence_boost: float = 0.0
    canonical_updates: dict[str, Any] = field(default_factory=dict)


class ListingLLMProvider(Protocol):
    def parse_listing_title(self, title: str) -> dict[str, Any] | None:
        """Return extracted card fields for ambiguous listing titles."""


class CardValidationProvider(Protocol):
    def validate(self, parsed: ParsedCard) -> ValidationResult:
        """Validate parsed fields against known card catalog data."""


class CardNormalizer:
    SPORT_ALIASES: dict[str, str] = {
        "nba": "basketball",
        "basketball": "basketball",
        "nfl": "football",
        "football": "football",
        "mlb": "baseball",
        "baseball": "baseball",
        "soccer": "soccer",
        "futbol": "soccer",
    }
    PLAYER_ALIASES: dict[str, str] = {
        "wemby": "victor wembanyama",
        "victor wembanyama": "victor wembanyama",
    }
    PLAYER_SPORT_LOOKUP: dict[str, str] = {
        "victor wembanyama": "basketball",
    }
    MANUFACTURER_ALIASES: dict[str, str] = {
        "topps": "topps",
        "panini": "panini",
        "upper deck": "upper deck",
    }
    SET_ALIASES: dict[str, str] = {
        "tc": "topps chrome",
        "topps chrome": "topps chrome",
        "chrome": "topps chrome",
        "prizm": "panini prizm",
    }
    PARALLEL_ALIASES: dict[str, str] = {
        "ref": "refractor",
        "refractor": "refractor",
        "silver": "silver",
        "gold": "gold",
    }
    GRADING_COMPANY_ALIASES: dict[str, str] = {
        "psa": "PSA",
        "bgs": "BGS",
        "sgc": "SGC",
        "cgc": "CGC",
    }

    def normalize_text(self, value: str) -> str:
        lowered = value.lower().strip()
        lowered = re.sub(r"[^a-z0-9/# ]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def normalize_token(self, value: str) -> str:
        return self.normalize_text(value)

    def canonical_from_alias(self, value: str, aliases: dict[str, str]) -> str | None:
        token = self.normalize_token(value)
        return aliases.get(token)

    def identity_key(self, parsed: ParsedCard) -> str:
        parts = [
            str(parsed.year or "unknown"),
            parsed.sport or "unknown",
            parsed.player or "unknown",
            parsed.manufacturer or "unknown",
            parsed.set_name or "unknown",
            parsed.card_number or "unknown",
            "rc" if parsed.is_rookie else "v",
            parsed.parallel or "base",
            parsed.serial_number or "ns",
            "auto" if parsed.is_autograph else "na",
            "mem" if parsed.is_memorabilia else "nm",
            parsed.grading_company or "raw",
            parsed.grade or "ungraded",
        ]
        return "|".join(_normalize_part(part) for part in parts)


class SQLCardValidationProvider:
    def __init__(self, db: Session, normalizer: CardNormalizer | None = None) -> None:
        self.db = db
        self.normalizer = normalizer or CardNormalizer()

    def validate(self, parsed: ParsedCard) -> ValidationResult:
        if not (parsed.year and parsed.player and parsed.manufacturer and parsed.set_name):
            return ValidationResult()

        statement = (
            select(Card, Player, Sport)
            .join(Player, Player.id == Card.player_id)
            .join(Sport, Sport.id == Card.sport_id)
            .where(Card.year == parsed.year)
            .where(func.lower(Player.name) == parsed.player.lower())
            .where(func.lower(Card.manufacturer) == parsed.manufacturer.lower())
            .where(func.lower(Card.set_name) == parsed.set_name.lower())
        )

        if parsed.card_number:
            statement = statement.where(func.lower(Card.card_number) == parsed.card_number.lower())

        row = self.db.execute(statement.limit(1)).first()
        if not row:
            return ValidationResult()

        card, player, sport = row
        updates: dict[str, Any] = {
            "player": player.name,
            "sport": sport.name.lower(),
            "manufacturer": card.manufacturer,
            "set_name": card.set_name,
            "card_number": card.card_number,
            "is_rookie": card.is_rookie,
        }
        return ValidationResult(confidence_boost=0.2, canonical_updates=updates)


class CardParser:
    YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
    TWO_DIGIT_YEAR_PATTERN = re.compile(r"\b(\d{2})\b")
    CARD_NUMBER_PATTERN = re.compile(r"(?:#|no\.?\s*)([a-z0-9-]{1,10})\b", re.IGNORECASE)
    SERIAL_PATTERN = re.compile(r"\b(\d{1,4}\s*/\s*\d{1,4})\b")
    GRADE_PATTERN = re.compile(r"\b(PSA|BGS|SGC|CGC)\s*([0-9]{1,2}(?:\.[0-9])?)\b", re.IGNORECASE)

    def __init__(
        self,
        normalizer: CardNormalizer | None = None,
        llm_provider: ListingLLMProvider | None = None,
        validator: CardValidationProvider | None = None,
    ) -> None:
        self.normalizer = normalizer or CardNormalizer()
        self.llm_provider = llm_provider
        self.validator = validator

    def parse(self, title: str) -> ParsedCard:
        normalized = self.normalizer.normalize_text(title)
        tokens = normalized.split()

        notes: list[str] = []
        score = 0.0

        sport = self._extract_sport(tokens)
        if sport:
            score += 0.08

        player = self._extract_player(normalized)
        if player:
            score += 0.22
            if not sport and player in self.normalizer.PLAYER_SPORT_LOOKUP:
                sport = self.normalizer.PLAYER_SPORT_LOOKUP[player]
                score += 0.06

        year = self._extract_year(normalized)
        if year:
            score += 0.12

        set_name = self._extract_set_name(tokens, normalized)
        if set_name:
            score += 0.12

        manufacturer = self._extract_manufacturer(tokens, set_name)
        if manufacturer:
            score += 0.08

        card_number = self._extract_card_number(normalized)
        if card_number:
            score += 0.06

        is_rookie = "rookie" in tokens or "rc" in tokens
        if is_rookie:
            score += 0.06

        parallel = self._extract_parallel(tokens)
        if parallel:
            score += 0.06

        serial_number = self._extract_serial(normalized)
        if serial_number:
            score += 0.05

        is_autograph = any(token in {"auto", "autograph", "signed"} for token in tokens)
        if is_autograph:
            score += 0.03

        is_memorabilia = any(token in {"patch", "relic", "jersey", "mem"} for token in tokens)
        if is_memorabilia:
            score += 0.03

        grading_company, grade = self._extract_grade(normalized)
        if grading_company:
            score += 0.05
        if grade:
            score += 0.04

        parsed = ParsedCard(
            raw_title=title,
            sport=sport,
            player=player,
            year=year,
            manufacturer=manufacturer,
            set_name=set_name,
            card_number=card_number,
            is_rookie=is_rookie,
            parallel=parallel,
            serial_number=serial_number,
            is_autograph=is_autograph,
            is_memorabilia=is_memorabilia,
            grading_company=grading_company,
            grade=grade,
            confidence=0.0,
            extraction_notes=tuple(notes),
        )

        parsed, score = self._apply_optional_llm(parsed, score)
        parsed, score = self._apply_validation(parsed, score)

        missing_core = sum(
            field_value is None
            for field_value in (parsed.player, parsed.year, parsed.manufacturer, parsed.set_name)
        )
        score -= 0.06 * missing_core
        confidence = max(0.0, min(1.0, round(score, 4)))
        return ParsedCard(**{**parsed.__dict__, "confidence": confidence})

    def _apply_optional_llm(self, parsed: ParsedCard, score: float) -> tuple[ParsedCard, float]:
        if not self.llm_provider:
            return parsed, score

        missing_core = [
            field_name
            for field_name in ("player", "year", "manufacturer", "set_name")
            if getattr(parsed, field_name) is None
        ]
        if not missing_core:
            return parsed, score

        llm_result = self.llm_provider.parse_listing_title(parsed.raw_title)
        if not llm_result:
            return parsed, score

        payload = parsed.__dict__.copy()
        filled_core = 0
        for field_name in (
            "sport",
            "player",
            "year",
            "manufacturer",
            "set_name",
            "card_number",
            "parallel",
            "serial_number",
            "grading_company",
            "grade",
        ):
            if payload[field_name] is None and llm_result.get(field_name) is not None:
                payload[field_name] = llm_result[field_name]
                if field_name in {"player", "year", "manufacturer", "set_name"}:
                    filled_core += 1

        if not payload["is_rookie"] and llm_result.get("is_rookie") is True:
            payload["is_rookie"] = True
        if not payload["is_autograph"] and llm_result.get("is_autograph") is True:
            payload["is_autograph"] = True
        if not payload["is_memorabilia"] and llm_result.get("is_memorabilia") is True:
            payload["is_memorabilia"] = True

        score += min(0.18, 0.06 * filled_core)
        return ParsedCard(**payload), score

    def _apply_validation(self, parsed: ParsedCard, score: float) -> tuple[ParsedCard, float]:
        if not self.validator:
            return parsed, score

        validation = self.validator.validate(parsed)
        if not validation.canonical_updates:
            return parsed, score + validation.confidence_boost

        payload = parsed.__dict__.copy()
        payload.update(validation.canonical_updates)
        return ParsedCard(**payload), score + validation.confidence_boost

    def _extract_sport(self, tokens: list[str]) -> str | None:
        for token in tokens:
            if token in self.normalizer.SPORT_ALIASES:
                return self.normalizer.SPORT_ALIASES[token]
        return None

    def _extract_player(self, normalized_title: str) -> str | None:
        for alias, canonical in self.normalizer.PLAYER_ALIASES.items():
            if alias in normalized_title:
                return canonical
        return None

    def _extract_year(self, normalized_title: str) -> int | None:
        match = self.YEAR_PATTERN.search(normalized_title)
        if match:
            return int(match.group(1))

        for token in normalized_title.split():
            if self.TWO_DIGIT_YEAR_PATTERN.fullmatch(token):
                as_int = int(token)
                if 0 <= as_int <= 30:
                    return 2000 + as_int
        return None

    def _extract_set_name(self, tokens: list[str], normalized_title: str) -> str | None:
        for alias, canonical in self.normalizer.SET_ALIASES.items():
            if alias in normalized_title:
                return canonical
        for token in tokens:
            canonical = self.normalizer.canonical_from_alias(token, self.normalizer.SET_ALIASES)
            if canonical:
                return canonical
        return None

    def _extract_manufacturer(self, tokens: list[str], set_name: str | None) -> str | None:
        for token in tokens:
            canonical = self.normalizer.canonical_from_alias(token, self.normalizer.MANUFACTURER_ALIASES)
            if canonical:
                return canonical

        if set_name == "topps chrome":
            return "topps"
        if set_name == "panini prizm":
            return "panini"
        return None

    def _extract_card_number(self, normalized_title: str) -> str | None:
        match = self.CARD_NUMBER_PATTERN.search(normalized_title)
        if not match:
            return None
        return match.group(1).upper()

    def _extract_parallel(self, tokens: list[str]) -> str | None:
        for token in tokens:
            canonical = self.normalizer.canonical_from_alias(token, self.normalizer.PARALLEL_ALIASES)
            if canonical:
                return canonical
        return None

    def _extract_serial(self, normalized_title: str) -> str | None:
        match = self.SERIAL_PATTERN.search(normalized_title)
        if not match:
            return None
        return re.sub(r"\s+", "", match.group(1))

    def _extract_grade(self, normalized_title: str) -> tuple[str | None, str | None]:
        match = self.GRADE_PATTERN.search(normalized_title)
        if match:
            company = self.normalizer.GRADING_COMPANY_ALIASES[match.group(1).lower()]
            return company, match.group(2)

        for alias, canonical in self.normalizer.GRADING_COMPANY_ALIASES.items():
            compact = f"{alias}10"
            if compact in normalized_title.replace(" ", ""):
                return canonical, "10"
        return None, None


class CardMatcher:
    def __init__(self, threshold: float = 0.78, normalizer: CardNormalizer | None = None) -> None:
        self.threshold = threshold
        self.normalizer = normalizer or CardNormalizer()

    def match(self, left: ParsedCard, right: ParsedCard) -> MatchResult:
        confidence = self._compute_match_confidence(left, right)
        if confidence < self.threshold:
            return MatchResult(
                is_match=False,
                confidence=confidence,
                reason="below-threshold-or-ambiguous",
            )
        return MatchResult(is_match=True, confidence=confidence, reason="high-confidence")

    def should_auto_match(self, parsed: ParsedCard) -> bool:
        return parsed.confidence >= self.threshold

    def _compute_match_confidence(self, left: ParsedCard, right: ParsedCard) -> float:
        weighted_fields = {
            "sport": 0.1,
            "player": 0.25,
            "year": 0.15,
            "manufacturer": 0.1,
            "set_name": 0.15,
            "card_number": 0.05,
            "is_rookie": 0.05,
            "parallel": 0.05,
            "serial_number": 0.03,
            "is_autograph": 0.03,
            "is_memorabilia": 0.02,
            "grading_company": 0.015,
            "grade": 0.015,
        }

        score = 0.0
        total = 0.0
        for field_name, weight in weighted_fields.items():
            left_value = getattr(left, field_name)
            right_value = getattr(right, field_name)

            if left_value is None or right_value is None:
                continue

            total += weight
            if left_value == right_value:
                score += weight

        if total == 0:
            return 0.0

        aligned = score / total
        confidence = aligned * min(left.confidence, right.confidence)
        return round(max(0.0, min(1.0, confidence)), 4)


def _normalize_part(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


__all__ = [
    "CardIdentifier",
    "ParsedCard",
    "MatchResult",
    "ValidationResult",
    "ListingLLMProvider",
    "CardValidationProvider",
    "CardNormalizer",
    "SQLCardValidationProvider",
    "CardParser",
    "CardMatcher",
]
