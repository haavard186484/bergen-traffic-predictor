# Bergen Traffic Predictor

En maskinlæringsapplikasjon som predikerer antall kjøretøy ved ett
trafikkregistreringspunkt i Bergen én time frem i tid.

Prosjektet bruker historiske trafikkdata fra Statens vegvesen og kan hente
historiske værdata fra MET Norway / Frost. Første versjon arbeider med timedata
for ett valgt målepunkt.

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

## Værdata fra MET Norway / Frost

Den reproduserbare Frost-klienten henter timeserier fra standardstasjonen
Bergen - Florida (`SN50540`) for temperatur, timesnedbør og vindhastighet.
Opprett en Frost client ID og angi den kun i miljøet; den skal aldri stå i en
fil som committes:

```bash
export FROST_CLIENT_ID='din-client-id'
make download-weather
```

Dette skriver genererte, ignorerte data til `data/processed/weather_hourly.csv`
og en sidecar-metadatafil. Metadataen dokumenterer Frost-kilde, hentetid,
stasjon, periode, elementer, tidsserie-tilgjengelighet og observert/manglende
dekning. Vær og trafikk kobles på UTC-`timestamp`; alle tidsstempel beholdes
med tidssone under behandling.

Frosts `referenceTime` angir observasjonstid, ikke publiseringstid. Den
lekkasjesikre løsningen bruker derfor aldri vær ved `t`, men eksakte
temperatur-, nedbør- og vindlag fra `t − 1`, `t − 2` og `t − 24` timer. Én
times forsinkelse er en bevisst konservativ prosjektantakelse; et målegap i
vær gir manglende features og fylles ikke. Se
[værdatadokumentasjonen](docs/weather-data.md) for stasjon, mangler og
begrensningen.

Værmodellene evalueres uten å bruke 2025-testen i modellvalg:

```bash
python -m scripts.run_weather_model --weather data/processed/weather_hourly.csv
```

Den gjenbruker samme feature- og treningskode og sammenligner
`HistGradientBoostingRegressor` med og uten vær på identiske gyldige rader i
2024. SN50540-dekningen for 2022--2025 er 35 016/35 064 timer for temperatur
og nedbør, og 34 458/35 064 for vind; mangler fylles ikke.

På 8 126 felles, gyldige forecast-rader i 2024 fikk HGB uten vær MAE 103,41
og RMSE 163,28. HGB med vær-lag fikk MAE 106,73 og RMSE 168,87; forrige-
uke-baseline fikk MAE 201,86. Vær-lagene ble derfor ikke valgt og ble ikke
evaluert på 2025-testen. Dagens valgte modell er fortsatt trafikk-HGB med
tidligere rapportert full test-MAE 106,22. Se
[værmodellrapporten](docs/weather-model.md).

## Feilanalyse av valgt modell

Kjør den reproduserbare, diagnostiske 2024-analysen med lokale trafikk- og
værdata:

```bash
python -m scripts.run_model_evaluation
```

Den skriver [feilanalyserapporten](docs/model-evaluation.md). Trafikk-HGB
trenes da kun på 2022--2023, og analysen bruker 2024-valideringen; 2025-testen
leses eller brukes ikke. Rapporten fordeler feil etter lokal time, ukedag og
måned, undersøker datoer med store feil og grupperer dem etter Frost-vær ved
`t - 1` (regn, vind og temperatur). Væropplysningene er diagnostiske, ikke
nye modellfeatures, og Frost-mangler holdes eksplisitte uten imputering.

## Kalenderfeatures og videre modellvalg

Helligdags- og høytidsindikatorer evalueres uten å bruke 2025:

```bash
python -m scripts.run_calendar_model
```

Dette skriver [kalender-modellrapporten](docs/calendar-model.md). Kandidaten
velges på ekspanderende tidsserie-kryssvalidering i 2022--2023 og bruker bare
deterministisk kalenderinformasjon i `Europe/Oslo`. 2024 rapporteres
etterfølgende for den CV-valgte kandidaten, men er ikke et uavhengig testsett
fordi perioden allerede er brukt i tidligere eksperimenter. 2025 forblir
urørt for videre feature- og modellvalg. Kalender-HGB er foreløpig å
foretrekke: gjennomsnittlig CV-MAE er 119,69 mot 120,03 uten kalenderfeatures,
og den etterfølgende 2024-MAE er 99,83. Den lille CV-forskjellen tilsier at
featurelisten må fryses før en eventuell senere, én-gangs sluttevaluering.

## Frosset kalender- og værmodell

Når den siste, forhåndsdefinerte værpakken skal vurderes og modellen fryses,
kjør:

```bash
python -m scripts.run_final_model_evaluation
```

Kommandoen velger mellom kalender-HGB og kalender-HGB med avledet vær kun fra
ekspanderende CV i 2022--2023. Værpakken består av akkumulert nedbør,
regnstart/rush-interaksjon og sesongjustert temperatur og vind, alle basert på
observasjoner senest ved `t - 1`. Den skriver
[sluttrapporten](docs/final-model-evaluation.md), evaluerer den frosne
kandidaten én gang på 2025, og lagrer modell samt feature-metadata lokalt i
`models/`. Modellartefaktene er ignorert av Git. 2025-resultatet skal ikke
brukes til ytterligere modellvalg.

Den frosne `traffic-hgb-calendar-v1`-modellen ble valgt: værpakken tapte alle
tre 2022--2023-folds og inngår ikke i den endelige featurelisten. Sluttmålingen
på 2025 sammenlignes med forrige-uke-baselinen på identiske forecast-rader.

## Streamlit-prediksjon

Generer først den lokale, ignorerte modellartefakten fra det lokale
trafikkdatasettet, og start deretter appen:

```bash
python -m scripts.run_final_model_evaluation
streamlit run app/streamlit_app.py
```

Appen laster den frosne `traffic-hgb-calendar-v1`-artefakten fra
`models/traffic_hgb_v2.joblib`. For forecast-tidspunktet `t` (tolket i
`Europe/Oslo`) henter den observerte trafikkvolumer fra Traffic Data API ved
nøyaktig `t - 1`, `t - 2`, `t - 24` og `t - 168` timer. Appen bygger kalender-
og trafikkfeatures med samme kode som treningen, og nekter å predikere dersom
API-et feiler eller nødvendig historikk mangler eller ikke er et endelig tall.
Ferdig aggregerte timesverdier publiseres med forsinkelse; appen foreslår derfor
et forecast-tidspunkt tre timer tilbake i tid. Forecast-tidspunktet må være på
hel time, siden API-et bare leverer timesaggregater. Velg en eldre time dersom
API-et rapporterer manglende historikk for et helt nylig tidspunkt.

Den frosne modellen bruker trafikkhistorikk og deterministiske norske
kalenderfeatures, men ingen Frost-værfeatures, værvarsel eller
`FROST_CLIENT_ID`. Sluttevalueringen på 2025 ble gjort én gang etter CV-valget:
MAE 102,35 og RMSE 149,62 på 8 760 forecast-rader, mot forrige-uke-baselinens
MAE 191,73 og RMSE 398,95 på de samme radene. Dette resultatet skal ikke brukes
til videre modell- eller featurevalg.

## Status

Trafikkdata, EDA, baseline og første lekkasjesikre ML-modell for Danmarks plass
er etablert. Historisk Frost-nedlasting og konservative vær-lag er klare for
validering på samme 2024-periode.
