const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"),
  "utf8",
);

const start = source.indexOf("const fetchServerText = async");
const end = source.indexOf("const fetchProgressJsonFromBase = async", start);
assert.ok(start >= 0 && end > start, "server text fetch source missing");
const block = source.slice(start, end);
assert.ok((block.match(/offlineCache: true/g) || []).length >= 2, "single and multi-base paths need offline fallback");
assert.match(block, /base: "local-cache"/);
assert.match(block, /cachedRow && typeof cachedRow\.text === "string" && cachedRow\.text\.length/);
assert.match(source, /headers\["If-None-Match"\] = clean\(cachedRow\.etag\)/);
assert.match(source, /response\.status === 304[\s\S]*delete headers\["If-None-Match"\]/, "304 without payload must retry full");

console.log("server_file_offline_cache=ok user_path_etag=true 304_without_payload=full_retry network_failure=local_cache");
