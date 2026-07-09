from fastapi import APIRouter

from src.generation.rag_chain import RAGChain
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

rag = RAGChain()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = rag.ask(request.question)

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )