"""
Groq LLM adapter for Kayas.
Provides access to Llama 3.3 70B via Groq's free API.
"""
from __future__ import annotations

from typing import Optional, Any, Dict, List
import os
import httpx
from groq import Groq


class GroqLLM:
    """Wrapper for Groq API (Llama 3.3 70B)."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq LLM.
        
        Args:
            api_key: Groq API key (if None, reads from GROQ_API_KEY env var)
            model: Model name (default: llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided and not in environment")
        
        self.model = model
        
        # Create a custom httpx client to avoid proxies parameter issue
        try:
            http_client = httpx.Client(timeout=30.0)
            self.client = Groq(api_key=self.api_key, http_client=http_client)
        except Exception:
            # Fallback to default initialization
            self.client = Groq(api_key=self.api_key)
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        timeout: float = 30.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Groq.
        
        Args:
            prompt: User prompt
            system: System prompt/instructions
            temperature: Sampling temperature (0-2)
            timeout: Timeout in seconds (Groq is fast, 30s is plenty)
            tools: Optional tools/functions for function calling
            **kwargs: Additional parameters
        
        Returns:
            Generated text
        """
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Build request
            request_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Add tools if provided (for function calling)
            if tools:
                request_kwargs["tools"] = tools
                request_kwargs["tool_choice"] = "auto"
            
            # Call Groq API
            response = self.client.chat.completions.create(**request_kwargs)
            
            # Extract response
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            
            return ""
        
        except Exception as e:
            raise RuntimeError(f"Groq API error: {str(e)}")
    
    def generate_with_functions(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate with function calling support.
        
        Returns:
            Dict with either:
            - "text": str (if no function call)
            - "function": Dict (if function was called)
        """
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            request_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if tools:
                request_kwargs["tools"] = tools
                request_kwargs["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**request_kwargs)
            
            if not response.choices:
                return {"text": ""}
            
            choice = response.choices[0]
            
            # Check for function call
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                return {
                    "type": "function_call",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    }
                }
            
            # Regular text response
            return {
                "type": "text",
                "text": choice.message.content or ""
            }
        
        except Exception as e:
            raise RuntimeError(f"Groq function call error: {str(e)}")
    
    def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Stream text generation.
        
        Yields:
            Text chunks as they arrive
        """
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            raise RuntimeError(f"Groq streaming error: {str(e)}")
