"""
LLM Provider interface for semantic analysis and alignment.

Used in pipeline stages 4-7 for:
- Sentence segmentation
- Paragraph and sentence alignment
- Semantic unit mapping
- Phonetic transcription
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class SentenceSegmentRequest(BaseModel):
    """Request for sentence segmentation within a paragraph"""
    text: str
    language: str


class SentenceSegmentResponse(BaseModel):
    """Response with sentence boundaries"""
    sentences: list[dict[str, Any]]  # {text, start_char, end_char}


class AlignmentRequest(BaseModel):
    """Request for cross-language alignment"""
    home_items: list[str]
    study_items: list[str]
    home_language: str
    study_language: str


class AlignmentResponse(BaseModel):
    """Response with alignment groups"""
    groups: list[dict[str, list[int]]]  # {home: [indices], study: [indices]}


class SemanticMapRequest(BaseModel):
    """Request for semantic unit mapping"""
    home_text: str
    study_text: str
    home_language: str
    study_language: str


class SemanticMapResponse(BaseModel):
    """Response with spans and semantic links"""
    spans: list[dict[str, Any]]
    links: list[dict[str, Any]]


class LLMProvider(ABC):
    """Interface for LLM-based analysis"""

    @abstractmethod
    async def segment_sentences(self, request: SentenceSegmentRequest) -> SentenceSegmentResponse:
        """Split a paragraph into sentences with character offsets"""
        pass

    @abstractmethod
    async def align_items(self, request: AlignmentRequest) -> AlignmentResponse:
        """Align paragraphs or sentences across languages"""
        pass

    @abstractmethod
    async def generate_semantic_map(self, request: SemanticMapRequest) -> SemanticMapResponse:
        """Generate fine-grained semantic mapping between aligned sentences"""
        pass

    @abstractmethod
    async def generate_phonetic(self, text: str, language: str) -> str:
        """Generate phonetic transcription (pinyin, IPA, etc.)"""
        pass


class MockLLMProvider(LLMProvider):
    """Stub implementation for testing"""

    async def segment_sentences(self, request: SentenceSegmentRequest) -> SentenceSegmentResponse:
        """Returns a single sentence (the whole paragraph)"""
        return SentenceSegmentResponse(
            sentences=[{
                "text": request.text,
                "start_char": 0,
                "end_char": len(request.text)
            }]
        )

    async def align_items(self, request: AlignmentRequest) -> AlignmentResponse:
        """Returns 1:1 alignment"""
        groups = []
        for i in range(min(len(request.home_items), len(request.study_items))):
            groups.append({"home": [i], "study": [i]})
        return AlignmentResponse(groups=groups)

    async def generate_semantic_map(self, request: SemanticMapRequest) -> SemanticMapResponse:
        """Returns empty mapping"""
        return SemanticMapResponse(spans=[], links=[])

    async def generate_phonetic(self, text: str, language: str) -> str:
        """Returns the original text"""
        return text
