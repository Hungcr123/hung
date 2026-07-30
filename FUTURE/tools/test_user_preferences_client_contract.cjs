const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const client = fs.readFileSync(path.join(root, "web", "js_parts", "01_bootstrap_guard_ai_agent.js"), "utf8");
const route = fs.readFileSync(path.join(root, "server_parts", "http_server", "post_route_parts", "03_pdf_ai_tasks_auth.pyfrag"), "utf8");

for (const marker of [
  'if (path === "/auth/preferences")',
  'headers["X-Future-Response-Mode"] = "preferences-compact-v1"',
]) {
  if (!client.includes(marker)) throw new Error(`Missing preference client marker: ${marker}`);
}
for (const marker of [
  'X-Future-Response-Mode',
  'preferences-compact-v1',
  '"server_revision": max(0, int(preferences.get("_serverRevision", 0) or 0))',
]) {
  if (!route.includes(marker)) throw new Error(`Missing preference route marker: ${marker}`);
}

console.log("user_preferences_client_contract=ok compact=opt-in legacy=full-response");
