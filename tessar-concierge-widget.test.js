// Unit tests voor de pure streamparser van de Tess-widget.
// Draaien: node tessar-concierge-widget.test.js
// Zelfde stijl als n8n-workflows/src/*.test.js: kaal node:assert, geen
// testframework, geen dependencies.
const assert = require('node:assert');
const { parseStreamChunk, stripToolCallLeaks } = require('./tessar-concierge-widget.js');

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
  const state = { blockCount: 0 };
  const raw = beginLine() + itemLine('Hoi') + itemLine(' daar') + itemLine('!') + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Hoi daar!');
  assert.strictEqual(state.blockCount, 1);
});

run('meerdere losse decoded chunks (zoals de echte reader-loop) accumuleren correct', () => {
  const state = { blockCount: 0 };
  let acc = '';
  acc += parseStreamChunk(beginLine(), state);
  acc += parseStreamChunk(itemLine('Deel een.'), state);
  acc += parseStreamChunk(itemLine(' Deel twee.'), state);
  acc += parseStreamChunk(endLine(), state);
  assert.strictEqual(acc, 'Deel een. Deel twee.');
});

run('meerdere begin/end-blokken in één respons zijn LEGITIEM (aankondiging + antwoord na een tool-aanroep) en worden allebei getoond', () => {
  // Live gereproduceerd op 2026-08-14: een boekingsbevestiging bestond uit
  // exact dit patroon (aankondiging, dan het echte antwoord na
  // cal_boek_afspraak). Een eerdere versie van parseStreamChunk gooide het
  // tweede blok weg - de bezoeker zag toen alleen de aankondiging en daarna
  // niets meer, ook al was de boeking al gelukt. Beide blokken moeten nu
  // altijd behouden blijven, met een scheiding ertussen zodat ze niet als
  // "week!Fijn" aan elkaar plakken.
  const state = { blockCount: 0 };
  const raw =
    beginLine() +
    itemLine('Even checken wat er nog open is deze week!') +
    endLine() +
    beginLine() +
    itemLine('Fijn, er is wat ruimte deze week!') +
    endLine();
  const text = parseStreamChunk(raw, state);
  assert.ok(text.includes('Even checken wat er nog open is deze week!'), 'aankondiging moet blijven staan');
  assert.ok(text.includes('Fijn, er is wat ruimte deze week!'), 'het echte antwoord mag nooit verdwijnen');
  assert.ok(!text.includes('week!Fijn'), 'blokken mogen niet zonder scheiding aan elkaar plakken');
  assert.strictEqual(state.blockCount, 2);
});

run('onherkenbare (niet-JSON) regels crashen niet en leveren geen tekst op', () => {
  const state = { blockCount: 0 };
  const raw = beginLine() + 'dit is geen json\n' + itemLine('Wel geldig.') + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Wel geldig.');
});

run('lege/whitespace-regels worden overgeslagen', () => {
  const state = { blockCount: 0 };
  const raw = '\n   \n' + beginLine() + itemLine('Tekst.') + '\n' + endLine();
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Tekst.');
});

run('data:-prefix (SSE-stijl) wordt gestript voordat er geparsed wordt', () => {
  const state = { blockCount: 0 };
  const raw = 'data: ' + JSON.stringify({ type: 'item', content: 'Prefix-tekst' }) + '\n';
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'Prefix-tekst');
});

run('fallback-velden (chunk/text/output) werken ook zonder "content"', () => {
  const state = { blockCount: 0 };
  const raw =
    line({ type: 'item', chunk: 'A' }) +
    line({ type: 'item', text: 'B' }) +
    line({ type: 'item', output: 'C' });
  const text = parseStreamChunk(raw, state);
  assert.strictEqual(text, 'ABC');
});

// ----------------------- stripToolCallLeaks -----------------------

run('stripToolCallLeaks: knipt een live gevangen tool-aanroep-lek volledig weg', () => {
  // Exacte tekst gevangen op 2026-08-14 tijdens een boekingsbevestiging -
  // de velden matchen de $fromAI-parameters van de stuur_lead_naar_team-tool.
  const leak = 'Calling stuur_lead_naar_team with input: {"naam":"Testsessie Diagnose","email":"testsessie+widgetcheck@tessar.nl","telefoon":"0600000000","bedrijf":"Widget QA Test","sector":"onbekend"}';
  const text = 'Top, ik zet het voor je klaar!\n\n' + leak + '\n\nPerfect! Je kennismaking is geboekt.';
  const result = stripToolCallLeaks(text);
  assert.strictEqual(result, 'Top, ik zet het voor je klaar!\n\n\n\nPerfect! Je kennismaking is geboekt.');
  assert.ok(!result.includes('Calling'), 'geen spoor van de tool-aanroep mag overblijven');
  assert.ok(!result.includes('{'), 'geen JSON-fragment mag overblijven');
});

run('stripToolCallLeaks: geneste accolades in de tool-input worden correct gematcht', () => {
  const leak = 'Calling cal_boek_afspraak with input: {"attendee":{"name":"Job Nop","location":{"type":"integration"}}}';
  const text = 'Alvast bezig...\n\n' + leak + '\n\nKlaar!';
  const result = stripToolCallLeaks(text);
  assert.strictEqual(result, 'Alvast bezig...\n\n\n\nKlaar!');
});

run('stripToolCallLeaks: nog niet volledig binnengekomen JSON (geen sluitende accolade) wordt volledig verborgen tot die compleet is', () => {
  const partial = 'Momentje...\n\nCalling stuur_lead_naar_team with input: {"naam":"Jo';
  const partialResult = stripToolCallLeaks(partial);
  assert.strictEqual(partialResult, 'Momentje...\n\n');

  const complete = partial + 'b Nop","email":"x@y.nl"}\n\nGelukt!';
  const completeResult = stripToolCallLeaks(complete);
  assert.strictEqual(completeResult, 'Momentje...\n\n\n\nGelukt!');
});

run('stripToolCallLeaks: normale tekst zonder lek blijft volledig ongewijzigd', () => {
  const text = 'Hoi! Ik ben Tess. Wat kost een traject? Dat leggen we uit in de kennismaking.';
  assert.strictEqual(stripToolCallLeaks(text), text);
});
