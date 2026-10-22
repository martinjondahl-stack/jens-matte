# Oppgavebanken

`data/questions.json` inneholder 500 oppgaver fordelt slik:

| Tema | Antall |
|---|---:|
| Tall og regnearter | 70 |
| Brøk | 75 |
| Desimaltall | 50 |
| Prosent | 55 |
| Algebra og mønster | 50 |
| Geometri | 45 |
| Måling | 35 |
| Statistikk og sannsynlighet | 35 |
| Økonomi | 30 |
| Problemløsing | 55 |

Hver oppgave har klassetrinn, nivå 1–10, tema, ferdighet, type, spørsmål, hint, fire unike alternativer, fasit, målrettet feilfeedback, stegvis forklaring, XP og eventuelt en visuell spesifikasjon.

Kjør `npm run questions:validate` og `npm run questions:audit` før oppgavebanken pushes. Fordelingsrapporten ligger i `data/question-bank-report.json`, og den semantiske auditrapporten i `data/question-bank-audit.json`.
