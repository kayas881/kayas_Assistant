# -*- coding: utf-8 -*-
"""
Profile commands for Kayas.
Allows users to manage their profile and relationships through natural commands.
"""

from typing import Optional, Dict, Any
from ..memory.user_profile import get_profile_manager, ContactRelationship


class ProfileCommands:
    """
    Handle profile and relationship commands.
    
    Commands like:
    - "my name is John"
    - "call me Johnny"
    - "Sarah is my ex"
    - "Mark is my boss"
    - "don't let me text Sarah late at night"
    - "warn me before I message Mike"
    """
    
    def __init__(self):
        self.profile_manager = get_profile_manager()
    
    def process_command(self, text: str) -> Optional[str]:
        """
        Process a potential profile/relationship command.
        Returns response if handled, None if not a profile command.
        """
        text_lower = text.lower().strip()
        
        # Name setting - multiple patterns
        if text_lower.startswith("my name is "):
            name = text[11:].strip().rstrip(".")
            return self.set_name(name)
        
        # Handle "my name's [name]" pattern
        if text_lower.startswith("my name's "):
            name = text[10:].strip().split()[0].rstrip(".,!")  # Get first word
            return self.set_name(name)
        
        # Handle name corrections: "my name is X not Y", "I'm X not Y", "it's X not Y"
        if self._is_name_correction(text_lower):
            return self._handle_name_correction(text)
        
        # Handle "I'm [name]" or "I am [name]"
        if text_lower.startswith("i'm ") or text_lower.startswith("i am "):
            # Check if it looks like a name introduction
            prefix_len = 4 if text_lower.startswith("i'm ") else 5
            rest = text[prefix_len:].strip()
            first_word = rest.split()[0] if rest else ""
            # Only treat as name if it's capitalized and not a common word
            if first_word and first_word[0].isupper() and first_word.lower() not in ["going", "trying", "working", "looking", "doing", "busy", "fine", "good", "okay", "here", "back"]:
                return self.set_name(first_word.rstrip(".,!"))
        
        if text_lower.startswith("call me "):
            nickname = text[8:].strip().rstrip(".")
            return self.set_nickname(nickname)
        
        # Relationship setting patterns
        # "[Name] is my [relationship]"
        if " is my " in text_lower:
            return self._parse_relationship(text)
        
        # Caution commands
        if "don't let me" in text_lower or "dont let me" in text_lower:
            return self._parse_caution_command(text)
        
        if text_lower.startswith("warn me before"):
            return self._parse_warning_command(text)
        
        # Goal setting
        if text_lower.startswith("i want to ") or text_lower.startswith("i'm trying to "):
            return self._add_goal(text)
        
        # Show profile
        if text_lower in ["who am i", "what do you know about me", "my profile"]:
            return self.show_profile()
        
        # Show contacts
        if text_lower in ["who do i know", "my contacts", "show relationships"]:
            return self.show_contacts()
        
        return None
    
    def _is_name_correction(self, text_lower: str) -> bool:
        """Check if this is a name correction statement."""
        correction_patterns = [
            "my name's",
            "my name is",
            "i'm ",
            "i am ",
            "it's ",
            "its ",
        ]
        negation_words = [" not ", " isn't ", " isnt ", " ain't "]
        
        has_name_intro = any(p in text_lower for p in correction_patterns)
        has_negation = any(n in text_lower for n in negation_words)
        
        return has_name_intro and has_negation
    
    def _handle_name_correction(self, text: str) -> str:
        """Handle name corrections like 'My name's Ayan not Johnny'."""
        text_lower = text.lower()
        
        # Find the correct name (before "not")
        # Pattern: "[intro] [correct_name] not [wrong_name]"
        
        for negation in [" not ", " isn't ", " isnt "]:
            if negation in text_lower:
                before_not = text[:text_lower.index(negation)]
                break
        else:
            return None
        
        # Extract name from before the negation
        # Remove intro phrases
        for intro in ["my name's ", "my name is ", "i'm ", "i am ", "it's ", "its "]:
            if before_not.lower().startswith(intro):
                name_part = before_not[len(intro):].strip()
                break
        else:
            name_part = before_not.strip()
        
        # Get the first word as the name
        correct_name = name_part.split()[0] if name_part else ""
        correct_name = correct_name.strip(".,!").title()
        
        if correct_name:
            self.profile_manager.update_profile(name=correct_name, nickname=correct_name)
            return f"Got it! Your name is {correct_name}. I've updated my memory - won't make that mistake again! 😊"
        
        return None
    
    def set_name(self, name: str) -> str:
        """Set the user's name."""
        self.profile_manager.update_profile(name=name)
        return f"Got it! I'll remember your name is {name}."
    
    def set_nickname(self, nickname: str) -> str:
        """Set what to call the user."""
        self.profile_manager.update_profile(nickname=nickname)
        return f"Okay, I'll call you {nickname} from now on."
    
    def _parse_relationship(self, text: str) -> str:
        """Parse '[Name] is my [relationship]' patterns."""
        # Handle variations: "Sarah is my ex", "My mom is Susan", etc.
        text_lower = text.lower()
        
        # Pattern: [Name] is my [relationship]
        if " is my " in text_lower:
            parts = text.split(" is my ")
            if len(parts) == 2:
                name = parts[0].strip()
                relationship = parts[1].strip().rstrip(".")
                return self._set_relationship(name, relationship)
        
        return "I didn't quite catch that relationship. Try: '[Name] is my [relationship]'"
    
    def _set_relationship(self, name: str, relationship: str) -> str:
        """Set a relationship with a contact."""
        # Check if contact exists
        contact = self.profile_manager.get_contact(name)
        
        if contact:
            contact.relationship_type = relationship
        else:
            contact = ContactRelationship(name=name, relationship_type=relationship)
        
        # Set default flags based on relationship type
        if relationship.lower() in ["ex", "ex-girlfriend", "ex-boyfriend", "ex-wife", "ex-husband"]:
            contact.sentiment = "complicated"
            contact.caution_level = "gentle"
            contact.avoid_late_night = True
            contact.caution_reason = "Ex relationship - might want to think twice"
        
        self.profile_manager.set_contact(contact)
        
        response = f"Noted! {name} is your {relationship}."
        if contact.avoid_late_night:
            response += " I'll keep an eye out for late-night messaging impulses. 😉"
        
        return response
    
    def _parse_caution_command(self, text: str) -> str:
        """Parse commands like 'don't let me text Sarah late at night'."""
        text_lower = text.lower()
        
        # Extract contact name - look for common patterns
        # "don't let me text/message/call [name]..."
        for trigger in ["text ", "message ", "call ", "email ", "contact "]:
            if trigger in text_lower:
                start_idx = text_lower.index(trigger) + len(trigger)
                rest = text[start_idx:]
                
                # Get the name (first word or until common words)
                words = rest.split()
                if words:
                    name = words[0]
                    
                    # Determine caution level
                    if "at all" in text_lower or "ever" in text_lower:
                        level = "block"
                        reason = "You asked me to block messages to this contact"
                    elif "late at night" in text_lower or "after midnight" in text_lower:
                        level = "warn"
                        reason = "Late night messaging restriction"
                        self._set_contact_flag(name, "avoid_late_night", True)
                    else:
                        level = "warn"
                        reason = "You asked me to warn you"
                    
                    contact = self.profile_manager.get_contact(name)
                    if not contact:
                        contact = ContactRelationship(name=name)
                    
                    contact.caution_level = level
                    contact.caution_reason = reason
                    self.profile_manager.set_contact(contact)
                    
                    if level == "block":
                        return f"Okay, I won't let you message {name}. You'll have to tell me to remove this restriction if you change your mind."
                    else:
                        return f"Got it. I'll check in with you before you send anything to {name}."
        
        return "I didn't understand who you want me to watch out for. Try: 'don't let me text [name] late at night'"
    
    def _parse_warning_command(self, text: str) -> str:
        """Parse 'warn me before I message [name]' commands."""
        text_lower = text.lower()
        
        for trigger in ["message ", "text ", "email ", "call ", "contact "]:
            if trigger in text_lower:
                start_idx = text_lower.index(trigger) + len(trigger)
                name = text[start_idx:].split()[0] if text[start_idx:] else ""
                
                if name:
                    contact = self.profile_manager.get_contact(name)
                    if not contact:
                        contact = ContactRelationship(name=name)
                    
                    contact.caution_level = "gentle"
                    self.profile_manager.set_contact(contact)
                    
                    return f"I'll give you a gentle heads-up before sending messages to {name}."
        
        return "Who should I warn you about? Try: 'warn me before I message [name]'"
    
    def _set_contact_flag(self, name: str, flag: str, value: bool) -> None:
        """Set a flag on a contact."""
        contact = self.profile_manager.get_contact(name)
        if not contact:
            contact = ContactRelationship(name=name)
        setattr(contact, flag, value)
        self.profile_manager.set_contact(contact)
    
    def _add_goal(self, text: str) -> str:
        """Add a goal to track."""
        # Extract goal text
        for prefix in ["i want to ", "i'm trying to ", "im trying to "]:
            if text.lower().startswith(prefix):
                goal = text[len(prefix):].strip()
                break
        else:
            goal = text
        
        profile = self.profile_manager.get_profile()
        goals = profile.current_goals or []
        
        if goal not in goals:
            goals.append(goal)
            self.profile_manager.update_profile(current_goals=goals)
            return f"Added to your goals: {goal}. I'll keep this in mind and might suggest things to help!"
        else:
            return "You already have that goal tracked!"
    
    def show_profile(self) -> str:
        """Show the current user profile."""
        profile = self.profile_manager.get_profile()
        
        lines = ["Here's what I know about you:\n"]
        
        if profile.name:
            lines.append(f"• Name: {profile.name}")
        if profile.nickname:
            lines.append(f"• I call you: {profile.nickname}")
        if profile.communication_style:
            lines.append(f"• Communication style: {profile.communication_style}")
        if profile.current_goals:
            lines.append(f"• Goals: {', '.join(profile.current_goals)}")
        if profile.total_interactions:
            lines.append(f"• We've chatted {profile.total_interactions} times")
        
        if len(lines) == 1:
            return "I don't know much about you yet. Tell me things like 'my name is [name]' or 'call me [nickname]'!"
        
        return "\n".join(lines)
    
    def show_contacts(self) -> str:
        """Show all saved contact relationships."""
        contacts = self.profile_manager.get_all_contacts()
        
        if not contacts:
            return "I don't have any relationship info saved. Tell me things like 'Sarah is my sister' to start!"
        
        lines = ["People I know about:\n"]
        
        for contact in contacts:
            line = f"• {contact.name}"
            if contact.relationship_type:
                line += f" ({contact.relationship_type})"
            if contact.caution_level != "none":
                line += f" ⚠️"
            if contact.avoid_late_night:
                line += " 🌙"
            lines.append(line)
        
        lines.append("\n⚠️ = caution flag, 🌙 = no late night messages")
        
        return "\n".join(lines)


# Singleton instance
_profile_commands: Optional[ProfileCommands] = None


def get_profile_commands() -> ProfileCommands:
    """Get the singleton profile commands handler."""
    global _profile_commands
    if _profile_commands is None:
        _profile_commands = ProfileCommands()
    return _profile_commands


def handle_profile_command(text: str) -> Optional[str]:
    """
    Convenience function to check if text is a profile command.
    Returns response if handled, None otherwise.
    """
    return get_profile_commands().process_command(text)
