from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.agents.knowledge_agent import knowledge_agent
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class ChatQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)

class CitationOut(BaseModel):
    source: str
    title: str
    url: Optional[str] = None
    excerpt: str

class ChatResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationOut] = []

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: ChatQuery,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user) # Require citizen login to chat
):
    try:
        response = await knowledge_agent.answer_query(db, payload.query)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat assistant error: {str(e)}"
        )
