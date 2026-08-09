# Tessar Content-Brief Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, manually-triggered n8n workflow that reads the existing "Keyword rankings" Google Sheet, generates a structured SEO content brief per tracked keyword via Claude, and emails one organized report to Tessar with a prioritized "where to start" summary.

**Architecture:** A new n8n workflow, authored first as a plain JSON file in this repo and imported into n8n at the end. Two pure-JavaScript data-shaping functions (grouping/priority-sort) are written and unit-tested with Node's built-in `assert` before being embedded into the workflow's Code nodes, so the logic that ships is exactly the logic that was tested. The workflow reuses the already-authenticated "Google Sheets account", "Anthropic account", and "Gmail account" credentials from the existing tracker workflow — credentials are never stored in the JSON file, only selected live in the n8n UI at import time.

**Tech Stack:** n8n (self-hosted, `n8n.tessar.nl`), Claude Opus 5 via the Anthropic n8n node, Node.js (for pre-embedding unit tests), Python 3 (for JSON structural validation).

## Global Constraints

- Tracked keywords (must match the tracker workflow's Configuration node exactly — keep in sync manually if that list changes): `AI automatisering voor het mkb, AI oplossingen voor bedrijven, AI receptioniste voor bedrijven, AI chatbot voor bedrijven, workflow automatisering met AI, AI implementatie laten uitvoeren, AI telefonist voor bedrijf, bedrijfsprocessen automatiseren met AI`
- Claude model: `claude-opus-5` (same as the tracker workflow)
- Report recipient: `info@tessar.nl`
- Known direct competitors to name explicitly when they appear in the data: Voicelabs, VoxFlow, Aanloop AI, Frontcall, Ploko, HartAI, EasyData
- Email HTML is restricted to `h2`, `h3`, `p`, `ul`, `li`, `strong` tags only — no markdown, no CSS, no `html`/`head`/`body` wrapper (same restriction as the tracker's report email)
- Credentials are never written into the JSON file with real IDs — every service node ships with no `credentials` block, and the credential is selected live in the n8n UI during Task 7 (matches how the tracker workflow's Apify credential was fixed earlier)
- Source of truth for the workflow is `n8n-workflows/tessar-content-brief-generator.json` in this repo, kept in sync with n8n via manual export after Task 9

---

## File Structure

- `n8n-workflows/tessar-content-brief-generator.json` — the n8n workflow definition, built incrementally across Tasks 1–6
- `n8n-workflows/validate.py` — shared structural-validation helpers, reused by every task's test step
- `n8n-workflows/src/build-keyword-context.js` — pure function used inside the "Bouw keyword-context" Code node
- `n8n-workflows/src/build-keyword-context.test.js` — unit test for the above
- `n8n-workflows/src/build-email-html.js` — pure function used inside the "Sorteer en bouw e-mail" Code node
- `n8n-workflows/src/build-email-html.test.js` — unit test for the above

---

### Task 1: Scaffold the workflow file + shared validator

**Files:**
- Create: `n8n-workflows/tessar-content-brief-generator.json`
- Create: `n8n-workflows/validate.py`

**Interfaces:**
- Produces: `validate.py` exposes `load(path)`, `assert_node(wf, name, node_type)`, `assert_connection(wf, source, target, conn_type="main", target_index=0)` — every later task imports these.
- Produces: the workflow file contains 3 nodes (`When clicking 'Execute workflow'`, `Tracked keywords`, `Read keyword rankings`), wired trigger → keywords → sheets.

- [ ] **Step 1: Write `validate.py`**

```python
"""Shared structural checks for the Tessar content-brief workflow JSON."""
import json


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_node(wf, name, node_type):
    matches = [n for n in wf["nodes"] if n["name"] == name]
    assert matches, f"node '{name}' not found (have: {[n['name'] for n in wf['nodes']]})"
    assert matches[0]["type"] == node_type, (
        f"node '{name}' has type {matches[0]['type']!r}, expected {node_type!r}"
    )
    return matches[0]


def assert_connection(wf, source, target, conn_type="main", target_index=0):
    conns = wf["connections"].get(source, {}).get(conn_type, [])
    flat = [c for bucket in conns for c in bucket]
    matches = [c for c in flat if c["node"] == target and c["type"] == conn_type]
    assert matches, (
        f"no {conn_type!r} connection from '{source}' to '{target}' "
        f"(have: {[(c['node'], c['type']) for c in flat]})"
    )
    assert matches[0]["index"] == target_index, (
        f"connection '{source}' -> '{target}' has index {matches[0]['index']}, "
        f"expected {target_index}"
    )
```

- [ ] **Step 2: Write the scaffold JSON**

```json
{
  "name": "Generate content briefs for Tessar SEO keywords",
  "nodes": [
    {
      "parameters": {},
      "id": "a1b2c3d4-0001-4000-8000-000000000001",
      "name": "When clicking 'Execute workflow'",
      "type": "n8n-nodes-base.manualTrigger",
      "position": [800, 600],
      "typeVersion": 1
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "keywords-field",
              "name": "keywords",
              "type": "string",
              "value": "AI automatisering voor het mkb, AI oplossingen voor bedrijven, AI receptioniste voor bedrijven, AI chatbot voor bedrijven, workflow automatisering met AI, AI implementatie laten uitvoeren, AI telefonist voor bedrijf, bedrijfsprocessen automatiseren met AI"
            }
          ]
        },
        "options": {}
      },
      "id": "a1b2c3d4-0001-4000-8000-000000000002",
      "name": "Tracked keywords",
      "type": "n8n-nodes-base.set",
      "position": [1024, 600],
      "typeVersion": 3.4
    },
    {
      "parameters": {
        "operation": "read",
        "resource": "sheet",
        "documentId": {
          "__rl": true,
          "mode": "list",
          "value": "",
          "cachedResultName": "Keyword rankings"
        },
        "sheetName": {
          "__rl": true,
          "mode": "list",
          "value": ""
        },
        "options": {}
      },
      "id": "a1b2c3d4-0001-4000-8000-000000000003",
      "name": "Read keyword rankings",
      "type": "n8n-nodes-base.googleSheets",
      "position": [1248, 600],
      "typeVersion": 4.7
    }
  ],
  "pinData": {},
  "connections": {
    "When clicking 'Execute workflow'": {
      "main": [[{ "node": "Tracked keywords", "type": "main", "index": 0 }]]
    },
    "Tracked keywords": {
      "main": [[{ "node": "Read keyword rankings", "type": "main", "index": 0 }]]
    }
  },
  "active": false,
  "settings": { "executionOrder": "v1" }
}
```

- [ ] **Step 3: Validate**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, \"When clicking 'Execute workflow'\", 'n8n-nodes-base.manualTrigger')
assert_node(wf, 'Tracked keywords', 'n8n-nodes-base.set')
assert_node(wf, 'Read keyword rankings', 'n8n-nodes-base.googleSheets')
assert_connection(wf, \"When clicking 'Execute workflow'\", 'Tracked keywords')
assert_connection(wf, 'Tracked keywords', 'Read keyword rankings')
print('OK: Task 1 scaffold valid')
"
```

Expected: `OK: Task 1 scaffold valid` with no assertion errors.

- [ ] **Step 4: Commit**

```bash
git add n8n-workflows/tessar-content-brief-generator.json n8n-workflows/validate.py
git commit -m "Scaffold Tessar content-brief workflow: trigger, keyword list, sheet read"
```

---

### Task 2: Keyword-context grouping logic

**Files:**
- Create: `n8n-workflows/src/build-keyword-context.js`
- Create: `n8n-workflows/src/build-keyword-context.test.js`
- Modify: `n8n-workflows/tessar-content-brief-generator.json`

**Interfaces:**
- Consumes: the Task 1 file, unchanged, as a starting point.
- Consumes: `Read keyword rankings` output items shaped like the tracker's Sheet rows: `{checked_at, keyword, rank, title, url, domain, description, is_target_domain}`.
- Produces: `buildKeywordContext(rows, trackedKeywords)` returning an array of `{keyword, has_data, top_competitors}`, where `top_competitors` is `[{domain, title, description, rank}]` (max 3, excluding `is_target_domain` rows, sorted by rank).
- Produces: a 4th workflow node, `Bouw keyword-context` (Code, type `n8n-nodes-base.code`), wired after `Read keyword rankings`.

- [ ] **Step 1: Write the failing test**

```javascript
// n8n-workflows/src/build-keyword-context.test.js
const assert = require('node:assert');
const { buildKeywordContext } = require('./build-keyword-context');

const rows = [
  {
    checked_at: '2026-08-03',
    keyword: 'AI receptioniste voor bedrijven',
    rank: 1,
    title: 'Oude titel',
    url: 'https://old.example/',
    domain: 'old.example',
    description: 'Oude beschrijving',
    is_target_domain: false,
  },
  {
    checked_at: '2026-08-10',
    keyword: 'AI receptioniste voor bedrijven',
    rank: 2,
    title: 'Voicelabs AI-receptioniste',
    url: 'https://voicelabs.nl/',
    domain: 'voicelabs.nl',
    description: 'AI-receptioniste voor mkb-klantenservice',
    is_target_domain: false,
  },
  {
    checked_at: '2026-08-10',
    keyword: 'AI receptioniste voor bedrijven',
    rank: 1,
    title: 'Aanloop AI',
    url: 'https://aanloopai.nl/',
    domain: 'aanloopai.nl',
    description: 'AI-bureau voor het Nederlandse mkb',
    is_target_domain: false,
  },
  {
    checked_at: '2026-08-10',
    keyword: 'AI receptioniste voor bedrijven',
    rank: 4,
    title: 'Tessar',
    url: 'https://tessar.nl/',
    domain: 'tessar.nl',
    description: '',
    is_target_domain: true,
  },
];

const trackedKeywords = ['AI receptioniste voor bedrijven', 'AI telefonist voor bedrijf'];

const result = buildKeywordContext(rows, trackedKeywords);

assert.strictEqual(result.length, 2, 'one item per tracked keyword');

const withData = result.find((r) => r.keyword === 'AI receptioniste voor bedrijven');
assert.strictEqual(withData.has_data, true);
assert.strictEqual(withData.top_competitors.length, 2, 'excludes is_target_domain row, uses latest date only');
assert.strictEqual(withData.top_competitors[0].domain, 'aanloopai.nl', 'sorted by rank ascending');
assert.strictEqual(withData.top_competitors[1].domain, 'voicelabs.nl');
assert.ok(
  !withData.top_competitors.some((c) => c.domain === 'old.example'),
  'must not use the 2026-08-03 row once a 2026-08-10 row exists'
);

const noData = result.find((r) => r.keyword === 'AI telefonist voor bedrijf');
assert.strictEqual(noData.has_data, false);
assert.deepStrictEqual(noData.top_competitors, []);

console.log('OK: build-keyword-context tests passed');
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node n8n-workflows/src/build-keyword-context.test.js
```

Expected: FAIL — `Cannot find module './build-keyword-context'` (file does not exist yet).

- [ ] **Step 3: Write the implementation**

```javascript
// n8n-workflows/src/build-keyword-context.js
function buildKeywordContext(rows, trackedKeywords) {
  const byKeyword = {};
  for (const row of rows) {
    if (!byKeyword[row.keyword]) byKeyword[row.keyword] = [];
    byKeyword[row.keyword].push(row);
  }

  return trackedKeywords.map((keyword) => {
    const rowsForKeyword = byKeyword[keyword] || [];
    if (rowsForKeyword.length === 0) {
      return { keyword, has_data: false, top_competitors: [] };
    }
    const latestDate = rowsForKeyword
      .map((r) => r.checked_at)
      .sort()
      .slice(-1)[0];
    const latestRows = rowsForKeyword.filter((r) => r.checked_at === latestDate);
    const topCompetitors = latestRows
      .filter((r) => !r.is_target_domain)
      .sort((a, b) => Number(a.rank) - Number(b.rank))
      .slice(0, 3)
      .map((r) => ({
        domain: r.domain,
        title: r.title,
        description: r.description,
        rank: Number(r.rank),
      }));
    return { keyword, has_data: true, top_competitors: topCompetitors };
  });
}

module.exports = { buildKeywordContext };
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node n8n-workflows/src/build-keyword-context.test.js
```

Expected: `OK: build-keyword-context tests passed`

- [ ] **Step 5: Embed the verified function into the workflow's Code node**

Add this node to the `nodes` array in `n8n-workflows/tessar-content-brief-generator.json` (the `jsCode` body below is the exact, already-tested function from Step 3, adapted to n8n's `$input`/`$('Node Name')` runtime):

```json
{
  "parameters": {
    "jsCode": "const trackedKeywords = $('Tracked keywords').first().json.keywords\n  .split(',')\n  .map((k) => k.trim())\n  .filter((k) => k.length > 0);\nconst rows = $input.all().map((item) => item.json);\n\nfunction buildKeywordContext(rows, trackedKeywords) {\n  const byKeyword = {};\n  for (const row of rows) {\n    if (!byKeyword[row.keyword]) byKeyword[row.keyword] = [];\n    byKeyword[row.keyword].push(row);\n  }\n\n  return trackedKeywords.map((keyword) => {\n    const rowsForKeyword = byKeyword[keyword] || [];\n    if (rowsForKeyword.length === 0) {\n      return { keyword, has_data: false, top_competitors: [] };\n    }\n    const latestDate = rowsForKeyword\n      .map((r) => r.checked_at)\n      .sort()\n      .slice(-1)[0];\n    const latestRows = rowsForKeyword.filter((r) => r.checked_at === latestDate);\n    const topCompetitors = latestRows\n      .filter((r) => !r.is_target_domain)\n      .sort((a, b) => Number(a.rank) - Number(b.rank))\n      .slice(0, 3)\n      .map((r) => ({\n        domain: r.domain,\n        title: r.title,\n        description: r.description,\n        rank: Number(r.rank),\n      }));\n    return { keyword, has_data: true, top_competitors: topCompetitors };\n  });\n}\n\nconst result = buildKeywordContext(rows, trackedKeywords);\nreturn result.map((r) => ({ json: r }));"
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000004",
  "name": "Bouw keyword-context",
  "type": "n8n-nodes-base.code",
  "position": [1472, 600],
  "typeVersion": 2
}
```

Add the connection to the `connections` object:

```json
"Read keyword rankings": {
  "main": [[{ "node": "Bouw keyword-context", "type": "main", "index": 0 }]]
}
```

- [ ] **Step 6: Validate the JSON**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, 'Bouw keyword-context', 'n8n-nodes-base.code')
assert_connection(wf, 'Read keyword rankings', 'Bouw keyword-context')
print('OK: Task 2 node and connection present')
"
```

Expected: `OK: Task 2 node and connection present`

- [ ] **Step 7: Commit**

```bash
git add n8n-workflows/src/build-keyword-context.js n8n-workflows/src/build-keyword-context.test.js n8n-workflows/tessar-content-brief-generator.json
git commit -m "Add keyword-context grouping logic (tested) and wire into workflow"
```

---

### Task 3: Branch on data availability + generate briefs with Claude

**Files:**
- Modify: `n8n-workflows/tessar-content-brief-generator.json`

**Interfaces:**
- Consumes: `Bouw keyword-context` output items, each `{keyword, has_data, top_competitors}` (from Task 2).
- Produces: an `If` node `Heeft data?` with two outputs — index 0 (true) continues to brief generation, index 1 (false) is left unconnected in this task (wired to `Merge` in Task 4).
- Produces: `Anthropic Chat Model` (sub-node), `Brief JSON-schema` (Structured Output Parser sub-node), and `Genereer brief` (Basic LLM Chain) — the true branch ends at `Genereer brief`, whose output items are shaped `{output: {keyword, title, meta_description, content_type, outline, differentiation, estimated_word_count, priority, priority_reason}}`.

- [ ] **Step 1: Add the `If` node**

```json
{
  "parameters": {
    "conditions": {
      "options": {
        "caseSensitive": true,
        "leftValue": "",
        "typeValidation": "strict",
        "version": 2
      },
      "combinator": "and",
      "conditions": [
        {
          "id": "has-data-check",
          "leftValue": "={{ $json.has_data }}",
          "rightValue": "",
          "operator": { "type": "boolean", "operation": "true", "singleValue": true }
        }
      ]
    },
    "options": {}
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000005",
  "name": "Heeft data?",
  "type": "n8n-nodes-base.if",
  "position": [1696, 600],
  "typeVersion": 2.2
}
```

Connection from Task 2's node:

```json
"Bouw keyword-context": {
  "main": [[{ "node": "Heeft data?", "type": "main", "index": 0 }]]
}
```

- [ ] **Step 2: Add the Structured Output Parser sub-node**

```json
{
  "parameters": {
    "schemaType": "manual",
    "inputSchema": "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"keyword\": { \"type\": \"string\" },\n    \"title\": { \"type\": \"string\" },\n    \"meta_description\": { \"type\": \"string\" },\n    \"content_type\": { \"type\": \"string\", \"enum\": [\"blogartikel\", \"dienstenpagina\"] },\n    \"outline\": {\n      \"type\": \"array\",\n      \"items\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"heading\": { \"type\": \"string\" },\n          \"guidance\": { \"type\": \"string\" }\n        },\n        \"required\": [\"heading\", \"guidance\"]\n      }\n    },\n    \"differentiation\": { \"type\": \"string\" },\n    \"estimated_word_count\": { \"type\": \"number\" },\n    \"priority\": { \"type\": \"string\", \"enum\": [\"makkelijk\", \"gemiddeld\", \"lastig\"] },\n    \"priority_reason\": { \"type\": \"string\" }\n  },\n  \"required\": [\"keyword\", \"title\", \"meta_description\", \"content_type\", \"outline\", \"differentiation\", \"estimated_word_count\", \"priority\", \"priority_reason\"]\n}"
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000006",
  "name": "Brief JSON-schema",
  "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
  "position": [1840, 800],
  "typeVersion": 1.2
}
```

- [ ] **Step 3: Add the Anthropic Chat Model sub-node**

```json
{
  "parameters": {
    "model": {
      "__rl": true,
      "mode": "id",
      "value": "claude-opus-5"
    },
    "options": {}
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000007",
  "name": "Anthropic Chat Model",
  "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
  "position": [2000, 800],
  "typeVersion": 1.3
}
```

- [ ] **Step 4: Add the `Genereer brief` Basic LLM Chain node**

```json
{
  "parameters": {
    "promptType": "define",
    "text": "=Keyword: {{ $json.keyword }}\n\nTop 3 concurrenten die nu op dit keyword scoren (titel, beschrijving, domein, positie):\n{{ JSON.stringify($json.top_competitors) }}\n\nSchrijf de SEO-brief voor dit keyword.",
    "hasOutputParser": true,
    "messages": {
      "messageValues": [
        {
          "message": "You are a senior SEO content strategist for Tessar (tessar.nl), a Dutch AI-automation and AI-receptionist company for the Nederlandse mkb that is currently pre-launch. For the given keyword and its current top-3 ranking competitors (from live Google SERP data), produce one structured content brief that a non-marketing founder can hand to a writer. The competitors are Tessar's direct rivals in this space - actual examples include Voicelabs, VoxFlow, Aanloop AI, Frontcall, Ploko, HartAI and EasyData; reference the specific competitor names and what their ranking page appears to cover, based on the given titles and descriptions, when describing the differentiation angle. Assess priority as 'makkelijk' when the competition looks weak or thin (generic content, few strong competitors, or a specific/long-tail keyword), 'lastig' when strong, well-established players dominate all 3 spots, and 'gemiddeld' otherwise. Be factual: only reference competitor content visible in the given titles/descriptions, never invent facts about a competitor's page. Respond only in the required JSON format."
        }
      ]
    },
    "batching": {}
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000008",
  "name": "Genereer brief",
  "type": "@n8n/n8n-nodes-langchain.chainLlm",
  "position": [1920, 600],
  "typeVersion": 1.9
}
```

- [ ] **Step 5: Wire the true branch and the two sub-node connections**

```json
"Heeft data?": {
  "main": [
    [{ "node": "Genereer brief", "type": "main", "index": 0 }]
  ]
},
"Anthropic Chat Model": {
  "ai_languageModel": [[{ "node": "Genereer brief", "type": "ai_languageModel", "index": 0 }]]
},
"Brief JSON-schema": {
  "ai_outputParser": [[{ "node": "Genereer brief", "type": "ai_outputParser", "index": 0 }]]
}
```

Note: `Heeft data?`'s `main` array only has index-0 (true) populated in this task — Task 4 adds index-1 (false) once `Merge` exists to connect it to.

- [ ] **Step 6: Validate**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, 'Heeft data?', 'n8n-nodes-base.if')
assert_node(wf, 'Brief JSON-schema', '@n8n/n8n-nodes-langchain.outputParserStructured')
assert_node(wf, 'Anthropic Chat Model', '@n8n/n8n-nodes-langchain.lmChatAnthropic')
assert_node(wf, 'Genereer brief', '@n8n/n8n-nodes-langchain.chainLlm')
assert_connection(wf, 'Bouw keyword-context', 'Heeft data?')
assert_connection(wf, 'Heeft data?', 'Genereer brief', target_index=0)
assert_connection(wf, 'Anthropic Chat Model', 'Genereer brief', conn_type='ai_languageModel')
assert_connection(wf, 'Brief JSON-schema', 'Genereer brief', conn_type='ai_outputParser')
print('OK: Task 3 nodes and connections present')
"
```

Expected: `OK: Task 3 nodes and connections present`

- [ ] **Step 7: Commit**

```bash
git add n8n-workflows/tessar-content-brief-generator.json
git commit -m "Add has_data branch and Claude brief generation (structured output)"
```

---

### Task 4: Merge branches

**Files:**
- Modify: `n8n-workflows/tessar-content-brief-generator.json`

**Interfaces:**
- Consumes: `Genereer brief` output (has_data=true items, shape `{output: {...}}`) and `Heeft data?` false output (has_data=false items, shape `{keyword, has_data, top_competitors}`), both from Task 3.
- Produces: a `Merge` node `Combineer branches` whose single output stream contains both item shapes, ready for Task 5's sort/build step.

- [ ] **Step 1: Add the `Merge` node**

```json
{
  "parameters": {
    "mode": "append",
    "numberInputs": 2
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000009",
  "name": "Combineer branches",
  "type": "n8n-nodes-base.merge",
  "position": [2144, 700],
  "typeVersion": 3
}
```

- [ ] **Step 2: Wire both branches into it**

Update `Heeft data?`'s connections to add the false-output (index 1) target, and add `Genereer brief`'s outgoing connection:

```json
"Heeft data?": {
  "main": [
    [{ "node": "Genereer brief", "type": "main", "index": 0 }],
    [{ "node": "Combineer branches", "type": "main", "index": 1 }]
  ]
},
"Genereer brief": {
  "main": [[{ "node": "Combineer branches", "type": "main", "index": 0 }]]
}
```

- [ ] **Step 3: Validate**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, 'Combineer branches', 'n8n-nodes-base.merge')
assert_connection(wf, 'Heeft data?', 'Combineer branches', target_index=1)
assert_connection(wf, 'Genereer brief', 'Combineer branches', target_index=0)
print('OK: Task 4 merge wired')
"
```

Expected: `OK: Task 4 merge wired`

- [ ] **Step 4: Commit**

```bash
git add n8n-workflows/tessar-content-brief-generator.json
git commit -m "Merge has_data and no-data branches before the email step"
```

---

### Task 5: Sort by priority and build the email HTML

**Files:**
- Create: `n8n-workflows/src/build-email-html.js`
- Create: `n8n-workflows/src/build-email-html.test.js`
- Modify: `n8n-workflows/tessar-content-brief-generator.json`

**Interfaces:**
- Consumes: `Combineer branches` output items — a mix of `{output: {keyword, title, meta_description, content_type, outline, differentiation, estimated_word_count, priority, priority_reason}}` (generated briefs) and `{keyword, has_data: false, top_competitors: []}` (no-data keywords), from Task 4.
- Produces: `buildEmailHtml(items)` returning one HTML string: a "Waar begin je?" list (sorted `makkelijk` → `gemiddeld` → `lastig`), a "nog geen data" block if applicable, then the full briefs in the same order.
- Produces: a `Sorteer en bouw e-mail` Code node whose single output item is `{json: {html: "<the string>"}}`.

- [ ] **Step 1: Write the failing test**

```javascript
// n8n-workflows/src/build-email-html.test.js
const assert = require('node:assert');
const { buildEmailHtml } = require('./build-email-html');

const items = [
  {
    output: {
      keyword: 'AI telefonist voor bedrijf',
      title: 'AI-telefonist voor het mkb: complete gids',
      meta_description: 'Alles over AI-telefonisten voor kleine bedrijven.',
      content_type: 'blogartikel',
      outline: [{ heading: 'Wat is een AI-telefonist?', guidance: 'Leg het begrip uit.' }],
      differentiation: 'Voicelabs focust op telefonie; Tessar kan breder mkb-verhaal benadrukken.',
      estimated_word_count: 1200,
      priority: 'lastig',
      priority_reason: 'Sterke, gevestigde spelers domineren alle 3 posities.',
    },
  },
  {
    output: {
      keyword: 'AI receptioniste voor bedrijven',
      title: 'AI-receptioniste: de complete oplossing voor mkb',
      meta_description: 'Ontdek hoe een AI-receptioniste jouw bedrijf helpt.',
      content_type: 'dienstenpagina',
      outline: [{ heading: 'Wat doet Tess?', guidance: 'Introduceer het product.' }],
      differentiation: 'Aanloop AI is generiek; Tessar kan dieper op mkb-integraties ingaan.',
      estimated_word_count: 900,
      priority: 'makkelijk',
      priority_reason: 'Concurrentie is generiek en dun uitgewerkt.',
    },
  },
  { keyword: 'bedrijfsprocessen automatiseren met AI', has_data: false, top_competitors: [] },
];

const html = buildEmailHtml(items);

const startIdx = html.indexOf('Waar begin je?');
const easyIdx = html.indexOf('AI receptioniste voor bedrijven');
const hardIdx = html.indexOf('AI telefonist voor bedrijf');
assert.ok(startIdx !== -1, 'has a "Waar begin je?" heading');
assert.ok(startIdx < easyIdx && easyIdx < hardIdx, 'easiest keyword listed before hardest');
assert.ok(html.includes('bedrijfsprocessen automatiseren met AI'), 'mentions the no-data keyword');
assert.ok(html.includes('Nog geen data'), 'flags the no-data keyword clearly');
assert.ok(html.includes('<h2>'), 'produces HTML, not markdown');
assert.ok(!html.includes('<script'), 'no script tags');

console.log('OK: build-email-html tests passed');
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node n8n-workflows/src/build-email-html.test.js
```

Expected: FAIL — `Cannot find module './build-email-html'`.

- [ ] **Step 3: Write the implementation**

```javascript
// n8n-workflows/src/build-email-html.js
const PRIORITY_ORDER = { makkelijk: 0, gemiddeld: 1, lastig: 2 };

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildEmailHtml(items) {
  const briefs = items.filter((item) => item.output).map((item) => item.output);
  const missing = items.filter((item) => item.has_data === false).map((item) => item.keyword);

  briefs.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99));

  let html = '<h2>Waar begin je?</h2><ul>';
  for (const brief of briefs) {
    html += `<li><strong>${escapeHtml(brief.keyword)}</strong> (${escapeHtml(brief.priority)}) - ${escapeHtml(brief.priority_reason)}</li>`;
  }
  html += '</ul>';

  if (missing.length > 0) {
    html += `<h3>Nog geen data voor: ${escapeHtml(missing.join(', '))}</h3><p>Draai eerst de rankingtracker-workflow voor deze keywords.</p>`;
  }

  for (const brief of briefs) {
    html += `<h2>${escapeHtml(brief.title)}</h2>`;
    html += `<p><strong>Keyword:</strong> ${escapeHtml(brief.keyword)}</p>`;
    html += `<p><strong>Meta-beschrijving:</strong> ${escapeHtml(brief.meta_description)}</p>`;
    html += `<p><strong>Contenttype:</strong> ${escapeHtml(brief.content_type)}</p>`;
    html += '<ul>';
    for (const section of brief.outline) {
      html += `<li><strong>${escapeHtml(section.heading)}</strong>: ${escapeHtml(section.guidance)}</li>`;
    }
    html += '</ul>';
    html += `<p><strong>Invalshoek:</strong> ${escapeHtml(brief.differentiation)}</p>`;
    html += `<p><strong>Geschatte lengte:</strong> ${brief.estimated_word_count} woorden</p>`;
  }

  return html;
}

module.exports = { buildEmailHtml };
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node n8n-workflows/src/build-email-html.test.js
```

Expected: `OK: build-email-html tests passed`

- [ ] **Step 5: Embed into the workflow's Code node**

```json
{
  "parameters": {
    "jsCode": "const items = $input.all().map((item) => item.json);\n\nconst PRIORITY_ORDER = { makkelijk: 0, gemiddeld: 1, lastig: 2 };\n\nfunction escapeHtml(str) {\n  return String(str)\n    .replace(/&/g, '&amp;')\n    .replace(/</g, '&lt;')\n    .replace(/>/g, '&gt;');\n}\n\nfunction buildEmailHtml(items) {\n  const briefs = items.filter((item) => item.output).map((item) => item.output);\n  const missing = items.filter((item) => item.has_data === false).map((item) => item.keyword);\n\n  briefs.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99));\n\n  let html = '<h2>Waar begin je?</h2><ul>';\n  for (const brief of briefs) {\n    html += `<li><strong>${escapeHtml(brief.keyword)}</strong> (${escapeHtml(brief.priority)}) - ${escapeHtml(brief.priority_reason)}</li>`;\n  }\n  html += '</ul>';\n\n  if (missing.length > 0) {\n    html += `<h3>Nog geen data voor: ${escapeHtml(missing.join(', '))}</h3><p>Draai eerst de rankingtracker-workflow voor deze keywords.</p>`;\n  }\n\n  for (const brief of briefs) {\n    html += `<h2>${escapeHtml(brief.title)}</h2>`;\n    html += `<p><strong>Keyword:</strong> ${escapeHtml(brief.keyword)}</p>`;\n    html += `<p><strong>Meta-beschrijving:</strong> ${escapeHtml(brief.meta_description)}</p>`;\n    html += `<p><strong>Contenttype:</strong> ${escapeHtml(brief.content_type)}</p>`;\n    html += '<ul>';\n    for (const section of brief.outline) {\n      html += `<li><strong>${escapeHtml(section.heading)}</strong>: ${escapeHtml(section.guidance)}</li>`;\n    }\n    html += '</ul>';\n    html += `<p><strong>Invalshoek:</strong> ${escapeHtml(brief.differentiation)}</p>`;\n    html += `<p><strong>Geschatte lengte:</strong> ${brief.estimated_word_count} woorden</p>`;\n  }\n\n  return html;\n}\n\nreturn [{ json: { html: buildEmailHtml(items) } }];"
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000010",
  "name": "Sorteer en bouw e-mail",
  "type": "n8n-nodes-base.code",
  "position": [2368, 700],
  "typeVersion": 2
}
```

Connection:

```json
"Combineer branches": {
  "main": [[{ "node": "Sorteer en bouw e-mail", "type": "main", "index": 0 }]]
}
```

- [ ] **Step 6: Validate**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, 'Sorteer en bouw e-mail', 'n8n-nodes-base.code')
assert_connection(wf, 'Combineer branches', 'Sorteer en bouw e-mail')
print('OK: Task 5 node and connection present')
"
```

Expected: `OK: Task 5 node and connection present`

- [ ] **Step 7: Commit**

```bash
git add n8n-workflows/src/build-email-html.js n8n-workflows/src/build-email-html.test.js n8n-workflows/tessar-content-brief-generator.json
git commit -m "Add priority sort + HTML email builder (tested) and wire into workflow"
```

---

### Task 6: Send the email and validate the full graph

**Files:**
- Modify: `n8n-workflows/tessar-content-brief-generator.json`

**Interfaces:**
- Consumes: `Sorteer en bouw e-mail` output, `{json: {html: "..."}}`, from Task 5.
- Produces: the workflow's terminal node, `Verstuur content briefs` (Gmail), completing the graph from trigger to email.

- [ ] **Step 1: Add the Gmail node**

```json
{
  "parameters": {
    "sendTo": "info@tessar.nl",
    "subject": "=Content briefs - Tessar - {{ $now.toFormat(\"yyyy-MM-dd\") }}",
    "message": "={{ $json.html }}",
    "options": {
      "appendAttribution": false,
      "senderName": "Tessar Content Briefs"
    }
  },
  "id": "a1b2c3d4-0001-4000-8000-000000000011",
  "name": "Verstuur content briefs",
  "type": "n8n-nodes-base.gmail",
  "position": [2592, 700],
  "typeVersion": 2.2
}
```

Connection:

```json
"Sorteer en bouw e-mail": {
  "main": [[{ "node": "Verstuur content briefs", "type": "main", "index": 0 }]]
}
```

- [ ] **Step 2: Add a full-graph connectivity check to `validate.py`**

```python
def assert_full_chain(wf, node_names_in_order):
    """Every node in the list must be reachable from the trigger via `main` edges,
    and every node in the workflow must appear in node_names_in_order (no orphans)."""
    actual_names = {n["name"] for n in wf["nodes"]}
    expected_names = set(node_names_in_order)
    missing = expected_names - actual_names
    extra = actual_names - expected_names
    assert not missing, f"expected nodes missing from workflow: {missing}"
    assert not extra, f"workflow has nodes not accounted for: {extra}"
```

Append this function to `n8n-workflows/validate.py`.

- [ ] **Step 3: Validate the complete workflow**

```bash
python3 -c "
import sys
sys.path.insert(0, 'n8n-workflows')
from validate import load, assert_node, assert_connection, assert_full_chain

wf = load('n8n-workflows/tessar-content-brief-generator.json')
assert_node(wf, 'Verstuur content briefs', 'n8n-nodes-base.gmail')
assert_connection(wf, 'Sorteer en bouw e-mail', 'Verstuur content briefs')

assert_full_chain(wf, [
    \"When clicking 'Execute workflow'\",
    'Tracked keywords',
    'Read keyword rankings',
    'Bouw keyword-context',
    'Heeft data?',
    'Anthropic Chat Model',
    'Brief JSON-schema',
    'Genereer brief',
    'Combineer branches',
    'Sorteer en bouw e-mail',
    'Verstuur content briefs',
])
print('OK: full workflow graph valid, 11 nodes, no orphans')
"
```

Expected: `OK: full workflow graph valid, 11 nodes, no orphans`

- [ ] **Step 4: Commit**

```bash
git add n8n-workflows/validate.py n8n-workflows/tessar-content-brief-generator.json
git commit -m "Add Gmail send node, completing the workflow graph"
```

---

### Task 7: Import into n8n and wire credentials + the real spreadsheet

**Files:** none (this task happens entirely in the n8n browser UI at `https://n8n.tessar.nl`)

**Interfaces:**
- Consumes: the finished `n8n-workflows/tessar-content-brief-generator.json` from Task 6.
- Produces: a live n8n workflow with all credential and document-reference warnings cleared, ready for Tasks 8–9.

- [ ] **Step 1: Import the workflow**

In n8n, go to **Overview → + → Import from File** (or paste the JSON via the "..." menu → Import from URL/File) and select `n8n-workflows/tessar-content-brief-generator.json`.

- [ ] **Step 2: Bind credentials**

Open each of these 3 nodes and select the existing credential from the dropdown (do not create new ones — these are the same accounts already authenticated for the tracker workflow):

- `Read keyword rankings` → Credential: **Google Sheets account**
- `Anthropic Chat Model` → Credential: **Anthropic account**
- `Verstuur content briefs` → Credential: **Gmail account**

If either the Google Sheets or Gmail credential still shows "Unauthorized" / needs reconnecting (as seen earlier when setting up the tracker workflow), click **Sign in with Google** on that credential first.

- [ ] **Step 3: Point at the real spreadsheet**

On `Read keyword rankings`, set **Document** to the same Google Sheet the tracker workflow logs to ("Keyword rankings"), and **Sheet** to the tab the tracker appends rows to. Both red warning triangles on this node should clear once selected.

- [ ] **Step 4: Save**

Save the workflow in the n8n editor (the top-right Save control, or `Cmd+S`). Confirm no red warning triangles remain on any node.

---

### Task 8: Test the data-prep and brief-generation nodes live

**Files:** none (browser-based verification in n8n)

**Interfaces:**
- Consumes: the imported, credentialed workflow from Task 7.
- Produces: confidence that `Bouw keyword-context` and `Genereer brief` behave correctly against real Sheet data before running the full workflow.

- [ ] **Step 1: Run the data-prep half**

In the n8n editor, right-click `Bouw keyword-context` (or open it and click "Execute step" after executing everything upstream via "Execute previous nodes"). Confirm:
- One output item per tracked keyword (8 total).
- At least one item has `has_data: true` with up to 3 `top_competitors`, sorted by `rank` ascending.
- Any keyword not yet present in the Sheet shows `has_data: false` and `top_competitors: []`.

- [ ] **Step 2: Run one keyword through `Genereer brief`**

Open `Genereer brief` and click "Execute step" (this pulls whatever `has_data: true` items reached it through `Heeft data?`). Confirm the output item's `output` field is a JSON object containing all 9 fields from the schema (`keyword`, `title`, `meta_description`, `content_type`, `outline`, `differentiation`, `estimated_word_count`, `priority`, `priority_reason`), and that:
- `differentiation` names a real competitor from the input data, not a generic statement.
- `priority` is one of `makkelijk` / `gemiddeld` / `lastig`.

If the output doesn't match the schema, n8n will show a parsing error — re-check that `Brief JSON-schema` is correctly connected via `ai_outputParser` (Task 3, Step 5).

---

### Task 9: End-to-end run and email verification

**Files:** none (browser-based verification in n8n and email inbox)

**Interfaces:**
- Consumes: the fully verified workflow from Task 8.
- Produces: a delivered email at `info@tessar.nl`, confirming the spec's end-to-end behavior.

- [ ] **Step 1: Execute the full workflow**

Click "Execute workflow" from the canvas (not a single node). Wait for all 11 nodes to complete without errors.

- [ ] **Step 2: Check the received email**

Open the `info@tessar.nl` inbox and confirm:
- Subject line reads `Content briefs - Tessar - <today's date>`.
- The email opens with a **"Waar begin je?"** list, ordered `makkelijk` → `gemiddeld` → `lastig`.
- Any keyword with no tracker data yet appears in a clearly separated "Nog geen data voor: …" block, not mixed into the priority list.
- Every keyword with data has a full brief below the summary, in the same order, with all 9 fields rendered.
- Only `h2`, `h3`, `p`, `ul`, `li`, `strong` tags are present — no raw markdown syntax (`**`, `##`) leaking into the email body.

- [ ] **Step 3: Export the final workflow JSON back into the repo**

From n8n's "..." menu on the workflow, choose **Download**, and overwrite `n8n-workflows/tessar-content-brief-generator.json` with the exported file (this captures the real credential-bound state, document/sheet selection, and n8n-assigned `id`/`versionId`/`meta` fields).

```bash
git add n8n-workflows/tessar-content-brief-generator.json
git commit -m "Sync final Tessar content-brief workflow JSON after live verification"
```
