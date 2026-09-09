#!/usr/bin/env node
// Bakt index.src.html (client-side {{ }}/<sc-for>-template, dc-runtime/React)
// naar een volledig statisch index.html: een headless Chromium laadt de
// pagina, wacht tot de client-side render klaar is, en de resulterende DOM
// wordt weggeschreven. dc-runtime's <x-dc>-root bestaat op dat moment niet
// meer (dc-runtime heeft 'm zelf al vervangen door #dc-root), dus dc-runtime's
// eigen client-side hydratie-boot vindt in de browser nooit een <x-dc> terug
// en doet daarna niets meer - support.js en de React/ReactDOM-vendor-bundels
// zijn dus alleen nog nodig geweest om deze bake te draaien, niet voor de
// uitgeleverde pagina. Daarom worden die <script>-tags (plus de dc-runtime-
// editor-annotaties en de dubbel gebakken Tess-widget-stylesheet) hieronder
// uit de gerenderde DOM verwijderd voordat page.content() wordt uitgelezen.
// curl/crawlers zonder JS zien zo de echte tekst in plaats van
// {{ placeholders }}, en de browser downloadt geen dode runtime meer.
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

    // De header krijgt de class "scrolled-past-hero" (effen achtergrond)
    // pas via een scroll-listener zodra de bezoeker voorbij de hero-foto
    // scrollt. Die class hangt af van waar het prerender-script toevallig
    // stond op het moment van page.content() - een niet-deterministische
    // scroll-snapshot die nooit mee gebakken mag worden. Een verse paginalaad
    // start altijd bovenaan (scrollY 0), dus de juiste, gebakken standaard is
    // zonder deze class (transparante header over de foto); de JS zet 'm er
    // zelf weer bij zodra de bezoeker daadwerkelijk voorbij de hero scrolt.
    const hadScrolledClass = await page.evaluate(() => {
      const header = document.querySelector("header.scrolled-past-hero");
      if (!header) return false;
      header.classList.remove("scrolled-past-hero");
      return true;
    });
    if (hadScrolledClass) console.error("header.scrolled-past-hero-class verwijderd voor het bakken (scroll-afhankelijke staat, geen SEO-content).");

    // dc-runtime's <x-dc>-root wordt door dc-runtime zelf al vervangen door
    // #dc-root voordat deze pagina hier gerenderd wordt (zie parseDcDocument
    // in support.js: die zoekt naar <x-dc>, vindt 'm nooit meer terug in de
    // gebakken output, en stopt meteen). Met andere woorden: dc-runtime's
    // client-side hydratie draait in productie nooit - support.js en de
    // React/ReactDOM-vendor-bundels die het zelf inlaadt worden dus alleen
    // gedownload en geparsed, zonder ooit iets te doen. Diezelfde bake haalt
    // ook de 549 data-dc-tpl-editor-annotaties weg (dc-runtime's eigen
    // node-mapping voor het design-canvas, puur voor dat canvas relevant, geen
    // functionele/CSS-afhankelijkheid in de uitgeleverde pagina), de dubbel
    // gebakken Tess-widget-stylesheet (tessar-concierge-widget.js injecteert
    // zijn <style data-tessar-concierge> zelf, onvoorwaardelijk, bij elke
    // paginalaad - de gebakken kopie is dus altijd een duplicaat), en het
    // window.__resources-configuratieblok dat alleen bestond om support.js's
    // eigen dynamische CDN-scriptloader (react/react-dom) same-origin te laten
    // serveren - zonder support.js is dat blok eveneens dode configuratie.
    const deadRuntimeStats = await page.evaluate(() => {
      const deadScriptMarkers = ['support.js', 'react.production.min.js', 'react-dom.production.min.js'];
      let scriptsRemoved = 0;
      document.querySelectorAll('script[src]').forEach((el) => {
        if (deadScriptMarkers.some((marker) => el.getAttribute('src').includes(marker))) {
          el.remove();
          scriptsRemoved++;
        }
      });

      let resourcesConfigRemoved = 0;
      document.querySelectorAll('script:not([src])').forEach((el) => {
        if (el.textContent.includes('window.__resources')) {
          el.remove();
          resourcesConfigRemoved++;
        }
      });

      let dcTplAttrsRemoved = 0;
      document.querySelectorAll('[data-dc-tpl]').forEach((el) => {
        el.removeAttribute('data-dc-tpl');
        dcTplAttrsRemoved++;
      });

      let widgetStyleRemoved = 0;
      document.querySelectorAll('style[data-tessar-concierge]').forEach((el) => {
        el.remove();
        widgetStyleRemoved++;
      });

      return { scriptsRemoved, resourcesConfigRemoved, dcTplAttrsRemoved, widgetStyleRemoved };
    });
    console.error(
      `dc-runtime opgeruimd: ${deadRuntimeStats.scriptsRemoved} dode <script src>-tag(s), `
      + `${deadRuntimeStats.resourcesConfigRemoved} window.__resources-configuratieblok(ken), `
      + `${deadRuntimeStats.dcTplAttrsRemoved} data-dc-tpl-attribu(u)t(en), `
      + `${deadRuntimeStats.widgetStyleRemoved} gedupliceerd(e) Tess-widget-stylesheet(s).`
    );

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
