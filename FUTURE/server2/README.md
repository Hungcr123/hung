# Future Server 2

Server 2 is the split Future runtime. It keeps the stable root `FUTURE_SERVER.py` untouched and serves:

- `FUTURE/web/future_split.html`
- `FUTURE/web/future.css`
- `FUTURE/web/future.js`
- `FUTURE/server2/future_stt_worker_2.py`

Default ports:

- App: `8877`
- STT worker: `8878`

Run from `C:\programe\write_html\FUTURE`:

```powershell
.\RUN_SERVER_2.bat
```

Or:

```powershell
python .\server2\run_server_2.py
```

## WebRTC screen share across different networks

The screen-share button uses direct WebRTC first and falls back to server-relayed JPEG frames when direct WebRTC cannot cross NAT/CGNAT. For smoother direct video across different Internet networks, configure a public TURN server before starting Server 2:

```powershell
$env:FUTURE_TURN_URLS="turn:YOUR_TURN_HOST:3478?transport=udp,turn:YOUR_TURN_HOST:3478?transport=tcp"
$env:FUTURE_TURN_USERNAME="YOUR_TURN_USER"
$env:FUTURE_TURN_CREDENTIAL="YOUR_TURN_PASSWORD"
.\RUN_SERVER_2.bat
```

Optional strict relay mode:

```powershell
$env:FUTURE_WEBRTC_FORCE_RELAY="1"
```

For Cốc Cốc after a server update, use Ctrl+F5 once if an old tab is still showing a cached page.
