# Status Page Source Fragments

These files are ordered source fragments for `FUTURE/server_parts/vocab_build_status/03_status_page.py`.

`03_status_page.py` is still the Python runtime file loaded by the Future server. The fragments are concatenated to rebuild that file byte-for-byte.

## Workflow

1. Edit the relevant fragment in this folder.
2. Rebuild the Python runtime file:

   ```powershell
   node FUTURE\tools\build_status_page.cjs
   ```

3. Verify the runtime file matches the fragments:

   ```powershell
   node FUTURE\tools\build_status_page.cjs --check
   ```

4. Compile and import-check the server before running Future.

## Guardrails

- These fragments are not standalone Python modules.
- The dashboard is one large Python f-string, so preserve doubled braces `{{` and `}}` inside CSS/JavaScript.
- Keep `03_status_page.py` as the runtime entrypoint until the dashboard HTML, CSS, and JavaScript are intentionally extracted into separate template/assets.
- Route/state injections such as `{title}` must remain valid Python f-string expressions after rebuild.
