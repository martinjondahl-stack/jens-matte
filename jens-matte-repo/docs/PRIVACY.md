# Personvernnotat

JENS MATTE er designet for familie- og skolebruk med minst mulig persondata.

## Data som lagres

Når skyprogresjon er aktiv, lagres:

- fornavn eller kallenavn
- tilfeldig spiller-ID
- XP og nivå
- mestring per matematikkferdighet
- besvarte oppgaver, valgt alternativ, om hint ble brukt og svartid
- hasher av spillkoden og aktive økttokener

Appen ber ikke om e-post, telefonnummer, fødselsdato, adresse eller posisjon.

## Lokal modus

Uten database lagres profilen bare i nettleserens `localStorage`. Data kan fjernes ved å velge «Bytt spiller» eller ved å slette nettleserdata.

## Sletting

En synkronisert profil kan slettes fra profilsiden. Sletting fjerner spilleren og tilhørende runder, svar og ferdighetsdata fra databasen.

## Driftsansvar

Den som publiserer løsningen på Railway er behandlingsansvarlig for produksjonsdataene og bør begrense tilgang til Railway- og GitHub-kontoene.
