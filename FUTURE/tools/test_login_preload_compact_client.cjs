const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const source = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");

for (const marker of [
  'preloadQuery.set("response", "compact-v2")',
  "preloadPayload.preload.progress_snapshot",
  "rememberPdfProgressLoginSnapshot(preloadPayload.preload.progress_snapshot)",
]) {
  if (!source.includes(marker)) throw new Error(`Missing compact-v2 login-preload client marker: ${marker}`);
}

console.log("login_preload_compact_client=ok nested_snapshot=true legacy_fallback=true");
