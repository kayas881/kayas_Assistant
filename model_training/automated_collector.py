"""
Automated UI Interaction Dataset Generator

Automatically generates training data by:
1. Opening Windows apps (Settings, Notepad, etc.)
2. Performing random UI interactions
3. Capturing screenshots with bounding boxes
4. Labeling elements using Windows UIAutomation API

Runs in background without disturbing your actual workflow.

Usage:
    python automated_collector.py --apps settings notepad --duration 3600
"""

import uiautomation as auto
import pyautogui
import time
import json
import random
import os
from pathlib import Path
from datetime import datetime
import argparse
import subprocess
import win32gui
import win32con
from PIL import ImageGrab
import logging
from collections import deque, defaultdict

# Setup logging with UTF-8 encoding for Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure StreamHandler to use UTF-8 on Windows
import sys
if sys.platform == 'win32':
    import io
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            # Only wrap stderr, leave file handler alone
            handler.stream = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)


class AutomatedDataCollector:
    """Generates training data by automating UI interactions"""
    
    # App configurations
    APP_CONFIGS = {
        "settings": {
            "command": "start ms-settings:",
            "wait_time": 5,  # Settings needs more time to load
            "interactions": ["click", "navigate"],
            "max_depth": 2  # Reduced depth to avoid deep navigation that might close Settings
        },
        "notepad": {
            "command": "notepad.exe",
            "wait_time": 2,
            "interactions": ["type", "click", "menu"],
            "max_depth": 2
        },
        "calculator": {
            "command": "calc.exe",
            "wait_time": 2,
            "interactions": ["click"],
            "max_depth": 1
        },
        "explorer": {
            "command": "explorer.exe",
            "wait_time": 2,
            "interactions": ["click", "navigate"],
            "max_depth": 3
        },
        "paint": {
            "command": "mspaint.exe",
            "wait_time": 2,
            "interactions": ["click"],
            "max_depth": 2
        },
        "taskmanager": {
            "command": "taskmgr.exe",
            "wait_time": 3,
            "interactions": ["click", "navigate"],
            "max_depth": 2
        },
        "snipping": {
            "command": "snippingtool.exe",
            "wait_time": 2,
            "interactions": ["click"],
            "max_depth": 1
        },
        "msstore": {
            "command": "start ms-windows-store:",
            "wait_time": 4,
            "interactions": ["click", "navigate"],
            "max_depth": 3
        },
        "photos": {
            "command": "start ms-photos:",
            "wait_time": 3,
            "interactions": ["click"],
            "max_depth": 2
        },
        "clock": {
            "command": "start ms-clock:",
            "wait_time": 2,
            "interactions": ["click"],
            "max_depth": 1
        },
        "weather": {
            "command": "start bingweather:",
            "wait_time": 3,
            "interactions": ["click"],
            "max_depth": 2
        },
        "news": {
            "command": "start bingnews:",
            "wait_time": 3,
            "interactions": ["click", "navigate"],
            "max_depth": 2
        },
        "taskbar": {
            "command": "explorer.exe shell:::{05d7b0f4-2121-4eff-bf6b-ed3f69b894d9}",  # Open notification center
            "wait_time": 2,
            "interactions": ["click"],
            "max_depth": 2
        },
        "maps": {
            "command": "start bingmaps:",
            "wait_time": 3,
            "interactions": ["click"],
            "max_depth": 2
        }
    }
    
    def __init__(self, output_dir="training_data_auto", headless=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.headless = headless
        
        self.samples = []
        self.sample_id = 0
        # Track recently clicked targets per app to reduce repetition
        self.recent_targets_by_app = defaultdict(lambda: deque(maxlen=15))
        
        logger.info(f"Initialized collector, output: {self.output_dir}")
    
    def launch_app(self, app_name):
        """Launch application and return window handle"""
        config = self.APP_CONFIGS.get(app_name)
        if not config:
            logger.error(f"Unknown app: {app_name}")
            return None
        
        logger.info(f"Launching {app_name}...")
        
        try:
            # Launch app
            subprocess.Popen(config["command"], shell=True)
            time.sleep(config["wait_time"])
            
            # Find window - use multiple strategies
            window = None
            
            # Strategy 1: Try by app name
            if app_name == "calculator":
                window = auto.WindowControl(searchDepth=1, ClassName="ApplicationFrameWindow", Name="Calculator")
            elif app_name == "notepad":
                window = auto.WindowControl(searchDepth=1, ClassName="Notepad")
            elif app_name == "settings":
                window = auto.WindowControl(searchDepth=1, Name="Settings")
            elif app_name == "explorer":
                window = auto.WindowControl(searchDepth=1, ClassName="CabinetWClass")
            elif app_name == "paint":
                window = auto.WindowControl(searchDepth=1, ClassName="MSPaintApp")
            elif app_name == "taskmanager":
                window = auto.WindowControl(searchDepth=1, Name="Task Manager")
            elif app_name == "snipping":
                window = auto.WindowControl(searchDepth=1, Name="Snipping Tool")
            elif app_name == "taskbar":
                # For taskbar interactions, use desktop window
                window = auto.WindowControl(searchDepth=1, ClassName="Shell_TrayWnd") or \
                         auto.GetForegroundControl()
            elif app_name in ["msstore", "photos", "clock", "weather", "news", "maps"]:
                # Modern UWP apps use ApplicationFrameWindow
                window = auto.WindowControl(searchDepth=1, ClassName="ApplicationFrameWindow")
            
            # Strategy 2: Try foreground window
            if not window or not window.Exists(0, 0):
                time.sleep(1)
                window = auto.GetForegroundControl()
            
            # Strategy 3: Find any top-level window
            if not window or not window.Exists(0, 0):
                desktop = auto.GetRootControl()
                for child in desktop.GetChildren():
                    if child.ControlTypeName == "WindowControl" and child.IsEnabled:
                        window = child
                        break
            
            if not window or not window.Exists(0, 0):
                logger.warning(f"Could not find window for {app_name}")
                return None
            
            # Make window active
            try:
                window.SetFocus()
            except:
                pass  # Some windows can't be focused
            
            logger.info(f"[OK] Launched {app_name}")
            return window
            
        except Exception as e:
            logger.error(f"Failed to launch {app_name}: {e}")
            return None
    
    def capture_ui_state(self, window, action_context=None):
        """Capture screenshot + UI element metadata"""
        try:
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Save screenshot
            screenshot_file = f"frame_{self.sample_id:06d}.png"
            screenshot.save(self.output_dir / screenshot_file)
            
            # Get all UI elements using UIAutomation
            elements = []
            
            def walk_ui_tree(control, depth=0, max_depth=5):
                """Recursively walk UI tree and extract element info"""
                if depth > max_depth:
                    return
                
                try:
                    rect = control.BoundingRectangle
                    if rect.width() > 0 and rect.height() > 0:
                        element = {
                            "type": control.ControlTypeName,
                            "name": control.Name or "",
                            "automation_id": control.AutomationId or "",
                            "class_name": control.ClassName or "",
                            "bbox": [rect.left, rect.top, rect.right, rect.bottom],
                            "enabled": control.IsEnabled,
                            "visible": control.IsOffscreen == False,
                            "depth": depth
                        }
                        
                        # Get additional properties for specific types
                        if control.ControlTypeName == "ButtonControl":
                            element["clickable"] = True
                        elif control.ControlTypeName == "EditControl":
                            element["text"] = control.GetValuePattern().Value if control.GetValuePattern() else ""
                        elif control.ControlTypeName == "SliderControl":
                            try:
                                value_pattern = control.GetValuePattern()
                                element["value"] = value_pattern.Value
                            except:
                                pass
                        
                        elements.append(element)
                    
                    # Walk children
                    for child in control.GetChildren():
                        walk_ui_tree(child, depth + 1, max_depth)
                        
                except Exception as e:
                    # Skip elements that cause errors
                    pass
            
            # Start walking from window
            walk_ui_tree(window, max_depth=3)
            
            # Create sample
            sample = {
                "id": self.sample_id,
                "timestamp": datetime.now().isoformat(),
                "screenshot": screenshot_file,
                "elements": elements,
                "num_elements": len(elements)
            }
            
            # Add action context if provided
            if action_context:
                sample["action"] = action_context
            
            self.samples.append(sample)
            self.sample_id += 1
            
            logger.info(f"[CAPTURE] Frame {self.sample_id} ({len(elements)} elements)")
            return sample
            
        except Exception as e:
            logger.error(f"Failed to capture state: {e}")
            return None
    
    def perform_random_interaction(self, window, app_name):
        """Perform a random UI interaction"""
        config = self.APP_CONFIGS[app_name]
        interaction_type = random.choice(config["interactions"])
        
        try:
            # Get all clickable elements - correct syntax for uiautomation
            def find_clickable(control, depth=0, max_depth=5):
                """Recursively find all clickable controls"""
                clickable = []
                if depth > max_depth:
                    return clickable
                
                try:
                    # Check if this control is clickable
                    if control.ControlTypeName in ["ButtonControl", "MenuItemControl", "ListItemControl"]:
                        if control.IsEnabled and control.Name:
                            # EXCLUDE window control buttons (close, minimize, maximize)
                            excluded_names = [
                                "Close", "Minimize", "Maximize",
                                "Close Calculator", "Minimize Calculator", "Maximize Calculator",
                                "Close Settings", "Minimize Settings", "Maximize Settings",
                                "Close Notepad", "Minimize Notepad", "Maximize Notepad",
                                "Close Paint", "Minimize Paint", "Maximize Paint",
                                "Restore", "Restore Settings", "Restore Calculator"
                            ]
                            # Also exclude buttons with just these keywords
                            name_lower = control.Name.lower()
                            # Skip invisible or offscreen items (0-sized bounding rectangle)
                            try:
                                rect = control.BoundingRectangle
                                width = max(0, rect.right - rect.left)
                                height = max(0, rect.bottom - rect.top)
                            except Exception:
                                width = height = 0

                            if (
                                control.Name not in excluded_names
                                and not any(keyword in name_lower for keyword in ["close", "minimize", "maximize", "restore"])
                                and width > 1 and height > 1
                            ):
                                clickable.append(control)
                    
                    # Recursively check children
                    for child in control.GetChildren():
                        clickable.extend(find_clickable(child, depth + 1, max_depth))
                except:
                    pass
                
                return clickable
            
            buttons = find_clickable(window, max_depth=5)
            
            if not buttons:
                logger.warning("No interactive elements found")
                return None
            
            # Reduce repetition: exclude recently clicked targets for this app
            recent = self.recent_targets_by_app[app_name]
            non_recent = [b for b in buttons if b.Name not in recent]
            if non_recent:
                buttons = non_recent
            
            # For Settings app, deprioritize Accounts and prioritize System/Display/Brightness
            if app_name == "settings":
                lower_name = lambda c: c.Name.lower()
                # Prefer these if available
                prefer_keywords = ["system", "display", "brightness", "back", "windows update", "personalization", "network", "bluetooth"]
                preferred = [b for b in buttons if any(k in lower_name(b) for k in prefer_keywords)]
                if preferred and random.random() < 0.7:  # 70% chance to pick from preferred when present
                    buttons = preferred
                else:
                    # Deprioritize accounts/email items if other options exist
                    deprior_keywords = ["account", "email", "sign-in", "kayas"]
                    non_accounts = [b for b in buttons if not any(k in lower_name(b) for k in deprior_keywords)]
                    if non_accounts:
                        buttons = non_accounts

            # Pick random element from the refined list
            target = random.choice(buttons)
            
            action_context = {
                "type": interaction_type,
                "target_name": target.Name,
                "target_type": target.ControlTypeName,
                "target_bbox": [
                    target.BoundingRectangle.left,
                    target.BoundingRectangle.top,
                    target.BoundingRectangle.right,
                    target.BoundingRectangle.bottom
                ]
            }
            
            # Perform interaction
            if interaction_type == "click":
                logger.info(f"Clicking: {target.Name}")
                target.Click(simulateMove=False)
                time.sleep(0.5)
                
            elif interaction_type == "navigate":
                logger.info(f"Navigating to: {target.Name}")
                target.Click(simulateMove=False)
                time.sleep(1)
                
            elif interaction_type == "type":
                # Find text input - correct syntax
                def find_edit_boxes(control, depth=0, max_depth=5):
                    boxes = []
                    if depth > max_depth:
                        return boxes
                    try:
                        if control.ControlTypeName == "EditControl" and control.IsEnabled:
                            boxes.append(control)
                        for child in control.GetChildren():
                            boxes.extend(find_edit_boxes(child, depth + 1, max_depth))
                    except:
                        pass
                    return boxes
                
                edit_boxes = find_edit_boxes(window)
                if edit_boxes:
                    edit_box = random.choice(edit_boxes)
                    text = random.choice([
                        "Hello World",
                        "Test input",
                        "Sample text",
                        "Automated entry"
                    ])
                    logger.info(f"Typing: {text}")
                    edit_box.SendKeys(text)
                    action_context["target_name"] = edit_box.Name
                    action_context["text"] = text
            
            # Track recent targets for this app to reduce repetition
            try:
                recent.append(target.Name)
            except Exception:
                pass
            return action_context
            
        except Exception as e:
            logger.warning(f"Interaction failed: {e}")
            return None
    
    def collect_from_app(self, app_name, num_samples=50):
        """Collect samples from a specific app with robust error recovery"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecting from: {app_name}")
        logger.info(f"{'='*60}")
        
        samples_collected = 0
        attempts = 0
        max_attempts = 3
        
        while samples_collected < num_samples and attempts < max_attempts:
            attempts += 1
            
            # Launch app
            window = self.launch_app(app_name)
            if not window:
                logger.warning(f"Attempt {attempts}/{max_attempts}: Failed to launch {app_name}")
                time.sleep(5)
                continue
            
            try:
                # Capture initial state
                sample = self.capture_ui_state(window)
                if sample and sample.get("num_elements", 0) > 0:
                    samples_collected += 1
                    logger.info(f"Sample {samples_collected}/{num_samples} captured")
                
                # Perform random interactions
                failed_interactions = 0
                max_failed = 5
                
                while samples_collected < num_samples and failed_interactions < max_failed:
                    try:
                        # Check if window still exists
                        if not window.Exists(0, 0):
                            logger.warning(f"Window closed unexpectedly at sample {samples_collected}")
                            break
                        
                        # Perform interaction
                        action = self.perform_random_interaction(window, app_name)
                        
                        # Capture resulting state
                        sample = self.capture_ui_state(window, action)
                        
                        # Verify sample quality
                        if sample and sample.get("num_elements", 0) > 0:
                            samples_collected += 1
                            failed_interactions = 0  # Reset failure counter
                            
                            # Log progress
                            if samples_collected % 10 == 0:
                                logger.info(f"Progress: {samples_collected}/{num_samples}")
                        else:
                            failed_interactions += 1
                            logger.warning(f"Empty sample captured (failed: {failed_interactions}/{max_failed})")
                        
                        # Small delay between interactions
                        time.sleep(random.uniform(0.5, 1.5))
                        
                    except Exception as e:
                        failed_interactions += 1
                        logger.warning(f"Interaction error: {e} (failed: {failed_interactions}/{max_failed})")
                        time.sleep(2)
                        
                        if failed_interactions >= max_failed:
                            logger.error(f"Too many failures, restarting app...")
                            break
                
            except Exception as e:
                logger.error(f"Error during collection attempt {attempts}: {e}")
            
            finally:
                # Close app
                try:
                    window.Close()
                    time.sleep(2)
                except:
                    # Force kill if close fails
                    try:
                        if app_name in ["calculator", "notepad", "mspaint"]:
                            os.system(f"taskkill /F /IM {self.app_configs[app_name]['command']} 2>nul")
                    except:
                        pass
            
            # If we got enough samples, we're done
            if samples_collected >= num_samples:
                break
            
            # Otherwise, log restart attempt
            if samples_collected < num_samples:
                logger.warning(f"Only collected {samples_collected}/{num_samples}, restarting app (attempt {attempts}/{max_attempts})")
                time.sleep(3)
        
        logger.info(f"[OK] Collected {samples_collected}/{num_samples} samples from {app_name}")
        return samples_collected
    
    def save_dataset(self):
        """Save dataset metadata to JSON"""
        dataset_file = self.output_dir / "dataset.json"
        
        with open(dataset_file, "w") as f:
            json.dump({
                "num_samples": len(self.samples),
                "created_at": datetime.now().isoformat(),
                "samples": self.samples
            }, f, indent=2)
        
        logger.info(f"[SAVE] Dataset saved: {len(self.samples)} samples")
    
    def export_for_training(self):
        """Export dataset in training format"""
        train_file = self.output_dir / "train.jsonl"
        
        with open(train_file, "w") as f:
            for sample in self.samples:
                # Create training example
                example = {
                    "image": sample["screenshot"],
                    "elements": sample["elements"],
                    "num_elements": sample["num_elements"]
                }
                
                # Add action if present
                if "action" in sample:
                    example["action"] = sample["action"]
                
                f.write(json.dumps(example) + "\n")
        
        logger.info(f"[EXPORT] Training file: {train_file}")
        
        # Also create bounding box annotations file
        bbox_file = self.output_dir / "bboxes.json"
        bboxes = {}
        
        for sample in self.samples:
            bboxes[sample["screenshot"]] = [
                {
                    "type": elem["type"],
                    "name": elem["name"],
                    "bbox": elem["bbox"]
                }
                for elem in sample["elements"]
            ]
        
        with open(bbox_file, "w") as f:
            json.dump(bboxes, f, indent=2)
        
        logger.info(f"[EXPORT] Bounding boxes: {bbox_file}")


def main():
    parser = argparse.ArgumentParser(description="Automated UI dataset collector")
    parser.add_argument(
        "--apps",
        nargs="+",
        choices=[
            "calculator", "notepad", "paint", "explorer", "settings",
            "taskmanager", "snipping", "clock", "msstore", "photos",
            "weather", "news", "taskbar", "maps", "all"
        ],
        default=["all"],
        help="Apps to collect from"
    )
    parser.add_argument(
        "--samples-per-app",
        type=int,
        default=50,
        help="Number of samples per app"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Max duration in seconds (overrides samples-per-app)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="training_data_auto",
        help="Output directory"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force collection even if an app was previously marked completed"
    )
    
    args = parser.parse_args()
    
    # Determine apps to use
    if "all" in args.apps:
        apps = [
            "calculator", "notepad", "paint", "explorer", "settings",
            "taskmanager", "snipping", "clock", "msstore", "photos",
            "weather", "news", "taskbar", "maps"
        ]
    else:
        apps = args.apps
    
    logger.info("\n" + "="*60)
    logger.info("Automated UI Dataset Collector")
    logger.info("="*60)
    logger.info(f"Apps: {', '.join(apps)}")
    logger.info(f"Samples per app: {args.samples_per_app}")
    logger.info(f"Output: {args.output}")
    logger.info("="*60)
    
    # Create collector
    collector = AutomatedDataCollector(output_dir=args.output)
    
    # Progress tracking
    progress_file = Path(args.output) / "progress.json"
    app_results = {}
    
    # Load previous progress if exists
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                app_results = json.load(f)
            logger.info(f"[RESUME] Found previous progress: {len(app_results)} apps completed")
        except:
            pass
    
    # Collect from each app
    start_time = time.time()
    total_samples = 0
    failed_apps = []
    
    for app in apps:
        try:
            # Skip if already completed in previous run (unless forced)
            if app in app_results and app_results[app].get("completed", False) and not args.force:
                samples = app_results[app].get("samples", 0)
                logger.info(f"[SKIP] {app} already completed ({samples} samples)")
                total_samples += samples
                continue
            elif app in app_results and app_results[app].get("completed", False) and args.force:
                logger.info(f"[FORCE] Re-collecting for {app} despite completed status")
            
            # Check duration limit
            if args.duration:
                elapsed = time.time() - start_time
                if elapsed >= args.duration:
                    logger.info(f"[TIMEOUT] Duration limit reached ({args.duration}s)")
                    break
            
            logger.info(f"\n[START] Processing {app}...")
            samples = collector.collect_from_app(app, args.samples_per_app)
            total_samples += samples
            
            # Track results
            app_results[app] = {
                "samples": samples,
                "target": args.samples_per_app,
                "completed": samples >= args.samples_per_app * 0.8,  # 80% threshold
                "timestamp": datetime.now().isoformat()
            }
            
            # Save progress after each app
            with open(progress_file, "w") as f:
                json.dump(app_results, f, indent=2)
            
            logger.info(f"[OK] {app}: {samples}/{args.samples_per_app} samples")
            
            if samples < args.samples_per_app * 0.5:
                failed_apps.append((app, samples))
                logger.warning(f"[LOW] {app} collected less than 50% of target samples")
            
            # Break between apps
            time.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("\n[STOP] Interrupted by user")
            # Save progress before exit
            with open(progress_file, "w") as f:
                json.dump(app_results, f, indent=2)
            break
        except Exception as e:
            logger.error(f"[ERROR] {app} failed: {e}")
            failed_apps.append((app, 0))
            app_results[app] = {
                "samples": 0,
                "target": args.samples_per_app,
                "completed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            # Save progress
            with open(progress_file, "w") as f:
                json.dump(app_results, f, indent=2)
            continue
    
    # Save dataset
    collector.save_dataset()
    collector.export_for_training()
    
    # Summary
    elapsed = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info("Collection Summary")
    logger.info("="*60)
    logger.info(f"Total samples: {total_samples}")
    logger.info(f"Target samples: {len(apps) * args.samples_per_app}")
    logger.info(f"Success rate: {(total_samples / (len(apps) * args.samples_per_app) * 100):.1f}%")
    logger.info(f"Total time: {elapsed/60:.1f} minutes")
    if elapsed > 0 and total_samples > 0:
        logger.info(f"Rate: {total_samples/(elapsed/60):.1f} samples/minute")
    logger.info(f"Output: {collector.output_dir}")
    
    if failed_apps:
        logger.warning("\n[WARNING] Some apps had low collection rates:")
        for app, samples in failed_apps:
            logger.warning(f"  - {app}: {samples}/{args.samples_per_app} samples")
    
    logger.info("="*60)
    
    # Create summary report
    summary_file = Path(args.output) / "COLLECTION_REPORT.txt"
    with open(summary_file, "w") as f:
        f.write("="*60 + "\n")
        f.write("AUTOMATED COLLECTION REPORT\n")
        f.write("="*60 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Time: {elapsed/60:.1f} minutes\n")
        f.write(f"Total Samples: {total_samples}\n")
        f.write(f"Target: {len(apps) * args.samples_per_app}\n")
        f.write(f"Success Rate: {(total_samples / (len(apps) * args.samples_per_app) * 100):.1f}%\n\n")
        
        f.write("Per-App Results:\n")
        f.write("-"*60 + "\n")
        for app in apps:
            if app in app_results:
                result = app_results[app]
                status = "[OK]" if result.get("completed") else "[PARTIAL]"
                f.write(f"{status} {app}: {result['samples']}/{result['target']} samples\n")
            else:
                f.write(f"[SKIP] {app}: Not processed\n")
        
        if failed_apps:
            f.write("\n" + "-"*60 + "\n")
            f.write("Apps needing retry:\n")
            for app, samples in failed_apps:
                f.write(f"  - {app} (got {samples} samples)\n")
    
    logger.info(f"\n[REPORT] Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
