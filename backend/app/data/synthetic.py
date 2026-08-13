from datetime import UTC, datetime, timedelta


def synthetic_sale_rows() -> list[dict[str, object]]:
    now = datetime.now(UTC)
    return [
        {
            "athlete_name": "Sample Athlete",
            "brand": "Topps Chrome",
            "set_name": "Demo Set",
            "year": 2024,
            "card_number": "SC-1",
            "sale_date": now - timedelta(days=14),
            "sale_price": 125.0,
            "currency": "USD",
            "source_name": "synthetic_seed_sales",
        },
        {
            "athlete_name": "Sample Athlete",
            "brand": "Topps Chrome",
            "set_name": "Demo Set",
            "year": 2024,
            "card_number": "SC-1",
            "sale_date": now - timedelta(days=7),
            "sale_price": 142.5,
            "currency": "USD",
            "source_name": "synthetic_seed_sales",
        },
    ]
