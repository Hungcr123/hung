const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const source = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "19_pdf_speak_chrome.js"), "utf8");

for (const marker of [
  "pdfLegacyProgressIdentityForPath",
  "return clean(pdfState.lessonId)",
  "migratePdfLocalStateToLessonIdentity",
  "pdfLegacyDrawingLayerKey",
  "lesson_id: clean(pdfState && pdfState.lessonId",
  "appendPdfLessonIdentityQuery",
]) {
  if (!source.includes(marker)) throw new Error(`Missing PDF/Picture client lesson identity marker: ${marker}`);
}

console.log("space_pdf_client_lesson_identity=ok progress=id-first drawing=id-first legacy=one-time-migrate outbox=lesson-id");
