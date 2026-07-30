const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "07_server_data_pdf_qmdict.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "server_data_pdf_qmdict");

const partSpecs = [
  ["01_server_data_paths_links.py", "def safe_server_data_path(relative_path: str = \"\", username: str = \"\", admin: bool = False) -> Path:"],
  ["02_lesson_study_progress.py", "def normalize_study_block(payload: dict) -> dict:"],
  ["03_lesson_tasks_logs.py", "def lesson_task_owner_for_path(relative_path: str = \"\", username: str = \"\", admin: bool = False) -> str:"],
  ["04_server_data_manifest_listing.py", "def server_data_manifest_skip_tops() -> set[str]:"],
  ["05_picture_pdf_render.py", "def safe_pdf_server_data_path(relative_path: str = \"\", username: str = \"\", admin: bool = False) -> Path:"],
  ["06_ocr_qmdict_core.py", "def resolve_tesseract_cmd() -> str:"],
  ["07_qmlearn_audio_spacev_repair.py", "def qmdict_space_v_meaning_audio_map(meaning: object = \"\", *, online_fallback: bool = True) -> dict:"],
  ["08_pdf_vocab_scan.py", "def pdf_vocab_phrase_summary(item: object = None) -> dict:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("SERVER_DATA_PDF_QMDICT_PART_FILES = (")) {
  throw new Error("07_server_data_pdf_qmdict.py already appears to use nested runtime parts.");
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
  "SERVER_DATA_PDF_QMDICT_PARTS_ROOT = SERVER_PARTS_ROOT / \"server_data_pdf_qmdict\"",
  "SERVER_DATA_PDF_QMDICT_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_server_data_pdf_qmdict_part(part_name: str) -> None:",
  "    part_path = SERVER_DATA_PDF_QMDICT_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _server_data_pdf_qmdict_part_name in SERVER_DATA_PDF_QMDICT_PART_FILES:",
  "    _load_server_data_pdf_qmdict_part(_server_data_pdf_qmdict_part_name)",
  "del _server_data_pdf_qmdict_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.",
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
    file: path.join("FUTURE", "server_parts", "server_data_pdf_qmdict", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
