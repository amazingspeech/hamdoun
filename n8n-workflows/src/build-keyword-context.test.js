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
