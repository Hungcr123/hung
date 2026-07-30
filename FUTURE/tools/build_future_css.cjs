const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "web", "future.css");
const partsRoot = path.join(root, "FUTURE", "web", "css_parts");
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
  if (!manifest || manifest.version !== 1 || !Array.isArray(manifest.parts)) {
    throw new Error("Unsupported future.css parts manifest.");
  }
  return manifest;
}

function buildSource(manifest) {
  return manifest.parts.map((part) => {
    const fileName = String(part.file || "");
    if (!fileName || fileName.includes("..") || path.isAbsolute(fileName)) {
      throw new Error(`Invalid part file in manifest: ${fileName}`);
    }
    const filePath = path.join(partsRoot, fileName);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Missing future.css part: ${path.relative(root, filePath)}`);
    }
    return fs.readFileSync(filePath, "utf8");
  }).join("");
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
      error: "FUTURE/web/future.css does not match css_parts build output.",
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
