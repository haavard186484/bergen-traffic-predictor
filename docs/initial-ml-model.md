# Første lekkasjesikre ML-modell

Generert med `python -m scripts.run_initial_ml_model` fra lokalt trafikkdatasett.

## Oppsett

Hver rad er for tidspunkt `t` (UTC i datafilen, kalenderfeatures i `Europe/Oslo`). Målet er observert trafikk ved `t + 1 time`. Features er time, ukedag, måned, helg, syklisk time og eksakte trafikklag ved `t - 1`, `t - 2`, `t - 24` og `t - 168` timer. Oppslag skjer på timestamp, ikke radposisjon; alle rader med manglende feature eller mål utelates uten imputering.

Splitten gjelder predikert tidspunkt (`t + 1`): trening er 2022–2023, validering 2024 og test 2025. Lineær regresjon og `HistGradientBoostingRegressor` ble sammenlignet på validerings-MAE. Test ble først brukt etter valget; den valgte modellen er deretter trent på trening + validering.

## Validering

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| hist_gradient_boosting | 8231 | 103.28 | 162.94 |
| previous_week_baseline | 8231 | 200.78 | 419.89 |
| linear_regression | 8231 | 322.45 | 475.79 |

Valgt modell: **hist_gradient_boosting** (lavest MAE på validering).

## Endelig test mot forrige-uke-baseline

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| hist_gradient_boosting | 8760 | 106.22 | 164.43 |
| previous_week_baseline | 8760 | 191.73 | 398.95 |

## Feilanalyse på test: valgt modell per time

| hour | observations | mae | rmse |
| --- | --- | --- | --- |
| 0 | 365 | 42.45 | 70.79 |
| 1 | 365 | 31.76 | 53.24 |
| 2 | 365 | 28.42 | 42.32 |
| 3 | 365 | 41.72 | 51.78 |
| 4 | 365 | 70.39 | 94.59 |
| 5 | 365 | 173.53 | 285.74 |
| 6 | 365 | 152.85 | 248.40 |
| 7 | 365 | 131.51 | 206.62 |
| 8 | 365 | 115.15 | 169.15 |
| 9 | 365 | 123.39 | 168.57 |
| 10 | 365 | 122.17 | 173.93 |
| 11 | 365 | 120.13 | 170.72 |
| 12 | 365 | 113.87 | 158.22 |
| 13 | 365 | 116.14 | 174.39 |
| 14 | 365 | 155.62 | 215.48 |
| 15 | 365 | 140.64 | 199.01 |
| 16 | 365 | 145.88 | 192.92 |
| 17 | 365 | 135.62 | 187.39 |
| 18 | 365 | 116.44 | 156.42 |
| 19 | 365 | 101.64 | 137.43 |
| 20 | 365 | 116.19 | 160.71 |
| 21 | 365 | 99.61 | 125.16 |
| 22 | 365 | 93.22 | 134.32 |
| 23 | 365 | 61.03 | 91.83 |

## Feilanalyse på test: valgt modell per ukedag

| weekday | observations | mae | rmse |
| --- | --- | --- | --- |
| Friday | 1248 | 106.14 | 155.62 |
| Monday | 1248 | 110.65 | 188.29 |
| Saturday | 1248 | 103.94 | 151.69 |
| Sunday | 1248 | 97.21 | 135.89 |
| Thursday | 1248 | 111.77 | 171.59 |
| Tuesday | 1249 | 97.55 | 142.82 |
| Wednesday | 1271 | 116.12 | 195.11 |
