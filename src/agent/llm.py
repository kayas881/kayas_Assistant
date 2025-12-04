from __future__ import annotations

from typing import Iterable, Optional

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class LLM:
    def __init__(self, model: str) -> None:
        if not OLLAMA_AVAILABLE:
            raise ImportError("ollama module not installed. Install with: pip install ollama")
        self.model = model

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        res = ollama.chat(model=self.model, messages=messages, options={"temperature": temperature})
        return res["message"]["content"]

    def stream(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> Iterable[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        for part in ollama.chat(model=self.model, messages=messages, options={"temperature": temperature}, stream=True):
            yield part.get("message", {}).get("content", "")
