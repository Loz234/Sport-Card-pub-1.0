from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random

SYNTHETIC_LABEL = "SYNTHETIC"
DEFAULT_SYNTHETIC_SEED = 20260813

SPORTS = ("NBA", "NFL", "MLB", "Soccer")
MANUFACTURERS = ("Topps", "Panini", "Upper Deck", "Leaf", "Donruss")
SETS = ("Chrome", "Prizm", "Select", "Mosaic", "Optic", "Finest", "Heritage")
MARKETPLACES = (
    "SYNTHETIC_EBAY",
    "SYNTHETIC_GOLDIN",
    "SYNTHETIC_ALT",
    "SYNTHETIC_COMC",
    "SYNTHETIC_STOCKX",
)
GRADES = ("PSA 10", "PSA 9", "BGS 9.5", "BGS 9", "SGC 10", "Raw")

TREND_RISING = "rising"
TREND_FALLING = "falling"
TREND_STABLE = "stable"

LIQUIDITY_HIGH = "high-volume"
LIQUIDITY_LOW = "low-volume"
LIQUIDITY_ILLIQUID = "illiquid"

VOLATILITY_HIGH = "highly-volatile"
VOLATILITY_LOW = "stable-volatility"


@dataclass(frozen=True)
class CardProfile:
    trend: str
    liquidity: str
    volatility: str


def _player_name(sport: str, index: int) -> str:
    normalized_sport = sport.replace(" ", "")
    return f"{normalized_sport} Player {index + 1}"


def _build_card_profiles() -> list[CardProfile]:
    # Include all required profile examples by construction, then cycle.
    base_profiles = [
        CardProfile(TREND_RISING, LIQUIDITY_HIGH, VOLATILITY_HIGH),
        CardProfile(TREND_RISING, LIQUIDITY_LOW, VOLATILITY_LOW),
        CardProfile(TREND_FALLING, LIQUIDITY_HIGH, VOLATILITY_LOW),
        CardProfile(TREND_FALLING, LIQUIDITY_LOW, VOLATILITY_HIGH),
        CardProfile(TREND_STABLE, LIQUIDITY_HIGH, VOLATILITY_LOW),
        CardProfile(TREND_STABLE, LIQUIDITY_LOW, VOLATILITY_HIGH),
        CardProfile(TREND_RISING, LIQUIDITY_ILLIQUID, VOLATILITY_HIGH),
        CardProfile(TREND_FALLING, LIQUIDITY_ILLIQUID, VOLATILITY_LOW),
        CardProfile(TREND_STABLE, LIQUIDITY_ILLIQUID, VOLATILITY_LOW),
    ]
    return base_profiles


def _sales_weight_for_liquidity(liquidity: str) -> float:
    if liquidity == LIQUIDITY_HIGH:
        return 3.5
    if liquidity == LIQUIDITY_LOW:
        return 1.0
    return 0.3


def _sale_volume_for_liquidity(rng: Random, liquidity: str) -> int:
    if liquidity == LIQUIDITY_HIGH:
        return rng.randint(4, 15)
    if liquidity == LIQUIDITY_LOW:
        return rng.randint(1, 4)
    return 1


def _trend_drift(trend: str, age_ratio: float) -> float:
    if trend == TREND_RISING:
        return 0.6 * age_ratio
    if trend == TREND_FALLING:
        return -0.45 * age_ratio
    return 0.05 * (age_ratio - 0.5)


def _volatility_noise(rng: Random, volatility: str) -> float:
    scale = 0.18 if volatility == VOLATILITY_HIGH else 0.05
    return rng.uniform(-scale, scale)


