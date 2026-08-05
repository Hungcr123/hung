from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "FUTURE/server2/future_worker_auto.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("future_worker_auto_contract", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


assert module.worker_server_url_allowed("http://192.168.1.21:8890")
assert module.worker_server_url_allowed("http://127.0.0.1:8890")
assert not module.worker_server_url_allowed("https://qm-tech.io.vn")
assert not module.worker_server_url_allowed("https://name.trycloudflare.com")
assert not module.worker_server_url_allowed("http://192.168.1.21:8877")
assert module.worker_server_url_allowed("http://192.168.1.21:8877", allow_legacy=True)
assert not module.worker_server_url_allowed("http://8.8.8.8:8890")

print("worker_auto_lan_url_contract=ok public=blocked legacy=explicit_only")
