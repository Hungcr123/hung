const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const serverPath = path.join(root, "FUTURE", "server_app.py");
const partsRoot = path.join(root, "FUTURE", "server_parts");

const partSpecs = [
  ["01_core_runtime.py", "def clean(value) -> str:"],
  ["02_users_auth_settings.py", "def normalize_username(value: str) -> str:"],
  ["03_chat_paint_runtime.py", "def load_chat_state_locked() -> dict:"],
  ["04_ai_language_agents.py", "def chat_builder_tools():"],
  ["05_stream_screen_security.py", "def dashboard_is_online() -> bool:"],
  ["06_process_frontend_runtime.py", "def normalize_words(text: str) -> list[str]:"],
  ["07_server_data_pdf_qmdict.py", "def safe_server_data_path(relative_path: str = \"\", username: str = \"\", admin: bool = False) -> Path:"],
  ["08_progress_inventory_vocab.py", "def space_w_progress_path(username: str) -> Path:"],
  ["09_vocab_world_game.py", "def load_vocab_leaderboard_period_state() -> dict:"],
  ["10_vocab_build_status.py", "def lesson_english_text(payload: dict) -> str:"],
  ["11_http_server.py", "def parse_multipart_form(headers, rfile, max_bytes: int = 80 * 1024 * 1024) -> tuple[dict[str, str], dict[str, dict]]:"],
];

const source = fs.readFileSync(serverPath, "utf8");
if (source.includes("SERVER_PART_FILES = (")) {
  throw new Error("FUTURE/server_app.py already appears to use server_parts.");
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
  "SERVER_PARTS_ROOT = FUTURE_ROOT / \"server_parts\"",
  "SERVER_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_server_part(part_name: str) -> None:",
  "    part_path = SERVER_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _server_part_name in SERVER_PART_FILES:",
  "    _load_server_part(_server_part_name)",
  "del _server_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_app into the shared Future server runtime namespace.",
    "# Keep this transitional part free of imports unless it becomes a standalone module.",
    "",
    body,
  ].join("\n");
  fs.writeFileSync(filePath, text, "utf8");
}

fs.writeFileSync(serverPath, `${header}${loaderLines.join("\n")}`, "utf8");

console.log(JSON.stringify({
  server: path.relative(root, serverPath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map(([fileName, body]) => ({
    file: path.join("FUTURE", "server_parts", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
