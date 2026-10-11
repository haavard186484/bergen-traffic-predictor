"""Inference helpers for the frozen one-hour-ahead traffic model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import MODEL_VERSION, MODELS_DIR, TIMEZONE
from src.features.build_features import TRAFFIC_LAGS, create_features, feature_columns

MODEL_ARTIFACT_PATH = MODELS_DIR / "traffic_hgb_v2.joblib"
CALENDAR_COLUMNS = feature_columns(calendar_event_features=True)


class PredictionInputError(ValueError):
    """Raised when an operational forecast cannot be constructed safely."""


@dataclass(frozen=True)
class FrozenModel:
    """The locally generated model and its validated feature contract."""

    model: object
    feature_columns: tuple[str, ...]
    version: str


def forecast_timestamp(value: datetime | pd.Timestamp) -> pd.Timestamp:
    """Interpret a naive UI timestamp as local Bergen time."""
    timestamp = pd.Timestamp(value)
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise PredictionInputError(
            "Forecast-tidspunktet må være på hel time, fordi trafikkdataene er timesaggregater."
        )
    if timestamp.tzinfo is None:
        try:
            return timestamp.tz_localize(TIMEZONE, ambiguous="raise", nonexistent="raise")
        except ValueError as error:
            raise PredictionInputError(
                "Tidspunktet er tvetydig eller finnes ikke ved overgang til/fra sommertid. "
                "Velg en annen lokal time."
            ) from error
    return timestamp.tz_convert(TIMEZONE)


def load_frozen_model(path: Path = MODEL_ARTIFACT_PATH) -> FrozenModel:
    """Load and validate the local artefact made by the final evaluation script."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Modellartefakt mangler: {path}. Kjør python -m scripts.run_final_model_evaluation først."
        )
    payload = joblib.load(path)
    if not isinstance(payload, dict):
        raise PredictionInputError("Modellartefakten har ugyldig format.")
    metadata = payload.get("metadata")
    columns = payload.get("feature_columns")
    if not isinstance(metadata, dict) or not isinstance(columns, (list, tuple)) or "model" not in payload:
        raise PredictionInputError("Modellartefakten mangler modell eller feature-metadata.")
    if metadata.get("model_version") != MODEL_VERSION:
        raise PredictionInputError("Modellartefakten har en annen modellversjon enn den frosne appen.")
    feature_columns = tuple(columns)
    if feature_columns != CALENDAR_COLUMNS:
        raise PredictionInputError("Modellartefakten har en uventet featureliste.")
    return FrozenModel(payload["model"], feature_columns, MODEL_VERSION)


def build_prediction_features(
    timestamp: datetime | pd.Timestamp, traffic_history: Mapping[int, float | None]
) -> pd.DataFrame:
    """Build the frozen feature row using the shared training feature code.

    ``traffic_history`` is keyed by hours before the forecast timestamp. Exact
    timestamps are deliberately used, so incomplete history cannot be shifted
    over a data gap.
    """
    local_timestamp = forecast_timestamp(timestamp)
    missing_lags = [lag for lag in TRAFFIC_LAGS if traffic_history.get(lag) is None]
    if missing_lags:
        formatted = ", ".join(f"t−{lag}" for lag in missing_lags)
        raise PredictionInputError(
            f"Mangler nødvendig trafikkhistorikk: {formatted} timer. "
            "Hvis tidspunktet er nylig eller fremtidig, velg en tidligere time; "
            "Traffic Data API publiserer ferdig aggregerte timedata med forsinkelse."
        )

    values: dict[int, float] = {}
    for lag in TRAFFIC_LAGS:
        value = traffic_history[lag]
        if not isinstance(value, (int, float)) or not np.isfinite(value):
            raise PredictionInputError(f"Trafikkverdien ved t−{lag} må være et endelig tall.")
        values[lag] = float(value)

    rows = [{"timestamp": local_timestamp.tz_convert("UTC"), "traffic_volume": np.nan}]
    rows.extend(
        {
            "timestamp": (local_timestamp - pd.Timedelta(hours=lag)).tz_convert("UTC"),
            "traffic_volume": values[lag],
        }
        for lag in TRAFFIC_LAGS
    )
    features = create_features(pd.DataFrame(rows), calendar_event_features=True)
    row = features.loc[features["timestamp"] == local_timestamp.tz_convert("UTC")]
    if len(row) != 1 or row.loc[:, list(CALENDAR_COLUMNS)].isna().any(axis=None):
        raise PredictionInputError("Kunne ikke bygge en komplett feature-rad fra trafikkhistorikken.")
    return row.loc[:, list(CALENDAR_COLUMNS)]


def predict_one_hour_ahead(
    frozen_model: FrozenModel,
    timestamp: datetime | pd.Timestamp,
    traffic_history: Mapping[int, float | None],
) -> float:
    """Predict traffic for one hour after ``timestamp``."""
    features = build_prediction_features(timestamp, traffic_history)
    return float(frozen_model.model.predict(features.loc[:, list(frozen_model.feature_columns)])[0])
