from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path


WRITE_HTML_DIR = Path(__file__).resolve().parents[2]
if str(WRITE_HTML_DIR) not in sys.path:
    sys.path.insert(0, str(WRITE_HTML_DIR))
from future_sound_asset_index import write_server_sound_asset as indexed_write_server_sound_asset

PROGRAME_ROOT = WRITE_HTML_DIR.parent
SERVER_DATA_ROOT = Path(r"C:\server data")
SERVER_SOUND_DIR = SERVER_DATA_ROOT / "Sound"
CACHE_ROOT = Path(r"C:\programe\programe_cache\future_lesson_builder")
TTS_CACHE_DIR = CACHE_ROOT / "tts"
LOCAL_TTS_OUTPUT_DIR = CACHE_ROOT / "local_tts_outputs"
KOKORO_VI_MODEL_ROOT = Path(r"C:\QMLearn\models\kokoro_vietnamese")
KOKORO_VI_VOICEPACK_DIR = KOKORO_VI_MODEL_ROOT / "voicepacks"
KOKORO_VI_ONNX_PATH = KOKORO_VI_MODEL_ROOT / "kokoro_vi.onnx"
KOKORO_VI_CONFIG_PATH = KOKORO_VI_MODEL_ROOT / "config.json"
KOKORO_VI_DEFAULT_VOICEPACK = KOKORO_VI_MODEL_ROOT / "kokoro_vi_voicepack.pt"
KOKORO_VI_FALLBACK_VOICES = [
    ("Kokoro VI | Diem Trinh", "kokoro_vi:diem_trinh"),
    ("Kokoro VI | Mai Loan", "kokoro_vi:mai_loan"),
    ("Kokoro VI | My Yen", "kokoro_vi:my_yen"),
    ("Kokoro VI | Ngoc Huyen", "kokoro_vi:ngoc_huyen"),
]

for _import_root in (PROGRAME_ROOT, WRITE_HTML_DIR):
    _import_text = str(_import_root)
    if _import_root.exists() and _import_text not in sys.path:
        sys.path.insert(0, _import_text)

_TTS_SYNTH_LOCK = threading.RLock()
_TTS_SYNTH_LOCKS: dict[str, threading.Lock] = {}
_KOKORO_RUNTIME = None
_KOKORO_VI_ONNX_RUNTIME_LOCK = threading.RLock()
_KOKORO_VI_ONNX_RUNTIMES: dict[str, object] = {}
_KOKORO_VI_ONNX_RUNTIME_LOAD_LOCKS: dict[str, threading.Lock] = {}


def clean_text(value: object = "") -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\x00", " ")).strip()


def clean_kokoro_tts_text(value: object = "") -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[\r\n\u2028\u2029]+", " ", text)
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", text)
    return clean_text(text)


# Added 2026-07-14: worker exe must use clean external Python for Kokoro VI ONNX to avoid bundled DLL collisions.
def kokoro_vi_subprocess_only() -> bool:
    raw = clean_text(os.environ.get("FUTURE_KOKORO_VI_SUBPROCESS_ONLY", "1"))
    return raw.lower() not in {"0", "false", "no", "off"}


# Added 2026-07-14: runs Kokoro English outside the worker process so native ONNX crashes cannot kill the dashboard.
def kokoro_en_subprocess_only() -> bool:
    raw = clean_text(os.environ.get("FUTURE_KOKORO_EN_SUBPROCESS_ONLY", "1"))
    return raw.lower() not in {"0", "false", "no", "off"}


def ensure_cache_dirs() -> None:
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_SOUND_DIR.mkdir(parents=True, exist_ok=True)


