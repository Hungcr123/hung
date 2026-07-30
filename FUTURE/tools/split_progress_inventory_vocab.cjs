const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "08_progress_inventory_vocab.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "progress_inventory_vocab");

const partSpecs = [
  ["01_space_w_progress.py", "def space_w_progress_path(username: str) -> Path:"],
  ["02_space_q_progress.py", "def space_q_progress_path(username: str) -> Path:"],
  ["03_space_v_progress.py", "def space_v_progress_path(username: str) -> Path:"],
  ["04_space_p_pdf_progress.py", "def space_p_progress_path(username: str) -> Path:"],
  ["05_inventory_keyboard_assets.py", "def inventory_path(username: str) -> Path:"],
  ["06_vocab_registry_core.py", "def safe_name_segment(value: str, fallback: str = \"Mission\", limit: int = 54) -> str:"],
  ["07_main_vocab_sync.py", "def main_vocab_progress_path(username: str) -> Path:"],
  ["08_vocab_recording_summary.py", "def record_user_vocabulary_items("],
  ["09_vocab_period_stats.py", "def local_period_starts_epoch() -> dict:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("PROGRESS_INVENTORY_VOCAB_PART_FILES = (")) {
  throw new Error("08_progress_inventory_vocab.py already appears to use nested runtime parts.");
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
  "PROGRESS_INVENTORY_VOCAB_PARTS_ROOT = SERVER_PARTS_ROOT / \"progress_inventory_vocab\"",
  "PROGRESS_INVENTORY_VOCAB_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_progress_inventory_vocab_part(part_name: str) -> None:",
  "    part_path = PROGRESS_INVENTORY_VOCAB_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _progress_inventory_vocab_part_name in PROGRESS_INVENTORY_VOCAB_PART_FILES:",
  "    _load_progress_inventory_vocab_part(_progress_inventory_vocab_part_name)",
  "del _progress_inventory_vocab_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.",
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
    file: path.join("FUTURE", "server_parts", "progress_inventory_vocab", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
