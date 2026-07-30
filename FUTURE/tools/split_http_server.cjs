const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "11_http_server.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "http_server");

const globalPartSpecs = [
  ["01_multipart_server.py", "def parse_multipart_form(headers, rfile, max_bytes: int = 80 * 1024 * 1024) -> tuple[dict[str, str], dict[str, dict]]:"],
  ["06_main.py", "def main() -> int:"],
];

const handlerPartSpecs = [
  ["02_handler_core.py", "    def end_headers(self):"],
  ["03_handler_get_routes.py", "    def do_GET(self):"],
  ["04_handler_post_routes.py", "    def do_POST(self):"],
  ["05_handler_logging.py", "    def log_message(self, fmt, *args):"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("HTTP_SERVER_PART_FILES = (")) {
  throw new Error("11_http_server.py already appears to use nested runtime parts.");
}

const markerIndex = (marker, label) => {
  const index = source.indexOf(marker);
  if (index < 0) {
    throw new Error(`Missing split marker for ${label}: ${marker}`);
  }
  if (index > 0 && source[index - 1] !== "\n") {
    throw new Error(`Split marker is not at the beginning of a line for ${label}.`);
  }
  return index;
};

const parseStart = markerIndex(globalPartSpecs[0][1], globalPartSpecs[0][0]);
const handlerClassStart = markerIndex("class FutureWhisperHandler(BaseHTTPRequestHandler):", "FutureWhisperHandler");
const handlerStarts = handlerPartSpecs.map(([fileName, marker]) => markerIndex(marker, fileName));
const mainStart = markerIndex(globalPartSpecs[1][1], globalPartSpecs[1][0]);

const orderedStarts = [parseStart, handlerClassStart, ...handlerStarts, mainStart];
for (let index = 1; index < orderedStarts.length; index += 1) {
  if (orderedStarts[index] <= orderedStarts[index - 1]) {
    throw new Error(`Split markers are out of order near index ${index}.`);
  }
}

const header = source.slice(0, parseStart).trimEnd();
const globalParts = [
  [globalPartSpecs[0][0], source.slice(parseStart, handlerClassStart).trimEnd() + "\n"],
  [globalPartSpecs[1][0], source.slice(mainStart).trimEnd() + "\n"],
];

const dedentMethodBlock = (text) => {
  const dedented = text
    .split(/\n/)
    .map((line) => (line.startsWith("    ") ? line.slice(4) : line))
    .join("\n");
  return dedented.replace("super().end_headers()", "BaseHTTPRequestHandler.end_headers(self)");
};

const handlerParts = handlerPartSpecs.map(([fileName], index) => {
  const start = handlerStarts[index];
  const end = index + 1 < handlerStarts.length ? handlerStarts[index + 1] : mainStart;
  const body = dedentMethodBlock(source.slice(start, end).trimEnd()) + "\n";
  return [fileName, body];
});

const loaderLines = [
  "",
  "",
  "HTTP_SERVER_PARTS_ROOT = SERVER_PARTS_ROOT / \"http_server\"",
  "HTTP_HANDLER_PART_FILES = (",
  ...handlerPartSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "HTTP_SERVER_GLOBAL_PART_FILES = (",
  ...globalPartSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "HTTP_SERVER_PART_FILES = (",
  `    \"${globalPartSpecs[0][0]}\",`,
  ...handlerPartSpecs.map(([fileName]) => `    \"${fileName}\",`),
  `    \"${globalPartSpecs[1][0]}\",`,
  ")",
  "",
  "",
  "def _load_http_server_part(part_name: str) -> None:",
  "    part_path = HTTP_SERVER_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "def _load_http_handler_part(part_name: str, class_namespace: dict) -> None:",
  "    part_path = HTTP_SERVER_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals(), class_namespace)",
  "",
  "",
  `for _http_server_global_part_name in (\"${globalPartSpecs[0][0]}\",):`,
  "    _load_http_server_part(_http_server_global_part_name)",
  "del _http_server_global_part_name",
  "",
  "",
  "class FutureWhisperHandler(BaseHTTPRequestHandler):",
  "    server_version = \"FutureWhisperServer/1.0\"",
  "",
  "    for _http_handler_part_name in HTTP_HANDLER_PART_FILES:",
  "        _load_http_handler_part(_http_handler_part_name, locals())",
  "    del _http_handler_part_name",
  "",
  "",
  `for _http_server_global_part_name in (\"${globalPartSpecs[1][0]}\",):`,
  "    _load_http_server_part(_http_server_global_part_name)",
  "del _http_server_global_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of [...globalParts, ...handlerParts]) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.",
    "# This is a nested transitional split; do not import directly yet.",
    "",
    body,
  ].join("\n");
  fs.writeFileSync(filePath, text, "utf8");
}

fs.writeFileSync(sourcePath, `${header}${loaderLines.join("\n")}`, "utf8");

const orderedOutput = [
  [globalPartSpecs[0][0], globalParts[0][1]],
  ...handlerParts,
  [globalPartSpecs[1][0], globalParts[1][1]],
];

console.log(JSON.stringify({
  loader: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: orderedOutput.map(([fileName, body]) => ({
    file: path.join("FUTURE", "server_parts", "http_server", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
