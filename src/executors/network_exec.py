"""
Network executor for HTTP requests, downloads, and network operations.
"""
from __future__ import annotations

import requests
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import json


@dataclass
class NetworkConfig:
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    user_agent: str = "Kayas-AI-Agent/1.0"


class NetworkExecutor:
    def __init__(self, cfg: NetworkConfig | None = None):
        self.cfg = cfg or NetworkConfig()
        self.session = None

    def http_request(self, url: str, method: str = "GET", headers: Dict[str, str] | None = None,
                    data: Any | None = None, json_data: Dict | None = None,
                    params: Dict | None = None, timeout: int | None = None) -> Dict[str, Any]:
        """Make an HTTP request."""
        try:
            headers = headers or {}
            headers.setdefault("User-Agent", self.cfg.user_agent)
            
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                timeout=timeout or self.cfg.timeout,
                verify=self.cfg.verify_ssl
            )
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "action": "network.http_request",
                "success": response.ok,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data,
                "url": url,
                "method": method
            }
        except Exception as e:
            return {
                "action": "network.http_request",
                "success": False,
                "error": str(e),
                "url": url
            }

    def download_file(self, url: str, save_path: str, chunk_size: int = 8192,
                     show_progress: bool = True) -> Dict[str, Any]:
        """Download a file from URL."""
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(
                url,
                stream=True,
                timeout=self.cfg.timeout,
                verify=self.cfg.verify_ssl
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if show_progress and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rDownloading: {percent:.1f}%", end="")
            
            if show_progress:
                print()  # New line after progress
            
            return {
                "action": "network.download_file",
                "success": True,
                "url": url,
                "save_path": str(save_path),
                "size_bytes": downloaded,
                "size_mb": round(downloaded / 1024 / 1024, 2)
            }
        except Exception as e:
            return {
                "action": "network.download_file",
                "success": False,
                "error": str(e),
                "url": url
            }

    def upload_file(self, url: str, file_path: str, field_name: str = "file",
                   additional_data: Dict | None = None) -> Dict[str, Any]:
        """Upload a file to a URL."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    "action": "network.upload_file",
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            with open(file_path, 'rb') as f:
                files = {field_name: f}
                response = requests.post(
                    url,
                    files=files,
                    data=additional_data,
                    timeout=self.cfg.timeout,
                    verify=self.cfg.verify_ssl
                )
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "action": "network.upload_file",
                "success": response.ok,
                "status_code": response.status_code,
                "file_path": str(file_path),
                "url": url,
                "response": response_data
            }
        except Exception as e:
            return {
                "action": "network.upload_file",
                "success": False,
                "error": str(e),
                "file_path": str(file_path)
            }

    def get_url_info(self, url: str) -> Dict[str, Any]:
        """Get information about a URL without downloading."""
        try:
            response = requests.head(
                url,
                timeout=self.cfg.timeout,
                verify=self.cfg.verify_ssl,
                allow_redirects=True
            )
            
            return {
                "action": "network.url_info",
                "success": True,
                "url": url,
                "final_url": response.url,
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type'),
                "content_length": int(response.headers.get('content-length', 0)),
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {
                "action": "network.url_info",
                "success": False,
                "error": str(e),
                "url": url
            }

    def check_connectivity(self, hosts: List[str] | None = None) -> Dict[str, Any]:
        """Check internet connectivity."""
        hosts = hosts or ["https://www.google.com", "https://www.cloudflare.com"]
        
        results = {}
        for host in hosts:
            try:
                response = requests.get(host, timeout=5)
                results[host] = {
                    "reachable": True,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                results[host] = {
                    "reachable": False,
                    "error": str(e)
                }
        
        any_reachable = any(r.get("reachable") for r in results.values())
        
        return {
            "action": "network.check_connectivity",
            "success": any_reachable,
            "online": any_reachable,
            "results": results
        }

    async def _async_request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make an async HTTP request."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    try:
                        data = await response.json()
                    except:
                        data = await response.text()
                    
                    return {
                        "action": "network.async_request",
                        "success": response.ok,
                        "status_code": response.status,
                        "data": data,
                        "url": url
                    }
        except Exception as e:
            return {
                "action": "network.async_request",
                "success": False,
                "error": str(e),
                "url": url
            }

    def async_request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Wrapper for async request."""
        return asyncio.run(self._async_request(url, method, **kwargs))
