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
from ..memory.session_continuity import get_session_continuity

# Try to import enhanced voice
try:
    from .enhanced_voice import EnhancedVoiceAgent, EnhancedVoiceConfig
    ENHANCED_VOICE_AVAILABLE = True
except ImportError:
    ENHANCED_VOICE_AVAILABLE = False


@dataclass
class ChatAgentConfig:
    voice_enabled: bool = True
    continuous_listening: bool = False
    voice_activation_keywords: list[str] = None
    auto_speak_responses: bool = True
    text_fallback: bool = True
    use_enhanced_voice: bool = True  # Use new Edge TTS + wake word
    conversation_config: ConversationConfig = None
    voice_config: VoiceConfig = None


class ChatAgent:
    def __init__(self, cfg: ChatAgentConfig | None = None):
        self.cfg = cfg or ChatAgentConfig()
        if self.cfg.voice_activation_keywords is None:
            self.cfg.voice_activation_keywords = ["hey kayas", "kayas", "assistant"]
        
        # Initialize components
        self.conversation = ConversationManager(self.cfg.conversation_config)
        
        # Try enhanced voice first
        self.enhanced_voice: Optional[EnhancedVoiceAgent] = None
        self.voice_agent: Optional[VoiceAgent] = None
        
        if self.cfg.voice_enabled:
            if self.cfg.use_enhanced_voice and ENHANCED_VOICE_AVAILABLE:
                try:
                    self.enhanced_voice = EnhancedVoiceAgent()
                    print("[ChatAgent] Enhanced voice initialized (Edge TTS + Wake Word)")
                except Exception as e:
                    print(f"[ChatAgent] Enhanced voice failed: {e}, falling back to legacy")
            
            if not self.enhanced_voice:
                try:
                    self.voice_agent = VoiceAgent(self.cfg.voice_config)
                    print("[ChatAgent] Legacy voice agent initialized")
                except Exception as e:
                    print(f"[ChatAgent] Failed to initialize voice: {e}")
                    if not self.cfg.text_fallback:
                        raise
        
        self._listening = False
        self._speaking = False
        self._wake_word_detected = False
        
        # Initialize session continuity
        self._session = None
        try:
            # Get memory and profile from conversation manager's direct agent
            memory = getattr(self.conversation.agent, 'memory', None)
            profile_mgr = None
            if hasattr(self.conversation.agent, 'smart_executor'):
                se = self.conversation.agent.smart_executor
                if se:
                    profile_mgr = getattr(se, 'profile_manager', None)
            self._session = get_session_continuity(memory, profile_mgr)
        except Exception as e:
            print(f"[ChatAgent] Session continuity init: {e}")

    def _get_greeting(self) -> str:
        """Get personalized greeting based on session history."""
        if self._session:
            try:
                return self._session.generate_welcome_message()
            except Exception as e:
                print(f"[ChatAgent] Greeting generation failed: {e}")
        
        # Fallback
        return ("Hello! I'm Kayas, your AI assistant. I can help you with desktop automation, "
                "web browsing, managing your calendar, and much more. How can I assist you today?")

    def _speak(self, text: str) -> None:
        """Speak using the best available TTS."""
        if self.enhanced_voice:
            self.enhanced_voice.speak(text)
        elif self.voice_agent:
            self.voice_agent.speak(text)
        else:
            print(f"[TTS] {text}")

    def _listen(self, timeout: float = 10.0) -> Optional[str]:
        """Listen using the best available STT."""
        if self.enhanced_voice:
            return self.enhanced_voice.listen(timeout)
        elif self.voice_agent:
            return self.voice_agent.listen_once(timeout)
        return None
    
    def _listen_with_confirmation(self, timeout: float = 10.0) -> Optional[str]:
        """
        Listen with confirmation for low-confidence transcriptions.
        
        If confidence is below threshold, asks user to confirm.
        """
        if not self.enhanced_voice:
            return self._listen(timeout)
        
        result = self.enhanced_voice.listen_with_confidence(timeout)
        if not result:
            return None
        
        text, confidence = result
        
        # Check if we need confirmation
        if confidence < self.enhanced_voice.config.low_confidence_threshold:
            if self.enhanced_voice.config.ask_confirmation_on_low:
                # Ask for confirmation
                self._speak(f"Did you say: {text}?")
                print("   [Confirming - say 'yes', 'no', or repeat your message]")
                
                # Listen for confirmation
                confirm_result = self.enhanced_voice.listen_with_confidence(timeout=5.0)
                if confirm_result:
                    confirm_text, _ = confirm_result
                    confirm_lower = confirm_text.lower().strip()
                    
                    if confirm_lower in ['yes', 'yeah', 'yep', 'correct', 'right', 'that is correct']:
                        return text
                    elif confirm_lower in ['no', 'nope', 'wrong', 'not']:
                        self._speak("Sorry, please say it again.")
                        return self._listen(timeout)
                    else:
                        # They repeated or said something different, use that
                        return confirm_text
        
        return text

    def start_voice_mode(self):
        """Start voice interaction mode."""
        # Check which voice system is available
        if self.enhanced_voice:
            availability = self.enhanced_voice.is_available()
            print("Enhanced voice mode starting...")
            print("Available components:", availability)
        elif self.voice_agent:
            availability = self.voice_agent.is_available()
            print("Voice mode starting...")
            print("Available components:", availability)
        else:
            print("No voice agent available")
            return False
            
        if not any(availability.values()):
            print("No voice components available")
            return False
        
        # Initial greeting - personalized based on session history
        greeting = self._get_greeting()
        
        print(f"\nKayas: {greeting}")
        if self.cfg.auto_speak_responses:
            self._speak(greeting)
        
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
        
        # If we have enhanced voice with wake word detection, use it
        if self.enhanced_voice:
            def on_wake_detected():
                """Called when wake word is detected."""
                self._wake_word_detected = True
                self._speak("Yes? How can I help?")
                
                # Listen for command
                command = self._listen(timeout=10.0)
                if command:
                    text_lower = command.lower()
                    
                    # Check for stop command
                    if any(stop_word in text_lower for stop_word in ["stop listening", "exit", "quit"]):
                        self._listening = False
                        self._speak("Goodbye! Voice mode deactivated.")
                        return
                    
                    self._process_voice_command(command)
                
                self._wake_word_detected = False
            
            self._listening = True
            self.enhanced_voice.start_wake_word_listening(on_wake_detected)
            
            try:
                while self._listening:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.enhanced_voice.stop_wake_word_listening()
                self._listening = False
            return
        
        # Fallback to legacy voice agent
        def voice_callback(text: str):
            if self._speaking:
                return  # Ignore input while speaking
                
            text_lower = text.lower()
            
            # Check for stop command
            if any(stop_word in text_lower for stop_word in ["stop listening", "exit", "quit"]):
                if self.voice_agent:
                    self.voice_agent.stop_continuous_listening()
                self._listening = False
                goodbye = "Goodbye! Voice mode deactivated."
                print(goodbye)
                self._speak(goodbye)
                return
            
            # Check for wake word with fuzzy matching to handle pronunciation variations
            wake_detected = False
            matched_keyword = None
            
            # First try exact substring match
            for keyword in self.cfg.voice_activation_keywords:
                if keyword in text_lower:
                    wake_detected = True
                    matched_keyword = keyword
                    break
            
            # If no exact match, try fuzzy matching for similar sounds
            if not wake_detected:
                import difflib
                # Split into words and check each
                words = text_lower.split()
                for word in words:
                    for keyword in self.cfg.voice_activation_keywords:
                        # Check similarity (handles Kaya, Kyaz, Chaos, etc.)
                        similarity = difflib.SequenceMatcher(None, word, keyword.replace(" ", "")).ratio()
                        if similarity > 0.6:  # 60% similar
                            wake_detected = True
                            matched_keyword = keyword
                            break
                    if wake_detected:
                        break
            
            if wake_detected or self._wake_word_detected:
                # Remove wake word from command
                command = text
                for keyword in self.cfg.voice_activation_keywords:
                    command = command.replace(keyword, "").strip()
                
                # Also remove the fuzzy matched word if found
                if matched_keyword and not any(kw in text_lower for kw in self.cfg.voice_activation_keywords):
                    # Remove the word that matched fuzzily
                    words = command.split()
                    filtered_words = []
                    for word in words:
                        is_wake = False
                        for keyword in self.cfg.voice_activation_keywords:
                            similarity = difflib.SequenceMatcher(None, word.lower(), keyword.replace(" ", "")).ratio()
                            if similarity > 0.6:
                                is_wake = True
                                break
                        if not is_wake:
                            filtered_words.append(word)
                    command = " ".join(filtered_words).strip()
                
                if command:  # If there's a command after the wake word
                    self._process_voice_command(command)
                    self._wake_word_detected = False
                else:
                    # Just wake word, wait for command
                    self._wake_word_detected = True
                    self._speak("Yes? How can I help you?")
        
        self._listening = True
        if self.voice_agent:
            self.voice_agent.start_continuous_listening(voice_callback)
        
        # Keep the main thread alive
        try:
            while self._listening:
                time.sleep(0.1)
        except KeyboardInterrupt:
            if self.voice_agent:
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
                    # Voice input with confirmation for uncertain transcriptions
                    print("Listening... speak now")
                    text = self._listen_with_confirmation(timeout=15.0)
                    if text:
                        self._process_voice_command(text)
                    else:
                        print("No speech detected")
                        
            except KeyboardInterrupt:
                break
        
        goodbye = "Goodbye!"
        print(goodbye)
        if self.cfg.auto_speak_responses:
            self._speak(goodbye)

    def _process_voice_command(self, text: str):
        """Process a voice command."""
        print(f"\nYou said: {text}")
        
        # Check for correction patterns and auto-learn
        self._check_for_correction(text)
        
        self._process_command(text)
    
    def _check_for_correction(self, text: str):
        """
        Detect when user is correcting a transcription error and learn from it.
        
        Patterns:
        - "not X, I mean Y" / "not X, I said Y" 
        - "I said Y, not X"
        - "it's Y not X"
        """
        if not self.enhanced_voice:
            return
        
        import re
        text_lower = text.lower()
        
        # Pattern: "not X, I mean/said Y" or "not X I mean Y"
        match = re.search(r"not\s+(\w+)[,.]?\s*i\s*(?:mean|said|meant)\s+(\w+)", text_lower)
        if match:
            wrong, right = match.group(1), match.group(2)
            self.enhanced_voice.learn_correction(wrong, right.capitalize())
            print(f"   [Auto-learned] Will replace '{wrong}' with '{right.capitalize()}' in future")
            return
        
        # Pattern: "I said/mean Y, not X"
        match = re.search(r"i\s*(?:said|mean|meant)\s+(\w+)[,.]?\s*not\s+(\w+)", text_lower)
        if match:
            right, wrong = match.group(1), match.group(2)
            self.enhanced_voice.learn_correction(wrong, right.capitalize())
            print(f"   [Auto-learned] Will replace '{wrong}' with '{right.capitalize()}' in future")
            return
        
        # Pattern: "it's Y not X" or "its Y not X"
        match = re.search(r"it'?s\s+(\w+)[,.]?\s*not\s+(\w+)", text_lower)
        if match:
            right, wrong = match.group(1), match.group(2)
            self.enhanced_voice.learn_correction(wrong, right.capitalize())
            print(f"   [Auto-learned] Will replace '{wrong}' with '{right.capitalize()}' in future")
            return
        
        # Pattern: spelling out "A B D U S" -> learn "abdus"
        match = re.search(r"([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s*([a-z])?", text_lower)
        if match:
            letters = [g for g in match.groups() if g]
            if len(letters) >= 4:
                spelled_word = "".join(letters).capitalize()
                # Look for what they might be correcting (word before the spelling)
                pre_match = re.search(r"(\w+)\s+[a-z]\s+[a-z]\s+[a-z]", text_lower)
                if pre_match:
                    wrong_word = pre_match.group(1)
                    if wrong_word not in ['is', 'its', 'the', 'not', 'and', 'mean', 'said']:
                        self.enhanced_voice.learn_correction(wrong_word, spelled_word)
                        self.enhanced_voice.add_known_name(spelled_word)
                        print(f"   [Auto-learned] Will replace '{wrong_word}' with '{spelled_word}' in future")
        
        # Also extract any capitalized names from the text for context
        self._extract_names_from_text(text)
    
    def _extract_names_from_text(self, text: str):
        """Extract potential names from text and add to known names."""
        if not self.enhanced_voice:
            return
        
        import re
        # Find capitalized words that might be names
        # Patterns: "to Abdul", "from Abdul", "tell Abdul", "message Abdul"
        name_patterns = [
            r"(?:to|from|tell|message|call|text|contact|ask)\s+([A-Z][a-z]+)",
            r"(?:said|says|told|asked)\s+([A-Z][a-z]+)",
            r"([A-Z][a-z]+)\s+(?:said|says|told|asked)",
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for name in matches:
                if len(name) > 2 and name.lower() not in ['the', 'and', 'but', 'yes', 'not']:
                    self.enhanced_voice.add_known_name(name)

    def _process_text_command(self, text: str):
        """Process a text command."""
        print(f"\nYou typed: {text}")
        self._process_command(text)
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
            if self.cfg.auto_speak_responses:
                self._speak(response)
                
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            print(f"\nError: {error_msg}")
            if self.cfg.auto_speak_responses:
                self._speak(error_msg)
        finally:
            self._speaking = False

    def start_text_mode(self):
        """Start text-only interaction mode."""
        print("Text mode active. Type your messages below.")
        print("Type 'quit' to exit.\n")
        
        # Initial greeting - personalized based on session history
        greeting = self._get_greeting()
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
            "enhanced_voice": self.enhanced_voice is not None,
        }
        
        if self.enhanced_voice:
            status["voice_availability"] = self.enhanced_voice.is_available()
        elif self.voice_agent:
            status["voice_availability"] = self.voice_agent.is_available()
        
        return status

    def shutdown(self):
        """Shutdown the chat agent."""
        if self.enhanced_voice:
            self.enhanced_voice.stop_wake_word_listening()
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