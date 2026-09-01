# Tessar MCP-server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw en deploy een publieke, read-only MCP-server op `https://tessar.nl/mcp` (met `/mcp/health`) die 4 tools aanbiedt over de live site-content.

**Architecture:** Eén nieuwe Python 3.11-service (`mcp-server`), gebouwd met de officiële `mcp`-SDK, draaiend als eigen Docker-container naast de bestaande `contact-api`/`auth-api`-services in de gedeelde compose-stack op Hetzner. Leest live HTML read-only vanaf `/var/www/tessar`. Caddy routeert `/mcp` en `/mcp/*` naar de nieuwe container.

**Tech Stack:** Python 3.11, `mcp` SDK (PyPI, versie `2.1.1`), stdlib `html.parser`/`re`/`glob` voor content-extractie (geen andere dependencies), Starlette (komt mee met `mcp`) voor de custom health-route.

**Spec:** `docs/superpowers/specs/2026-09-01-tessar-mcp-server-design.md`

## Global Constraints

- Alleen 4 tools: `list_pages`, `get_page`, `search`, `get_pricing`. Er zijn geen bestaande tools om intact te houden.
- Contentbron is altijd de live, read-only gemounte site (`/srv/tessar-site` in de container, gemapt op `/var/www/tessar` op de host) — geen aparte databron.
- `get_pricing()` faalt expliciet (gooit een fout) als de verwachte `data-mcp-*`-attributen ontbreken; nooit stilzwijgend lege/foute data teruggeven.
- Geen schrijf-operaties. Deze server raakt nooit `contact-api`/`auth-api` of hun data.
- Broncode van de nieuwe service leeft op de server (`/home/job/tessar/mcp-server-src/`), niet in de `hamdoun`-git-repo — zelfde conventie als `contact-api-src`/`auth-api-src`.
- Server: `157.90.244.24`, gebruiker `job`, key `~/.ssh/tessar_deploy_ed25519`. Compose-project: `/home/job/tessar/`.
- Lokale ontwikkel-/testmap: `~/development/tessar-mcp-server-src/` (buiten de `hamdoun`-repo, zodat er niets per ongeluk wordt meegecommit).

---

### Task 1: `data-mcp-*`-attributen toevoegen aan prijzen.html

**Files:**
- Modify: `~/development/hamdoun/prijzen.html:171,185,199,220,235` (de 5 pricing-card-`<div data-reveal ...>`-openingstags)

**Interfaces:**
- Produces: 5 `<div data-reveal data-mcp-tier="..." data-mcp-price="..." data-mcp-duration="..." style="...">`-tags die Task 4 (`pricing.py`) leest.

- [ ] **Step 1: Voeg de attributen toe aan alle 5 kaarten**

In `~/development/hamdoun/prijzen.html`, vervang de 5 openingstags exact als volgt (attributen toegevoegd, verder ongewijzigd — geen visuele impact):

```html
<div data-reveal data-mcp-tier="Kennismaking" data-mcp-price="Gratis" data-mcp-duration="30 minuten" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
```

```html
<div data-reveal data-mcp-tier="AI-readiness scan" data-mcp-price="vanaf €295" data-mcp-duration="2-3 dagen" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
```

```html
<div data-reveal data-mcp-tier="Quick win" data-mcp-price="€1.250" data-mcp-duration="1 week" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
```

```html
<div data-reveal data-mcp-tier="Proof of Concept" data-mcp-price="Op aanvraag" data-mcp-duration="2-3 weken" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
```

```html
<div data-reveal data-mcp-tier="Volledige implementatie" data-mcp-price="Op aanvraag" data-mcp-duration="2-4 weken" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:clamp(28px,4vw,36px);display:flex;flex-direction:column;transition:all 220ms ease, opacity 600ms ease, transform 600ms ease;">
```

(Alle 5 `<div data-reveal style="background:var(--surface);...">`-tags in dit bestand zijn tekstueel identiek vóór deze wijziging — gebruik de context van de voorafgaande `<h3>` in elke tekst-editor om de juiste te raken, of vervang op volgorde van voorkomen.)

- [ ] **Step 2: Verifieer met een korte Python-check dat alle 5 attributen aanwezig zijn**

