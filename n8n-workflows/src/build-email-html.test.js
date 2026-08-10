const assert = require('node:assert');
const { buildEmailHtml } = require('./build-email-html');

const items = [
  {
    output: {
      keyword: 'AI telefonist voor bedrijf',
      search_intent: 'informational',
      suggested_title: 'AI-telefonist voor het mkb: complete gids',
      meta_description: 'Alles over AI-telefonisten voor kleine bedrijven.',
      content_type: 'blogartikel',
      content_type_reason: 'Informatief onderwerp waar mensen eerst over lezen voor ze kopen.',
      target_audience_pain_point: 'Mkb-ondernemers die telefonisch onbereikbaar zijn tijdens drukte.',
      suggested_h2s: [{ heading: 'Wat is een AI-telefonist?', guidance: 'Leg het begrip uit.' }],
      differentiation_angle: 'Voicelabs focust op telefonie; Tessar kan breder mkb-verhaal benadrukken.',
      competitor_analysis: [
        { name: 'Voicelabs', covers: 'Telefonie-integraties en features.', gap: 'Geen mkb-specifieke voorbeelden.' },
      ],
      cta_direction: 'Gratis gesprek inplannen.',
      target_word_count: 1200,
      priority: 'lastig',
      priority_reason: 'Sterke, gevestigde spelers domineren alle 3 posities.',
    },
  },
  {
    output: {
      keyword: 'AI receptioniste voor bedrijven',
      search_intent: 'commercial',
      suggested_title: 'AI-receptioniste: de complete oplossing voor mkb',
      meta_description: 'Ontdek hoe een AI-receptioniste jouw bedrijf helpt.',
      content_type: 'dienstenpagina',
      content_type_reason: 'Keyword heeft koopintentie, dus een dienstenpagina converteert beter.',
      target_audience_pain_point: 'Ondernemers die klantcontact missen buiten kantooruren.',
      suggested_h2s: [{ heading: 'Wat doet Tessar?', guidance: 'Introduceer het product.' }],
      differentiation_angle: 'Aanloop AI is generiek; Tessar kan dieper op mkb-integraties ingaan.',
      competitor_analysis: [
        { name: 'Aanloop AI', covers: 'Algemene AI-receptioniste-uitleg.', gap: 'Geen concrete integratievoorbeelden.' },
      ],
      cta_direction: 'Demo aanvragen.',
      target_word_count: 900,
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
assert.ok(html.includes('<h2'), 'produces HTML, not markdown');
assert.ok(!html.includes('<script'), 'no script tags');
assert.ok(!html.includes('<style'), 'styling is inlined, not in a <style> block (mail clients strip those)');
assert.ok(
  html.includes('Informatief onderwerp waar mensen eerst over lezen voor ze kopen.'),
  'renders the content_type_reason justification next to the content type'
);
assert.ok(html.includes('Mkb-ondernemers die telefonisch onbereikbaar zijn tijdens drukte.'), 'renders target_audience_pain_point');
assert.ok(html.includes('Gratis gesprek inplannen.'), 'renders cta_direction');
assert.ok(html.includes('Voicelabs') && html.includes('Geen mkb-specifieke voorbeelden.'), 'renders competitor_analysis name + gap');
assert.ok(html.includes('informational') && html.includes('commercial'), 'renders search_intent per brief');

// Tessar house style (preview/assets/tessar-tokens.css, converted to hex for mail clients)
assert.ok(html.includes('#00BCD8') && html.includes('#0091CE'), 'header uses the Tessar gradient');
assert.ok(html.includes("IBM Plex Sans") && html.includes("IBM Plex Mono"), 'uses Tessar typography');
assert.ok(html.includes('#AF3E30'), "'lastig' priority uses the danger palette");
assert.ok(html.includes('#006C41'), "'makkelijk' priority uses the ok palette");

console.log('OK: build-email-html tests passed');
