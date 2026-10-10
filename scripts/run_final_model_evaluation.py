"""Freeze candidate selection, run final 2025 evaluation, and save the model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from scripts.run_initial_ml_model import _markdown_table
from src.data.build_dataset import build_hourly_dataset
from src.evaluation.final_model_evaluation import (
    MODEL_VERSION,
    chronological_cross_validation,
    evaluate_period,
    select_by_cross_validation,
    train_final_model,
)


def build_report(data: pd.DataFrame) -> tuple[str, dict[str, object]]:
    """Select only from CV, then report diagnostic 2024 and final 2025 metrics."""
    cross_validation = chronological_cross_validation(data)
    means = cross_validation.groupby(level="model")[["mae", "rmse"]].mean().rename(
        columns={"mae": "mean_mae", "rmse": "mean_rmse"}
    )
    selected = select_by_cross_validation(cross_validation)
    diagnostic_2024 = evaluate_period(data, selected, "2024-01-01", "2024-01-01", "2025-01-01")
    final_2025 = evaluate_period(data, selected, "2025-01-01", "2025-01-01", "2026-01-01")
    metadata: dict[str, object] = {
        "model_version": MODEL_VERSION,
        "selected_candidate": selected.name,
        "feature_columns": list(selected.columns),
        "weather_transformer": "SeasonalWeatherAnomaly" if selected.use_weather_derivatives else None,
        "selection_period": "expanding CV folds in 2022-2023",
        "diagnostic_period": "2024",
        "final_test_period": "2025",
    }
    report = "\n".join(
        [
            "# Endelig modellvalg: kalender og avledet vær",
            "",
            "Generert med `python -m scripts.run_final_model_evaluation`.",
            "",
            "## Forhåndsdefinerte kandidater",
            "",
            "Begge kandidatene bruker trafikk-HGB og deterministiske norske kalenderfeatures. Værkandidaten legger i tillegg til 6-/24-timers akkumulert nedbør, regnstart, regn i rush-time og sesongjustert temperatur- og vindavvik. Værverdier slutter ved eksakt `t - 1`; manglende observasjoner fylles ikke. HGB behandler manglende værfeatures eksplisitt, mens manglende trafikkhistorikk fortsatt gjør forecast-raden ugyldig.",
            "",
            "Sesongnormalene estimeres per lokal måned og time bare fra hver folds treningsperiode. De kan dermed ikke inneholde validerings- eller testvær.",
            "",
            "## Modellvalg: ekspanderende CV i 2022–2023",
            "",
            _markdown_table(cross_validation),
            "",
            "## Gjennomsnitt over CV-folds",
            "",
            _markdown_table(means),
            "",
            f"Frosset kandidat valgt kun på CV-MAE: **{selected.name}**.",
            "",
            "## Diagnostisk 2024-resultat",
            "",
            "2024 var brukt i tidligere eksperimenter og er ikke et uavhengig utvalg for dette arbeidet. Resultatet rapporteres derfor bare som diagnose og har ikke påvirket valget.",
            "",
            _markdown_table(diagnostic_2024),
            "",
            "## Endelig 2025-test",
            "",
            "Dette er én fast sluttevaluering av den CV-frosne kandidaten. Resultatet skal ikke brukes til videre feature- eller modellvalg.",
            "",
            _markdown_table(final_2025),
            "",
            "## Frosset modellkonfigurasjon",
            "",
            f"Modellversjon: `{MODEL_VERSION}`. Featurelisten og eventuell sesongtransform lagres sammen med den lokale, ignorerte modellartefakten i `models/`.",
            "",
            "Konklusjon: Den avledede værpakken ble forkastet fordi den tapte alle tre CV-folds mot kalender-HGB. Den endelige, frosne modellen bruker derfor trafikkhistorikk, kalenderfeatures og ingen Frost-features. Videre værfeaturevalg er avsluttet; 2025-resultatet brukes bare som sluttevaluering.",
            "",
        ]
    )
    return report, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traffic", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--weather", type=Path, default=Path("data/processed/weather_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/final-model-evaluation.md"))
    parser.add_argument("--model-output", type=Path, default=Path("models/traffic_hgb_v2.joblib"))
    args = parser.parse_args()
    data = build_hourly_dataset(pd.read_csv(args.traffic), pd.read_csv(args.weather))
    report, metadata = build_report(data)
    selected_name = str(metadata["selected_candidate"])
    from src.evaluation.final_model_evaluation import CANDIDATES

    selected = next(candidate for candidate in CANDIDATES if candidate.name == selected_name)
    model, transformer, training_rows = train_final_model(data, selected)
    metadata["training_period"] = "2022-2024"
    metadata["training_rows"] = training_rows
    args.output.write_text(report, encoding="utf-8")
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": selected.columns, "transformer": transformer, "metadata": metadata}, args.model_output)
    args.model_output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output} and {args.model_output}")


if __name__ == "__main__":
    main()
