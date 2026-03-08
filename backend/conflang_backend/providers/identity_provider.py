"""
Identity Provider interface for user management.

For now, we use a stub implementation (X-User-Id header).
In production, swap for a real auth provider (Supabase, Firebase, etc.).
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any


class User(BaseModel):
    """User model"""
    id: str
    display_name: str


class UserPreferences(BaseModel):
    """User preferences model"""
    user_id: str
    home_language: str = "eng"
    study_languages: list[str] = ["ces"]
    active_study_lang: str = "ces"
    playback_speed: float = 1.0
    interlinear_pause_ms: int = 500
    show_phonetics: bool = True
    show_diff_markers: bool = True
    font_size: str = "medium"
    theme: str = "light"


class IdentityProvider(ABC):
    """Interface for user identity and preferences"""

    @abstractmethod
    async def get_current_user(self, user_id: str | None = None) -> User | None:
        """Get the current user from context"""
        pass

    @abstractmethod
    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences"""
        pass

    @abstractmethod
    async def save_preferences(self, preferences: UserPreferences) -> None:
        """Save user preferences"""
        pass


class StubIdentityProvider(IdentityProvider):
    """
    Stub implementation using X-User-Id header.

    No authentication — just read the user ID from the header and trust it.
    """

    async def get_current_user(self, user_id: str | None = None) -> User | None:
        """Return a stub user"""
        if not user_id:
            user_id = "default-user"

        return User(id=user_id, display_name="Test User")

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Return default preferences"""
        return UserPreferences(user_id=user_id)

    async def save_preferences(self, preferences: UserPreferences) -> None:
        """No-op for stub"""
        pass
