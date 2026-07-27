# Fase 4 — SaaS Foundation: architectuur en beslissingen

Vastgelegd op 2026-07-26. Dit document is het resultaat van een architectuur-
onderzoek plus een beslissingsronde met de opdrachtgever — de negen open
vragen uit het onderzoek zijn allemaal beantwoord (zie "Beslissingen"
hieronder). **Nog niet gebouwd.** Dit is de blauwdruk voor wanneer dat wél
gebeurt, zodat een toekomstige lezer (mens of AI) niet opnieuw hoeft te
onderzoeken wat hier al is uitgezocht en besloten.

## Kernbevinding

Er bestaat in de huidige codebase **geen enkel** eigenaarschap-concept over
een `store_id`. Elke geldige API-key mag vandaag elke winkel opvragen die in
het geladen modelartefact voorkomt (`serving/app.py`). Klantisolatie is dus
niet iets verzwakken dat er al staat — het is een mechanisme dat volledig van
de grond af moet worden toegevoegd.

## Beslissingen

| # | Vraag | Beslissing |
|---|---|---|
| 1 | Self-service signup of handmatig? | **Handmatig.** Een organisatie zonder gekoppelde winkeldata is toch een lege huls; self-service is pas zinvol met een eigen data-onboardingsflow, die niet in scope is. |
| 2 | Certo-klanten hergebruiken of gescheiden? | **Volledig gescheiden** identity, geen gedeeld gebruikersbestand met Certo. |
| 3 | Prijsmodel? | **Flat-fee per organisatie**, geen usage-metering. Geen metering-tabel nodig in iteratie 1. |
| 4 | Eén gedeeld model of per-organisatie getraind? | **Eén gedeeld, globaal model.** Isolatie zit volledig in toegangscontrole (welk `store_id` mag een org opvragen), niet in gescheiden training. |
| 5 | Verwachte schaal? | **~10 klanten, een paar winkels elk.** |
| 6 | Database-engine? | **SQLite.** Op deze schaal is het single-writer-nadeel geen probleem; de query-laag wordt vanaf stap 0 portable opgezet (zie hieronder) zodat een latere overstap naar Postgres een migratie-run is, geen herontwerp. |
| 7 | Mailprovider voor wachtwoord-reset? | **Bestaat nog niet, moet vanaf nul opgezet worden.** Blokkeert concreet Stap 4 hieronder — niet de rest van het plan. |
| 8 | Wie gebruikt de login? | **Een volwaardig klantdashboard** waar klanten zelf inloggen. "Enterprise" hier = professionele kwaliteit/uitstraling (Stripe/Linear-niveau), expliciet **geen** SSO/RBAC. |
| 9 | Data-retentie bij opzegging? | **Hard verwijderen** (AVG-vereiste), geen soft-delete. Zie implicatie hieronder. |

### Implicatie van beslissing 9 voor het datamodel

Een organisatie verwijderen moet **cascade-delete** zijn: gebruikers,
winkels, api_keys, sessies en wachtwoord-reset-tokens ruimen mee op in
dezelfde transactie. Geen orphaned rows, geen soft-delete-vlaggen.

## Database-aanpak (SQLite als bewuste, tijdelijke brug)

Gebruik een query-laag die niet SQLite-specifiek is (bv. SQLAlchemy Core,
geen zware ORM — consistent met de bestaande stijl van platte functies in
`security/api_keys.py`) plus Alembic-migraties. Concrete triggers om alsnog
naar Postgres te gaan, net zo expliciet gedocumenteerd als de bestaande
"per-instance rate limiting"-beperking in `KNOWN-LIMITATIONS.md`:
1. Een tweede horizontaal geschaalde API-instance wordt nodig.
2. Een klant eist contractueel database-niveau-isolatie (Row-Level Security).
3. Schrijfconcurrentie wordt merkbaar.
4. Operationeel gemak om op dezelfde Postgres-server als Certo aan te sluiten.

## Datamodel

Het bestaande `models/<versie>/`-artefact-mechanisme (`training/artifact.py`)
blijft **ongewijzigd** — de database komt ernaast als toegangslaag.

