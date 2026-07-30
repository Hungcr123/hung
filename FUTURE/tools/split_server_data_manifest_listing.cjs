const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "server_data_pdf_qmdict", "04_server_data_manifest_listing.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "server_data_pdf_qmdict", "server_data_manifest_listing");

const partSpecs = [
  ["01_manifest_build_scan.py", "def server_data_manifest_skip_tops() -> set[str]:"],
  ["02_manifest_cache_refresh.py", "def load_server_data_manifest_from_disk() -> dict:"],
  ["03_manifest_query_cache.py", "def server_data_manifest_root_entry(folder_name: str, owner: str = \"\") -> dict:"],
  ["04_lesson_completion.py", "def record_lesson_completion(relative_path: str, username: str, info: dict | None = None) -> dict:"],
  ["05_list_server_data.py", "def list_server_data(relative_path: str = \"\", username: str = \"\", admin: bool = False, task_owner_hint: str = \"\", fresh: bool = False) -> dict:"],
  ["06_link_copy_mission_cleanup.py", "def server_data_unique_child_path(folder: Path, desired_name: str) -> Path:"],
  ["07_operations_read.py", "def server_data_path_top(relative_path: str = \"\") -> str:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("SERVER_DATA_MANIFEST_LISTING_PART_FILES = (")) {
  throw new Error("04_server_data_manifest_listing.py already appears to use deeper manifest/listing parts.");
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
  "SERVER_DATA_MANIFEST_LISTING_PARTS_ROOT = SERVER_DATA_PDF_QMDICT_PARTS_ROOT / \"server_data_manifest_listing\"",
  "SERVER_DATA_MANIFEST_LISTING_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_server_data_manifest_listing_part(part_name: str) -> None:",
  "    part_path = SERVER_DATA_MANIFEST_LISTING_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _server_data_manifest_listing_part_name in SERVER_DATA_MANIFEST_LISTING_PART_FILES:",
  "    _load_server_data_manifest_listing_part(_server_data_manifest_listing_part_name)",
  "del _server_data_manifest_listing_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.",
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
    file: path.join("FUTURE", "server_parts", "server_data_pdf_qmdict", "server_data_manifest_listing", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
