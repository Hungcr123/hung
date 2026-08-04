from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CLIENT_VERSION = "2026-07-22"
HTTP_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 FutureWorker/2026.07 Safari/537.36"
WORKER_WARM_LOCK = threading.RLock()
WORKER_WARMED: set[str] = set()
WORKER_FEATURES_LOCK = threading.RLock()
WORKER_RUNTIME_FEATURES: dict[str, object] = {}
WORKER_JOB_KINDS = ("translate", "tts", "stt", "gemini", "phonemize")
WORKER_ONNX_TTS_LOCK = threading.RLock()
WORKER_NATIVE_DLL_LOCK = threading.RLock()
WORKER_NATIVE_DLL_PATHS: set[str] = set()
WORKER_NATIVE_DLL_HANDLES: list[object] = []
# Added 2026-07-07: lets Server 2 config control real pool use without rebuilding clients.
DEFAULT_MAX_JOBS = "translate=16,tts=16,stt=16,gemini=16,phonemize=16"
DEFAULT_SERVER_URL = ""
DEFAULT_WORKER_TOKEN = ""
MAX_JOBS_PER_KIND = 16
ACTIVE_LOCK = threading.RLock()
ACTIVE_JOBS: dict[str, list[str]] = {kind: [] for kind in WORKER_JOB_KINDS}


def clean(value: object = "") -> str:
    return str(value or "").replace("\x00", "").strip()

def clean_tts_text(value: object = "") -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[\r\n\u2028\u2029]+", " ", text)
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# Added 2026-07-13: registers PyInstaller onedir native DLL folders before ML imports.
def configure_worker_native_dll_paths() -> dict:
    if os.name != "nt":
        return {"ok": True, "paths": []}
    candidates: list[Path] = []
    try:
        if getattr(sys, "_MEIPASS", ""):
            candidates.append(Path(getattr(sys, "_MEIPASS")).resolve())
    except Exception:
        pass
    try:
        candidates.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass
    try:
        candidates.append(Path.cwd().resolve())
    except Exception:
        pass
    expanded: list[Path] = []
    for root in candidates:
        expanded.extend(
            [
                root,
                root / "_internal",
                root / "torch" / "lib",
                root / "_internal" / "torch" / "lib",
                root / "ctranslate2",
                root / "_internal" / "ctranslate2",
                root / "onnxruntime" / "capi",
                root / "_internal" / "onnxruntime" / "capi",
                root / "av",
                root / "_internal" / "av",
                root / "numpy.libs",
                root / "_internal" / "numpy.libs",
            ]
        )
    added: list[str] = []
    with WORKER_NATIVE_DLL_LOCK:
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        lower_path_parts = {part.lower() for part in path_parts if part}
        for item in expanded:
            try:
                resolved = item.resolve()
            except Exception:
                continue
            if not resolved.exists():
                continue
            text = str(resolved)
            lower = text.lower()
            if lower not in lower_path_parts:
                os.environ["PATH"] = text + os.pathsep + os.environ.get("PATH", "")
                lower_path_parts.add(lower)
            if lower not in WORKER_NATIVE_DLL_PATHS and hasattr(os, "add_dll_directory"):
                try:
                    WORKER_NATIVE_DLL_HANDLES.append(os.add_dll_directory(text))
                except (FileNotFoundError, OSError):
                    pass
            if lower not in WORKER_NATIVE_DLL_PATHS:
                WORKER_NATIVE_DLL_PATHS.add(lower)
                added.append(text)
    return {"ok": True, "paths": added}


# Added 2026-07-07: identifies a physical client machine without relying on proxy/NAT IP.
def worker_machine_id(name: str) -> str:
    hostname = clean(socket.gethostname() or os.environ.get("COMPUTERNAME", "") or name).lower()
    mac = ""
    try:
        mac = f"{uuid.getnode():012x}"
    except Exception:
        mac = ""
    raw = f"{hostname}|{mac}"
    digest = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{hostname or 'machine'}-{digest}"


def clean_capabilities(value: str) -> list[str]:
    result: list[str] = []
    for item in str(value or "").replace(";", ",").replace("|", ",").split(","):
        key = clean(item).lower()
        if key in WORKER_JOB_KINDS and key not in result:
            result.append(key)
    return result or ["translate"]


