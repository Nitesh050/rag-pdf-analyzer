from fastapi import FastAPI

from src.routers.chat import router as chat_router
from src.routers.upload import router as upload_router

app = FastAPI(title="RAG Platform API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "RAG Platform API is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
app.include_router(upload_router)