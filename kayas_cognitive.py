#!/usr/bin/env python3
"""
Cognitive Agent with Async Notifications.

This version runs in a way that allows proactive messages to appear
even while waiting for user input - true JARVIS-like interruption.
"""
import sys
import threading
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.config import ensure_groq_api_key
ensure_groq_api_key()


def proactive_notification_loop(agent, stop_event):
    """Background thread that checks for proactive messages."""
    while not stop_event.is_set():
        try:
            proactive = agent.check_proactive()
            if proactive:
                # Print proactive message (interrupts the input line)
                print(f"\n\n💡 Kayas: {proactive}\n")
                print("You: ", end="", flush=True)
        except Exception:
            pass
        
        # Check every 30 seconds
        stop_event.wait(30)


def main():
    print("=" * 60)
    print("KAYAS - Cognitive Mode (JARVIS-like)")
    print("=" * 60)
    print()
    print("This mode uses a 5-phase cognitive loop:")
    print("PERCEIVE → THINK → DECIDE → ACT → REFLECT")
    print()
    print("Background monitoring is ACTIVE - I'll speak up if I notice something.")
    print()
    
    from src.voice.direct_agent import DirectAgent
    from src.voice.cognitive_agent import CognitiveDirectAgent
    
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
        greeting = "Good morning! ☀️"
    elif 12 <= hour < 17:
        greeting = "Good afternoon! 👋"
    elif 17 <= hour < 21:
        greeting = "Good evening! 🌆"
    else:
        greeting = "Hey there, night owl! 🌙"
    
    print(f"Kayas: {greeting} What's on your mind?")
    print("-" * 60)
    
    # Start proactive notification thread
    stop_event = threading.Event()
    notifier_thread = threading.Thread(
        target=proactive_notification_loop,
        args=(agent, stop_event),
        daemon=True
    )
    notifier_thread.start()
    
    conversation_context = ""
    try:
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break
            
            result = agent.run(user_input, conversation_context)
            print(f"\nKayas: {result['response']}")
            conversation_context = f"User: {user_input}\nAssistant: {result['response']}\n"
            
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    finally:
        stop_event.set()
        agent.shutdown()


if __name__ == "__main__":
    main()
