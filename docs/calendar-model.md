# Kalenderfeatures: tidsserie-kryssvalidering

Generert med `python -m scripts.run_calendar_model` fra lokalt trafikkdatasett.

## Oppsett

Kandidaten legger til deterministiske norske kalenderindikatorer: offentlig helligdag, dag før/etter offentlig helligdag, jule-/nyttårsperiode og 17. mai. Datoene beregnes fra timezone-bevarte `Europe/Oslo`-tidspunkter; de er kjent ved forecast-tidspunktet og påvirker ikke manglende trafikkobservasjoner.

Modellvalg skjer kun på tre ekspanderende, kronologiske folds innen 2022–2023: validering i 2022 H2, 2023 H1 og 2023 H2. 2025 brukes ikke. 2024 hadde allerede vært brukt i tidligere eksperimenter og er dermed ikke et uavhengig testsett; den vises nedenfor kun som en bekreftende, etterfølgende evaluering av CV-valget.

## Kryssvalidering per fold

| model | fold | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- | --- |
| traffic_hgb | 2022_h2 | 4417 | 140.42 | 233.58 |
| traffic_hgb | 2023_h1 | 4343 | 118.89 | 178.02 |
| traffic_hgb | 2023_h2 | 4417 | 100.79 | 151.43 |
| traffic_hgb_with_calendar_events | 2022_h2 | 4417 | 143.81 | 240.90 |
| traffic_hgb_with_calendar_events | 2023_h1 | 4343 | 117.69 | 175.88 |
| traffic_hgb_with_calendar_events | 2023_h2 | 4417 | 97.58 | 143.11 |

## Gjennomsnitt over folds

| model | mean_mae | mean_rmse |
| --- | --- | --- |
| traffic_hgb | 120.03 | 187.68 |
| traffic_hgb_with_calendar_events | 119.69 | 186.63 |

Valgt kun fra 2022–2023-CV: **traffic_hgb_with_calendar_events**.

## Bekreftende 2024-evaluering av forhåndsvalgt variant

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| traffic_hgb_with_calendar_events | 8231 | 99.83 | 152.54 |

Kalenderkandidaten er foreløpig å foretrekke fordi den vant gjennomsnittlig MAE i 2022–2023-CV og forbedret den etterfølgende 2024-målingen. CV-forskjellen er liten, så featurelisten skal fryses og dokumenteres før en eventuell senere, én-gangs endelig evaluering på 2025. 2025 skal ikke brukes til ytterligere feature- eller modellvalg.