Run:
```bash
cd ~/development/hamdoun
python3 -c "
content = open('prijzen.html', encoding='utf-8').read()
import re
tiers = re.findall(r'data-mcp-tier=\"([^\"]*)\"', content)
prices = re.findall(r'data-mcp-price=\"([^\"]*)\"', content)
durations = re.findall(r'data-mcp-duration=\"([^\"]*)\"', content)
assert tiers == ['Kennismaking', 'AI-readiness scan', 'Quick win', 'Proof of Concept', 'Volledige implementatie'], tiers
assert len(prices) == 5 and len(durations) == 5
print('OK:', list(zip(tiers, prices, durations)))
"
```
Expected: `OK: [('Kennismaking', 'Gratis', '30 minuten'), ...]` — geen AssertionError.

- [ ] **Step 3: Verifieer dat de HTML-structuur nog geldig is (tag-balans)**

Run:
```bash
cd ~/development/hamdoun
python3 -c "
from html.parser import HTMLParser
class C(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack=[]; self.errors=[]
        self.void={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def handle_starttag(self, tag, attrs):
        if tag not in self.void: self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in self.void: return
        if self.stack and self.stack[-1] == tag: self.stack.pop()
        else: self.errors.append(tag)
c = C()
c.feed(open('prijzen.html', encoding='utf-8').read())
assert not c.errors and not c.stack, (c.errors, c.stack)
print('HTML OK')
"
```
Expected: `HTML OK`.

- [ ] **Step 4: Commit**

```bash
cd ~/development/hamdoun
git add prijzen.html
git commit -m "prijzen.html: data-mcp-* attributen op de 5 pricing-cards

Geen visuele wijziging. Bron voor de nieuwe MCP-server se get_pricing()-tool
(zie docs/superpowers/plans/2026-09-01-tessar-mcp-server.md)."
```

---

### Task 2: `content.py` — pagina's opsommen en lezen

**Files:**
- Create: `~/development/tessar-mcp-server-src/content.py`
- Test: `~/development/tessar-mcp-server-src/test_content.py`

**Interfaces:**
- Produces: `list_pages() -> list[dict]` (`{"path", "title", "description"}` per pagina), `get_page(path: str) -> dict` (`{"path", "title", "description", "content"}`), `PageNotFoundError` — gebruikt door Task 3 (`search.py`) en Task 5 (`server.py`).

- [ ] **Step 1: Maak de lokale werkmap en schrijf de eerste falende test**

```bash
mkdir -p ~/development/tessar-mcp-server-src
cd ~/development/tessar-mcp-server-src
```

Schrijf `test_content.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
os.environ["SITE_ROOT"] = os.path.expanduser("~/development/hamdoun")

import content  # noqa: E402


class ListPagesTests(unittest.TestCase):
    def test_includes_known_page(self):
        paths = [p["path"] for p in content.list_pages()]
        self.assertIn("/services.html", paths)

    def test_homepage_path_is_root(self):
        paths = [p["path"] for p in content.list_pages()]
        self.assertIn("/", paths)

    def test_excludes_index_src(self):
        paths = [p["path"] for p in content.list_pages()]
        self.assertNotIn("/index.src.html", paths)

    def test_excludes_google_verification_file(self):
        paths = [p["path"] for p in content.list_pages()]
        self.assertFalse(any("google" in p for p in paths))

    def test_page_has_title_and_description(self):
        pages = {p["path"]: p for p in content.list_pages()}
        self.assertTrue(pages["/services.html"]["title"])
        self.assertTrue(pages["/services.html"]["description"])


class GetPageTests(unittest.TestCase):
    def test_returns_title_and_description(self):
        page = content.get_page("/services.html")
        self.assertIn("Diensten", page["title"])
        self.assertTrue(page["description"])

    def test_content_has_no_html_tags(self):
        page = content.get_page("/services.html")
        self.assertNotIn("<", page["content"])

    def test_content_is_nonempty(self):
        page = content.get_page("/services.html")
        self.assertGreater(len(page["content"]), 100)

    def test_root_path_maps_to_index(self):
        page = content.get_page("/")
        self.assertIn("Tessar", page["title"])

    def test_unknown_path_raises(self):
        with self.assertRaises(content.PageNotFoundError):
            content.get_page("/does-not-exist.html")

    def test_rejects_path_traversal(self):
        with self.assertRaises(content.PageNotFoundError):
            content.get_page("/../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run de tests, verifieer dat ze falen op een import-fout**

Run: `python3 test_content.py -v`
Expected: `ModuleNotFoundError: No module named 'content'` (content.py bestaat nog niet).

- [ ] **Step 3: Schrijf `content.py`**

```python
"""HTML-content-extractie voor de Tessar MCP-server. Alleen Python-stdlib.

Leest pagina's uit SITE_ROOT (de live site, read-only gemount) en geeft
titel/beschrijving/leestekst terug voor de tools in server.py.
"""

