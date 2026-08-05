"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const bootstrap = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const chrome = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "19_pdf_speak_chrome.js"), "utf8");

assert.match(bootstrap, /var pdfRenderQualityLevel = 1;/);
assert.match(bootstrap, /pdfjs-local-q1-20260803/);
assert.match(chrome, /const readPdfRenderQualityPreference = \(\) => \{\s*return 1;/);
assert.match(chrome, /24 \* 1024 \* 1024/);
assert.match(chrome, /8192 \/ pagePointWidth/);
assert.match(chrome, /const shouldUseLocalPdfRender = stateSnapshot\.mode !== "picture";/);

console.log("pdf render quality contract: PASS");
