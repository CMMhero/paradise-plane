#!/usr/bin/env node
/**
 * Server statis kecil untuk mengukur build produksi web: fallback SPA ke index.html dan gzip (level 6, sama
 * dengan `serve`) untuk aset teks, supaya ukuran transfer realistis.
 *
 *   node serve-static.mjs <dir build/client> [port=4000]
 *
 * Dibuat karena `serve -s` di repo ini mogok: override path-to-regexp membuat serve-handler melempar
 * "pathToRegExp.compile is not a function" pada setiap rewrite SPA.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import zlib from "node:zlib";

const root = path.resolve(process.argv[2] ?? "build/client");
const port = Number(process.argv[3] ?? 4000);
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".txt": "text/plain; charset=utf-8",
  ".webmanifest": "application/manifest+json",
};
const COMPRESSIBLE = new Set([".html", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".webmanifest"]);
const gzCache = new Map();

http
  .createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://x");
    let file = path.join(root, decodeURIComponent(url.pathname));
    if (!file.startsWith(root)) return res.writeHead(403).end();
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      const idx = path.join(file, "index.html");
      // Aset yang tidak ada harus 404, bukan index.html (kalau tidak, chunk hilang tampak "berhasil").
      file = fs.existsSync(idx) ? idx : path.extname(url.pathname) ? null : path.join(root, "index.html");
    }
    if (!file) return res.writeHead(404).end("not found");
    const ext = path.extname(file);
    const headers = { "Content-Type": TYPES[ext] ?? "application/octet-stream", "Cache-Control": "no-cache" };
    let body = fs.readFileSync(file);
    if (COMPRESSIBLE.has(ext) && /\bgzip\b/.test(req.headers["accept-encoding"] ?? "")) {
      if (!gzCache.has(file)) gzCache.set(file, zlib.gzipSync(body, { level: 6 }));
      body = gzCache.get(file);
      headers["Content-Encoding"] = "gzip";
      headers.Vary = "Accept-Encoding";
    }
    headers["Content-Length"] = body.length;
    res.writeHead(200, headers).end(req.method === "HEAD" ? undefined : body);
  })
  .listen(port, () => console.log(`serving ${root} on :${port}`));
