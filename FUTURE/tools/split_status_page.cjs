const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "vocab_build_status", "03_status_page.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "vocab_build_status", "status_page_parts");
const manifestPath = path.join(partsRoot, "manifest.json");
const targetBytes = 75 * 1024;

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function assertFreshPartsFolder() {
  if (!fs.existsSync(partsRoot)) {
    return;
  }
  const existing = fs.readdirSync(partsRoot).filter((name) => name.endsWith(".pyfrag") || name === "manifest.json");
  if (existing.length) {
    throw new Error(`Refusing to overwrite existing status_page_parts files. Remove or archive ${path.relative(root, partsRoot)} first.`);
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

function markerEnd(source, marker) {
  const index = source.indexOf(marker);
  if (index < 0) {
    throw new Error(`Missing status page marker: ${marker}`);
  }
  const newline = source.indexOf("\n", index);
  return newline < 0 ? source.length : newline + 1;
}

function markerStart(source, marker) {
  const index = source.indexOf(marker);
  if (index < 0) {
    throw new Error(`Missing status page marker: ${marker}`);
  }
  return index;
}

function chunkRegion(source, start, end, label, state) {
  if (end <= start) {
    return [];
  }
  const parts = [];
  let offset = start;
  let chunkIndex = 1;
  while (offset < end) {
    const remaining = end - offset;
    let next = end;
    if (remaining > targetBytes) {
      const hardEnd = Math.min(end, offset + targetBytes);
      const newline = source.lastIndexOf("\n", hardEnd);
      next = newline > offset ? newline + 1 : hardEnd;
    }
    const body = source.slice(offset, next);
    const suffix = end - start > targetBytes ? `_${String(chunkIndex).padStart(2, "0")}` : "";
    const file = `${String(state.nextPartNumber).padStart(2, "0")}_${label}${suffix}.pyfrag`;
    fs.writeFileSync(path.join(partsRoot, file), body, "utf8");
    parts.push({
      file,
      region: label,
      line_start: lineNumberAt(state.lineStarts, offset),
      line_end: lineNumberAt(state.lineStarts, Math.max(offset, next - 1)),
      bytes: Buffer.byteLength(body, "utf8"),
      sha256: sha256(body),
    });
    state.nextPartNumber += 1;
    chunkIndex += 1;
    offset = next;
  }
  return parts;
}

assertFreshPartsFolder();

const source = fs.readFileSync(sourcePath, "utf8");
const styleStart = markerStart(source, "  <style>");
const styleEnd = markerEnd(source, "  </style>");
const scriptStart = markerStart(source, "  <script>");
const scriptEnd = markerEnd(source, "  </script>");

if (!(styleStart < styleEnd && styleEnd < scriptStart && scriptStart < scriptEnd)) {
  throw new Error("Status page markers are not in the expected order.");
}

fs.mkdirSync(partsRoot, { recursive: true });

const state = {
  lineStarts: lineStartsFor(source),
  nextPartNumber: 1,
};

const regions = [
  ["function_head", 0, styleStart],
  ["dashboard_styles", styleStart, styleEnd],
  ["dashboard_markup", styleEnd, scriptStart],
  ["dashboard_script", scriptStart, scriptEnd],
  ["function_tail", scriptEnd, source.length],
];

const parts = regions.flatMap(([label, start, end]) => chunkRegion(source, start, end, label, state));
const rebuilt = parts.map((part) => fs.readFileSync(path.join(partsRoot, part.file), "utf8")).join("");
if (rebuilt !== source) {
  throw new Error("Internal split check failed: rebuilt 03_status_page.py does not match source.");
}

const manifest = {
  version: 1,
  source: "FUTURE/server_parts/vocab_build_status/03_status_page.py",
  mode: "status_page_fstring_fragments",
  target_bytes: targetBytes,
  source_sha256: sha256(source),
  markers: {
    style_start: styleStart,
    style_end: styleEnd,
    script_start: scriptStart,
    script_end: scriptEnd,
  },
  parts,
};

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  ok: true,
  source: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map((part) => ({
    file: path.join("FUTURE", "server_parts", "vocab_build_status", "status_page_parts", part.file),
    region: part.region,
    lines: `${part.line_start}-${part.line_end}`,
    bytes: part.bytes,
  })),
  sha256: manifest.source_sha256,
}, null, 2));
