# Feilanalyse: trafikk-HGB, validering 2024

Generert med `python -m scripts.run_model_evaluation`. Dette er en diagnostisk analyse av 2024-valideringen; 2025-testen brukes ikke.

## Oppsett og avgrensning

Den valgte trafikk-HGB-en trenes på 2022–2023 og predikerer trafikk ved `t + 1` fra features ved `t`. Kalendergruppene nedenfor er basert på predikert tidspunkt i `Europe/Oslo`. Alle 8 231 gyldige trafikk-forecast-rader i 2024 beholdes i kalenderanalysen.

Værgruppene bruker eksakt observert Frost-vær fra SN50540 ved `t − 1` (to timer før forecast-målet) kun som etterfølgende diagnose. Været er ikke input til den valgte modellen. Manglende Frost-observasjoner fylles ikke: hver værtabell ekskluderer bare rader som mangler gruppens aktuelle værverdi. Rader med alle tre `t − 1`-verdier observert: 8175.

## Feil per time

| hour | observations | mae | rmse |
| --- | --- | --- | --- |
| 0 | 343 | 68.57 | 99.58 |
| 1 | 343 | 47.77 | 77.96 |
| 2 | 343 | 31.47 | 54.47 |
| 3 | 343 | 27.60 | 42.62 |
| 4 | 343 | 32.60 | 43.62 |
| 5 | 343 | 70.18 | 89.64 |
| 6 | 343 | 138.64 | 253.06 |
| 7 | 343 | 143.08 | 240.31 |
| 8 | 343 | 140.90 | 233.78 |
| 9 | 343 | 110.06 | 168.87 |
| 10 | 342 | 111.00 | 170.57 |
| 11 | 343 | 123.18 | 182.39 |
| 12 | 343 | 117.40 | 166.83 |
| 13 | 343 | 106.37 | 140.60 |
| 14 | 343 | 121.21 | 155.44 |
| 15 | 343 | 159.25 | 220.27 |
| 16 | 343 | 148.51 | 209.88 |
| 17 | 343 | 129.84 | 176.30 |
| 18 | 343 | 141.37 | 199.37 |
| 19 | 343 | 110.32 | 151.60 |
| 20 | 343 | 103.18 | 145.72 |
| 21 | 343 | 99.72 | 146.73 |
| 22 | 343 | 90.75 | 122.42 |
| 23 | 343 | 105.66 | 152.47 |

## Feil per ukedag

| weekday | observations | mae | rmse |
| --- | --- | --- | --- |
| Friday | 1165 | 107.54 | 162.70 |
| Monday | 1200 | 119.92 | 210.17 |
| Saturday | 1176 | 101.96 | 139.87 |
| Sunday | 1176 | 93.61 | 140.89 |
| Thursday | 1152 | 104.14 | 155.78 |
| Tuesday | 1200 | 99.06 | 167.32 |
| Wednesday | 1162 | 96.44 | 151.79 |

## Feil per måned

| month | observations | mae | rmse |
| --- | --- | --- | --- |
| April | 720 | 108.67 | 174.56 |
| August | 744 | 89.60 | 125.48 |
| December | 744 | 138.54 | 213.18 |
| February | 696 | 82.82 | 115.48 |
| January | 744 | 125.71 | 222.09 |
| July | 744 | 94.01 | 139.76 |
| June | 720 | 83.70 | 115.29 |
| March | 743 | 99.36 | 150.89 |
| May | 744 | 136.25 | 223.02 |
| November | 720 | 85.95 | 119.80 |
| October | 192 | 121.34 | 184.76 |
| September | 720 | 83.81 | 118.83 |

## Feil ved regn og ikke-regn

| rain | observations | mae | rmse |
| --- | --- | --- | --- |
| no_rain | 5812 | 100.02 | 159.41 |
| rain | 2391 | 111.39 | 171.39 |

## Feil per vindstyrke ved t − 1

Intervaller: under 4 m/s, 4 til under 8 m/s og minst 8 m/s.

| wind_band | observations | mae | rmse |
| --- | --- | --- | --- |
| under_4_m_s | 5356 | 98.39 | 155.02 |
| 4_to_under_8_m_s | 2459 | 109.56 | 166.49 |
| 8_m_s_or_more | 360 | 134.27 | 239.24 |

