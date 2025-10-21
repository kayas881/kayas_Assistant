"""
Unified chat agent that combines voice, text, and all tool capabilities.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from .voice_agent import VoiceAgent, VoiceConfig
from .conversation import ConversationManager, ConversationConfig


@dataclass
class ChatAgentConfig:
    voice_enabled: bool = True
    continuous_listening: bool = False
    voice_activation_keywords: list[str] = None
    auto_speak_responses: bool = True
    text_fallback: bool = True
    conversation_config: ConversationConfig = None
    voice_config: VoiceConfig = None


class ChatAgent:
    def __init__(self, cfg: ChatAgentConfig | None = None):
        self.cfg = cfg or ChatAgentConfig()
        if self.cfg.voice_activation_keywords is None:
            self.cfg.voice_activation_keywords = ["hey kayas", "kayas", "assistant"]
        
        # Initialize components
        self.conversation = ConversationManager(self.cfg.conversation_config)
        
        self.voice_agent: Optional[VoiceAgent] = None
        if self.cfg.voice_enabled:
            try:
                self.voice_agent = VoiceAgent(self.cfg.voice_config)
                print("Voice agent initialized successfully")
            except Exception as e:
                print(f"Failed to initialize voice agent: {e}")
                if not self.cfg.text_fallback:
                    raise
        
        self._listening = False
        self._speaking = False
        self._wake_word_detected = False

    def start_voice_mode(self):
        """Start voice interaction mode."""
        if not self.voice_agent:
            print("Voice agent not available")
            return False
            
        availability = self.voice_agent.is_available()
        if not any(availability.values()):
            print("No voice components available")
            return False
            
        print("Voice mode starting...")
        print("Available components:", availability)
        
        # Initial greeting
        greeting = ("Hello! I'm Kayas, your AI assistant. I can help you with desktop automation, "
                   "web browsing, managing your calendar, and much more. How can I assist you today?")
        
        print(greeting)
        if self.cfg.auto_speak_responses and self.voice_agent:
            self.voice_agent.speak(greeting)
        
        if self.cfg.continuous_listening:
            self._start_continuous_mode()
        else:
            self._start_push_to_talk_mode()
            
        return True

    def _start_continuous_mode(self):
        """Start continuous listening mode with wake word detection."""
        print("\nContinuous listening mode active.")
        print("Say one of these wake words to activate:")
        for keyword in self.cfg.voice_activation_keywords:
            print(f"  - {keyword}")
        print("Say 'stop listening' to end the session.\n")
        
        def voice_callback(text: str):
            if self._speaking:
                return  # Ignore input while speaking
                
            text_lower = text.lower()
            
            # Check for stop command
            if any(stop_word in text_lower for stop_word in ["stop listening", "exit", "quit"]):
                self.voice_agent.stop_continuous_listening()
                self._listening = False
                goodbye = "Goodbye! Voice mode deactivated."
                print(goodbye)
                if self.voice_agent:
                    self.voice_agent.speak(goodbye)
                return
            
            # Check for wake word
            wake_detected = any(keyword in text_lower for keyword in self.cfg.voice_activation_keywords)
            
            if wake_detected or self._wake_word_detected:
                # Remove wake word from command
                command = text
                for keyword in self.cfg.voice_activation_keywords:
                    command = command.replace(keyword, "").strip()
                
                if command:  # If there's a command after the wake word
                    self._process_voice_command(command)
                    self._wake_word_detected = False
                else:
                    # Just wake word, wait for command
                    self._wake_word_detected = True
                    if self.voice_agent:
                        self.voice_agent.speak("Yes? How can I help you?")
        
        self._listening = True
        self.voice_agent.start_continuous_listening(voice_callback)
        
        # Keep the main thread alive
        try:
            while self._listening:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.voice_agent.stop_continuous_listening()
            self._listening = False

    def _start_push_to_talk_mode(self):
        """Start push-to-talk mode."""
        print("\nPush-to-talk mode active.")
        print("Press Enter to start speaking, or type 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input("\n[Press Enter to speak or type your message]: ").strip()
                
                if user_input.lower() in ["quit", "exit", "bye"]:
                    break
                
                if user_input:
                    # Text input
                    self._process_text_command(user_input)
                else:
                    # Voice input
                    print("Listening... speak now")
                    text = self.voice_agent.listen_once(timeout=10.0)
                    if text:
                        self._process_voice_command(text)
                    else:
                        print("No speech detected")
                        
            except KeyboardInterrupt:
                break
        
        goodbye = "Goodbye!"
        print(goodbye)
        if self.voice_agent and self.cfg.auto_speak_responses:
            self.voice_agent.speak(goodbye)

    def _process_voice_command(self, text: str):
        """Process a voice command."""
        print(f"\nYou said: {text}")
        self._process_command(text)

    def _process_text_command(self, text: str):
        """Process a text command."""
        print(f"\nYou typed: {text}")
        self._process_command(text)

    def _process_command(self, text: str):
        """Process a command (voice or text)."""
        if not text.strip():
            return
            
        try:
            # Set speaking flag to avoid voice feedback loops
            self._speaking = True
            
            # Process with conversation manager
            response = self.conversation.process_user_input(text)
            
            print(f"\nKayas: {response}")
            
            # Speak response if enabled
            if self.cfg.auto_speak_responses and self.voice_agent:
                self.voice_agent.speak(response)
                
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            print(f"\nError: {error_msg}")
            if self.cfg.auto_speak_responses and self.voice_agent:
                self.voice_agent.speak(error_msg)
        finally:
            self._speaking = False

    def start_text_mode(self):
        """Start text-only interaction mode."""
        print("Text mode active. Type your messages below.")
        print("Type 'quit' to exit.\n")
        
        # Initial greeting
        greeting = ("Hello! I'm Kayas, your AI assistant. I can help you with desktop automation, "
                   "web browsing, managing your calendar, and much more. How can I assist you today?")
        print(f"Kayas: {greeting}")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("Kayas: Goodbye!")
                    break
                
                if user_input:
                    self._process_text_command(user_input)
                    
            except KeyboardInterrupt:
                print("\nKayas: Goodbye!")
                break

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the chat agent."""
        status = {
            "voice_enabled": self.cfg.voice_enabled,
            "listening": self._listening,
            "speaking": self._speaking,
            "conversation": self.conversation.get_conversation_summary(),
        }
        
        if self.voice_agent:
            status["voice_availability"] = self.voice_agent.is_available()
        
        return status

    def shutdown(self):
        """Shutdown the chat agent."""
        if self.voice_agent:
            self.voice_agent.stop_continuous_listening()
        self._listening = False
        print("Chat agent shutdown complete")


def main():
    """Main entry point for the chat agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kayas AI Assistant")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice features")
    parser.add_argument("--continuous", action="store_true", help="Enable continuous listening")
    parser.add_argument("--no-speak", action="store_true", help="Disable text-to-speech")
    
    args = parser.parse_args()
    
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