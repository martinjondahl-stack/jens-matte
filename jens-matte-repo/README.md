# JENS MATTE – 5.–7.

Et mobilvennlig og adaptivt mattespill for 5.–7. trinn, laget med Next.js, TypeScript og PostgreSQL.

Spillet inneholder:

- 500 originale multiple-choice-oppgaver fordelt på 10 temaer
- 264 oppgaver med enkle, responsive matematikkillustrasjoner
- målrettet tilbakemelding for hvert gale svar
- forklaringer steg for steg
- 10 oppgaver per runde, uten tidspress
- XP, streak og adaptivt nivå 1–10 per ferdighet
- lokal lagring når databasen ikke er tilgjengelig
- skyprogresjon på tvers av iPhone og Mac når PostgreSQL er koblet til
- spillkode i stedet for e-post og passord

> Oppgavebanken er originalt innhold laget for dette prosjektet. Den er strukturert med utgangspunkt i temaer og progresjon i LK20, men er ikke utgitt eller godkjent av Utdanningsdirektoratet.

## Publiser først

Følg [START_HER.md](START_HER.md) for en kort GitHub + Railway-oppskrift, eller [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for alle detaljene.

## Kom raskt i gang lokalt

Krav: Node.js 22 og Python 3.

```bash
npm install
cp .env.example .env.local
npm run dev
```

Åpne `http://localhost:3000`. Uten `DATABASE_URL` kjører spillet i lokal modus og lagrer profilen i nettleseren.

## Kvalitetssikre oppgavebanken

```bash
npm run questions:generate
npm run questions:validate
npm run questions:audit
npm test
```

Generatoren er deterministisk. Samme seed gir samme bank, slik at endringer kan vurderes tydelig i Git. Se [docs/QUALITY.md](docs/QUALITY.md) for innholdskontroll og pilotplan.

## Prosjektstruktur

```text
app/                    Next.js-sider og API-ruter
components/             Spillgrensesnitt og SVG-illustrasjoner
data/questions.json     De 500 oppgavene
lib/                    Adaptiv utvelgelse, poeng og databasekode
migrations/             PostgreSQL-skjema
scripts/                Generator, validator og migrering
```

## Deploy

Se [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for GitHub + Railway-oppsett.

## Personvern

Appen trenger bare fornavn eller kallenavn. Den ber ikke om e-post, telefonnummer, fødselsdato eller posisjon. Se [docs/PRIVACY.md](docs/PRIVACY.md).

## Lisens

Programkoden er MIT-lisensiert. Oppgavebanken kan fritt brukes og videreutvikles som del av dette prosjektet.
