"""
Provider interfaces for the pipeline.

All external concerns are accessed through these interfaces.
The pipeline injects concrete implementations at startup.
"""

from .llm_provider import LLMProvider, MockLLMProvider
from .audio_provider import AudioProvider, MockAudioProvider
from .content_provider import ContentProvider, MockContentProvider, TalkTextResult
from .church_content_provider import ChurchContentProvider
from .persistence_provider import PersistenceProvider, JSONPersistenceProvider

__all__ = [
    "LLMProvider",
    "MockLLMProvider",
    "AudioProvider",
    "MockAudioProvider",
    "ContentProvider",
    "MockContentProvider",
    "ChurchContentProvider",
    "TalkTextResult",
    "PersistenceProvider",
    "JSONPersistenceProvider",
]
