"""Regression for cold-listen retry and three-sample steady-state idle gating."""

from pathlib import Path


source = (Path(__file__).parent / "benchmark_server2_mixed_100_users.py").read_text(encoding="utf-8")
warm_start = source.index("def wait_for_server_warm")
warm_end = source.index("def wait_for_server_idle", warm_start)
warm = source[warm_start:warm_end]
idle_start = warm_end
idle_end = source.index("def run_phase", idle_start)
idle = source[idle_start:idle_end]

assert "except requests.RequestException" in warm
assert '"probe_error": str(exc)' in warm
assert "if stable >= 3" in idle
assert "cpu_delta <= 0.25" in idle
assert "not queue_busy" in idle
assert 'not last["writer_depth"]' in idle

print("mixed_benchmark_readiness_gate=ok cold_listen_retry=true idle_samples=3 queues=empty")