import glob
import os
import re
from html.parser import HTMLParser

SITE_ROOT = os.environ.get("SITE_ROOT", "/srv/tessar-site")

# Bestanden die geen echte, met de tools op te vragen contentpagina zijn.
_EXCLUDED_FILENAMES = {"index.src.html"}
_EXCLUDED_PREFIXES = ("google",)

# Alleen kale lowercase-bestandsnamen toestaan -- voorkomt padtraversal
# (bv. "../../etc/passwd") en sluit per definitie index.src.html uit
# (bevat een punt binnen de naam, matcht deze regex niet).
_FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*\.html$")

_TITLE_RE = re.compile(r"<title>([^<]*)</title>")
_DESCRIPTION_RE = re.compile(r'<meta name="description" content="([^"]*)"')


class PageNotFoundError(Exception):
    """De opgevraagde pagina bestaat niet of is niet toegestaan."""


class _TextExtractor(HTMLParser):
    """Strip tags en <script>/<style>-inhoud, houd de leesbare tekst over."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self):
        return " ".join(self._chunks)


def _is_content_page(filename):
    if not _FILENAME_RE.match(filename):
        return False
    if filename in _EXCLUDED_FILENAMES:
        return False
    if filename.startswith(_EXCLUDED_PREFIXES):
        return False
    return True


def _filename_from_path(path):
    name = (path or "").strip()
    if name in ("", "/"):
        return "index.html"
    return name.lstrip("/")


def _url_path(filename):
    return "/" if filename == "index.html" else "/" + filename


def _read_html(filename):
    full = os.path.join(SITE_ROOT, filename)
    if not os.path.isfile(full):
        raise PageNotFoundError(filename)
    with open(full, encoding="utf-8") as f:
        return f.read()


def _extract_title(html):
    m = _TITLE_RE.search(html)
    return m.group(1) if m else ""


def _extract_description(html):
    m = _DESCRIPTION_RE.search(html)
    return m.group(1) if m else ""


def list_pages():
    """Geeft {path, title, description} terug voor elke echte contentpagina."""
    pages = []
    for full in sorted(glob.glob(os.path.join(SITE_ROOT, "*.html"))):
        filename = os.path.basename(full)
        if not _is_content_page(filename):
            continue
        html = _read_html(filename)
        pages.append({
            "path": _url_path(filename),
            "title": _extract_title(html),
            "description": _extract_description(html),
        })
    return pages


def get_page(path):
    """Geeft {path, title, description, content} terug voor 1 pagina.

    Gooit PageNotFoundError bij een onbekend of niet-toegestaan pad
    (inclusief padtraversal-pogingen).
    """
    filename = _filename_from_path(path)
    if not _is_content_page(filename):
        raise PageNotFoundError(path)
    html = _read_html(filename)
    extractor = _TextExtractor()
    extractor.feed(html)
    return {
        "path": _url_path(filename),
        "title": _extract_title(html),
        "description": _extract_description(html),
        "content": extractor.get_text(),
    }
```

- [ ] **Step 4: Run de tests, verifieer dat ze slagen**

Run: `python3 test_content.py -v`
Expected: alle 10 tests `ok`.

- [ ] **Step 5: Commit (lokaal, geen remote — deze map wordt pas in Task 6 naar de server gekopieerd)**

```bash
cd ~/development/tessar-mcp-server-src
git init -q 2>/dev/null || true
git add content.py test_content.py
git commit -q -m "content.py: pagina's opsommen en lezen" 2>/dev/null || true
```

---

### Task 3: `search.py` — full-text zoeken

**Files:**
- Create: `~/development/tessar-mcp-server-src/search.py`
- Test: `~/development/tessar-mcp-server-src/test_search.py`

**Interfaces:**
- Consumes: `content.list_pages() -> list[dict]`, `content.get_page(path: str) -> dict` (Task 2).
- Produces: `search_pages(query: str) -> list[dict]` (`{"path", "title", "snippet"}` per treffer) — gebruikt door Task 5 (`server.py`).

- [ ] **Step 1: Schrijf de falende test**

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
os.environ["SITE_ROOT"] = os.path.expanduser("~/development/hamdoun")

import search  # noqa: E402


class SearchPagesTests(unittest.TestCase):
    def test_finds_known_term(self):
        results = search.search_pages("AI-readiness")
        paths = [r["path"] for r in results]
        self.assertIn("/services.html", paths)

    def test_case_insensitive(self):
        results_lower = search.search_pages("avg")
        results_upper = search.search_pages("AVG")
        self.assertEqual(
            {r["path"] for r in results_lower},
            {r["path"] for r in results_upper},
        )

    def test_no_match_returns_empty_list(self):
        results = search.search_pages("ditbestaatnergensopdesite")
        self.assertEqual(results, [])

    def test_result_has_snippet(self):
        results = search.search_pages("AI-readiness")
        self.assertTrue(all(r["snippet"] for r in results))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, verifieer falen**

Run: `python3 test_search.py -v`
Expected: `ModuleNotFoundError: No module named 'search'`.

- [ ] **Step 3: Schrijf `search.py`**

```python
"""Eenvoudige full-text zoekopdracht over alle pagina's. Alleen stdlib."""

