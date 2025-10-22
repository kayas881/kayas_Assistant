"""
Trello executor for board and card management.
"""
from __future__ import annotations

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class TrelloConfig:
    api_key: str
    token: str


class TrelloExecutor:
    def __init__(self, cfg: TrelloConfig):
        self.cfg = cfg
        self.base_url = "https://api.trello.com/1"
        self.auth_params = {
            "key": cfg.api_key,
            "token": cfg.token
        }

    def list_boards(self, filter_type: str = "open") -> Dict[str, Any]:
        """List all boards."""
        try:
            response = requests.get(
                f"{self.base_url}/members/me/boards",
                params={**self.auth_params, "filter": filter_type}
            )
            response.raise_for_status()
            boards = response.json()
            
            return {
                "action": "trello.list_boards",
                "success": True,
                "count": len(boards),
                "boards": [{
                    "id": b["id"],
                    "name": b["name"],
                    "url": b["url"],
                    "closed": b.get("closed", False),
                    "desc": b.get("desc", "")
                } for b in boards]
            }
        except Exception as e:
            return {
                "action": "trello.list_boards",
                "success": False,
                "error": str(e)
            }

    def create_board(self, name: str, desc: str = "", default_lists: bool = True) -> Dict[str, Any]:
        """Create a new board."""
        try:
            data = {
                **self.auth_params,
                "name": name,
                "desc": desc,
                "defaultLists": str(default_lists).lower()
            }
            
            response = requests.post(
                f"{self.base_url}/boards",
                params=data
            )
            response.raise_for_status()
            board = response.json()
            
            return {
                "action": "trello.create_board",
                "success": True,
                "id": board["id"],
                "name": board["name"],
                "url": board["url"]
            }
        except Exception as e:
            return {
                "action": "trello.create_board",
                "success": False,
                "error": str(e)
            }

    def get_lists(self, board_id: str) -> Dict[str, Any]:
        """Get all lists on a board."""
        try:
            response = requests.get(
                f"{self.base_url}/boards/{board_id}/lists",
                params=self.auth_params
            )
            response.raise_for_status()
            lists = response.json()
            
            return {
                "action": "trello.get_lists",
                "success": True,
                "count": len(lists),
                "lists": [{
                    "id": l["id"],
                    "name": l["name"],
                    "closed": l.get("closed", False)
                } for l in lists]
            }
        except Exception as e:
            return {
                "action": "trello.get_lists",
                "success": False,
                "error": str(e)
            }

    def create_card(self, list_id: str, name: str, desc: str = "",
                   due: str | None = None, labels: List[str] | None = None) -> Dict[str, Any]:
        """Create a new card."""
        try:
            data = {
                **self.auth_params,
                "idList": list_id,
                "name": name,
                "desc": desc
            }
            
            if due:
                data["due"] = due
            if labels:
                data["idLabels"] = ",".join(labels)
            
            response = requests.post(
                f"{self.base_url}/cards",
                params=data
            )
            response.raise_for_status()
            card = response.json()
            
            return {
                "action": "trello.create_card",
                "success": True,
                "id": card["id"],
                "name": card["name"],
                "url": card["url"]
            }
        except Exception as e:
            return {
                "action": "trello.create_card",
                "success": False,
                "error": str(e)
            }

    def get_cards(self, list_id: str | None = None, board_id: str | None = None) -> Dict[str, Any]:
        """Get cards from a list or board."""
        try:
            if list_id:
                url = f"{self.base_url}/lists/{list_id}/cards"
            elif board_id:
                url = f"{self.base_url}/boards/{board_id}/cards"
            else:
                return {
                    "action": "trello.get_cards",
                    "success": False,
                    "error": "Either list_id or board_id must be provided"
                }
            
            response = requests.get(url, params=self.auth_params)
            response.raise_for_status()
            cards = response.json()
            
            return {
                "action": "trello.get_cards",
                "success": True,
                "count": len(cards),
                "cards": [{
                    "id": c["id"],
                    "name": c["name"],
                    "desc": c.get("desc", ""),
                    "url": c["url"],
                    "due": c.get("due"),
                    "labels": [l["name"] for l in c.get("labels", [])]
                } for c in cards]
            }
        except Exception as e:
            return {
                "action": "trello.get_cards",
                "success": False,
                "error": str(e)
            }

    def update_card(self, card_id: str, name: str | None = None, desc: str | None = None,
                   list_id: str | None = None, due: str | None = None) -> Dict[str, Any]:
        """Update a card."""
        try:
            data = {**self.auth_params}
            
            if name:
                data["name"] = name
            if desc is not None:
                data["desc"] = desc
            if list_id:
                data["idList"] = list_id
            if due is not None:
                data["due"] = due
            
            response = requests.put(
                f"{self.base_url}/cards/{card_id}",
                params=data
            )
            response.raise_for_status()
            card = response.json()
            
            return {
                "action": "trello.update_card",
                "success": True,
                "id": card["id"],
                "name": card["name"]
            }
        except Exception as e:
            return {
                "action": "trello.update_card",
                "success": False,
                "error": str(e)
            }

    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        """Add a comment to a card."""
        try:
            data = {
                **self.auth_params,
                "text": text
            }
            
            response = requests.post(
                f"{self.base_url}/cards/{card_id}/actions/comments",
                params=data
            )
            response.raise_for_status()
            comment = response.json()
            
            return {
                "action": "trello.add_comment",
                "success": True,
                "id": comment["id"],
                "text": text
            }
        except Exception as e:
            return {
                "action": "trello.add_comment",
                "success": False,
                "error": str(e)
            }
