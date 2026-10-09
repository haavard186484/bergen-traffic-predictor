"""Train, select and evaluate leakage-safe one-hour-ahead traffic models."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.evaluation.model_evaluation import complete_model_rows, error_summary, evaluate_predictions
from src.evaluation.traffic_eda import assign_chronological_split, prepare_traffic_for_eda
from src.features.build_features import FEATURE_COLUMNS, create_features
from src.models.baselines import previous_week_forecast_baseline
from src.models.train import train_model


def _markdown_table(data: pd.DataFrame) -> str:
    table = data.reset_index()
    headers = [str(column) if str(column) else "index" for column in table.columns]
    rows = []
    for row in table.itertuples(index=False, name=None):
        rows.append([f"{value:.2f}" if isinstance(value, float) else str(value) for value in row])
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in rows),
        ]
    )


def _predict(model_data: pd.DataFrame, model_name: str, train_data: pd.DataFrame) -> pd.Series:
    model = train_model(train_data, FEATURE_COLUMNS, model_name)
    prediction = pd.Series(model.predict(model_data[list(FEATURE_COLUMNS)]), index=model_data.index)
    return prediction.rename(model_name)


def run_experiment(data: pd.DataFrame) -> tuple[pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Select by validation MAE, then evaluate the selected setup once on test."""
    prepared = prepare_traffic_for_eda(data)
    features = create_features(prepared)
    # The split belongs to the prediction target at t + 1, not to the
    # feature timestamp at t. This preserves the stated calendar periods.
    target_times = prepared.copy()
    target_times["local_timestamp"] = target_times["local_timestamp"] + pd.Timedelta(hours=1)
    features["split"] = assign_chronological_split(target_times)
    model_rows = complete_model_rows(features, FEATURE_COLUMNS)
    raw_baseline = previous_week_forecast_baseline(prepared)
    baseline = raw_baseline.reindex(model_rows.index)
    train_rows = model_rows.loc[model_rows["split"].eq("train")]
    validation_rows = model_rows.loc[model_rows["split"].eq("validation")]
    test_rows = model_rows.loc[model_rows["split"].eq("test")]

    validation_results = []
    for model_name in ("linear_regression", "hist_gradient_boosting"):
        prediction = _predict(validation_rows, model_name, train_rows)
        validation_results.append({"model": model_name, **evaluate_predictions(validation_rows["target_traffic"], prediction)})
    validation_results.append(
        {"model": "previous_week_baseline", **evaluate_predictions(validation_rows["target_traffic"], baseline.loc[validation_rows.index])}
    )
    validation = pd.DataFrame(validation_results).set_index("model").sort_values("mae")
    selected = validation.index[0]
    if selected == "previous_week_baseline":
        raise RuntimeError("The baseline won validation; no ML model was selected")

    selected_prediction = _predict(test_rows, selected, pd.concat([train_rows, validation_rows]))
    test_results = pd.DataFrame(
        [
            {"model": selected, **evaluate_predictions(test_rows["target_traffic"], selected_prediction)},
            {"model": "previous_week_baseline", **evaluate_predictions(test_rows["target_traffic"], baseline.loc[test_rows.index])},
        ]
    ).set_index("model")
    hourly_errors = error_summary(test_rows, test_rows["target_traffic"], selected_prediction, "hour")
    weekday_errors = error_summary(test_rows, test_rows["target_traffic"], selected_prediction, "weekday")
    return validation, selected, test_results, hourly_errors, weekday_errors


def build_report(data: pd.DataFrame) -> str:
    validation, selected, test_results, hourly_errors, weekday_errors = run_experiment(data)
    return "\n".join(
        [
            "# Første lekkasjesikre ML-modell",
            "",
            "Generert med `python -m scripts.run_initial_ml_model` fra lokalt trafikkdatasett.",
            "",
            "## Oppsett",
            "",
            (
                "Hver rad er for tidspunkt `t` (UTC i datafilen, kalenderfeatures i `Europe/Oslo`). "
                "Målet er observert trafikk ved `t + 1 time`. Features er time, ukedag, måned, helg, "
                "syklisk time og eksakte trafikklag ved `t - 1`, `t - 2`, `t - 24` og `t - 168` timer. "
                "Oppslag skjer på timestamp, ikke radposisjon; alle rader med manglende feature eller mål "
                "utelates uten imputering."
            ),
            "",
            (
                "Splitten gjelder predikert tidspunkt (`t + 1`): trening er 2022–2023, validering 2024 "
                "og test 2025. Lineær regresjon og "
                "`HistGradientBoostingRegressor` ble sammenlignet på validerings-MAE. Test ble først brukt etter "
                "valget; den valgte modellen er deretter trent på trening + validering."
            ),
            "",
            "## Validering",
            "",
            _markdown_table(validation),
            "",
            f"Valgt modell: **{selected}** (lavest MAE på validering).",
            "",
            "## Endelig test mot forrige-uke-baseline",
            "",
            _markdown_table(test_results),
            "",
            "## Feilanalyse på test: valgt modell per time",
            "",
            _markdown_table(hourly_errors),
            "",
            "## Feilanalyse på test: valgt modell per ukedag",
            "",
            _markdown_table(weekday_errors),
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/initial-ml-model.md"))
    args = parser.parse_args()
    report = build_report(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
