const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const source = fs.readFileSync(
  path.join(root, "FUTURE", "web", "js_parts", "20_pdf_page_progress.js"),
  "utf8",
);

if (!source.includes("const resolvedPath = clean(result.payload && result.payload.path || requestPath);")) {
  throw new Error("Lesson Vault does not trust the server-resolved fallback path.");
}
if (!source.includes('rememberLessonVaultFolder(resolvedPath, taskOwner, "folder_restore_server");')) {
  throw new Error("Lesson Vault still persists the missing requested folder.");
}
if (!source.includes('updateFutureAppRoute("lesson_vault", {') || !source.includes("replace: true,")) {
  throw new Error("Lesson Vault does not replace a stale route after folder fallback.");
}

console.log("lesson_vault_missing_folder_fallback=ok route=replace persisted=resolved_path");
