from fastapi import FastAPI

from src.routers.chat import router as chat_router
from src.routers.upload import router as upload_router

app = FastAPI(title="RAG Platform API")

app.include_router(chat_router)
app.include_router(upload_router)