const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "http_server", "03_handler_get_routes.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "http_server", "get_route_parts");
const manifestPath = path.join(partsRoot, "manifest.json");

const partSpecs = [
  ["01_entry_frontend_status.pyfrag", ""],
  ["02_chat_stream_screen_paint.pyfrag", "    if path == \"/chat/attachment\":"],
  ["03_auth_dashboard_server_data.pyfrag", "    if path == \"/auth/me\":"],
  ["04_pdf_picture_render.pyfrag", "    if path == \"/pdf/info\":"],
  ["05_progress_vocab_leaderboard.pyfrag", "    if path == \"/space-pdf/progress\":"],
  ["06_world_game_assets.pyfrag", "    if path == \"/world/state\":"],
];

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function assertFreshPartsFolder() {
  if (!fs.existsSync(partsRoot)) {
    return;
  }
  const existing = fs.readdirSync(partsRoot).filter((name) => name.endsWith(".pyfrag") || name === "manifest.json");
  if (existing.length) {
    throw new Error(`Refusing to overwrite existing get_route_parts files. Remove or archive ${path.relative(root, partsRoot)} first.`);
  }
}

function lineStartsFor(source) {
  const starts = [0];
  for (let index = 0; index < source.length; index += 1) {
    if (source[index] === "\n") {
      starts.push(index + 1);
    }
  }
  return starts;
}

function lineNumberAt(lineStarts, index) {
  let low = 0;
  let high = lineStarts.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (lineStarts[mid] <= index) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return high + 1;
}

function firstRoute(text) {
  const match = text.match(/^\s+if path(?:\.startswith)? (?:==|in|!=|\.startswith)[^\n]+/m);
  return match ? match[0].trim() : "def do_GET(self)";
}

function lastRoute(text) {
  const matches = [...text.matchAll(/^\s+if path(?:\.startswith)? (?:==|in|!=|\.startswith)[^\n]+/gm)];
  return matches.length ? matches[matches.length - 1][0].trim() : "";
}

assertFreshPartsFolder();

const source = fs.readFileSync(sourcePath, "utf8");
const lineStarts = lineStartsFor(source);
const starts = partSpecs.map(([fileName, marker]) => {
  if (!marker) {
    return 0;
  }
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

fs.mkdirSync(partsRoot, { recursive: true });

const parts = partSpecs.map(([fileName], index) => {
  const start = starts[index];
  const end = index + 1 < starts.length ? starts[index + 1] : source.length;
  const body = source.slice(start, end);
  fs.writeFileSync(path.join(partsRoot, fileName), body, "utf8");
  return {
    file: fileName,
    line_start: lineNumberAt(lineStarts, start),
    line_end: lineNumberAt(lineStarts, Math.max(start, end - 1)),
    bytes: Buffer.byteLength(body, "utf8"),
    sha256: sha256(body),
    first: firstRoute(body),
    last: lastRoute(body),
  };
});

const rebuilt = parts.map((part) => fs.readFileSync(path.join(partsRoot, part.file), "utf8")).join("");
if (rebuilt !== source) {
  throw new Error("Internal split check failed: rebuilt 03_handler_get_routes.py does not match source.");
}

const manifest = {
  version: 1,
  source: "FUTURE/server_parts/http_server/03_handler_get_routes.py",
  mode: "get_route_method_fragments",
  source_sha256: sha256(source),
  parts,
};

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  ok: true,
  source: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map((part) => ({
    file: path.join("FUTURE", "server_parts", "http_server", "get_route_parts", part.file),
    lines: `${part.line_start}-${part.line_end}`,
    bytes: part.bytes,
    first: part.first,
    last: part.last,
  })),
  sha256: manifest.source_sha256,
}, null, 2));