## Feil per temperaturintervall ved t − 1

Intervaller: under 0 °C, 0 til under 5 °C, 5 til under 10 °C og minst 10 °C.

| temperature_band | observations | mae | rmse |
| --- | --- | --- | --- |
| below_0_c | 647 | 114.91 | 183.69 |
| 0_to_under_5_c | 1470 | 107.02 | 181.14 |
| 5_to_under_10_c | 2396 | 100.97 | 160.35 |
| 10_c_or_more | 3706 | 101.30 | 152.77 |

## Enkeltdager med størst feil

Tabellen viser de ti lokale datoene med høyest MAE blant datoer med minst 20 gyldige forecasts. Positiv `mean_signed_error` betyr at modellen i gjennomsnitt overpredikerte den dagen.

| date | observations | mae | rmse | mean_signed_error | maximum_absolute_error |
| --- | --- | --- | --- | --- | --- |
| 2024-01-01 | 24 | 655.66 | 856.10 | 442.56 | 1654.64 |
| 2024-12-31 | 24 | 479.65 | 603.03 | 424.69 | 1240.34 |
| 2024-05-17 | 24 | 388.84 | 578.35 | 192.19 | 1773.65 |
| 2024-12-24 | 24 | 315.25 | 451.19 | 171.28 | 1294.11 |
| 2024-05-01 | 24 | 313.36 | 441.74 | 109.41 | 1454.92 |
| 2024-04-01 | 24 | 304.27 | 527.41 | 158.01 | 1641.37 |
| 2024-05-09 | 24 | 295.60 | 424.56 | 154.46 | 1365.86 |
| 2024-03-27 | 24 | 249.00 | 404.86 | 133.47 | 1322.39 |
| 2024-12-23 | 24 | 244.17 | 322.91 | 21.07 | 681.39 |
| 2024-01-08 | 24 | 237.67 | 293.82 | -92.84 | 674.79 |

De høyeste dagene sammenfaller i stor grad med norske helligdager eller høytidsdager: nyttårsaften/-dagen, påske (1. april), 1. mai, Kristi himmelfartsdag (9. mai), 17. mai og julaften. Det peker på kalender- og hendelseseffekter som dagens features ikke representerer. 27. mars og 8. januar har også høye feil, men prosjektet har ikke hendelsesdata som kan bekrefte en årsak; tabellen må derfor ikke tolkes som kausal dokumentasjon.

## Kan vær være nyttig i bestemte situasjoner?

Den allerede avviste vær-HGB-en sammenlignes her med trafikk-HGB på samme 2024-rader, delt etter regn, vind og temperatur ved `t − 1`. Positiv `weather_minus_traffic_mae` betyr at vær-HGB er dårligere. Dette er eksplorativ undergruppeanalyse, ikke grunnlag for nytt modellvalg; 2024 er allerede brukt til valg, og 2025 forblir urørt.

| weather_group | condition | observations | traffic_hgb_mae | weather_hgb_mae | weather_minus_traffic_mae |
| --- | --- | --- | --- | --- | --- |
| rain | no_rain | 5730 | 100.04 | 103.02 | 2.98 |
| rain | rain | 2380 | 111.63 | 115.74 | 4.11 |
| wind_band | under_4_m_s | 5337 | 98.58 | 101.87 | 3.29 |
| wind_band | 4_to_under_8_m_s | 2434 | 109.57 | 113.26 | 3.69 |
| wind_band | 8_m_s_or_more | 355 | 133.70 | 135.11 | 1.40 |
| temperature_band | below_0_c | 647 | 114.91 | 118.45 | 3.54 |
| temperature_band | 0_to_under_5_c | 1466 | 107.09 | 108.15 | 1.06 |
| temperature_band | 5_to_under_10_c | 2385 | 101.08 | 106.42 | 5.33 |
| temperature_band | 10_c_or_more | 3628 | 101.39 | 104.28 | 2.89 |

Konklusjon: Vær kan forklare variasjon i feilnivået i enkelte værgrupper, men de tre rå, konservative Frost-lagene har ikke vist en robust samlet forbedring. Det finnes derfor ikke grunnlag for å endre valgt modell. Eventuelle nye væravledninger må velges med tidsseriekryssvalidering innen 2022–2023 før én endelig 2024-evaluering; bruk heller ikke 2025 til featurevalg.
