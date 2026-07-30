const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const htmlPath = path.join(root, "future.html");
const cssPath = path.join(root, "FUTURE", "web", "future.css");
const jsPath = path.join(root, "FUTURE", "web", "future.js");

const html = fs.readFileSync(htmlPath, "utf8");
const styleOpen = html.indexOf("<style>");
const styleClose = styleOpen >= 0 ? html.indexOf("</style>", styleOpen) : -1;
const bodyOpen = styleClose >= 0 ? html.indexOf("<body", styleClose) : -1;
const scriptOpen = bodyOpen >= 0 ? html.indexOf("<script>", bodyOpen) : -1;
const scriptClose = scriptOpen >= 0 ? html.lastIndexOf("</script>") : -1;

if (styleOpen < 0 || styleClose < 0 || bodyOpen < 0 || scriptOpen < 0 || scriptClose < scriptOpen) {
  throw new Error("Could not find the expected inline style/script blocks in future.html.");
}

const css = html.slice(styleOpen + "<style>".length, styleClose);
const js = html.slice(scriptOpen + "<script>".length, scriptClose);
const slimHtml =
  html.slice(0, styleOpen) +
  '<link rel="stylesheet" href="/future-assets/future.css">\n' +
  html.slice(styleClose + "</style>".length, scriptOpen) +
  '<script src="/future-assets/future.js"></script>' +
  html.slice(scriptClose + "</script>".length);

fs.mkdirSync(path.dirname(cssPath), { recursive: true });
fs.writeFileSync(cssPath, css, "utf8");
fs.writeFileSync(jsPath, js, "utf8");
fs.writeFileSync(htmlPath, slimHtml, "utf8");

console.log(JSON.stringify({
  html: path.relative(root, htmlPath),
  css: path.relative(root, cssPath),
  js: path.relative(root, jsPath),
  cssBytes: Buffer.byteLength(css, "utf8"),
  jsBytes: Buffer.byteLength(js, "utf8"),
  htmlBytes: Buffer.byteLength(slimHtml, "utf8")
}, null, 2));
