"""
Provider interfaces for the backend.

All external concerns are accessed through these interfaces.
The backend injects concrete implementations via config.py.
"""

from .persistence_provider import PersistenceProvider, JSONPersistenceProvider
from .identity_provider import IdentityProvider, StubIdentityProvider
from .llm_provider import LLMProvider, MockLLMProvider

__all__ = [
    "PersistenceProvider",
    "JSONPersistenceProvider",
    "IdentityProvider",
    "StubIdentityProvider",
    "LLMProvider",
    "MockLLMProvider",
]
