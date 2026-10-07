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

## Arbeidsflyt

1. Hent og valider trafikk- og værdata til `data/raw/`.
2. Bygg et modellklart datasett med `src/data/build_dataset.py`.
3. Tren og evaluer mot en tidsserie-baseline.
4. Lagre valgt modell i `models/` og bruk den i Streamlit-appen.

Se [data-feasibility-guiden](docs/data-feasibility.md) for første dataoppgave.

## Status

Dette er et prosjektskjelett. API-integrasjoner, valgt registreringspunkt og
modelltrening må implementeres når datakilder og prosjektavgrensning er låst.
