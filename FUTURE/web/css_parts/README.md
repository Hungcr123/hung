# Future CSS Runtime Parts

These files are ordered source chunks for `FUTURE/web/future.css`.

`future.css` is still the browser-served stylesheet entrypoint. The app should continue loading only:

```html
<link rel="stylesheet" href="/future-assets/future.css">
```

## Workflow

1. Edit the relevant ordered part in this folder.
2. Rebuild the served entrypoint:

   ```powershell
   node FUTURE\tools\build_future_css.cjs
   ```

3. Verify the generated entrypoint matches the parts:

   ```powershell
   node FUTURE\tools\build_future_css.cjs --check
   ```

## Guardrails

- These chunks are concatenated in manifest order; cascade order must stay stable.
- Do not switch `future.html` to multiple stylesheet links for these files until cascade dependencies are mapped.
- The split preserves the current CSS byte-for-byte, including one top-level unmatched closing brace already present in the original stylesheet.
- Prefer moving toward semantic UI-domain CSS files gradually after visual smoke tests cover each area.
