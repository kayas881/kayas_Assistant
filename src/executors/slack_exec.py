from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import json

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

from ..agent.config import slack_config


@dataclass
class SlackConfig:
    bot_token: str
    user_token: Optional[str] = None


class SlackExecutor:
    def __init__(self, cfg: SlackConfig):
        self.cfg = cfg
        self.client = None
        if SLACK_AVAILABLE and cfg.bot_token:
            self.client = WebClient(token=cfg.bot_token)

    def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> Dict:
        """Send a message to a Slack channel"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            
            return {
                "action": "slack.send_message",
                "channel": channel,
                "message_ts": response["ts"],
                "permalink": response.get("permalink", ""),
                "text": text
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to send message: {str(e)}"}

    def list_channels(self, types: str = "public_channel,private_channel", limit: int = 100) -> Dict:
        """List Slack channels"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            response = self.client.conversations_list(
                types=types,
                limit=limit
            )
            
            channels = []
            for channel in response["channels"]:
                channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel.get("is_private", False),
                    "is_member": channel.get("is_member", False),
                    "num_members": channel.get("num_members", 0),
                    "purpose": channel.get("purpose", {}).get("value", ""),
                    "topic": channel.get("topic", {}).get("value", "")
                })
            
            return {
                "action": "slack.list_channels",
                "channels": channels,
                "count": len(channels)
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to list channels: {str(e)}"}

    def get_user_info(self, user_id: str) -> Dict:
        """Get information about a Slack user"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            response = self.client.users_info(user=user_id)
            user = response["user"]
            
            return {
                "action": "slack.get_user_info",
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "real_name": user.get("real_name", ""),
                    "display_name": user.get("profile", {}).get("display_name", ""),
                    "email": user.get("profile", {}).get("email", ""),
                    "title": user.get("profile", {}).get("title", ""),
                    "status": user.get("profile", {}).get("status_text", ""),
                    "timezone": user.get("tz", ""),
                    "is_admin": user.get("is_admin", False),
                    "is_bot": user.get("is_bot", False)
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to get user info: {str(e)}"}

    def get_channel_history(self, channel: str, limit: int = 50, latest: Optional[str] = None) -> Dict:
        """Get recent messages from a channel"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            response = self.client.conversations_history(
                channel=channel,
                limit=limit,
                latest=latest
            )
            
            messages = []
            for message in response["messages"]:
                messages.append({
                    "ts": message["ts"],
                    "user": message.get("user", ""),
                    "text": message.get("text", ""),
                    "type": message.get("type", ""),
                    "subtype": message.get("subtype", ""),
                    "thread_ts": message.get("thread_ts", ""),
                    "reply_count": message.get("reply_count", 0)
                })
            
            return {
                "action": "slack.get_channel_history",
                "channel": channel,
                "messages": messages,
                "count": len(messages)
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to get channel history: {str(e)}"}

    def search_messages(self, query: str, count: int = 20) -> Dict:
        """Search for messages across Slack workspace"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            response = self.client.search_messages(
                query=query,
                count=count
            )
            
            matches = []
            for match in response["messages"]["matches"]:
                matches.append({
                    "text": match["text"],
                    "user": match.get("user", ""),
                    "username": match.get("username", ""),
                    "channel": match.get("channel", {}).get("name", ""),
                    "ts": match["ts"],
                    "permalink": match.get("permalink", "")
                })
            
            return {
                "action": "slack.search_messages",
                "query": query,
                "matches": matches,
                "total": response["messages"]["total"]
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to search messages: {str(e)}"}

    def set_status(self, text: str, emoji: str = "", expiration: Optional[int] = None) -> Dict:
        """Set user status"""
        if not SLACK_AVAILABLE or not self.client:
            return {"error": "Slack SDK not available or not authenticated"}
        
        try:
            profile = {
                "status_text": text,
                "status_emoji": emoji
            }
            if expiration:
                profile["status_expiration"] = expiration
            
            response = self.client.users_profile_set(profile=profile)
            
            return {
                "action": "slack.set_status",
                "status_text": text,
                "status_emoji": emoji,
                "success": response["ok"]
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
        except Exception as e:
            return {"error": f"Failed to set status: {str(e)}"}