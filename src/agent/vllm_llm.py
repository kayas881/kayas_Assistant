# -*- coding: utf-8 -*-
"""
vLLM Remote LLM - Connect to self-hosted vLLM server via ngrok.
Optimized for Qwen3 models with thinking mode support.
Uses OpenAI-compatible API with native tool calling.
"""

import os
import json
import re
import httpx
from typing import List, Dict, Any, Optional


class VLLMLlm:
    """
    LLM client for remote vLLM server (OpenAI-compatible API).
    
    Supports Qwen3 features:
    - Thinking mode: Detailed reasoning with <think> tags (default)
    - Fast mode: Quick responses without reasoning
    - Native tool calling with XML format
    """
    
    # Context limits for different models
    MODEL_CONTEXT_LIMITS = {
        "Qwen/Qwen2.5-7B-Instruct": 4096,
        "Qwen/Qwen3-32B-AWQ": 8192,
        "QuantTrio/Qwen3-VL-32B-Instruct-AWQ": 8192,
        "Qwen/Qwen3-14B-AWQ": 8192,
        "Qwen/Qwen3-8B": 8192,
        "default": 8192,
    }
    
    # Qwen3 thinking mode control
    FAST_MODE_INSTRUCTION = "/no_think"  # Disables thinking in Qwen3
    THINKING_MODE_INSTRUCTION = "/think"  # Enables detailed reasoning
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = 300.0,  # 5 minutes - VL model is slow on Kaggle T4s
        max_context: int = None,
        mode: str = "thinking",  # "thinking" or "fast"
    ):
        # Import config for defaults
        from .config import vllm_api_url, vllm_model, vllm_max_context, vllm_mode
        
        self.base_url = base_url or vllm_api_url()
        self.model = model or vllm_model()
        self.timeout = timeout
        self.mode = mode or vllm_mode()
        self.client = httpx.Client(timeout=timeout)
        
        # Set context limit (can be overridden)
        self.max_context = max_context or vllm_max_context() or self.MODEL_CONTEXT_LIMITS.get(
            self.model, self.MODEL_CONTEXT_LIMITS["default"]
        )
        
        if not self.base_url:
            raise ValueError("VLLM_API_URL not configured. Set it in .agent/profile.yaml or environment.")
        
        # Ensure URL doesn't end with /
        self.base_url = self.base_url.rstrip("/")
    
    def set_mode(self, mode: str):
        """Switch between 'thinking' and 'fast' modes."""
        self.mode = mode.lower()
    
    def _get_mode_instruction(self) -> str:
        """Get the mode instruction to prepend to prompts."""
        if self.mode == "fast":
            return self.FAST_MODE_INSTRUCTION + " "
        return ""  # Thinking is default for Qwen3
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (avg ~3 chars per token for mixed content)."""
        return len(text) // 3  # Conservative estimate
    
    def _calculate_max_tokens(self, messages: list, tools: list = None) -> int:
        """Calculate safe max_tokens based on input size."""
        # Estimate input tokens
        input_text = ""
        for msg in messages:
            input_text += msg.get("content", "") + " "
        
        # Tools add significant tokens
        if tools:
            input_text += json.dumps(tools)
        
        estimated_input = self._estimate_tokens(input_text)
        
        # For thinking mode, allow more tokens for reasoning
        if self.mode == "thinking":
            max_response = 1024
        else:
            max_response = 512
        
        available = self.max_context - estimated_input - 100  # Safety margin
        max_tokens = max(256, min(max_response, available))
        
        return max_tokens
        
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        use_thinking: bool = None,  # Override mode for this call
        **kwargs
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Max response tokens (auto-calculated if None)
            use_thinking: Override thinking mode (None = use default mode)
        """
        messages = []
        
        # Determine mode for this request
        mode = self.mode if use_thinking is None else ("thinking" if use_thinking else "fast")
        
        if system:
            messages.append({"role": "system", "content": system})
        
        # Add mode instruction for Qwen3
        user_content = prompt
        if mode == "fast":
            user_content = f"{self.FAST_MODE_INSTRUCTION} {prompt}"
        
        messages.append({"role": "user", "content": user_content})
        
        # Calculate safe max_tokens if not specified
        if max_tokens is None:
            max_tokens = self._calculate_max_tokens(messages)
        
        try:
            response = self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            # Strip Qwen3 thinking tags for cleaner output
            return self._strip_thinking_tags(content)
            
        except Exception as e:
            raise RuntimeError(f"vLLM API error: {str(e)}")
    
    def _strip_thinking_tags(self, text: str) -> str:
        """Remove Qwen3 <think>...</think> blocks from output."""
        if not text:
            return text
        # Remove thinking blocks
        cleaned = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
        return cleaned.strip()
    
    def get_thinking_content(self, text: str) -> Optional[str]:
        """Extract the thinking content from a response (for debugging/logging)."""
        if not text:
            return None
        match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
        return match.group(1).strip() if match else None
    
    def generate_with_functions(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        use_thinking: bool = False,  # Tool calls typically don't need thinking
    ) -> Dict[str, Any]:
        """
        Generate with function calling support.
        
        Uses native vLLM tool calling with Qwen3 XML format.
        Tool calls default to fast mode for quicker responses.
        
        Args:
            prompt: User prompt
            system: System prompt
            tools: Tool definitions
            temperature: Sampling temperature
            use_thinking: Whether to enable thinking mode (default False for speed)
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        
        # Use fast mode for tool calls unless explicitly requested
        user_content = prompt
        if not use_thinking:
            user_content = f"{self.FAST_MODE_INSTRUCTION} {prompt}"
        
        messages.append({"role": "user", "content": user_content})
        
        # Calculate safe max_tokens based on context
        max_tokens = self._calculate_max_tokens(messages, tools)
        
        # Try native tool calling first
        try:
            request_body = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if tools:
                request_body["tools"] = tools
                request_body["tool_choice"] = "auto"
            
            response = self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            choice = data["choices"][0]
            message = choice["message"]
            
            # Check for native tool calls in tool_calls array
            if message.get("tool_calls") and len(message["tool_calls"]) > 0:
                tool_call = message["tool_calls"][0]
                return {
                    "type": "function_call",
                    "function": {
                        "name": tool_call["function"]["name"],
                        "arguments": tool_call["function"]["arguments"],
                    }
                }
            
            # Check for Qwen-style <tool_call> tags in content
            content = message.get("content", "")
            if "<tool_call>" in content:
                tool_match = re.search(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', content, re.DOTALL)
                if tool_match:
                    try:
                        tool_data = json.loads(tool_match.group(1))
                        return {
                            "type": "function_call",
                            "function": {
                                "name": tool_data.get("name", ""),
                                "arguments": json.dumps(tool_data.get("arguments", {}))
                            }
                        }
                    except json.JSONDecodeError:
                        pass
            
            # Regular text response
            return {
                "type": "text",
                "text": content
            }
            
        except Exception as e:
            error_msg = str(e)
            # If native tool calling isn't enabled, fall back to prompt-based
            if "enable-auto-tool-choice" in error_msg or "tool_call_parser" in error_msg:
                return self._generate_with_prompt_tools(prompt, system, tools, temperature)
            raise RuntimeError(f"vLLM function call error: {error_msg}")
    
    def _generate_with_prompt_tools(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Fallback: Use prompt-based tool selection."""
        # Build tool descriptions for the prompt
        tool_descriptions = self._build_tool_descriptions(tools) if tools else ""
        
        # Create a structured prompt that encourages JSON tool responses
        augmented_system = f"""{system or "You are a helpful assistant."}

You have access to these tools:
{tool_descriptions}

IMPORTANT: When the user makes a request that requires a tool, respond with ONLY a JSON object in this exact format:
{{"tool": "tool_name", "arguments": {{"arg1": "value1"}}}}

For conversational responses (greetings, thanks, questions about yourself), use:
{{"tool": "respond_conversationally", "arguments": {{"response": "your message"}}}}

If the request is unclear, use:
{{"tool": "ask_clarification", "arguments": {{"question": "what do you need to know?"}}}}

RESPOND WITH JSON ONLY. No explanation, no markdown, just the JSON object."""
        
        # Calculate safe max_tokens
        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": prompt}
        ]
        max_tokens = self._calculate_max_tokens(messages)
        
        try:
            response = self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            
            # Try to parse as JSON
            parsed = self._parse_tool_response(content)
            
            if parsed:
                return {
                    "type": "function_call",
                    "function": {
                        "name": parsed["tool"],
                        "arguments": json.dumps(parsed.get("arguments", {}))
                    }
                }
            
            # Fallback to text response
            return {
                "type": "text",
                "text": content
            }
            
        except Exception as e:
            raise RuntimeError(f"vLLM function call error: {str(e)}")
    
    def _build_tool_descriptions(self, tools: List[Dict]) -> str:
        """Build a text description of available tools."""
        descriptions = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                name = func["name"]
                desc = func.get("description", "")
                params = func.get("parameters", {}).get("properties", {})
                
                param_strs = []
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    param_strs.append(f"  - {pname} ({ptype}): {pdesc}")
                
                param_block = "\n".join(param_strs) if param_strs else "  (no parameters)"
                descriptions.append(f"• {name}: {desc}\n{param_block}")
        
        return "\n\n".join(descriptions)
    
    def _parse_tool_response(self, content: str) -> Optional[Dict]:
        """Try to parse a tool call from the response."""
        # Clean up the response
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = re.sub(r"```(?:json)?\s*", "", content)
            content = content.rstrip("`").strip()
        
        # Try direct JSON parse
        try:
            parsed = json.loads(content)
            if "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Try to find nested JSON
        try:
            # Find first { to last }
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        
        return None
    
    def test_connection(self) -> bool:
        """Test if the vLLM server is reachable."""
        try:
            response = self.client.get(f"{self.base_url}/v1/models", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the vLLM connection."""
        status = {
            "connected": False,
            "model": self.model,
            "mode": self.mode,
            "max_context": self.max_context,
            "base_url": self.base_url,
        }
        
        try:
            response = self.client.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    model_info = models[0]
                    status["connected"] = True
                    status["server_model"] = model_info.get("id")
                    status["max_model_len"] = model_info.get("max_model_len")
        except Exception as e:
            status["error"] = str(e)
        
        return status


def create_vllm_llm(
    url: str = None, 
    model: str = None, 
    mode: str = None
) -> VLLMLlm:
    """
    Factory function to create vLLM client.
    
    Args:
        url: Override API URL
        model: Override model name
        mode: Override mode ('thinking' or 'fast')
    """
    return VLLMLlm(base_url=url, model=model, mode=mode)
