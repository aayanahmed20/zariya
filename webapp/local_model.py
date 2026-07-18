"""
Optional real local-model inference, server-side.

Zariya is designed to run as a fully standalone app with zero API keys. If no
model file is present in server/models/, this module downloads a small
instruction-tuned GGUF model (Qwen2.5-1.5B-Instruct, ~1GB, a public file with
no account or key required) the first time the server starts, in a background
thread so Flask itself is never blocked waiting on it. Until the download and
load finish, app.py falls through to the offline knowledge engine, so the app
always responds to something -- it just gets noticeably better once the local
model is ready.

To use a different model instead of the default, put a GGUF file in
server/models/ yourself and set LOCAL_MODEL_PATH in .env to its filename --
this module will use that file and will not attempt to download anything.

Set DISABLE_LOCAL_MODEL_DOWNLOAD=1 in .env to turn off auto-download entirely
(e.g. for an offline-only deployment) and stay on the offline knowledge engine.
"""
import os
import threading
from pathlib import Path

import requests

MODELS_DIR = Path(__file__).parent / "server" / "models"

DEFAULT_MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/"
    + DEFAULT_MODEL_FILENAME
)

MODEL_PATH = os.environ.get("LOCAL_MODEL_PATH", "") or DEFAULT_MODEL_FILENAME
_AUTO_DOWNLOAD_DISABLED = os.environ.get("DISABLE_LOCAL_MODEL_DOWNLOAD", "").lower() in ("1", "true", "yes")

_llama = None
_load_error = None
_status = "starting"


def is_available() -> bool:
    return _llama is not None


def load_status() -> str:
    return _status


def generate_reply(messages: list[dict], system_prompt: str) -> str | None:
    if _llama is None:
        return None
    chat_messages = [{"role": "system", "content": system_prompt}]
    chat_messages += [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
    try:
        result = _llama.create_chat_completion(messages=chat_messages, max_tokens=500, temperature=0.7)
        return result["choices"][0]["message"]["content"]
    except Exception:
        return None


def _download_default_model(model_file: Path) -> bool:
    """Stream the default model to a temp file first, then rename it into
    place once complete -- so an interrupted download never leaves behind a
    truncated file that looks valid on the next run."""
    global _load_error, _status
    tmp_file = model_file.with_suffix(model_file.suffix + ".part")
    try:
        _status = "downloading default model (~1GB, one-time)"
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with requests.get(DEFAULT_MODEL_URL, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        tmp_file.rename(model_file)
        return True
    except Exception as e:
        _load_error = f"Auto-download of default model failed: {e}"
        _status = _load_error
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
        return False


def _load_model(model_file: Path):
    global _llama, _load_error, _status
    try:
        from llama_cpp import Llama
    except ImportError:
        _load_error = "llama-cpp-python isn't installed (pip install -r requirements.txt)"
        _status = _load_error
        return
    try:
        _status = "loading model into memory"
        _llama = Llama(model_path=str(model_file), n_ctx=2048, verbose=False)
        _status = "loaded"
    except Exception as e:
        _load_error = f"Failed to load model: {e}"
        _status = _load_error


def _init_in_background():
    global _load_error, _status
    model_file = MODELS_DIR / MODEL_PATH
    if model_file.exists():
        _load_model(model_file)
        return
    if MODEL_PATH != DEFAULT_MODEL_FILENAME:
        _load_error = f"Model file not found at {model_file}"
        _status = _load_error
        return
    if _AUTO_DOWNLOAD_DISABLED:
        _status = "not configured (auto-download disabled)"
        return
    if _download_default_model(model_file):
        _load_model(model_file)


threading.Thread(target=_init_in_background, daemon=True).start()
