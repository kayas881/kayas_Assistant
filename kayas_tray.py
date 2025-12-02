#!/usr/bin/env python3
"""
Kayas System Tray Application
Runs Kayas in the background with a system tray icon for easy control.
"""
import sys
import os
import threading
from pathlib import Path

# Fix COM threading
if sys.platform == "win32":
    os.environ.setdefault('PYWINAUTO_COINIT_FLAGS', '0')

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("⚠️ System tray support not available. Install with: pip install pystray pillow")

from src.voice.chat_agent import ChatAgent, ChatAgentConfig


def create_icon_image():
    """Create a simple icon for the system tray."""
    # Create a 64x64 image with a gradient
    size = 64
    image = Image.new('RGB', (size, size), color='#2196F3')
    draw = ImageDraw.Draw(image)
    
    # Draw a simple "K" letter
    draw.text((20, 15), "K", fill='white', font=None)
    
    return image


class KayasTrayApp:
    def __init__(self):
        self.agent = None
        self.agent_thread = None
        self.running = False
        
        # Create icon
        if HAS_TRAY:
            self.icon = pystray.Icon(
                "kayas",
                create_icon_image(),
                "Kayas AI Assistant",
                menu=pystray.Menu(
                    pystray.MenuItem("Status: Starting...", self.show_status, enabled=False),
                    pystray.MenuItem("Open Chat Window", self.open_chat, enabled=False),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Restart", self.restart),
                    pystray.MenuItem("Quit", self.quit_app),
                )
            )
        else:
            self.icon = None

    def start_agent(self):
        """Start the Kayas agent in a background thread."""
        self.running = True
        
        config = ChatAgentConfig(
            voice_enabled=True,
            continuous_listening=True,
            auto_speak_responses=True,
            voice_activation_keywords=["kayas", "hey kayas", "okay kayas"],
        )
        
        self.agent = ChatAgent(config)
        
        def run_voice_mode():
            try:
                if not self.agent.start_voice_mode():
                    print("Failed to start voice mode")
                    self.update_status("Error: Voice mode failed")
            except Exception as e:
                print(f"Agent error: {e}")
                self.update_status(f"Error: {e}")
        
        self.agent_thread = threading.Thread(target=run_voice_mode, daemon=True)
        self.agent_thread.start()
        
        self.update_status("Listening... (Say 'Kayas' + command)")

    def update_status(self, status_text):
        """Update the status menu item."""
        if HAS_TRAY and self.icon:
            self.icon.menu = pystray.Menu(
                pystray.MenuItem(f"Status: {status_text}", self.show_status, enabled=False),
                pystray.MenuItem("Open Chat Window", self.open_chat, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Restart", self.restart),
                pystray.MenuItem("Quit", self.quit_app),
            )

    def show_status(self):
        """Show status (placeholder)."""
        pass

    def open_chat(self):
        """Open chat window (placeholder for future GUI)."""
        pass

    def restart(self):
        """Restart the agent."""
        print("Restarting Kayas...")
        if self.agent:
            self.agent.shutdown()
        self.start_agent()

    def quit_app(self):
        """Quit the application."""
        print("Shutting down Kayas...")
        self.running = False
        if self.agent:
            self.agent.shutdown()
        if HAS_TRAY and self.icon:
            self.icon.stop()

    def run(self):
        """Run the system tray application."""
        print("=" * 80)
        print("🎤 KAYAS SYSTEM TRAY")
        print("=" * 80)
        print()
        print("Starting Kayas in system tray...")
        print("Look for the 'K' icon in your system tray.")
        print()
        print("Say 'Kayas' followed by your command to activate.")
        print("Right-click the tray icon for options.")
        print()
        print("=" * 80)
        print()
        
        # Start the agent
        self.start_agent()
        
        if HAS_TRAY:
            # Run the system tray icon
            self.icon.run()
        else:
            # Fallback: just run in console
            print("Running in console mode (no system tray)...")
            try:
                while self.running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.quit_app()


def main():
    if not HAS_TRAY:
        print("\n⚠️ System tray dependencies not installed.")
        print("For system tray support, install:")
        print("  pip install pystray pillow")
        print("\nFalling back to console mode...")
        print()
        
        # Run without tray
        import subprocess
        subprocess.run([sys.executable, "kayas_background.py"])
        return
    
    app = KayasTrayApp()
    try:
        app.run()
    except KeyboardInterrupt:
        app.quit_app()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
