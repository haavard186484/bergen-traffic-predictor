# Bergen Traffic Predictor

[Les prosjektrapporten (PDF)](report/bergen-traffic-predictor-report.pdf)

## Videodemonstrasjon

En kort demonstrasjon av prognoseappen:



https://github.com/user-attachments/assets/5598cc2d-ddde-4813-93b8-5eb32f29f990



En maskinlæringsapplikasjon som predikerer antall kjøretøy ved ett
trafikkregistreringspunkt i Bergen én time frem i tid.

Den endelige løsningen er den latensrobuste, værfrie
`traffic-hgb-latency-robust-v1`-modellen for Danmarks plass (`14630V805616`).
Den predikerer trafikkvolum én time frem i tid fra kalenderfeatures og eksakte
trafikklag ved `t-24`, `t-48` og `t-168`. Historiske forsøk med Frost-værdata
er dokumentert nedenfor, men inngår ikke i appen eller sluttmodellen.

## Bygg rapporten

Bygg prosjektrapporten på nytt med:

```bash
make report
```

Bygget krever `latexmk`, pdfLaTeX, Biber og `texcount`. LaTeX-kildene og den
reproduserbare figuren ligger i `report/`.

## Kom i gang

Krever Python 3.11 eller nyere.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make build-app-model
pytest
streamlit run app/streamlit_app.py
```

`make build-app-model` henter og normaliserer trafikkdata for 2022--2026 H1
og trener den frosne modellen lokalt. Rådata, prosesserte data og
modellartefakter er ignorert av Git, men kan gjenskapes med kommandoen. Appen
krever ingen Frost-nøkkel eller Frost-data.

## Hent eller oppdater trafikkdata

Bruk Traffic Data API, ikke manuell eksport, for flerårig timetrafikk. Med
virtuelt miljø aktivert henter og klargjør denne kommandoen data for Danmarks
plass (`14630V805616`) for perioden 2022--2026 H1 som sluttmodellen trenger:

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

## Eksperimenthistorikk

Seksjonene nedenfor dokumenterer EDA, baseline og de kronologiske
modellforsøkene som ledet fram til sluttmodellen. De beholdes for
etterprøvbarhet, men bare den latensrobuste modellen i seksjonen
«Latensrobust modell og Streamlit-app» er produksjonskandidaten.

### EDA og baseline

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

### Første ML-modell

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

### Værdata fra MET Norway / Frost

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

### Feilanalyse av valgt modell

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

### Kalenderfeatures og videre modellvalg

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

### Frosset kalender- og værmodell

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

## Latensrobust modell og Streamlit-app

Den tidligere modellen krevde de nyligste trafikkobservasjonene (`t - 1` og
`t - 2`), som ikke alltid er publisert når en forecast skal lages. Den frosne
latensrobuste modellen `traffic-hgb-latency-robust-v1` bruker i stedet bare
deterministiske norske kalenderfeatures og trafikk-lagene `t - 24`, `t - 48`
og `t - 168`. Target er fortsatt trafikkvolumet ved `t + 1`. Det brukes ikke
Frost, `FROST_CLIENT_ID` eller andre datakilder.

Kandidatlisten ble bestemt før resultater ble inspisert og besto av HGB med
lagpakkene `(24, 168)`, `(24, 48, 168)` og `(24, 168, 336)`. Kun
ekspanderende CV i 2022--2023 ble brukt til valg. Vinneren var pakken
`(24, 48, 168)` med gjennomsnittlig CV-MAE 133,77. 2025 var låst og ble ikke
brukt til kandidatvalg. Etter frysing ble modellen trent på 2022--2025 og
målt én gang på den nye perioden 2026 H1:

| periode | modell | MAE | RMSE | gyldige, delte forecast-rader |
| --- | --- | ---: | ---: | ---: |
| 2026 H1 | latency-robust HGB | 108,81 | 161,85 | 4 343 |
| 2026 H1 | forrige uke-baseline | 211,79 | 454,47 | 4 343 |

Resultatet, inklusive feilanalyse per forecast-time og -ukedag, gjenskapes
med følgende kommando. Den leser bare `data/processed/traffic_hourly.csv` og
lagrer en ignorert artefakt i `models/`:

```bash
python -m scripts.run_latency_robust_model
```

Kjør `make build-app-model` fra en tom arbeidskopi for å hente hele perioden,
bygge det normaliserte datasettet og lage modellartefakten. Dersom dataene
allerede finnes, er `make train-latency-robust-model` tilstrekkelig for å lage
artefakten på nytt.

Start deretter appen med `streamlit run app/streamlit_app.py`. Appen henter
trafikkhistorikk fra Traffic Data API for biltrafikk ved Danmarks plass
(`14630V805616`). Velg «Neste time» (standard) eller en historisk dato og time,
og trykk «Vis prognose». Appen viser et prognosekort i kjøretøy/time og det
eksakte timeintervallet i `Europe/Oslo`, med UTC-offset. Ved overgang til
vintertid kan begge forekomster av samme klokkeslett velges; ikke-eksisterende
timer ved overgang til sommertid tilbys ikke. «Neste time» beregnes i UTC,
slik at intervallet alltid er én faktisk time.

Sammenligningen er observert trafikk ved **target−168 timer**, altså **t−167**
når target=t+1. Den er separat fra modellens t−168-feature. Ved overgang til
sommertid/vintertid kan lokal klokkeslett derfor avvike fra target. Appen viser
prosentforskjellen `(prognose / observasjon − 1) × 100` bare når observasjonen
er positiv. Manglende sammenligningsdata blokkerer ikke en gyldig prognose.

Grafen viser observasjoner i de siste 72 timene før target og prognosen som
en separat diamant. Manglende timer og nullverdier beholdes som hull, uten
imputering eller linjer over gapene. Prognosen gjelder kun registreringspunktet,
ikke all trafikk på Danmarks plass. Tekniske input og modellmetadata finnes i
en utfellbar seksjon. Modell, features og evalueringsresultater er uendret.

Datastatus viser kilde, hentetidspunkt og siste tilgjengelige observasjon i
uttrekket. API-feil, manglende modellartefakt og manglende nødvendige lag gir
meldinger med neste steg. Hvert klikk henter data på nytt; det kreves ingen
API-nøkler eller nye miljøvariabler. Siden modellen ikke krever siste times
observasjon, tåler den forsinket publisering. Historiske oppslag bruker dagens
API-data; tidligere publiseringstidspunkt rekonstrueres ikke. Historiske
prognoser innen treningsperioden er demonstrasjoner, ikke ny testevaluering.

Dashboardets tema ligger i `.streamlit/config.toml`. Kjør kontrollene med:

```bash
pytest
ruff check .
ruff format --check app/streamlit_app.py tests/test_streamlit_app.py
```

## Status

Prosjektet er klart for lokal demonstrasjon: den frosne, latensrobuste
trafikk-HGB-en for Danmarks plass er trent på 2022--2025, evaluert én gang på
2026 H1 og tilgjengelig gjennom Streamlit-appen. Værforsøkene er avsluttet
fordi de ikke forbedret den kronologiske valideringen; Frost brukes derfor
ikke i sluttmodellen.
