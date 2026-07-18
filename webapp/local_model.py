"""
Local-model inference via Ollama, server-side.

Why Ollama instead of embedding llama-cpp-python directly: llama-cpp-python
needs a working C++ build toolchain to install on many machines, which fails
silently or loudly depending on the platform. Ollama (https://ollama.com) is
a free, single-installer application -- prebuilt for Windows/Mac/Linux, no
compiler, no account, no API key -- that runs open-source models locally and
exposes them over a small local HTTP API. This module just talks to that API.

Setup, once, on the machine that runs this server:
1. Install Ollama from https://ollama.com/download (a normal app installer).
2. Make sure it's running (it starts automatically after install on most
   platforms; otherwise run the `ollama` app / `ollama serve`).
3. That's it. On first request, this module asks Ollama to pull a small
   default model automatically if it isn't already present -- no need to run
   any command yourself.

If Ollama isn't installed or isn't running, this module simply reports
itself as unavailable and app.py falls through to the offline knowledge
engine, so the app is never broken by this being absent.

Override the model with LOCAL_MODEL_NAME in .env (any name from
https://ollama.com/library). Override the Ollama address with OLLAMA_URL if
it's running on a different host/port. Set DISABLE_LOCAL_MODEL=1 to skip
trying to use a local model entirely.
"""
import os
import threading
import time

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("LOCAL_MODEL_NAME", "qwen2.5:1.5b")
_DISABLED = os.environ.get("DISABLE_LOCAL_MODEL", "").lower() in ("1", "true", "yes")

_status = "starting"
_ready = False


def is_available() -> bool:
    return _ready


def load_status() -> str:
    return _status


def _ollama_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _model_present(model: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
        base = model.split(":")[0]
        return any(n == model or n.startswith(base + ":") for n in names)
    except Exception:
        return False


def _pull_model(model: str) -> bool:
    global _status
    try:
        _status = f"downloading '{model}' via Ollama (one-time)"
        with requests.post(
            f"{OLLAMA_URL}/api/pull", json={"name": model}, stream=True, timeout=None
        ) as r:
            r.raise_for_status()
            for _ in r.iter_lines():
                pass  # drain streamed progress; nothing to show server-side
        return True
    except Exception as e:
        _status = f"Failed to pull model '{model}' from Ollama: {e}"
        return False


def _init_in_background():
    global _ready, _status
    if _DISABLED:
        _status = "not configured (DISABLE_LOCAL_MODEL is set)"
        return
    delay = 3
    while True:
        if not _ollama_running():
            _status = ("Ollama isn't running yet -- install it from https://ollama.com/download and start it "
                        "(this will retry automatically once it's up)")
        elif not _model_present(DEFAULT_MODEL):
            if _pull_model(DEFAULT_MODEL):
                _status = "loaded"
                _ready = True
                return
            # pull failed -- _pull_model already set a status message; retry after a delay
        else:
            _status = "loaded"
            _ready = True
            return
        time.sleep(delay)
        delay = min(delay * 2, 60)

threading.Thread(target=_init_in_background, daemon=True).start()


def generate_reply(messages: list[dict], system_prompt: str) -> str | None:
    if not _ready:
        return None
    chat_messages = [{"role": "system", "content": system_prompt}]
    chat_messages += [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": DEFAULT_MODEL, "messages": chat_messages, "stream": False},
            timeout=60,
        )
        res.raise_for_status()
        data = res.json()
        return data.get("message", {}).get("content")
    except Exception:
        return None
