"""Token service for generating and validating password reset tokens."""
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

class TokenService:
    def __init__(self, token_file: str = "tokens.json"):
        self.token_file = Path(token_file)
        self._tokens: Dict[str, Dict] = {}
        self._load_tokens()

    def _load_tokens(self):
        if self.token_file.exists():
            try:
                with open(self.token_file, "r") as f:
                    self._tokens = json.load(f)
                self._cleanup_expired()
            except Exception:
                self._tokens = {}

    def _save_tokens(self):
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as f:
                json.dump(self._tokens, f, indent=2)
        except Exception as e:
            print(f"Error saving tokens: {e}")

    def _cleanup_expired(self):
        now = datetime.now().timestamp()
        expired = [t for t, data in self._tokens.items() if data["expires"] < now]
        for t in expired:
            del self._tokens[t]
        if expired:
            self._save_tokens()

    def generate_reset_token(self, username: str, expires_in_hours: int = 24) -> str:
        self._cleanup_expired()
        
        # Remove any existing tokens for this user
        existing = [t for t, data in self._tokens.items() if data["username"].lower() == username.lower()]
        for t in existing:
            del self._tokens[t]

        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(hours=expires_in_hours)).timestamp()
        
        self._tokens[token] = {
            "username": username,
            "expires": expires
        }
        self._save_tokens()
        return token

    def validate_token(self, token: str) -> Optional[str]:
        self._cleanup_expired()
        data = self._tokens.get(token)
        if data:
            now = datetime.now().timestamp()
            if data["expires"] > now:
                return data["username"]
        return None

    def consume_token(self, token: str) -> bool:
        self._cleanup_expired()
        if token in self._tokens:
            del self._tokens[token]
            self._save_tokens()
            return True
        return False

# Global instance
_token_service: Optional[TokenService] = None

def get_token_service(config_dir: str = "/app/config") -> TokenService:
    global _token_service
    if _token_service is None:
        token_path = os.path.join(config_dir, "tokens.json")
        _token_service = TokenService(token_file=token_path)
    return _token_service
