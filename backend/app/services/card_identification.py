from dataclasses import dataclass
import re


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


def _normalize_part(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
