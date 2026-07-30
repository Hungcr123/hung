const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "01_core_runtime.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "core_runtime");

const partSpecs = [
  ["01_clean_cpu_work_queue.py", "def clean(value) -> str:"],
  ["02_sort_anti_robot.py", "def natural_sort_key(value: object = \"\") -> list[tuple]:"],
  ["03_path_asset_guards.py", "def clean_path_value(value) -> str:"],
  ["04_time_debug_logging.py", "def local_timestamp(epoch: float | None = None) -> str:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("CORE_RUNTIME_PART_FILES = (")) {
  throw new Error("01_core_runtime.py already appears to use nested runtime parts.");
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
  "CORE_RUNTIME_PARTS_ROOT = SERVER_PARTS_ROOT / \"core_runtime\"",
  "CORE_RUNTIME_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_core_runtime_part(part_name: str) -> None:",
  "    part_path = CORE_RUNTIME_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _core_runtime_part_name in CORE_RUNTIME_PART_FILES:",
  "    _load_core_runtime_part(_core_runtime_part_name)",
  "del _core_runtime_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.01_core_runtime into the shared Future server runtime namespace.",
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
    file: path.join("FUTURE", "server_parts", "core_runtime", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
