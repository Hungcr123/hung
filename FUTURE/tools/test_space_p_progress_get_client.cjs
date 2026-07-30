const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..", "..");
const progressSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const transportSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");

// Added 2026-07-21: P/L/S Continue revalidates atomically while folder chips trust preload.
assert.match(progressSource, /currentParagraphProgressCache\.serverPayload = payload/);
assert.match(progressSource, /currentParagraphProgressCache\.serverEtag = clean\(result && result\.etag \|\| ""\)/);
assert.match(progressSource, /fetchProgressJsonFast\(`\/space-p\/progress\?\$\{query\.toString\(\)\}`, cachedRow\)/);
assert.match(progressSource, /currentParagraphProgressCache\.serverPayload = null/);
assert.match(progressSource, /currentParagraphProgressCache\.serverEtag = ""/);
assert.match(transportSource, /\["Space_W", "Space_Q", "Space_P", "Space_S", "Space_L"\]\.includes\(space\)/);

console.log("space_p_progress_get_client=ok conditional_refresh=true atomic_etag=true post_invalidation=true vault_preload=true");
