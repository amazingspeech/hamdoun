# Changelog

Bijhoudt van betekenisvolle wijzigingen aan de tessar.nl-codebase. Formaat losjes gebaseerd op [Keep a Changelog](https://keepachangelog.com/); nieuwste bovenaan.

## Ongepubliceerd (branch `css-consolidatie-fase3`)

### In uitvoering
- CSS-consolidatie fase 3: gedeelde `assets/tessar.css` voor de 13 Eleventy-pagina's, tokenbestand-tegenstrijdigheid oplossen. Plan: `docs/superpowers/plans/2026-09-14-css-consolidatie-fase3.md`.

## 2026-09-14/15

### Toegevoegd
- Partners-banner op de homepage ("Vertrouwd door"): logo's van Van Dijk Clinic en LouxLoux, direct onder de hero, met retina (1x/2x) varianten en hover-naar-kleur.
- `scripts/check-asset-refs.mjs` als onderdeel van `npm test` (uit Fase 2, gecommit 2026-09-09) — scant gebouwde pagina's op lokale asset-referenties die niet resolven.

### Gewijzigd
- JSON-LD-entiteiten (Organization/ProfessionalService) op 8 pagina's gekoppeld met een gedeelde `@id`, zodat zoekmachines ze als één bedrijf herkennen in plaats van losse entiteiten.
- Van Dijk Clinic-partnerlogo linkt naar `www.vandijkclinic.nl` (publieke site) i.p.v. het interne protocolchecker-subdomein.

### Opgeruimd
- 7 verweesde, al-gemergede lokale git-branches verwijderd (`add-blog-post-cover-images`, `blog-nav-and-style-consistency`, `blog-page-and-avg-copy-fix`, `contact-page-nav-fix`, `fix-mobile-nav-overflow`, `seo-brief-schema-v2`, `website-dark-mode`).

## 2026-09-09

### Fase 2 — Eleventy-migratie
- Alle 13 niet-homepage-pagina's gemigreerd van losse statische HTML naar Eleventy-templates met gedeelde includes (`_includes/base.njk`, `header.njk`, `footer-and-scripts.njk`).
- Deploy-workflow bouwt en synct nu vanuit `_site/` i.p.v. de repo-root.
- Kritieke bevindingen tijdens het traject gecorrigeerd: `preview/`-map (klantdata) beschermd tegen `rsync --delete`; `og-image.jpg` en logo-bestanden alsnog aan de passthrough-copy toegevoegd.

### Fase 1 — dode runtime gestript
- De homepage levert niet langer ~65KB dode React/dc-runtime-code uit (was gedownload en geparsed maar deed niets in productie).

## Eerder

Wijzigingen van vóór 2026-09-09 staan niet in dit bestand — zie `git log` voor de volledige geschiedenis.
