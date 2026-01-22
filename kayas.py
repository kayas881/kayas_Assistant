#!/usr/bin/env python3
"""
Main entry point for the Kayas AI Assistant with voice capabilities.
"""
import sys
import os
import argparse
from pathlib import Path

# Fix COM threading for pywinauto - MUST be before any imports
if sys.platform == "win32":
    os.environ.setdefault('PYWINAUTO_COINIT_FLAGS', '0')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure Groq API key is available before importing agents
from src.agent.config import ensure_groq_api_key
ensure_groq_api_key()

from src.voice.chat_agent import ChatAgent, ChatAgentConfig
from src.voice.gui import ChatGUI


def main():
    parser = argparse.ArgumentParser(description="Kayas AI Assistant")
    parser.add_argument("--gui", action="store_true", help="Launch GUI interface")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice features")
    parser.add_argument("--continuous", action="store_true", help="Enable continuous listening")
    parser.add_argument("--no-speak", action="store_true", help="Disable text-to-speech")
    parser.add_argument("--cognitive", action="store_true", help="Use JARVIS-like cognitive mode (experimental)")
    parser.add_argument("--voice", action="store_true", help="Enable voice output in cognitive mode")
    
    args = parser.parse_args()
    
    if args.cognitive:
        # Launch cognitive mode (JARVIS-like thinking)
        import threading
        
        print("=" * 60)
        print("KAYAS - Cognitive Mode (JARVIS-like)")
        print("=" * 60)
        print()
        print("This mode uses a 5-phase cognitive loop:")
        print("PERCEIVE → THINK → DECIDE → ACT → REFLECT")
        print()
        print("Background monitoring ACTIVE - I'll speak up if I notice something.")
        print()
        
        from src.voice.direct_agent import DirectAgent
        from src.voice.cognitive_agent import CognitiveDirectAgent
        
        # Initialize TTS if voice mode enabled
        tts = None
        if args.voice:
            try:
                from src.voice.edge_tts import EdgeTTS
                tts = EdgeTTS(voice="jenny")  # Friendly female voice
                print("[Voice] Edge TTS enabled - I'll speak my responses")
            except Exception as e:
                print(f"[Voice] TTS unavailable: {e}")
        
        print("[Setup] Loading executors...")
        direct = DirectAgent()
        agent = CognitiveDirectAgent(
            router=direct.router, 
            smart_executor=direct.smart_executor
        )
        
        print()
        
        # Time-based greeting
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning! What's on your mind?"
        elif 12 <= hour < 17:
            greeting = "Good afternoon! What's on your mind?"
        elif 17 <= hour < 21:
            greeting = "Good evening! What's on your mind?"
        else:
            greeting = "Hey there, night owl! What's on your mind?"
        
        print(f"Kayas: {greeting}")
        if tts:
            tts.speak_async(greeting)
        print("-" * 60)
        
        # Background thread for proactive notifications (interrupt while idle)
        stop_event = threading.Event()
        processing_lock = threading.Lock()  # Prevents proactive during user response
        
        def proactive_loop():
            while not stop_event.is_set():
                try:
                    # Don't interrupt while processing user input
                    if processing_lock.locked():
                        stop_event.wait(5)
                        continue
                    
                    proactive = agent.check_proactive()
                    if proactive and not processing_lock.locked():
                        print(f"\n\n💡 Kayas: {proactive}\n")
                        if tts:
                            tts.speak_async(proactive)
                        print("You: ", end="", flush=True)
                except Exception:
                    pass
                stop_event.wait(30)  # Check every 30 seconds
        
        notifier = threading.Thread(target=proactive_loop, daemon=True)
        notifier.start()
        
        conversation_context = ""
        try:
            while True:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    goodbye = "Goodbye! Take care!"
                    print(f"\nKayas: {goodbye}")
                    if tts:
                        tts.speak(goodbye)
                    break
                
                # User responded - reset ignored count if we had spoken
                if agent.analyst and agent.analyst.last_intervention_message:
                    agent.analyst.mark_responded()
                
                # Lock to prevent proactive messages during response
                with processing_lock:
                    result = agent.run(user_input, conversation_context)
                    response = result['response']
                    print(f"\nKayas: {response}")
                    if tts:
                        tts.speak_async(response)
                    conversation_context = f"User: {user_input}\nAssistant: {response}\n"
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        finally:
            stop_event.set()
            if tts:
                tts.shutdown()
            agent.shutdown()
        return
    
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