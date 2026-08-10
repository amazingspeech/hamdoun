# Prijzen-pagina Herziening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise `preview/prijzen.html` to soften an over-confident pricing promise, add a
concurrentie-onderbouwde vaste prijs on the entry-level "Quick win" package, add a new
"AI-readiness scan" package between the free intro call and Quick win, and add an FAQ item
covering payment/ownership reassurance.

**Architecture:** Single static HTML page, hand-authored inline styles (no build step, no CSS
framework) — same pattern as every other page in `preview/`. All changes are content/markup edits
within the existing section structure; no new files, no new CSS classes beyond what's already
defined in the page's `<style>` block.

**Tech Stack:** Vanilla HTML/CSS (inline styles, oklch colors, `clamp()`), no JS changes needed —
the existing `[data-reveal]` scroll-animation and FAQ `<details>` mechanisms already handle any new
elements that reuse those patterns.

## Global Constraints

- Hero subtitle changes from *"Vaste scope, vaste prijs, altijd vooraf besproken. Geen
  verrassingen achteraf. Klein beginnen kan, groot bouwen ook."* to *"Vaste scope, vaste prijs
  zodra we de scope kennen. Klein beginnen kan, groot bouwen ook."* — exact wording, do not
  paraphrase.
- New FAQ item (both the visible accordion AND the `application/ld+json` FAQPage schema) — exact
  Q&A text: Q: *"Hoe zit het met betaling en eigendom?"* A: *"Betalingsafspraken leggen we vast in
  de offerte, zodra de scope duidelijk is — geen verrassingen daar ook. De code en workflows die
  we bouwen zijn en blijven van jou: geen lock-in, geen abonnement dat je vasthoudt."*
- New "AI-readiness scan" package: titel "AI-readiness scan", subtitel "Concreet rapport, geen
  vrijblijvend gesprek", prijs "vanaf €295", duur "2-3 dagen", exact 3 bullets (see Task 2), CTA
  text "Vraag een scan aan".
