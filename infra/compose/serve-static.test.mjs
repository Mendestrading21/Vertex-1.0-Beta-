import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { createVertexWebServer, safePath } from "./serve-static.mjs";

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve(`http://127.0.0.1:${address.port}`);
    });
  });
}

function close(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

test("safePath rejects traversal outside the build root", () => {
  assert.equal(safePath("/tmp/vertex-dist", "/../secret"), null);
  assert.equal(safePath("/tmp/vertex-dist", "/%2e%2e/secret"), null);
});

test("serves the SPA and proxies every API method", async () => {
  const root = await mkdtemp(join(tmpdir(), "vertex-web-"));
  await writeFile(join(root, "index.html"), "<main>Vertex</main>");

  const api = createServer((request, response) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => {
      response.writeHead(request.method === "POST" ? 204 : 200, {
        "Content-Type": "application/json",
        "Set-Cookie": "vertex_session=test; HttpOnly; Path=/",
      });
      if (request.method !== "POST") {
        response.end(JSON.stringify({ method: request.method, path: request.url }));
      } else {
        response.end(body);
      }
    });
  });

  let web;
  try {
    const apiUrl = await listen(api);
    web = createVertexWebServer({ root, apiUpstream: apiUrl });
    const webUrl = await listen(web);

    const page = await fetch(`${webUrl}/today`);
    assert.equal(page.status, 200);
    assert.equal(await page.text(), "<main>Vertex</main>");
    assert.match(page.headers.get("content-security-policy"), /default-src 'self'/);

    const health = await fetch(`${webUrl}/api/v1/health`);
    assert.equal(health.status, 200);
    assert.deepEqual(await health.json(), {
      method: "GET",
      path: "/api/v1/health",
    });
    assert.match(health.headers.get("set-cookie"), /vertex_session=test/);

    const logout = await fetch(`${webUrl}/api/v1/auth/logout`, {
      body: JSON.stringify({ reason: "test" }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    assert.equal(logout.status, 204);
  } finally {
    if (web?.listening) await close(web);
    if (api.listening) await close(api);
    await rm(root, { force: true, recursive: true });
  }
});
