# Protocolchecker

Lokale webapp waarmee personeel protocollen kan opzoeken én — desgewenst — een
AI-vraag kan stellen die alleen op basis van de geladen protocolteksten
antwoordt. Draait volledig lokaal (alleen op `127.0.0.1`, geen data verlaat de
machine tenzij de AI-functie wordt gebruikt, zie hieronder).

## Starten

```
cd protocolchecker
python3 server.py
```

Open daarna http://127.0.0.1:8420 in de browser.

## Protocollen vervangen

Elk protocol is een los bestand in `protocols/*.md`:

```markdown
---
title: Titel van het protocol
category: Categorie (bv. Behandelingen, Spoed)
status: voorbeeld   # of: te-verifieren
---

## Kopje
Tekst met **vet**, *cursief*, lijsten en > blockquotes.
```

`status: voorbeeld` toont een rode "VOORBEELD"-badge (nog niet gecontroleerde
placeholder-inhoud); `status: te-verifieren` toont een oranje badge (inhoud
gebaseerd op eerdere afspraken, maar nog te bevestigen door bevoegd
personeel). Zodra een protocol echt is goedgekeurd, verwijder je het
`status`-veld (of zet een andere waarde) zodat de badge verdwijnt.

Vervangen = bestand overschrijven (zelfde bestandsnaam) of vervangen door een nieuwe
versie. Geen herstart van de server nodig — gewoon de pagina verversen in de browser.
Nieuw bestand toevoegen laat automatisch een nieuw protocol verschijnen in de lijst;
bestand verwijderen laat het verdwijnen.

## Huidige inhoud is voorbeelddata

Alle protocollen in deze map zijn placeholders (zie de waarschuwing bovenaan elk
bestand en de badge in de lijst). Niet gebruiken in de praktijk voordat ze zijn
vervangen door goedgekeurde, gecontroleerde protocollen.

## AI-assistent

De knop "Vraag het AI" opent een paneel waar personeel een vraag kan stellen.
Twee harde regels, ongeacht de vraag:

1. **Escalatie gaat altijd voor.** Vóórdat er ook maar een AI-aanroep gebeurt,
   scant de server de vraag op de spoedsignalen uit `00-spoedsignalen.md`
   (koorts, hevige pijn, visusklachten na filler, etc.). Bij een match krijgt
   de gebruiker direct de escalatie-instructie te zien — dit is een vaste,
   niet-AI-afhankelijke check in `server.py` (`ESCALATION_KEYWORDS`), zodat
   escalatie nooit van een taalmodel-beoordeling afhangt.
2. **De AI antwoordt uitsluitend op basis van de geladen protocolteksten.**
   Staat het antwoord niet in de protocollen, dan zegt de AI dat expliciet in
   plaats van iets te verzinnen. Elk antwoord toont welke protocol(len) zijn
   gebruikt, aanklikbaar om het volledige protocol te openen.

### Configureren

Vereist het officiële `anthropic` Python-pakket en een API key:

```
pip3 install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 server.py
```

Zonder `ANTHROPIC_API_KEY` blijft de rest van de app gewoon werken — alleen
`/api/ask` geeft dan een nette foutmelding in het paneel in plaats van een
antwoord.

### Nog te doen vóór echt gebruik

Dit is een technische basis, geen juridisch akkoord. Voordat dit met echte
protocollen en personeel gebruikt wordt, moet nog getoetst worden of dit
overeenkomt met de EU AI Act / AVG-afspraken die eerder zijn vastgelegd
(zie de projectcontext over gecontroleerde brondata en het juridisch kader).
