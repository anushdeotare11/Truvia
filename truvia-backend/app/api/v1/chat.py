from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.agents.knowledge_agent import knowledge_agent
from app.models.report import Report
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class ChatQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    report_id: Optional[UUID] = None

class CitationOut(BaseModel):
    source: str
    title: str
    url: Optional[str] = None
    excerpt: str

class ChatResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationOut] = []

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: ChatQuery,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user) # Require citizen login to chat
):
    # If report_id is provided, validate it exists
    if payload.report_id is not None:
        result = await db.execute(
            select(Report).where(Report.id == payload.report_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with id '{payload.report_id}' not found"
            )

    try:
        response = await knowledge_agent.answer_query(db, payload.query, report_id=payload.report_id)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat assistant error: {str(e)}"
        )
