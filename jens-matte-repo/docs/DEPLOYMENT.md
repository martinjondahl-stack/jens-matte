# Publisering med GitHub og Railway

## 1. Legg prosjektet i GitHub

1. Opprett et nytt, privat repository, for eksempel `jens-matte`.
2. Last opp alle filene i denne mappen, eller bruk Git fra Mac:

```bash
git init
git add .
git commit -m "Første versjon av JENS MATTE"
git branch -M main
git remote add origin <ADRESSEN-TIL-REPOSITORYET>
git push -u origin main
```

GitHub Actions-filen i `.github/workflows/ci.yml` validerer alle 500 oppgavene, kjører den semantiske auditen, typekontrollerer koden og bygger produksjonsversjonen.

## 2. Opprett Railway-prosjektet

1. Velg **New Project** i Railway.
2. Velg **Deploy from GitHub repo** og repositoryet `jens-matte`.
3. Legg til en PostgreSQL-tjeneste i samme Railway-prosjekt via **+ New → Database → PostgreSQL**.
4. Åpne app-tjenesten → **Variables** og opprett:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
PROFILE_CODE_PEPPER=<EN-LANG-TILFELDIG-HEMMELIGHET>
```

`Postgres` må være det faktiske navnet på databasetjenesten i Railway. Har den et annet navn, bruker du det navnet i referansen. Bruk minst 40 tilfeldige tegn i `PROFILE_CODE_PEPPER`, og ikke legg verdien i GitHub.

5. Start en ny deploy. Appens `start`-kommando kjører den idempotente databasemigreringen før Next.js starter.
6. Åpne app-tjenesten → **Settings → Networking → Public Networking → Generate Domain**.
7. Under **Settings → Deploy** kan du sette healthcheck path til `/api/health`.
8. Under GitHub/deploy-innstillingene bør **Wait for CI** slås på, slik at Railway bare deployer commits som har bestått GitHub Actions.

## 3. Kontroller produksjonen

Åpne disse adressene:

- `/` – spillet
- `/api/health` – skal vise `questions: 500`, `database: "ok"` og `ok: true`

Opprett en testspiller på iPhone, ta vare på spillkoden og hent samme spiller på Mac. Spill én runde på hver enhet og kontroller at XP og mestring følger profilen.

## Miljøvariabler

| Variabel | Påkrevd | Beskrivelse |
|---|---:|---|
| `DATABASE_URL` | For skyprogresjon | Referanse til Railway PostgreSQL, vanligvis `${{Postgres.DATABASE_URL}}` |
| `PROFILE_CODE_PEPPER` | Ja i produksjon | Hemmelig verdi brukt ved hashing av spillkode og økttoken |
| `PGSSLMODE` | Vanligvis nei | Sett `require` bare dersom den valgte tilkoblingen krever det |

## Oppdateringer

Når Railway er koblet til `main`, gir en ny push en ny deploy:

```bash
git add .
git commit -m "Forbedre oppgaver og forklaringer"
git push
```

Oppgavebanken er generert fra `scripts/generate_question_bank.py`. Endre generatoren, regenerer banken og kjør `npm test` før push.
