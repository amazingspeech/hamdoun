# Tess-widget: systeemprompt-diff en teststrategie (review, nog niet geïmplementeerd)

**Datum:** 2026-08-14
**Repo:** `amazingspeech/hamdoun` (lokaal `/Users/hamdeco/development/hamdoun`)
**Status:** ter review — diagnose is afgerond, dit document beschrijft de voorgestelde wijzigingen.
Zie sessie-diagnoserapport voor de onderliggende bewijsvoering per bug.

Al toegepast (kleine, geïsoleerde fix, bevestigd door gebruiker): `stuur_lead_naar_team` in de
n8n-workflow "Tessar AI Concierge - Website" stuurt nu naar `info@tessar.nl` in plaats van naar
`scrapingscrambling@gmail.com`.

Alles hieronder is **nog niet doorgevoerd**.

## 1. Systeemprompt-diff (n8n-node "Tessar Concierge Agent" → `options.systemMessage`)

De systeemprompt leeft in n8n, niet in deze repo — onderstaande diffs beschrijven exact welke
tekst verandert. Toegepast worden ze via de n8n API, pas na akkoord.

### 1a. Tijd- en tijdzonecontext (fix BUG 2)

Node "Prompt met datum" geeft nu alleen de datum mee, nooit de klok­tijd:

```diff
- "value": "={{ 'Vandaag is ' + $now.setZone('Europe/Amsterdam').toFormat('cccc d MMMM yyyy') + '. Gebruik deze datum om relatieve tijdsaanduidingen (morgen, overmorgen, volgende week dinsdag, etc.) om te rekenen naar een concrete datum (YYYY-MM-DD) voor tool-aanroepen.\n\nBericht van bezoeker: ' + ($json.chatInput || $json.testBericht) }}"
+ "value": "={{ 'Vandaag is ' + $now.setZone('Europe/Amsterdam').toFormat('cccc d MMMM yyyy') + ', het is nu ' + $now.setZone('Europe/Amsterdam').toFormat('HH:mm') + ' (Europe/Amsterdam). Gebruik dit om relatieve tijdsaanduidingen (morgen, overmorgen, volgende week dinsdag, etc.) om te rekenen naar een concrete datum (YYYY-MM-DD) voor tool-aanroepen, en om — indien je toch voor een dagdeel-gebonden opening kiest — deze te laten kloppen met het huidige tijdstip.\n\nBericht van bezoeker: ' + ($json.chatInput || $json.testBericht) }}"
```

Bijbehorende regel in de systeemprompt zelf (nieuwe regel, toegevoegd na regel 16):

```diff
+ 16b. Gebruik nooit een dagdeel-gebonden begroeting (Goedemorgen/Goedemiddag/Goedenavond) tenzij
+ je in dit bericht een betrouwbaar tijdstip hebt meegekregen (zie boven aan dit bericht). Twijfel
+ je, of ontbreekt het tijdstip: open dan neutraal, zonder dagdeel ("Hoi, leuk dat je er bent" i.p.v.
+ "Goedemorgen").
```

**Jouw voorkeur uit de opdracht** ("neutrale opening tenzij tijd betrouwbaar bekend") is hiermee
gevolgd: nu de tijd wél altijd meegegeven wordt, mag een dagdeel-begroeting best, maar alleen als
die klopt.

### 1b. Geen belofte vóór een geslaagde actie (fix BUG 5, generieke regel)

De letterlijk voorgeschreven tekst in de "BELANGRIJKE UPDATE"-sectie, stap 3:

```diff
- "Top, dan zet ik 'm vast! Heb je een voorkeur voor bellen of videobellen? En dan heb ik nog nodig:
+ "Top, die tijd hou ik erbij zodra ik je gegevens heb! Heb je een voorkeur voor bellen of videobellen? En dan heb ik nog nodig:
  - Voornaam
  - Achternaam
  - Bedrijfsnaam
  - E-mailadres
  - Telefoonnummer"
```

Plus een generieke regel (nieuw, regel 24 — voorkomt dat dit patroon ergens anders in de prompt
terugsluipt):

