#!/usr/bin/env node
// scripts/extract-shared-css.mjs
//
// Analyseert de {% block styles %}-inhoud van alle 13 Eleventy-pagina's en
// rapporteert per unieke, exact-identieke regeltekst op welke pagina's die
// voorkomt. Een @media/@keyframes-blok wordt als één ondeelbare top-level
// "regel" behandeld (via accolade-diepte-tracking), zodat geneste content
// nooit wordt afgekapt door een naive '}'-split.
//
// Gebruik: node scripts/extract-shared-css.mjs
// Output: twee secties naar stdout - "gedeeld" (regels die overal waar ze
// voorkomen byte-identiek zijn, dus veilig te centraliseren) en een lijst
// van welke pagina's elke regel bevatten, zodat een implementer kan zien
// of een regel conflicteert (zelfde selector, andere body op een andere
// pagina - zie het bekende a/a:hover-geval in dit plan) voordat hij 'm
// verplaatst.

import { readFile } from 'node:fs/promises';

const PAGES = [
  'privacy.html', 'services.html', 'chatbots.html', 'prijzen.html', 'contact.html',
  'blog.html', '404.html',
  'ai-telefonist-voor-bedrijf.html', 'ai-receptioniste-voor-bedrijven.html',
  'ai-chatbot-voor-bedrijven.html', 'workflow-automatisering-met-ai.html',
  'ai-implementatie-laten-uitvoeren.html', 'bedrijfsprocessen-automatiseren-met-ai.html',
];

function splitTopLevelRules(css) {
  const rules = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < css.length; i++) {
    const ch = css[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) {
        rules.push(css.slice(start, i + 1).trim());
        start = i + 1;
      }
    }
  }
  return rules.filter(Boolean);
}

async function main() {
  const ruleToPages = new Map();

  for (const page of PAGES) {
    const content = await readFile(page, 'utf-8');
    const match = content.match(/\{% block styles %\}([\s\S]*?)\{% endblock %\}/);
    if (!match) throw new Error(`${page}: geen {% block styles %} gevonden`);
    const rules = splitTopLevelRules(match[1]);
    for (const rule of rules) {
      const norm = rule.replace(/\s+/g, ' ').trim();
      if (!ruleToPages.has(norm)) ruleToPages.set(norm, new Set());
      ruleToPages.get(norm).add(page);
    }
  }

  const entries = [...ruleToPages.entries()].sort((a, b) => b[1].size - a[1].size);

  console.log(`# ${entries.length} unieke regel-teksten gevonden over ${PAGES.length} pagina's\n`);
  for (const [rule, pages] of entries) {
    const pageList = [...pages].sort();
    console.log(`[${pageList.length}/${PAGES.length}: ${pageList.join(', ')}]`);
    console.log(rule);
    console.log();
  }
}

main();
