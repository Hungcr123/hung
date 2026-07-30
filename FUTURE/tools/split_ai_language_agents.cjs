const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "04_ai_language_agents.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "ai_language_agents");

const partSpecs = [
  ["01_chat_translation_voice.py", "def chat_builder_tools():"],
  ["02_gemini_keys_models.py", "def load_gemini_api_keys(force_refresh: bool = False) -> list[str]:"],
  ["03_ai_agent_requests.py", "def sanitize_ai_agent_vietnamese_reply(text: str, limit: int = 9000) -> str:"],
  ["04_ai_agent_history.py", "def ai_agent_history_path(username: str) -> Path:"],
  ["05_word_agent_core_history.py", "def word_agent_key(value: object = \"\") -> str:"],
  ["06_phonetic_ipa.py", "def phonetic_ipa_key(value: object = \"\") -> str:"],
  ["07_word_agent_gemini.py", "def save_word_agent_history(source: object = None) -> dict:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("AI_LANGUAGE_AGENTS_PART_FILES = (")) {
  throw new Error("04_ai_language_agents.py already appears to use nested runtime parts.");
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
  "AI_LANGUAGE_AGENTS_PARTS_ROOT = SERVER_PARTS_ROOT / \"ai_language_agents\"",
  "AI_LANGUAGE_AGENTS_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_ai_language_agents_part(part_name: str) -> None:",
  "    part_path = AI_LANGUAGE_AGENTS_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _ai_language_agents_part_name in AI_LANGUAGE_AGENTS_PART_FILES:",
  "    _load_ai_language_agents_part(_ai_language_agents_part_name)",
  "del _ai_language_agents_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.",
    "# This is a nested transitional split; do not import directly yet.",
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
    file: path.join("FUTURE", "server_parts", "ai_language_agents", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
