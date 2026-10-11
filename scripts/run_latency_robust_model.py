"""Select, freeze, and evaluate the latency-robust traffic HGB model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from scripts.run_initial_ml_model import _markdown_table
from src.evaluation.latency_robust_model_evaluation import (
    CANDIDATES,
    FINAL_EVALUATION_END,
    FINAL_EVALUATION_START,
    FINAL_TRAIN_END,
    MODEL_VERSION,
    chronological_cross_validation,
    final_evaluation,
    select_by_cross_validation,
    train_final_model,
)


def build_report(data: pd.DataFrame) -> tuple[str, dict[str, object]]:
    """Produce the fixed-CV selection and the one-time 2026 H1 report."""
    cv_results = chronological_cross_validation(data)
    means = (
        cv_results.groupby(level="model")[["mae", "rmse"]]
        .mean()
        .rename(columns={"mae": "mean_mae", "rmse": "mean_rmse"})
    )
    selected = select_by_cross_validation(cv_results)
    final_metrics, hourly, weekday = final_evaluation(data, selected)
    metadata: dict[str, object] = {
        "model_version": MODEL_VERSION,
        "selected_candidate": selected.name,
        "feature_columns": list(selected.columns),
        "traffic_lags": list(selected.traffic_lags),
        "selection_period": "expanding CV folds in 2022-2023",
        "training_period": "2022-2025 after candidate freeze",
        "final_test_period": "2026-01-01 to 2026-07-01 Europe/Oslo",
        "traffic_source": "Statens vegvesen Traffic Data API",
    }
    report = "\n".join(
        [
            "# Latensrobust modellvalg",
            "",
            "Generert med `python -m scripts.run_latency_robust_model`.",
            "",
            "## Forhåndsdefinerte kandidater",
            "",
            "Alle kandidatene bruker `HistGradientBoostingRegressor`, deterministiske norske kalenderfeatures i `Europe/Oslo` og kun Statens vegvesens eksisterende timeserie. Kandidatlisten ble frosset før CV-resultatene ble inspisert: `(t−24, t−168)`, `(t−24, t−48, t−168)` og `(t−24, t−168, t−336)`. Ingen bruker `t−1`, `t−2`, vær eller andre datakilder. Eksakte timestamp-oppslag gjør at målegap fortsatt gir en ugyldig forecast-rad fremfor å forskyve data.",
            "",
            "## Modellvalg: ekspanderende CV i 2022–2023",
            "",
            _markdown_table(cv_results),
            "",
            "## Gjennomsnitt over CV-folds",
            "",
            _markdown_table(means),
            "",
            f"Kandidaten ble fryst kun på gjennomsnittlig CV-MAE: **{selected.name}**.",
            "",
            "2025 var låst fra forrige sluttevaluering og ble ikke brukt til kandidat-, feature- eller modellvalg. Etter frysing ble modellen trent på 2022–2025.",
            "",
            "## Én sluttevaluering: 2026 H1",
            "",
            f"Den nye, tidligere ubrukte perioden er {FINAL_EVALUATION_START} til {FINAL_EVALUATION_END} i `Europe/Oslo`. Modell og forrige-uke-baseline scores på nøyaktig de samme forecast-radene.",
            "",
            _markdown_table(final_metrics),
            "",
            "## Feilanalyse etter forecast-time",
            "",
            _markdown_table(hourly),
            "",
            "## Feilanalyse etter forecast-ukedag",
            "",
            _markdown_table(weekday),
            "",
            "## Frosset modellkonfigurasjon",
            "",
            f"Modellversjon: `{MODEL_VERSION}`. Den frosne HGB-modellen og metadata lagres lokalt, ignorert av Git, i `models/`. Treningsperioden slutter før sluttevalueringen ({FINAL_TRAIN_END}); 2026-resultatet brukes ikke videre til tuning.",
            "",
        ]
    )
    return report, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traffic", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument(
        "--output", type=Path, default=Path("docs/latency-robust-model-evaluation.md")
    )
    parser.add_argument(
        "--model-output", type=Path, default=Path("models/traffic_hgb_latency_robust_v1.joblib")
    )
    args = parser.parse_args()
    data = pd.read_csv(args.traffic)
    report, metadata = build_report(data)
    selected = next(
        candidate for candidate in CANDIDATES if candidate.name == metadata["selected_candidate"]
    )
    model, training_rows = train_final_model(data, selected)
    metadata["training_rows"] = training_rows
    args.output.write_text(report, encoding="utf-8")
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_columns": selected.columns, "metadata": metadata},
        args.model_output,
    )
    args.model_output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output} and {args.model_output}")


if __name__ == "__main__":
    main()
