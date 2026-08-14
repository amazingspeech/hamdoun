// Minimale statische server voor de e2e-tests, puur ingebouwde node:http en
// node:fs - geen dependency. Serveert de repo-root zodat de testpagina de
// echte, ongewijzigde tessar-concierge-widget.js kan laden op een gewoon
// http-origin (nodig zodat CORS-mocking van de webhook-call realistisch is;
// een file://-origin gedraagt zich hier anders dan productie).
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = req.url.split('?')[0];
      const filePath = path.join(ROOT, decodeURIComponent(urlPath));
      if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
      fs.readFile(filePath, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        const ext = path.extname(filePath);
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ server, baseURL: `http://127.0.0.1:${port}` });
    });
  });
}

module.exports = { startServer };
