const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const acorn = require("acorn");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "web", "future.js");
const partsRoot = path.join(root, "FUTURE", "web", "js_parts");
const manifestPath = path.join(partsRoot, "manifest.json");
const targetBytes = 170 * 1024;

const sectionLabels = [
  "bootstrap_guard_ai_agent",
  "ai_agent_world_training",
  "world_motion_shared_state",
  "world_screen_paint",
  "screen_motion_layout",
  "spacew_audio_scheduler",
  "audio_speak_runtime",
  "speak_question_input",
  "question_select_picture_regions",
  "question_root_mobile_guidance",
  "question_guidance_picture_reveal",
  "question_translation_loader",
  "translation_vocab_sync",
  "vocab_sync_tasks",
  "task_notices_ai_focus",
  "notices_vocabulary_missions",
  "vocab_to_pdf_bootstrap",
  "pdf_mode_style_speak",
  "pdf_speak_chrome",
  "pdf_page_progress",
  "progress_bootstrap_events",
];

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function statementLabel(node, source) {
  if (!node) {
    return "";
  }
  if (node.type === "VariableDeclaration") {
    return node.declarations
      .slice(0, 3)
      .map((declaration) => declaration.id && declaration.id.name ? declaration.id.name : "")
      .filter(Boolean)
      .join(", ");
  }
  if (node.type === "FunctionDeclaration" && node.id && node.id.name) {
    return node.id.name;
  }
  return source.slice(node.start, Math.min(node.start + 80, node.end)).replace(/\s+/g, " ").trim();
}

function assertFreshPartsFolder() {
  if (!fs.existsSync(partsRoot)) {
    return;
  }
  const existing = fs.readdirSync(partsRoot).filter((name) => name.endsWith(".js") || name === "manifest.json");
  if (existing.length) {
    throw new Error(`Refusing to overwrite existing js_parts files. Remove or archive ${path.relative(root, partsRoot)} first.`);
  }
}

function parseFutureIife(source) {
  const ast = acorn.parse(source, {
    ecmaVersion: "latest",
    sourceType: "script",
    locations: true,
  });
  if (ast.body.length !== 1 || ast.body[0].type !== "ExpressionStatement") {
    throw new Error("future.js is expected to contain one top-level IIFE expression.");
  }
  const expression = ast.body[0].expression;
  if (!expression || expression.type !== "CallExpression" || !expression.callee || expression.callee.type !== "FunctionExpression") {
    throw new Error("future.js top-level expression is not the expected function IIFE.");
  }
  const fn = expression.callee;
  if (!fn.body || !Array.isArray(fn.body.body) || !fn.body.body.length) {
    throw new Error("future.js IIFE has no body statements to split.");
  }
  return {
    body: fn.body.body,
    innerStart: fn.body.start + 1,
    innerEnd: fn.body.end - 1,
  };
}

function chunkStatements(statements, innerStart, innerEnd) {
  const chunks = [];
  let chunkStart = innerStart;
  let firstStatementIndex = 0;
  for (let index = 0; index < statements.length; index += 1) {
    const statement = statements[index];
    const projectedBytes = statement.end - chunkStart;
    if (index > firstStatementIndex && projectedBytes > targetBytes) {
      const previous = statements[index - 1];
      chunks.push({
        firstStatementIndex,
        lastStatementIndex: index - 1,
        start: chunkStart,
        end: previous.end,
      });
      chunkStart = previous.end;
      firstStatementIndex = index;
    }
  }
  chunks.push({
    firstStatementIndex,
    lastStatementIndex: statements.length - 1,
    start: chunkStart,
    end: innerEnd,
  });
  return chunks;
}

assertFreshPartsFolder();

const source = fs.readFileSync(sourcePath, "utf8");
const parsed = parseFutureIife(source);
const chunks = chunkStatements(parsed.body, parsed.innerStart, parsed.innerEnd);
const prefix = source.slice(0, parsed.innerStart);
const suffix = source.slice(parsed.innerEnd);

fs.mkdirSync(partsRoot, { recursive: true });

const parts = chunks.map((chunk, index) => {
  const firstStatement = parsed.body[chunk.firstStatementIndex];
  const lastStatement = parsed.body[chunk.lastStatementIndex];
  const label = sectionLabels[index] || `section_${String(index + 1).padStart(2, "0")}`;
  const file = `${String(index + 1).padStart(2, "0")}_${label}.js`;
  const body = source.slice(chunk.start, chunk.end);
  fs.writeFileSync(path.join(partsRoot, file), body, "utf8");
  return {
    file,
    line_start: firstStatement.loc.start.line,
    line_end: lastStatement.loc.end.line,
    statement_start: chunk.firstStatementIndex + 1,
    statement_end: chunk.lastStatementIndex + 1,
    bytes: Buffer.byteLength(body, "utf8"),
    sha256: sha256(body),
    first: statementLabel(firstStatement, source),
    last: statementLabel(lastStatement, source),
  };
});

const rebuilt = `${prefix}${parts.map((part) => fs.readFileSync(path.join(partsRoot, part.file), "utf8")).join("")}${suffix}`;
if (rebuilt !== source) {
  throw new Error("Internal split check failed: rebuilt future.js does not match source.");
}

const manifest = {
  version: 1,
  source: "FUTURE/web/future.js",
  mode: "single_iife_body_parts",
  target_bytes: targetBytes,
  source_sha256: sha256(source),
  wrapper: {
    prefix,
    suffix,
  },
  parts,
};

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  ok: true,
  source: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map((part) => ({
    file: path.join("FUTURE", "web", "js_parts", part.file),
    lines: `${part.line_start}-${part.line_end}`,
    statements: `${part.statement_start}-${part.statement_end}`,
    bytes: part.bytes,
  })),
  sha256: manifest.source_sha256,
}, null, 2));
