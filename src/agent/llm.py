from __future__ import annotations

from typing import Iterable, Optional
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

try:
    import ollama
    import httpx
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class LLM:
    def __init__(self, model: str) -> None:
        if not OLLAMA_AVAILABLE:
            raise ImportError("ollama module not installed. Install with: pip install ollama")
        self.model = model
        # Prefer OLLAMA_URL used elsewhere in the repo; fall back to OLLAMA_HOST.
        self.host = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        # Smaller context is often more reliable (less hanging / faster).
        try:
            self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
        except Exception:
            self.num_ctx = 2048

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2, timeout: float = 120.0) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            # NOTE: The ollama python client can sometimes block indefinitely on network/long generations.
            # Enforce a hard timeout at the Python layer so callers don't hang forever.
            def _do_chat() -> dict:
                client = ollama.Client(host=self.host)
                return client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": temperature, "num_ctx": self.num_ctx},
                    stream=False,
                )

            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_do_chat)
                try:
                    res = fut.result(timeout=timeout)
                except FuturesTimeoutError:
                    raise RuntimeError(f"LLM timeout after {timeout:.0f}s")
            
            return res["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LLM error: {str(e)}")

    def stream(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> Iterable[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        for part in ollama.chat(model=self.model, messages=messages, options={"temperature": temperature}, stream=True):
            yield part.get("message", {}).get("content", "")
