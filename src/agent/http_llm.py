from __future__ import annotations

from typing import Optional
import httpx


class HTTPLLM:
    """
    Thin HTTP client for a remote LLM service.

    Expected server API:
      POST {base_url}/generate
      body: {
        "prompt": str,
        "system": Optional[str],
        "temperature": Optional[float],
        "max_tokens": Optional[int]
      }
      returns: { "text": str }
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.client = httpx.Client(timeout=timeout)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = self.client.post(
                f"{self.base_url}/generate",
                json={
                    "prompt": prompt,
                    "system": system or "",
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            # Most servers will return {"text": "..."}
            text = data.get("text")
            if isinstance(text, str):
                return text
            # Fallbacks
            if isinstance(data, dict):
                for key in ("output", "completion", "response"):
                    if isinstance(data.get(key), str):
                        return data[key]
            return ""
        except Exception as e:
            return f"ERROR: {e}"
