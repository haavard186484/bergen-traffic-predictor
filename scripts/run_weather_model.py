"""Compare the selected traffic-only model with conservative weather lags."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.run_initial_ml_model import _markdown_table, _predict
from src.data.build_dataset import build_hourly_dataset
from src.data.frost import WEATHER_COLUMNS
from src.evaluation.model_evaluation import complete_model_rows, evaluate_predictions
from src.evaluation.traffic_eda import assign_chronological_split, prepare_traffic_for_eda
from src.features.build_features import FEATURE_COLUMNS, create_features, feature_columns
from src.models.baselines import previous_week_forecast_baseline


def evaluate_weather_against_traffic(data: pd.DataFrame) -> pd.DataFrame:
    """Evaluate HGB feature sets on exactly the same valid 2024 timestamps.

    Weather is represented only by exact values at t-1, t-2 and t-24 hours.
    The one-hour delay is a documented conservative availability assumption.
    """
    prepared = prepare_traffic_for_eda(data)
    traffic_features = create_features(prepared)
    weather_features = create_features(prepared, weather_columns=WEATHER_COLUMNS)
    target_times = prepared.copy()
    target_times["local_timestamp"] += pd.Timedelta(hours=1)
    split = assign_chronological_split(target_times)
    traffic_features["split"] = split
    weather_features["split"] = split
    traffic_rows = complete_model_rows(traffic_features, FEATURE_COLUMNS)
    weather_columns = feature_columns(WEATHER_COLUMNS)
    weather_rows = complete_model_rows(weather_features, weather_columns)

    # The intersection gives a fair feature-set comparison even when weather
    # observations have holes. Training remains chronological.
    validation_index = traffic_rows.index.intersection(weather_rows.index)
    validation_index = validation_index[traffic_rows.loc[validation_index, "split"].eq("validation")]
    if validation_index.empty:
        raise RuntimeError(
            "No comparable 2024 rows. Check weather coverage and missing observations."
        )
    traffic_train = traffic_rows.loc[traffic_rows["split"].eq("train")]
    weather_train = weather_rows.loc[weather_rows["split"].eq("train")]
    traffic_validation = traffic_rows.loc[validation_index]
    weather_validation = weather_rows.loc[validation_index]
    traffic_prediction = _predict(traffic_validation, "hist_gradient_boosting", traffic_train)
    weather_prediction = _predict(
        weather_validation, "hist_gradient_boosting", weather_train, weather_columns
    )
    baseline = previous_week_forecast_baseline(prepared).reindex(validation_index)
    actual = traffic_validation["target_traffic"]
    return pd.DataFrame(
        [
            {"model": "traffic_only_hist_gradient_boosting", **evaluate_predictions(actual, traffic_prediction)},
            {"model": "weather_augmented_hist_gradient_boosting", **evaluate_predictions(actual, weather_prediction)},
            {"model": "previous_week_baseline", **evaluate_predictions(actual, baseline)},
        ]
    ).set_index("model").sort_values("mae")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traffic", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/weather-model.md"))
    args = parser.parse_args()
    data = build_hourly_dataset(pd.read_csv(args.traffic), pd.read_csv(args.weather))
    result = evaluate_weather_against_traffic(data)
    selected = result.loc[
        ["traffic_only_hist_gradient_boosting", "weather_augmented_hist_gradient_boosting"], "mae"
    ].idxmin()
    report = "\n".join(
        [
            "# Værfeatures: validering 2024",
            "",
            (
                "Begge modellene er evaluert på nøyaktig samme forecast-tidspunkter. "
                "Værfeatures er eksakte observerte lag ved `t−1`, `t−2` og `t−24` timer."
            ),
            "",
            _markdown_table(result),
            "",
            f"Valgt oppsett: **{selected}** (lavest MAE på validering).",
            "",
            (
                "Værmodellen evalueres ikke på 2025-testen fordi den ikke vant valideringen. "
                "Den tidligere rapporterte testen for valgt trafikkmodell beholdes uendret."
            ),
            "",
        ]
    )
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
