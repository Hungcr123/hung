const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "ai_language_agents", "03_ai_agent_requests.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "ai_language_agents", "ai_agent_requests");

const partSpecs = [
  ["01_sanitize_context.py", "def sanitize_ai_agent_vietnamese_reply(text: str, limit: int = 9000) -> str:"],
  ["02_translation_english_reply.py", "def request_gemini_vietnamese_translation(text: str, structured: bool = False) -> str:"],
  ["03_qm_city_npc_reply.py", "def request_gemini_qm_city_npc_reply("],
  ["04_vietnamese_reply.py", "def request_gemini_vietnamese_reply("],
  ["05_pdf_explanation.py", "def request_gemini_pdf_vietnamese_explanation("],
  ["06_notice_followup.py", "def build_ai_agent_notice(username: str, message: str, context: dict | None = None, mode: str = \"spoken\") -> dict:"],
  ["07_shared_agent_state.py", "AI_AGENT_HISTORY_LOCK = threading.RLock()"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("AI_AGENT_REQUESTS_PART_FILES = (")) {
  throw new Error("03_ai_agent_requests.py already appears to use nested request parts.");
}

const starts = partSpecs.map(([fileName, marker]) => {
  const index = source.indexOf(marker);
  if (index < 0) {
    throw new Error(`Missing split marker for ${fileName}: ${marker}`);
  }
  if (index > 0 && source[index - 1] !== "\n") {
    throw new Error(`Split marker is not at the beginning of a line for ${fileName}.`);
  }
  return index;
});

for (let index = 1; index < starts.length; index += 1) {
  if (starts[index] <= starts[index - 1]) {
    throw new Error(`Split markers are out of order at ${partSpecs[index][0]}.`);
  }
}

const header = source.slice(0, starts[0]).trimEnd();
const parts = partSpecs.map(([fileName], index) => {
  const start = starts[index];
  const end = index + 1 < starts.length ? starts[index + 1] : source.length;
  const body = source.slice(start, end).trimEnd() + "\n";
  return [fileName, body];
});

const loaderLines = [
  "",
  "",
  "AI_AGENT_REQUESTS_PARTS_ROOT = AI_LANGUAGE_AGENTS_PARTS_ROOT / \"ai_agent_requests\"",
  "AI_AGENT_REQUESTS_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_ai_agent_requests_part(part_name: str) -> None:",
  "    part_path = AI_AGENT_REQUESTS_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _ai_agent_requests_part_name in AI_AGENT_REQUESTS_PART_FILES:",
  "    _load_ai_agent_requests_part(_ai_agent_requests_part_name)",
  "del _ai_agent_requests_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.",
    "# This is a deeper transitional split; do not import directly yet.",
    "",
    body,
  ].join("\n");
  fs.writeFileSync(filePath, text, "utf8");
}

fs.writeFileSync(sourcePath, `${header}${loaderLines.join("\n")}`, "utf8");

console.log(JSON.stringify({
  loader: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map(([fileName, body]) => ({
    file: path.join("FUTURE", "server_parts", "ai_language_agents", "ai_agent_requests", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
