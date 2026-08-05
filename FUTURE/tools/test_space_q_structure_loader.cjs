const assert = require("assert");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const scheduler = fs.readFileSync(path.join(root, "web", "js_parts", "06_spacew_audio_scheduler.js"), "utf8");
const serverText = fs.readFileSync(path.join(root, "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");

assert.match(
  scheduler,
  /fetchServerText\(requestPath\)\.then/,
  "Structure manifests must use the shared multi-endpoint text loader",
);
assert.match(
  scheduler,
  /futureStructureTextCache\.delete\(assetUrl\)/,
  "Failed Structure promises must be evicted so a later Space_Q open can retry",
);
assert.match(
  serverText,
  /isStructureAssetRequest \? 8000 : 90000/,
  "Single-endpoint Structure reads must have an 8 second ceiling",
);
assert.match(
  serverText,
  /isStructureAssetRequest \? 5000 : 9000/,
  "Parallel Structure reads must have a 5 second ceiling",
);

console.log("Space_Q Structure loader regression checks passed.");
