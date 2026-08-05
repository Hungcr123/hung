const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..", "..");
const bootstrap = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const pdfRuntime = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "19_pdf_speak_chrome.js"), "utf8");
const pdfRoute = fs.readFileSync(path.join(root, "FUTURE", "server_parts", "http_server", "get_route_parts", "04_pdf_picture_render.pyfrag"), "utf8");

assert.match(bootstrap, /const PDF_FILE_CHUNK_BYTES = 2 \* 1024 \* 1024;/);
assert.match(bootstrap, /const PDF_FILE_FULL_CACHE_MAX_BYTES = PDF_FILE_CHUNK_BYTES;/);
assert.match(pdfRuntime, /for \(let attempt = 0; attempt < 2; attempt \+= 1\)/);
assert.match(pdfRuntime, /loaded: Math\.min\(totalBytes, loaded \+ chunkLoaded\)/);
assert.match(pdfRuntime, /query\.set\("client_source", "pdf_source_chunk"\)/);
assert.match(pdfRuntime, /xhr\.timeout = requestTimeoutMs/);
assert.match(pdfRuntime, /recordPdfSourceNetworkTrace\("progress"/);
assert.match(pdfRuntime, /downloadPdfSourceFileByChunks[\s\S]{0,5000}progressTransport: "xhr"/);
assert.match(pdfRuntime, /if \(sourceLessonId && currentLessonId\) return currentLessonId === sourceLessonId;/);
assert.doesNotMatch(pdfRuntime, /normalizeServerPathValue\(pdfState\.path \|\| ""\) === sourcePath\s*&&\s*\(!sourceLessonId/);
assert.match(pdfRuntime, /withPdfCacheTimeout\(caches\.open\(PDF_FILE_PERSISTENT_CACHE\)/);
assert.match(pdfRuntime, /void writePdfSourceFileChunkCache\(key, index, blob/);
assert.match(pdfRuntime, /Range: `bytes=\$\{start\}-\$\{end\}`/);
assert.match(pdfRoute, /Content-Range/);
assert.match(pdfRoute, /Accept-Ranges/);
assert.match(pdfRoute, /file_in\.read\(min\(64 \* 1024, remaining\)\)/);
assert.match(pdfRoute, /self\.wfile\.flush\(\)/);

const measuredPdfBytes = 36_877_351;
const chunkBytes = 2 * 1024 * 1024;
assert.equal(Math.ceil(measuredPdfBytes / chunkBytes), 18);
assert.equal(Math.ceil(measuredPdfBytes / (512 * 1024)), 71);

console.log(JSON.stringify({
  ok: true,
  measuredPdfBytes,
  chunksNow: 18,
  chunksAt512KiB: 71,
  retryAttempts: 2,
  serverFlushBytes: 64 * 1024,
}));
