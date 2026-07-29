# Hard-delete cascade bij opzegging

**Status:** approved design, not yet implemented
**Date:** 2026-07-29
**Context:** `FASE4-SAAS-FOUNDATION.md`, beslissing 9 (data-retentie bij opzegging), legt vast: "Hard verwijderen (AVG-vereiste), geen soft-delete." Alleen de eerste helft daarvan is gebouwd — `POST /webhooks/stripe` deactiveert een organisatie (`organisaties.actief = false`) zodra Stripe `customer.subscription.deleted` meldt, maar de daadwerkelijke, definitieve verwijdering is bewust nog niet gebouwd: een geannuleerd abonnement kan tijdens Stripe's eigen betaalretry-cyclus soms alsnog herstellen, en onomkeerbaar verwijderen op basis van één webhook-event zou daar geen ruimte voor geven. Dit document werkt die tweede, nog ontbrekende helft uit.

## Problem

Een gedeactiveerde organisatie blijft voor onbepaalde tijd met alle klantdata in de database staan — gebruikers, winkels, geüploade verkoopdata, API-keys, sessies. Dat is geen tijdelijke overgangstoestand meer zodra een opzegging definitief is, maar een AVG-verplichting die nog openstaat.

## Goal

Dertig dagen na deactivering (ruim voorbij Stripe's eigen betaalretry-cyclus) verwijdert een dagelijkse achtergrondtaak de organisatie en alle bijbehorende data definitief, in één transactie, zonder handmatig ingrijpen.

## Explicitly out of scope

- **Reactivatie van een gedeactiveerde organisatie.** Er bestaat vandaag al geen enkel codepad dat `organisaties.actief` ooit weer op `true` zet — dat is een bestaand, los gat, niet iets wat deze taak oplost. De dertig dagen wachttijd is dus in de praktijk een venster waarin een mens (de operator) het handmatig kan rechtzetten, geen geautomatiseerd hersteltraject.
- **De audit-log** (`security/audit.py`). Eén gedeeld, append-only logbestand voor alle organisaties samen. **Correctie (finale review):** dit bevat niet alleen metadata — `serving/app.py` schrijft op minstens twee plekken een e-mailadres rechtstreeks in een audit-log-entry: `"key": eigenaar.email` (winkeltoewijzing-endpoint) en `"gebruiker": gebruiker.email` (`/voorbeeld/forecast`). E-mailadressen zijn directe persoonsgegevens, en die overleven de hard-delete cascade in dit document onbeperkt lang — dit is een bekend, niet door deze taak opgelost restgat (zie `KNOWN-LIMITATIONS.md`). Technisch onpraktisch om één organisatie er middenin uit te knippen zonder het hele bestand te herschrijven, en gangbaar om beveiligingslogs een eigen, kortere bewaartermijn te geven los van de verwijderplicht op klantdata zelf — maar dat is een keuze die nog los, expliciet gemaakt moet worden, niet iets dat al klopt op basis van "bevat toch geen persoonsgegevens".
- **Boekhoudkundige/fiscale bewaarplicht.** De `organisaties`-rij (incl. `stripe_customer_id`/`stripe_subscription_id`) wordt volledig verwijderd, geen geanonimiseerde rest. Facturatiegeschiedenis blijft toch al bij Stripe zelf bestaan, met een eigen bewaarplicht — hier hoeft niets dubbel bewaard te worden.
- **Wijziging van de webhook-handler zelf**, buiten het toevoegen van een tijdstempel. Het moment en de voorwaarde waarop een organisatie gedeactiveerd wordt blijven ongewijzigd.

## Architecture

Drie onderdelen, in afhankelijkheidsvolgorde:

1. **`gedeactiveerd_op`-kolom** op `organisaties` (nullable DateTime). `deactiveer_organisatie()` zet deze bij het `customer.subscription.deleted`-webhookevent, naast de bestaande `actief=False`.
2. **`verwijder_organisatie()`** in `db/organisaties.py` — de daadwerkelijke cascade-delete, één transactie, expliciete SQLAlchemy Core-deletes in afhankelijkheidsvolgorde (kind-tabellen eerst): `sessies` en `wachtwoord_reset_tokens` (via de gebruikers van deze org), `gebruiker_winkels`, `api_keys`, `eigen_verkoopdata`, `eigen_product_verkoopdata`, `winkels`, `gebruikers`, dan `aanmeldingen.organisatie_id` op NULL, en tot slot de `organisaties`-rij zelf.
3. **`db/opschonen_cli.py`** — een cron-script (zelfde patroon als `serving/herbestel_email_cli.py`) dat organisaties zoekt met `actief=False AND gedeactiveerd_op < nu - 30 dagen`, en `verwijder_organisatie()` per stuk aanroept.

Geen wijziging aan de webhook-handler zelf buiten het zetten van `gedeactiveerd_op` — de deactivering blijft precies zoals nu, alleen nu met een tijdstempel eraan. Geen database-cascade (`ON DELETE CASCADE`): explicite, plain SQLAlchemy Core-functies passen bij de bestaande stijl van de rest van `db/` (`db/gebruikers.py`, `db/api_keys.py`), en vermijden de SQLite-specifieke complicaties van FK-cascade (`PRAGMA foreign_keys`, tabel-herbouw voor bestaande kolommen).

## Components

**`db/schema.py`** — één nieuwe kolom: `Column("gedeactiveerd_op", DateTime, nullable=True)` op `organisaties`. Bestaande databases krijgen 'm automatisch via het al-aanwezige `_migreer_ontbrekende_kolommen()`-mechanisme, geen aparte migratiestap nodig.

**`db/organisaties.py`**
- `deactiveer_organisatie()` — uitgebreid: zet nu ook `gedeactiveerd_op=nu` naast `actief=False`.
- `verwijder_organisatie(engine, organisatie_id)` — nieuw. Eén transactie, verwijdert in volgorde: `sessies`/`wachtwoord_reset_tokens` (via een subquery op `gebruikers.organisatie_id`), `gebruiker_winkels` (via `gebruikers` of `winkels`), `api_keys`, `eigen_verkoopdata`, `eigen_product_verkoopdata`, `winkels`, `gebruikers`, zet `aanmeldingen.organisatie_id=NULL` waar van toepassing, en tot slot de `organisaties`-rij zelf.
- `haal_te_verwijderen_organisaties(engine, nu, wachtdagen=30)` — nieuw. Query-helper: `actief=False AND gedeactiveerd_op IS NOT NULL AND gedeactiveerd_op < nu - wachtdagen`. Los van `verwijder_organisatie()` gehouden zodat de cron-selectielogica apart testbaar is van de delete zelf.

**`db/opschonen_cli.py`** — nieuw, zelfde vorm als `serving/herbestel_email_cli.py`: geen argumenten, leest de standaard `.env`-instellingen, loopt `haal_te_verwijderen_organisaties()` langs, roept per organisatie `verwijder_organisatie()` aan, logt naar stdout (via cron-redirect naar een logfile, zelfde patroon) alleen `organisatie_id` + tijdstip — nooit naam/e-mail, want dat is precies de data die net verwijderd wordt.

**`deploy/DEPLOY.md`** — nieuwe cron-regel naast de bestaande herbestel-mail-regel, dagelijks (niet wekelijks zoals herbestel — een verwijdering hoeft niet wekenlang na de 30 dagen te blijven hangen).

## Data flow

1. Stripe stuurt `customer.subscription.deleted` → webhook zet `actief=False` én `gedeactiveerd_op=nu` op de organisatie (ongewijzigd gedrag, plus de tijdstempel).
2. Elke dag draait de cron `db/opschonen_cli.py` → haalt organisaties op met `actief=False` en `gedeactiveerd_op` ouder dan 30 dagen.
3. Voor elke gevonden organisatie: `verwijder_organisatie()` in één transactie — alle scoped data weg, organisatie-rij weg.
4. Niets in de bestaande login/toegangscontrole-paden verandert — die controleren nu al op `actief`, en een verwijderde organisatie geeft daar automatisch hetzelfde resultaat als een gedeactiveerde (organisatie bestaat niet meer → `is_actief()` geeft `False` terug via het bestaande "onbekend `organisatie_id` → False"-gedrag).

## Error handling

- **Transactie-atomiciteit**: als een stap in `verwijder_organisatie()` faalt, rolt de hele transactie terug — geen halfverwijderde organisatie. De cron-loop vangt een fout per organisatie op (log + door naar de volgende), zodat één probleemgeval niet de hele nachtelijke sweep blokkeert.
- **Race met een late webhook-retry**: als Stripe tóch nog een laat `checkout.session.completed` voor een inmiddels verwijderde organisatie aflevert (zeer onwaarschijnlijk binnen 30 dagen, maar niet uit te sluiten) — de webhook-handler zoekt dan een `organisatie_id` dat niet meer bestaat en behandelt dat al net zo als "onbekend" (bestaand gedrag, geen wijziging nodig).
- **Geen reactivatie-pad**: zoals hierboven genoemd bestaat er nu al geen enkele manier om een gedeactiveerde organisatie weer actief te zetten (bewust buiten scope van deze taak) — de 30-dagenwachttijd is dus praktisch een mens-kan-het-nog-handmatig-rechtzetten-venster, niet een geautomatiseerd hersteltraject.

## Testing

**Backend, TDD zoals gebruikelijk:**
- `tests/test_db_organisaties.py` — uitgebreid: `deactiveer_organisatie()` zet nu ook `gedeactiveerd_op`; nieuwe tests voor `verwijder_organisatie()` (alle betrokken tabellen zijn leeg na aanroep, `organisaties`-rij zelf is weg, `aanmeldingen.organisatie_id` is NULL i.p.v. de rij te verwijderen, en — het belangrijkste isolatie-scenario — data van een **andere** organisatie blijft volledig intact); en tests voor `haal_te_verwijderen_organisaties()` (een net-gedeactiveerde org verschijnt niet, een 30+ dagen geleden gedeactiveerde org wel, een nog-actieve org nooit, een org zonder `gedeactiveerd_op` — kan niet meer voorkomen na deze wijziging, maar defensief getest — wordt genegeerd in plaats van een crash te geven).
- `tests/test_opschonen_cli.py` — nieuw: de cron-entrypoint roept `verwijder_organisatie()` aan voor elke gevonden organisatie, logt alleen `organisatie_id`/tijdstip (geen naam/e-mail in de output), en een fout bij één organisatie stopt de sweep niet voor de rest.

Geen frontend-wijzigingen in deze taak — dit is een achtergrondproces.
