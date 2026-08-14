from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from math import sqrt
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
from xgboost import XGBRegressor

from app.ml.features import MARKET_PREDICTION_FEATURES

PredictionDirection = str
_HORIZONS = (7, 30, 90)


@dataclass(frozen=True)
class PredictorMetadata:
    model_version: str
    feature_count: int
    trained: bool


@dataclass(frozen=True)
class FeatureVector:
    card_id: int
    as_of: datetime
    current_price: float
    values: dict[str, float]
    targets: dict[int, float]


@dataclass(frozen=True)
class DatasetSplit:
    train: list[FeatureVector]
    validation: list[FeatureVector]
    test: list[FeatureVector]


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    mape: float
    directional_accuracy: float


@dataclass(frozen=True)
class ModelPerformance:
    xgboost: dict[int, RegressionMetrics]
    baseline: dict[int, RegressionMetrics]


@dataclass(frozen=True)
class PredictionOutput:
    direction: PredictionDirection
    predicted_change_7d: float
    predicted_change_30d: float
    predicted_change_90d: float
    confidence: float
    model_version: str


def get_predictor_metadata(model_version: str) -> PredictorMetadata:
    return PredictorMetadata(model_version=model_version, feature_count=len(MARKET_PREDICTION_FEATURES), trained=False)


