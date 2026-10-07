# Data feasibility

Målet er å bekrefte at minst ett trafikkregistreringspunkt i Bergen har en
sammenhengende og brukbar timebasert serie før vi bygger hele datapipelinen.

## Avgrensning

Bruk ett målepunkt, `Felt = Totalt` og én måned, for eksempel januar 2025.
Dette er nok til å kontrollere eksportformatet, datakvaliteten og døgnmønsteret
uten å bruke tid på en flerårig datahenting.

## Hent data

1. Åpne [Trafikkdataportalen](https://trafikkdata.atlas.vegvesen.no/eksport).
2. Søk etter et punkt i Bergen, og velg et punkt med tydelig trafikkvolum.
3. Velg en hel måned i 2025 og tidsoppløsning **timetrafikk**.
4. Last ned CSV-filen til `data/raw/traffic_feasibility.csv`.
5. Noter punktets ID, navn, vegreferanse og valgt periode i issue eller PR.

Ikke legg den nedlastede CSV-filen i Git; `data/raw/` er ignorert.

## Valider eksporten

Etter installasjon av avhengighetene, kjør:

```bash
python3 -m scripts.check_traffic_export data/raw/traffic_feasibility.csv
```

Resultatet er **GO** når eksporten minst inneholder 28 døgn, minst 95 % gyldige
rader og ingen dupliserte tidspunkter. Ved **REVIEW** velger dere et annet
punkt eller undersøker manglende timer før dere går videre.

Kontroller også manuelt at:

- tidsserien har ett observasjonspunkt per time
- trafikkvolumet er ikke-negativt
- det finnes et plausibelt morgen- og/eller ettermiddagsrush
- dere bruker raden `Felt = Totalt`, ikke én enkelt kjøreretning

## Værdata etter godkjent trafikkserie

Frost krever en `FROST_CLIENT_ID` og henter observasjoner med stasjon,
referansetidsrom og elementer. Start med temperatur, nedbør og vindhastighet,
men sjekk først at den valgte værstasjonen dekker samme periode som
trafikkserien.
