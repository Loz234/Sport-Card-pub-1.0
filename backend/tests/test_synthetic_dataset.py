from __future__ import annotations

from collections import defaultdict
from statistics import mean

from app.data.synthetic_dataset import (
    DEFAULT_SYNTHETIC_SEED,
    LIQUIDITY_HIGH,
    LIQUIDITY_ILLIQUID,
    LIQUIDITY_LOW,
    SYNTHETIC_LABEL,
    TREND_FALLING,
    TREND_RISING,
    TREND_STABLE,
    VOLATILITY_HIGH,
    generate_synthetic_dataset,
)


def _card_price_changes(dataset: dict[str, list[dict[str, object]]]) -> dict[int, float]:
    by_card: dict[int, list[dict[str, object]]] = defaultdict(list)
    for sale in dataset["historical_sales"]:
        by_card[int(sale["card_id"])].append(sale)

    deltas: dict[int, float] = {}
    for card_id, sales in by_card.items():
        ordered = sorted(sales, key=lambda row: row["date"])
        deltas[card_id] = float(ordered[-1]["sale_price"]) - float(ordered[0]["sale_price"])
    return deltas


def test_synthetic_dataset_counts_and_sports() -> None:
    dataset = generate_synthetic_dataset()
    assert {sport["name"] for sport in dataset["sports"]} == {"NBA", "NFL", "MLB", "Soccer"}
    assert len(dataset["players"]) == 100
    assert len(dataset["cards"]) == 500
    assert len(dataset["historical_sales"]) == 5000
    assert len(dataset["current_listings"]) == 500


def test_synthetic_dataset_is_reproducible_with_fixed_seed() -> None:
    dataset_1 = generate_synthetic_dataset(seed=DEFAULT_SYNTHETIC_SEED)
    dataset_2 = generate_synthetic_dataset(seed=DEFAULT_SYNTHETIC_SEED)
    assert dataset_1 == dataset_2


def test_all_rows_are_clearly_marked_as_synthetic() -> None:
    dataset = generate_synthetic_dataset()
    for section_name in ("sports", "players", "cards", "historical_sales", "current_listings"):
        assert all(row["data_label"] == SYNTHETIC_LABEL for row in dataset[section_name])


def test_historical_sales_include_required_fields() -> None:
    sale = generate_synthetic_dataset()["historical_sales"][0]
    assert {"card_id", "card", "date", "sale_price", "marketplace", "grade", "sale_volume", "data_label"}.issubset(
        sale
    )


def test_dataset_contains_requested_market_profiles() -> None:
    dataset = generate_synthetic_dataset()
    cards = dataset["cards"]
    assert {card["trend_profile"] for card in cards} == {TREND_RISING, TREND_FALLING, TREND_STABLE}
    assert {card["liquidity_profile"] for card in cards} == {LIQUIDITY_HIGH, LIQUIDITY_LOW, LIQUIDITY_ILLIQUID}
    assert VOLATILITY_HIGH in {card["volatility_profile"] for card in cards}


def test_price_behavior_matches_trend_profiles() -> None:
    dataset = generate_synthetic_dataset()
    cards_by_id = {int(card["id"]): card for card in dataset["cards"]}
    deltas = _card_price_changes(dataset)

    rising = [delta for card_id, delta in deltas.items() if cards_by_id[card_id]["trend_profile"] == TREND_RISING]
    falling = [delta for card_id, delta in deltas.items() if cards_by_id[card_id]["trend_profile"] == TREND_FALLING]
    stable = [delta for card_id, delta in deltas.items() if cards_by_id[card_id]["trend_profile"] == TREND_STABLE]

    assert mean(rising) > 0
    assert mean(falling) < 0
    assert abs(mean(stable)) < mean(abs(delta) for delta in rising)


def test_liquidity_profiles_drive_volume_signals() -> None:
    dataset = generate_synthetic_dataset()
    cards_by_id = {int(card["id"]): card for card in dataset["cards"]}
    volume_per_card: dict[int, int] = defaultdict(int)
    sales_count_per_card: dict[int, int] = defaultdict(int)
    for sale in dataset["historical_sales"]:
        card_id = int(sale["card_id"])
        volume_per_card[card_id] += int(sale["sale_volume"])
        sales_count_per_card[card_id] += 1

    high = [
        volume_per_card[card_id]
        for card_id, card in cards_by_id.items()
        if card["liquidity_profile"] == LIQUIDITY_HIGH and card_id in volume_per_card
    ]
    low = [
        volume_per_card[card_id]
        for card_id, card in cards_by_id.items()
        if card["liquidity_profile"] == LIQUIDITY_LOW and card_id in volume_per_card
    ]
    illiquid = [
        sales_count_per_card[card_id]
        for card_id, card in cards_by_id.items()
        if card["liquidity_profile"] == LIQUIDITY_ILLIQUID and card_id in sales_count_per_card
    ]

    assert mean(high) > mean(low)
    assert mean(illiquid) < mean(low)