def generate_synthetic_dataset(
    *,
    seed: int = DEFAULT_SYNTHETIC_SEED,
    players_count: int = 100,
    cards_count: int = 500,
    historical_sales_count: int = 5000,
    current_listings_count: int = 500,
    reference_now: datetime = datetime(2026, 1, 1, tzinfo=UTC),
) -> dict[str, list[dict[str, object]]]:
    rng = Random(seed)
    now = reference_now
    profiles = _build_card_profiles()

    players: list[dict[str, object]] = []
    players_per_sport = players_count // len(SPORTS)
    leftovers = players_count % len(SPORTS)
    player_id = 1
    for sport_index, sport in enumerate(SPORTS):
        count = players_per_sport + (1 if sport_index < leftovers else 0)
        for player_index in range(count):
            players.append(
                {
                    "id": player_id,
                    "sport": sport,
                    "name": _player_name(sport, player_index),
                    "data_label": SYNTHETIC_LABEL,
                }
            )
            player_id += 1

    cards: list[dict[str, object]] = []
    for card_id in range(1, cards_count + 1):
        player = players[(card_id - 1) % len(players)]
        profile = profiles[(card_id - 1) % len(profiles)]
        release_year = rng.randint(1990, now.year)
        manufacturer = MANUFACTURERS[(card_id - 1) % len(MANUFACTURERS)]
        card_set = f"{SETS[(card_id - 1) % len(SETS)]} {release_year}"
        cards.append(
            {
                "id": card_id,
                "sport": player["sport"],
                "player_id": player["id"],
                "player_name": player["name"],
                "year": release_year,
                "manufacturer": manufacturer,
                "set_name": card_set,
                "card_number": f"{manufacturer[:2].upper()}-{card_id:04d}",
                "is_rookie": (release_year >= now.year - 3) and ((card_id % 5) == 0),
                "trend_profile": profile.trend,
                "liquidity_profile": profile.liquidity,
                "volatility_profile": profile.volatility,
                "data_label": SYNTHETIC_LABEL,
            }
        )

    cards_by_id = {card["id"]: card for card in cards}
    weighted_card_ids = [
        card["id"]
        for card in cards
        for _ in range(int(_sales_weight_for_liquidity(str(card["liquidity_profile"])) * 10))
    ]

    historical_sales: list[dict[str, object]] = []
    for sale_id in range(1, historical_sales_count + 1):
        card_id = int(rng.choice(weighted_card_ids))
        card = cards_by_id[card_id]
        days_back = rng.randint(1, 730)
        sale_date = now - timedelta(days=days_back)
        age_ratio = (730 - days_back) / 730
        base_price = 25 + (card_id % 60) * 12
        drift = _trend_drift(str(card["trend_profile"]), age_ratio)
        noise = _volatility_noise(rng, str(card["volatility_profile"]))
        sale_price = max(2.0, round(base_price * (1 + drift + noise), 2))

        historical_sales.append(
            {
                "id": sale_id,
                "card_id": card_id,
                "card": f"{card['year']} {card['manufacturer']} {card['set_name']} #{card['card_number']}",
                "date": sale_date,
                "sale_price": sale_price,
                "marketplace": rng.choice(MARKETPLACES),
                "grade": rng.choice(GRADES),
                "sale_volume": _sale_volume_for_liquidity(rng, str(card["liquidity_profile"])),
                "currency": "USD",
                "source": "SYNTHETIC_GENERATOR",
                "data_label": SYNTHETIC_LABEL,
            }
        )

    card_last_price: dict[int, float] = {}
    for sale in sorted(historical_sales, key=lambda item: item["date"]):
        card_last_price[int(sale["card_id"])] = float(sale["sale_price"])

    current_listings: list[dict[str, object]] = []
    for listing_id in range(1, current_listings_count + 1):
        card = cards[(listing_id - 1) % len(cards)]
        card_id = int(card["id"])
        anchor_price = card_last_price.get(card_id, 40.0)
        premium = rng.uniform(-0.1, 0.3)
        listing_price = max(2.0, round(anchor_price * (1 + premium), 2))
        current_listings.append(
            {
                "id": listing_id,
                "card_id": card_id,
                "card": f"{card['year']} {card['manufacturer']} {card['set_name']} #{card['card_number']}",
                "listing_price": listing_price,
                "marketplace": rng.choice(MARKETPLACES),
                "listing_url": f"https://synthetic.cardsignal.local/listings/{listing_id}",
                "listing_date": now - timedelta(days=rng.randint(0, 30)),
                "is_active": rng.random() > 0.12,
                "currency": "USD",
                "source": "SYNTHETIC_GENERATOR",
                "data_label": SYNTHETIC_LABEL,
            }
        )

    return {
        "sports": [{"name": sport, "data_label": SYNTHETIC_LABEL} for sport in SPORTS],
        "players": players,
        "cards": cards,
        "historical_sales": historical_sales,
        "current_listings": current_listings,
    }
