# Tessar publieke MCP-server (`/mcp`) — design

**Status:** goedgekeurd door gebruiker (brainstorming-sessie 2026-09-01), klaar voor implementatieplan.

## Context

De terminologie/SEO-opdracht voor tessar.nl (zie `docs/superpowers/plans/` en de bijbehorende commits op branch `seo-terminologie-afstemming`) veronderstelde een publieke, read-only MCP-server op `/mcp` (met `/mcp/health`) die al zou bestaan met zes tools. Onderzoek wees uit dat deze server nergens bestaat (`/mcp` en `/mcp/health` geven 404 op de live site) — de opdracht ging uit van een verkeerde aanname over het project (TanStack Start/React SSR, terwijl tessar.nl grotendeels statische HTML is). Dit document ontwerpt de server vanaf nul.

## Waarom dit iets nieuws is (niet nog een pagina)

De bestaande website is bedoeld voor menselijke bezoekers (en zoekmachine-crawlers) die HTML-pagina's bekijken. Een MCP-server is geen pagina — het is een programmatisch loket specifiek voor AI-assistenten/-agents, die er gestructureerde vragen aan kunnen stellen ("wat kost pakket X?") en gestructureerde antwoorden voor terugkrijgen, in plaats van HTML te moeten scrapen. Niemand navigeert er in een browser naartoe; het heeft geen visuele laag.

## Bestaande conventies (leidend voor dit ontwerp)

Onderzocht via SSH op de Hetzner-server (`157.90.244.24`, gebruiker `job`, compose-project in `/home/job/tessar/`):

- `contact-api` en `auth-api` zijn allebei kale **Python 3.11**-services: `http.server.BaseHTTPRequestHandler`/`ThreadingHTTPServer` uit de standaardbibliotheek, één `server.py`, geen externe dependencies, gebouwd via een simpel `Dockerfile` (`FROM python:3.11-slim`).
- Bron van elke service leeft **direct op de server** (`/home/job/tessar/<service>-src/`), niet in de `hamdoun`-git-repo. Dit ontwerp volgt die conventie voor de MCP-server (`mcp-server-src/`) in plaats van 'm nu te veranderen.
- Caddy (`/home/job/tessar/Caddyfile`) routeert per pad binnen het `tessar.nl`-blok: `@contact path /api/contact` → `reverse_proxy contact-api:8421`, `@auth path /api/auth/*` → `reverse_proxy auth-api:8422`. Statische site-bestanden komen uit `/var/www/tessar` (read-only gemount als `/srv/tessar-site`).
- Compose-stack (`docker-compose.yml`) is eigendom van `job`, gedeeld met andere projecten op dezelfde server (n8n, protocolwijzer/Certo) — wijzigingen hier raken die niet, maar vereisen wel zorgvuldigheid bij het herstarten van de stack.

## Architectuur

- **Taal & protocol-implementatie**: Python 3.11 + de officiële `mcp`-PyPI-SDK. Enige uitzondering op de "geen dependencies"-conventie van de andere services, bewust gekozen omdat het MCP-protocol (JSON-RPC, sessiebeheer, Streamable HTTP-transport) te foutgevoelig is om met de hand te bouwen; de SDK garandeert protocolcorrectheid.
- **Transport**: MCP Streamable HTTP, luisterend op poort 8423 binnen de container.
- **Container**: nieuwe compose-service `mcp-server`, gebouwd uit `./mcp-server-src` (eigen `Dockerfile`, zelfde stijl als `contact-api-src`).
- **Contentbron**: de container mount `/var/www/tessar` **read-only** (dezelfde live site-bestanden die Caddy serveert) — geen aparte databron om te synchroniseren; de server leest altijd wat er daadwerkelijk live staat.
- **Routing**: Caddyfile krijgt `@mcp path /mcp /mcp/*` → `reverse_proxy mcp-server:8423`, naast de bestaande `/api/*`-blokken.
- **Health check**: `/mcp/health` → simpele 200 met JSON-status (bijv. `{"status": "ok"}`), voor monitoring en om de opdracht-eis aantoonbaar te maken.

## Tools (4, geen 6 — geen bestaande tools om intact te houden)

1. **`list_pages()`** — geen argumenten. Retourneert alle 13 echte contentpagina's (de 12 uit `sitemap.xml` plus `privacy.html`, exclusief het Google-verificatiebestand) als lijst van `{path, title, description}`.
2. **`get_page(path)`** — retourneert `{path, title, description, content}`; `content` is de leestekst van de pagina, geëxtraheerd met stdlib `html.parser` (tags/scripts/styles gestript). Onbekend pad → nette MCP-foutmelding, geen crash.
3. **`search(query)`** — eenvoudige case-insensitive zoekopdracht over title/description/leestekst van alle pagina's. Retourneert lijst van `{path, title, snippet}` per match. Geen treffers → lege lijst (geen fout). Geen zware zoekindex nodig voor een site van deze omvang.
4. **`get_pricing()`** — retourneert gestructureerde pakketten/prijzen. Bron: expliciete `data-mcp-*`-attributen die worden toegevoegd aan de bestaande prijzenblokken in `prijzen.html` (bijv. `data-mcp-tier`, `data-mcp-price`) — geen visuele wijziging aan de pagina. Gekozen boven CSS-classes/structuur parsen omdat dat laatste **stil** breekt (verkeerde of lege data zonder foutmelding) als de pagina ooit herontworpen wordt; met expliciete markeringen geeft de server een duidelijke fout als ze ontbreken, in plaats van foute data te tonen.

## Testen

- Python `unittest` (stdlib) voor de HTML-parsing- en zoeklogica.
- Vóór deploy: een handmatig testscript dat alle 4 tools via een echte MCP-client aanroept tegen een lokaal gestarte instance van de server.

## Bewust buiten scope van dit ontwerp

- Schrijf-operaties (contactformulier etc. blijven bij de bestaande `contact-api`/`auth-api`) — deze server is strikt read-only.
- Versiebeheer voor `mcp-server-src` in de `hamdoun`-repo (volgt de bestaande, ongeversioneerde server-side-conventie van de andere backend-services).
- Per-sector use-case-cijfers en een eventueel nieuw blogartikel (aparte, nog openstaande punten uit de terminologie/SEO-opdracht, niet gerelateerd aan de MCP-server).
