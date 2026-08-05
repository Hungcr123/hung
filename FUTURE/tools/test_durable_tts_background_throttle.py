import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


class DummyServer:
    _future_active_requests = 0
    _future_active_builder_requests = 0


server = DummyServer()
original_server = getattr(app, "SERVER_HTTPD", None)
original_cpu = app.current_system_cpu_percent
original_guard = app.cpu_guard_settings_snapshot
try:
    app.SERVER_HTTPD = server
    app.current_system_cpu_percent = lambda: 12.0
    app.cpu_guard_settings_snapshot = lambda: {"enabled": True, "threshold": 90}
    assert not app.durable_tts_background_throttle_state()["throttled"]

    server._future_active_requests = 5
    server._future_active_builder_requests = 2
    learner = app.durable_tts_background_throttle_state()
    assert learner["throttled"] and learner["learner_requests"] == 3
    assert learner["reason"] == "learner_requests"

    server._future_active_requests = 2
    server._future_active_builder_requests = 2
    app.current_system_cpu_percent = lambda: 94.0
    cpu = app.durable_tts_background_throttle_state()
    assert cpu["throttled"] and cpu["cpu_high"]
    assert cpu["reason"] == "cpu_high"
finally:
    app.SERVER_HTTPD = original_server
    app.current_system_cpu_percent = original_cpu
    app.cpu_guard_settings_snapshot = original_guard

print("durable_tts_background_throttle=ok learner_gate=true cpu_gate=true")