```diff
+ 24. Beloof of impliceer nooit dat een actie al voltooid is (boeking, bevestigingsmail, notitie)
+ voordat de bijbehorende tool succesvol is teruggekomen (zie regel 23). Gebruik voor een actie die
+ nog moet gebeuren altijd voorwaardelijke/toekomstige taal ("zodra ik je gegevens heb, boek ik 'm
+ in"), nooit voltooide-tijd-taal ("ik heb 'm vast gezet", "dan zet ik 'm vast", "ik heb je een
+ mail gestuurd").
```

### 1c. Bevestig verstrekte gegevens, vraag nooit dubbel (fix BUG 3-gedrag)

Nieuwe regel (25), aansluitend bij regel 4 (stuur_lead_naar_team) en de BELANGRIJKE UPDATE-sectie:

```diff
+ 25. Wanneer een bezoeker een of meerdere gevraagde contactgegevens spontaan geeft — ook als dat
+ niet alle gevraagde velden zijn — bevestig kort en concreet welke gegevens je hebt genoteerd, en
+ vraag daarna uitsluitend naar wat nog ontbreekt. Vraag nooit opnieuw naar iets dat al gegeven is,
+ en val bij voortgang nooit terug op een generieke oproep tot een kennismaking in plaats van de
+ ontbrekende velden te benoemen.
```

### 1d. Meta-klachten van de bezoeker oppikken (fix BUG 4/7-gedrag, voor zover model-kant)

```diff
+ 26. Als een bezoeker aangeeft dat je jezelf herhaalt, dat je iets al eerder vroeg, of dat je een
+ fout maakte: erken dat kort en concreet (één zin, geen overdreven excuus), en ga expliciet terug
+ naar het punt waar het gesprek was blijven steken — bijvoorbeeld de eerder gevraagde gegevens of
+ het eerder besproken onderwerp. Ga nooit terug naar de generieke oproep tot een kennismaking als
+ reactie op zo'n opmerking.
```

*Kanttekening:* de meeste concrete BUG 4/7-gevallen bleken het gevolg van de widget-berichtenlimiet
(zie §2) die het bericht nooit bij het model laat aankomen — deze regel is een aanvullende
vangnet-laag voor gevallen waarin het bericht wél aankomt maar het model zelf niet goed reageert.

### 1e. Toon: minder ingewisselbare complimenten (kwaliteitscheck, jouw verzoek)

Amendement op regel 16:

```diff
  16. Schrijf menselijk, niet als een samenvatting-machine: gewone spreektaal, samentrekkingen
  mogen ("je", "we", "dat werkt zo"), varieer je zinsbouw, en reageer af en toe eerst kort op wat
  de bezoeker zegt voordat je verdergaat (bijv. "Goede vraag" of "Snap ik") in plaats van meteen met
  feiten te openen. Dit staat los van regel 8: blijf altijd eerlijk dat je een AI bent, menselijk
  schrijven betekent natuurlijk klinken, niet doen alsof je een mens bent.
+ Herhaal nooit dezelfde openingszin of hetzelfde compliment binnen één gesprek (bijv. niet
+ meermaals "Heel goed!" of "Dat klinkt als precies het soort werk waar we mee helpen") — varieer,
+ of laat de opener gewoon weg als je kort daarvoor al iets vergelijkbaars zei.
```

## 2. Widget-side wijzigingen (`tessar-concierge-widget.js`) — voorstel, nog niet toegepast

