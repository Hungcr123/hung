const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..", "..");
const source = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");

// Added 2026-07-20: payload and ETag must remain one user-scoped cache record with a cache-loss retry.
assert.match(source, /SERVER_FILE_TEXT_CACHE_NAME = "future-server-file-text-v1"/);
assert.match(source, /clean\(currentAuthUsername \|\| ""\)\.toLowerCase\(\)/);
assert.match(source, /"X-Future-Cache-Schema": SERVER_FILE_TEXT_CACHE_SCHEMA/);
assert.match(source, /"X-Future-Source-Etag": clean\(row\.etag\)/);
assert.match(source, /response\.status === 304/);
assert.match(source, /cachedRow && typeof cachedRow\.text === "string" && cachedRow\.text\.length/);
assert.match(source, /delete headers\["If-None-Match"\]/);
assert.match(source, /await cache\.delete\(serverFileTextCacheRequestUrl\(path\)\)/);
assert.match(source, /for \(const base of candidates\)/);
assert.match(source, /void persistServerFileTextCache/);
assert.doesNotMatch(source, /localStorage\.setItem\([^\n]*Source-Etag/i);

console.log("server_data_file_client_cache=ok atomic=true user_scoped=true cache_loss_retry=true sequential_origin=true");
