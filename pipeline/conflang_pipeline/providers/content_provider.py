"""
Content Provider interface for fetching talk data from churchofjesuschrist.org.

Used in pipeline stage 1 (Ingest).
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class TalkMetadata(BaseModel):
    """Metadata for a Conference talk"""
    talk_id: str
    conference_id: str
    session: str
    speaker: str
    title: dict[str, str]  # {lang: title}
    source_urls: dict[str, str]  # {lang: url}


class ContentProvider(ABC):
    """Interface for fetching Conference content"""

    @abstractmethod
    async def fetch_talk_metadata(self, url: str, languages: list[str]) -> TalkMetadata:
        """Fetch metadata for a talk across multiple languages"""
        pass

    @abstractmethod
    async def fetch_talk_text(self, url: str, language: str) -> str:
        """
        Fetch the official text of a talk.

        Returns: plain text with paragraphs separated by double newlines.
        Preserves Unicode, diacritics, etc.
        """
        pass

    @abstractmethod
    async def fetch_talk_audio(self, url: str, language: str) -> bytes:
        """
        Fetch the audio file for a talk.

        Returns: audio data (MP3)
        """
        pass


class MockContentProvider(ContentProvider):
    """Stub implementation for testing"""

    async def fetch_talk_metadata(self, url: str, languages: list[str]) -> TalkMetadata:
        """Returns stub metadata"""
        return TalkMetadata(
            talk_id="2025-10-test-01",
            conference_id="2025-10",
            session="Test Session",
            speaker="Elder Test",
            title={lang: f"Test Talk ({lang})" for lang in languages},
            source_urls={lang: f"{url}?lang={lang}" for lang in languages}
        )

    async def fetch_talk_text(self, url: str, language: str) -> str:
        """Returns stub text"""
        if language == "eng":
            return "Brothers and sisters, today I speak about faith.\n\nFaith is a principle of power."
        elif language == "ces":
            return "Bratři a sestry, dnes mluvím o víře.\n\nVíra je princip moci."
        else:
            return "Mock text in " + language

    async def fetch_talk_audio(self, url: str, language: str) -> bytes:
        """Returns empty bytes (stub)"""
        return b"MOCK_AUDIO_DATA"
