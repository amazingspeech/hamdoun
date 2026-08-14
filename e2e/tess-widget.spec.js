// E2E-tests voor BUG 1 (dubbele/gelijktijdige requests). Draait tegen een
// lokale statische server die de echte, ongewijzigde
// tessar-concierge-widget.js serveert - geen kopie, geen gemockte widget.
// Alleen de netwerkoproep naar de n8n-webhook wordt onderschept, zodat de
// suite geen echte productie-calls maakt (kosten, en reproduceerbaarheid).
const { test, expect } = require('@playwright/test');
const { startServer } = require('./fixtures/static-server');

const WEBHOOK_PATTERN = '**/webhook/c1a2b3c4-1111-4ed4-9c97-e633ab209b8c/chat';

let server;
let baseURL;

test.beforeAll(async () => {
  ({ server, baseURL } = await startServer());
});

test.afterAll(async () => {
  await new Promise((resolve) => server.close(resolve));
});

async function mockWebhook(page, { requests, delayMs = 250, replyText = 'Test-antwoord.' }) {
  await page.route(WEBHOOK_PATTERN, async (route) => {
    requests.push(route.request().postData());
    await new Promise((r) => setTimeout(r, delayMs));
    const body =
      JSON.stringify({ type: 'begin' }) + '\n' +
      JSON.stringify({ type: 'item', content: replyText }) + '\n' +
      JSON.stringify({ type: 'end' }) + '\n';
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*' },
      body
    });
  });
}

async function openPanelAndGetInput(page) {
  await page.goto(baseURL + '/e2e/fixtures/widget-host.html');
  await page.click('.tsc-launcher');
  const input = page.locator('[data-tsc-input]');
  await expect(input).toBeVisible();
  return input;
}

test('Enter drukken, tijdens het wachten opnieuw typen en weer Enter -> precies 1 fetch-aanroep', async ({ page }) => {
  // Let op: Enter op een LEEG veld (bijv. twee keer snel Enter zonder
  // opnieuw te typen) is al vacuum-veilig, want sendMessage() cleart
  // inputEl.value synchroon voordat de eerste await - een tweede druk op
  // hetzelfde lege veld doet sowieso niets, met of zonder lock. Het echte
  // gat (voor de fix) zat in het scenario hieronder: de bezoeker typt een
  // NIEUW bericht terwijl het eerste antwoord nog onderweg is en drukt
  // opnieuw Enter, ruim binnen 100ms na het versturen van bericht 1.
  const requests = [];
  await mockWebhook(page, { requests, delayMs: 400 });
  const input = await openPanelAndGetInput(page);

  await input.fill('Wat kost een traject?');
  await input.press('Enter'); // verzoek 1 vertrekt, blijft 400ms hangen
  await page.waitForTimeout(50); // < 100ms: verzoek 1 loopt gegarandeerd nog
  await input.fill('En hoe lang duurt het?');
  await input.press('Enter'); // moet door de request-lock genegeerd worden

  await page.waitForTimeout(600);

  expect(requests.length).toBe(1);
  // 1 statische begroeting (bij openPanel) + 1 echte reply = 2 bot-bubbels.
  await expect(page.locator('.tsc-msg-bot')).toHaveCount(2);
  await expect(page.locator('.tsc-msg-bot').last()).toContainText('Test-antwoord.');
});

test('dubbelklik op de verstuurknop binnen 100ms -> precies 1 fetch-aanroep', async ({ page }) => {
  const requests = [];
  await mockWebhook(page, { requests });
  const input = await openPanelAndGetInput(page);
  const sendBtn = page.locator('[data-tsc-send]');

  await input.fill('Is dit iets voor mijn bedrijf?');
  await Promise.all([sendBtn.click(), sendBtn.click({ force: true }).catch(() => {})]);

  await page.waitForTimeout(500);
  expect(requests.length).toBe(1);
});

test('na een afgeronde beurt werkt een nieuw bericht gewoon (de lock blijft niet hangen)', async ({ page }) => {
  const requests = [];
  await mockWebhook(page, { requests, delayMs: 50 });
  const input = await openPanelAndGetInput(page);

  await input.fill('Eerste bericht');
  await input.press('Enter');
  await page.waitForTimeout(300);

  await input.fill('Tweede bericht');
  await input.press('Enter');
  await page.waitForTimeout(300);

  expect(requests.length).toBe(2);
  // 1 begroeting + 2 replies = 3 bot-bubbels.
  await expect(page.locator('.tsc-msg-bot')).toHaveCount(3);
});

test('meerdere begin/end-blokken in één respons (aankondiging + antwoord na een tool-aanroep) worden allebei getoond, niet weggegooid', async ({ page }) => {
  // Regressietest voor een bug die de eerdere versie van deze fix zelf
  // introduceerde: n8n stuurt bij een tool-aanroep vaak een korte
  // aankondiging (begin/item/end) gevolgd door het echte antwoord (nog een
  // begin/item/end) in DEZELFDE respons - dit is normaal, geen corruptie.
  // Live gereproduceerd op 2026-08-14: een boekingsbevestiging bestond uit
  // precies dit patroon, en de bezoeker zag na de aankondiging niets meer
  // omdat het tweede (echte) blok werd genegeerd. Dat mag nooit meer.
  const requests = [];
  await page.route(WEBHOOK_PATTERN, async (route) => {
    requests.push(route.request().postData());
    const body =
      JSON.stringify({ type: 'begin' }) + '\n' +
      JSON.stringify({ type: 'item', content: "Ik zet 'm even voor je klaar." }) + '\n' +
      JSON.stringify({ type: 'end' }) + '\n' +
      JSON.stringify({ type: 'begin' }) + '\n' +
      JSON.stringify({ type: 'item', content: 'Mooi, je kennismaking staat in!' }) + '\n' +
      JSON.stringify({ type: 'end' }) + '\n';
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*' },
      body
    });
  });
  const input = await openPanelAndGetInput(page);

  await input.fill('Vraag');
  await input.press('Enter');
  await page.waitForTimeout(300);

  const lastBubble = page.locator('.tsc-msg-bot').last();
  await expect(lastBubble).toContainText('Ik zet');
  await expect(lastBubble).toContainText('Mooi, je kennismaking staat in!');
});
