# Deel 4 (Formatteer goedgekeurd conceptartikel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new n8n workflow ("Deel 4") that turns an approved conceptartikel into paste-ready HTML and e-mails it, and fix Deel 3's existing e-mail formatter which currently drops bold text and lists.

**Architecture:** One new, well-tested JS module (`n8n-workflows/src/format-article-html.js`) holds the shared markdown→HTML logic and two thin e-mail-wrapper functions (one per workflow's e-mail style). Its logic gets embedded — not imported — into two separate n8n Code-node `jsCode` strings, because n8n Code nodes cannot `require()` local files; the module is the single tested source of truth, the embed step is a mechanical, verified copy. All workflow changes go through the n8n REST API (`https://n8n.tessar.nl/api/v1`), the same way every fix in this system has been made so far — GET the current workflow, edit the JSON in memory, PUT it back, then GET again to verify.

**Tech Stack:** n8n (self-hosted, workflow-as-JSON via its REST API), plain Node.js (`node:assert`, no test framework, matching the existing `n8n-workflows/src/*.test.js` convention), Python 3 for JSON construction/API calls (matching this session's established pattern), curl.

## Global Constraints

- Repo: `/Users/hamdeco/development/hamdoun`, branch `deel4-formatteer-goedgekeurd-concept-design` (already created; continue on it, don't create a new one).
- n8n API base: `https://n8n.tessar.nl/api/v1`. Auth header: `X-N8N-API-KEY: <value>`, value lives in `/Users/hamdeco/development/hamdoun/.env` as `N8N_API_KEY` — `source .env` before every curl call, never print or log the key itself.
- Deel 3 workflow ID: `Vv3niLLmxvet5ORD`. Do not touch any node in Deel 3 other than "Bouw e-mail met conceptartikelen" (Task 3) and the "Update status naar 'concept klaar'" regression fix (Task 1) — no other node, connection, or credential in Deel 3 changes.
- Spreadsheet ID: `1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0`. "Content briefs" tab gid: `210428761`. In any Google Sheets node's `sheetName` field with `mode: "list"`, the `value` MUST be the bare JSON number `210428761` — not a string, not prefixed with `"gid="`. Both other forms fail silently or fall back to the wrong tab with no error (discovered the hard way earlier this session).
- Google Sheets OAuth2 credential: id `OqN22aXOGK3lLPnS`, name "Google Sheets account". Gmail OAuth2 credential: id `A8raSb8NMOkgmEgX`, name "Gmail account". Use these exact id/name pairs whenever a task calls for attaching a credential — never invent or guess a credential id.
- The new Deel 4 workflow must be created **inactive**, and **no credentials attached to any of its nodes** — the user wires those up manually in the n8n UI afterward. This is a deliberate difference from how Deel 3's credentials are already attached.
- No automated test-execution of any live n8n workflow via the API (no `POST /workflows/{id}/run` equivalent, no triggering an execution). The user tests manually in the n8n UI himself. Verification in this plan means "GET the workflow back and inspect its JSON structure," never "run it and check the output."
- Every PUT to an existing workflow must be built from a **fresh GET performed in the same task** — never reuse a JSON file fetched in an earlier task or an earlier session. State drifts (a node fixed earlier this session was found reverted by the time planning started — see Task 1) and a stale base will silently undo other people's or your own prior fixes.
- `n8n-workflows/src/format-article-html.test.js` must be run with plain `node n8n-workflows/src/format-article-html.test.js` (no test framework is installed in this repo) and must print `OK: format-article-html tests passed` and exit 0.

---

## Note on one deliberate deviation from the design spec

The spec ([2026-08-10-deel4-formatteer-goedgekeurd-concept-design.md](../specs/2026-08-10-deel4-formatteer-goedgekeurd-concept-design.md)) lists "Formatteer HTML" and "Bouw e-mail" as two separate Code nodes. While writing this plan, mirroring Deel 3's actual proven topology turned out cleaner: Deel 3 does formatting *inside* its single "Bouw e-mail met conceptartikelen" node — there's no standalone node that only formats and hands off a `formatted_html` field to something else. Deel 4 follows the same shape: one Code node does both jobs. Splitting them would add a node with no consumer of the intermediate value. If this is reviewed and disagreed with, splitting back into two nodes is a five-minute change to Task 4. Everything else in the spec is implemented as written.

---

## Task 1: Fix the "Update status naar 'concept klaar'" regression in Deel 3

This node was already fixed once earlier this session (its `sheetName.value` was changed from the string `"Content briefs"` to the bare number `210428761`), but a fresh check while writing this plan shows it has reverted to the broken string value — most likely from the user re-selecting the sheet in the n8n UI while testing. This blocks Deel 3 from working correctly right now (it's the same "Sheet with ID Content briefs not found" bug reported earlier in this conversation) and must be fixed before Task 3 touches the neighboring e-mail node, so that a fresh GET in Task 3 doesn't accidentally re-embed the broken value into its own base copy.

**Files:** none (API-only change, no repo files touched)

**Interfaces:**
- Consumes: `N8N_API_KEY` from `.env`, workflow ID `Vv3niLLmxvet5ORD`, gid `210428761` (Global Constraints)
- Produces: nothing later tasks import — this is a standalone correctness fix, verified independently

- [ ] **Step 1: Confirm the regression is still present**

```bash
cd /Users/hamdeco/development/hamdoun
set -a; source .env; set +a
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "https://n8n.tessar.nl/api/v1/workflows/Vv3niLLmxvet5ORD" -o /tmp/deel4-plan-t1-before.json -w "HTTP_STATUS:%{http_code}\n"
python3 -c "
import json
with open('/tmp/deel4-plan-t1-before.json') as f:
    wf = json.load(f)
node = next(n for n in wf['nodes'] if n['name'] == \"Update status naar 'concept klaar'\")
print(json.dumps(node['parameters']['sheetName'], indent=2))
"
```

Expected: `HTTP_STATUS:200`, and the printed `sheetName` shows `"value": "Content briefs"` (the broken string form) — confirming the regression. If it already shows `"value": 210428761`, someone fixed it already; skip to Step 4 with no change needed.

- [ ] **Step 2: Patch the node and build the PUT payload**

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t1-before.json') as f:
    wf = json.load(f)

node = next(n for n in wf['nodes'] if n['name'] == \"Update status naar 'concept klaar'\")
node['parameters']['sheetName'] = {
    '__rl': True,
    'value': 210428761,
    'mode': 'list',
    'cachedResultName': 'Content briefs',
    'cachedResultUrl': 'https://docs.google.com/spreadsheets/d/1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0/edit#gid=210428761',
}

payload = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': {'executionOrder': 'v1'},
}
with open('/tmp/deel4-plan-t1-payload.json', 'w') as f:
    json.dump(payload, f)
print('payload written')
"
```

Expected: prints `payload written`, no traceback.

- [ ] **Step 3: PUT the fix**

```bash
cd /Users/hamdeco/development/hamdoun
set -a; source .env; set +a
curl -s -X PUT \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  --data @/tmp/deel4-plan-t1-payload.json \
  "https://n8n.tessar.nl/api/v1/workflows/Vv3niLLmxvet5ORD" \
  -o /tmp/deel4-plan-t1-after.json -w "HTTP_STATUS:%{http_code}\n"
```

Expected: `HTTP_STATUS:200`.

- [ ] **Step 4: Verify the fix and that nothing else moved**

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t1-after.json') as f:
    wf = json.load(f)
node = next(n for n in wf['nodes'] if n['name'] == \"Update status naar 'concept klaar'\")
assert node['parameters']['sheetName']['value'] == 210428761, 'sheetName still broken'
assert node['credentials']['googleSheetsOAuth2Api']['id'] == 'OqN22aXOGK3lLPnS', 'credential lost'
assert wf['active'] == False, 'workflow got activated unexpectedly'
assert len(wf['nodes']) == 12, f\"expected 12 nodes, got {len(wf['nodes'])}\"
print('OK: Task 1 verified')
"
```

Expected: prints `OK: Task 1 verified`, no `AssertionError`.

---

## Task 2: Write and test the shared markdown→HTML module

**Files:**
- Create: `n8n-workflows/src/format-article-html.js`
- Create: `n8n-workflows/src/format-article-html.test.js`

**Interfaces:**
- Produces (used by Task 3 and Task 4 as the source of truth to embed):
  - `escapeHtml(str: string): string`
  - `markdownToHtml(md: string): string` — converts `#`/`##` headings, `**bold**` (including inline within paragraphs and list items), `- item` bullet lists, and `1. item` numbered lists into real HTML (`<h1>`, `<h2>`, `<strong>`, `<ul><li>`, `<ol><li>`, `<p>`). Everything else becomes a `<p>` with `<br>` for single line breaks. All raw input is HTML-escaped first — no injection risk from LLM output.
  - `buildDraftReviewEmailHtml(items: Array<{keyword, content_type, draft_markdown, editor_notes}>): string` — Deel 3's e-mail body (banner reads "klaar voor review", includes a "Redactie-checklist" box per item).
  - `buildFormattedArticleEmailHtml(items: Array<{keyword, content_type, draft_markdown}>): string` — Deel 4's e-mail body (banner reads "klaar om te plakken", no checklist box).

- [ ] **Step 1: Write the failing test**

Create `n8n-workflows/src/format-article-html.test.js`:

```js
const assert = require('node:assert');
const {
  markdownToHtml,
  buildDraftReviewEmailHtml,
  buildFormattedArticleEmailHtml,
} = require('./format-article-html');

// Representative sample: mirrors the real shape Deel 3 produces (H1, H2, a
// bullet list, a numbered list with bold lead-ins, and an FAQ-style
// bold-question-then-answer paragraph) — this exact shape is what broke the
// old #/## -only converter (bold and list markers were left as literal
// asterisks/dashes in the e-mail).
const sampleMarkdown = `# AI Oplossingen voor Bedrijven: Slim Automatiseren met Tessar

Als mkb-ondernemer hoor je overal dat AI je bedrijf kan veranderen.

## Wat zijn AI oplossingen voor bedrijven?

AI oplossingen voor bedrijven zijn systemen die taken overnemen:

- Een telefoontje aannemen en er direct iets mee doen.
- Een afspraak inplannen zonder tussenkomst.
- Een terugkerende klantvraag beantwoorden.

Zo pakken we implementatie doorgaans aan:

1. **Kennismaking en behoefte in kaart brengen.** We bespreken je processen.
2. **Voorstel op maat.** We bepalen welke oplossing past.

**Is een AI-oplossing wel geschikt voor een klein bedrijf?**
Ja. Juist kleinere bedrijven kunnen veel winnen.`;

const html = markdownToHtml(sampleMarkdown);

assert.ok(html.includes('<h1') && html.includes('AI Oplossingen voor Bedrijven: Slim Automatiseren met Tessar'), 'renders # as a real h1');
assert.ok(html.includes('<h2') && html.includes('Wat zijn AI oplossingen voor bedrijven?'), 'renders ## as a real h2');

assert.ok(html.includes('<ul'), 'bullet list becomes a real <ul>');
assert.ok(html.includes('<li>Een telefoontje aannemen en er direct iets mee doen.</li>'), 'each bullet becomes its own <li>, dash stripped');
assert.ok(!html.includes('- Een telefoontje'), 'no leftover literal dash bullet syntax');

assert.ok(html.includes('<ol'), 'numbered list becomes a real <ol>');
assert.ok(html.includes('<strong>Kennismaking en behoefte in kaart brengen.</strong>'), 'bold lead-in inside a numbered item is converted');
assert.ok(!/>\s*1\.\s/.test(html), 'no leftover literal "1." numbering text (the browser renders <ol> numbering itself)');

assert.ok(html.includes('<strong>Is een AI-oplossing wel geschikt voor een klein bedrijf?</strong>'), 'FAQ-style bold question is converted');
assert.ok(html.includes('Ja. Juist kleinere bedrijven kunnen veel winnen.'), 'FAQ answer text is preserved');

assert.ok(!html.includes('**'), 'no leftover markdown bold markers anywhere in the output');

// Security: draft_markdown comes from an LLM and must never let raw HTML through.
const unsafe = markdownToHtml('<script>alert(1)</script>\n\nSome **bold** text.');
assert.ok(!unsafe.includes('<script>alert'), 'HTML in the input is escaped, not passed through');
assert.ok(unsafe.includes('&lt;script&gt;'), 'escaped script tag is visible as text, not executable markup');
assert.ok(unsafe.includes('<strong>bold</strong>'), 'bold still converts correctly alongside escaped content');

// Email wrapper functions
const items = [{
  keyword: 'AI oplossingen voor bedrijven',
  content_type: 'dienstenpagina',
  draft_markdown: sampleMarkdown,
  editor_notes: 'Check de prijsindicatie.',
}];

const reviewHtml = buildDraftReviewEmailHtml(items);
assert.ok(reviewHtml.includes('klaar voor review'), 'draft-review email uses the review-stage heading');
assert.ok(reviewHtml.includes('Redactie-checklist'), 'draft-review email includes the editor checklist section');
assert.ok(reviewHtml.includes('Check de prijsindicatie.'), 'draft-review email renders editor_notes');
assert.ok(reviewHtml.includes('#00BCD8') && reviewHtml.includes('#0091CE'), 'draft-review email uses the Tessar gradient');
assert.ok(reviewHtml.includes('<ul') && reviewHtml.includes('<strong>'), 'draft-review email uses the fixed markdownToHtml (bold + lists render)');

const formattedHtml = buildFormattedArticleEmailHtml(items);
assert.ok(formattedHtml.includes('klaar om te plakken'), 'formatted-article email uses the paste-ready heading');
assert.ok(!formattedHtml.includes('Redactie-checklist'), 'formatted-article email omits the editor checklist (already reviewed by this point)');
assert.ok(formattedHtml.includes('<h1') && formattedHtml.includes('<ul') && formattedHtml.includes('<ol'), 'formatted-article email includes the fully formatted HTML body');

console.log('OK: format-article-html tests passed');
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/hamdeco/development/hamdoun
node n8n-workflows/src/format-article-html.test.js
```

Expected: `Error: Cannot find module './format-article-html'` (the module doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `n8n-workflows/src/format-article-html.js`:

```js
const FONT_SANS = "'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif";
const FONT_MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";
const COLOR = {
  text: '#0C121A',
  textDim: '#555A53',
  border: '#E3E1DD',
  panel: '#F9F8F5',
  accent: '#006894',
  onGradient: '#001A2E',
  gradientStart: '#00BCD8',
  gradientEnd: '#0091CE',
};

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Applies to text that has ALREADY been through escapeHtml.
function inlineMarkdown(escapedText) {
  return escapedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function markdownToHtml(md) {
  const lines = escapeHtml(md).split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === '') {
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      blocks.push({ type: 'h1', text: line.slice(2) });
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', text: line.slice(3) });
      i++;
      continue;
    }
    if (/^-\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^-\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^-\s+/, ''));
        i++;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }

    // Plain paragraph: collect consecutive non-blank, non-special lines.
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('# ') &&
      !lines[i].startsWith('## ') &&
      !/^-\s+/.test(lines[i]) &&
      !/^\d+\.\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push({ type: 'p', text: paraLines.join('\n') });
  }

  return blocks
    .map((block) => {
      if (block.type === 'h1') {
        return `<h1 style="font-family:${FONT_SANS}; font-size:22px; color:${COLOR.text}; margin:20px 0 10px;">${inlineMarkdown(block.text)}</h1>`;
      }
      if (block.type === 'h2') {
        return `<h2 style="font-family:${FONT_SANS}; font-size:17px; color:${COLOR.accent}; margin:18px 0 8px;">${inlineMarkdown(block.text)}</h2>`;
      }
      if (block.type === 'ul') {
        const items = block.items.map((it) => `<li style="margin:0 0 4px;">${inlineMarkdown(it)}</li>`).join('');
        return `<ul style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px; padding-left:20px;">${items}</ul>`;
      }
      if (block.type === 'ol') {
        const items = block.items.map((it) => `<li style="margin:0 0 4px;">${inlineMarkdown(it)}</li>`).join('');
        return `<ol style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px; padding-left:20px;">${items}</ol>`;
      }
      return `<p style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px;">${inlineMarkdown(block.text).replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}

function buildDraftReviewEmailHtml(items) {
  let html = `<div style="font-family:${FONT_SANS}; max-width:680px; margin:0 auto; background-color:#FFFFFF;">`;
  html += `<div style="background-image:linear-gradient(135deg, ${COLOR.gradientStart}, ${COLOR.gradientEnd}); padding:28px 24px; border-radius:0 0 12px 12px;">`;
  html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:${COLOR.onGradient}; opacity:0.7; margin:0 0 6px;">Tessar &middot; Conceptartikelen</div>`;
  html += `<div style="font-family:${FONT_SANS}; font-size:20px; font-weight:600; color:${COLOR.onGradient};">${items.length} nieuw${items.length === 1 ? '' : 'e'} conceptartikel${items.length === 1 ? '' : 'en'} klaar voor review</div>`;
  html += `</div>`;

  for (const item of items) {
    html += `<div style="padding:20px 24px; border-bottom:1px solid ${COLOR.border};">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:11px; color:${COLOR.textDim}; text-transform:uppercase; margin-bottom:6px;">${escapeHtml(item.keyword)} &middot; ${escapeHtml(item.content_type)}</div>`;
    html += markdownToHtml(item.draft_markdown || '');
    html += `<div style="background-color:${COLOR.panel}; border:1px solid ${COLOR.border}; border-radius:8px; padding:12px 14px; margin-top:12px;">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:${COLOR.textDim}; margin-bottom:6px;">Redactie-checklist</div>`;
    html += `<div style="font-family:${FONT_SANS}; font-size:13px; line-height:1.5; color:${COLOR.text};">${escapeHtml(item.editor_notes || '').replace(/\n/g, '<br>')}</div>`;
    html += `</div></div>`;
  }

  html += `</div>`;
  return html;
}

function buildFormattedArticleEmailHtml(items) {
  let html = `<div style="font-family:${FONT_SANS}; max-width:680px; margin:0 auto; background-color:#FFFFFF;">`;
  html += `<div style="background-image:linear-gradient(135deg, ${COLOR.gradientStart}, ${COLOR.gradientEnd}); padding:28px 24px; border-radius:0 0 12px 12px;">`;
  html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:${COLOR.onGradient}; opacity:0.7; margin:0 0 6px;">Tessar &middot; Geformatteerde artikelen</div>`;
  html += `<div style="font-family:${FONT_SANS}; font-size:20px; font-weight:600; color:${COLOR.onGradient};">${items.length} artikel${items.length === 1 ? '' : 'en'} klaar om te plakken</div>`;
  html += `</div>`;

  for (const item of items) {
    html += `<div style="padding:20px 24px; border-bottom:1px solid ${COLOR.border};">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:11px; color:${COLOR.textDim}; text-transform:uppercase; margin-bottom:6px;">${escapeHtml(item.keyword)} &middot; ${escapeHtml(item.content_type)}</div>`;
    html += markdownToHtml(item.draft_markdown || '');
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

module.exports = { escapeHtml, markdownToHtml, buildDraftReviewEmailHtml, buildFormattedArticleEmailHtml };
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd /Users/hamdeco/development/hamdoun
node n8n-workflows/src/format-article-html.test.js
```

Expected: `OK: format-article-html tests passed`, exit code 0.

- [ ] **Step 5: Commit**

```bash
cd /Users/hamdeco/development/hamdoun
git add n8n-workflows/src/format-article-html.js n8n-workflows/src/format-article-html.test.js
git commit -m "$(cat <<'EOF'
Add tested markdown->HTML converter with bold/list support

The existing email formatter only converted #/## headings; bold text and
bullet/numbered lists were left as literal markdown syntax. This module
fixes that and is the shared source embedded into both Deel 3's email
node (Task 3) and the new Deel 4 workflow (Task 4).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Embed the fixed converter into Deel 3's e-mail node

**Files:** none in the repo (Deel 3's workflow JSON lives only on the n8n server — see the project memory note that Deel 3 was never git-tracked, unlike Deel 2's `tessar-content-brief-generator.json`)

**Interfaces:**
- Consumes: `n8n-workflows/src/format-article-html.js` (Task 2), workflow ID `Vv3niLLmxvet5ORD`, node name `"Bouw e-mail met conceptartikelen"` (id `c5e7846b-5aab-4d17-b2b8-d3afd1b90336`)
- Produces: nothing later tasks import

- [ ] **Step 1: Assemble the embed script from the tested module**

This reads the tested file and mechanically strips its `module.exports` line (Code nodes execute top-level, they can't `require()`), then appends the four lines that turn it into a working node script. No logic is retyped by hand — the embedded copy is byte-derived from the tested file, so Step 4's sync check is meaningful.

```bash
cd /Users/hamdeco/development/hamdoun
python3 -c "
with open('n8n-workflows/src/format-article-html.js') as f:
    src = f.read()

# Strip the trailing module.exports line (and the blank line before it) —
# Code nodes execute top-level and return a value, they don't export.
lines = src.rstrip().split('\n')
assert lines[-1].startswith('module.exports'), f'unexpected last line: {lines[-1]!r}'
body = '\n'.join(lines[:-1]).rstrip()

footer = '''

const items = \$input.all().map((item) => item.json);
const html = buildDraftReviewEmailHtml(items);
return [{ json: { html } }];'''

with open('/tmp/deel4-plan-t3-jscode.txt', 'w') as f:
    f.write(body + footer)
print('embed script written, length:', len(body + footer))
"
```

Expected: prints `embed script written, length: <some number>`, no `AssertionError`.

- [ ] **Step 2: Fetch Deel 3 fresh and patch the node**

```bash
cd /Users/hamdeco/development/hamdoun
set -a; source .env; set +a
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "https://n8n.tessar.nl/api/v1/workflows/Vv3niLLmxvet5ORD" -o /tmp/deel4-plan-t3-before.json -w "HTTP_STATUS:%{http_code}\n"

python3 -c "
import json
with open('/tmp/deel4-plan-t3-before.json') as f:
    wf = json.load(f)
with open('/tmp/deel4-plan-t3-jscode.txt') as f:
    new_js_code = f.read()

node = next(n for n in wf['nodes'] if n['name'] == 'Bouw e-mail met conceptartikelen')
assert node['id'] == 'c5e7846b-5aab-4d17-b2b8-d3afd1b90336', f\"unexpected node id {node['id']}, is this really the same node?\"
node['parameters']['jsCode'] = new_js_code

payload = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': {'executionOrder': 'v1'},
}
with open('/tmp/deel4-plan-t3-payload.json', 'w') as f:
    json.dump(payload, f)
print('payload written')
"
```

Expected: `HTTP_STATUS:200` on the GET, then `payload written`.

- [ ] **Step 3: PUT the fix**

```bash
cd /Users/hamdeco/development/hamdoun
set -a; source .env; set +a
curl -s -X PUT \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  --data @/tmp/deel4-plan-t3-payload.json \
  "https://n8n.tessar.nl/api/v1/workflows/Vv3niLLmxvet5ORD" \
  -o /tmp/deel4-plan-t3-after.json -w "HTTP_STATUS:%{http_code}\n"
```

Expected: `HTTP_STATUS:200`.

- [ ] **Step 4: Verify structure is untouched and sync-check the live jsCode against the same test assertions**

First the structural check:

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t3-after.json') as f:
    wf = json.load(f)
assert len(wf['nodes']) == 12, f\"expected 12 nodes, got {len(wf['nodes'])}\"
assert wf['active'] == False, 'workflow got activated unexpectedly'
node = next(n for n in wf['nodes'] if n['name'] == 'Bouw e-mail met conceptartikelen')
assert node['id'] == 'c5e7846b-5aab-4d17-b2b8-d3afd1b90336', 'node id changed'
assert 'buildDraftReviewEmailHtml' in node['parameters']['jsCode'], 'new jsCode was not actually written'
conns = wf['connections']
assert conns['Combineer brief + concept']['main'][0][1]['node'] == 'Bouw e-mail met conceptartikelen', 'connection into the email node changed'
assert conns['Bouw e-mail met conceptartikelen']['main'][0][0]['node'] == 'Verstuur conceptartikelen', 'connection out of the email node changed'
print('OK: structure verified')
"
```

Expected: `OK: structure verified`.

Then extract the actual live `jsCode` and run it through Node with the same mock input the unit test uses, proving the deployed code and the tested module produce identical output (this is the "sync check" pattern already established in this repo's git history for `build-email-html.js`):

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t3-after.json') as f:
    wf = json.load(f)
node = next(n for n in wf['nodes'] if n['name'] == 'Bouw e-mail met conceptartikelen')
with open('/tmp/deel4-plan-t3-live-jscode.js', 'w') as f:
    f.write(node['parameters']['jsCode'])
print('extracted')
"

node -e "
const fs = require('fs');
const liveCode = fs.readFileSync('/tmp/deel4-plan-t3-live-jscode.js', 'utf8');

// Mock the n8n \$input API the same way the node expects it.
const mockItems = [{
  json: {
    keyword: 'AI oplossingen voor bedrijven',
    content_type: 'dienstenpagina',
    draft_markdown: '# Titel\n\n- Punt een\n- Punt twee\n\n**Bold tekst.**',
    editor_notes: 'Check dit.',
  },
}];
const \$input = { all: () => mockItems };

const fn = new Function('\$input', liveCode);
const result = fn(\$input);
const html = result[0].json.html;

if (!html.includes('<h1')) throw new Error('live code missing <h1>');
if (!html.includes('<ul') || !html.includes('<li>Punt een</li>')) throw new Error('live code missing list conversion');
if (!html.includes('<strong>Bold tekst.</strong>')) throw new Error('live code missing bold conversion');
if (html.includes('**')) throw new Error('live code left raw markdown bold markers');
if (!html.includes('Redactie-checklist')) throw new Error('live code lost the editor checklist section');
console.log('OK: live jsCode matches tested module behavior');
"
```

Expected: `OK: live jsCode matches tested module behavior`, no thrown error.

---

## Task 4: Create the new Deel 4 workflow

**Files:** none in the repo (matching how Deel 3 is not git-tracked either — see Task 3's note; this keeps the new workflow consistent with its sibling rather than introducing a new convention for just this one workflow)

**Interfaces:**
- Consumes: `n8n-workflows/src/format-article-html.js` (Task 2), Deel 3's current node structure as a style reference (already fetched in Task 1/3)
- Produces: a new n8n workflow, inactive, credential-less, ready for the user to wire up and test manually

- [ ] **Step 1: Assemble the Deel 4 e-mail node's embed script**

Same mechanical extraction as Task 3, but calling `buildFormattedArticleEmailHtml` instead:

```bash
cd /Users/hamdeco/development/hamdoun
python3 -c "
with open('n8n-workflows/src/format-article-html.js') as f:
    src = f.read()

lines = src.rstrip().split('\n')
assert lines[-1].startswith('module.exports'), f'unexpected last line: {lines[-1]!r}'
body = '\n'.join(lines[:-1]).rstrip()

footer = '''

const items = \$input.all().map((item) => item.json);
const html = buildFormattedArticleEmailHtml(items);
return [{ json: { html } }];'''

with open('/tmp/deel4-plan-t4-jscode.txt', 'w') as f:
    f.write(body + footer)
print('embed script written, length:', len(body + footer))
"
```

Expected: prints `embed script written, length: <some number>`.

- [ ] **Step 2: Build the full workflow JSON and POST it**

```bash
cd /Users/hamdeco/development/hamdoun
set -a; source .env; set +a
python3 -c "
import json, uuid

with open('/tmp/deel4-plan-t4-jscode.txt') as f:
    email_js_code = f.read()

def nid():
    return str(uuid.uuid4())

trigger = {
    'parameters': {},
    'id': nid(),
    'name': \"When clicking 'Execute workflow'\",
    'type': 'n8n-nodes-base.manualTrigger',
    'typeVersion': 1,
    'position': [0, 0],
}

read_sheet = {
    'parameters': {
        'documentId': {
            '__rl': True,
            'value': 'https://docs.google.com/spreadsheets/d/1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0/edit',
            'mode': 'url',
        },
        'sheetName': {
            '__rl': True,
            'value': 210428761,
            'mode': 'list',
            'cachedResultName': 'Content briefs',
            'cachedResultUrl': 'https://docs.google.com/spreadsheets/d/1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0/edit#gid=210428761',
        },
        'options': {},
    },
    'id': nid(),
    'name': 'Lees Content briefs',
    'type': 'n8n-nodes-base.googleSheets',
    'typeVersion': 4.7,
    'position': [224, 0],
    # Deliberately NO 'credentials' key — user attaches it manually in the UI.
}

filter_approved = {
    'parameters': {
        'jsCode': \"return \$input.all().filter((item) => item.json.status === 'goedgekeurd');\",
    },
    'id': nid(),
    'name': 'Filter goedgekeurde briefs',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [448, 0],
}

build_email = {
    'parameters': {
        'jsCode': email_js_code,
    },
    'id': nid(),
    'name': \"Bouw e-mail met opgemaakt artikel\",
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [672, -144],
}

send_email = {
    'parameters': {
        'sendTo': 'info@tessar.nl',
        'subject': '=Geformatteerde artikelen - Tessar - {{ \$now.toFormat(\"yyyy-MM-dd\") }}',
        'message': '={{ \$json.html }}',
        'options': {
            'appendAttribution': False,
            'senderName': 'Tessar Content Briefs',
        },
    },
    'id': nid(),
    'name': 'Verstuur geformatteerd artikel',
    'type': 'n8n-nodes-base.gmail',
    'typeVersion': 2.2,
    'position': [896, -144],
    # Deliberately NO 'credentials' key — user attaches it manually in the UI.
}

set_status = {
    'parameters': {
        'assignments': {
            'assignments': [
                {'id': 'force-status', 'name': 'status', 'type': 'string', 'value': 'geformatteerd'},
            ],
        },
        'includeOtherFields': True,
        'options': {'dotNotation': False},
    },
    'id': nid(),
    'name': \"Zet status op 'geformatteerd'\",
    'type': 'n8n-nodes-base.set',
    'typeVersion': 3.4,
    'position': [672, 144],
}

update_sheet = {
    'parameters': {
        'operation': 'update',
        'documentId': {
            '__rl': True,
            'value': 'https://docs.google.com/spreadsheets/d/1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0/edit',
            'mode': 'url',
        },
        'sheetName': {
            '__rl': True,
            'value': 210428761,
            'mode': 'list',
            'cachedResultName': 'Content briefs',
            'cachedResultUrl': 'https://docs.google.com/spreadsheets/d/1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0/edit#gid=210428761',
        },
        'columns': {
            'mappingMode': 'autoMapInputData',
            'value': {},
            'matchingColumns': ['row_number'],
            'schema': [
                {'id': 'row_number', 'displayName': 'row_number', 'required': False, 'defaultMatch': True, 'display': True, 'type': 'string', 'canBeUsedToMatch': True, 'removed': False},
                {'id': 'status', 'displayName': 'status', 'required': False, 'defaultMatch': False, 'display': True, 'type': 'string', 'canBeUsedToMatch': True, 'removed': False},
            ],
            'attemptToConvertTypes': False,
            'convertFieldsToString': False,
        },
        'options': {},
    },
    'id': nid(),
    'name': \"Update status naar 'geformatteerd'\",
    'type': 'n8n-nodes-base.googleSheets',
    'typeVersion': 4.7,
    'position': [896, 144],
    # Deliberately NO 'credentials' key — user attaches it manually in the UI.
}

nodes = [trigger, read_sheet, filter_approved, build_email, send_email, set_status, update_sheet]

connections = {
    trigger['name']: {'main': [[{'node': read_sheet['name'], 'type': 'main', 'index': 0}]]},
    read_sheet['name']: {'main': [[{'node': filter_approved['name'], 'type': 'main', 'index': 0}]]},
    filter_approved['name']: {'main': [[
        {'node': build_email['name'], 'type': 'main', 'index': 0},
        {'node': set_status['name'], 'type': 'main', 'index': 0},
    ]]},
    build_email['name']: {'main': [[{'node': send_email['name'], 'type': 'main', 'index': 0}]]},
    set_status['name']: {'main': [[{'node': update_sheet['name'], 'type': 'main', 'index': 0}]]},
}

payload = {
    'name': 'Deel 4 - Formatteer goedgekeurd conceptartikel',
    'nodes': nodes,
    'connections': connections,
    'settings': {'executionOrder': 'v1'},
}

with open('/tmp/deel4-plan-t4-payload.json', 'w') as f:
    json.dump(payload, f)
print('payload written, nodes:', len(nodes))
"

curl -s -X POST \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  --data @/tmp/deel4-plan-t4-payload.json \
  "https://n8n.tessar.nl/api/v1/workflows" \
  -o /tmp/deel4-plan-t4-response.json -w "HTTP_STATUS:%{http_code}\n"
```

Expected: `payload written, nodes: 7`, then `HTTP_STATUS:200`.

- [ ] **Step 3: Verify the created workflow**

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t4-response.json') as f:
    wf = json.load(f)

assert wf['name'] == 'Deel 4 - Formatteer goedgekeurd conceptartikel'
assert wf['active'] == False, 'workflow was created active — must be inactive'
assert len(wf['nodes']) == 7, f\"expected 7 nodes, got {len(wf['nodes'])}\"

names = {n['name'] for n in wf['nodes']}
expected_names = {
    \"When clicking 'Execute workflow'\",
    'Lees Content briefs',
    'Filter goedgekeurde briefs',
    'Bouw e-mail met opgemaakt artikel',
    'Verstuur geformatteerd artikel',
    \"Zet status op 'geformatteerd'\",
    \"Update status naar 'geformatteerd'\",
}
assert names == expected_names, f'node names mismatch: {names.symmetric_difference(expected_names)}'

for n in wf['nodes']:
    assert 'credentials' not in n or not n['credentials'], f\"node {n['name']!r} unexpectedly has credentials attached\"

read_sheet = next(n for n in wf['nodes'] if n['name'] == 'Lees Content briefs')
assert read_sheet['parameters']['sheetName']['value'] == 210428761, 'wrong gid on read node'

update_sheet = next(n for n in wf['nodes'] if n['name'] == \"Update status naar 'geformatteerd'\")
assert update_sheet['parameters']['sheetName']['value'] == 210428761, 'wrong gid on update node'

email_node = next(n for n in wf['nodes'] if n['name'] == 'Bouw e-mail met opgemaakt artikel')
assert 'buildFormattedArticleEmailHtml' in email_node['parameters']['jsCode'], 'wrong builder function embedded'

conns = wf['connections']
assert conns[\"When clicking 'Execute workflow'\"]['main'][0][0]['node'] == 'Lees Content briefs'
assert conns['Lees Content briefs']['main'][0][0]['node'] == 'Filter goedgekeurde briefs'
branch_targets = {c['node'] for c in conns['Filter goedgekeurde briefs']['main'][0]}
assert branch_targets == {'Bouw e-mail met opgemaakt artikel', \"Zet status op 'geformatteerd'\"}, f'filter fan-out wrong: {branch_targets}'
assert conns['Bouw e-mail met opgemaakt artikel']['main'][0][0]['node'] == 'Verstuur geformatteerd artikel'
assert conns[\"Zet status op 'geformatteerd'\"]['main'][0][0]['node'] == \"Update status naar 'geformatteerd'\"

print('OK: Deel 4 workflow verified, id =', wf['id'])
"
```

Expected: `OK: Deel 4 workflow verified, id = <some id>` — note this id down, you'll need it to tell the user where to find the workflow and to link it from project memory.

- [ ] **Step 4: Sync-check the live email node's jsCode the same way as Task 3**

```bash
python3 -c "
import json
with open('/tmp/deel4-plan-t4-response.json') as f:
    wf = json.load(f)
node = next(n for n in wf['nodes'] if n['name'] == 'Bouw e-mail met opgemaakt artikel')
with open('/tmp/deel4-plan-t4-live-jscode.js', 'w') as f:
    f.write(node['parameters']['jsCode'])
print('extracted')
"

node -e "
const fs = require('fs');
const liveCode = fs.readFileSync('/tmp/deel4-plan-t4-live-jscode.js', 'utf8');

const mockItems = [{
  json: {
    keyword: 'AI oplossingen voor bedrijven',
    content_type: 'dienstenpagina',
    draft_markdown: '# Titel\n\n- Punt een\n- Punt twee\n\n**Bold tekst.**',
  },
}];
const \$input = { all: () => mockItems };

const fn = new Function('\$input', liveCode);
const result = fn(\$input);
const html = result[0].json.html;

if (!html.includes('<h1')) throw new Error('live code missing <h1>');
if (!html.includes('<ul') || !html.includes('<li>Punt een</li>')) throw new Error('live code missing list conversion');
if (!html.includes('<strong>Bold tekst.</strong>')) throw new Error('live code missing bold conversion');
if (html.includes('**')) throw new Error('live code left raw markdown bold markers');
if (html.includes('Redactie-checklist')) throw new Error('live code wrongly includes the editor checklist (that is Deel 3 only)');
if (!html.includes('klaar om te plakken')) throw new Error('live code missing the paste-ready heading');
console.log('OK: live Deel 4 jsCode matches tested module behavior');
"
```

Expected: `OK: live Deel 4 jsCode matches tested module behavior`, no thrown error.

- [ ] **Step 5: Commit the plan/spec state (no code to commit — workflow lives only on the n8n server)**

Nothing to commit here — Deel 4's workflow JSON, like Deel 3's, is not git-tracked (see Task 3's file note). If a later task wants to change this convention for both workflows, that's a separate, explicitly-scoped piece of work, not part of this plan.

---

## Final check before handing back to the user

- [ ] Re-read the "Global Constraints" section and confirm every task actually honored each line — in particular: Deel 4 has zero attached credentials, Deel 4 is inactive, no node outside the two named ones was touched in Deel 3, and no workflow was executed via the API at any point.
- [ ] Report to the user: the Deel 4 workflow id from Task 4 Step 3, that the "Update status naar 'concept klaar'" regression is fixed again (and that it reverted once already — worth mentioning so the user knows not to be alarmed if it's the UI doing this), and that they need to manually attach the Google Sheets + Gmail credentials to Deel 4's three unattached nodes in the n8n UI before testing.
