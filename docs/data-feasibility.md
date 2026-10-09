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

## Bygg komplett trafikkdatasett

Bruk Traffic Data API for flerårige timeverdier. Nedlasteren følger API-ets
paginering automatisk; dere trenger derfor ikke å eksportere manuelt fra
portalen.

For Danmarks plass (`14630V805616`) og perioden 2022–2025 er dette den
anbefalte kommandoen fra prosjektroten:

```bash
make refresh-traffic
```

Den tilsvarer følgende API-kall:

```bash
python3 -m scripts.download_traffic_data \
  --point-id 14630V805616 \
  --from 2022-01-01T00:00:00+01:00 \
  --to 2026-01-01T00:00:00+01:00 \
  --output data/raw/traffic_2022_2025.csv
```

Kommandoen lagrer den rå CSV-filen og hentemetadata i `data/raw/`. Deretter
bygges det normaliserte datasettet. For Danmarks plass skal `--allow-gaps`
brukes, siden punktet har dokumenterte målegap:

```bash
python3 -m scripts.prepare_traffic_dataset \
  data/raw/traffic_2022_2025.csv \
  --allow-gaps
```

Ved behov kan `prepare_traffic_dataset` fortsatt kombinere flere eksportfiler:

```text
data/raw/traffic_2022.csv
data/raw/traffic_2023.csv
data/raw/traffic_2024.csv
data/raw/traffic_2025.csv
```

Kommandoen stopper dersom eksporten inneholder ugyldige rader, dupliserte
tidspunkter eller manglende timer, også i overgangen mellom filer. Ved suksess skriver den
`data/processed/traffic_hourly.csv` og en sidecar-fil med kildefilens SHA-256,
kvalitetsrapport og kolonnenavn. Begge filene er genererte artefakter og skal
ikke committes.

### Dokumentert håndtering av målegap

For Danmarks plass inneholder API-dataene to målegap: 4.–7. juni 2022 og
2.–18. oktober 2024. De skal ikke fylles eller slettes. Bygg i stedet en
komplett timeakse med ukjent trafikkvolum som manglende verdi:

```bash
python3 -m scripts.prepare_traffic_dataset \
  data/raw/traffic_2022_2025.csv \
  --allow-gaps
```

Da kan senere feature-kode ekskludere rader der en nødvendig lag-feature eller
target mangler, uten at den flytter observasjoner over et målegap.
