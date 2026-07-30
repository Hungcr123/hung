# Future JS Runtime Parts

These files are ordered body chunks for `FUTURE/web/future.js`.

`future.js` is still the browser-served entrypoint. The app should continue loading only:

```html
<script src="/future-assets/future.js"></script>
```

## Workflow

1. Edit the relevant ordered part in this folder.
2. Rebuild the served entrypoint:

   ```powershell
   node FUTURE\tools\build_future_js.cjs
   ```

3. Verify the generated entrypoint matches the parts:

   ```powershell
   node FUTURE\tools\build_future_js.cjs --check
   ```

4. Parse-check the browser runtime:

   ```powershell
   node -e "const fs=require('fs'); new Function(fs.readFileSync('FUTURE/web/future.js','utf8')); console.log('future.js parse ok')"
   ```

## Guardrails

- These chunks are not independent browser modules yet.
- The parts are concatenated inside the original single IIFE wrapper so shared `const`/`let` state keeps the same scope as before.
- Keep the order in `manifest.json` stable unless the code dependency order has been mapped.
- Do not switch `future.html` to multiple `<script>` tags for these files; doing that would move code out of the original IIFE scope.
