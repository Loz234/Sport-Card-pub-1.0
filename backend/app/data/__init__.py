"""Data ingestion and synthetic development datasets."""

from app.data.synthetic_dataset import DEFAULT_SYNTHETIC_SEED, SYNTHETIC_LABEL, generate_synthetic_dataset

__all__ = ["SYNTHETIC_LABEL", "DEFAULT_SYNTHETIC_SEED", "generate_synthetic_dataset"]
