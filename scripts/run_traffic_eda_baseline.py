"""Create a Markdown EDA and previous-week-baseline report from local traffic data."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import regression_metrics
from src.evaluation.traffic_eda import (
    CHRONOLOGICAL_SPLITS,
    assign_chronological_split,
    grouped_volume_summary,
    missing_value_gaps,
    prepare_traffic_for_eda,
    traffic_quality_summary,
)
from src.models.baselines import previous_week_baseline


def _markdown_table(data: pd.DataFrame) -> str:
    """Render a small DataFrame without pandas' optional ``tabulate`` package."""
    table = data.reset_index()
    headers = [str(column) if str(column) else "index" for column in table.columns]

    def format_value(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value).replace("|", "\\|")

    rows = [[format_value(value) for value in row] for row in table.itertuples(index=False, name=None)]
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def build_report(data: pd.DataFrame) -> str:
    """Build a deterministic Markdown report from an hourly traffic dataset."""
    prepared = prepare_traffic_for_eda(data)
    prepared["split"] = assign_chronological_split(prepared)
    prediction = previous_week_baseline(prepared)
    quality = traffic_quality_summary(prepared)
    gaps = missing_value_gaps(prepared)
    hourly = grouped_volume_summary(prepared, "hour")
    weekday = grouped_volume_summary(prepared, "weekday")
    month = grouped_volume_summary(prepared, "month")
    weekend = grouped_volume_summary(prepared, "is_weekend")

    monthly = (
        prepared.set_index("local_timestamp")["traffic_volume"]
        .resample("MS")
        .agg(observations="count", mean="mean", median="median", minimum="min", maximum="max")
        .round(2)
    )
    split_rows = []
    for split in CHRONOLOGICAL_SPLITS:
        selection = prepared["split"].eq(split.name)
        actual = prepared.loc[selection, "traffic_volume"]
        predicted = prediction.loc[selection]
        metrics = regression_metrics(actual, predicted)
        split_rows.append(
            {
                "split": split.name,
                "start_local": split.start,
                "end_local_exclusive": split.end,
                "hours": int(selection.sum()),
                "observed_targets": int(actual.notna().sum()),
                "evaluated_predictions": int((actual.notna() & predicted.notna()).sum()),
                "mae": round(metrics["mae"], 2),
                "rmse": round(metrics["rmse"], 2),
            }
        )
    evaluation = pd.DataFrame(split_rows).set_index("split")
    peak_hour = int(hourly["mean"].idxmax())
    quiet_hour = int(hourly["mean"].idxmin())
    busiest_month = str(month["mean"].idxmax())
    quietest_month = str(month["mean"].idxmin())
    weekday_mean = weekend.loc[False, "mean"]
    weekend_mean = weekend.loc[True, "mean"]
    weekend_reduction = (1 - weekend_mean / weekday_mean) * 100

    lines = [
        "# Trafikk-EDA og forrige-uke-baseline",
        "",
        (
            "Denne rapporten er generert med `python -m scripts.run_traffic_eda_baseline`. "
            "Tidspunkter og kalendergrupper er i `Europe/Oslo`; kildefilen lagrer UTC-tid."
        ),
        "",
        "## Datakvalitet og ekstremer",
        "",
        _markdown_table(pd.DataFrame([quality]).T.rename(columns={0: "value"})),
        "",
        (
            "Ekstreme verdier er definert som observasjoner utenfor 1,5 × IQR. Manglende "
            "trafikkverdier er målegap og er verken behandlet som null eller imputert."
        ),
        "",
        "## Datagap",
        "",
        _markdown_table(gaps) if not gaps.empty else "Ingen manglende trafikkverdier.",
        "",
        "## Nøkkelfunn",
        "",
        (
            f"- Det er {quality['missing_hours']} manglende av {quality['hours']} timer og "
            f"ingen nullverdier. IQR-regelen flagger {quality['iqr_extreme_hours']} ekstreme timer; "
            f"observert minimum/maksimum er {quality['minimum']:.0f}/{quality['maximum']:.0f} kjøretøy per time."
        ),
        (
            f"- Gjennomsnittet topper kl. {peak_hour:02d} ({hourly.loc[peak_hour, 'mean']:.0f}) "
            f"og er lavest kl. {quiet_hour:02d} ({hourly.loc[quiet_hour, 'mean']:.0f})."
        ),
        (
            f"- Helgegjennomsnittet er {weekend_mean:.0f}, {weekend_reduction:.1f} % lavere enn "
            f"hverdagssnittet på {weekday_mean:.0f} kjøretøy per time."
        ),
        (
            f"- {quietest_month} har lavest månedsmiddel ({month.loc[quietest_month, 'mean']:.0f}) "
            f"og {busiest_month} høyest ({month.loc[busiest_month, 'mean']:.0f})."
        ),
        "",
        "## Utvikling over tid (per lokal kalendermåned)",
        "",
        _markdown_table(monthly),
        "",
        "## Fordeling per time", "", _markdown_table(hourly),
        "", "## Fordeling per ukedag", "", _markdown_table(weekday),
        "", "## Fordeling per måned", "", _markdown_table(month),
        "", "## Fordeling: helg og hverdag", "", _markdown_table(weekend),
        "", "## Kronologisk split og baseline", "",
        (
            "Train er 2022--2023, validering er 2024 og test er 2025, avgrenset i lokal tid. "
            "Ingen modell eller terskel velges mot testperioden."
        ),
        "",
        (
            "Baselinen predikerer tidspunkt `t` med observert trafikk ved `t - 168 timer`. "
            "Oppslaget gjøres på eksakt tidsstempel, slik at manglende input eller mål gir "
            "manglende prediksjon i stedet for at et gap hoppes over."
        ),
        "",
        _markdown_table(evaluation),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/traffic-eda-baseline.md"))
    args = parser.parse_args()
    report = build_report(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