# Added 2026-07-11: advertises Kokoro VI only when this worker has the real Python runtime and model files.
def worker_runtime_features(capabilities: list[str]) -> dict[str, object]:
    features = {
        "tts_kokoro_vi": False,
        "tts_kokoro_vi_cuda": False,
        "tts_kokoro_vi_warm": False,
        "phonemize_warm": False,
        "spacy_warm": False,
        "kokoro_vi_error": "",
    }
    if "tts" not in capabilities:
        return features
    try:
        # Added 2026-07-14: keep the Kokoro VI probe on the same builder path as the known-good WorkerAuto build.
        import future_lesson_builder_gui as builder  # type: ignore

        download_files = clean(os.environ.get("FUTURE_PREPARE_KOKORO_VI_FILES", "1")).lower() not in {"0", "false", "no", "off"}
        state = builder.ensure_kokoro_vietnamese_model_files(download=download_files, log=None)
        missing_model = [key for key in ("onnx", "config", "default_voicepack") if not bool(state.get(key))]
        if missing_model:
            root = clean(state.get("root", ""))
            detail = ", ".join(missing_model)
            features["kokoro_vi_error"] = f"missing model files: {detail}; root={root or 'unknown'}"
            return features
    except Exception as exc:
        features["kokoro_vi_error"] = f"model check failed: {clean(exc)[:220]}"
        return features
    candidates: list[list[str]] = []
    env_python = clean(os.environ.get("FUTURE_KOKORO_VI_PYTHON", ""))
    if env_python:
        candidates.append([env_python])
    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable])
    candidates.extend([["python"], ["py", "-3"]])
    for candidate in candidates:
        try:
            probe = subprocess.run(
                [
                    *candidate,
                    "-c",
                    (
                        "import sys, kokoro_vietnamese.onnx_cli, onnxruntime as ort, soundfile; "
                        "assert hasattr(ort, 'InferenceSession'), getattr(ort, '__file__', 'onnxruntime missing file'); "
                        "print('ok|' + sys.executable + '|' + str(getattr(ort, '__file__', '')))"
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if probe.returncode == 0 and "ok" in str(probe.stdout or ""):
                features["tts_kokoro_vi"] = True
                features["kokoro_vi_error"] = ""
                features["kokoro_vi_python"] = clean(str(probe.stdout or "").split("|")[1] if "|" in str(probe.stdout or "") else " ".join(candidate))
                try:
                    cuda_probe = subprocess.run(
                        [*candidate, "-c", "import onnxruntime as ort; print('CUDAExecutionProvider' in ort.get_available_providers())"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=12,
                        check=False,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    features["tts_kokoro_vi_cuda"] = cuda_probe.returncode == 0 and "True" in str(cuda_probe.stdout or "")
                except Exception:
                    features["tts_kokoro_vi_cuda"] = False
                break
            detail = clean((probe.stderr or probe.stdout or "")[-500:])
            features["kokoro_vi_error"] = f"python {' '.join(candidate)} cannot import Kokoro VI deps: {detail or 'no detail'}"
        except Exception:
            features["kokoro_vi_error"] = f"python {' '.join(candidate)} probe failed"
            continue
    if not features.get("tts_kokoro_vi") and not features.get("kokoro_vi_error"):
        features["kokoro_vi_error"] = "no usable Python found for kokoro-vietnamese/onnxruntime/soundfile"
    return features


def mark_worker_feature(key: str, value: object) -> None:
    clean_key = clean(key)
    if not clean_key:
        return
    with WORKER_FEATURES_LOCK:
        WORKER_RUNTIME_FEATURES[clean_key] = value


def parse_max_jobs_by_kind(raw: str, capabilities: list[str]) -> dict[str, int]:
    # Added 2026-07-07: lets portable workers expose lane capacity while defaulting to one job per type.
    result = {kind: (1 if kind in capabilities else 0) for kind in WORKER_JOB_KINDS}
    text = clean(raw)
    if not text:
        return result
    for item in text.replace(";", ",").replace("|", ",").split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        kind = clean(key).lower()
        if kind not in result:
            continue
        try:
            amount = int(float(value))
        except Exception:
            amount = result[kind]
        result[kind] = max(0, min(MAX_JOBS_PER_KIND, amount))
    return result


def active_jobs_snapshot() -> dict[str, list[str]]:
    with ACTIVE_LOCK:
        return {kind: list(ACTIVE_JOBS.get(kind, [])) for kind in WORKER_JOB_KINDS}


def active_job_count(kind: str) -> int:
    key = clean(kind).lower()
    with ACTIVE_LOCK:
        return len([item for item in ACTIVE_JOBS.get(key, []) if item])


def worker_has_free_slot(max_jobs_by_kind: dict[str, int], capabilities: list[str]) -> bool:
    with ACTIVE_LOCK:
        for kind in capabilities:
            limit = max(0, int(max_jobs_by_kind.get(kind, 0) or 0))
            if limit > len([item for item in ACTIVE_JOBS.get(kind, []) if item]):
                return True
    return False


def worker_free_slot_count(max_jobs_by_kind: dict[str, int], capabilities: list[str]) -> int:
    total = 0
    with ACTIVE_LOCK:
        for kind in capabilities:
            limit = max(0, int(max_jobs_by_kind.get(kind, 0) or 0))
            used = len([item for item in ACTIVE_JOBS.get(kind, []) if item])
            total += max(0, limit - used)
    return total


def mark_active_job(kind: str, job_id: str, active: bool) -> None:
    key = clean(kind).lower()
    if key not in ACTIVE_JOBS:
        return
    with ACTIVE_LOCK:
        current = [item for item in ACTIVE_JOBS.get(key, []) if item and item != job_id]
        if active and job_id:
            current.append(job_id)
        ACTIVE_JOBS[key] = current


def configure_worker_runtime_environment() -> None:
    configure_worker_native_dll_paths()
    # Added 2026-07-07: one-file classroom workers do not ship Kokoro's sidecar helper exe.
    if bool(getattr(sys, "frozen", False)):
        os.environ.setdefault("KOKORO_DISABLE_HELPER", "1")
    key_names = ("gemini_key.txt", "gemini_keys.txt", "key.txt")
    roots: list[Path] = []
    try:
        roots.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass
    try:
        roots.append(Path.cwd().resolve())
    except Exception:
        pass
    for root in roots:
        for name in key_names:
            candidate = root / name
            if candidate.is_file():
                os.environ.setdefault("FUTURE_GEMINI_KEY_FILE", str(candidate))
                return


def configure_import_roots(app_root: str = "") -> None:
    configure_worker_runtime_environment()
    candidates = []
    if app_root:
        candidates.append(Path(app_root))
    here = Path(__file__).resolve()
    frozen_root = getattr(sys, "_MEIPASS", "")
    if frozen_root:
        candidates.append(Path(frozen_root))
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir, exe_dir.parent])
    except Exception:
        pass
    candidates.extend([here.parent, here.parent.parent, here.parent.parent.parent, Path.cwd(), Path.cwd().parent])
    # Added 2026-07-07: portable packages can carry C:\QMLearn-style models beside the worker.
    for portable_root in candidates:
        try:
            resolved = portable_root.resolve()
        except Exception:
            continue
        if (resolved / "models").exists():
            if not os.environ.get("FUTURE_QMLEARN_ROOT"):
                os.environ["FUTURE_QMLEARN_ROOT"] = str(resolved)
            os.environ.setdefault("QMLEARN_ROOT", str(resolved))
            break
    for candidate in candidates:
        try:
            root = candidate.resolve()
        except Exception:
            continue
        for item in (root, root / "FUTURE", root / "module_main"):
            text = str(item)
            if item.exists() and text not in sys.path:
                sys.path.insert(0, text)


# Added 2026-07-07: remote workers keep heavy translate/TTS/STT runtimes hot in RAM between jobs.
def warm_worker_runtime(kind: str = "", force: bool = False) -> dict:
    configure_import_roots()
    key = clean(kind).lower() or "all"
    with WORKER_WARM_LOCK:
        if key in WORKER_WARMED and not force:
            return {"kind": key, "cached": True}
        started = time.time()
        if key == "translate":
            from FUTURE.server_parts.worker_jobs.heavy_language_jobs import warm_language_worker

            result = warm_language_worker("translate")
        elif key == "tts":
            from FUTURE.server_parts.worker_jobs.heavy_language_jobs import warm_language_worker

            if clean(os.environ.get("FUTURE_WARM_ALL_KOKORO_VI", "")).lower() in {"1", "true", "yes", "on"}:
                os.environ["FUTURE_KOKORO_VI_IN_PROCESS"] = "1"
                os.environ["FUTURE_TTS_LOCAL_ONLY"] = "1"
                os.environ.setdefault("FUTURE_KOKORO_VI_DEVICE", "cpu")
            warm_language_worker("voice")
            result = warm_language_worker("voice-model")
            # Added 2026-07-07: validates Kokoro/eSpeak packaged data during warmup, before a learner waits for TTS.
            if clean(os.environ.get("FUTURE_WARM_KOKORO_EN", "")).lower() in {"1", "true", "yes", "on"}:
                # Added 2026-07-14: use the same builder path as the stable D: WorkerAuto build.
                import future_lesson_builder_gui as builder  # type: ignore

                try:
                    builder.synthesize_embedded_audio("Worker voice ready.", "kokoro:am_adam", lambda _message: None)
                    result = {**(result if isinstance(result, dict) else {}), "tts_smoke": True}
                except RuntimeError as exc:
                    if "Kokoro helper executable not found" not in str(exc):
                        raise
                    os.environ["KOKORO_DISABLE_HELPER"] = "1"
                    try:
                        setattr(builder, "_KOKORO_RUNTIME", None)
                    except Exception:
                        pass
                    builder.synthesize_embedded_audio("Worker voice ready.", "kokoro:am_adam", lambda _message: None)
                    result = {**(result if isinstance(result, dict) else {}), "tts_smoke": True, "kokoro_helper_disabled": True}
        elif key in {"stt", "phonemize"}:
            import FUTURE.server2.run_server_2 as future  # type: ignore
            from FUTURE.server_parts.worker_jobs.heavy_language_jobs import warm_language_worker

            warm_parts: dict[str, object] = {}
            preload = getattr(future, "preload_model_sync", None)
            if key == "stt" and callable(preload):
                try:
                    warm_parts["whisper_preloaded"] = bool(preload("small", "en"))
                except Exception as exc:
                    warm_parts["whisper_error"] = clean(exc)
            for queue_name, warm_kind in (("PHONETIC_WORK_QUEUE", "phonetic"), ("SPACY_WORK_QUEUE", "spacy")):
                queue_obj = getattr(future, queue_name, None)
                try:
                    if queue_obj is not None and callable(getattr(queue_obj, "warm", None)):
                        queue_obj.warm(f"worker-warm:{warm_kind}", warm_language_worker, warm_kind, timeout=min(90, int(getattr(queue_obj, "timeout_seconds", 90) or 90)))
                    else:
                        warm_language_worker(warm_kind)
                    warm_parts[f"{warm_kind}_warmed"] = True
                    mark_worker_feature("phonemize_warm" if warm_kind == "phonetic" else "spacy_warm", True)
                except Exception as exc:
                    warm_parts[f"{warm_kind}_error"] = clean(exc)
            result = {"kind": key, "ok": True, "transcribe_ready": callable(getattr(future, "transcribe_audio", None)), **warm_parts}
        elif key == "gemini":
            result = {"kind": key, "ok": True, "network_ready": True}
        else:
            result = {"kind": key, "ok": True}
        WORKER_WARMED.add(key)
        result.setdefault("ms", int((time.time() - started) * 1000))
        if key == "tts":
            vi_payload = result.get("vi", {}) if isinstance(result, dict) else {}
            warmed_rows = vi_payload.get("warmed", []) if isinstance(vi_payload, dict) else []
            if any(clean(row.get("voice", "")).lower().startswith("kokoro_vi:") for row in warmed_rows if isinstance(row, dict)):
                mark_worker_feature("tts_kokoro_vi_warm", True)
        return result


def warm_worker_runtime_background(capabilities: list[str], server: str = "", base_payload: dict | None = None) -> None:
    def runner() -> None:
        for kind in capabilities:
            try:
                result = warm_worker_runtime(kind)
                print(f"WARM | {worker_job_source_label(kind, {})} | ready {int(result.get('ms', 0) or 0)}ms", flush=True)
            except Exception as exc:
                error = f"{exc}\n{traceback.format_exc()}"
                print(f"WARM | {worker_job_source_label(kind, {})} | failed: {exc}", flush=True)
                if server:
                    report_worker_log(server, base_payload or {}, f"warm {kind} failed", kind=kind, error=error)

    threading.Thread(target=runner, name="future-distributed-worker-warm", daemon=True).start()


def http_json(server: str, path: str, payload: dict, timeout: float | None = 30.0) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        server.rstrip("/") + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {payload.get('token', '')}",
            "User-Agent": HTTP_USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
    except HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            raw = b""
        message = ""
        migrate_to = ""
        if raw:
            try:
                parsed_error = json.loads(raw.decode("utf-8", errors="replace") or "{}")
                if isinstance(parsed_error, dict):
                    message = clean(parsed_error.get("error", ""))
                    migrate_to = clean(parsed_error.get("migrate_to", ""))
            except Exception:
                message = clean(raw.decode("utf-8", errors="replace"))
        error = RuntimeError(f"HTTP {exc.code}: {message or exc.reason or 'Server rejected request.'}")
        if migrate_to:
            setattr(error, "migrate_to", migrate_to)
        raise error from exc
    parsed = json.loads(data.decode("utf-8", errors="replace") or "{}")
    if not isinstance(parsed, dict):
        raise RuntimeError("Invalid server response.")
    if parsed.get("ok") is False:
        raise RuntimeError(clean(parsed.get("error", "")) or "Server rejected request.")
    return parsed


# Added 2026-07-11: retries large TTS result uploads when Server 2 or Windows aborts a busy socket.
def http_json_retry(server: str, path: str, payload: dict, timeout: float | None = 30.0, attempts: int = 1, delay: float = 1.0) -> dict:
    last_exc: Exception | None = None
    total = max(1, int(attempts or 1))
    for index in range(total):
        try:
            return http_json(server, path, payload, timeout=timeout)
        except Exception as exc:
            last_exc = exc
            if index + 1 >= total:
                break
            print(f"post {path} retry {index + 1}/{total} after: {exc}", flush=True)
            time.sleep(max(0.2, float(delay or 0.2)) * (index + 1))
    raise last_exc or RuntimeError(f"Failed to POST {path}.")


# Added 2026-07-07: auto-sends worker failures to Server 2 with version/job context.
def report_worker_log(server: str, base_payload: dict, message: str, *, kind: str = "", job_id: str = "", error: str = "") -> None:
    try:
        payload = {
            **(base_payload if isinstance(base_payload, dict) else {}),
            "message": str(message or "")[-12000:],
            "kind": clean(kind),
            "job_id": clean(job_id),
            "error": str(error or "")[-12000:],
            "version": CLIENT_VERSION,
            "reported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        http_json(server, "/distributed-worker/log", payload, timeout=12)
    except Exception:
        pass


# Added 2026-07-14: names worker job sources clearly for dashboard logs and Server 2 diagnostics.
def worker_tts_source_label(voice: str) -> str:
    key = clean(voice).lower()
    if key.startswith("edge:"):
        return "TTS | online Edge/Microsoft"
    if key.startswith(("sot:", "soundoftext:")):
        return "TTS | online SoundOfText"
    if key.startswith("kokoro_vi:"):
        return "TTS | local Kokoro VI"
    if key.startswith("kokoro:"):
        return "TTS | local Kokoro EN"
    if "neural" in key or key.startswith(("vi-vn-", "en-us-", "en-gb-")):
        return "TTS | online Edge/Microsoft"
    return "TTS | unknown voice source"


def worker_job_source_label(kind: str, payload: dict | None = None, result: dict | None = None) -> str:
    data = payload if isinstance(payload, dict) else {}
    output = result if isinstance(result, dict) else {}
    lowered = clean(kind).lower()
    if lowered == "tts":
        voice = clean(output.get("voice", "") or data.get("voice", "") or data.get("voice_key", ""))
        return f"{worker_tts_source_label(voice)} | {voice or 'voice?'}"
    if lowered == "stt":
        model = clean(output.get("model", "") or data.get("model_name", "small")) or "small"
        language = clean(output.get("language", "") or data.get("language", "en")) or "en"
        cached = output.get("cached_ready")
        cache_note = "cached model" if cached is True else "fresh/preload model" if cached is False else "model"
        return f"STT | local Faster-Whisper {model} | {language} | {cache_note}"
    if lowered == "translate":
        src = clean(output.get("src", "") or data.get("src", "auto")) or "auto"
        dest = clean(output.get("dest", "") or data.get("dest", "en")) or "en"
        result_source = clean(output.get("source", "")) or "fresh/cache?"
        engine = clean(output.get("engine", "")) or "googletrans/http"
        return f"TRANSLATE | {result_source} {engine} | {src}->{dest}"
    if lowered == "gemini":
        model = clean(output.get("model", "") or data.get("model", "gemini-1.5-flash")) or "gemini"
        return f"GEMINI | online Google Gemini | {model}"
    if lowered == "phonemize":
        voice = clean(output.get("voice", "") or data.get("voice", "en-US")) or "en-US"
        return f"PHONEMIZE | local IPA/spaCy | {voice}"
    return clean(kind).upper() or "JOB"


def translate_job(payload: dict) -> dict:
    warm_worker_runtime("translate")
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import translate_text_once_worker_with_meta

    text = str(payload.get("text", "") or "")
    dest = clean(payload.get("dest", "en")) or "en"
    src = clean(payload.get("src", "auto")) or "auto"
    limit = max(1, int(payload.get("limit", 2200) or 2200))
    force_refresh = str(payload.get("force", payload.get("force_refresh", payload.get("forceRefresh", ""))) or "").strip().lower() in {"1", "true", "yes", "on", "force"}
    return translate_text_once_worker_with_meta(text, dest=dest, src=src, limit=limit, force_refresh=force_refresh)


def tts_job(payload: dict) -> dict:
    warm_worker_runtime("tts")
    text = clean_tts_text(payload.get("text", "") or "")
    voice = clean(payload.get("voice", "") or payload.get("voice_key", ""))
    if not text:
        raise RuntimeError("Empty TTS text.")
    if not voice:
        raise RuntimeError("Missing voice.")
    old_bridge_disabled = os.environ.get("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", "")
    os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = "1"
    try:
        # Added 2026-07-14: keep TTS on the stable builder path used by the D: WorkerAuto build.
        import future_lesson_builder_gui as builder  # type: ignore
        from FUTURE.server_parts.worker_jobs.heavy_language_jobs import _chat_audio_timing_payload

        try:
            # Added 2026-07-13: ONNX/Kokoro DLL initialization can race inside a one-file worker when many TTS lanes start at once.
            if voice.lower().startswith(("kokoro_vi:", "kokoro:")):
                with WORKER_ONNX_TTS_LOCK:
                    audio_bytes, mime = builder.synthesize_embedded_audio(text, voice, lambda _message: None)
            else:
                audio_bytes, mime = builder.synthesize_embedded_audio(text, voice, lambda _message: None)
        except RuntimeError as exc:
            if "Kokoro helper executable not found" not in str(exc):
                raise
            os.environ["KOKORO_DISABLE_HELPER"] = "1"
            try:
                setattr(builder, "_KOKORO_RUNTIME", None)
            except Exception:
                pass
            audio_bytes, mime = builder.synthesize_embedded_audio(text, voice, lambda _message: None)
    finally:
        if old_bridge_disabled:
            os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = old_bridge_disabled
        else:
            os.environ.pop("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", None)
    timing = _chat_audio_timing_payload(builder, text, voice, audio_bytes, mime)
    normalized = builder.normalize_audio_voice_key(voice) or voice
    return {
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "audio_mime": mime,
        "voice": normalized,
        "voice_label": builder.embedded_voice_label(voice),
        **timing,
    }


def stt_job(payload: dict) -> dict:
    warm_worker_runtime("stt")
    import FUTURE.server2.run_server_2 as future  # type: ignore

    audio_b64 = clean(payload.get("audio_base64", ""))
    if not audio_b64:
        raise RuntimeError("Missing audio data.")
    audio_bytes = base64.b64decode(audio_b64.encode("ascii"), validate=True)
    suffix = Path(clean(payload.get("audio_name", "")) or "audio.webm").suffix or ".webm"
    model_name = clean(payload.get("model_name", "small")) or "small"
    language = clean(payload.get("language", "en")) or "en"
    expected = str(payload.get("expected", "") or "")
    with tempfile.NamedTemporaryFile(prefix="future-worker-stt-", suffix=suffix, delete=False) as handle:
        handle.write(audio_bytes)
        audio_path = handle.name
    try:
        model_ref = str(future.resolve_model_path(model_name) or "").strip() if callable(getattr(future, "resolve_model_path", None)) else model_name
        cache = getattr(future, "MODEL_CACHE", {}) if isinstance(getattr(future, "MODEL_CACHE", {}), dict) else {}
        cached_ready = bool(cache.get("obj") is not None and str(cache.get("model_ref", "") or "") == model_ref)
        if not cached_ready:
            preload = getattr(future, "preload_model_sync", None)
            if not callable(preload):
                raise RuntimeError("Worker STT preload function is unavailable.")
            if not preload(model_name, language):
                raise RuntimeError(f"Worker could not preload Whisper model: {model_ref}")
        result = future.transcribe_audio(audio_path, model_name, language)
        text = clean(result.get("text", ""))
        timeline = result.get("timeline_words") if isinstance(result.get("timeline_words"), list) else []
        response = {
            "text": text,
            "segments": result.get("segments") or [],
            "timeline_words": timeline,
            "model": result.get("model") or model_name,
            "model_ref": result.get("model_ref", ""),
            "language": result.get("language") or language,
            "source": "local Faster-Whisper",
            "cached_ready": cached_ready,
        }
        if expected:
            # Added 2026-07-07: remote STT must return the transcript even if optional spaCy scoring times out.
            try:
                scoring = future.score_spoken(expected, text, timeline)
                if isinstance(scoring, dict):
                    response.update(scoring)
                if int(response.get("total", 0) or 0) <= 0 or not isinstance(response.get("details"), list):
                    raise RuntimeError("Worker STT scoring returned no word-level results.")
            except Exception as exc:
                raise RuntimeError(f"Worker STT scoring failed: {clean(exc) or exc}") from exc
        return response
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


def gemini_job(payload: dict, server: str, base_payload: dict) -> dict:
    from future_ipv4_http import ipv4_https_request_bytes

    warm_worker_runtime("gemini")
    model = clean(payload.get("model", "gemini-1.5-flash")) or "gemini-1.5-flash"
    body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
    if not body:
        body_json = str(payload.get("body_json", "") or "")
        if body_json:
            body = json.loads(body_json)
    if not isinstance(body, dict) or not body:
        raise RuntimeError("Missing Gemini request body.")
    key_payload = http_json(server, "/distributed-worker/gemini-key", base_payload, timeout=20)
    api_key = clean(key_payload.get("api_key", ""))
    if not api_key:
        raise RuntimeError("Server did not return a Gemini key.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent"
    timeout = max(5.0, min(30.0, float(payload.get("timeout_seconds", 20) or 20)))
    try:
        raw, timing = ipv4_https_request_bytes(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json", "x-goog-api-key": api_key, "User-Agent": HTTP_USER_AGENT},
            method="POST",
            timeout=timeout,
        )
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            detail = ""
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail or exc.reason or 'Forbidden'}") from exc
    data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    if not isinstance(data, dict):
        raise RuntimeError("Invalid Gemini response.")
    data["_future_gemini"] = {**timing, "attempt_id": "worker-ipv4-1"}
    return {"model": model, "response": data, "timing": timing}


def phonemize_job(payload: dict) -> dict:
    warm_worker_runtime("phonemize")
    old_bridge_disabled = os.environ.get("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", "")
    os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = "1"
    try:
        import future_lesson_builder_gui as builder  # type: ignore

        text = clean(payload.get("text", ""))
        voice = clean(payload.get("voice", "en-US")) or "en-US"
        if not text:
            raise RuntimeError("Empty phonemize text.")
        return {"ipa": builder.phonemize_text(text, voice), "voice": voice}
    finally:
        if old_bridge_disabled:
            os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = old_bridge_disabled
        else:
            os.environ.pop("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", None)


def run_job(kind: str, payload: dict, server: str = "", base_payload: dict | None = None) -> dict:
    if kind == "translate":
        return translate_job(payload)
    if kind == "tts":
        return tts_job(payload)
    if kind == "stt":
        return stt_job(payload)
    if kind == "gemini":
        return gemini_job(payload, server, base_payload or {})
    if kind == "phonemize":
        return phonemize_job(payload)
    raise RuntimeError(f"Unsupported job kind: {kind}")


def run_claimed_job_thread(kind: str, lane_name: str, job: dict, args, base_payload: dict) -> None:
    job_id = clean(job.get("job_id", ""))
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    print(f"{worker_job_source_label(kind, payload)} | {lane_name} | {job_id} | started", flush=True)
    started = time.time()
    try:
        result = run_job(kind, payload, args.server, base_payload)
        result_timeout = None if clean(kind).lower() == "tts" else 60
        result_attempts = 6 if clean(kind).lower() == "tts" else 2
        http_json_retry(args.server, "/distributed-worker/result", {**base_payload, "job_id": job_id, "ok": True, "result": result, "active_jobs": active_jobs_snapshot()}, timeout=result_timeout, attempts=result_attempts, delay=1.5)
        print(f"{worker_job_source_label(kind, payload, result)} | {lane_name} | {job_id} | done in {int((time.time() - started) * 1000)}ms", flush=True)
    except Exception as exc:
        error = f"{exc}\n{traceback.format_exc()}"
        try:
            http_json_retry(args.server, "/distributed-worker/result", {**base_payload, "job_id": job_id, "ok": False, "error": error, "active_jobs": active_jobs_snapshot()}, timeout=30, attempts=3, delay=1.0)
        except Exception as post_exc:
            print(f"job {job_id} failed and error POST failed: {post_exc}", flush=True)
        report_worker_log(args.server, base_payload, f"job {job_id} {kind} failed", kind=kind, job_id=job_id, error=error)
        print(f"{worker_job_source_label(kind, payload)} | {lane_name} | {job_id} | failed: {exc}", flush=True)
    finally:
        mark_active_job(kind, job_id, False)


def worker_dispatch_loop(capabilities: list[str], max_jobs_by_kind: dict[str, int], args, base_payload: dict) -> None:
    # Added 2026-07-07: one representative long-polls Server 2 and redistributes jobs to local slots.
    lane_name = "dispatcher"
    active_until = 0.0
    no_job_since = time.time()
    idle_poll_seconds = max(0.5, min(5.0, float(args.poll_seconds or 1.0)))
    active_poll_seconds = max(0.1, min(0.5, idle_poll_seconds / 3.0))
    while True:
        try:
            if not worker_has_free_slot(max_jobs_by_kind, capabilities):
                time.sleep(0.05)
                continue
            now = time.time()
            fast_mode = now < active_until and (now - no_job_since) < 3.0
            wait_seconds = active_poll_seconds if fast_mode else idle_poll_seconds
            poll_payload = {
                **base_payload,
                "wait_seconds": wait_seconds,
                "claim_limit": worker_free_slot_count(max_jobs_by_kind, capabilities),
                "lane": "",
                "lane_id": lane_name,
                "active_jobs": active_jobs_snapshot(),
            }
            response = http_json(args.server, "/distributed-worker/poll", poll_payload, timeout=wait_seconds + 15)
            jobs = response.get("jobs") if isinstance(response.get("jobs"), list) else []
            if not jobs and isinstance(response.get("job"), dict):
                jobs = [response.get("job")]
            if not jobs:
                if time.time() >= active_until:
                    no_job_since = time.time()
                continue
            started_any = False
            active_until = time.time() + 3.0
            no_job_since = time.time()
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                job_id = clean(job.get("job_id", ""))
                kind = clean(job.get("kind", "")).lower()
                if kind not in capabilities:
                    continue
                mark_active_job(kind, job_id, True)
                job_lane_name = f"{kind}-{active_job_count(kind)}"
                thread = threading.Thread(
                    target=run_claimed_job_thread,
                    args=(kind, job_lane_name, job, args, base_payload),
                    name=f"future-worker-job-{kind}-{job_id[:8] or uuid.uuid4().hex[:8]}",
                    daemon=True,
                )
                thread.start()
                started_any = True
            if not started_any:
                time.sleep(0.05)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"{lane_name} connection issue: {exc}", flush=True)
            time.sleep(3)
        except RuntimeError as exc:
            migrate_to = clean(getattr(exc, "migrate_to", ""))
            if migrate_to:
                args.server = migrate_to.rstrip("/")
                print(f"Switching worker polling to LAN broker {args.server}", flush=True)
                active_until = 0.0
                no_job_since = time.time()
                continue
            report_worker_log(args.server, base_payload, f"{lane_name} worker loop error", error=str(exc))
            time.sleep(3)
        except Exception as exc:
            error = f"{exc}\n{traceback.format_exc()}"
            report_worker_log(args.server, base_payload, f"{lane_name} worker loop error", error=error)
            print(f"{lane_name} worker loop error: {exc}", flush=True)
            time.sleep(3)


def main() -> int:
    parser = argparse.ArgumentParser(description="Future distributed worker client")
    parser.add_argument("--server", default=os.environ.get("FUTURE_SERVER_URL", "") or DEFAULT_SERVER_URL, help="Future Server 2 URL, for example https://name.trycloudflare.com")
    parser.add_argument("--token", default=os.environ.get("WORKER_TOKEN", "") or DEFAULT_WORKER_TOKEN, help="Worker token from dashboard")
    parser.add_argument("--name", default=os.environ.get("COMPUTERNAME") or socket.gethostname() or "future-worker")
    parser.add_argument("--worker-id", default=os.environ.get("FUTURE_WORKER_ID", ""), help="Stable worker id saved by the portable installer")
    parser.add_argument("--owner-user", default=os.environ.get("FUTURE_WORKER_OWNER", ""), help="Future username to prefer this machine for that user's jobs")
    parser.add_argument("--capabilities", default=os.environ.get("FUTURE_WORKER_CAPABILITIES", "translate,tts,stt,gemini,phonemize"))
    parser.add_argument("--max-jobs", default=os.environ.get("FUTURE_WORKER_MAX_JOBS", DEFAULT_MAX_JOBS), help="Per-kind capacity, for example translate=1,tts=4,stt=1,gemini=1")
    parser.add_argument("--app-root", default=os.environ.get("FUTURE_APP_ROOT", ""))
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    args.server = clean(args.server)
    if not args.server:
        raise SystemExit("Missing --server")
    token = clean(args.token)
    if not token:
        raise SystemExit("Missing --token")
    configure_import_roots(args.app_root)
    # Added 2026-07-07: portable workers keep a stable dashboard identity across Windows restarts.
    worker_id = clean(args.worker_id) or uuid.uuid4().hex[:16]
    capabilities = clean_capabilities(args.capabilities)
    max_jobs_by_kind = parse_max_jobs_by_kind(args.max_jobs, capabilities)
    features = worker_runtime_features(capabilities)
    with WORKER_FEATURES_LOCK:
        WORKER_RUNTIME_FEATURES.clear()
        WORKER_RUNTIME_FEATURES.update(features)
        features = WORKER_RUNTIME_FEATURES
    base_payload = {
        "token": token,
        "worker_id": worker_id,
        "name": args.name,
        "machine_id": worker_machine_id(args.name),
        "machine_name": clean(socket.gethostname() or os.environ.get("COMPUTERNAME", "") or args.name),
        "owner_user": clean(args.owner_user).lower(),
        "capabilities": capabilities,
        "features": features,
        "max_jobs_by_kind": max_jobs_by_kind,
        "version": CLIENT_VERSION,
    }
    print(f"Future distributed worker {worker_id} connecting to {args.server}", flush=True)
    while True:
        try:
            registered = http_json(args.server, "/distributed-worker/register", base_payload, timeout=20)
            if registered.get("rejected"):
                print(clean(registered.get("error", "worker rejected by server")) or "worker rejected by server", flush=True)
                return 0
            worker_id = clean(registered.get("worker_id", worker_id)) or worker_id
            base_payload["worker_id"] = worker_id
            if "tts" in capabilities:
                if features.get("tts_kokoro_vi"):
                    report_worker_log(args.server, base_payload, "Kokoro Vietnamese ready.", kind="tts")
                else:
                    report_worker_log(
                        args.server,
                        base_payload,
                        "Kokoro Vietnamese missing on this worker.",
                        kind="tts",
                        error=clean(features.get("kokoro_vi_error", "")) or "unknown Kokoro Vietnamese runtime error",
                    )
            # Added 2026-07-14: startup warm is opt-in because auto-importing heavy native runtimes can crash onefile workers on some machines.
            startup_warm = clean(os.environ.get("FUTURE_WORKER_STARTUP_WARM", "")).lower() in {"1", "true", "yes", "on"}
            if startup_warm:
                if "phonemize" in capabilities:
                    report_worker_log(args.server, base_payload, "Phonemize and spaCy warm will stay cached in RAM after startup.", kind="phonemize")
                warm_worker_runtime_background(capabilities, args.server, base_payload)
            break
        except Exception as exc:
            print(f"register failed: {exc}", flush=True)
            time.sleep(5)
    threads: list[threading.Thread] = []
    if worker_has_free_slot(max_jobs_by_kind, capabilities):
        thread = threading.Thread(target=worker_dispatch_loop, args=(capabilities, max_jobs_by_kind, args, base_payload), name="future-worker-dispatcher", daemon=True)
        thread.start()
        threads.append(thread)
    if not threads:
        raise SystemExit("No worker lanes enabled.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("worker stopped", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
