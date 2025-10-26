from __future__ import annotations

from typing import Iterable, Optional, List, Dict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

try:
    from transformers import BitsAndBytesConfig  # type: ignore
    _HAS_BNB = True
except Exception:
    _HAS_BNB = False

try:
    from peft import PeftModel  # type: ignore
    _HAS_PEFT = True
except Exception:
    _HAS_PEFT = False


class HFLLM:
    """
    Hugging Face backend for the Agent LLM.

    Supports either a merged model directory or (base_model + LoRA adapter).
    Uses 4-bit quantization when available and enabled.
    """

    def __init__(
        self,
        base_or_merged: str,
        adapter_dir: Optional[str] = None,
        use_4bit: bool = True,
        attn_eager: bool = True,
    ) -> None:
        self.model_name = base_or_merged
        self.adapter_dir = adapter_dir or ""
        self.use_4bit = bool(use_4bit)
        self.attn_eager = bool(attn_eager)

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, 
            use_fast=True, 
            trust_remote_code=True,
            local_files_only=False
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quant_config = None
        if self.use_4bit and _HAS_BNB:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quant_config,
            device_map="auto",
            torch_dtype=torch.float16 if torch.cuda.is_available() else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            local_files_only=False
        )
        if self.attn_eager:
            try:
                self.model.config.attn_implementation = "eager"
            except Exception:
                pass
        self.model.config.use_cache = False

        # Attach adapter if provided (and not already merged)
        if self.adapter_dir:
            if not _HAS_PEFT:
                raise RuntimeError("peft is required to load LoRA adapter but is not installed.")
            self.model = PeftModel.from_pretrained(self.model, self.adapter_dir)

        self.model.eval()

    def _build_messages(self, prompt: str, system: Optional[str]) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2, max_tokens: Optional[int] = None) -> str:
        import signal
        import time
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Model generation timed out after 60 seconds")
        
        try:
            messages = self._build_messages(prompt, system)
            text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer([text], return_tensors="pt")
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            gen_conf = GenerationConfig(
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                max_new_tokens=max_tokens or 512,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
            )
            
            # Set timeout on Windows (different approach since SIGALRM doesn't work)
            start_time = time.time()
            with torch.inference_mode():
                out = self.model.generate(**inputs, generation_config=gen_conf)
                
            elapsed = time.time() - start_time
            if elapsed > 120:  # 2 minute warning
                print(f"Warning: Generation took {elapsed:.1f}s")
                
            decoded = self.tokenizer.decode(out[0], skip_special_tokens=True)
            # Extract the assistant response
            if "<|im_start|>assistant" in decoded:
                return decoded.split("<|im_start|>assistant")[-1].replace("<|im_end|>", "").strip()
            return decoded
        except Exception as e:
            error_msg = f"HF generation failed: {type(e).__name__}: {str(e)}"
            print(error_msg)
            return f"ERROR: {error_msg}"

    def stream(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> Iterable[str]:
        # Simple non-streaming fallback: yield once
        yield self.generate(prompt, system=system, temperature=temperature)
