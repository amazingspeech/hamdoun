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

test('twee gelijktijdige beurten voor dezelfde sessie op serverniveau blijven client-side ontkoppeld (stream-boundary-hardening)', async ({ page }) => {
  // Simuleert het exacte, live gereproduceerde defect: n8n's streaming-
  // webhook die twee volledige antwoorden op één HTTP-respons plakt. Ook al
  // zou de request-lock om wat voor reden dan ook omzeild worden, mag de
  // widget nooit twee beurten in één bubbel tonen.
  const requests = [];
  await page.route(WEBHOOK_PATTERN, async (route) => {
    requests.push(route.request().postData());
    const body =
      JSON.stringify({ type: 'begin' }) + '\n' +
      JSON.stringify({ type: 'item', content: 'Eerste antwoord.' }) + '\n' +
      JSON.stringify({ type: 'end' }) + '\n' +
      JSON.stringify({ type: 'begin' }) + '\n' +
      JSON.stringify({ type: 'item', content: 'Tweede antwoord.' }) + '\n' +
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
  await expect(lastBubble).toContainText('Eerste antwoord.');
  await expect(lastBubble).not.toContainText('Tweede antwoord.');
});
