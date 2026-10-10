# Endelig modellvalg: kalender og avledet vær

Generert med `python -m scripts.run_final_model_evaluation`.

## Forhåndsdefinerte kandidater

Begge kandidatene bruker trafikk-HGB og deterministiske norske kalenderfeatures. Værkandidaten legger i tillegg til 6-/24-timers akkumulert nedbør, regnstart, regn i rush-time og sesongjustert temperatur- og vindavvik. Værverdier slutter ved eksakt `t - 1`; manglende observasjoner fylles ikke. HGB behandler manglende værfeatures eksplisitt, mens manglende trafikkhistorikk fortsatt gjør forecast-raden ugyldig.

Sesongnormalene estimeres per lokal måned og time bare fra hver folds treningsperiode. De kan dermed ikke inneholde validerings- eller testvær.

## Modellvalg: ekspanderende CV i 2022–2023

| model | fold | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- | --- |
| traffic_hgb_with_calendar_events | 2022_h2 | 4417 | 143.81 | 240.90 |
| traffic_hgb_with_calendar_events | 2023_h1 | 4343 | 117.69 | 175.88 |
| traffic_hgb_with_calendar_events | 2023_h2 | 4417 | 97.58 | 143.11 |
| traffic_hgb_with_calendar_and_weather | 2022_h2 | 4417 | 151.14 | 245.49 |
| traffic_hgb_with_calendar_and_weather | 2023_h1 | 4343 | 122.69 | 182.80 |
| traffic_hgb_with_calendar_and_weather | 2023_h2 | 4417 | 99.47 | 146.04 |

## Gjennomsnitt over CV-folds

| model | mean_mae | mean_rmse |
| --- | --- | --- |
| traffic_hgb_with_calendar_and_weather | 124.43 | 191.44 |
| traffic_hgb_with_calendar_events | 119.69 | 186.63 |

Frosset kandidat valgt kun på CV-MAE: **traffic_hgb_with_calendar_events**.

## Diagnostisk 2024-resultat

2024 var brukt i tidligere eksperimenter og er ikke et uavhengig utvalg for dette arbeidet. Resultatet rapporteres derfor bare som diagnose og har ikke påvirket valget.

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| traffic_hgb_with_calendar_events | 8231 | 99.83 | 152.54 |
| previous_week_baseline | 8231 | 200.78 | 419.89 |

## Endelig 2025-test

Dette er én fast sluttevaluering av den CV-frosne kandidaten. Resultatet skal ikke brukes til videre feature- eller modellvalg.

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| traffic_hgb_with_calendar_events | 8760 | 102.35 | 149.62 |
| previous_week_baseline | 8760 | 191.73 | 398.95 |

## Frosset modellkonfigurasjon

Modellversjon: `traffic-hgb-calendar-v1`. Featurelisten og eventuell sesongtransform lagres sammen med den lokale, ignorerte modellartefakten i `models/`.

Konklusjon: Den avledede værpakken ble forkastet fordi den tapte alle tre CV-folds mot kalender-HGB. Den endelige, frosne modellen bruker derfor trafikkhistorikk, kalenderfeatures og ingen Frost-features. Videre værfeaturevalg er avsluttet; 2025-resultatet brukes bare som sluttevaluering.
