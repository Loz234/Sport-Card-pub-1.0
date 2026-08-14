from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.data.synthetic_dataset import generate_synthetic_dataset
from app.ml.predictor import CardSignalPredictionEngine, MarketFeaturePipeline


def _training_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    dataset = generate_synthetic_dataset(
        seed=20260814,
        cards_count=220,
        historical_sales_count=5000,
        current_listings_count=400,
        reference_now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return dataset["historical_sales"], dataset["current_listings"]


def test_feature_pipeline_uses_time_ordered_splits_without_lookahead() -> None:
    sales, listings = _training_data()
    pipeline = MarketFeaturePipeline()
    vectors = pipeline.build_feature_vectors(sales=sales, listings=listings)

    assert vectors
    split = pipeline.split_by_time(vectors)
    assert split.train and split.validation and split.test
    assert max(row.as_of for row in split.train) <= min(row.as_of for row in split.validation)
    assert max(row.as_of for row in split.validation) <= min(row.as_of for row in split.test)


def test_xgboost_pipeline_trains_and_reports_out_of_sample_metrics() -> None:
    sales, listings = _training_data()
    engine = CardSignalPredictionEngine(model_version="xgb-v1")
    _, performance = engine.train(sales=sales, listings=listings)

    for horizon in (7, 30, 90):
        xgb_metrics = performance.xgboost[horizon]
        baseline_metrics = performance.baseline[horizon]
        assert xgb_metrics.mae >= 0
        assert xgb_metrics.rmse >= 0
        assert xgb_metrics.mape >= 0
        assert 0 <= xgb_metrics.directional_accuracy <= 1
        assert xgb_metrics.rmse <= baseline_metrics.rmse * 1.2


def test_prediction_output_matches_contract() -> None:
    sales, listings = _training_data()
    engine = CardSignalPredictionEngine(model_version="xgb-v1")
    split, _ = engine.train(sales=sales, listings=listings)

    sample = split.test[0]
    prediction = engine.predict_from_features(sample.values)
    assert prediction.direction in {"UP", "DOWN", "STABLE"}
    assert isinstance(prediction.predicted_change_30d, float)
    assert 0.0 <= prediction.confidence <= 1.0
    assert prediction.model_version == "xgb-v1"


def test_model_persistence_and_versioning_round_trip(tmp_path: Path) -> None:
    sales, listings = _training_data()
    engine = CardSignalPredictionEngine(model_version="xgb-v2")
    split, _ = engine.train(sales=sales, listings=listings)

    model_dir = tmp_path / "models" / "xgb-v2"
    engine.save(model_dir)

    loaded = CardSignalPredictionEngine.load(model_dir)
    prediction_before = engine.predict_from_features(split.test[0].values)
    prediction_after = loaded.predict_from_features(split.test[0].values)

    assert loaded.model_version == "xgb-v2"
    assert prediction_before.direction == prediction_after.direction
    assert abs(prediction_before.predicted_change_30d - prediction_after.predicted_change_30d) < 1e-6
