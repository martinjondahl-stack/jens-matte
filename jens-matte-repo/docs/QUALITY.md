# Kvalitet og faglig kontroll

## Oppgavebanken

Oppgavebanken inneholder 500 originale oppgaver for 5.–7. trinn. Den er organisert etter temaer og progresjon som er relevante for LK20, men prosjektet er ikke et offisielt produkt fra Utdanningsdirektoratet.

Hver oppgave har:

- fire svaralternativer og nøyaktig ett riktig svar
- et kort hint som ikke røper svaret
- målrettet tilbakemelding til hvert galt alternativ
- en utregning eller forklaring steg for steg
- klassetrinn, tema, ferdighet, nivå 1–10 og XP
- en enkel illustrasjon der en visuell modell gir faglig verdi

## Automatiske kontroller

Kjør:

```bash
npm run questions:validate
npm run questions:audit
```

`questions:validate` kontrollerer blant annet:

- nøyaktig 500 oppgaver og riktig temafordeling
- unike ID-er og oppgaver
- fire unike alternativer merket A–D
- gyldig fasit, hint, forklaring og feedback
- støttede illustrasjonstyper

`questions:audit` gjør en uavhengig semantisk kontroll av blant annet:

- svaralternativer som er skrevet forskjellig, men betyr det samme
- sirkeloppgaver mot den oppgitte verdien π ≈ 3,14
- sannsynlighetsoppgaver og samsvar med illustrasjonene
- ulikheter og åpne/lukkede endepunkter på tallinjer
- fleretappers fart–tid-oppgaver
- enkelte vanlige språkfeller i norsk oppgavetekst

Generatoren er deterministisk. `npm run questions:generate` skal derfor gi samme bank for samme seed. Etter generering skal både validering og audit kjøres på nytt.

## Før bred bruk

Matematikk, språk og grensesnitt er kontrollert systematisk, men en pilot med faktiske elever anbefales før bred bruk. Noter spesielt:

- oppgaver som oppleves uklare selv om fasiten er riktig
- feilalternativer som ingen velger, eller flere oppfatter som riktige
- illustrasjoner som blir for små på enkelte iPhone-modeller
- forklaringer som bruker ord eleven ikke kjenner
- nivåer som oppleves for lette eller for bratte

Slike observasjoner bør rettes i generatoren, ikke bare direkte i `data/questions.json`, slik at banken forblir reproduserbar.
