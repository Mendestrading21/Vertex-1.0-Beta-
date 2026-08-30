// Service de fichiers statiques pour l'interface web, sans dépendance.
//
// Périmètre volontairement minimal : lire un fichier sous `dist/`, le rendre.
// Aucun proxy, aucune réécriture d'API, aucune donnée métier. L'écoute est
// bornée à la boucle locale : rien n'est publié sur le LAN.
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve, sep } from 'node:path';

const ROOT = resolve(process.cwd(), 'dist');
const HOST = '127.0.0.1';
const PORT = Number(process.env['VERTEX_WEB_PORT'] ?? 4173);

const TYPES = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
  ['.woff2', 'font/woff2'],
  ['.png', 'image/png'],
  ['.webmanifest', 'application/manifest+json'],
]);

/**
 * Résout une URL en chemin de fichier SOUS `dist/`, ou `null`.
 * Une tentative de traversée (`..`, chemin absolu, octet nul) renvoie `null` :
 * refus par défaut, jamais de servir en dehors de la racine.
 */
function safePath(urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null; // encodage invalide : refus
  }
  if (decoded.includes('\0')) return null;
  const candidate = resolve(join(ROOT, normalize(decoded)));
  if (candidate !== ROOT && !candidate.startsWith(ROOT + sep)) return null;
  return candidate;
}

const server = createServer(async (request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { allow: 'GET, HEAD' }).end();
    return;
  }
  const requested = new URL(request.url ?? '/', `http://${HOST}`).pathname;
  let file = safePath(requested);
  if (file === null) {
    response.writeHead(400).end();
    return;
  }
  try {
    const info = await stat(file);
    if (info.isDirectory()) file = join(file, 'index.html');
  } catch {
    // Application à page unique : une route inconnue rend le document racine,
    // c'est le routeur client qui décide (y compris de son état « inconnue »).
    file = join(ROOT, 'index.html');
  }
  const headers = {
    'content-type': TYPES.get(extname(file)) ?? 'application/octet-stream',
    // L'application est locale : aucun cadrage tiers, aucun sniffing de type.
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'referrer-policy': 'no-referrer',
  };
  response.writeHead(200, headers);
  if (request.method === 'HEAD') {
    response.end();
    return;
  }
  createReadStream(file).pipe(response);
});

server.listen(PORT, HOST, () => {
  process.stdout.write(`web statique sur http://${HOST}:${PORT}\n`);
});