| # | Wijziging | Regels | Reden |
|---|---|---|---|
| 1 | `isSending`-vlag: blokkeer een nieuw `sendMessage()`-verzoek zolang er nog een loopt voor dezelfde sessie (niet alleen `sendBtn.disabled`, ook de Enter-handler moet 'm respecteren) | 384-463 | Directe fix van de race die BUG 1 live reproduceerde |
| 2 | Stuur de lokale tijd (`new Date().toISOString()` + tijdzone-aanduiding) mee in `metadata` | 411-416 | Redundante, snellere tijdcontext naast de n8n-kant (§1a); kost niets, geen downside |
| 3 | Defensieve stream-boundary-check: negeer/log content die binnenkomt ná een `type:"end"`-event zonder nieuwe `type:"begin"` in dezelfde beurt | 357-375, 421-437 | Extra vangnet tegen precies het mechanisme dat de live race liet zien, ook als de request-lock (1) om wat voor reden dan ook faalt |
| 4 | `maxMessagesPerSession`: **besluit nodig van jou** — nu 5, en het gedrag bij overschrijding is een silent drop (bericht wordt getoond maar nooit verstuurd). Voorstel: verhoog naar bijv. 15 én stuur bij het bereiken van de limiet het bericht nog gewoon door (het gesprek eindigt netjes via de systeemprompt in plaats van via een harde client-side afkap) | 55-56, 388-395 | Structurele oorzaak van BUG 3/4/6/7 |

Punt 4 heeft een productbeslissing nodig (kosten vs. conversie) — daar wacht ik mee tot je akkoord
geeft op de rest.

## 3. Teststrategie (overzicht — code volgt na akkoord)

| Test | Type | Wat het aantoont |
|---|---|---|
| 1. Eén bericht → precies één antwoord-bubbel, ook bij dubbele submit binnen 100ms | Unit (widget, jsdom) | `isSending`-guard werkt clientside |
| 2. Twee keer snel Enter → maar 1 `fetch`-aanroep | Unit (widget, jsdom, gemockte `fetch`) | Idem, meetbaar op netwerk-mock |
| 3. E-mail + telefoon + bedrijfsnaam in één bericht → alle drie in leadstate, volgende bot-vraag alleen naam | E2E tegen een test-sessie op de n8n-staging/dev-workflow (niet productie) | Systeemprompt-regel 25 werkt, `stuur_lead_naar_team`/geheugen slaat het correct op |
| 4. Alleen e-mail → wordt opgeslagen, rest nagevraagd | E2E, zelfde als 3 maar partieel | Idem, deelgeval |
| 5. Twee identieke opeenvolgende bot-antwoorden onmogelijk | Unit + assertie op berichtenstate | Combinatie van widget-cap-fix (2.4) en prompt-regel 26 |
| 6. "Je vroeg net nog om mijn gegevens" → verwijst naar eerdere gegevens, niet naar CTA | E2E | Prompt-regel 26 |
| 7. Sessie overleeft page-refresh (gesprek + gegevens) | E2E (browser) | Vereist eerst een besluit: nu overleeft alleen `sessionId`, niet de zichtbare geschiedenis — dit is een aparte, grotere wijziging (chatgeschiedenis lokaal cachen) die ik apart wil voorleggen, niet stilzwijgend meenemen |
| 8. Modelfout/timeout → eerlijke foutmelding, geen canned verkooptekst | Unit (widget, gemockte fetch-reject) | Bestaat al deels (regel 447-450) — test legt vast dat dit zo blijft, en dat dit nooit samenvalt met de cap-melding uit 2.4 |
| 9. Begroeting klopt bij 09:00 en 22:00 Europe/Amsterdam | E2E tegen n8n (met gemockte `$now` of twee losse testruns) | Prompt-regels §1a |

Test 7 heb ik bewust apart gezet: "sessie overleeft refresh met behoud van *zichtbare* conversatie"
is een grotere wijziging dan een bugfix (chatgeschiedenis moet dan ook lokaal opgeslagen en
gerenderd worden bij het laden van de widget) — dat wil ik niet ongevraagd meenemen onder het mom
van een test.

## Openstaande besluiten van jou

1. **§2 punt 4** — nieuwe waarde voor `maxMessagesPerSession` en het gedrag bij overschrijding.
2. **Test 7 / BUG 6** — wil je dat ik chatgeschiedenis-persistentie über page-refresh als aparte,
   grotere wijziging oppak, of laten we 'm nu buiten scope?
3. Akkoord op de systeemprompt-diff in §1 zoals die er nu staat, of wijzigingen?
