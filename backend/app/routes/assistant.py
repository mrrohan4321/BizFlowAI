from fastapi import APIRouter, Depends

from app.auth import get_business_id
from app.schemas.assistant import AssistantQuestion
from app.services import assistant

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat")
def chat(body: AssistantQuestion, business_id: str = Depends(get_business_id)):
    """LLM only picks an approved tool and explains it; Python calculates every number."""
    return assistant.chat(business_id, body.question)