class MarketFeaturePipeline:
    FEATURE_NAMES = [feature.name for feature in MARKET_PREDICTION_FEATURES]

    def build_feature_vectors(
        self,
        *,
        sales: Sequence[Mapping[str, Any]],
        listings: Sequence[Mapping[str, Any]],
        horizons: tuple[int, ...] = _HORIZONS,
    ) -> list[FeatureVector]:
        sales_by_card: dict[int, list[dict[str, Any]]] = {}
        for row in sales:
            card_id = int(row["card_id"])
            sales_by_card.setdefault(card_id, []).append(
                {
                    "date": _to_utc(row["date"]),
                    "sale_price": float(row["sale_price"]),
                }
            )
        for card_sales in sales_by_card.values():
            card_sales.sort(key=lambda row: row["date"])

        listings_by_card: dict[int, list[dict[str, Any]]] = {}
        for row in listings:
            card_id = int(row["card_id"])
            listings_by_card.setdefault(card_id, []).append(
                {
                    "listing_date": _to_utc(row["listing_date"]),
                    "is_active": bool(row["is_active"]),
                }
            )

        vectors: list[FeatureVector] = []
        max_horizon = max(horizons)
        for card_id, card_sales in sales_by_card.items():
            if len(card_sales) < 10:
                continue
            for idx in range(5, len(card_sales) - 1):
                as_of = card_sales[idx]["date"]
                past_sales = [sale for sale in card_sales if sale["date"] <= as_of]
                future_sales = [sale for sale in card_sales if as_of < sale["date"] <= as_of + timedelta(days=max_horizon)]
                if len(past_sales) < 5 or not future_sales:
                    continue

                features = self._compute_features(
                    card_id=card_id,
                    as_of=as_of,
                    past_sales=past_sales,
                    listings=listings_by_card.get(card_id, []),
                )
                if features is None:
                    continue

                targets = self._compute_targets(as_of=as_of, current_price=features["current_price"], sales=card_sales, horizons=horizons)
                if any(horizon not in targets for horizon in horizons):
                    continue
                vectors.append(
                    FeatureVector(
                        card_id=card_id,
                        as_of=as_of,
                        current_price=features["current_price"],
                        values={name: features[name] for name in self.FEATURE_NAMES},
                        targets=targets,
                    )
                )
        vectors.sort(key=lambda row: row.as_of)
        return vectors

    def split_by_time(
        self,
        vectors: Sequence[FeatureVector],
        *,
        train_ratio: float = 0.7,
        validation_ratio: float = 0.15,
    ) -> DatasetSplit:
        if not vectors:
            return DatasetSplit(train=[], validation=[], test=[])
        ordered = sorted(vectors, key=lambda row: row.as_of)
        train_end = max(1, int(len(ordered) * train_ratio))
        val_end = max(train_end + 1, int(len(ordered) * (train_ratio + validation_ratio)))
        val_end = min(val_end, len(ordered))
        return DatasetSplit(
            train=list(ordered[:train_end]),
            validation=list(ordered[train_end:val_end]),
            test=list(ordered[val_end:]),
        )

    def _compute_features(
        self,
        *,
        card_id: int,
        as_of: datetime,
        past_sales: Sequence[Mapping[str, float | datetime]],
        listings: Sequence[Mapping[str, Any]],
    ) -> dict[str, float] | None:
        sales_7 = self._window_sales(past_sales, as_of, days=7)
        sales_14 = self._window_sales(past_sales, as_of, days=14)
        sales_30 = self._window_sales(past_sales, as_of, days=30)
        sales_90 = self._window_sales(past_sales, as_of, days=90)
        if not sales_30 or not sales_90:
            return None

        price_7 = median(sale["sale_price"] for sale in sales_7) if sales_7 else median(sale["sale_price"] for sale in sales_30)
        price_30 = median(sale["sale_price"] for sale in sales_30)
        price_90 = median(sale["sale_price"] for sale in sales_90)
        recent_median = median(sale["sale_price"] for sale in sales_14) if sales_14 else price_30
        momentum = (price_7 - price_30) / price_30 if price_30 else 0.0
        sales_volume = float(len(sales_30))
        sales_velocity = sales_volume / 30.0
        volatility = _coefficient_of_variation([sale["sale_price"] for sale in sales_90])
        active_listings = float(sum(1 for listing in listings if listing["is_active"] and listing["listing_date"] <= as_of))
        listing_to_sales_ratio = active_listings / sales_volume if sales_volume else 0.0
        historical_trend = _normalized_slope(sales_90)

        return {
            "card_id": float(card_id),
            "current_price": float(price_30),
            "recent_median_price": float(recent_median),
            "price_7d": float(price_7),
            "price_30d": float(price_30),
            "price_90d": float(price_90),
            "price_momentum": float(momentum),
            "sales_velocity": float(sales_velocity),
            "sales_volume": float(sales_volume),
            "price_volatility": float(volatility),
            "active_listings": float(active_listings),
            "listing_to_sales_ratio": float(listing_to_sales_ratio),
            "historical_price_trend": float(historical_trend),
        }

    def _window_sales(
        self,
        sales: Sequence[Mapping[str, float | datetime]],
        as_of: datetime,
        *,
        days: int,
    ) -> list[Mapping[str, float | datetime]]:
        start = as_of - timedelta(days=days)
        return [sale for sale in sales if start <= sale["date"] <= as_of]

    def _compute_targets(
        self,
        *,
        as_of: datetime,
        current_price: float,
        sales: Sequence[Mapping[str, float | datetime]],
        horizons: Sequence[int],
    ) -> dict[int, float]:
        targets: dict[int, float] = {}
        for horizon in horizons:
            future_window = [sale["sale_price"] for sale in sales if as_of < sale["date"] <= as_of + timedelta(days=horizon)]
            if not future_window or current_price <= 0:
                continue
            future_median = float(median(future_window))
            targets[horizon] = ((future_median - current_price) / current_price) * 100.0
        return targets


class BaselineMomentumModel:
    def predict(self, features: Mapping[str, float], *, horizon: int) -> float:
        momentum_pct = float(features["price_momentum"]) * 100.0
        trend_pct = float(features["historical_price_trend"]) * 100.0
        horizon_scale = horizon / 30.0
        return (0.75 * momentum_pct + 0.25 * trend_pct) * horizon_scale


