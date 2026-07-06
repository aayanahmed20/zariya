"""
Optional real local-model inference, server-side.

This replaces the earlier browser-based WebGPU approach, which depended on the
visitor's GPU, browser, and an internet-reachable CDN just to *download* the
model into the tab -- three separate points of failure that were never
reliably testable. Running the model on the server instead means it only has
to work once, on the machine that's actually hosting Zariya, using the same
llama.cpp approach the original version of this project was built around.

To enable it:
  1. pip install llama-cpp-python
  2. Download a small instruction-tuned GGUF model (e.g. a quantized Qwen2.5-0.5B
     or Llama-3.2-1B-Instruct GGUF) to server/models/ and set LOCAL_MODEL_PATH
     in .env to its filename.
  3. Restart the server.

If llama-cpp-python isn't installed, or no model file is configured, this
module simply reports itself as unavailable -- app.py falls through to the
offline knowledge engine, so the app is never broken by this being absent.
"""
import os
from pathlib import Path

MODEL_PATH = os.environ.get("LOCAL_MODEL_PATH", "")
MODELS_DIR = Path(__file__).parent / "server" / "models"

_llama = None
_load_error = None


def is_available() -> bool:
    return _llama is not None


def load_status() -> str:
    if _llama is not None:
        return "loaded"
    if _load_error:
        return _load_error
    return "not configured"


def _try_load():
    global _llama, _load_error
    if not MODEL_PATH:
        _load_error = "LOCAL_MODEL_PATH not set in .env"
        return
    model_file = MODELS_DIR / MODEL_PATH
    if not model_file.exists():
        _load_error = f"Model file not found at {model_file}"
        return
    try:
        from llama_cpp import Llama
    except ImportError:
        _load_error = "llama-cpp-python isn't installed (pip install llama-cpp-python)"
        return
    try:
        _llama = Llama(model_path=str(model_file), n_ctx=2048, verbose=False)
    except Exception as e:
        _load_error = f"Failed to load model: {e}"


_try_load()


def generate_reply(messages: list[dict], system_prompt: str) -> str | None:
    if _llama is None:
        return None
    chat_messages = [{"role": "system", "content": system_prompt}]
    chat_messages += [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
    try:
        result = _llama.create_chat_completion(messages=chat_messages, max_tokens=500, temperature=0.7)
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return None
