from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers.chat import router as chat_router
from src.routers.upload import router as upload_router

app = FastAPI(title="RAG Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "RAG Platform API is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
app.include_router(upload_router)