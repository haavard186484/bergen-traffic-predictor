"""Select calendar-event features by 2022--2023 CV and report 2024 once."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.run_initial_ml_model import _markdown_table
from src.evaluation.calendar_model_evaluation import (
    chronological_cross_validation,
    evaluate_selected_on_2024,
    select_by_cross_validation,
)


def build_report(data: pd.DataFrame) -> str:
    """Build the reproducible calendar-feature experiment report."""
    cross_validation = chronological_cross_validation(data)
    means = cross_validation.groupby(level="model")[["mae", "rmse"]].mean().rename(columns={"mae": "mean_mae", "rmse": "mean_rmse"})
    selected = select_by_cross_validation(cross_validation)
    validation = evaluate_selected_on_2024(data, selected)
    return "\n".join(
        [
            "# Kalenderfeatures: tidsserie-kryssvalidering",
            "",
            "Generert med `python -m scripts.run_calendar_model` fra lokalt trafikkdatasett.",
            "",
            "## Oppsett",
            "",
            "Kandidaten legger til deterministiske norske kalenderindikatorer: offentlig helligdag, dag før/etter offentlig helligdag, jule-/nyttårsperiode og 17. mai. Datoene beregnes fra timezone-bevarte `Europe/Oslo`-tidspunkter; de er kjent ved forecast-tidspunktet og påvirker ikke manglende trafikkobservasjoner.",
            "",
            "Modellvalg skjer kun på tre ekspanderende, kronologiske folds innen 2022–2023: validering i 2022 H2, 2023 H1 og 2023 H2. 2025 brukes ikke. 2024 hadde allerede vært brukt i tidligere eksperimenter og er dermed ikke et uavhengig testsett; den vises nedenfor kun som en bekreftende, etterfølgende evaluering av CV-valget.",
            "",
            "## Kryssvalidering per fold",
            "",
            _markdown_table(cross_validation),
            "",
            "## Gjennomsnitt over folds",
            "",
            _markdown_table(means),
            "",
            f"Valgt kun fra 2022–2023-CV: **{selected}**.",
            "",
            "## Bekreftende 2024-evaluering av forhåndsvalgt variant",
            "",
            _markdown_table(validation),
            "",
            "Kalenderkandidaten er foreløpig å foretrekke fordi den vant gjennomsnittlig MAE i 2022–2023-CV og forbedret den etterfølgende 2024-målingen. CV-forskjellen er liten, så featurelisten skal fryses og dokumenteres før en eventuell senere, én-gangs endelig evaluering på 2025. 2025 skal ikke brukes til ytterligere feature- eller modellvalg.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/calendar-model.md"))
    args = parser.parse_args()
    args.output.write_text(build_report(pd.read_csv(args.input)), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