def voice_cache_key(text: str, voice_key: str) -> str:
    raw = json.dumps({"text": clean_text(text), "voice": clean_text(voice_key)}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def normalize_sound_of_text_voice_key(voice_key: str) -> str:
    key = clean_text(voice_key).lower()
    if key in {"female-uk", "uk", "en-gb", "sot:en-gb", "soundoftext:en-gb"}:
        return "en-GB"
    if key in {"female-us", "male-us", "us", "en-us", "sot:en-us", "soundoftext:en-us"}:
        return "en-US"
    if key.startswith("sot:"):
        return clean_text(voice_key).split(":", 1)[1] or "en-US"
    return ""


def normalize_audio_voice_key(voice_key: str) -> str:
    key = clean_text(voice_key)
    lowered = key.lower()
    if lowered.startswith(("kokoro-vietnamese:", "kokoro_vietnamese:", "kokoro-vi:")):
        suffix = clean_text(key.split(":", 1)[1] if ":" in key else "")
        return f"kokoro_vi:{suffix}" if suffix else "kokoro_vi:diem_trinh"
    if lowered.startswith(("microsoft:", "msedge:")):
        suffix = clean_text(key.split(":", 1)[1] if ":" in key else "")
        return f"microsoft:{suffix}" if suffix else key
    if lowered == "male-us":
        return "edge:en-US-GuyNeural"
    sot = normalize_sound_of_text_voice_key(key)
    if sot and lowered in {"female-uk", "female-us", "sot:en-gb", "sot:en-us", "uk", "us", "en-gb", "en-us"}:
        return f"sot:{sot}"
    return key


def _kokoro_vietnamese_voice_label(name: str) -> str:
    label = clean_text(name).replace("_", " ").replace("-", " ").title()
    return f"Kokoro VI | {label or 'Voice'}"


def _kokoro_voice_label(name: str) -> str:
    return f"Kokoro | {clean_text(name) or 'Voice'}"


def embedded_voice_label(voice_key: str, fallback: str = "") -> str:
    key = normalize_audio_voice_key(voice_key)
    lowered = key.lower()
    if lowered.startswith("sot:"):
        voice = normalize_sound_of_text_voice_key(key)
        return "Sound of Text | Female UK" if voice == "en-GB" else ("Sound of Text | Female US" if voice == "en-US" else f"Sound of Text | {voice}")
    if lowered.startswith("edge:"):
        try:
            from module_main.edge_tts_service import edge_voice_option_label

            return edge_voice_option_label(key.split(":", 1)[1])
        except Exception:
            return f"Edge | {key.split(':', 1)[1]}"
    if lowered.startswith("microsoft:"):
        return f"Microsoft | {key.split(':', 1)[1]}"
    if lowered.startswith("kokoro_vi:"):
        return _kokoro_vietnamese_voice_label(key.split(":", 1)[1])
    if lowered.startswith("kokoro:"):
        return _kokoro_voice_label(key.split(":", 1)[1])
    return clean_text(fallback) or key or "Embedded voice"


def audio_mime_for_voice(voice_key: str) -> tuple[str, str]:
    lowered = normalize_audio_voice_key(voice_key).lower()
    if lowered.startswith(("kokoro:", "kokoro_vi:", "sapi:")):
        return "audio/wav", "wav"
    return "audio/mpeg", "mp3"


def write_server_sound_asset(prefix: str, audio_bytes: bytes, mime: str) -> str:
    # Added 2026-07-16: use the shared Sound JSON/WAL index so worker-created audio also lands in sharded buckets.
    ensure_cache_dirs()
    return indexed_write_server_sound_asset(prefix, bytes(audio_bytes or b""), mime)


def kokoro_vietnamese_voice_specs() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    voices_path = KOKORO_VI_MODEL_ROOT / "voices.json"
    if voices_path.is_file():
        try:
            data = json.loads(voices_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for name, info in data.items():
                    voice_name = clean_text(name)
                    label = clean_text(info.get("label", "")) if isinstance(info, dict) else ""
                    if voice_name:
                        rows.append((label or _kokoro_vietnamese_voice_label(voice_name), f"kokoro_vi:{voice_name}"))
        except Exception:
            rows = []
    return rows or list(KOKORO_VI_FALLBACK_VOICES)


def ensure_kokoro_vietnamese_model_files(download: bool = True, log=None) -> dict:
    KOKORO_VI_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    KOKORO_VI_VOICEPACK_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "root": str(KOKORO_VI_MODEL_ROOT),
        "onnx": KOKORO_VI_ONNX_PATH.is_file() and KOKORO_VI_ONNX_PATH.stat().st_size > 44,
        "config": KOKORO_VI_CONFIG_PATH.is_file() and KOKORO_VI_CONFIG_PATH.stat().st_size > 10,
        "default_voicepack": KOKORO_VI_DEFAULT_VOICEPACK.is_file() and KOKORO_VI_DEFAULT_VOICEPACK.stat().st_size > 44,
        "downloaded": [],
        "missing": [],
    }
    if all(bool(state[key]) for key in ("onnx", "config", "default_voicepack")) or not download:
        return state
    try:
        from kokoro_vietnamese.core import DEFAULT_HF_REPO_ID, _download_or_resolve  # type: ignore

        for remote_name, target in (
            ("kokoro_vi.onnx", KOKORO_VI_ONNX_PATH),
            ("config.json", KOKORO_VI_CONFIG_PATH),
            ("kokoro_vi_voicepack.pt", KOKORO_VI_DEFAULT_VOICEPACK),
        ):
            if target.is_file() and target.stat().st_size > 44:
                continue
            source = Path(_download_or_resolve(DEFAULT_HF_REPO_ID, remote_name, None))
            if source.is_file():
                target.write_bytes(source.read_bytes())
                state["downloaded"].append(str(target))
    except Exception as exc:
        state["error"] = clean_text(exc)
    state["onnx"] = KOKORO_VI_ONNX_PATH.is_file() and KOKORO_VI_ONNX_PATH.stat().st_size > 44
    state["config"] = KOKORO_VI_CONFIG_PATH.is_file() and KOKORO_VI_CONFIG_PATH.stat().st_size > 10
    state["default_voicepack"] = KOKORO_VI_DEFAULT_VOICEPACK.is_file() and KOKORO_VI_DEFAULT_VOICEPACK.stat().st_size > 44
    state["missing"] = [key for key in ("onnx", "config", "default_voicepack") if not state.get(key)]
    return state


def _external_python_env() -> dict:
    env = dict(os.environ)
    bad_markers = ("\\_internal", "\\pyqt5\\qt5\\bin")
    env["PATH"] = os.pathsep.join(part for part in env.get("PATH", "").split(os.pathsep) if not any(marker in part.lower() for marker in bad_markers))
    env.pop("QT_PLUGIN_PATH", None)
    env.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    env.pop("QT_QPA_PLATFORM", None)
    return env


def _kokoro_vi_python_command() -> list[str]:
    candidates: list[list[str]] = []
    env_python = clean_text(os.environ.get("FUTURE_KOKORO_VI_PYTHON", ""))
    if env_python:
        candidates.append([env_python])
    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable])
    candidates.extend([["python"], ["py", "-3"]])
    for candidate in candidates:
        try:
            probe = subprocess.run(
                [*candidate, "-c", "import kokoro_vietnamese.onnx_cli, onnxruntime, soundfile; print('ok')"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
                check=False,
                env=_external_python_env(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if probe.returncode == 0 and "ok" in str(probe.stdout or ""):
                return candidate
        except Exception:
            continue
    return []


def synthesize_kokoro_vietnamese_audio_bytes(text: str, voice_key: str, output_path: Path, log=None) -> bytes:
    clean_sentence = clean_text(text)
    if not clean_sentence:
        raise RuntimeError("Missing text for Kokoro Vietnamese voice.")
    key = normalize_audio_voice_key(voice_key)
    voice_name = clean_text(key.split(":", 1)[1] if ":" in key else "") or "diem_trinh"
    voicepack = KOKORO_VI_VOICEPACK_DIR / f"{voice_name}.pt"
    if not voicepack.is_file():
        voicepack = KOKORO_VI_DEFAULT_VOICEPACK
    missing = [str(path) for path in (KOKORO_VI_ONNX_PATH, KOKORO_VI_CONFIG_PATH, voicepack) if not path.is_file()]
    if missing:
        raise RuntimeError("Kokoro Vietnamese model file missing: " + "; ".join(missing))
    if callable(log):
        log(f"Kokoro Vietnamese ONNX: {voice_name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def device_candidates() -> list[str]:
        requested = clean_text(os.environ.get("FUTURE_KOKORO_VI_DEVICE", "")).lower() or "cpu"
        if requested in {"cuda", "gpu"}:
            return ["cuda", "cpu"]
        return ["cpu"]

    def run_subprocess(run_voicepack: Path, device: str = "cpu") -> bytes:
        python_cmd = _kokoro_vi_python_command()
        if not python_cmd:
            raise RuntimeError("Kokoro Vietnamese needs a real Python runtime with kokoro_vietnamese, onnxruntime, and soundfile.")
        try:
            output_path.unlink()
        except OSError:
            pass
        command = [
            *python_cmd,
            "-m",
            "kokoro_vietnamese.onnx_cli",
            "--text",
            clean_sentence,
            "--output",
            str(output_path),
            "--device",
            device,
            "--onnx",
            str(KOKORO_VI_ONNX_PATH),
            "--voicepack",
            str(run_voicepack),
            "--config",
            str(KOKORO_VI_CONFIG_PATH),
        ]
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(WRITE_HTML_DIR), timeout=None, check=False, env=_external_python_env(), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stderr_text = completed.stderr.decode("utf-8", errors="ignore").strip() if isinstance(completed.stderr, (bytes, bytearray)) else str(completed.stderr or "").strip()
        stdout_text = completed.stdout.decode("utf-8", errors="ignore").strip() if isinstance(completed.stdout, (bytes, bytearray)) else str(completed.stdout or "").strip()
        if completed.returncode != 0:
            raise RuntimeError(stderr_text or stdout_text or f"Kokoro Vietnamese exited with {completed.returncode}.")
        if output_path.is_file() and output_path.stat().st_size > 44:
            return output_path.read_bytes()
        raise RuntimeError(f"Kokoro Vietnamese did not create audio. voice={voice_name}; stdout={stdout_text[:300]}; stderr={stderr_text[:300]}")

    def run_in_process(run_voicepack: Path, device: str = "cpu") -> bytes:
        from kokoro_vietnamese.core import SAMPLE_RATE  # type: ignore
        from kokoro_vietnamese.onnx_cli import KokoroVietnameseONNX  # type: ignore
        import soundfile as sf  # type: ignore

        runtime_key = "|".join(str(item) for item in (KOKORO_VI_ONNX_PATH, KOKORO_VI_CONFIG_PATH, run_voicepack, device))
        with _KOKORO_VI_ONNX_RUNTIME_LOCK:
            runtime = _KOKORO_VI_ONNX_RUNTIMES.get(runtime_key)
            load_lock = _KOKORO_VI_ONNX_RUNTIME_LOAD_LOCKS.setdefault(runtime_key, threading.Lock())
        if runtime is None:
            with load_lock:
                runtime = _KOKORO_VI_ONNX_RUNTIMES.get(runtime_key)
                if runtime is None:
                    runtime = KokoroVietnameseONNX(voice=None, onnx_path=KOKORO_VI_ONNX_PATH, voicepack_path=run_voicepack, config_path=KOKORO_VI_CONFIG_PATH, device=device)
                    with _KOKORO_VI_ONNX_RUNTIME_LOCK:
                        _KOKORO_VI_ONNX_RUNTIMES[runtime_key] = runtime
        audio, _phonemes = runtime.synthesize(clean_sentence)
        if len(audio) == 0:
            raise RuntimeError("Kokoro Vietnamese did not create audio.")
        sf.write(output_path, audio, SAMPLE_RATE)
        return output_path.read_bytes()

    subprocess_only = kokoro_vi_subprocess_only()
    prefer_in_process = (not subprocess_only) and clean_text(os.environ.get("FUTURE_KOKORO_VI_IN_PROCESS", "")).lower() in {"1", "true", "yes", "on", "warm"}
    fallback_default = "0" if (subprocess_only or getattr(sys, "frozen", False)) else "1"
    allow_in_process_fallback = (not subprocess_only) and clean_text(os.environ.get("FUTURE_KOKORO_VI_IN_PROCESS_FALLBACK", fallback_default)).lower() not in {"0", "false", "no", "off"}
    last_exc: Exception | None = None
    for device in device_candidates():
        try:
            return run_in_process(voicepack, device=device) if prefer_in_process else run_subprocess(voicepack, device=device)
        except Exception as exc:
            last_exc = exc
            if prefer_in_process:
                try:
                    return run_subprocess(voicepack, device=device)
                except Exception as sub_exc:
                    last_exc = sub_exc
            elif allow_in_process_fallback:
                try:
                    return run_in_process(voicepack, device=device)
                except Exception as in_exc:
                    last_exc = in_exc
    raise RuntimeError(str(last_exc or "Kokoro Vietnamese failed."))


def get_kokoro_runtime():
    global _KOKORO_RUNTIME
    if _KOKORO_RUNTIME is None:
        from module_main.tts_kokoro_local import KokoroLocalTTS

        _KOKORO_RUNTIME = KokoroLocalTTS()
        _KOKORO_RUNTIME.prefer_subprocess = True
    return _KOKORO_RUNTIME


# Added 2026-07-14: Kokoro EN helper subprocess path avoids frozen worker DLL collisions and hard exits.
def synthesize_kokoro_english_audio_bytes(text: str, voice_name: str, output_path: Path, log=None) -> bytes:
    safe_text = clean_kokoro_tts_text(text)
    safe_voice = clean_text(voice_name) or "am_adam"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if callable(log):
            log(f"TTS | local Kokoro EN helper | {safe_voice}")
        result_path, _voice_name = get_kokoro_runtime().synthesize_to_file(
            safe_text,
            safe_voice,
            str(output_path),
            speed=1.0,
            allow_subprocess=True,
        )
        audio_bytes = Path(result_path).read_bytes()
        if audio_bytes:
            return audio_bytes
    except Exception as helper_exc:
        # Added 2026-07-14: frozen workers may not carry the helper EXE; fall back to real Python instead of importing ONNX in-process.
        if callable(log):
            log(f"TTS | local Kokoro EN helper unavailable, using Python subprocess | {clean_text(helper_exc)[:180]}")
    model_root = Path(os.environ.get("FUTURE_KOKORO_EN_MODEL_ROOT", r"C:\QMLearn\models\kokoro_onnx"))
    model_path = Path(os.environ.get("FUTURE_KOKORO_EN_MODEL_PATH", str(model_root / "kokoro-v1.0.onnx")))
    voices_path = Path(os.environ.get("FUTURE_KOKORO_EN_VOICES_PATH", str(model_root / "voices-v1.0.bin")))
    missing = [str(path) for path in (model_path, voices_path) if not path.is_file()]
    if missing:
        raise RuntimeError("Kokoro EN missing model files: " + "; ".join(missing))
    payload = {
        "action": "synthesize",
        "model_path": str(model_path),
        "voices_path": str(voices_path),
        "text": safe_text,
        "voice_name": safe_voice,
        "output_path": str(output_path),
        "speed": 1.0,
    }
    candidates: list[list[str]] = []
    env_python = clean_text(os.environ.get("FUTURE_KOKORO_EN_PYTHON", "") or os.environ.get("FUTURE_KOKORO_VI_PYTHON", ""))
    if env_python:
        candidates.append([env_python])
    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable])
    candidates.extend([["py", "-3.11"], ["py", "-3"], ["python"]])
    env = os.environ.copy()
    env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    current_pythonpath = env.get("PYTHONPATH", "")
    roots = [str(PROGRAME_ROOT), str(WRITE_HTML_DIR)]
    env["PYTHONPATH"] = os.pathsep.join([*roots, current_pythonpath]) if current_pythonpath else os.pathsep.join(roots)
    timeout_raw = clean_text(os.environ.get("FUTURE_KOKORO_EN_TIMEOUT", "0"))
    try:
        timeout_value = float(timeout_raw)
    except Exception:
        timeout_value = 0.0
    timeout_arg = None if timeout_value <= 0 else max(30.0, timeout_value)
    startupinfo = None
    if os.name == "nt":
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        except Exception:
            startupinfo = None
    last_error = ""
    for candidate in candidates:
        try:
            command = [*candidate, "-m", "module_main.kokoro_tts_worker"]
            if callable(log):
                log(f"TTS | local Kokoro EN subprocess | {' '.join(candidate)} | {safe_voice}")
            completed = subprocess.run(
                command,
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(PROGRAME_ROOT),
                env=env,
                timeout=timeout_arg,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                startupinfo=startupinfo,
            )
            stdout_text = completed.stdout.decode("utf-8", errors="ignore").strip()
            stderr_text = completed.stderr.decode("utf-8", errors="ignore").strip()
            raw_line = ""
            for line in reversed(stdout_text.splitlines()):
                if str(line or "").strip():
                    raw_line = str(line or "").strip()
                    break
            data = {}
            if raw_line:
                try:
                    data = json.loads(raw_line)
                except Exception:
                    data = {}
            if completed.returncode == 0 and bool(data.get("ok", False)) and output_path.is_file():
                audio_bytes = output_path.read_bytes()
                if audio_bytes:
                    return audio_bytes
            detail = clean_text(str(data.get("error", "") if isinstance(data, dict) else "") or stderr_text or stdout_text or f"exit={completed.returncode}")
            last_error = f"{' '.join(candidate)} failed: {detail[-900:]}"
        except Exception as exc:
            last_error = f"{' '.join(candidate)} failed: {exc}"
    raise RuntimeError(last_error or "Kokoro EN subprocess failed.")


def synthesize_embedded_audio(text: str, voice_key: str, log=None) -> tuple[bytes, str]:
    ensure_cache_dirs()
    key = normalize_audio_voice_key(voice_key)
    mime, extension = audio_mime_for_voice(key)
    cache_path = TTS_CACHE_DIR / f"{voice_cache_key(text, key)}.{extension}"
    if cache_path.is_file():
        if callable(log):
            log(f"Audio cache: {embedded_voice_label(key)}")
        return cache_path.read_bytes(), mime
    cache_lock_key = str(cache_path)
    with _TTS_SYNTH_LOCK:
        cache_lock = _TTS_SYNTH_LOCKS.setdefault(cache_lock_key, threading.Lock())
    with cache_lock:
        if cache_path.is_file():
            return cache_path.read_bytes(), mime
        lowered = key.lower()
        if callable(log):
            log(f"TTS | local/headless | {embedded_voice_label(key)}")
        if lowered.startswith("sot:"):
            from module_main.Soundoftext_Api import Soundoftext_Api

            voice = normalize_sound_of_text_voice_key(key) or "en-US"
            audio_bytes = Soundoftext_Api().load_mp3_bytes(text, voice=voice)
            if not audio_bytes:
                raise RuntimeError(f"Sound of Text khong tao duoc audio cho {voice}.")
        elif lowered.startswith("edge:"):
            from module_main.edge_tts_service import synthesize_edge_tts_bytes

            audio_bytes = synthesize_edge_tts_bytes(text, key, speed_percent=92)
        elif lowered.startswith("microsoft:"):
            from module_main.edge_tts_service import synthesize_edge_tts_bytes

            short_name = key.split(":", 1)[1]
            audio_bytes = synthesize_edge_tts_bytes(text, f"edge:{short_name}", speed_percent=92)
        elif lowered.startswith("kokoro_vi:"):
            voice_name = key.split(":", 1)[1]
            safe_voice = re.sub(r"[^0-9A-Za-z._-]+", "-", voice_name).strip("-") or "voice"
            output_path = LOCAL_TTS_OUTPUT_DIR / f"kokoro_vi_{safe_voice}_{voice_cache_key(text, key)}.wav"
            try:
                audio_bytes = synthesize_kokoro_vietnamese_audio_bytes(text, key, output_path, log)
            except Exception as exc:
                raise RuntimeError(f"Kokoro Vietnamese voice {voice_name} failed. Detail: {exc}") from exc
        elif lowered.startswith("kokoro:"):
            voice_name = key.split(":", 1)[1]
            safe_voice = re.sub(r"[^0-9A-Za-z._-]+", "-", voice_name).strip("-") or "voice"
            kokoro_text = clean_kokoro_tts_text(text)
            output_path = LOCAL_TTS_OUTPUT_DIR / f"kokoro_{safe_voice}_{voice_cache_key(kokoro_text, key)}.wav"
            if kokoro_en_subprocess_only():
                audio_bytes = synthesize_kokoro_english_audio_bytes(kokoro_text, voice_name, output_path, log)
            else:
                result_path, _voice_name = get_kokoro_runtime().synthesize_to_file(kokoro_text, voice_name, str(output_path), speed=1.0, allow_subprocess=True)
                audio_bytes = Path(result_path).read_bytes()
        else:
            raise RuntimeError(f"Voice chua ho tro nhung audio: {voice_key}")
        cache_path.write_bytes(bytes(audio_bytes or b""))
        return bytes(audio_bytes or b""), mime


def audio_duration_ms(audio_bytes: bytes, mime: str = "") -> int:
    payload = bytes(audio_bytes or b"")
    if not payload:
        return 0
    try:
        import soundfile as sf  # type: ignore

        info = sf.info(io.BytesIO(payload))
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        if duration > 0:
            return int(round(duration * 1000))
    except Exception:
        pass
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            if frames > 0 and sample_rate > 0:
                return int(round((frames / float(sample_rate)) * 1000))
    except Exception:
        pass
    return 0


def analyze_sentence(text: str) -> list[dict]:
    return []


def sentence_spans(text: str, analyzed: list[dict], voice: str) -> list[dict]:
    spans = []
    for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        surface = match.group(0)
        spans.append({"t": surface, "s": int(match.start()), "e": int(match.end()), "i": "", "iu": "", "ik": "", "l": surface.lower(), "p": "", "d": "", "m": ""})
    return spans


def estimate_duration_ms(text: str, tokens: list[dict]) -> int:
    token_count = len(tokens) if tokens else len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))
    compact = re.sub(r"\s+", "", clean_text(text))
    estimated = (float(max(1, token_count)) * 420.0) + (float(max(1, len(compact))) * 18.0) + 160.0
    return int(round(max(720.0, min(18000.0, estimated))))


def build_timings(tokens: list[dict], duration_ms: int) -> list[dict]:
    if not tokens:
        return []
    duration = max(int(duration_ms or 0), 720)
    step = float(duration) / max(1, len(tokens))
    rows = []
    for index, token in enumerate(tokens):
        rows.append({"t": clean_text(token.get("t") or token.get("text")), "s": int(round(index * step)), "e": int(round((index + 1) * step))})
    return rows


def build_audio_guided_timings(tokens: list[dict], duration_ms: int, audio_bytes: bytes) -> list[dict]:
    return build_timings(tokens, duration_ms)
