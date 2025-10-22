"""
Image processing executor for editing, resizing, and converting images.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
from dataclasses import dataclass
import io


@dataclass
class ImageConfig:
    default_format: str = "PNG"
    quality: int = 95


class ImageProcessingExecutor:
    def __init__(self, cfg: ImageConfig | None = None):
        self.cfg = cfg or ImageConfig()

    def resize_image(self, input_path: str, output_path: str | None = None,
                    width: int | None = None, height: int | None = None,
                    scale: float | None = None, maintain_aspect: bool = True) -> Dict[str, Any]:
        """Resize an image."""
        try:
            img = Image.open(input_path)
            original_size = img.size
            
            if scale:
                new_size = (int(img.width * scale), int(img.height * scale))
            elif width and height:
                if maintain_aspect:
                    img.thumbnail((width, height), Image.Resampling.LANCZOS)
                    new_size = img.size
                else:
                    new_size = (width, height)
            elif width:
                aspect = img.height / img.width
                new_size = (width, int(width * aspect))
            elif height:
                aspect = img.width / img.height
                new_size = (int(height * aspect), height)
            else:
                return {
                    "action": "image.resize",
                    "success": False,
                    "error": "Must provide width, height, or scale"
                }
            
            if not maintain_aspect or (width and height and not scale):
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            output_path = output_path or self._generate_output_path(input_path, "_resized")
            img.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.resize",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "original_size": original_size,
                "new_size": new_size
            }
        except Exception as e:
            return {
                "action": "image.resize",
                "success": False,
                "error": str(e)
            }

    def crop_image(self, input_path: str, output_path: str | None = None,
                  left: int = 0, top: int = 0, right: int | None = None,
                  bottom: int | None = None) -> Dict[str, Any]:
        """Crop an image."""
        try:
            img = Image.open(input_path)
            
            right = right or img.width
            bottom = bottom or img.height
            
            cropped = img.crop((left, top, right, bottom))
            
            output_path = output_path or self._generate_output_path(input_path, "_cropped")
            cropped.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.crop",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "crop_box": (left, top, right, bottom),
                "new_size": cropped.size
            }
        except Exception as e:
            return {
                "action": "image.crop",
                "success": False,
                "error": str(e)
            }

    def rotate_image(self, input_path: str, output_path: str | None = None,
                    angle: float = 90, expand: bool = True) -> Dict[str, Any]:
        """Rotate an image."""
        try:
            img = Image.open(input_path)
            rotated = img.rotate(angle, expand=expand)
            
            output_path = output_path or self._generate_output_path(input_path, "_rotated")
            rotated.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.rotate",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "angle": angle,
                "new_size": rotated.size
            }
        except Exception as e:
            return {
                "action": "image.rotate",
                "success": False,
                "error": str(e)
            }

    def convert_format(self, input_path: str, output_path: str | None = None,
                      format: str | None = None) -> Dict[str, Any]:
        """Convert image format."""
        try:
            img = Image.open(input_path)
            
            if img.mode in ('RGBA', 'LA', 'P') and format and format.upper() in ('JPEG', 'JPG'):
                # Convert RGBA to RGB for JPEG
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            format = format or self.cfg.default_format
            
            if not output_path:
                input_p = Path(input_path)
                output_path = str(input_p.with_suffix(f".{format.lower()}"))
            
            img.save(output_path, format=format.upper(), quality=self.cfg.quality)
            
            return {
                "action": "image.convert_format",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "format": format.upper()
            }
        except Exception as e:
            return {
                "action": "image.convert_format",
                "success": False,
                "error": str(e)
            }

    def apply_filter(self, input_path: str, output_path: str | None = None,
                    filter_type: str = "BLUR") -> Dict[str, Any]:
        """Apply filter to image."""
        try:
            img = Image.open(input_path)
            
            filter_map = {
                "BLUR": ImageFilter.BLUR,
                "CONTOUR": ImageFilter.CONTOUR,
                "DETAIL": ImageFilter.DETAIL,
                "EDGE_ENHANCE": ImageFilter.EDGE_ENHANCE,
                "EMBOSS": ImageFilter.EMBOSS,
                "SHARPEN": ImageFilter.SHARPEN,
                "SMOOTH": ImageFilter.SMOOTH
            }
            
            filter_obj = filter_map.get(filter_type.upper())
            if not filter_obj:
                return {
                    "action": "image.apply_filter",
                    "success": False,
                    "error": f"Unknown filter: {filter_type}. Available: {', '.join(filter_map.keys())}"
                }
            
            filtered = img.filter(filter_obj)
            
            output_path = output_path or self._generate_output_path(input_path, f"_{filter_type.lower()}")
            filtered.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.apply_filter",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "filter": filter_type.upper()
            }
        except Exception as e:
            return {
                "action": "image.apply_filter",
                "success": False,
                "error": str(e)
            }

    def adjust_brightness(self, input_path: str, output_path: str | None = None,
                         factor: float = 1.5) -> Dict[str, Any]:
        """Adjust image brightness."""
        try:
            img = Image.open(input_path)
            enhancer = ImageEnhance.Brightness(img)
            enhanced = enhancer.enhance(factor)
            
            output_path = output_path or self._generate_output_path(input_path, "_brightness")
            enhanced.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.adjust_brightness",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "factor": factor
            }
        except Exception as e:
            return {
                "action": "image.adjust_brightness",
                "success": False,
                "error": str(e)
            }

    def adjust_contrast(self, input_path: str, output_path: str | None = None,
                       factor: float = 1.5) -> Dict[str, Any]:
        """Adjust image contrast."""
        try:
            img = Image.open(input_path)
            enhancer = ImageEnhance.Contrast(img)
            enhanced = enhancer.enhance(factor)
            
            output_path = output_path or self._generate_output_path(input_path, "_contrast")
            enhanced.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.adjust_contrast",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "factor": factor
            }
        except Exception as e:
            return {
                "action": "image.adjust_contrast",
                "success": False,
                "error": str(e)
            }

    def add_text(self, input_path: str, output_path: str | None = None,
                text: str = "", position: Tuple[int, int] = (10, 10),
                font_size: int = 40, color: Tuple[int, int, int] = (255, 255, 255)) -> Dict[str, Any]:
        """Add text overlay to image."""
        try:
            img = Image.open(input_path)
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            draw.text(position, text, font=font, fill=color)
            
            output_path = output_path or self._generate_output_path(input_path, "_text")
            img.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.add_text",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "text": text,
                "position": position
            }
        except Exception as e:
            return {
                "action": "image.add_text",
                "success": False,
                "error": str(e)
            }

    def get_image_info(self, input_path: str) -> Dict[str, Any]:
        """Get image information."""
        try:
            img = Image.open(input_path)
            
            return {
                "action": "image.get_info",
                "success": True,
                "path": input_path,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "file_size_bytes": Path(input_path).stat().st_size
            }
        except Exception as e:
            return {
                "action": "image.get_info",
                "success": False,
                "error": str(e)
            }

    def create_thumbnail(self, input_path: str, output_path: str | None = None,
                        size: Tuple[int, int] = (128, 128)) -> Dict[str, Any]:
        """Create thumbnail."""
        try:
            img = Image.open(input_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            output_path = output_path or self._generate_output_path(input_path, "_thumb")
            img.save(output_path, quality=self.cfg.quality)
            
            return {
                "action": "image.create_thumbnail",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "size": img.size
            }
        except Exception as e:
            return {
                "action": "image.create_thumbnail",
                "success": False,
                "error": str(e)
            }

    def _generate_output_path(self, input_path: str, suffix: str) -> str:
        """Generate output path with suffix."""
        p = Path(input_path)
        return str(p.parent / f"{p.stem}{suffix}{p.suffix}")
