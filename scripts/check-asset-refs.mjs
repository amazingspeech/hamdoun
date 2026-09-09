#!/usr/bin/env node
// scripts/check-asset-refs.mjs
//
// Pragmatische, regex-gebaseerde check die na een build (npm run build &&
// npm run build:site) elk lokaal/relatief bestand dat de gebouwde pagina's
// in _site/ refereren (src="...", href="...", srcset="...") probeert te
// vinden op de plek waar het naartoe verwijst. Rapporteert elke ontbrekende
// referentie plus de pagina(s) die ernaar verwijzen, en sluit af met
// exit-code 1 als er iets ontbreekt.
//
// Dit bestaat om de klasse bug uit finding C1 van de final-review-report
// (.superpowers/sdd/2026-09-09-eleventy-migratie-fase2/final-review-report.md)
// te vangen: og-image.jpg werd door meerdere pagina's gerefereerd, maar
// ontbrak in _site/ omdat .eleventy.js er geen addPassthroughCopy voor had.
// Elke eerdere verificatie in deze migratie vergeleek pagina-HTML met
// pagina-HTML; niets controleerde of de bestandenset die _site/ (en dus de
// server) bereikt nog een superset is van wat de pagina's daadwerkelijk
// refereren. Dit script is die ontbrekende controle.
//
// Bewust GEEN volwaardige HTML-parser en GEEN algemene link-checker: het
// doel is "overduidelijk ontbrekend gerefereerd bestand" vangen, niet elke
// mogelijke referentie (JS-strings, inline SVG, CSS url(), externe links,
// etc.) uitputtend valideren.
//
// Gebruik: node scripts/check-asset-refs.mjs
// Vereist dat _site/ al gebouwd is (npm run build && npm run build:site).

import { readdirSync, statSync, existsSync, readFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");
const siteDir = join(repoRoot, "_site");

if (!existsSync(siteDir)) {
  console.error(
    "check-asset-refs: _site/ bestaat niet. Draai eerst `npm run build && npm run build:site`."
  );
  process.exit(1);
}

// Alle .html-bestanden in _site/ vinden (recursief, voor het geval er ooit
// submappen bijkomen; vandaag is alles plat).
function findHtmlFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      out.push(...findHtmlFiles(full));
    } else if (entry.endsWith(".html")) {
      out.push(full);
    }
  }
  return out;
}

// Eén src="...", href="..." of srcset="..." attribuutwaarde ontleden tot
// een lijst van kandidaat-URL's (srcset kan meerdere, komma-gescheiden
// "url breedte-descriptor"-paren bevatten).
function splitAttrValue(attr, value) {
  if (attr === "srcset") {
    return value
      .split(",")
      .map((part) => part.trim().split(/\s+/)[0])
      .filter(Boolean);
  }
  return [value];
}

// Eigen domeinen: og:image/twitter:image en dergelijke wijzen op tessar.nl
// vrijwel altijd naar een absolute https://tessar.nl/...-URL, niet naar een
// relatief pad (dat is precies hoe og-image.jpg in finding C1 gerefereerd
// werd). Zo'n zelf-referentie is voor deze check net zo lokaal als
// "./og-image.jpg", alleen de domeinprefix moet eraf.
const SITE_ORIGINS = ["https://tessar.nl", "http://tessar.nl"];

// Beslist of een referentie het soort "lokaal bestand op deze server" is dat
// we willen checken, en geeft zo ja het pad terug zoals het t.o.v. de
// pagina (voor relatieve refs) of t.o.v. de site-root (voor eigen-domein-
// absolute refs) gecontroleerd moet worden. Sluit uit: externe URL's naar
// andere domeinen, protocol-relative // naar andere domeinen, pure
// fragment-anchors (#foo), mailto:/tel:, en overige root-absolute paden
// (/login e.d., dat zijn routes op de server die niet door deze build
// worden geproduceerd, geen statische bestanden in _site/).
function classifyRef(raw) {
  if (!raw) return null;
  if (raw.startsWith("#")) return null;
  if (raw.startsWith("mailto:") || raw.startsWith("tel:")) return null;
  for (const origin of SITE_ORIGINS) {
    if (raw.startsWith(origin + "/")) {
      return { kind: "site-root", path: raw.slice(origin.length) };
    }
    if (raw === origin) {
      return { kind: "site-root", path: "/" };
    }
  }
  if (raw.startsWith("http://") || raw.startsWith("https://")) return null;
  if (raw.startsWith("//")) return null;
  if (raw.startsWith("/")) return null; // root-absolute route op een ander deel van de server
  return { kind: "relative", path: raw };
}