| Tabel | Kernvelden | Doel |
|---|---|---|
| `organisaties` | id, naam, slug, actief | De klant/tenant. |
| `gebruikers` | id, organisatie_id (FK), email, wachtwoord_hash/salt, rol | Login-accounts — zelfde PBKDF2-HMAC-SHA256, 600.000 iteraties als `security/api_keys.py` nu al gebruikt. |
| `sessies` | token_hash, gebruiker_id (FK), verloopt_op | Server-side sessiestaat, HttpOnly-cookie. |
| `wachtwoord_reset_tokens` | token_hash, verloopt_op, gebruikt_op | Single-use, verlopend, gehasht. |
| `winkels` | id, organisatie_id (FK), extern_store_id, naam | **De cruciale koppeltabel**: welke winkel hoort bij welke organisatie. |
| `api_keys` | id, organisatie_id (FK), hash, salt, verlopen_op | Vervangt `api_keys.json` — hergebruikt exact dezelfde hash-functies, alleen de opslaglaag verandert. |

## Klantisolatie: afdwingen en testen

Elke query die tenant-eigen data ophaalt krijgt `organisatie_id` als
verplicht, niet-optioneel parameter — geen functie die zonder tenant-scope
kán worden aangeroepen (zelfde "geen stille default voor iets
veiligheidskritisch"-reflex als `serving/config.py`).

Concreet voor `/forecast`: `vereis_api_key()` levert straks key-naam +
organisatie_id; vóór `voorspel_periode(...)` een lookup in `winkels` of het
gevraagde `store_id` bij die organisatie hoort. Bij een mismatch: **404, niet
403** — een 403 zou bevestigen "dit store_id bestaat, is alleen niet van
jou", wat andermans store-ID's enumereerbaar maakt.

Getest via `tests/test_tenant_isolatie.py`: het scenario org A + winkel 1 +
eigen key, org B + winkel 2 + eigen key, alle vier kruislingse combinaties
getoetst, plus een check dat een geweigerde cross-tenant-poging ook in de
audit-log met het juiste `organisatie_id` terechtkomt.

## Stappenplan

Elke stap is op zichzelf shipbaar en testbaar — geen big-bang-migratie.

0. **✅ Database-fundament, geen gedragsverandering — gedaan 2026-07-26.**
   Schema voor organisaties + winkels in `db/schema.py` (SQLAlchemy Core,
   SQLite), bootstrap-functie in `db/bootstrap.py`, en een operator-CLI
   (`python3 -m db.cli --models-dir models --model-version <versie>
   --organisatie-naam ... --organisatie-slug ...`) die alle store-ID's uit
   een modelartefact aan één organisatie koppelt. Nog geen Alembic —
   bewust uitgesteld tot de eerste echte schemawijziging na Stap 0 (zie
   `db/schema.py`'s docstring); `create_all()` volstaat voor de allereerste
   tabellen. **Nog niet gewijzigd:** `serving/app.py` gebruikt deze database
   nog niet — de API is functioneel ongewijzigd, precies zoals bedoeld.
   Getest via TDD (`tests/test_db_schema.py`, `tests/test_db_bootstrap.py`,
   `tests/test_db_cli.py`), 96/96 tests groen.
1. **✅ API-keys naar de database, zelfde gedrag — gedaan 2026-07-26.**
   `api_keys`-tabel in `db/schema.py` (organisatie_id, naam, hash, salt,
   verlopen_op, actief). `db/api_keys.py` bevat `migreer_bestaande_key()`
   die alleen al-gehashte waarden overzet (nooit een ruwe key opnieuw
   hashen). `db/migreer_keys_cli.py` migreert een echte `api_keys.json`
   naar één organisatie (op slug): `python3 -m db.migreer_keys_cli
   --api-keys-json api_keys.json --database-pad tenants.db
   --organisatie-slug <slug>`. **Nog niet gewijzigd:** `serving/app.py`
   leest nog steeds `api_keys.json`, niet de database — bewust, want Stap 2
   is expliciet de eerste stap die gedrag verandert, niet Stap 1. Getest
   via TDD (`tests/test_db_api_keys.py`, `tests/test_db_migreer_keys_cli.py`),
   99/99 tests groen.
2. **✅ Klantisolatie daadwerkelijk afdwingen — gedaan 2026-07-26.**
   `serving/app.py` leest nu de database (`db_api_keys.vind_organisatie_voor_key`)
   in plaats van `api_keys.json`, en checkt vóór elke `/forecast`-aanroep
   via `db_winkels.hoort_store_bij_organisatie()` of het gevraagde
   `store_id` bij de organisatie van de key hoort — bij een mismatch 404
   (nooit 403, zie boven), en dat wordt net als een geslaagd verzoek in de
   audit-log gezet (met `organisatie_id`) zodat probeerpogingen op
   andermans winkels zichtbaar zijn. `api_keys.json` blijft vooralsnog
   vereist door `serving/config.py` (bewust nog niet opgeruimd). Getest
   via `tests/test_tenant_isolatie.py` (het letterlijke org-A/org-B-
   kruisscenario) plus een bijgewerkte `tests/test_app.py`-fixture — 112/112
   tests groen. Live gedemonstreerd: de lokale demo-server draait nu op
   deze code, met de echte klant ("Tessar demo") en alle 1115 winkels
   gebootstrapt via `db.cli` + `db.migreer_keys_cli`.
3. **✅ Accounts + login/sessiebeheer — gedaan 2026-07-27.**
   `gebruikers`- en `sessies`-tabellen in `db/schema.py`. `db/gebruikers.py`
   hergebruikt `security.api_keys.hash_key()`/`verifieer_key()` voor
   wachtwoorden (zelfde PBKDF2-HMAC-SHA256, geen tweede hashformaat);
   `verifieer_inloggegevens()` lekt nooit of een e-mailadres bestaat (fout
   wachtwoord en onbekend e-mailadres geven allebei `None`). `db/sessies.py`
   hasht sessietokens met SHA-256, niet PBKDF2 — bewust, want een
   `secrets.token_urlsafe`-token is al hoge-entropie, geen mensgekozen
   geheim. Nog steeds geen self-service-registratie (beslissing 1) —
   gebruikers worden handmatig aangemaakt via `db/gebruikers_cli.py`
   (`python3 -m db.gebruikers_cli --database-pad tenants.db
   --organisatie-slug <slug> --email ... --wachtwoord ...`), zelfde patroon
   als `db/migreer_keys_cli.py`. HTTP-laag in `serving/app.py`: `POST
   /login` (zet een HttpOnly-sessiecookie, `Secure`-vlag via de nieuwe
   `SESSIE_COOKIE_SECURE`-instelling — standaard aan, net als
   `EXPOSE_API_DOCS` standaard uit staat, expliciete opt-out i.p.v.
   impliciete onveilige default), `POST /logout` (verwijdert de sessie
   server-side), `GET /me` (bevestigt dat een sessie geldig is — nodig om
   de hele flow end-to-end te kunnen testen en voor toekomstig
   dashboardgebruik). `/login` deelt dezelfde rate-limit-instelling als
   `/forecast`, maar per bron-IP (er is nog geen API-key op het moment van
   inloggen) — bescherming tegen wachtwoord-bruteforcing. Getest via TDD
   (`tests/test_db_schema.py`, `tests/test_db_gebruikers.py`,
   `tests/test_db_sessies.py`, `tests/test_db_gebruikers_cli.py`,
   `tests/test_config.py`, `tests/test_schemas.py`, `tests/test_login.py`),
   133/133 tests groen, ruff schoon.
4. **Wachtwoord-resetflow.** Geblokkeerd op beslissing 7 (mailprovider moet
   nog gekozen/opgezet worden).
5. **✅ Meerdere gebruikers per organisatie — gedaan 2026-07-27.**
   Rolonderscheid (eigenaar/lid) wordt nu daadwerkelijk afgedwongen, niet
   meer alleen een inert kolomveld. `POST /gebruikers` (alleen bereikbaar
   voor een ingelogde `eigenaar` — `vereis_eigenaar()`, 403 bij een `lid`,
   401 zonder sessie) maakt een nieuwe gebruiker aan in de eigen
   organisatie van de aanroeper, altijd met rol `lid` — een tweede eigenaar
   toevoegen kan bewust alleen via `db/gebruikers_cli.py` (operator-
   handeling), om privilege-escalatie via dit endpoint uit te sluiten. Een
   dubbel e-mailadres geeft 409, niet een 500 (`gebruikers.email` had al
   een unique-constraint uit Stap 3, nu voor het eerst via de API
   bereikbaar). `GET /gebruikers` toont de teamlijst, org-scoped, voor elke
   ingelogde gebruiker (eigenaar én lid). `vereis_sessie()` geeft nu een
   `GeauthenticeerdeGebruiker`-NamedTuple terug (gebruiker_id,
   organisatie_id, rol, email) in plaats van alleen een id — zelfde patroon
   als `GeauthenticeerdeKey` bij de API-key-auth — zodat `/me` en de nieuwe
   endpoints niet elk apart de gebruikersrij hoeven op te zoeken. Getest via
   `tests/test_gebruikers_endpoint.py` (eigenaar mag, lid mag niet, geen
   sessie geeft 401, dubbel e-mailadres geeft 409, teamlijst blijft
   org-gescheiden tussen twee klanten). 142/142 tests groen, ruff schoon.
6. **✅ Zelfbediening van API-keys — gedaan 2026-07-27.**
   `db/api_keys.py`: `maak_api_key()` genereert een ruwe key
   (`vk_`-prefix + `secrets.token_urlsafe(32)`), hasht 'm met dezelfde
   `security.api_keys.hash_key()` als altijd, en geeft `(id, ruwe_key)`
   terug — de ruwe waarde wordt precies één keer getoond. `lijst_api_keys()`
   geeft alleen id/naam/actief/aangemaakt_op terug, nooit hash/salt.
   `deactiveer_api_key()` is org-gescoped (geeft `False` terug bij een
   andermans key-id, geen exception). HTTP-laag, alle drie eigenaar-only
   via `vereis_eigenaar`: `POST /api-keys` (201, geeft de ruwe key eenmalig
   terug), `GET /api-keys` (lijst, nooit de ruwe waarde), `DELETE
   /api-keys/{id}` (204, of 404 bij andermans key — zelfde
   enumeratie-preventie-redenering als bij store_id). Nieuwe zelfbediende
   keys werken meteen voor `/forecast`/`/metrics`-auth, exact dezelfde
   verificatiepad als een gemigreerde key. UI op `team.html`: een
   eigenaar-only kaart om keys aan te maken (ruwe waarde in een
   kopieerbare monospace-regel, met expliciete "wordt niet nog een keer
   getoond"-waarschuwing) en in te trekken. Twee echte CSS-bugs gevonden
   en gefixt tijdens het bouwen: `.kaart`/`.aanbeveling` (elk met een eigen
   `display`-regel) overschreven telkens het `hidden`-attribuut — opgelost
   met één generieke `[hidden] { display:none !important; }` in plaats van
   per component te patchen. Getest via `tests/test_db_api_keys.py` en
   `tests/test_api_keys_endpoint.py` (eigenaar mag, lid mag niet (403),
   geen sessie geeft 401, nieuwe key werkt voor forecast-auth, lijst nooit
   hash/salt, andermans key intrekken geeft 404). 158/158 tests groen,
   ruff schoon. Live geverifieerd: key aanmaken, tonen, intrekken, status
   wisselt naar "Ingetrokken".
7. **Rate limiting per organisatie.** Pas relevant zodra een organisatie
   meerdere keys deelt.
8. **Postgres-migratie (voorwaardelijk).** Alleen bij een van de triggers
   hierboven — dankzij het portable schema een migratie-run, geen herontwerp.

## Wat niet te bouwen in de eerste iteratie

- Granulaire RBAC/permissiematrix — twee rollen (eigenaar/lid) volstaan.
- SSO/OAuth/SAML en 2FA — bevestigd door beslissing 8.
- Self-service org-signup — bevestigd door beslissing 1.
- Per-organisatie modeltraining — bevestigd door beslissing 4.
- Horizontale schaal / gedeelde rate-limit-state.
- Billing-integratie (Stripe e.d.) — flat-fee (beslissing 3) heeft dit nu niet nodig.
- Zware ORM-laag.

## Volgende stap

Stap 0 hierboven is de eerste uitvoerbare taak zodra hiermee begonnen wordt —
vraag het expliciet na vóór je start, dit document legt alleen de beslissingen
vast, het is geen startsignaal.