- Quick win package: price becomes "€1.250" (not "vanaf €1.250" — it's a fixed price), 5 bullets
  (see Task 3), a money-back reassurance line, and a "Pilotproject" callout box with exact copy
  (see Task 3) — none of this text may be paraphrased, it was deliberately worded to avoid a false
  market-wide claim.
- Proof of Concept and Volledige implementatie packages are NOT touched — stay exactly as they are
  ("Op aanvraag", same bullets).
- No changes to `chatbots.html`, no new ToS/voorwaarden page, no changes outside
  `preview/prijzen.html`.

---

### Task 1: Soften the hero promise, add the payment/ownership FAQ item

**Files:**
- Modify: `preview/prijzen.html` (hero subtitle ~line 107, FAQ JSON-LD ~lines 53-75, visible FAQ
  accordion ~lines 190-210)

**Interfaces:** None — this task only touches static text/markup, no shared state with other
tasks.

- [ ] **Step 1: Soften the hero subtitle**

In `preview/prijzen.html`, find:
```html
    <p style="font:400 clamp(1rem,1.6vw,1.125rem)/1.7 'IBM Plex Sans';color:oklch(75% 0.10 250);margin:0;">Vaste scope, vaste prijs, altijd vooraf besproken. Geen verrassingen achteraf. Klein beginnen kan, groot bouwen ook.</p>
```
Replace with:
```html
    <p style="font:400 clamp(1rem,1.6vw,1.125rem)/1.7 'IBM Plex Sans';color:oklch(75% 0.10 250);margin:0;">Vaste scope, vaste prijs zodra we de scope kennen. Klein beginnen kan, groot bouwen ook.</p>
```

- [ ] **Step 2: Add the 4th FAQ item to the JSON-LD FAQPage schema**

Find:
```html
    {
      "@type": "Question",
      "name": "Waarom een vaste prijs in plaats van een uurtarief?",
      "acceptedAnswer": { "@type": "Answer", "text": "Bij een uurtarief ligt het risico van uitloop bij jou. Bij een vaste prijs, afgesproken nadat de scope in de kennismaking is bepaald, ligt dat risico bij Tessar — de prijs verandert niet meer nadat de scope vaststaat." }
    }
  ]
}
</script>
```
Replace with:
```html
    {
      "@type": "Question",
      "name": "Waarom een vaste prijs in plaats van een uurtarief?",
      "acceptedAnswer": { "@type": "Answer", "text": "Bij een uurtarief ligt het risico van uitloop bij jou. Bij een vaste prijs, afgesproken nadat de scope in de kennismaking is bepaald, ligt dat risico bij Tessar — de prijs verandert niet meer nadat de scope vaststaat." }
    },
    {
      "@type": "Question",
      "name": "Hoe zit het met betaling en eigendom?",
      "acceptedAnswer": { "@type": "Answer", "text": "Betalingsafspraken leggen we vast in de offerte, zodra de scope duidelijk is — geen verrassingen daar ook. De code en workflows die we bouwen zijn en blijven van jou: geen lock-in, geen abonnement dat je vasthoudt." }
    }
  ]
}
</script>
```

- [ ] **Step 3: Add the 4th FAQ item to the visible accordion**

Find:
```html
        <details class="faq-item" style="border:1px solid oklch(90% 0.006 90);border-radius:10px;padding:18px 22px;background:oklch(98% 0.004 90);">
          <summary style="display:flex;align-items:center;justify-content:space-between;gap:16px;font:600 1rem/1.4 'IBM Plex Sans';color:oklch(18% 0.02 255);">
            <span>Waarom een vaste prijs in plaats van een uurtarief?</span>
            <div class="icon icon-chevron-down faq-chevron" style="width:18px;height:18px;color:oklch(48% 0.12 230);transition:transform 200ms ease;flex-shrink:0;"></div>
          </summary>
          <p style="font:400 0.9375rem/1.65 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:14px 0 0;">Bij een uurtarief ligt het risico van uitloop bij jou. Bij een vaste prijs, afgesproken nadat de scope in de kennismaking is bepaald, ligt dat risico bij Tessar — de prijs verandert niet meer nadat de scope vaststaat.</p>
        </details>
    </div>
```
Replace with:
```html
        <details class="faq-item" style="border:1px solid oklch(90% 0.006 90);border-radius:10px;padding:18px 22px;background:oklch(98% 0.004 90);">
          <summary style="display:flex;align-items:center;justify-content:space-between;gap:16px;font:600 1rem/1.4 'IBM Plex Sans';color:oklch(18% 0.02 255);">
            <span>Waarom een vaste prijs in plaats van een uurtarief?</span>
            <div class="icon icon-chevron-down faq-chevron" style="width:18px;height:18px;color:oklch(48% 0.12 230);transition:transform 200ms ease;flex-shrink:0;"></div>
          </summary>
          <p style="font:400 0.9375rem/1.65 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:14px 0 0;">Bij een uurtarief ligt het risico van uitloop bij jou. Bij een vaste prijs, afgesproken nadat de scope in de kennismaking is bepaald, ligt dat risico bij Tessar — de prijs verandert niet meer nadat de scope vaststaat.</p>
        </details>
        <details class="faq-item" style="border:1px solid oklch(90% 0.006 90);border-radius:10px;padding:18px 22px;background:oklch(98% 0.004 90);">
          <summary style="display:flex;align-items:center;justify-content:space-between;gap:16px;font:600 1rem/1.4 'IBM Plex Sans';color:oklch(18% 0.02 255);">
            <span>Hoe zit het met betaling en eigendom?</span>
            <div class="icon icon-chevron-down faq-chevron" style="width:18px;height:18px;color:oklch(48% 0.12 230);transition:transform 200ms ease;flex-shrink:0;"></div>
          </summary>
          <p style="font:400 0.9375rem/1.65 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:14px 0 0;">Betalingsafspraken leggen we vast in de offerte, zodra de scope duidelijk is — geen verrassingen daar ook. De code en workflows die we bouwen zijn en blijven van jou: geen lock-in, geen abonnement dat je vasthoudt.</p>
        </details>
    </div>
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "zodra we de scope kennen" preview/prijzen.html
grep -c "Hoe zit het met betaling en eigendom" preview/prijzen.html
```
Expected: both print `2` (one occurrence each in the JSON-LD, one in the visible accordion — for
the betaling question; the hero subtitle grep should print `1`. Run them separately if unsure):
```bash
grep -c "zodra we de scope kennen" preview/prijzen.html
```
Expected: `1`
```bash
grep -c "Hoe zit het met betaling en eigendom" preview/prijzen.html
```
Expected: `2` (JSON-LD `"name"` + visible `<span>`)

- [ ] **Step 5: Commit**

```bash
git add preview/prijzen.html
git commit -m "Soften pricing hero promise, add payment/ownership FAQ item"
```

---

### Task 2: Add the "AI-readiness scan" package card

**Files:**
- Modify: `preview/prijzen.html` (meta description ~line 7, pricing grid ~lines 118-121, new card
  inserted between the Kennismaking card and the Quick win card)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: a 5th pricing card in the grid. Task 3 modifies the Quick win card, which is the next
  sibling after this new card — Task 3's diff assumes this card already exists between Kennismaking
  and Quick win.

- [ ] **Step 1: Update the meta description (4 → 5 pakketten)**

Find:
```html
<meta name="description" content="Vaste scope, vaste prijs, altijd vooraf besproken. Vier pakketten van gratis kennismaking tot volledige implementatie, voor het Nederlandse en Europese mkb.">
```
Replace with:
```html
<meta name="description" content="Vaste scope, vaste prijs, altijd vooraf besproken. Vijf pakketten van gratis kennismaking tot volledige implementatie, voor het Nederlandse en Europese mkb.">
```

- [ ] **Step 2: Insert the new card between Kennismaking and Quick win**

Find (the closing of the Kennismaking card, immediately followed by the Quick win card's opening):
```html
          <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:12px 20px;border-radius:6px;text-align:center;font-weight:600;font-size:0.9375rem;transition:all 200ms ease;white-space:nowrap;">Plan gesprek</a>
        </div>
        <div data-reveal style="background:#FFF;border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
          <h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3 'IBM Plex Sans';margin:0 0 8px;color:oklch(18% 0.02 255);">Quick win</h3>
```
Replace with:
```html
          <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:12px 20px;border-radius:6px;text-align:center;font-weight:600;font-size:0.9375rem;transition:all 200ms ease;white-space:nowrap;">Plan gesprek</a>
        </div>
        <div data-reveal style="background:#FFF;border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
          <h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3 'IBM Plex Sans';margin:0 0 8px;color:oklch(18% 0.02 255);">AI-readiness scan</h3>
          <p style="font:400 0.9375rem/1.6 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:0 0 20px;">Concreet rapport, geen vrijblijvend gesprek</p>
          <div style="margin:20px 0;padding:20px;background:oklch(99% 0.003 90);border-radius:8px;border:1px solid oklch(91% 0.006 90);">
            <div style="font:700 clamp(1.875rem,3vw,2.25rem)/1 'IBM Plex Mono';color:oklch(48% 0.12 230);">vanaf €295</div>
            <div style="font:400 0.875rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);margin-top:6px;">2-3 dagen</div>
          </div>
          <ul style="list-style:none;margin:0 0 24px;padding:0;display:flex;flex-direction:column;gap:12px;flex:1;">
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Analyse van je huidige processen en systemen</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Concreet rapport met kansen, geschat rendement en risico's</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Eén aanbevolen vervolgstap (Quick win, PoC of volledige implementatie)</span></li>
          </ul>
          <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:12px 20px;border-radius:6px;text-align:center;font-weight:600;font-size:0.9375rem;transition:all 200ms ease;white-space:nowrap;">Vraag een scan aan</a>
        </div>
        <div data-reveal style="background:#FFF;border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
          <h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3 'IBM Plex Sans';margin:0 0 8px;color:oklch(18% 0.02 255);">Quick win</h3>
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "AI-readiness scan" preview/prijzen.html
grep -c "Vijf pakketten" preview/prijzen.html
```
Expected: first prints `1` (the `<h3>`), second prints `1`.

```bash
python3 -c "
import re
html = open('preview/prijzen.html').read()
for tag in ['div','section','header','footer','nav','ul','li','h3']:
    opens = len(re.findall(r'<'+tag+r'(\s|>)', html))
    closes = len(re.findall(r'</'+tag+r'>', html))
    assert opens == closes, f'{tag}: open={opens} close={closes} MISMATCH'
print('all tags balanced')
"
```
Expected: `all tags balanced`

- [ ] **Step 4: Commit**

```bash
git add preview/prijzen.html
git commit -m "Add AI-readiness scan package to prijzen.html"
```

---

### Task 3: Quick win — fixed price, expanded scope, guarantee, pilot offer

**Files:**
- Modify: `preview/prijzen.html` (the Quick win card, immediately after the AI-readiness scan card
  added in Task 2)

**Interfaces:**
- Consumes: the AI-readiness scan card from Task 2 (this task's diff targets the Quick win card
  that now sits right after it — if Task 2 wasn't applied first, the find-string in Step 1 below
  still uniquely matches the Quick win card's own content, so this task is resilient to task order,
  but the plan assumes Task 2 ran first per the numbering).
- Produces: nothing further tasks depend on — this is the last content change in the plan.

- [ ] **Step 1: Replace the Quick win card's price, bullets, and add the guarantee + pilot callout**

Find:
```html
          <p style="font:400 0.9375rem/1.6 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:0 0 20px;">Eén proces automatiseren</p>
          <div style="margin:20px 0;padding:20px;background:oklch(99% 0.003 90);border-radius:8px;border:1px solid oklch(91% 0.006 90);">
            <div style="font:700 clamp(1.875rem,3vw,2.25rem)/1 'IBM Plex Mono';color:oklch(48% 0.12 230);">Op aanvraag</div>
            <div style="font:400 0.875rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);margin-top:6px;">1 week</div>
          </div>
          <ul style="list-style:none;margin:0 0 24px;padding:0;display:flex;flex-direction:column;gap:12px;flex:1;">
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Eén concreet proces geautomatiseerd</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Koppeling met 1-2 bestaande systemen</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Overdracht en documentatie</span></li>
          </ul>
          <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:12px 20px;border-radius:6px;text-align:center;font-weight:600;font-size:0.9375rem;transition:all 200ms ease;white-space:nowrap;">Bespreek dit pakket</a>
        </div>
        <div data-reveal style="background:#FFF;border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
          <h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3 'IBM Plex Sans';margin:0 0 8px;color:oklch(18% 0.02 255);">Proof of Concept</h3>
```
Replace with:
```html
          <p style="font:400 0.9375rem/1.6 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:0 0 20px;">Eén proces automatiseren</p>
          <div style="margin:20px 0;padding:20px;background:oklch(99% 0.003 90);border-radius:8px;border:1px solid oklch(91% 0.006 90);">
            <div style="font:700 clamp(1.875rem,3vw,2.25rem)/1 'IBM Plex Mono';color:oklch(48% 0.12 230);">€1.250</div>
            <div style="font:400 0.875rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);margin-top:6px;">1 week</div>
          </div>
          <ul style="list-style:none;margin:0 0 16px;padding:0;display:flex;flex-direction:column;gap:12px;flex:1;">
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Eén concreet proces geautomatiseerd</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Koppeling met 1-2 bestaande systemen (standaard API — maatwerk-koppelingen apart besproken)</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>30 dagen nazorg</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>2 revisierondes inbegrepen</span></li>
            <li style="display:flex;gap:10px;align-items:flex-start;font:400 0.9375rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);"><div class="icon icon-check" style="width:15px;height:15px;color:oklch(48% 0.12 230);margin-top:3px;flex-shrink:0;"></div><span>Overdracht en documentatie</span></li>
          </ul>
          <p style="font:400 0.8125rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:0 0 16px;">Niet tevreden? Volledige terugbetaling — dat leggen we ook zo vast in de offerte.</p>
          <div style="margin:0 0 20px;padding:14px 16px;background:oklch(70% 0.14 220 / 0.08);border:1px solid oklch(70% 0.14 220 / 0.25);border-radius:8px;">
            <div style="font:600 0.8125rem/1.4 'IBM Plex Sans';color:oklch(18% 0.02 255);margin-bottom:4px;">🧭 Pilotproject — €795 <span style="font-weight:400;color:oklch(46% 0.012 140);">i.p.v. €1.250</span></div>
            <p style="font:400 0.8125rem/1.5 'IBM Plex Sans';color:oklch(46% 0.012 140);margin:0;">Nog niet eerder met Tessar in jouw sector gewerkt? Als pilotklant bouwen we samen de aanpak voor jouw sector uit, tegen pilotprijs. In ruil delen we (met jouw akkoord) wat we hebben gebouwd als voorbeeld voor de volgende in jouw sector.</p>
          </div>
          <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:12px 20px;border-radius:6px;text-align:center;font-weight:600;font-size:0.9375rem;transition:all 200ms ease;white-space:nowrap;">Bespreek dit pakket</a>
        </div>
        <div data-reveal style="background:#FFF;border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
          <h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3 'IBM Plex Sans';margin:0 0 8px;color:oklch(18% 0.02 255);">Proof of Concept</h3>
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -c "€1.250" preview/prijzen.html
grep -c "Pilotproject" preview/prijzen.html
grep -c "30 dagen nazorg" preview/prijzen.html
grep -c "2 revisierondes inbegrepen" preview/prijzen.html
grep -c "Volledige terugbetaling" preview/prijzen.html
```
Expected: `€1.250` → `2` (price box + pilot callout's "i.p.v. €1.250"); the other four each → `1`.

```bash
grep -c "Op aanvraag" preview/prijzen.html
```
Expected: `2` (Proof of Concept and Volledige implementatie — unchanged, confirms this task didn't
touch them).

```bash
python3 -c "
import re
html = open('preview/prijzen.html').read()
for tag in ['div','section','header','footer','nav','ul','li','h3','p']:
    opens = len(re.findall(r'<'+tag+r'(\s|>)', html))
    closes = len(re.findall(r'</'+tag+r'>', html))
    assert opens == closes, f'{tag}: open={opens} close={closes} MISMATCH'
print('all tags balanced')
"
```
Expected: `all tags balanced`

- [ ] **Step 3: Commit**

```bash
git add preview/prijzen.html
git commit -m "Quick win: fixed price €1.250, 30 dagen nazorg, geld-terug-garantie, pilotproject-aanbod"
```

---

### Task 4: Full-page verification

**Files:** none modified — read-only checks over `preview/prijzen.html`.

**Interfaces:**
- Consumes: the final state of the page from Tasks 1-3.
- Produces: a pass/fail report used as the gate before offering to push/deploy.

- [ ] **Step 1: Confirm Proof of Concept and Volledige implementatie are byte-identical to before
  this plan**

Run (from the worktree root, replace `<BASE>` with the commit hash immediately before Task 1 was
started — the implementer/controller running this step has that hash from their own session):
```bash
git diff <BASE> HEAD -- preview/prijzen.html | grep -A2 "Proof of Concept\|Volledige implementatie"
```
Expected: no `-`/`+` lines touching either card's price, duration, or bullet content — only
context lines (both packages were explicitly out of scope for this plan).

- [ ] **Step 2: Confirm the pricing grid now has 5 cards**

Run:
```bash
grep -c '<h3 style="font:600 clamp(1.0625rem,1.8vw,1.25rem)/1.3' preview/prijzen.html
```
Expected: `5` (Kennismaking, AI-readiness scan, Quick win, Proof of Concept, Volledige
implementatie).

- [ ] **Step 3: Full tag-balance check**

Run:
```bash
python3 -c "
import re
html = open('preview/prijzen.html').read()
for tag in ['div','section','header','footer','main','nav','ul','li','h1','h2','h3','p','a','details','summary','script','style']:
    opens = len(re.findall(r'<'+tag+r'(\s|>)', html))
    closes = len(re.findall(r'</'+tag+r'>', html))
    assert opens == closes, f'{tag}: open={opens} close={closes} MISMATCH'
print('all tags balanced')
"
```
Expected: `all tags balanced`

- [ ] **Step 4: Visual check in a real browser**

Serve `preview/` locally and open `prijzen.html`:
```bash
python3 -m http.server 8813 --directory preview
```
Open `http://localhost:8813/prijzen.html`. Confirm:
- 5 cards render in the grid, wrapping sensibly on narrow widths (no overflow/clipping — this page
  already has the site-wide nav-overflow fix, but check the pricing grid itself too).
- The AI-readiness scan card sits between Kennismaking and Quick win, styled identically to its
  siblings (same border/radius/padding, not visually distinct).
- The Quick win card shows a real `€1.250` price, the 5 bullets, the money-back line, and the blue
  pilotproject callout box — and that callout box doesn't overflow or look cramped.
- The 4th FAQ item ("Hoe zit het met betaling en eigendom?") opens/closes like the other three.
- The hero subtitle reads "Vaste scope, vaste prijs zodra we de scope kennen. Klein beginnen kan,
  groot bouwen ook." with no leftover "Geen verrassingen achteraf" text anywhere on the page.

Stop the server with Ctrl-C when done.

- [ ] **Step 5: Report status**

Summarize: commits made on this plan, and that the work is ready for the user to review before
pushing to `main` (which triggers the production deploy).
