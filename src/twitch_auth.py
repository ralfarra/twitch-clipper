"""
Twitch API authentication using Client Credentials flow.
No user login required — works with just Client ID + Secret.
"""

import time
import requests


class TwitchAuth:
    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    API_BASE = "https://api.twitch.tv/helix"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._token_expires_at = 0

    def get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = requests.post(self.TOKEN_URL, params={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        })
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
        return self._token

    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Client-Id": self.client_id,
        }
