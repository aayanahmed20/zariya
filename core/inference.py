from __future__ import annotations
import os
from pathlib import Path
from typing import Generator, Optional

MODEL_DIR = Path(__file__).parent.parent / "models"
DEFAULT_MODEL = MODEL_DIR / "model.gguf"

SYSTEM_PROMPT = """You are Zariya, an offline AI assistant built for Urdu-speaking and South Asian users.

You are helpful, culturally aware, and fluent in both Urdu (Roman and Nastaliq) and English.
When the user writes in Urdu, respond in Urdu. When they write in English, respond in English.
Match their language style — including mixed Urdu-English if that's what they use.
Keep responses clear, accurate, and reasonably brief.
You run fully offline."""


class InferenceEngine:

    def __init__(self, model_path: Optional[Path] = None):
        self._llm = None
        self._model_path = model_path or DEFAULT_MODEL
        self._loaded = False
        self._error: Optional[str] = None
        self._max_tokens = 512
        self._temperature = 0.7

    def _try_load(self) -> bool:
        if self._loaded:
            return True
        if self._error:
            return False

        if not self._model_path.exists():
            self._error = (
                f"Model not found at `{self._model_path}`.\n\n"
                "**Setup:**\n"
                "1. Download a GGUF model (Mistral 7B, LLaMA 3 8B, etc.)\n"
                "2. Put it in the `models/` folder\n"
                "3. Rename it to `model.gguf`\n\n"
                "Download from: [TheBloke on HuggingFace](https://huggingface.co/TheBloke)"
            )
            return False

        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=str(self._model_path),
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                n_gpu_layers=-1,
                verbose=False,
            )
            self._loaded = True
            return True
        except ImportError:
            self._error = (
                "`llama-cpp-python` not installed.\n\n"
                "Run: `pip install llama-cpp-python`"
            )
            return False
        except Exception as e:
            self._error = f"Failed to load model: {e}"
            return False

    @property
    def is_ready(self) -> bool:
        return self._try_load()

    @property
    def error(self) -> Optional[str]:
        self._try_load()
        return self._error

    def build_prompt(self, messages: list[dict]) -> str:
        prompt = SYSTEM_PROMPT.strip() + "\n\n"
        for msg in messages[-20:]:
            role = msg["role"]
            content = msg["content"].strip()
            if role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Zariya: {content}\n"
        prompt += "Zariya:"
        return prompt

    def chat(self, messages: list[dict]) -> str:
        if not self._try_load():
            return f"Error: {self._error}"

        prompt = self.build_prompt(messages)
        try:
            output = self._llm(
                prompt,
                max_tokens=512,
                stop=["User:", "\nUser", "Human:"],
                temperature=0.7,
                top_p=0.9,
                repeat_penalty=1.1,
                echo=False,
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"Generation error: {e}"

    def stream(self, messages: list[dict]) -> Generator[str, None, None]:
        if not self._try_load():
            yield f"Error: {self._error}"
            return

        prompt = self.build_prompt(messages)
        try:
            for chunk in self._llm(
                prompt,
                max_tokens=512,
                stop=["User:", "\nUser", "Human:"],
                temperature=0.7,
                top_p=0.9,
                repeat_penalty=1.1,
                stream=True,
                echo=False,
            ):
                token = chunk["choices"][0]["text"]
                if token:
                    yield token
        except Exception as e:
            yield f"\nStreaming error: {e}"

    def stream_with_settings(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        if not self._try_load():
            yield f"Error: {self._error}"
            return
        prompt = self.build_prompt(messages)
        try:
            for chunk in self._llm(
                prompt,
                max_tokens=max_tokens,
                stop=["User:", "\nUser", "Human:"],
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.1,
                stream=True,
                echo=False,
            ):
                token = chunk["choices"][0]["text"]
                if token:
                    yield token
        except Exception as e:
            yield f"\nStreaming error: {e}"

    def get_model_info(self) -> dict:
        if not self._try_load():
            return {"status": "error", "error": self._error}
        path = self._model_path
        size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        return {
            "status": "loaded",
            "name": path.stem,
            "path": str(path),
            "size_mb": round(size_mb, 1),
        }


_engine: Optional[InferenceEngine] = None


def get_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine


def chat(messages: list[dict]) -> str:
    return get_engine().chat(messages)


def stream(messages: list[dict]) -> Generator[str, None, None]:
    return get_engine().stream(messages)
