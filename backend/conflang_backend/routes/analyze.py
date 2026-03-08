"""
On-demand word analysis endpoint (proxies to LLM).
"""

from fastapi import APIRouter, Request
from ..providers.llm_provider import WordAnalysisRequest, WordAnalysis

router = APIRouter()


@router.post("/analyze-word", response_model=WordAnalysis)
async def analyze_word(request: Request, analysis_request: WordAnalysisRequest):
    """
    Analyze a word in context.

    This proxies to the LLM provider to avoid exposing API keys to the frontend.
    Results should be cached by the persistence layer.
    """
    config = request.app.state.config
    llm = config.llm

    return await llm.analyze_word(analysis_request)
