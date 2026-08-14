def build_card_name(*, year: int, manufacturer: str, set_name: str, card_number: str) -> str:
    core = f"{year} {manufacturer} {set_name}".strip()
    if card_number:
        return f"{core} #{card_number}"
    return core


__all__ = ["build_card_name"]
