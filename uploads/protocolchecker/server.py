#!/usr/bin/env python3
"""Lokale protocolchecker-server. Alleen Python 3 standaardbibliotheek nodig.

Start met: python3 server.py
Open dan:  http://127.0.0.1:8420
"""

import html
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent
PROTOCOLS_DIR = BASE_DIR / "protocols"
PUBLIC_DIR = BASE_DIR / "public"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", 8420))

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}

AI_MODEL = "claude-opus-4-8"

# Deterministische, niet-AI-afhankelijke check: als een van deze signalen in de
# vraag voorkomt, escaleren we altijd — ongeacht wat een taalmodel zou zeggen.
# Gebaseerd op protocols/00-spoedsignalen.md.
ESCALATION_KEYWORDS = [
    "ademhalingsprobleem", "ademnood", "benauwd",
    "bewusteloos", "flauwgevallen", "flauwvallen",
    "hevig bloedverlies", "onstelpbaar bloedverlies", "bloedt hevig",
    "allergische reactie", "zwelling van de keel", "keel zwelt", "gezicht zwelt op",
    "hevige pijn", "heftige pijn", "ondraaglijke pijn",
    "wit wordt", "wit weefsel", "blauw-paars", "blauwig-paars", "huidverkleuring",
    "wazig zien", "minder zien", "visusklachten", "slechter zien",
    "koorts", "abnormale zwelling",
    "112",
]

ESCALATION_MESSAGE = (
    "Dit klinkt als een spoedsignaal. Volg direct het protocol "
    "'Spoedsignalen — wanneer moet je escaleren?' en escaleer naar een "
    "verantwoordelijke behandelaar of 112. Dit systeem geeft hier bewust geen "
    "verdere AI-inhoudelijke reactie op."
)


def contains_escalation_signal(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ESCALATION_KEYWORDS)


def parse_protocol_file(path: Path):
    text = path.read_text(encoding="utf-8")
    title = None
    category = None
    status = None
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front, body = parts[1], parts[2].lstrip("\n")
            for line in front.strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key, val = key.strip().lower(), val.strip()
                    if key == "title":
                        title = val
                    elif key == "category":
                        category = val
                    elif key == "status":
                        status = val

    return title or path.stem, category or "Overig", status or "voorbeeld", body


def load_protocols():
    """Leest alle .md-bestanden live in — vervangen van een bestand werkt dus
    zonder de server te herstarten, gewoon de pagina verversen."""
    protocols = {}
    if not PROTOCOLS_DIR.exists():
        return protocols
    for path in sorted(PROTOCOLS_DIR.glob("*.md")):
        title, category, status, body = parse_protocol_file(path)
        protocols[path.stem] = {
            "id": path.stem,
            "title": title,
            "category": category,
            "status": status,
            "body": body,
        }
    return protocols


def inline_format(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_html(md_text: str) -> str:
    out = []
    in_ul = in_ol = False
    para = []
    quote_buf = []

    def flush_para():
        if para:
            out.append(f"<p>{inline_format(' '.join(para))}</p>")
            para.clear()

    def flush_quote():
        if quote_buf:
            out.append(f"<blockquote>{inline_format(' '.join(quote_buf))}</blockquote>")
            quote_buf.clear()

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw_line in md_text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            flush_para()
            flush_quote()
            close_lists()
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            flush_para()
            flush_quote()
            close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_format(heading.group(2))}</h{level}>")
            continue

        ul_item = re.match(r"^[-*]\s+(.*)$", stripped)
        if ul_item:
            flush_para()
            flush_quote()
            if not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_format(ul_item.group(1))}</li>")
            continue

        ol_item = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ol_item:
            flush_para()
            flush_quote()
            if not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_format(ol_item.group(1))}</li>")
            continue

        quote = re.match(r"^>\s?(.*)$", stripped)
        if quote:
            flush_para()
            close_lists()
            quote_buf.append(quote.group(1))
            continue

        flush_quote()
        close_lists()
        para.append(stripped)

    flush_para()
    flush_quote()
    close_lists()
    return "\n".join(out)


