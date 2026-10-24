# Latensrobust modellvalg

Generert med `python -m scripts.run_latency_robust_model`.

## Forhåndsdefinerte kandidater

Alle kandidatene bruker `HistGradientBoostingRegressor`, deterministiske norske kalenderfeatures i `Europe/Oslo` og kun Statens vegvesens eksisterende timeserie. Kandidatlisten ble frosset før CV-resultatene ble inspisert: `(t−24, t−168)`, `(t−24, t−48, t−168)` og `(t−24, t−168, t−336)`. Ingen bruker `t−1`, `t−2`, vær eller andre datakilder. Eksakte timestamp-oppslag gjør at målegap fortsatt gir en ugyldig forecast-rad fremfor å forskyve data.

## Modellvalg: ekspanderende CV i 2022–2023

| model | fold | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- | --- |
| traffic_hgb_calendar_lags_24_168 | 2022_h2 | 4417 | 167.80 | 284.53 |
| traffic_hgb_calendar_lags_24_168 | 2023_h1 | 4343 | 131.05 | 194.22 |
| traffic_hgb_calendar_lags_24_168 | 2023_h2 | 4417 | 105.78 | 153.92 |
| traffic_hgb_calendar_lags_24_48_168 | 2022_h2 | 4417 | 166.03 | 282.74 |
| traffic_hgb_calendar_lags_24_48_168 | 2023_h1 | 4343 | 129.99 | 193.22 |
| traffic_hgb_calendar_lags_24_48_168 | 2023_h2 | 4417 | 105.29 | 152.67 |
| traffic_hgb_calendar_lags_24_168_336 | 2022_h2 | 4417 | 170.05 | 289.04 |
| traffic_hgb_calendar_lags_24_168_336 | 2023_h1 | 4343 | 130.76 | 193.61 |
| traffic_hgb_calendar_lags_24_168_336 | 2023_h2 | 4417 | 106.58 | 154.81 |

## Gjennomsnitt over CV-folds

| model | mean_mae | mean_rmse |
| --- | --- | --- |
| traffic_hgb_calendar_lags_24_168 | 134.88 | 210.89 |
| traffic_hgb_calendar_lags_24_168_336 | 135.80 | 212.49 |
| traffic_hgb_calendar_lags_24_48_168 | 133.77 | 209.54 |

Kandidaten ble fryst kun på gjennomsnittlig CV-MAE: **traffic_hgb_calendar_lags_24_48_168**.

## Cross-validated permutation feature importance

Den valgte feature-pakken ble trent på nytt i hver av de tre kronologiske CV-foldene. Hver feature ble permutert 30 ganger på foldens validation-data. En positiv verdi er gjennomsnittlig økning i MAE, målt i kjøretøy per time. Analysen beskriver modellens avhengighet av inputene og ble ikke brukt til å endre den frosne kandidaten.

| feature | mean_delta_mae | std_delta_mae | folds | permutations |
| --- | --- | --- | --- | --- |
| traffic_168h_ago | 394.64 | 13.41 | 3 | 90 |
| hour_cos | 366.88 | 24.19 | 3 | 90 |
| traffic_24h_ago | 223.15 | 25.47 | 3 | 90 |
| day_of_week | 182.21 | 11.64 | 3 | 90 |
| hour | 153.33 | 9.75 | 3 | 90 |
| hour_sin | 23.46 | 4.11 | 3 | 90 |
| is_public_holiday | 19.94 | 16.09 | 3 | 90 |
| month | 11.52 | 10.35 | 3 | 90 |
| traffic_48h_ago | 11.30 | 4.68 | 3 | 90 |
| is_christmas_new_year_period | 5.07 | 6.59 | 3 | 90 |
| is_day_before_public_holiday | 1.74 | 1.66 | 3 | 90 |
| is_day_after_public_holiday | 0.51 | 0.74 | 3 | 90 |
| is_weekend | 0.00 | 0.00 | 3 | 90 |
| is_constitution_day | 0.00 | 0.00 | 3 | 90 |

2025 var låst fra forrige sluttevaluering og ble ikke brukt til kandidat-, feature- eller modellvalg. Etter frysing ble modellen trent på 2022–2025.

## Én sluttevaluering: 2026 H1

Den nye, tidligere ubrukte perioden er 2026-01-01 til 2026-07-01 i `Europe/Oslo`. Modell og forrige-uke-baseline scores på nøyaktig de samme forecast-radene.

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| traffic_hgb_calendar_lags_24_48_168 | 4343 | 108.81 | 161.85 |
| previous_week_baseline | 4343 | 211.79 | 454.47 |

## Feilanalyse etter forecast-time

| target_hour | observations | mae | rmse |
| --- | --- | --- | --- |
| 0 | 181 | 72.33 | 104.38 |
| 1 | 181 | 52.12 | 88.65 |
| 2 | 180 | 50.04 | 94.96 |
| 3 | 181 | 39.36 | 64.43 |
| 4 | 181 | 32.24 | 67.62 |
| 5 | 181 | 69.75 | 90.60 |
| 6 | 181 | 114.16 | 161.45 |
| 7 | 181 | 126.24 | 213.81 |
| 8 | 181 | 139.25 | 214.47 |
| 9 | 181 | 124.12 | 172.38 |
| 10 | 181 | 137.73 | 180.90 |
| 11 | 181 | 119.43 | 156.65 |
| 12 | 181 | 117.01 | 160.15 |
| 13 | 181 | 129.45 | 180.42 |
| 14 | 181 | 128.97 | 176.93 |
| 15 | 181 | 120.17 | 182.91 |
| 16 | 181 | 145.35 | 205.25 |
| 17 | 181 | 152.58 | 204.19 |
| 18 | 181 | 147.86 | 194.40 |
| 19 | 181 | 122.50 | 169.17 |
| 20 | 181 | 121.22 | 171.11 |
| 21 | 181 | 151.36 | 205.67 |
| 22 | 181 | 100.77 | 134.18 |
| 23 | 181 | 97.24 | 127.84 |

## Feilanalyse etter forecast-ukedag

| target_day_of_week | observations | mae | rmse |
| --- | --- | --- | --- |
| 0 | 624 | 107.97 | 153.76 |
| 1 | 624 | 97.05 | 150.01 |
| 2 | 600 | 100.14 | 155.16 |
| 3 | 624 | 111.01 | 155.86 |
| 4 | 624 | 110.34 | 167.55 |
| 5 | 624 | 121.89 | 181.73 |
| 6 | 623 | 112.98 | 166.37 |

## Frosset modellkonfigurasjon

Modellversjon: `traffic-hgb-latency-robust-v1`. Den frosne HGB-modellen og metadata lagres lokalt, ignorert av Git, i `models/`. Treningsperioden slutter før sluttevalueringen (2026-01-01); 2026-resultatet brukes ikke videre til tuning.
