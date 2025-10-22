"""
Vision executor for analyzing images and screens using AI vision models.
"""
from __future__ import annotations

import ollama
import base64
from typing import Dict, Any, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VisionConfig:
    model: str = "llava"  # or "bakllava", "llava-phi3"
    temperature: float = 0.7


class VisionExecutor:
    def __init__(self, cfg: VisionConfig | None = None):
        self.cfg = cfg or VisionConfig()

    def analyze_image(self, image_path: str, prompt: str = "Describe this image in detail") -> Dict[str, Any]:
        """Analyze an image with AI vision."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            response = ollama.chat(
                model=self.cfg.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_data]
                }]
            )
            
            return {
                "action": "vision.analyze_image",
                "success": True,
                "image_path": image_path,
                "prompt": prompt,
                "analysis": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "vision.analyze_image",
                "success": False,
                "error": str(e)
            }

    def answer_about_image(self, image_path: str, question: str) -> Dict[str, Any]:
        """Answer a question about an image."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            response = ollama.chat(
                model=self.cfg.model,
                messages=[{
                    'role': 'user',
                    'content': question,
                    'images': [image_data]
                }]
            )
            
            return {
                "action": "vision.answer_about_image",
                "success": True,
                "image_path": image_path,
                "question": question,
                "answer": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "vision.answer_about_image",
                "success": False,
                "error": str(e)
            }

    def compare_images(self, image_path1: str, image_path2: str,
                      prompt: str = "Compare these two images and describe the differences") -> Dict[str, Any]:
        """Compare two images."""
        try:
            with open(image_path1, 'rb') as f:
                image_data1 = f.read()
            with open(image_path2, 'rb') as f:
                image_data2 = f.read()
            
            response = ollama.chat(
                model=self.cfg.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_data1, image_data2]
                }]
            )
            
            return {
                "action": "vision.compare_images",
                "success": True,
                "image_path1": image_path1,
                "image_path2": image_path2,
                "comparison": response['message']['content']
            }
        except Exception as e:
            return {
                "action": "vision.compare_images",
                "success": False,
                "error": str(e)
            }

    def detect_objects(self, image_path: str) -> Dict[str, Any]:
        """Detect and list objects in an image."""
        prompt = "List all the objects you can see in this image. Be specific and detailed."
        return self.analyze_image(image_path, prompt)

    def read_text_in_image(self, image_path: str) -> Dict[str, Any]:
        """Read and extract text from an image."""
        prompt = "Extract and list all text visible in this image. Preserve formatting where possible."
        return self.analyze_image(image_path, prompt)

    def analyze_screenshot(self, screenshot_path: str,
                          question: str = "What is shown on this screen?") -> Dict[str, Any]:
        """Analyze a screenshot."""
        return self.answer_about_image(screenshot_path, question)
