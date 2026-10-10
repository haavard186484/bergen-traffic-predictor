"""Generate the 2024 diagnostic error analysis for the selected traffic HGB."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.run_initial_ml_model import _markdown_table
from src.data.build_dataset import build_hourly_dataset
from src.evaluation.weather_error_analysis import (
    calendar_error_summaries,
    daily_error_summary,
    validation_error_data,
    weather_error_summaries,
    weather_model_condition_summary,
)


def build_report(data: pd.DataFrame) -> str:
    """Build a diagnostic report without using 2025 data."""
    errors = validation_error_data(data)
    calendar = calendar_error_summaries(errors)
    weather = weather_error_summaries(errors)
    daily = daily_error_summary(errors).head(10)
    weather_model = weather_model_condition_summary(data)
    weather_rows = errors[errors[["temperature_c_t_minus_1", "precipitation_mm_t_minus_1", "wind_speed_m_s_t_minus_1"]].notna().all(axis=1)]
    return "\n".join(
        [
            "# Feilanalyse: trafikk-HGB, validering 2024",
            "",
            "Generert med `python -m scripts.run_model_evaluation`. Dette er en diagnostisk analyse av 2024-valideringen; 2025-testen brukes ikke.",
            "",
            "## Oppsett og avgrensning",
            "",
            "Den valgte trafikk-HGB-en trenes på 2022–2023 og predikerer trafikk ved `t + 1` fra features ved `t`. Kalendergruppene nedenfor er basert på predikert tidspunkt i `Europe/Oslo`. Alle 8 231 gyldige trafikk-forecast-rader i 2024 beholdes i kalenderanalysen.",
            "",
            "Værgruppene bruker eksakt observert Frost-vær fra SN50540 ved `t − 1` (to timer før forecast-målet) kun som etterfølgende diagnose. Været er ikke input til den valgte modellen. Manglende Frost-observasjoner fylles ikke: hver værtabell ekskluderer bare rader som mangler gruppens aktuelle værverdi. Rader med alle tre `t − 1`-verdier observert: " + str(len(weather_rows)) + ".",
            "",
            "## Feil per time",
            "",
            _markdown_table(calendar["hour"]),
            "",
            "## Feil per ukedag",
            "",
            _markdown_table(calendar["weekday"]),
            "",
            "## Feil per måned",
            "",
            _markdown_table(calendar["month"]),
            "",
            "## Feil ved regn og ikke-regn",
            "",
            _markdown_table(weather["rain"]),
            "",
            "## Feil per vindstyrke ved t − 1",
            "",
            "Intervaller: under 4 m/s, 4 til under 8 m/s og minst 8 m/s.",
            "",
            _markdown_table(weather["wind_band"]),
            "",
            "## Feil per temperaturintervall ved t − 1",
            "",
            "Intervaller: under 0 °C, 0 til under 5 °C, 5 til under 10 °C og minst 10 °C.",
            "",
            _markdown_table(weather["temperature_band"]),
            "",
            "## Enkeltdager med størst feil",
            "",
            "Tabellen viser de ti lokale datoene med høyest MAE blant datoer med minst 20 gyldige forecasts. Positiv `mean_signed_error` betyr at modellen i gjennomsnitt overpredikerte den dagen.",
            "",
            _markdown_table(daily),
            "",
            "De høyeste dagene sammenfaller i stor grad med norske helligdager eller høytidsdager: nyttårsaften/-dagen, påske (1. april), 1. mai, Kristi himmelfartsdag (9. mai), 17. mai og julaften. Det peker på kalender- og hendelseseffekter som dagens features ikke representerer. 27. mars og 8. januar har også høye feil, men prosjektet har ikke hendelsesdata som kan bekrefte en årsak; tabellen må derfor ikke tolkes som kausal dokumentasjon.",
            "",
            "## Kan vær være nyttig i bestemte situasjoner?",
            "",
            "Den allerede avviste vær-HGB-en sammenlignes her med trafikk-HGB på samme 2024-rader, delt etter regn, vind og temperatur ved `t − 1`. Positiv `weather_minus_traffic_mae` betyr at vær-HGB er dårligere. Dette er eksplorativ undergruppeanalyse, ikke grunnlag for nytt modellvalg; 2024 er allerede brukt til valg, og 2025 forblir urørt.",
            "",
            _markdown_table(weather_model),
            "",
            "Konklusjon: Vær kan forklare variasjon i feilnivået i enkelte værgrupper, men de tre rå, konservative Frost-lagene har ikke vist en robust samlet forbedring. Det finnes derfor ikke grunnlag for å endre valgt modell. Eventuelle nye væravledninger må velges med tidsseriekryssvalidering innen 2022–2023 før én endelig 2024-evaluering; bruk heller ikke 2025 til featurevalg.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traffic", type=Path, default=Path("data/processed/traffic_hourly.csv"))
    parser.add_argument("--weather", type=Path, default=Path("data/processed/weather_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/model-evaluation.md"))
    args = parser.parse_args()
    data = build_hourly_dataset(pd.read_csv(args.traffic), pd.read_csv(args.weather))
    args.output.write_text(build_report(data), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
