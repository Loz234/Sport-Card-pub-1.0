from dataclasses import dataclass

from app.ml.features import BASELINE_FEATURES


@dataclass(frozen=True)
class PredictorMetadata:
    model_version: str
    feature_count: int
    trained: bool


def get_predictor_metadata(model_version: str) -> PredictorMetadata:
    return PredictorMetadata(model_version=model_version, feature_count=len(BASELINE_FEATURES), trained=False)