// Query-string en fragment van een pad afknippen, zodat
// "./tessar-concierge-widget.js?v=4" resolvet naar het bestand zonder de
// querystring, en "./contact.html#stuur-bericht" naar contact.html.
function stripQueryAndFragment(ref) {
  return ref.split("#")[0].split("?")[0];
}

const attrRegex = /\b(src|href|srcset)="([^"]*)"/g;
// Alleen deze twee meta-velden refereren een asset via `content=`
// (og:image/twitter:image); de rest van `content=` is titel/beschrijving/
// configuratietekst, geen bestandsverwijzing, en zou als kandidaat-pad
// alleen valse missers opleveren.
const metaTagRegex = /<meta\s+[^>]*>/g;
const metaNameOrPropertyRegex = /\b(?:name|property)="([^"]*)"/;
const metaContentRegex = /\bcontent="([^"]*)"/;
const ASSET_META_FIELDS = new Set(["og:image", "twitter:image", "twitter:image:src"]);

const htmlFiles = findHtmlFiles(siteDir);
// Map: ontbrekend-bestand-relatief-pad -> Set van pagina's (relatief pad
// t.o.v. _site/) die ernaar verwijzen.
const missing = new Map();
let totalChecked = 0;

function recordCandidate(htmlFile, pageRel, candidate) {
  const classified = classifyRef(candidate);
  if (!classified) return;
  const cleaned = stripQueryAndFragment(classified.path);
  if (!cleaned || cleaned === "/") return;
  totalChecked += 1;
  const resolved =
    classified.kind === "site-root"
      ? resolve(siteDir, "." + cleaned)
      : resolve(dirname(htmlFile), cleaned);
  if (!existsSync(resolved)) {
    const key = resolved.slice(siteDir.length + 1);
    if (!missing.has(key)) missing.set(key, new Set());
    missing.get(key).add(pageRel);
  }
}

for (const htmlFile of htmlFiles) {
  const pageRel = htmlFile.slice(siteDir.length + 1);
  const html = readFileSync(htmlFile, "utf8");

  let match;
  attrRegex.lastIndex = 0;
  while ((match = attrRegex.exec(html)) !== null) {
    const [, attr, rawValue] = match;
    for (const candidate of splitAttrValue(attr, rawValue)) {
      recordCandidate(htmlFile, pageRel, candidate);
    }
  }

  let metaMatch;
  metaTagRegex.lastIndex = 0;
  while ((metaMatch = metaTagRegex.exec(html)) !== null) {
    const tag = metaMatch[0];
    const nameMatch = tag.match(metaNameOrPropertyRegex);
    const contentMatch = tag.match(metaContentRegex);
    if (!nameMatch || !contentMatch) continue;
    if (!ASSET_META_FIELDS.has(nameMatch[1])) continue;
    recordCandidate(htmlFile, pageRel, contentMatch[1]);
  }
}

console.log(
  `check-asset-refs: ${htmlFiles.length} HTML-bestand(en) gescand, ${totalChecked} lokale referenties gecontroleerd.`
);

if (missing.size === 0) {
  console.log("check-asset-refs: alle referenties resolven binnen _site/. OK.");
  process.exit(0);
}

console.error(
  `check-asset-refs: ${missing.size} ontbrekend(e) bestand(en) gevonden:\n`
);
for (const [file, pages] of missing) {
  console.error(`  _site/${file}`);
  for (const page of pages) {
    console.error(`    gerefereerd door: ${page}`);
  }
}
process.exit(1);
