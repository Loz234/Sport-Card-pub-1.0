from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class IngestionSource:
    name: str
    mode: Literal["synthetic", "manual_import"]
    description: str


SUPPORTED_INGESTION_SOURCES = [
    IngestionSource(
        name="synthetic_seed_sales",
        mode="synthetic",
        description="Synthetic sales rows for development and local testing only.",
    )
]
