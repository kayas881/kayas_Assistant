from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import json

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False

from ..agent.config import spotify_config


@dataclass 
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str


class SpotifyExecutor:
    def __init__(self, cfg: SpotifyConfig):
        self.cfg = cfg
        self.sp = None
        self._auth_error: Optional[str] = None
        if SPOTIFY_AVAILABLE:
            # Validate configuration before attempting OAuth
            missing = []
            if not (self.cfg.client_id or "").strip():
                missing.append("SPOTIFY_CLIENT_ID")
            if not (self.cfg.client_secret or "").strip():
                missing.append("SPOTIFY_CLIENT_SECRET")
            if not (self.cfg.redirect_uri or "").strip():
                missing.append("SPOTIFY_REDIRECT_URI")
            if missing:
                self._auth_error = (
                    "Spotify credentials missing: " + ", ".join(missing) + ". "
                    "Set them as environment variables or in your profile YAML under apis.spotify.*"
                )
            else:
                self._authenticate()

    def _authenticate(self):
        """Authenticate with Spotify API"""
        try:
            auth_manager = SpotifyOAuth(
                client_id=self.cfg.client_id,
                client_secret=self.cfg.client_secret,
                redirect_uri=self.cfg.redirect_uri,
                scope=self.cfg.scope
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            self._auth_error = f"Spotify authentication failed: {e}"
            print(self._auth_error)

    def search_music(self, query: str, search_type: str = "track", limit: int = 10) -> Dict:
        """Search for music on Spotify"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}
        
        try:
            results = self.sp.search(q=query, type=search_type, limit=limit)
            
            items = []
            for item in results[f"{search_type}s"]["items"]:
                if search_type == "track":
                    items.append({
                        "id": item["id"],
                        "name": item["name"],
                        "artists": [artist["name"] for artist in item["artists"]],
                        "album": item["album"]["name"],
                        "uri": item["uri"],
                        "preview_url": item.get("preview_url", ""),
                        "external_url": item["external_urls"]["spotify"],
                        "duration_ms": item["duration_ms"],
                        "popularity": item["popularity"]
                    })
                elif search_type == "album":
                    items.append({
                        "id": item["id"],
                        "name": item["name"],
                        "artists": [artist["name"] for artist in item["artists"]],
                        "uri": item["uri"],
                        "external_url": item["external_urls"]["spotify"],
                        "total_tracks": item["total_tracks"],
                        "release_date": item["release_date"]
                    })
                elif search_type == "artist":
                    items.append({
                        "id": item["id"],
                        "name": item["name"],
                        "uri": item["uri"],
                        "external_url": item["external_urls"]["spotify"],
                        "followers": item["followers"]["total"],
                        "popularity": item["popularity"],
                        "genres": item["genres"]
                    })
            
            return {
                "action": "spotify.search_music",
                "query": query,
                "type": search_type,
                "results": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": f"Failed to search music: {str(e)}"}

    def play_track(self, track_uri: str, device_id: Optional[str] = None) -> Dict:
        """Play a track on Spotify"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}
        
        try:
            self.sp.start_playback(device_id=device_id, uris=[track_uri])
            return {
                "action": "spotify.play_track",
                "track_uri": track_uri,
                "device_id": device_id,
                "playing": True
            }
        except Exception as e:
            return {"error": f"Failed to play track: {str(e)}"}

    def play_query(self, query: str, device_id: Optional[str] = None) -> Dict:
        """Search for a track by query and play the top result."""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}

        try:
            results = self.sp.search(q=query, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])
            if not items:
                return {"error": f"No tracks found for query: {query}"}
            track = items[0]
            uri = track["uri"]
            self.sp.start_playback(device_id=device_id, uris=[uri])
            return {
                "action": "spotify.play_query",
                "query": query,
                "device_id": device_id,
                "track": {
                    "id": track["id"],
                    "name": track["name"],
                    "artists": [a["name"] for a in track.get("artists", [])],
                    "album": track.get("album", {}).get("name", ""),
                    "uri": uri,
                    "external_url": track.get("external_urls", {}).get("spotify", "")
                },
                "playing": True
            }
        except Exception as e:
            return {"error": f"Failed to play query: {str(e)}"}

    def get_current_playing(self) -> Dict:
        """Get currently playing track"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}
        
        try:
            current = self.sp.current_playback()
            
            if not current or not current.get("item"):
                return {
                    "action": "spotify.get_current_playing",
                    "is_playing": False,
                    "track": None
                }
            
            track = current["item"]
            return {
                "action": "spotify.get_current_playing",
                "is_playing": current["is_playing"],
                "track": {
                    "id": track["id"],
                    "name": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album": track["album"]["name"],
                    "uri": track["uri"],
                    "external_url": track["external_urls"]["spotify"],
                    "duration_ms": track["duration_ms"],
                    "progress_ms": current["progress_ms"]
                },
                "device": {
                    "id": current["device"]["id"],
                    "name": current["device"]["name"],
                    "type": current["device"]["type"],
                    "volume": current["device"]["volume_percent"]
                }
            }
        except Exception as e:
            return {"error": f"Failed to get current playing: {str(e)}"}

    def pause_playback(self, device_id: Optional[str] = None) -> Dict:
        """Pause current playback"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}
        
        try:
            self.sp.pause_playback(device_id=device_id)
            return {
                "action": "spotify.pause_playback",
                "device_id": device_id,
                "paused": True
            }
        except Exception as e:
            return {"error": f"Failed to pause playback: {str(e)}"}

    def resume_playback(self, device_id: Optional[str] = None) -> Dict:
        """Resume current playback"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": self._auth_error or "Spotify API not available or not authenticated"}
        
        try:
            self.sp.start_playback(device_id=device_id)
            return {
                "action": "spotify.resume_playback",
                "device_id": device_id,
                "playing": True
            }
        except Exception as e:
            return {"error": f"Failed to resume playback: {str(e)}"}

    def get_user_playlists(self, limit: int = 20) -> Dict:
        """Get user's playlists"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": "Spotify API not available or not authenticated"}
        
        try:
            playlists = self.sp.current_user_playlists(limit=limit)
            
            items = []
            for playlist in playlists["items"]:
                items.append({
                    "id": playlist["id"],
                    "name": playlist["name"],
                    "description": playlist.get("description", ""),
                    "uri": playlist["uri"],
                    "external_url": playlist["external_urls"]["spotify"],
                    "public": playlist["public"],
                    "collaborative": playlist["collaborative"],
                    "total_tracks": playlist["tracks"]["total"],
                    "owner": playlist["owner"]["display_name"]
                })
            
            return {
                "action": "spotify.get_user_playlists",
                "playlists": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": f"Failed to get playlists: {str(e)}"}

    def create_playlist(self, name: str, description: str = "", public: bool = True) -> Dict:
        """Create a new playlist"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": "Spotify API not available or not authenticated"}
        
        try:
            user_id = self.sp.current_user()["id"]
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description
            )
            
            return {
                "action": "spotify.create_playlist",
                "playlist": {
                    "id": playlist["id"],
                    "name": playlist["name"],
                    "description": playlist.get("description", ""),
                    "uri": playlist["uri"],
                    "external_url": playlist["external_urls"]["spotify"],
                    "public": playlist["public"]
                }
            }
        except Exception as e:
            return {"error": f"Failed to create playlist: {str(e)}"}

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> Dict:
        """Add tracks to a playlist"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": "Spotify API not available or not authenticated"}
        
        try:
            self.sp.playlist_add_items(playlist_id=playlist_id, items=track_uris)
            return {
                "action": "spotify.add_tracks_to_playlist",
                "playlist_id": playlist_id,
                "tracks_added": len(track_uris),
                "track_uris": track_uris
            }
        except Exception as e:
            return {"error": f"Failed to add tracks to playlist: {str(e)}"}

    def get_devices(self) -> Dict:
        """Get available playback devices"""
        if not SPOTIFY_AVAILABLE or not self.sp:
            return {"error": "Spotify API not available or not authenticated"}
        
        try:
            devices = self.sp.devices()
            
            items = []
            for device in devices["devices"]:
                items.append({
                    "id": device["id"],
                    "name": device["name"],
                    "type": device["type"],
                    "is_active": device["is_active"],
                    "is_private_session": device["is_private_session"],
                    "is_restricted": device["is_restricted"],
                    "volume_percent": device["volume_percent"]
                })
            
            return {
                "action": "spotify.get_devices",
                "devices": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": f"Failed to get devices: {str(e)}"}