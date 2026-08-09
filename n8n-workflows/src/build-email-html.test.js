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
