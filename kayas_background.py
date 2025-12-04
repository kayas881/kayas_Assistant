#!/usr/bin/env python3
"""
Kayas Background Service - Always-on voice assistant.
Listens for "Kayas" wake word and processes commands in the background.
"""
import sys
import os
from pathlib import Path

# Fix COM threading for pywinauto - MUST be before any imports
if sys.platform == "win32":
    os.environ.setdefault('PYWINAUTO_COINIT_FLAGS', '0')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.voice.chat_agent import ChatAgent, ChatAgentConfig


def main():
    print("=" * 80)
    print("💬 KAYAS CHAT AGENT")
    print("=" * 80)
    print()
    print("Starting text-based assistant...")
    print("Type your commands and press Enter.")
    print()
    print("Examples:")
    print("  - 'Create a todo list'")
    print("  - 'Open Chrome and search for AI news'")
    print("  - 'Play some music'")
    print()
    print("Type 'quit' or 'exit' to shut down.")
    print()
    print("=" * 80)
    print()
    
    # Configure for text mode
    config = ChatAgentConfig(
        voice_enabled=False,  # Text only
        continuous_listening=False,
        auto_speak_responses=False,
    )
    
    agent = ChatAgent(config)
    
    try:
        # Start text mode
        agent.start_text_mode()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Kayas...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        agent.shutdown()
        print("✅ Service stopped. Goodbye!")


if __name__ == "__main__":
    main()
