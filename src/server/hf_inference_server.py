from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from ..agent.hf_llm import HFLLM
from ..agent.config import hf_base_model, hf_merged_model_dir, hf_adapter_dir, hf_use_4bit


app = FastAPI(title="Kayas HF Inference Server")


class GenerateRequest(BaseModel):
    prompt: str
    system: str | None = None
    temperature: float | None = 0.3
    max_tokens: int | None = 512


class GenerateResponse(BaseModel):
    text: str


_LLM: HFLLM | None = None


def _get_llm() -> HFLLM:
    global _LLM
    if _LLM is not None:
        return _LLM
    merged = hf_merged_model_dir()
    base_or_merged = merged if merged else hf_base_model()
    adapter = None if merged else (hf_adapter_dir() or None)
    _LLM = HFLLM(base_or_merged, adapter_dir=adapter, use_4bit=hf_use_4bit())
    return _LLM


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    llm = _get_llm()
    out = llm.generate(
        req.prompt,
        system=req.system or "",
        temperature=req.temperature or 0.3,
        max_tokens=req.max_tokens or 512,
    )
    return GenerateResponse(text=out)


# Run with: uvicorn src.server.hf_inference_server:app --host 0.0.0.0 --port 8008
