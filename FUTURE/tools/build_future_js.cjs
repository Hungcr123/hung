const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "web", "future.js");
const partsRoot = path.join(root, "FUTURE", "web", "js_parts");
const manifestPath = path.join(partsRoot, "manifest.json");

const args = new Set(process.argv.slice(2));
const checkOnly = args.has("--check");

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function readManifest() {
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`Missing manifest: ${path.relative(root, manifestPath)}`);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  if (!manifest || manifest.version !== 1 || !manifest.wrapper || !Array.isArray(manifest.parts)) {
    throw new Error("Unsupported future.js parts manifest.");
  }
  return manifest;
}

function buildSource(manifest) {
  const prefix = String(manifest.wrapper.prefix || "");
  const suffix = String(manifest.wrapper.suffix || "");
  const body = manifest.parts.map((part) => {
    const fileName = String(part.file || "");
    if (!fileName || fileName.includes("..") || path.isAbsolute(fileName)) {
      throw new Error(`Invalid part file in manifest: ${fileName}`);
    }
    const filePath = path.join(partsRoot, fileName);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Missing future.js part: ${path.relative(root, filePath)}`);
    }
    return fs.readFileSync(filePath, "utf8");
  }).join("");
  return `${prefix}${body}${suffix}`;
}

const manifest = readManifest();
const generated = buildSource(manifest);
const generatedHash = sha256(generated);
const existing = fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, "utf8") : "";
const existingHash = sha256(existing);

if (checkOnly) {
  if (generated !== existing) {
    console.error(JSON.stringify({
      ok: false,
      error: "FUTURE/web/future.js does not match js_parts build output.",
      generated_sha256: generatedHash,
      existing_sha256: existingHash,
      parts: manifest.parts.length,
    }, null, 2));
    process.exit(1);
  }
  console.log(JSON.stringify({
    ok: true,
    mode: "check",
    file: path.relative(root, sourcePath),
    parts: manifest.parts.length,
    bytes: Buffer.byteLength(generated, "utf8"),
    sha256: generatedHash,
  }, null, 2));
  process.exit(0);
}

fs.writeFileSync(sourcePath, generated, "utf8");
console.log(JSON.stringify({
  ok: true,
  mode: "write",
  file: path.relative(root, sourcePath),
  parts: manifest.parts.length,
  bytes: Buffer.byteLength(generated, "utf8"),
  sha256: generatedHash,
}, null, 2));
