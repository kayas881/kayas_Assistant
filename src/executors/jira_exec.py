"""
Jira executor for issue and project management.
"""
from __future__ import annotations

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import base64


@dataclass
class JiraConfig:
    url: str  # e.g., "https://yourcompany.atlassian.net"
    email: str
    api_token: str


class JiraExecutor:
    def __init__(self, cfg: JiraConfig):
        self.cfg = cfg
        self.base_url = f"{cfg.url.rstrip('/')}/rest/api/3"
        
        # Create basic auth header
        auth_str = f"{cfg.email}:{cfg.api_token}"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()
        
        self.headers = {
            "Authorization": f"Basic {auth_bytes}",
            "Content-Type": "application/json"
        }

    def search_issues(self, jql: str, max_results: int = 50, fields: List[str] | None = None) -> Dict[str, Any]:
        """Search for issues using JQL."""
        try:
            data = {
                "jql": jql,
                "maxResults": max_results,
                "fields": fields or ["summary", "status", "assignee", "created", "updated"]
            }
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            results = response.json()
            
            return {
                "action": "jira.search_issues",
                "success": True,
                "total": results.get("total", 0),
                "count": len(results.get("issues", [])),
                "issues": [{
                    "key": i["key"],
                    "summary": i["fields"]["summary"],
                    "status": i["fields"]["status"]["name"],
                    "assignee": i["fields"]["assignee"]["displayName"] if i["fields"].get("assignee") else "Unassigned",
                    "created": i["fields"]["created"],
                    "updated": i["fields"]["updated"]
                } for i in results.get("issues", [])]
            }
        except Exception as e:
            return {
                "action": "jira.search_issues",
                "success": False,
                "error": str(e)
            }

    def create_issue(self, project_key: str, summary: str, issue_type: str = "Task",
                    description: str = "", priority: str | None = None,
                    assignee: str | None = None, labels: List[str] | None = None) -> Dict[str, Any]:
        """Create a new issue."""
        try:
            fields = {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type}
            }
            
            if description:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }]
                }
            
            if priority:
                fields["priority"] = {"name": priority}
            
            if assignee:
                fields["assignee"] = {"accountId": assignee}
            
            if labels:
                fields["labels"] = labels
            
            data = {"fields": fields}
            
            response = requests.post(
                f"{self.base_url}/issue",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            issue = response.json()
            
            return {
                "action": "jira.create_issue",
                "success": True,
                "key": issue["key"],
                "id": issue["id"],
                "url": f"{self.cfg.url}/browse/{issue['key']}"
            }
        except Exception as e:
            return {
                "action": "jira.create_issue",
                "success": False,
                "error": str(e)
            }

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details."""
        try:
            response = requests.get(
                f"{self.base_url}/issue/{issue_key}",
                headers=self.headers
            )
            response.raise_for_status()
            issue = response.json()
            
            return {
                "action": "jira.get_issue",
                "success": True,
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "description": self._extract_description(issue["fields"].get("description")),
                "status": issue["fields"]["status"]["name"],
                "priority": issue["fields"]["priority"]["name"] if issue["fields"].get("priority") else None,
                "assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"].get("assignee") else "Unassigned",
                "reporter": issue["fields"]["reporter"]["displayName"] if issue["fields"].get("reporter") else None,
                "created": issue["fields"]["created"],
                "updated": issue["fields"]["updated"],
                "url": f"{self.cfg.url}/browse/{issue['key']}"
            }
        except Exception as e:
            return {
                "action": "jira.get_issue",
                "success": False,
                "error": str(e)
            }

    def update_issue(self, issue_key: str, summary: str | None = None,
                    description: str | None = None, status: str | None = None,
                    assignee: str | None = None) -> Dict[str, Any]:
        """Update an issue."""
        try:
            fields = {}
            
            if summary:
                fields["summary"] = summary
            
            if description is not None:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }]
                }
            
            if assignee is not None:
                fields["assignee"] = {"accountId": assignee} if assignee else None
            
            if fields:
                data = {"fields": fields}
                
                response = requests.put(
                    f"{self.base_url}/issue/{issue_key}",
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
            
            # Handle status transition separately
            if status:
                self._transition_issue(issue_key, status)
            
            return {
                "action": "jira.update_issue",
                "success": True,
                "key": issue_key
            }
        except Exception as e:
            return {
                "action": "jira.update_issue",
                "success": False,
                "error": str(e)
            }

    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        try:
            data = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/issue/{issue_key}/comment",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "action": "jira.add_comment",
                "success": True,
                "id": result["id"],
                "issue_key": issue_key
            }
        except Exception as e:
            return {
                "action": "jira.add_comment",
                "success": False,
                "error": str(e)
            }

    def list_projects(self) -> Dict[str, Any]:
        """List all projects."""
        try:
            response = requests.get(
                f"{self.base_url}/project",
                headers=self.headers
            )
            response.raise_for_status()
            projects = response.json()
            
            return {
                "action": "jira.list_projects",
                "success": True,
                "count": len(projects),
                "projects": [{
                    "key": p["key"],
                    "name": p["name"],
                    "id": p["id"],
                    "type": p.get("projectTypeKey", "")
                } for p in projects]
            }
        except Exception as e:
            return {
                "action": "jira.list_projects",
                "success": False,
                "error": str(e)
            }

    def _transition_issue(self, issue_key: str, status_name: str) -> None:
        """Transition an issue to a new status."""
        # Get available transitions
        response = requests.get(
            f"{self.base_url}/issue/{issue_key}/transitions",
            headers=self.headers
        )
        response.raise_for_status()
        transitions = response.json()["transitions"]
        
        # Find matching transition
        transition_id = None
        for t in transitions:
            if t["to"]["name"].lower() == status_name.lower():
                transition_id = t["id"]
                break
        
        if transition_id:
            data = {"transition": {"id": transition_id}}
            requests.post(
                f"{self.base_url}/issue/{issue_key}/transitions",
                headers=self.headers,
                json=data
            ).raise_for_status()

    def _extract_description(self, desc_obj: Dict | None) -> str:
        """Extract text from Jira's description format."""
        if not desc_obj:
            return ""
        
        try:
            content = desc_obj.get("content", [])
            text_parts = []
            
            for block in content:
                if block.get("type") == "paragraph":
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
            
            return " ".join(text_parts)
        except Exception:
            return ""
