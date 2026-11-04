from typing import Dict, Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User
from app.services import financial_assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AskAssistantRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500, description="User financial question")


@router.post("/ask")
@limiter.limit("30/minute")
async def ask_assistant(
    request: Request,
    payload: AskAssistantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Answers natural language queries about personal finances using safe predefined SQL tools.
    Requires user consent 'ai_processing'.
    """
    return await financial_assistant_service.answer_financial_query(
        db=db,
        user_id=current_user.id,
        question=payload.question,
    )

