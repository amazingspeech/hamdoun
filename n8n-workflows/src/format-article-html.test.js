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
