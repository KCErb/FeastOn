"""
LLM Provider interface for on-demand word analysis.

The backend proxies these calls to avoid exposing API keys to the frontend.
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any


class WordAnalysisRequest(BaseModel):
    """Request for word analysis"""
    word: str
    context: str
    home_language: str
    study_language: str
    talk_id: str


class WordAnalysis(BaseModel):
    """Response with detailed word analysis"""
    word: str
    language: str
    phonetic: str | None = None
    lemma: str | None = None
    part_of_speech: str | None = None
    morphology: dict[str, Any] = {}
    definition: str | None = None
    register: str | None = None
    informal_alt: str | None = None
    home_equivalent: str | None = None
    related_words: list[str] = []


class LLMProvider(ABC):
    """Interface for LLM-based analysis"""

    @abstractmethod
    async def analyze_word(self, request: WordAnalysisRequest) -> WordAnalysis:
        """Analyze a word in context"""
        pass


class MockLLMProvider(LLMProvider):
    """Stub implementation for testing"""

    async def analyze_word(self, request: WordAnalysisRequest) -> WordAnalysis:
        """Return stub analysis"""
        return WordAnalysis(
            word=request.word,
            language=request.study_language,
            phonetic="MOCK-pronunciation",
            lemma=request.word.lower(),
            part_of_speech="noun",
            definition=f"Mock definition for '{request.word}'",
            home_equivalent="mock translation",
        )
