# Værfeatures: validering 2024

Begge modellene er evaluert på nøyaktig samme forecast-tidspunkter. Værfeatures er eksakte observerte lag ved `t−1`, `t−2` og `t−24` timer.

| model | evaluated_predictions | mae | rmse |
| --- | --- | --- | --- |
| traffic_only_hist_gradient_boosting | 8126 | 103.41 | 163.28 |
| weather_augmented_hist_gradient_boosting | 8126 | 106.73 | 168.87 |
| previous_week_baseline | 8126 | 201.86 | 422.09 |

Valgt oppsett: **traffic_only_hist_gradient_boosting** (lavest MAE på validering).

Værmodellen evalueres ikke på 2025-testen fordi den ikke vant valideringen. Den tidligere rapporterte testen for valgt trafikkmodell beholdes uendret.