def build_protocol_context(protocols: dict) -> str:
    sections = []
    for p in sorted(protocols.values(), key=lambda p: (p["category"], p["title"])):
        sections.append(
            f"### Protocol-ID: {p['id']}\nTitel: {p['title']}\nCategorie: {p['category']}\n\n{p['body']}"
        )
    return "\n\n---\n\n".join(sections)


def ask_ai(question: str, protocols: dict) -> dict:
    import anthropic  # lokale import: alleen nodig als /api/ask echt gebruikt wordt

    protocol_ids = sorted(protocols.keys())
    context = build_protocol_context(protocols)

    system_prompt = (
        "Je bent een protocolchecker voor kliniekpersoneel. Je krijgt hieronder de "
        "volledige tekst van alle beschikbare protocollen. Beantwoord de vraag van "
        "het personeelslid UITSLUITEND op basis van deze protocolteksten.\n\n"
        "Regels:\n"
        "- Verzin nooit medische of klinische informatie die niet letterlijk in de "
        "protocollen staat.\n"
        "- Staat het antwoord niet in de protocollen? Zet covered=false en leg dat "
        "uit in het antwoord (bv. 'dit staat niet in de protocollen, vraag het aan "
        "een verantwoordelijke collega').\n"
        "- Lijkt de vraag op een spoedsituatie (zoals beschreven in het protocol "
        "Spoedsignalen)? Zet escalate=true en verwijs direct naar dat protocol in "
        "plaats van een normale protocolvraag te beantwoorden.\n"
        "- Vermeld in 'sources' de protocol-ID's die je daadwerkelijk hebt gebruikt.\n\n"
        f"PROTOCOLLEN:\n\n{context}"
    )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "covered": {"type": "boolean"},
                        "escalate": {"type": "boolean"},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string", "enum": protocol_ids},
                        },
                    },
                    "required": ["answer", "covered", "escalate", "sources"],
                    "additionalProperties": False,
                },
            }
        },
    )

    text_block = next(b for b in response.content if b.type == "text")
    return json.loads(text_block.text)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, filename, content_type):
        file_path = PUBLIC_DIR / filename
        if not file_path.exists():
            self.send_error(404)
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            self._send_file(filename, content_type)
            return

        if path == "/api/protocols":
            protocols = load_protocols()
            listing = sorted(
                (
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "category": p["category"],
                        "status": p["status"],
                    }
                    for p in protocols.values()
                ),
                key=lambda p: (p["category"], p["title"]),
            )
            self._send_json(listing)
            return

        if path.startswith("/api/protocols/"):
            protocol_id = path[len("/api/protocols/"):]
            protocol = load_protocols().get(protocol_id)
            if not protocol:
                self._send_json({"error": "not found"}, status=404)
                return
            self._send_json(
                {
                    "id": protocol["id"],
                    "title": protocol["title"],
                    "category": protocol["category"],
                    "status": protocol["status"],
                    "html": markdown_to_html(protocol["body"]),
                }
            )
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/ask":
            self._handle_ask()
            return

        self.send_error(404)

    def _handle_ask(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "ongeldige aanvraag"}, status=400)
            return

        question = (body.get("question") or "").strip()
        if not question:
            self._send_json({"error": "geen vraag meegegeven"}, status=400)
            return

        if contains_escalation_signal(question):
            self._send_json(
                {
                    "answer": ESCALATION_MESSAGE,
                    "covered": True,
                    "escalate": True,
                    "sources": ["00-spoedsignalen"],
                }
            )
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self._send_json(
                {
                    "error": (
                        "AI is niet geconfigureerd. Zet ANTHROPIC_API_KEY in de "
                        "omgeving en herstart de server."
                    )
                },
                status=503,
            )
            return

        try:
            answer = ask_ai(question, load_protocols())
        except Exception as exc:  # noqa: BLE001 — vertaald naar een nette foutmelding
            self._send_json(
                {"error": f"AI-aanvraag mislukt: {exc}"},
                status=502,
            )
            return

        self._send_json(answer)

    def log_message(self, format, *args):
        super().log_message(format, *args)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Protocolchecker draait op http://{HOST}:{PORT}  (Ctrl+C om te stoppen)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
