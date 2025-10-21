#!/usr/bin/env python3
"""
Main entry point for the Kayas AI Assistant with voice capabilities.
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.voice.chat_agent import ChatAgent, ChatAgentConfig
from src.voice.gui import ChatGUI


def main():
    parser = argparse.ArgumentParser(description="Kayas AI Assistant")
    parser.add_argument("--gui", action="store_true", help="Launch GUI interface")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice features")
    parser.add_argument("--continuous", action="store_true", help="Enable continuous listening")
    parser.add_argument("--no-speak", action="store_true", help="Disable text-to-speech")
    
    args = parser.parse_args()
    
    if args.gui:
        # Launch GUI
        try:
            app = ChatGUI()
            app.run()
        except ImportError as e:
            print(f"GUI dependencies not available: {e}")
            print("Try: pip install tkinter (if not included with Python)")
            sys.exit(1)
    else:
        # Launch CLI
        config = ChatAgentConfig(
            voice_enabled=not args.no_voice,
            continuous_listening=args.continuous,
            auto_speak_responses=not args.no_speak,
        )
        
        agent = ChatAgent(config)
        
        try:
            if config.voice_enabled:
                if agent.start_voice_mode():
                    return
            
            # Fallback to text mode
            agent.start_text_mode()
            
        except KeyboardInterrupt:
            pass
        finally:
            agent.shutdown()


if __name__ == "__main__":
    main()