class CardSignalPredictionEngine:
    def __init__(self, *, model_version: str, stable_band_pct: float = 2.0) -> None:
        self.model_version = model_version
        self.stable_band_pct = stable_band_pct
        self.feature_pipeline = MarketFeaturePipeline()
        self.baseline_model = BaselineMomentumModel()
        self._models: dict[int, XGBRegressor] = {}

    @property
    def trained(self) -> bool:
        return len(self._models) == len(_HORIZONS)

    def train(
        self,
        *,
        sales: Sequence[Mapping[str, Any]],
        listings: Sequence[Mapping[str, Any]],
    ) -> tuple[DatasetSplit, ModelPerformance]:
        vectors = self.feature_pipeline.build_feature_vectors(sales=sales, listings=listings, horizons=_HORIZONS)
        split = self.feature_pipeline.split_by_time(vectors)
        if not split.train or not split.validation or not split.test:
            raise ValueError("Insufficient data for time-based train/validation/test splits.")

        for horizon in _HORIZONS:
            model = XGBRegressor(
                objective="reg:squarederror",
                n_estimators=120,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
            x_train, y_train = self._matrix(split.train, horizon=horizon)
            x_val, y_val = self._matrix(split.validation, horizon=horizon)
            model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
            self._models[horizon] = model

        performance = self.evaluate(split.test)
        return split, performance

    def evaluate(self, test_vectors: Sequence[FeatureVector]) -> ModelPerformance:
        if not self.trained:
            raise ValueError("Model must be trained before evaluation.")
        xgb_metrics: dict[int, RegressionMetrics] = {}
        baseline_metrics: dict[int, RegressionMetrics] = {}
        feature_matrix = self._features_matrix(test_vectors)
        for horizon in _HORIZONS:
            y_true = np.array([vector.targets[horizon] for vector in test_vectors], dtype=np.float64)
            y_pred_xgb = self._models[horizon].predict(feature_matrix)
            y_pred_baseline = np.array(
                [self.baseline_model.predict(vector.values, horizon=horizon) for vector in test_vectors],
                dtype=np.float64,
            )
            xgb_metrics[horizon] = _regression_metrics(y_true, y_pred_xgb, stable_band_pct=self.stable_band_pct)
            baseline_metrics[horizon] = _regression_metrics(y_true, y_pred_baseline, stable_band_pct=self.stable_band_pct)
        return ModelPerformance(xgboost=xgb_metrics, baseline=baseline_metrics)

    def predict_from_features(self, features: Mapping[str, float]) -> PredictionOutput:
        if not self.trained:
            raise ValueError("Model must be trained before predictions can be generated.")
        vector = np.array([[features[name] for name in self.feature_pipeline.FEATURE_NAMES]], dtype=np.float64)
        changes = {horizon: float(self._models[horizon].predict(vector)[0]) for horizon in _HORIZONS}
        direction = _to_direction(changes[30], stable_band_pct=self.stable_band_pct)
        confidence = self._confidence(features=features, predicted_changes=changes)
        return PredictionOutput(
            direction=direction.upper(),
            predicted_change_7d=round(changes[7], 2),
            predicted_change_30d=round(changes[30], 2),
            predicted_change_90d=round(changes[90], 2),
            confidence=round(confidence, 4),
            model_version=self.model_version,
        )

    def save(self, directory: Path | str) -> None:
        if not self.trained:
            raise ValueError("Cannot persist an untrained model.")
        model_dir = Path(directory)
        model_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "model_version": self.model_version,
            "feature_names": self.feature_pipeline.FEATURE_NAMES,
            "stable_band_pct": self.stable_band_pct,
            "horizons": list(_HORIZONS),
            "saved_at": datetime.now(UTC).isoformat(),
        }
        for horizon, model in self._models.items():
            model.save_model(str(model_dir / f"xgb_{horizon}d.json"))
        (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path | str) -> CardSignalPredictionEngine:
        model_dir = Path(directory)
        metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
        engine = cls(
            model_version=str(metadata["model_version"]),
            stable_band_pct=float(metadata.get("stable_band_pct", 2.0)),
        )
        for horizon in metadata["horizons"]:
            model = XGBRegressor(objective="reg:squarederror")
            model.load_model(str(model_dir / f"xgb_{horizon}d.json"))
            engine._models[int(horizon)] = model
        return engine

    def _matrix(self, vectors: Sequence[FeatureVector], *, horizon: int) -> tuple[np.ndarray, np.ndarray]:
        x = self._features_matrix(vectors)
        y = np.array([vector.targets[horizon] for vector in vectors], dtype=np.float64)
        return x, y

    def _features_matrix(self, vectors: Sequence[FeatureVector]) -> np.ndarray:
        return np.array(
            [[vector.values[name] for name in self.feature_pipeline.FEATURE_NAMES] for vector in vectors],
            dtype=np.float64,
        )

    def _confidence(self, *, features: Mapping[str, float], predicted_changes: Mapping[int, float]) -> float:
        volatility_penalty = min(0.45, max(0.0, float(features["price_volatility"])) * 2.5)
        trend_signal = min(0.35, abs(float(features["historical_price_trend"])) * 4.0)
        direction_votes = [
            _to_direction(predicted_changes[7], stable_band_pct=self.stable_band_pct),
            _to_direction(predicted_changes[30], stable_band_pct=self.stable_band_pct),
            _to_direction(predicted_changes[90], stable_band_pct=self.stable_band_pct),
        ]
        agreement = max(direction_votes.count("up"), direction_votes.count("down"), direction_votes.count("stable")) / 3.0
        return max(0.0, min(1.0, 0.55 + trend_signal + (agreement * 0.25) - volatility_penalty))


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray, *, stable_band_pct: float) -> RegressionMetrics:
    errors = y_true - y_pred
    mae = float(np.mean(np.abs(errors)))
    rmse = float(sqrt(float(np.mean(np.square(errors)))))
    non_zero_mask = np.abs(y_true) > 1e-8
    mape = float(np.mean(np.abs(errors[non_zero_mask] / y_true[non_zero_mask])) * 100.0) if np.any(non_zero_mask) else 0.0
    true_direction = [_to_direction(value, stable_band_pct=stable_band_pct) for value in y_true]
    pred_direction = [_to_direction(value, stable_band_pct=stable_band_pct) for value in y_pred]
    directional_accuracy = float(sum(t == p for t, p in zip(true_direction, pred_direction, strict=True)) / len(y_true))
    return RegressionMetrics(mae=mae, rmse=rmse, mape=mape, directional_accuracy=directional_accuracy)


