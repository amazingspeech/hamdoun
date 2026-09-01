#!/usr/bin/env node
// Bakt index.src.html (client-side {{ }}/<sc-for>-template, dc-runtime/React)
// naar een volledig statisch index.html: een headless Chromium laadt de
// pagina, wacht tot de client-side render klaar is, en de resulterende DOM
// wordt as-is weggeschreven. De <script>-tags blijven behouden, dus na
// uitlevering hydrateert de browser gewoon overheen — maar curl/crawlers
// zonder JS zien nu de echte tekst in plaats van {{ placeholders }}.
//
// Gebruik: node scripts/prerender-index.mjs
// Vereist: een lokale statische server die de repo-root serveert (voor
// relatieve assets als ./support.js, ./assets/vendor/react*.js).

import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const PORT = 8933;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
};

function startServer() {
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      try {
        const url = new URL(req.url, 'http://localhost');
        let p = normalize(decodeURIComponent(url.pathname));
        if (p === '/') p = '/index.src.html';
        const full = join(ROOT, p);
        if (!full.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
        const data = await readFile(full);
        res.writeHead(200, { 'Content-Type': MIME[extname(full)] || 'application/octet-stream' });
        res.end(data);
      } catch (e) {
        res.writeHead(404);
        res.end('not found');
      }
    });
    server.listen(PORT, '127.0.0.1', () => resolve(server));
  });
}

async function main() {
  const server = await startServer();
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const consoleErrors = [];
    page.on('pageerror', (err) => consoleErrors.push(String(err)));
    page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

    await page.goto(`http://127.0.0.1:${PORT}/index.src.html`, { waitUntil: 'networkidle' });

    // Wacht tot de client-side template volledig is uitgerenderd: geen
    // {{ }}-tokens meer in de DOM-tekst.
    await page.waitForFunction(() => !document.body.innerHTML.includes('{{ '), { timeout: 15000 });
    // Kleine marge voor eventuele microtask-vervolgrenders (sc-for chunks).
    await page.waitForTimeout(300);

    const remaining = await page.evaluate(() => document.body.innerHTML.includes('{{ '));
    if (remaining) throw new Error('Er staan nog {{ }}-tokens in de gerenderde DOM.');

    if (consoleErrors.length) {
      console.error('Console/page errors tijdens render:');
      for (const e of consoleErrors) console.error(' -', e);
      throw new Error(`${consoleErrors.length} console/page error(s) tijdens prerender — zie hierboven.`);
    }

    // tessar-concierge-widget.js en assets/tessar-prefs.js bouwen hun DOM
    // (chatwidget, cookiebanner) zelf op met document.body.appendChild(...),
    // zonder te checken of dat al eens gebeurd is. Die scripts blijven in de
    // gebakken output staan (nodig voor echte interactiviteit) en draaien dus
    // gewoon opnieuw bij een verse paginalaad — wat een duplicaat zou
    // opleveren als hun al-gerenderde markup mee gebakken wordt. Die markup
    // is bovendien pure runtime-UI, geen SEO-content, dus verwijderen voor
    // het bakken.
    const removedCount = await page.evaluate(() => {
      const selectors = ['.tsc-root', '.tsc-panel', '[role="dialog"][aria-label="Cookievoorkeuren"]'];
      let n = 0;
      for (const sel of selectors) {
        document.querySelectorAll(sel).forEach((el) => { el.remove(); n++; });
      }
      return n;
    });
    if (removedCount) console.error(`${removedCount} runtime-widget-element(en) verwijderd voor het bakken (chatwidget/cookiebanner).`);

    let html = await page.content();

    // dc-runtime laat soms zijn interne editor-encoding (sc-camel-kebab-case
    // i.p.v. echte camelCase, zie support.js's CAMEL_ATTR/__dcAnnotatedTemplate)
    // achter in geserialiseerde tekstinhoud die het niet als DOM-attribuut
    // aanraakt — met name raw SVG-data-URI's in CSS en losstaande JS-variabelen
    // in <script>-tags. Dat is altijd fout (de brontemplate bevat nooit
    // "sc-camel-"), dus dit wordt hier onvoorwaardelijk teruggedraaid.
    const camelFixes = [];
    html = html.replace(/sc-camel-([a-z0-9-]+)/g, (match, kebab) => {
      const camel = kebab.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
      camelFixes.push(`${match} -> ${camel}`);
      return camel;
    });
    if (camelFixes.length) {
      console.error(`${camelFixes.length} sc-camel-* artefact(en) teruggezet naar camelCase:`);
      for (const f of [...new Set(camelFixes)]) console.error(' -', f);
    }

    // Verifieer dat elk inline <script>-blok (zonder src) na deze fix nog
    // steeds geldige JS is — een silent SyntaxError in productie is erger
    // dan een gefaalde build.
    const scriptBodies = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
      .filter(([, openTag]) => !/\bsrc=/.test(openTag) && !/type=["'](?!text\/javascript)[^"']*["']/i.test(openTag))
      .map(([, , body]) => body)
      .filter((s) => s.trim());
    for (const body of scriptBodies) {
      try {
        new Function(body);
      } catch (e) {
        throw new Error(`Ongeldige JS in een inline <script> na bake: ${e.message}\n${body.slice(0, 200)}`);
      }
    }

    process.stdout.write(html);
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
