"""
GitHub executor for repository management and code operations.
"""
from __future__ import annotations

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class GithubConfig:
    token: str
    username: str = ""
    base_url: str = "https://api.github.com"


class GithubExecutor:
    def __init__(self, cfg: GithubConfig):
        self.cfg = cfg
        self.headers = {
            "Authorization": f"token {cfg.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def list_repos(self, user: str | None = None, org: str | None = None,
                   visibility: str = "all", sort: str = "updated", limit: int = 30) -> Dict[str, Any]:
        """List repositories for a user or organization."""
        try:
            if org:
                url = f"{self.cfg.base_url}/orgs/{org}/repos"
            elif user:
                url = f"{self.cfg.base_url}/users/{user}/repos"
            else:
                url = f"{self.cfg.base_url}/user/repos"
            
            params = {
                "visibility": visibility,
                "sort": sort,
                "per_page": min(limit, 100)
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            repos = response.json()
            
            return {
                "action": "github.list_repos",
                "success": True,
                "count": len(repos),
                "repos": [{
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "description": r.get("description", ""),
                    "url": r["html_url"],
                    "private": r["private"],
                    "stars": r["stargazers_count"],
                    "forks": r["forks_count"],
                    "language": r.get("language"),
                    "updated_at": r["updated_at"]
                } for r in repos]
            }
        except Exception as e:
            return {
                "action": "github.list_repos",
                "success": False,
                "error": str(e)
            }

    def create_repo(self, name: str, description: str = "", private: bool = False,
                   auto_init: bool = True, gitignore_template: str | None = None) -> Dict[str, Any]:
        """Create a new repository."""
        try:
            data = {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init
            }
            
            if gitignore_template:
                data["gitignore_template"] = gitignore_template
            
            response = requests.post(
                f"{self.cfg.base_url}/user/repos",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            repo = response.json()
            
            return {
                "action": "github.create_repo",
                "success": True,
                "name": repo["name"],
                "url": repo["html_url"],
                "clone_url": repo["clone_url"]
            }
        except Exception as e:
            return {
                "action": "github.create_repo",
                "success": False,
                "error": str(e)
            }

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get detailed information about a repository."""
        try:
            response = requests.get(
                f"{self.cfg.base_url}/repos/{owner}/{repo}",
                headers=self.headers
            )
            response.raise_for_status()
            r = response.json()
            
            return {
                "action": "github.get_repo_info",
                "success": True,
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description", ""),
                "url": r["html_url"],
                "clone_url": r["clone_url"],
                "private": r["private"],
                "stars": r["stargazers_count"],
                "forks": r["forks_count"],
                "watchers": r["watchers_count"],
                "language": r.get("language"),
                "size": r["size"],
                "default_branch": r["default_branch"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            }
        except Exception as e:
            return {
                "action": "github.get_repo_info",
                "success": False,
                "error": str(e)
            }

    def list_issues(self, owner: str, repo: str, state: str = "open",
                   labels: List[str] | None = None, limit: int = 30) -> Dict[str, Any]:
        """List issues in a repository."""
        try:
            params = {
                "state": state,
                "per_page": min(limit, 100)
            }
            
            if labels:
                params["labels"] = ",".join(labels)
            
            response = requests.get(
                f"{self.cfg.base_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            issues = response.json()
            
            return {
                "action": "github.list_issues",
                "success": True,
                "count": len(issues),
                "issues": [{
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "url": i["html_url"],
                    "user": i["user"]["login"],
                    "labels": [l["name"] for l in i.get("labels", [])],
                    "created_at": i["created_at"],
                    "updated_at": i["updated_at"]
                } for i in issues if "pull_request" not in i]  # Filter out PRs
            }
        except Exception as e:
            return {
                "action": "github.list_issues",
                "success": False,
                "error": str(e)
            }

    def create_issue(self, owner: str, repo: str, title: str, body: str = "",
                    labels: List[str] | None = None, assignees: List[str] | None = None) -> Dict[str, Any]:
        """Create a new issue."""
        try:
            data = {
                "title": title,
                "body": body
            }
            
            if labels:
                data["labels"] = labels
            if assignees:
                data["assignees"] = assignees
            
            response = requests.post(
                f"{self.cfg.base_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            issue = response.json()
            
            return {
                "action": "github.create_issue",
                "success": True,
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"]
            }
        except Exception as e:
            return {
                "action": "github.create_issue",
                "success": False,
                "error": str(e)
            }

    def create_pr(self, owner: str, repo: str, title: str, head: str, base: str,
                 body: str = "", draft: bool = False) -> Dict[str, Any]:
        """Create a pull request."""
        try:
            data = {
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft
            }
            
            response = requests.post(
                f"{self.cfg.base_url}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            pr = response.json()
            
            return {
                "action": "github.create_pr",
                "success": True,
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
                "state": pr["state"]
            }
        except Exception as e:
            return {
                "action": "github.create_pr",
                "success": False,
                "error": str(e)
            }

    def get_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> Dict[str, Any]:
        """Get the contents of a file from a repository."""
        try:
            response = requests.get(
                f"{self.cfg.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                params={"ref": branch}
            )
            response.raise_for_status()
            data = response.json()
            
            # Decode base64 content
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            
            return {
                "action": "github.get_file_content",
                "success": True,
                "path": path,
                "content": content,
                "size": data["size"],
                "sha": data["sha"]
            }
        except Exception as e:
            return {
                "action": "github.get_file_content",
                "success": False,
                "error": str(e)
            }

    def search_code(self, query: str, limit: int = 30) -> Dict[str, Any]:
        """Search for code across GitHub."""
        try:
            params = {
                "q": query,
                "per_page": min(limit, 100)
            }
            
            response = requests.get(
                f"{self.cfg.base_url}/search/code",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            results = response.json()
            
            return {
                "action": "github.search_code",
                "success": True,
                "total_count": results["total_count"],
                "count": len(results["items"]),
                "results": [{
                    "name": i["name"],
                    "path": i["path"],
                    "repo": i["repository"]["full_name"],
                    "url": i["html_url"]
                } for i in results["items"]]
            }
        except Exception as e:
            return {
                "action": "github.search_code",
                "success": False,
                "error": str(e)
            }
