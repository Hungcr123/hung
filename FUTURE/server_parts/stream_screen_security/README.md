# Stream/Screen/Security Runtime Parts

These files are loaded by `FUTURE/server_parts/05_stream_screen_security.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the load order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_stream_sessions.py`
   - Dashboard online state, audio stream sessions, WebRTC stream signaling, stream chunks, and stream cleanup.

2. `02_screen_sessions.py`
   - Screen preview sessions, WebRTC screen signaling, frame polling, remote-control command normalization, and control polling.

3. `03_security_health.py`
   - Local/private host checks, origin normalization, hosted frontend obfuscation decision, CORS allow-listing, and public health payload.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve stream/screen session state names because routes and frontend polling use those strings.
- Preserve WebRTC candidate version/id behavior; clients depend on incremental polling.
- Preserve local/private host detection and CORS behavior because it controls hosted frontend protection.
