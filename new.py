# robust_click.py
import subprocess, time, sys, argparse, os, logging
from pathlib import Path
from PIL import Image
import pyautogui
import pytesseract
import cv2
from pywinauto import Desktop, Application

logging.basicConfig(level=logging.DEBUG, filename="robust_click.log", filemode="a",
                    format="%(asctime)s %(levelname)s: %(message)s")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

def take_screenshot(name="screencap.png"):
    p = Path("debug_screens")
    p.mkdir(exist_ok=True)
    path = p / name
    img = pyautogui.screenshot()
    img.save(path)
    logging.info(f"Saved screenshot: {path}")
    return str(path)

def start_program(exe_path, args=None):
    try:
        cmd = [exe_path]
        if args:
            cmd += args
        subprocess.Popen(cmd)
        logging.info(f"Started program: {exe_path}")
        return True
    except Exception as e:
        logging.exception("Failed to start program")
        return False

def bring_window_front_by_exe(exe_name, timeout=10):
    # try to find window by process exe_name or title containing exe_name
    import psutil
    desktop = Desktop(backend="uia")
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Build a map of PID->process_name for open processes
        pid_to_name = {}
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid_to_name[proc.info['pid']] = proc.info['name']
            except:
                pass
        
        wins = []
        for w in desktop.windows():
            pid = w.process_id()
            proc_name = pid_to_name.get(pid, "")
            title = w.window_text() or ""
            if exe_name.lower() in proc_name.lower() or exe_name.lower() in title.lower():
                wins.append(w)
        
        if wins:
            w = wins[0]
            try:
                w.set_focus()
                w.wrapper_object().restore()
                logging.info(f"Brought to front window: {w.window_text()}")
                return w
            except Exception as e:
                logging.exception("Failed to set focus on window")
        time.sleep(0.6)
    logging.warning("Could not find window by exe_name/title")
    return None

def uia_click_by_text(window, text, timeout=5):
    # search descendants for element with the text
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for ch in window.descendants():
                try:
                    t = ch.window_text()
                    if t and text.lower() in t.lower():
                        r = ch.rectangle()
                        cx = int((r.left + r.right) / 2)
                        cy = int((r.top + r.bottom) / 2)
                        pyautogui.moveTo(cx, cy, duration=0.2)
                        pyautogui.click()
                        logging.info(f"UIA clicked element with text '{text}' at {cx},{cy}")
                        return True
                except Exception:
                    continue
            time.sleep(0.4)
        logging.info("UIA did not find text element")
        return False
    except Exception as e:
        logging.exception("UIA click failed")
        return False

def image_click(template_path, timeout=8, confidence=0.7):
    deadline = time.time() + timeout
    while time.time() < deadline:
        take_screenshot("before_image_click.png")
        try:
            res = pyautogui.locateOnScreen(template_path, confidence=confidence)
        except Exception as e:
            logging.exception("locateOnScreen threw")
            res = None
        if res:
            cx, cy = pyautogui.center(res)
            pyautogui.moveTo(cx, cy, duration=0.2)
            pyautogui.click()
            logging.info(f"Image click successful at {cx},{cy} using {template_path}")
            return True
        time.sleep(0.6)
    logging.info("Image match not found on screen")
    return False

def ocr_click_text(text, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        screenshot_path = take_screenshot("ocr_try.png")
        img = cv2.imread(screenshot_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # optional: threshold to improve OCR
        #_, th = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        pil = Image.fromarray(gray)
        data = pytesseract.image_to_data(pil, output_type=pytesseract.Output.DICT)
        for i, t in enumerate(data['text']):
            if t and text.lower() in t.lower():
                x = data['left'][i]; y = data['top'][i]; w = data['width'][i]; h = data['height'][i]
                cx, cy = x + w//2, y + h//2
                pyautogui.moveTo(cx, cy, duration=0.2)
                pyautogui.click()
                logging.info(f"OCR clicked '{t}' at {cx},{cy}")
                return True
        time.sleep(0.7)
    logging.info("OCR did not find text")
    return False

def robust_click_flow(exe, click_text=None, image_template=None, wait_after_start=6):
    start_program(exe)
    logging.info(f"Waiting {wait_after_start}s for program to be ready...")
    time.sleep(wait_after_start)

    # bring to front
    basename = os.path.basename(exe)
    w = bring_window_front_by_exe(basename, timeout=10)
    if not w:
        logging.warning("Window not found; still continuing to try image/OCR")

    # Try UIA first
    if w and click_text:
        logging.info("Trying UIA click by text...")
        if uia_click_by_text(w, click_text, timeout=6):
            return True

    # Next: image match fallback
    if image_template and os.path.exists(image_template):
        logging.info("Trying image-based click fallback...")
        if image_click(image_template, timeout=8, confidence=0.7):
            return True

    # Next: OCR fallback
    if click_text:
        logging.info("Trying OCR fallback...")
        if ocr_click_text(click_text, timeout=10):
            return True

    logging.error("All click methods failed. Check debug_screens/ and robust_click.log")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, help="Full path to executable")
    parser.add_argument("--click-text", required=False, help="Text to click on-screen (OCR/UIA)")
    parser.add_argument("--image", required=False, help="Path to small template image for image-match click")
    parser.add_argument("--wait", type=int, default=6, help="Seconds to wait after launching")
    args = parser.parse_args()

    ok = robust_click_flow(args.exe, click_text=args.click_text, image_template=args.image, wait_after_start=args.wait)
    logging.info("FINAL RESULT: " + ("SUCCESS" if ok else "FAILED"))
    print("RESULT:", "SUCCESS" if ok else "FAILED")
