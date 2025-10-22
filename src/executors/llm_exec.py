"""
LLM executor for advanced language model operations.
"""
from __future__ import annotations

import ollama
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    default_model: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2000


class LLMExecutor:
    def __init__(self, cfg: LLMConfig | None = None):
        self.cfg = cfg or LLMConfig()
        self.conversation_history: Dict[str, List[Dict]] = {}

    def generate(self, prompt: str, model: str | None = None,
                temperature: float | None = None, system: str | None = None) -> Dict[str, Any]:
        """Generate text with specified model and parameters."""
        try:
            model = model or self.cfg.default_model
            temperature = temperature if temperature is not None else self.cfg.temperature
            
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': prompt})
            
            response = ollama.chat(
                model=model,
                messages=messages,
                options={'temperature': temperature}
            )
            
            return {
                "action": "llm.generate",
                "success": True,
                "model": model,
                "prompt": prompt,
                "response": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "llm.generate",
                "success": False,
                "error": str(e)
            }

    def chat(self, message: str, conversation_id: str = "default",
            model: str | None = None, system: str | None = None) -> Dict[str, Any]:
        """Have a multi-turn conversation."""
        try:
            model = model or self.cfg.default_model
            
            # Initialize conversation if needed
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = []
                if system:
                    self.conversation_history[conversation_id].append({
                        'role': 'system',
                        'content': system
                    })
            
            # Add user message
            self.conversation_history[conversation_id].append({
                'role': 'user',
                'content': message
            })
            
            # Get response
            response = ollama.chat(
                model=model,
                messages=self.conversation_history[conversation_id]
            )
            
            # Add assistant response to history
            assistant_msg = response['message']['content']
            self.conversation_history[conversation_id].append({
                'role': 'assistant',
                'content': assistant_msg
            })
            
            return {
                "action": "llm.chat",
                "success": True,
                "model": model,
                "conversation_id": conversation_id,
                "message": message,
                "response": assistant_msg,
                "turn_count": len([m for m in self.conversation_history[conversation_id] if m['role'] == 'user'])
            }
        except Exception as e:
            return {
                "action": "llm.chat",
                "success": False,
                "error": str(e)
            }

    def chain_of_thought(self, problem: str, model: str | None = None) -> Dict[str, Any]:
        """Use chain-of-thought reasoning."""
        try:
            model = model or self.cfg.default_model
            
            system_prompt = """You are an AI that solves problems using step-by-step reasoning.
For each problem, break it down into steps and show your thinking process.
Format your response as:

Step 1: [First step]
Step 2: [Second step]
...
Conclusion: [Final answer]"""
            
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': problem}
            ]
            
            response = ollama.chat(model=model, messages=messages)
            
            return {
                "action": "llm.chain_of_thought",
                "success": True,
                "model": model,
                "problem": problem,
                "reasoning": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "llm.chain_of_thought",
                "success": False,
                "error": str(e)
            }

    def few_shot_learning(self, task_description: str, examples: List[Dict[str, str]],
                         query: str, model: str | None = None) -> Dict[str, Any]:
        """Use few-shot learning with examples."""
        try:
            model = model or self.cfg.default_model
            
            messages = [
                {'role': 'system', 'content': task_description}
            ]
            
            # Add examples
            for example in examples:
                messages.append({'role': 'user', 'content': example['input']})
                messages.append({'role': 'assistant', 'content': example['output']})
            
            # Add actual query
            messages.append({'role': 'user', 'content': query})
            
            response = ollama.chat(model=model, messages=messages)
            
            return {
                "action": "llm.few_shot",
                "success": True,
                "model": model,
                "examples_count": len(examples),
                "query": query,
                "response": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "llm.few_shot",
                "success": False,
                "error": str(e)
            }

    def summarize(self, text: str, model: str | None = None,
                 style: str = "concise") -> Dict[str, Any]:
        """Summarize text."""
        try:
            model = model or self.cfg.default_model
            
            style_prompts = {
                "concise": "Provide a concise summary in 2-3 sentences.",
                "detailed": "Provide a detailed summary covering all main points.",
                "bullet": "Summarize as a list of bullet points.",
                "tldr": "Provide a TL;DR summary."
            }
            
            instruction = style_prompts.get(style, style_prompts["concise"])
            prompt = f"{instruction}\n\nText to summarize:\n{text}"
            
            response = ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            return {
                "action": "llm.summarize",
                "success": True,
                "model": model,
                "style": style,
                "original_length": len(text),
                "summary": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "llm.summarize",
                "success": False,
                "error": str(e)
            }

    def list_models(self) -> Dict[str, Any]:
        """List available Ollama models."""
        try:
            models = ollama.list()
            
            return {
                "action": "llm.list_models",
                "success": True,
                "count": len(models['models']),
                "models": [m['name'] for m in models['models']]
            }
        except Exception as e:
            return {
                "action": "llm.list_models",
                "success": False,
                "error": str(e)
            }

    def clear_conversation(self, conversation_id: str = "default") -> Dict[str, Any]:
        """Clear conversation history."""
        try:
            if conversation_id in self.conversation_history:
                del self.conversation_history[conversation_id]
            
            return {
                "action": "llm.clear_conversation",
                "success": True,
                "conversation_id": conversation_id
            }
        except Exception as e:
            return {
                "action": "llm.clear_conversation",
                "success": False,
                "error": str(e)
            }

    def embed_text(self, text: str, model: str = "nomic-embed-text") -> Dict[str, Any]:
        """Generate embeddings for text."""
        try:
            response = ollama.embeddings(model=model, prompt=text)
            
            return {
                "action": "llm.embed_text",
                "success": True,
                "model": model,
                "text_length": len(text),
                "embedding_dimensions": len(response['embedding']),
                "embedding": response['embedding']
            }
        except Exception as e:
            return {
                "action": "llm.embed_text",
                "success": False,
                "error": str(e)
            }
