"""
Simple GUI for the chat agent using tkinter.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
from typing import Optional, Dict, Any

from .chat_agent import ChatAgent, ChatAgentConfig
from .voice_agent import VoiceConfig
from .conversation import ConversationConfig


class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kayas AI Assistant")
        self.root.geometry("800x600")
        
        # Initialize chat agent
        config = ChatAgentConfig(
            voice_enabled=True,
            continuous_listening=False,
            auto_speak_responses=True,
            text_fallback=True,
        )
        
        self.chat_agent = ChatAgent(config)
        self.message_queue = queue.Queue()
        
        self._setup_ui()
        self._start_message_processor()
        
        # Initial greeting
        self._add_message("Assistant", 
                         "Hello! I'm Kayas, your AI assistant. I can help you with desktop automation, "
                         "web browsing, managing your calendar, and much more. How can I assist you today?")
        
        if self.chat_agent.voice_agent and self.chat_agent.cfg.auto_speak_responses:
            threading.Thread(target=lambda: self.chat_agent.voice_agent.speak(
                "Hello! I'm Kayas, your AI assistant. How can I help you today?"
            ), daemon=True).start()

    def _setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Kayas AI Assistant", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            width=70, 
            height=25,
            font=("Consolas", 10)
        )
        self.chat_display.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.chat_display.config(state=tk.DISABLED)
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        # Text input
        self.text_input = ttk.Entry(input_frame, font=("Arial", 11))
        self.text_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.text_input.bind("<Return>", self._send_text_message)
        
        # Send button
        self.send_button = ttk.Button(input_frame, text="Send", command=self._send_text_message)
        self.send_button.grid(row=0, column=1)
        
        # Voice button
        self.voice_button = ttk.Button(input_frame, text="🎤 Speak", command=self._start_voice_input)
        self.voice_button.grid(row=0, column=2, padx=(5, 0))
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Voice controls
        self.voice_enabled_var = tk.BooleanVar(value=True)
        voice_checkbox = ttk.Checkbutton(
            control_frame, 
            text="Voice enabled", 
            variable=self.voice_enabled_var,
            command=self._toggle_voice
        )
        voice_checkbox.grid(row=0, column=0, padx=(0, 10))
        
        self.auto_speak_var = tk.BooleanVar(value=True)
        speak_checkbox = ttk.Checkbutton(
            control_frame, 
            text="Auto-speak responses", 
            variable=self.auto_speak_var,
            command=self._toggle_auto_speak
        )
        speak_checkbox.grid(row=0, column=1, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Ready", foreground="green")
        self.status_label.grid(row=0, column=2, padx=(10, 0))
        
        # Update voice button state
        self._update_voice_button()

    def _setup_tags(self):
        """Setup text tags for different message types."""
        self.chat_display.tag_configure("user", foreground="blue", font=("Arial", 10, "bold"))
        self.chat_display.tag_configure("assistant", foreground="green", font=("Arial", 10))
        self.chat_display.tag_configure("system", foreground="gray", font=("Arial", 9, "italic"))

    def _add_message(self, sender: str, message: str, tag: str = None):
        """Add a message to the chat display."""
        self.chat_display.config(state=tk.NORMAL)
        
        if not tag:
            tag = "user" if sender == "You" else "assistant"
        
        # Add message
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        # Scroll to bottom
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _send_text_message(self, event=None):
        """Send a text message."""
        message = self.text_input.get().strip()
        if not message:
            return
            
        self.text_input.delete(0, tk.END)
        self._add_message("You", message)
        
        # Process in background thread
        threading.Thread(
            target=self._process_message,
            args=(message,),
            daemon=True
        ).start()

    def _start_voice_input(self):
        """Start voice input."""
        if not self.chat_agent.voice_agent:
            messagebox.showerror("Error", "Voice agent not available")
            return
            
        self.voice_button.config(text="🎤 Listening...", state=tk.DISABLED)
        self.status_label.config(text="Listening...", foreground="orange")
        
        # Listen in background thread
        threading.Thread(
            target=self._listen_for_voice,
            daemon=True
        ).start()

    def _listen_for_voice(self):
        """Listen for voice input in background thread."""
        try:
            text = self.chat_agent.voice_agent.listen_once(timeout=10.0)
            
            if text:
                # Queue the message for processing
                self.message_queue.put(("voice_received", text))
            else:
                self.message_queue.put(("voice_timeout", None))
                
        except Exception as e:
            self.message_queue.put(("voice_error", str(e)))

    def _process_message(self, message: str):
        """Process a message in background thread."""
        try:
            self.message_queue.put(("processing", None))
            
            # Process with chat agent
            response = self.chat_agent.conversation.process_user_input(message)
            
            # Queue response
            self.message_queue.put(("response", response))
            
            # Speak if enabled
            if (self.auto_speak_var.get() and 
                self.chat_agent.voice_agent and 
                self.chat_agent.cfg.auto_speak_responses):
                self.chat_agent.voice_agent.speak(response)
                
        except Exception as e:
            self.message_queue.put(("error", str(e)))

    def _start_message_processor(self):
        """Start the message processor for handling background events."""
        self._setup_tags()
        self._process_message_queue()

    def _process_message_queue(self):
        """Process messages from the background threads."""
        try:
            while True:
                event_type, data = self.message_queue.get_nowait()
                
                if event_type == "voice_received":
                    self._add_message("You", data)
                    self.voice_button.config(text="🎤 Speak", state=tk.NORMAL)
                    self.status_label.config(text="Processing...", foreground="orange")
                    
                    # Process the voice message
                    threading.Thread(
                        target=self._process_message,
                        args=(data,),
                        daemon=True
                    ).start()
                    
                elif event_type == "voice_timeout":
                    self.voice_button.config(text="🎤 Speak", state=tk.NORMAL)
                    self.status_label.config(text="No speech detected", foreground="red")
                    self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground="green"))
                    
                elif event_type == "voice_error":
                    self.voice_button.config(text="🎤 Speak", state=tk.NORMAL)
                    self.status_label.config(text=f"Voice error: {data}", foreground="red")
                    self.root.after(3000, lambda: self.status_label.config(text="Ready", foreground="green"))
                    
                elif event_type == "processing":
                    self.status_label.config(text="Processing...", foreground="orange")
                    
                elif event_type == "response":
                    self._add_message("Kayas", data)
                    self.status_label.config(text="Ready", foreground="green")
                    
                elif event_type == "error":
                    self._add_message("System", f"Error: {data}", "system")
                    self.status_label.config(text="Error occurred", foreground="red")
                    self.root.after(3000, lambda: self.status_label.config(text="Ready", foreground="green"))
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_message_queue)

    def _toggle_voice(self):
        """Toggle voice features."""
        self.chat_agent.cfg.voice_enabled = self.voice_enabled_var.get()
        self._update_voice_button()

    def _toggle_auto_speak(self):
        """Toggle auto-speak responses."""
        self.chat_agent.cfg.auto_speak_responses = self.auto_speak_var.get()

    def _update_voice_button(self):
        """Update voice button state."""
        if self.voice_enabled_var.get() and self.chat_agent.voice_agent:
            self.voice_button.config(state=tk.NORMAL)
        else:
            self.voice_button.config(state=tk.DISABLED)

    def run(self):
        """Run the GUI."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.chat_agent.shutdown()


def main():
    """Main entry point for the GUI."""
    try:
        app = ChatGUI()
        app.run()
    except Exception as e:
        print(f"GUI error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()