import { createReadStream, statSync } from "node:fs";
import { createServer, request as requestHttp } from "node:http";
import { extname, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_ROOT = resolve(process.cwd(), "dist");
const DEFAULT_HOST = process.env["VERTEX_WEB_HOST"] ?? "0.0.0.0";
const DEFAULT_PORT = Number(process.env["VERTEX_WEB_PORT"] ?? "4173");
const DEFAULT_API_UPSTREAM =
  process.env["VERTEX_API_UPSTREAM"] ?? "http://api:8000";

const CONTENT_TYPES = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".ico", "image/x-icon"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".map", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
]);

const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; img-src 'self' data:; font-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function isApiPath(pathname) {
  return pathname === "/api" || pathname.startsWith("/api/");
}

export function safePath(root, pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }

  if (decoded.includes("\0")) return null;
  const candidate = resolve(root, `.${decoded}`);
  if (candidate !== root && !candidate.startsWith(`${root}${sep}`)) return null;
  return candidate;
}

function copyHeaders(headers) {
  const copied = {};
  for (const [name, value] of Object.entries(headers)) {
    if (value !== undefined && !HOP_BY_HOP_HEADERS.has(name.toLowerCase())) {
      copied[name] = value;
    }
  }
  return copied;
}

function proxyApi(request, response, apiUpstream) {
  const upstream = new URL(request.url ?? "/", apiUpstream);
  if (upstream.protocol !== "http:") {
    response.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ detail: "Unsupported API upstream protocol" }));
    return;
  }

  const proxyRequest = requestHttp(
    upstream,
    {
      headers: copyHeaders({ ...request.headers, host: upstream.host }),
      method: request.method,
    },
    (proxyResponse) => {
      response.writeHead(
        proxyResponse.statusCode ?? 502,
        copyHeaders(proxyResponse.headers),
      );
      proxyResponse.pipe(response);
    },
  );

  proxyRequest.on("error", () => {
    if (response.headersSent) {
      response.destroy();
      return;
    }
    response.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ detail: "Vertex API unavailable" }));
  });
  request.pipe(proxyRequest);
}

function serveFile(request, response, filePath) {
  const contentType = CONTENT_TYPES.get(extname(filePath)) ?? "application/octet-stream";
  response.writeHead(200, {
    ...SECURITY_HEADERS,
    "Content-Type": contentType,
  });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(filePath).pipe(response);
}

export function createVertexWebServer({
  root = DEFAULT_ROOT,
  apiUpstream = DEFAULT_API_UPSTREAM,
} = {}) {
  const resolvedRoot = resolve(root);

  return createServer((request, response) => {
    const url = new URL(request.url ?? "/", "http://vertex.local");
    if (isApiPath(url.pathname)) {
      proxyApi(request, response, apiUpstream);
      return;
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      response.writeHead(405, {
        Allow: "GET, HEAD",
        ...SECURITY_HEADERS,
      });
      response.end();
      return;
    }

    const requestedPath = url.pathname === "/" ? "/index.html" : url.pathname;
    const candidate = safePath(resolvedRoot, requestedPath);
    if (candidate === null) {
      response.writeHead(400, SECURITY_HEADERS);
      response.end("Bad request");
      return;
    }

    try {
      if (statSync(candidate).isFile()) {
        serveFile(request, response, candidate);
        return;
      }
    } catch {
      // The SPA fallback below handles client-side routes.
    }

    const fallback = safePath(resolvedRoot, "/index.html");
    try {
      if (fallback !== null && statSync(fallback).isFile()) {
        serveFile(request, response, fallback);
        return;
      }
    } catch {
      // Report a real 404 when the build output is unavailable.
    }

    response.writeHead(404, SECURITY_HEADERS);
    response.end("Not found");
  });
}

const isDirectRun = process.argv[1]
  ? import.meta.url === pathToFileURL(resolve(process.argv[1])).href
  : false;

if (isDirectRun) {
  const server = createVertexWebServer();
  server.listen(DEFAULT_PORT, DEFAULT_HOST, () => {
    process.stdout.write(
      `Vertex web listening on http://${DEFAULT_HOST}:${DEFAULT_PORT}\n`,
    );
  });
}
