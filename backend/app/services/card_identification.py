from dataclasses import dataclass


@dataclass(frozen=True)
class CardIdentifier:
    athlete_name: str
    brand: str
    set_name: str
    year: int
    card_number: str

    @property
    def slug(self) -> str:
        base = f"{self.year}-{self.brand}-{self.set_name}-{self.athlete_name}-{self.card_number}"
        return "-".join(segment.strip().lower().replace(" ", "-") for segment in base.split("-"))
