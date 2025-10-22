"""
Notion executor for workspace and database management.
"""
from __future__ import annotations

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class NotionConfig:
    token: str
    version: str = "2022-06-28"


class NotionExecutor:
    def __init__(self, cfg: NotionConfig):
        self.cfg = cfg
        self.headers = {
            "Authorization": f"Bearer {cfg.token}",
            "Notion-Version": cfg.version,
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.notion.com/v1"

    def search(self, query: str = "", filter_type: str | None = None, limit: int = 100) -> Dict[str, Any]:
        """Search for pages and databases."""
        try:
            data = {
                "page_size": min(limit, 100)
            }
            
            if query:
                data["query"] = query
            
            if filter_type:
                data["filter"] = {"property": "object", "value": filter_type}
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            results = response.json()
            
            return {
                "action": "notion.search",
                "success": True,
                "count": len(results.get("results", [])),
                "has_more": results.get("has_more", False),
                "results": [{
                    "id": r["id"],
                    "type": r["object"],
                    "title": self._extract_title(r),
                    "url": r.get("url", ""),
                    "created_time": r.get("created_time", ""),
                    "last_edited_time": r.get("last_edited_time", "")
                } for r in results.get("results", [])]
            }
        except Exception as e:
            return {
                "action": "notion.search",
                "success": False,
                "error": str(e)
            }

    def create_page(self, parent_id: str, title: str, content: List[Dict] | None = None,
                   properties: Dict | None = None) -> Dict[str, Any]:
        """Create a new page."""
        try:
            data = {
                "parent": {"page_id": parent_id} if not parent_id.startswith("database") else {"database_id": parent_id},
                "properties": {
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                }
            }
            
            if properties:
                data["properties"].update(properties)
            
            if content:
                data["children"] = content
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            page = response.json()
            
            return {
                "action": "notion.create_page",
                "success": True,
                "id": page["id"],
                "url": page["url"],
                "title": title
            }
        except Exception as e:
            return {
                "action": "notion.create_page",
                "success": False,
                "error": str(e)
            }

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page details."""
        try:
            response = requests.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers
            )
            response.raise_for_status()
            page = response.json()
            
            return {
                "action": "notion.get_page",
                "success": True,
                "id": page["id"],
                "title": self._extract_title(page),
                "url": page.get("url", ""),
                "properties": page.get("properties", {}),
                "created_time": page.get("created_time", ""),
                "last_edited_time": page.get("last_edited_time", "")
            }
        except Exception as e:
            return {
                "action": "notion.get_page",
                "success": False,
                "error": str(e)
            }

    def append_blocks(self, block_id: str, blocks: List[Dict]) -> Dict[str, Any]:
        """Append blocks to a page or block."""
        try:
            data = {"children": blocks}
            
            response = requests.patch(
                f"{self.base_url}/blocks/{block_id}/children",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "action": "notion.append_blocks",
                "success": True,
                "block_id": block_id,
                "added_count": len(result.get("results", []))
            }
        except Exception as e:
            return {
                "action": "notion.append_blocks",
                "success": False,
                "error": str(e)
            }

    def query_database(self, database_id: str, filter_obj: Dict | None = None,
                      sorts: List[Dict] | None = None, limit: int = 100) -> Dict[str, Any]:
        """Query a database."""
        try:
            data = {"page_size": min(limit, 100)}
            
            if filter_obj:
                data["filter"] = filter_obj
            if sorts:
                data["sorts"] = sorts
            
            response = requests.post(
                f"{self.base_url}/databases/{database_id}/query",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            results = response.json()
            
            return {
                "action": "notion.query_database",
                "success": True,
                "count": len(results.get("results", [])),
                "has_more": results.get("has_more", False),
                "results": [{
                    "id": r["id"],
                    "title": self._extract_title(r),
                    "properties": r.get("properties", {}),
                    "url": r.get("url", "")
                } for r in results.get("results", [])]
            }
        except Exception as e:
            return {
                "action": "notion.query_database",
                "success": False,
                "error": str(e)
            }

    def create_database(self, parent_id: str, title: str, properties: Dict) -> Dict[str, Any]:
        """Create a new database."""
        try:
            data = {
                "parent": {"page_id": parent_id},
                "title": [{"text": {"content": title}}],
                "properties": properties
            }
            
            response = requests.post(
                f"{self.base_url}/databases",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            db = response.json()
            
            return {
                "action": "notion.create_database",
                "success": True,
                "id": db["id"],
                "url": db["url"],
                "title": title
            }
        except Exception as e:
            return {
                "action": "notion.create_database",
                "success": False,
                "error": str(e)
            }

    def _extract_title(self, obj: Dict) -> str:
        """Extract title from a Notion object."""
        try:
            # For pages
            if "properties" in obj:
                for prop_name, prop_value in obj["properties"].items():
                    if prop_value.get("type") == "title" and prop_value.get("title"):
                        return prop_value["title"][0]["text"]["content"]
            
            # For databases
            if "title" in obj and isinstance(obj["title"], list) and obj["title"]:
                return obj["title"][0]["text"]["content"]
            
            return "Untitled"
        except Exception:
            return "Untitled"
