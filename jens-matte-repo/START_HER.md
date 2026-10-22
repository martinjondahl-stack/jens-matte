# Start her – få JENS MATTE på nett

Dette prosjektet er klart for **GitHub + Railway**.

## A. Legg koden i GitHub

1. Pakk ut ZIP-filen.
2. Opprett et nytt **privat** repository på GitHub med navnet `jens-matte`.
3. Last opp innholdet i den utpakkede mappen. Pass på at skjulte mapper som `.github` også blir med.
4. Vent til handlingen **Kvalitetssjekk** er grønn.

## B. Publiser i Railway

1. Opprett et nytt Railway-prosjekt og velg **Deploy from GitHub repo**.
2. Velg `jens-matte`.
3. Legg til **PostgreSQL** i samme prosjekt.
4. På web-tjenesten oppretter du variablene:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
PROFILE_CODE_PEPPER=<minst 40 tilfeldige tegn>
```

5. Deploy på nytt.
6. Lag et offentlig domene under **Settings → Networking → Generate Domain**.
7. Åpne `https://<ditt-domene>/api/health` og kontroller at du får:

```json
{
  "ok": true,
  "questions": 500,
  "database": "ok"
}
```

## C. Test synk mellom iPhone og Mac

1. Opprett en spiller på iPhone.
2. Ta vare på spillkoden som vises.
3. Spill én runde.
4. Åpne samme side på Mac og velg **Jeg har spillkode**.
5. Skriv samme navn og spillkode. XP og mestring skal følge profilen.

Mer detaljert hjelp ligger i [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
