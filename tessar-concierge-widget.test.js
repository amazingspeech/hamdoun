// Unit tests voor de pure streamparser van de Tess-widget.
// Draaien: node tessar-concierge-widget.test.js
// Zelfde stijl als n8n-workflows/src/*.test.js: kaal node:assert, geen
// testframework, geen dependencies.
const assert = require('node:assert');
const { parseStreamChunk } = require('./tessar-concierge-widget.js');

function run(name, fn) {
  try {
    fn();
    console.log('ok -', name);
  } catch (err) {
    console.error('FAIL -', name);
    console.error(err);
    process.exitCode = 1;
  }
}

// Realistisch stukje van de echte n8n-stream (gevangen tijdens diagnose,
// zie docs/superpowers/specs/2026-08-14-tess-widget-bugfixes-design.md).
function line(obj) { return JSON.stringify(obj) + '\n'; }
function beginLine() { return line({ type: 'begin', metadata: {} }); }
function itemLine(content) { return line({ type: 'item', content: content, metadata: {} }); }
function endLine() { return line({ type: 'end', metadata: {} }); }

run('losse turn: begin -> items -> end levert precies de geconcateneerde tekst op', () => {
  const state = { ended: false };
  const raw = beginLine() + itemLine('Hoi') + itemLine(' daar') + itemLine('!') + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Hoi daar!');
  assert.strictEqual(state.ended, true);
});

run('meerdere losse decoded chunks (zoals de echte reader-loop) accumuleren correct', () => {
  const state = { ended: false };
  let acc = '';
  acc += parseStreamChunk(beginLine(), state);
  acc += parseStreamChunk(itemLine('Deel een.'), state);
  acc += parseStreamChunk(itemLine(' Deel twee.'), state);
  acc += parseStreamChunk(endLine(), state);
  assert.strictEqual(acc, 'Deel een. Deel twee.');
});

run('BUG 1: twee begin/end-blokken in één respons -> alleen het eerste blok telt mee', () => {
  // Dit is het exacte patroon dat tijdens de live-reproductie is gevangen:
  // twee volledige agent-antwoorden, geconcateneerd, geen scheiding.
  const state = { ended: false };
  const raw =
    beginLine() +
    itemLine('Wat kost je nu het meeste tijd, of wat zou je graag anders willen doen?') +
    endLine() +
    beginLine() +
    itemLine('Dat is zeker iets voor jullie!') +
    endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(
    text,
    'Wat kost je nu het meeste tijd, of wat zou je graag anders willen doen?'
  );
  assert.ok(!text.includes('Dat is zeker iets voor jullie'), 'tweede blok mag niet doorsijpelen');
});

run('onherkenbare (niet-JSON) regels crashen niet en leveren geen tekst op', () => {
  const state = { ended: false };
  const raw = beginLine() + 'dit is geen json\n' + itemLine('Wel geldig.') + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Wel geldig.');
});

run('lege/whitespace-regels worden overgeslagen', () => {
  const state = { ended: false };
  const raw = '\n   \n' + beginLine() + itemLine('Tekst.') + '\n' + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Tekst.');
});

run('data:-prefix (SSE-stijl) wordt gestript voordat er geparsed wordt', () => {
  const state = { ended: false };
  const raw = 'data: ' + JSON.stringify({ type: 'item', content: 'Prefix-tekst' }) + '\n';
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Prefix-tekst');
});

run('fallback-velden (chunk/text/output) werken ook zonder "content"', () => {
  const state = { ended: false };
  const raw =
    line({ type: 'item', chunk: 'A' }) +
    line({ type: 'item', text: 'B' }) +
    line({ type: 'item', output: 'C' });
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'ABC');
});
