from app.data.synthetic_dataset import generate_synthetic_dataset


def synthetic_sale_rows() -> list[dict[str, object]]:
    dataset = generate_synthetic_dataset(historical_sales_count=2, current_listings_count=0)
    cards_by_id = {card["id"]: card for card in dataset["cards"]}
    rows: list[dict[str, object]] = []
    for sale in dataset["historical_sales"]:
        card = cards_by_id[int(sale["card_id"])]
        rows.append(
            {
                "athlete_name": card["player_name"],
                "brand": card["manufacturer"],
                "set_name": card["set_name"],
                "year": card["year"],
                "card_number": card["card_number"],
                "sale_date": sale["date"],
                "sale_price": sale["sale_price"],
                "currency": sale["currency"],
                "source_name": "synthetic_seed_sales",
            }
        )
    return rows
