# Bergen Traffic Predictor

En maskinlæringsapplikasjon som predikerer antall kjøretøy ved ett
trafikkregistreringspunkt i Bergen én time frem i tid.

Prosjektet bruker historiske trafikkdata fra Statens vegvesen og kan utvides
med historiske værdata fra MET Norway / Frost. Første versjon arbeider med
timedata for ett valgt målepunkt.

## Kom i gang

Krever Python 3.11 eller nyere.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
streamlit run app/streamlit_app.py
```

## Hent eller oppdater trafikkdata

Bruk Traffic Data API, ikke manuell eksport, for flerårig timetrafikk. Med
virtuelt miljø aktivert henter og klargjør denne kommandoen data for Danmarks
plass (`14630V805616`) for perioden 2022–2025:

```bash
make refresh-traffic
```

Dette skriver rådata og hentemetadata til `data/raw/`, og normalisert data til
`data/processed/traffic_hourly.csv`. Kjente målegap beholdes som manglende
verdier; de fylles aldri automatisk.

For en annen periode eller et annet registreringspunkt kan variablene overstyres:

```bash
make refresh-traffic \
  TRAFFIC_POINT_ID=14630V805616 \
  TRAFFIC_FROM=2025-01-01T00:00:00+01:00 \
  TRAFFIC_TO=2026-01-01T00:00:00+01:00 \
  RAW_TRAFFIC=data/raw/traffic_2025.csv
```

## EDA og baseline

Lag EDA-rapporten og evaluer den reproduserbare baselinen med lokalt data:

```bash
python -m scripts.run_traffic_eda_baseline
```

Kommandoen leser `data/processed/traffic_hourly.csv` og oppdaterer
`docs/traffic-eda-baseline.md`. Rapporten bruker lokal tid (`Europe/Oslo`) for
kalendergrupper og deler kronologisk i trening (2022--2023), validering (2024)
og test (2025). Målegap beholdes som manglende verdier i alle steg.

Baselinen predikerer trafikken ved tidspunkt `t` med den observerte verdien ved
`t - 168 timer` (samme time forrige uke). Oppslaget gjøres på eksakt timestamp,
ikke radnummer: manglende input eller target gir derfor ikke en prediksjon og
kan aldri føre til at et målegap hoppes over. MAE er hovedmetrikken, med RMSE
som støttemål. Se den genererte [EDA- og baseline-rapporten](docs/traffic-eda-baseline.md)
for funn og resultater.

## Første ML-modell

Kjør det lekkasjesikre, reproduserbare modellforsøket på det lokale
trafikkdatasettet:

```bash
python -m scripts.run_initial_ml_model
```

Kommandoen skriver [modellrapporten](docs/initial-ml-model.md). Hver feature-rad
er for tidspunkt `t`; målet er trafikkvolumet ved `t + 1 time`. Kalenderfeatures
(time, ukedag, måned og helg) beregnes i `Europe/Oslo`, og timen er også uttrykt
syklisk. Trafikkfeatures er kun historiske, med eksakte timestamp-oppslag for
lagene 1, 2, 24 og 168 timer. Derfor blir både features og target manglende ved
målegap; ingenting imputeres eller forskyves over et hull.

Modellene trenes på 2022--2023 og velges utelukkende på validering i 2024.
`LinearRegression` og `HistGradientBoostingRegressor` sammenlignes med
forrige-uke-baselinen på de samme gyldige forecast-radene. Den valgte
`HistGradientBoostingRegressor` oppnådde følgende resultater:

| periode | modell | MAE | RMSE | gyldige prediksjoner |
| --- | --- | ---: | ---: | ---: |
| validering 2024 | HistGradientBoostingRegressor | 103,28 | 162,94 | 8 231 |
| validering 2024 | forrige uke-baseline | 200,78 | 419,89 | 8 231 |
| test 2025 | HistGradientBoostingRegressor | 106,22 | 164,43 | 8 760 |
| test 2025 | forrige uke-baseline | 191,73 | 398,95 | 8 760 |

Etter modellvalg er den valgte modellen trent på trening + validering og
evaluert én gang på 2025. Rapporten inneholder også feilanalyse fordelt på time
og ukedag. Modeller lagres ikke ennå, slik at ingen modellartefakter produseres
eller versjonskontrolleres av forsøket.

Kjente begrensninger: dette er kun trafikkhistorikk og kalenderdata for ett
målepunkt; det brukes ikke værvarsel, helligdager eller hendelsesdata. En
prediksjon kan ikke lages når nødvendig trafikkhistorikk eller neste times mål
berører et kjent målegap.

Se [datafeasibility-guiden](docs/data-feasibility.md) for detaljer om API,
datakvalitet og målegap.

## Status

Trafikkdata, EDA, baseline og første lekkasjesikre ML-modell for Danmarks plass
er etablert. Neste naturlige steg er å vurdere værdata som var tilgjengelige
ved prediksjonstidspunktet.