import content

_SNIPPET_RADIUS = 80


def _snippet(text, query):
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:160]
    start = max(0, idx - _SNIPPET_RADIUS)
    end = min(len(text), idx + len(query) + _SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def search_pages(query):
    """Geeft {path, title, snippet} terug voor elke pagina die `query`
    bevat in titel, beschrijving of leestekst (case-insensitive)."""
    query_lower = query.lower()
    results = []
    for summary in content.list_pages():
        page = content.get_page(summary["path"])
        haystack = " ".join([page["title"], page["description"], page["content"]])
        if query_lower in haystack.lower():
            results.append({
                "path": page["path"],
                "title": page["title"],
                "snippet": _snippet(haystack, query),
            })
    return results
```

- [ ] **Step 4: Run, verifieer slagen**

Run: `python3 test_search.py -v`
Expected: alle 4 tests `ok`.

- [ ] **Step 5: Commit**

```bash
cd ~/development/tessar-mcp-server-src
git add search.py test_search.py
git commit -q -m "search.py: full-text zoeken over alle pagina's"
```

---

### Task 4: `pricing.py` — gestructureerde prijzen

**Files:**
- Create: `~/development/tessar-mcp-server-src/pricing.py`
- Test: `~/development/tessar-mcp-server-src/test_pricing.py`

**Interfaces:**
- Consumes: `content.SITE_ROOT` (Task 2), de `data-mcp-*`-attributen uit Task 1.
- Produces: `get_pricing() -> list[dict]` (`{"tier", "price", "duration"}` per pakket), `PricingDataError` — gebruikt door Task 5.

- [ ] **Step 1: Schrijf de falende test**

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
os.environ["SITE_ROOT"] = os.path.expanduser("~/development/hamdoun")

import pricing  # noqa: E402


class GetPricingTests(unittest.TestCase):
    def test_returns_five_tiers(self):
        tiers = pricing.get_pricing()
        self.assertEqual(len(tiers), 5)

    def test_includes_known_tier(self):
        tiers = pricing.get_pricing()
        names = [t["tier"] for t in tiers]
        self.assertIn("Kennismaking", names)

    def test_tier_has_price_and_duration(self):
        tiers = pricing.get_pricing()
        kennismaking = next(t for t in tiers if t["tier"] == "Kennismaking")
        self.assertEqual(kennismaking["price"], "Gratis")
        self.assertEqual(kennismaking["duration"], "30 minuten")

    def test_raises_if_no_tiers_found(self):
        with self.assertRaises(pricing.PricingDataError):
            pricing._parse_tiers("<html><body>geen data-mcp-attributen hier</body></html>")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, verifieer falen**

Run: `python3 test_pricing.py -v`
Expected: `ModuleNotFoundError: No module named 'pricing'`.

- [ ] **Step 3: Schrijf `pricing.py`**

```python
"""Gestructureerde prijzen voor de Tessar MCP-server. Alleen stdlib.

Leest data-mcp-tier/data-mcp-price/data-mcp-duration-attributen uit
prijzen.html (toegevoegd in Task 1 van het implementatieplan). Faalt
expliciet als die attributen ontbreken, in plaats van lege/foute data
terug te geven.
"""

import os
import re

import content

_TIER_RE = re.compile(
    r'data-mcp-tier="([^"]*)"\s+data-mcp-price="([^"]*)"\s+data-mcp-duration="([^"]*)"'
)


class PricingDataError(Exception):
    """De verwachte data-mcp-*-attributen zijn niet gevonden in prijzen.html."""


def _parse_tiers(html):
    matches = _TIER_RE.findall(html)
    if not matches:
        raise PricingDataError(
            "Geen data-mcp-tier/data-mcp-price/data-mcp-duration-attributen "
            "gevonden in prijzen.html."
        )
    return [
        {"tier": tier, "price": price, "duration": duration}
        for tier, price, duration in matches
    ]


def get_pricing():
    """Geeft de 5 prijspakketten terug als {tier, price, duration}."""
    full = os.path.join(content.SITE_ROOT, "prijzen.html")
    if not os.path.isfile(full):
        raise PricingDataError("prijzen.html niet gevonden op SITE_ROOT.")
    with open(full, encoding="utf-8") as f:
        html = f.read()
    return _parse_tiers(html)
```

- [ ] **Step 4: Run, verifieer slagen**

Run: `python3 test_pricing.py -v`
Expected: alle 4 tests `ok`.

- [ ] **Step 5: Commit**

```bash
cd ~/development/tessar-mcp-server-src
git add pricing.py test_pricing.py
git commit -q -m "pricing.py: gestructureerde prijzen uit data-mcp-*-attributen"
```

---

### Task 5: `server.py` — de MCP-server zelf, `Dockerfile`, `requirements.txt`

**Files:**
- Create: `~/development/tessar-mcp-server-src/server.py`
- Create: `~/development/tessar-mcp-server-src/requirements.txt`
- Create: `~/development/tessar-mcp-server-src/Dockerfile`
- Test (handmatig, geen unittest): `~/development/tessar-mcp-server-src/smoke_test.py`

**Interfaces:**
- Consumes: `content.list_pages`, `content.get_page`, `content.PageNotFoundError` (Task 2); `search.search_pages` (Task 3); `pricing.get_pricing`, `pricing.PricingDataError` (Task 4).
- Produces: een draaiende MCP-server op poort 8423 met tools `list_pages`, `get_page`, `search`, `get_pricing`, en een `GET /mcp/health`-route.

- [ ] **Step 1: Installeer de dependency lokaal**

```bash
cd ~/development/tessar-mcp-server-src
pip install --user mcp==2.1.1
echo "mcp==2.1.1" > requirements.txt
```

- [ ] **Step 2: Schrijf `server.py`**

```python
#!/usr/bin/env python3
"""Publieke, read-only MCP-server voor tessar.nl.

Leest live site-content uit een read-only gemounte kopie van
/var/www/tessar (SITE_ROOT). Biedt 4 tools: list_pages, get_page, search,
get_pricing. Zie docs/superpowers/specs/2026-09-01-tessar-mcp-server-design.md
in de hamdoun-repo voor het ontwerp.
"""

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

import content
import pricing
from search import search_pages

mcp = MCPServer("Tessar")


@mcp.tool()
def list_pages() -> list[dict]:
    """Geeft alle pagina's van tessar.nl terug als {path, title, description}."""
    return content.list_pages()


@mcp.tool()
def get_page(path: str) -> dict:
    """Geeft de volledige leestekst van 1 pagina terug, bijv. "/services.html"
    of "/" voor de homepage."""
    return content.get_page(path)


@mcp.tool()
def search(query: str) -> list[dict]:
    """Doorzoekt alle pagina's van tessar.nl op een zoekterm, geeft
    {path, title, snippet} terug per treffer."""
    return search_pages(query)


@mcp.tool()
def get_pricing() -> list[dict]:
    """Geeft de 5 prijspakketten van tessar.nl/prijzen.html terug als
    {tier, price, duration}."""
    return pricing.get_pricing()


@mcp.custom_route("/mcp/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8423,
        streamable_http_path="/mcp",
    )
```

- [ ] **Step 3: Start de server lokaal tegen de hamdoun-checkout**

```bash
cd ~/development/tessar-mcp-server-src
SITE_ROOT=~/development/hamdoun PORT=8423 python3 server.py &
sleep 1
```

- [ ] **Step 4: Schrijf en run een smoke-test die alle 4 tools echt aanroept**

Schrijf `smoke_test.py`:

```python
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client("http://127.0.0.1:8423/mcp") as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            assert names == ["get_page", "get_pricing", "list_pages", "search"], names

            pages = await session.call_tool("list_pages", {})
            assert not pages.is_error, pages.content

            page = await session.call_tool("get_page", {"path": "/services.html"})
            assert not page.is_error, page.content

            hits = await session.call_tool("search", {"query": "AVG"})
            assert not hits.is_error, hits.content

            pricing = await session.call_tool("get_pricing", {})
            assert not pricing.is_error, pricing.content

            print("OK — alle 4 tools gaven een correct antwoord.")


asyncio.run(main())
```

Run:
```bash
cd ~/development/tessar-mcp-server-src
python3 smoke_test.py
```
Expected: `OK — alle 4 tools gaven een correct antwoord.`

- [ ] **Step 5: Test de health-route**

Run: `curl -s http://127.0.0.1:8423/mcp/health`
Expected: `{"status":"ok"}`

- [ ] **Step 6: Stop de lokale server**

```bash
kill %1
```

- [ ] **Step 7: Schrijf `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY content.py pricing.py search.py server.py ./

ENV SITE_ROOT=/srv/tessar-site
ENV PORT=8423
EXPOSE 8423

CMD ["python3", "server.py"]
```

- [ ] **Step 8: Commit**

```bash
cd ~/development/tessar-mcp-server-src
git add server.py requirements.txt Dockerfile smoke_test.py
git commit -q -m "server.py: MCP-server met 4 tools + /mcp/health, Dockerfile"
```

---

### Task 6: Deployen naar de Hetzner-server

**Files:**
- Create (op de server): `/home/job/tessar/mcp-server-src/{content.py,pricing.py,search.py,server.py,requirements.txt,Dockerfile}`
- Modify (op de server): `/home/job/tessar/docker-compose.yml`, `/home/job/tessar/Caddyfile`

**Interfaces:**
- Consumes: de complete, lokaal geteste `~/development/tessar-mcp-server-src/`-map (Task 2-5) en de gedeployde `prijzen.html` met `data-mcp-*`-attributen (Task 1 — moet al live staan via de bestaande `deploy-tessar.yml`-CI, of handmatig gersynct, vóór deze taak).

- [ ] **Step 1: Verifieer dat prijzen.html met de nieuwe attributen al live staat**

Run: `curl -s https://tessar.nl/prijzen.html | grep -c 'data-mcp-tier'`
Expected: `5`. Zo niet: wacht tot de bestaande CI (`deploy-tessar.yml`, triggert op push naar `main`) de `hamdoun`-branch met Task 1's commit heeft uitgerold, of rsync handmatig.

- [ ] **Step 2: Kopieer de geteste servercode naar de server**

```bash
scp -i ~/.ssh/tessar_deploy_ed25519 -r ~/development/tessar-mcp-server-src \
  job@157.90.244.24:/home/job/tessar/mcp-server-src
```

- [ ] **Step 3: Maak een backup van docker-compose.yml en Caddyfile, zoals de bestaande `.bak-*`-conventie op de server**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "
cd /home/job/tessar &&
cp docker-compose.yml docker-compose.yml.bak-\$(date +%Y%m%d-%H%M%S) &&
cp Caddyfile Caddyfile.bak-\$(date +%Y%m%d-%H%M%S)
"
```

- [ ] **Step 4: Voeg de `mcp-server`-service toe aan docker-compose.yml**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "
cd /home/job/tessar &&
python3 - <<'PYEOF'
content = open('docker-compose.yml', encoding='utf-8').read()
marker = '  caddy:\n'
assert content.count(marker) == 1
addition = '''  mcp-server:
    build: ./mcp-server-src
    restart: always
    volumes:
      - /var/www/tessar:/srv/tessar-site:ro

'''
content = content.replace(marker, addition + marker)
open('docker-compose.yml', 'w', encoding='utf-8').write(content)
print('docker-compose.yml bijgewerkt')
PYEOF
"
```

- [ ] **Step 5: Verifieer de compose-syntax**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "cd /home/job/tessar && docker compose config -q && echo COMPOSE_OK"
```
Expected: `COMPOSE_OK` (geen YAML/syntax-fouten).

- [ ] **Step 6: Voeg de `/mcp`-route toe aan de Caddyfile**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "
cd /home/job/tessar &&
python3 - <<'PYEOF'
content = open('Caddyfile', encoding='utf-8').read()
marker = '\t@auth path /api/auth/*\n\treverse_proxy @auth auth-api:8422\n'
assert content.count(marker) == 1
addition = marker + '\n\t@mcp path /mcp /mcp/*\n\treverse_proxy @mcp mcp-server:8423\n'
content = content.replace(marker, addition)
open('Caddyfile', 'w', encoding='utf-8').write(content)
print('Caddyfile bijgewerkt')
PYEOF
"
```

- [ ] **Step 7: Verifieer de Caddyfile-syntax**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "
docker run --rm -v /home/job/tessar/Caddyfile:/etc/caddy/Caddyfile:ro caddy:latest caddy validate --config /etc/caddy/Caddyfile
"
```
Expected: geen foutmelding (`Valid configuration` of stille exit 0).

- [ ] **Step 8: Bouw en start de nieuwe service, herlaad Caddy (geen full restart van de gedeelde stack)**

```bash
ssh -i ~/.ssh/tessar_deploy_ed25519 job@157.90.244.24 "
cd /home/job/tessar &&
docker compose up -d --build mcp-server &&
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
"
```

- [ ] **Step 9: Verifieer live via curl**

```bash
curl -s https://tessar.nl/mcp/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 10: Verifieer een echte tool-aanroep tegen de live server**

```bash
cd ~/development/tessar-mcp-server-src
python3 -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client('https://tessar.nl/mcp') as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('get_pricing', {})
            assert not result.is_error, result.content
            print('OK, live get_pricing werkt:', result.content)

asyncio.run(main())
"
```
Expected: `OK, live get_pricing werkt: ...` met de 5 pakketten.

- [ ] **Step 11: Controleer dat de bestaande services niets gebroken zijn**

```bash
curl -s -o /dev/null -w "tessar.nl: %{http_code}\n" https://tessar.nl/
curl -s -o /dev/null -w "contact-api: %{http_code}\n" -X POST https://tessar.nl/api/contact
curl -s -o /dev/null -w "n8n: %{http_code}\n" https://n8n.tessar.nl/
```
Expected: `tessar.nl: 200`, `contact-api: <4xx, geen 5xx of connectie-fout>` (POST zonder body faalt op validatie, niet op bereikbaarheid), `n8n: 200` of een n8n-eigen redirect — in elk geval geen verbindingsfout die op een kapotte Caddy/compose-herstart zou wijzen.

---

**Self-review (uitgevoerd tijdens het schrijven van dit plan):**
- Spec-dekking: alle 4 tools, de `data-mcp-*`-aanpak voor `get_pricing`, de `/var/www/tessar`-read-only-mount, de Caddy-routing en de `job`-gebruiker-conventie komen terug in Task 1-6.
- Geen placeholders: elke stap bevat de daadwerkelijke code/commando's, geen "implementeer analoog aan..." of "voeg foutafhandeling toe".
- Type-/naamconsistentie gecontroleerd: `content.list_pages`/`content.get_page`/`content.PageNotFoundError` (Task 2) worden in Task 3, 4 en 5 exact zo aangeroepen; `search.search_pages` (Task 3, geïmporteerd als `from search import search_pages` in Task 5 om naamsbotsing met de `search`-tool-functie te vermijden); `pricing.get_pricing`/`pricing.PricingDataError` (Task 4) exact zo gebruikt in Task 5.
