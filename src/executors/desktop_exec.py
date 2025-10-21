from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import time
from pathlib import Path

try:
    import pyautogui
    DESKTOP_AVAILABLE = True
except ImportError:
    DESKTOP_AVAILABLE = False

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    CV_AVAILABLE = True
except Exception:
    CV_AVAILABLE = False

try:
    import pytesseract  # type: ignore
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

try:
    import pyperclip  # type: ignore
    CLIP_AVAILABLE = True
except Exception:
    CLIP_AVAILABLE = False

try:
    import pygetwindow as gw  # type: ignore
    WIN_AVAILABLE = True
except Exception:
    WIN_AVAILABLE = False

from ..agent.config import artifacts_dir


@dataclass
class DesktopConfig:
    move_delay_ms: int = 0
    screenshot_dir: Optional[Path] = None


class DesktopExecutor:
    def __init__(self, cfg: DesktopConfig | None = None):
        self.cfg = cfg or DesktopConfig()
        self._prepare()

    def _prepare(self) -> None:
        if DESKTOP_AVAILABLE:
            pyautogui.FAILSAFE = True  # move mouse to top-left to abort
            if self.cfg.move_delay_ms:
                pyautogui.PAUSE = max(0.0, self.cfg.move_delay_ms / 1000.0)

    def _shot_path(self, name: str | None = None) -> Path:
        base = self.cfg.screenshot_dir or artifacts_dir()
        base.mkdir(parents=True, exist_ok=True)
        fname = name or f"screen_{int(time.time()*1000)}.png"
        return (base / fname).resolve()

    def run_steps(self, steps: List[Dict[str, Any]], stop_on_error: bool = True) -> Dict[str, Any]:
        if not DESKTOP_AVAILABLE:
            return {"error": "pyautogui not available. Install with 'pip install pyautogui'"}
        trace: List[Dict[str, Any]] = []
        screenshots: List[str] = []
        extracted: List[Any] = []
        success = True

        for i, step in enumerate(steps or []):
            if not isinstance(step, dict):
                trace.append({"step": i, "error": "Invalid step format"})
                if stop_on_error:
                    success = False
                    break
                else:
                    continue
            action = str(step.get("action", "")).lower()
            args = step.get("args", {}) or {}
            try:
                if action == "sleep":
                    ms = int(args.get("ms", 500))
                    time.sleep(ms / 1000.0)
                    trace.append({"step": i, "action": action, "ms": ms})
                elif action == "move_to":
                    x = int(args["x"])  # required
                    y = int(args["y"])  # required
                    dur = float(args.get("duration", 0))
                    pyautogui.moveTo(x, y, duration=dur)
                    trace.append({"step": i, "action": action, "x": x, "y": y})
                elif action == "move_rel":
                    dx = int(args["dx"])  # required
                    dy = int(args["dy"])  # required
                    dur = float(args.get("duration", 0))
                    pyautogui.moveRel(dx, dy, duration=dur)
                    trace.append({"step": i, "action": action, "dx": dx, "dy": dy})
                elif action == "click":
                    x = args.get("x")
                    y = args.get("y")
                    btn = str(args.get("button", "left"))
                    clicks = int(args.get("clicks", 1))
                    interval = float(args.get("interval", 0.0))
                    if x is not None and y is not None:
                        pyautogui.click(int(x), int(y), clicks=clicks, interval=interval, button=btn)
                    else:
                        pyautogui.click(clicks=clicks, interval=interval, button=btn)
                    trace.append({"step": i, "action": action, "x": x, "y": y})
                elif action == "double_click":
                    x = args.get("x")
                    y = args.get("y")
                    if x is not None and y is not None:
                        pyautogui.doubleClick(int(x), int(y))
                    else:
                        pyautogui.doubleClick()
                    trace.append({"step": i, "action": action, "x": x, "y": y})
                elif action == "right_click":
                    x = args.get("x")
                    y = args.get("y")
                    if x is not None and y is not None:
                        pyautogui.click(int(x), int(y), button='right')
                    else:
                        pyautogui.click(button='right')
                    trace.append({"step": i, "action": action, "x": x, "y": y})
                elif action == "middle_click":
                    x = args.get("x")
                    y = args.get("y")
                    if x is not None and y is not None:
                        pyautogui.click(int(x), int(y), button='middle')
                    else:
                        pyautogui.click(button='middle')
                    trace.append({"step": i, "action": action, "x": x, "y": y})
                elif action == "write":
                    text = str(args.get("text", ""))
                    interval = float(args.get("interval", 0.0))
                    pyautogui.write(text, interval=interval)
                    trace.append({"step": i, "action": action, "len": len(text)})
                elif action == "paste":
                    text = str(args.get("text", ""))
                    if CLIP_AVAILABLE:
                        pyperclip.copy(text)
                        pyautogui.hotkey('ctrl', 'v')
                        trace.append({"step": i, "action": action, "len": len(text)})
                    else:
                        raise RuntimeError("pyperclip not available ('pip install pyperclip')")
                elif action == "hotkey":
                    keys = args.get("keys") or []
                    if not isinstance(keys, list) or not keys:
                        raise ValueError("hotkey requires list 'keys'")
                    pyautogui.hotkey(*[str(k) for k in keys])
                    trace.append({"step": i, "action": action, "keys": keys})
                elif action == "key_down":
                    key = str(args["key"])  # required
                    pyautogui.keyDown(key)
                    trace.append({"step": i, "action": action, "key": key})
                elif action == "key_up":
                    key = str(args["key"])  # required
                    pyautogui.keyUp(key)
                    trace.append({"step": i, "action": action, "key": key})
                elif action == "scroll":
                    clicks = int(args.get("clicks", -500))
                    x = args.get("x")
                    y = args.get("y")
                    if x is not None and y is not None:
                        pyautogui.scroll(clicks, x=int(x), y=int(y))
                    else:
                        pyautogui.scroll(clicks)
                    trace.append({"step": i, "action": action, "clicks": clicks, "x": x, "y": y})
                elif action == "hscroll":
                    clicks = int(args.get("clicks", 100))
                    x = args.get("x")
                    y = args.get("y")
                    # hscroll may not be supported on all platforms
                    if hasattr(pyautogui, 'hscroll'):
                        if x is not None and y is not None:
                            pyautogui.hscroll(clicks, x=int(x), y=int(y))
                        else:
                            pyautogui.hscroll(clicks)
                        trace.append({"step": i, "action": action, "clicks": clicks, "x": x, "y": y})
                    else:
                        raise RuntimeError("horizontal scroll not supported on this platform")
                elif action == "drag_to":
                    x = int(args["x"])  # required
                    y = int(args["y"])  # required
                    duration = float(args.get("duration", 0.2))
                    button = str(args.get("button", "left"))
                    pyautogui.dragTo(x, y, duration=duration, button=button)
                    trace.append({"step": i, "action": action, "x": x, "y": y, "duration": duration})
                elif action == "drag_rel":
                    dx = int(args["dx"])  # required
                    dy = int(args["dy"])  # required
                    duration = float(args.get("duration", 0.2))
                    button = str(args.get("button", "left"))
                    pyautogui.dragRel(dx, dy, duration=duration, button=button)
                    trace.append({"step": i, "action": action, "dx": dx, "dy": dy, "duration": duration})
                elif action == "screenshot":
                    fname = args.get("filename")
                    out = self._shot_path(fname)
                    img = pyautogui.screenshot()
                    img.save(str(out))
                    screenshots.append(str(out))
                    trace.append({"step": i, "action": action, "path": str(out)})
                elif action == "locate_on_screen":
                    if not CV_AVAILABLE:
                        raise RuntimeError("OpenCV not available ('pip install opencv-python numpy')")
                    template_path = str(args["image"])  # required
                    confidence = float(args.get("confidence", 0.9))
                    region = args.get("region")  # [left, top, width, height]
                    # Use PyAutoGUI's locateOnScreen (uses confidence with OpenCV)
                    box = pyautogui.locateOnScreen(template_path, confidence=confidence, region=region)
                    res = None
                    if box:
                        center = pyautogui.center(box)
                        res = {"box": [box.left, box.top, box.width, box.height], "center": [center.x, center.y]}
                    trace.append({"step": i, "action": action, "found": bool(box)})
                    extracted.append(res)
                elif action == "wait_for_image":
                    if not CV_AVAILABLE:
                        raise RuntimeError("OpenCV not available ('pip install opencv-python numpy')")
                    template_path = str(args["image"])  # required
                    confidence = float(args.get("confidence", 0.9))
                    timeout_ms = int(args.get("timeout_ms", 10000))
                    start = time.time()
                    box = None
                    while (time.time() - start) * 1000 < timeout_ms:
                        box = pyautogui.locateOnScreen(template_path, confidence=confidence)
                        if box:
                            break
                        time.sleep(0.25)
                    if not box:
                        raise RuntimeError("image not found within timeout")
                    center = pyautogui.center(box)
                    res = {"box": [box.left, box.top, box.width, box.height], "center": [center.x, center.y]}
                    extracted.append(res)
                    trace.append({"step": i, "action": action, "found": True})
                elif action == "click_image":
                    if not CV_AVAILABLE:
                        raise RuntimeError("OpenCV not available ('pip install opencv-python numpy')")
                    template_path = str(args["image"])  # required
                    confidence = float(args.get("confidence", 0.9))
                    box = pyautogui.locateOnScreen(template_path, confidence=confidence)
                    if not box:
                        raise RuntimeError("image not found")
                    center = pyautogui.center(box)
                    pyautogui.click(center.x, center.y)
                    trace.append({"step": i, "action": action, "center": [center.x, center.y]})
                elif action == "ocr_region":
                    if not OCR_AVAILABLE:
                        raise RuntimeError("pytesseract not available ('pip install pytesseract') and install Tesseract OCR on Windows")
                    left = int(args["left"])  # required
                    top = int(args["top"])  # required
                    width = int(args["width"])  # required
                    height = int(args["height"])  # required
                    shot = pyautogui.screenshot(region=(left, top, width, height))
                    out = self._shot_path(args.get("filename"))
                    shot.save(str(out))
                    text = pytesseract.image_to_string(str(out))
                    extracted.append(text)
                    screenshots.append(str(out))
                    trace.append({"step": i, "action": action, "region": [left, top, width, height], "chars": len(text)})
                elif action == "find_text":
                    if not OCR_AVAILABLE:
                        raise RuntimeError("pytesseract not available ('pip install pytesseract') and install Tesseract OCR on Windows")
                    region = args.get("region")  # [left, top, width, height]
                    needle = str(args["text"]).strip()
                    lang = str(args.get("lang", "eng"))
                    if region:
                        shot = pyautogui.screenshot(region=tuple(region))
                        offset_left, offset_top = region[0], region[1]
                    else:
                        shot = pyautogui.screenshot()
                        offset_left, offset_top = 0, 0
                    out = self._shot_path(args.get("filename"))
                    shot.save(str(out))
                    data = pytesseract.image_to_data(str(out), lang=lang, output_type=getattr(pytesseract, 'Output').DICT)
                    hits = []
                    n = len(data.get('text', []))
                    for j in range(n):
                        txt = (data['text'][j] or '').strip()
                        if not txt:
                            continue
                        if needle.lower() in txt.lower():
                            x = int(data['left'][j]) + offset_left
                            y = int(data['top'][j]) + offset_top
                            w = int(data['width'][j])
                            h = int(data['height'][j])
                            hits.append({"text": txt, "box": [x, y, w, h], "center": [x + w//2, y + h//2]})
                    extracted.append(hits)
                    trace.append({"step": i, "action": action, "matches": len(hits)})
                elif action == "locate_by_text":
                    if not OCR_AVAILABLE:
                        raise RuntimeError("pytesseract not available ('pip install pytesseract') and install Tesseract OCR on Windows")
                    region = args.get("region")  # [left, top, width, height]
                    needle = str(args["text"]).strip()
                    lang = str(args.get("lang", "eng"))
                    match_mode = str(args.get("match", "contains")).lower()  # 'contains'|'equals'
                    return_mode = str(args.get("return", "all")).lower()  # 'first'|'all'
                    if region:
                        shot = pyautogui.screenshot(region=tuple(region))
                        offset_left, offset_top = region[0], region[1]
                    else:
                        shot = pyautogui.screenshot()
                        offset_left, offset_top = 0, 0
                    out = self._shot_path(args.get("filename"))
                    shot.save(str(out))
                    data = pytesseract.image_to_data(str(out), lang=lang, output_type=getattr(pytesseract, 'Output').DICT)
                    results = []
                    n = len(data.get('text', []))
                    for j in range(n):
                        txt = (data['text'][j] or '').strip()
                        if not txt:
                            continue
                        ok = (needle.lower() == txt.lower()) if match_mode == 'equals' else (needle.lower() in txt.lower())
                        if ok:
                            x = int(data['left'][j]) + offset_left
                            y = int(data['top'][j]) + offset_top
                            w = int(data['width'][j])
                            h = int(data['height'][j])
                            results.append({"text": txt, "box": [x, y, w, h], "center": [x + w//2, y + h//2]})
                            if return_mode == 'first':
                                break
                    extracted.append(results if return_mode == 'all' else (results[0] if results else None))
                    trace.append({"step": i, "action": action, "matches": len(results)})
                elif action == "click_text":
                    if not OCR_AVAILABLE:
                        raise RuntimeError("pytesseract not available ('pip install pytesseract') and install Tesseract OCR on Windows")
                    needle = str(args["text"]).strip()
                    lang = str(args.get("lang", "eng"))
                    region = args.get("region")
                    # Reuse find_text logic
                    if region:
                        shot = pyautogui.screenshot(region=tuple(region))
                        offset_left, offset_top = region[0], region[1]
                    else:
                        shot = pyautogui.screenshot()
                        offset_left, offset_top = 0, 0
                    out = self._shot_path(args.get("filename"))
                    shot.save(str(out))
                    data = pytesseract.image_to_data(str(out), lang=lang, output_type=getattr(pytesseract, 'Output').DICT)
                    target = None
                    for j in range(len(data.get('text', []))):
                        txt = (data['text'][j] or '').strip()
                        if not txt:
                            continue
                        if needle.lower() in txt.lower():
                            x = int(data['left'][j]) + offset_left
                            y = int(data['top'][j]) + offset_top
                            w = int(data['width'][j])
                            h = int(data['height'][j])
                            target = (x + w//2, y + h//2)
                            break
                    if not target:
                        raise RuntimeError("text not found")
                    pyautogui.click(target[0], target[1])
                    trace.append({"step": i, "action": action, "target": [target[0], target[1]]})
                elif action == "get_clipboard":
                    if not CLIP_AVAILABLE:
                        raise RuntimeError("pyperclip not available ('pip install pyperclip')")
                    text = pyperclip.paste()
                    extracted.append(text)
                    trace.append({"step": i, "action": action, "len": len(text)})
                elif action == "set_clipboard":
                    if not CLIP_AVAILABLE:
                        raise RuntimeError("pyperclip not available ('pip install pyperclip')")
                    text = str(args.get("text", ""))
                    pyperclip.copy(text)
                    trace.append({"step": i, "action": action, "len": len(text)})
                elif action == "list_windows":
                    if not WIN_AVAILABLE:
                        raise RuntimeError("pygetwindow not available ('pip install pygetwindow')")
                    wins = gw.getAllTitles()
                    extracted.append(wins)
                    trace.append({"step": i, "action": action, "count": len(wins)})
                elif action == "focus_window":
                    if not WIN_AVAILABLE:
                        raise RuntimeError("pygetwindow not available ('pip install pygetwindow')")
                    title = str(args.get("title", ""))
                    if not title:
                        raise ValueError("focus_window requires 'title'")
                    match = None
                    for w in gw.getAllWindows():
                        if w.title and title.lower() in w.title.lower():
                            match = w
                            break
                    if not match:
                        raise RuntimeError("window not found")
                    try:
                        match.activate()
                    except Exception:
                        pass
                    trace.append({"step": i, "action": action, "title": match.title if match else title})
                elif action == "bring_to_front":
                    if not WIN_AVAILABLE:
                        raise RuntimeError("pygetwindow not available ('pip install pygetwindow')")
                    title = str(args.get("title", ""))
                    if not title:
                        raise ValueError("bring_to_front requires 'title'")
                    target = None
                    for w in gw.getAllWindows():
                        if w.title and title.lower() in w.title.lower():
                            target = w
                            break
                    if not target:
                        raise RuntimeError("window not found")
                    try:
                        target.activate()
                    except Exception:
                        pass
                    trace.append({"step": i, "action": action, "title": target.title if target else title})
                elif action == "move_window":
                    if not WIN_AVAILABLE:
                        raise RuntimeError("pygetwindow not available ('pip install pygetwindow')")
                    title = str(args.get("title", ""))
                    x = int(args.get("x"))
                    y = int(args.get("y"))
                    target = None
                    for w in gw.getAllWindows():
                        if w.title and title.lower() in w.title.lower():
                            target = w
                            break
                    if not target:
                        raise RuntimeError("window not found")
                    try:
                        target.moveTo(x, y)
                    except Exception as _:
                        pass
                    trace.append({"step": i, "action": action, "title": target.title if target else title, "x": x, "y": y})
                else:
                    trace.append({"step": i, "error": f"Unknown action: {action}"})
                    if stop_on_error:
                        success = False
                        break
            except Exception as e:
                trace.append({"step": i, "error": str(e), "action": action})
                if stop_on_error:
                    success = False
                    break
        return {
            "action": "desktop.run_steps",
            "success": success,
            "trace": trace,
            "extracted": extracted,
            "screenshots": screenshots,
        }