def _to_direction(value: float, *, stable_band_pct: float) -> PredictionDirection:
    if value > stable_band_pct:
        return "up"
    if value < -stable_band_pct:
        return "down"
    return "stable"


def _coefficient_of_variation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = float(sum(values) / len(values))
    if mean_value == 0:
        return 0.0
    return float(np.std(np.array(values, dtype=np.float64), ddof=0) / mean_value)


def _normalized_slope(sales: Sequence[Mapping[str, float | datetime]]) -> float:
    if len(sales) < 2:
        return 0.0
    start = sales[0]["date"]
    x_values = np.array([(sale["date"] - start).total_seconds() / 86400.0 for sale in sales], dtype=np.float64)
    y_values = np.array([float(sale["sale_price"]) for sale in sales], dtype=np.float64)
    if np.allclose(x_values.var(), 0.0):
        return 0.0
    slope = float(np.cov(x_values, y_values, ddof=0)[0, 1] / np.var(x_values))
    mean_price = float(np.mean(y_values))
    if mean_price == 0:
        return 0.0
    return slope / mean_price


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "PredictorMetadata",
    "FeatureVector",
    "DatasetSplit",
    "RegressionMetrics",
    "ModelPerformance",
    "PredictionOutput",
    "MarketFeaturePipeline",
    "BaselineMomentumModel",
    "CardSignalPredictionEngine",
    "get_predictor_metadata",
]
