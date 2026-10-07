# AGENTS.md

## Prosjekt

Bergen Traffic Predictor predikerer trafikkvolum én time frem i tid for ett
trafikkregistreringspunkt i Bergen.

Primære datakilder:

- Statens vegvesen: historiske trafikkmålinger
- MET Norway / Frost: historiske værmålinger

Første versjon skal være avgrenset til ett målepunkt og timedata.

## Teknologi og struktur

Bruk Python som hovedspråk.

Forventet stack:

- pandas / numpy for dataarbeid
- scikit-learn for modeller og evaluering
- Streamlit for webappen
- pytest for tester

Anbefalt struktur:

```text
src/
  data/          # Nedlasting, validering og sammenslåing av rådata
  features/      # Feature engineering
  models/        # Trening, prediksjon og lagring av modeller
  evaluation/    # Metrikker, baselines og feilanalyse
app/             # Streamlit-app
tests/           # Tester
data/
  raw/           # Ikke versjonskontrollerte rådata
  processed/     # Genererte datasett
models/          # Genererte modellartefakter
```

## Viktige ML-regler

- Target er trafikkvolumet i neste time (`t + 1`).
- All splitting skal være kronologisk. Aldri bruk tilfeldig train/test-split for tidsserier.
- Testsettet skal representere en senere periode som modellen ikke har sett under trening eller tuning.
- Features for tidspunkt `t` kan bare bruke informasjon som faktisk var tilgjengelig ved `t`.
- Ikke bruk fremtidig observert vær som feature med mindre løsningen eksplisitt bruker værvarsel.
- Lag-features og rullerende statistikk må beregnes uten å inkludere nåværende eller fremtidige target-verdier.
- Bevar timestamp med tidssone gjennom hele pipelinen. Dokumenter valgt tidssone, normalt `Europe/Oslo`.
- Manglende observasjoner skal ikke fylles eller fjernes uten at valget er dokumentert.

## Modellering og evaluering

- Implementer minst én enkel baseline før ML-modeller:
  - trafikk samme time forrige uke
  - eventuelt historisk gjennomsnitt for samme time og ukedag
- Hovedmetrikken er MAE. Rapporter også RMSE ved behov.
- Sammenlign alltid modeller mot baseline på samme testperiode.
- Ikke velg modell basert på testsettet; bruk valideringsperiode eller tidsserie-kryssvalidering.
- Lag feilanalyse minst fordelt på time, ukedag og eventuelt værforhold.

## Data og reproduksjon

- Ikke commit API-nøkler, `.env`-filer, rådata, modellbinærer eller store genererte filer.
- Konfigurasjon som må endres mellom miljøer skal komme fra miljøvariabler eller en dokumentert konfigurasjonsfil.
- Lagring av datasett og modeller skal være reproduserbar fra kode og dokumenterte kommandoer.
- Hver datainnhenting bør lagre kilde, hentetidspunkt, tidsperiode og målepunkt-ID.

## Kodeprinsipper

- Skriv små, testbare funksjoner med typeannotasjoner der det er naturlig.
- Hold notebooker til utforskning; flytt gjenbrukbar logikk til `src/`.
- Ikke dupliser feature-logikk mellom trening og Streamlit-appen.
- Bruk stabile, beskrivende kolonnenavn og dokumenter enhetene, for eksempel kjøretøy per time og mm nedbør.
- Unngå skjulte sideeffekter ved import; nettverkskall og filskriving skal skje eksplisitt.

## Testing før endringer leveres

Kjør relevante kontroller før du avslutter:

```bash
pytest
```

Når prosjektet har avhengigheter og formatverktøy på plass, kjør også prosjektets definerte lint-, format- og testkommandoer.

## Dokumentasjon

Ved endringer som påvirker data, features, modell eller app, oppdater README med:

- hvordan løsningen kjøres
- datakilder og nødvendige miljøvariabler
- definisjon av target og features
- valgt tidsperiode og split
- baseline og evalueringsresultater
- kjente begrensninger
