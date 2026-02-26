from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from ..services.spam_shield import spam_shield_service
from .deps import get_current_user_id
from uuid import UUID

router = APIRouter(prefix="/spam-shield", tags=["Spam Shield"])

class SpamCheckRequest(BaseModel):
    text: str

class SpamCheckResponse(BaseModel):
    is_spam: bool
    score: float
    triggers: List[str]

@router.post("/check", response_model=SpamCheckResponse)
async def check_spam(
    request: SpamCheckRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Checks the provided text for spam trigger words and patterns."""
    try:
        results = spam_shield_service.check_text(request.text)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
