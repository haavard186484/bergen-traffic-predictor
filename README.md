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

## Videre arbeidsflyt

1. Utforsk og dokumenter datakvaliteten i det bearbeidede datasettet.
2. Etabler en kronologisk tidsserie-baseline.
3. Tren og evaluer modeller mot baselinen.
4. Legg til værdata etter at trafikkmodellen er etablert.
5. Koble valgt modell til Streamlit-appen.

Se [datafeasibility-guiden](docs/data-feasibility.md) for detaljer om API,
datakvalitet og målegap.

## Status

Trafikkdatasettet for Danmarks plass er etablert. Neste steg er utforskende
analyse og en tidsserie-baseline.
