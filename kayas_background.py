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
    print("🎤 KAYAS BACKGROUND SERVICE")
    print("=" * 80)
    print()
    print("Starting always-on voice assistant...")
    print("The assistant will wake up when you say 'Kayas' followed by your command.")
    print()
    print("Examples:")
    print("  - 'Kayas, create a todo list'")
    print("  - 'Kayas, open Chrome and search for AI news'")
    print("  - 'Kayas, play some music'")
    print()
    print("Say 'Kayas, stop listening' to shut down.")
    print("Or press Ctrl+C to exit.")
    print()
    print("=" * 80)
    print()
    
    # Configure for background continuous listening
    config = ChatAgentConfig(
        voice_enabled=True,
        continuous_listening=True,  # Always listening
        auto_speak_responses=True,  # Speak responses
        voice_activation_keywords=["kayas", "hey kayas", "okay kayas"],
    )
    
    agent = ChatAgent(config)
    
    try:
        # Start voice mode with continuous listening
        if not agent.start_voice_mode():
            print("❌ Failed to start voice mode. Check microphone and audio settings.")
            print("\nTroubleshooting:")
            print("1. Ensure microphone is connected and not muted")
            print("2. Install required packages: pip install SpeechRecognition pyaudio pyttsx3")
            print("3. On Windows, you may need to allow microphone access in Privacy settings")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Kayas background service...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        agent.shutdown()
        print("✅ Service stopped. Goodbye!")


if __name__ == "__main__":
    main()
