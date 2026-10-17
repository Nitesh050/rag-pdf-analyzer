from fastapi import APIRouter

from src.dependencies import get_rag_chain
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = get_rag_chain().ask(request.question, document_id=request.document_id)

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )