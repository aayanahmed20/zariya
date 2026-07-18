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
import json
import os
import threading
import time

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("LOCAL_MODEL_NAME", "qwen2.5:1.5b")
_DISABLED = os.environ.get("DISABLE_LOCAL_MODEL", "").lower() in ("1", "true", "yes")

_status = "starting"
_ready = False
_pulling = False
_progress = {"completed": 0, "total": 0}
_wake_event = threading.Event()


def is_available() -> bool:
    return _ready


def load_status() -> str:
    return _status


def load_progress() -> dict:
    """Bytes downloaded so far for the current/most recent pull, if known."""
    return dict(_progress)


def retry_now() -> dict:
    """Wakes the background loop up immediately instead of waiting out the
    current backoff delay. Safe to call any time -- a no-op if a pull is
    already in flight or the model is already loaded."""
    if _ready:
        return {"ok": True, "status": _status}
    if _pulling:
        return {"ok": False, "status": _status}
    _wake_event.set()
    return {"ok": True, "status": "Retrying now..."}


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
    """Streams a model pull from Ollama, actually reading each progress line
    instead of discarding it, so a failure reported mid-stream (bad model
    name, disk full, network drop) is caught instead of being silently
    treated as success. Always re-checks with Ollama's own model list
    afterwards before declaring victory, since a pull can end without an
    exception and still not have produced a usable model.
    """
    global _status, _pulling, _progress
    _pulling = True
    _progress = {"completed": 0, "total": 0}
    try:
        _status = f"Downloading '{model}' via Ollama (one-time, may take a few minutes)..."
        with requests.post(
            f"{OLLAMA_URL}/api/pull", json={"name": model}, stream=True, timeout=None
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except (ValueError, TypeError):
                    continue

                if payload.get("error"):
                    _status = f"Failed to pull model '{model}' from Ollama: {payload['error']}"
                    return False

                total = payload.get("total")
                completed = payload.get("completed")
                if isinstance(total, int):
                    _progress["total"] = total
                if isinstance(completed, int):
                    _progress["completed"] = completed
                status_line = payload.get("status")
                if status_line:
                    if _progress["total"]:
                        pct = round(_progress["completed"] / _progress["total"] * 100)
                        _status = f"{status_line} ({pct}%)"
                    else:
                        _status = status_line

        # A 200 response with no explicit "error" line still isn't proof the
        # model is actually usable -- confirm it shows up in Ollama's own
        # model list before telling the rest of the app it's ready.
        if not _model_present(model):
            _status = (
                f"Ollama finished responding but '{model}' still isn't in its model "
                "list -- the pull may have been interrupted. Will retry."
            )
            return False

        return True
    except Exception as e:
        _status = f"Failed to pull model '{model}' from Ollama: {e}"
        return False
    finally:
        _pulling = False


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
        _wake_event.wait(delay)
        _wake_event.clear()
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
