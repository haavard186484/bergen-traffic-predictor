# Historiske værdata fra Frost

## Stasjon og elementer

Pipelinen bruker som standard **SN50540 (Bergen - Florida)**, en sentral
Frost-stasjon i Bergen. Hver nedlasting spør først Frost om tilgjengelige
tidsserier for den konkrete perioden og lagrer svaret i metadatafilen. Det er
viktig: stasjonsdekning kan endres med sensor, element og tid, så stasjonsnavn
alene er ikke dokumentasjon på dekning.

De etterspurte timeseriene er:

| Frost-element | lokal kolonne | enhet |
| --- | --- | --- |
| `air_temperature` | `temperature_c` | °C |
| `sum(precipitation_amount PT1H)` | `precipitation_mm` | mm per time |
| `wind_speed` | `wind_speed_m_s` | m/s |

Nedlasting for 2022--2025 gjøres i månedlige, halve UTC-intervaller. Den
genererte `weather_hourly.csv.metadata.json` inneholder stasjon, eksakt
forespurt periode, elementer, hentetidspunkt, Frosts
`availableTimeSeries`-svar og antall observerte/manglende timer per element.
Manglende værverdier fylles aldri; de står som `NaN` etter sammenslåing med
trafikk på UTC-`timestamp`.

Nedlastingen for 2022--2025 ga følgende faktiske dekning av 35 064 trafikktimer:

| kolonne | observerte timer | manglende timer |
| --- | ---: | ---: |
| `temperature_c` | 35 016 | 48 |
| `precipitation_mm` | 35 016 | 48 |
| `wind_speed_m_s` | 34 458 | 606 |

## Forecast-sikkerhet: konservative vær-lag

Frosts `referenceTime` angir når observasjonen gjelder, ikke når den ble
tilgjengelig i en operativ prognose. Derfor brukes aldri værverdien ved `t`
som feature for prediksjonen fra `t` til `t + 1`.

I stedet bruker modellen bare eksakte observerte vær-lag fra `t − 1`, `t − 2`
og `t − 24` timer, for temperatur, nedbør og vind. Én time er en konservativ,
dokumentert prosjektantakelse om tilgjengelighet; den er ikke et bevis på
Frosts faktiske publiseringsforsinkelse. Eksakte timestamp-oppslag betyr at en
manglende værtime gir manglende features; den erstattes aldri av en observasjon
fra en annen time.

Kjør `python -m scripts.run_weather_model --weather
data/processed/weather_hourly.csv` etter nedlastingen. Den sammenligner HGB
med og uten vær-lag, samt forrige-uke-baseline, på nøyaktig samme gyldige
forecast-rader i 2024. Modellen velges bare på denne valideringen; 2025-testen
brukes først etterpå.

## Resultat: validering 2024

Sammenligningen bruker 8 126 forecast-rader der trafikkhistorikk, target og
alle tre værvariablene med lagene `t − 1`, `t − 2` og `t − 24` er observert.

| modell | MAE | RMSE |
| --- | ---: | ---: |
| HGB, kun trafikk | 103,41 | 163,28 |
| HGB, trafikk + vær-lag | 106,73 | 168,87 |
| forrige-uke-baseline | 201,86 | 422,09 |

Vær-lagene forbedret ikke valideringen. Trafikkmodellen uten vær beholdes,
og værmodellen evalueres derfor ikke på 2025-testen.

Ved senere produksjonssetting bør antakelsen erstattes eller kontrolleres med
målt publiseringsforsinkelse. Et arkiv av utstedte værvarsler er alternativet
hvis modellen skal bruke vær for `t + 1`.
