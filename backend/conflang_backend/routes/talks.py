"""
Talk data endpoints.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TalkListItem(BaseModel):
    """Summary of a talk for list view"""
    talk_id: str
    speaker: str
    title: dict[str, str]
    languages: list[str]


class TalkListResponse(BaseModel):
    """List of talks"""
    talks: list[TalkListItem]


@router.get("/talks", response_model=TalkListResponse)
async def list_talks(request: Request):
    """List all available talks"""
    # In a real implementation, this would read from packaged data
    return TalkListResponse(talks=[])


@router.get("/talks/{talk_id}")
async def get_talk(talk_id: str, request: Request):
    """Get full talk data for a specific talk"""
    config = request.app.state.config

    # In a real implementation, load from persistence
    # For now, return a stub message
    return {
        "talk_id": talk_id,
        "message": "Talk data loading not yet implemented"
    }
