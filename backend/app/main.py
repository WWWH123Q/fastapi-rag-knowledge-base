from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.file import router as file_router
from app.api.health import router as health_router
from app.api.rag import router as rag_router
from app.api.user import router as user_router
from app.config import settings
from app.security import InMemoryRateLimitMiddleware


app = FastAPI(
    title="RAG Knowledge Base API",
    description="Local knowledge base + web search + hybrid RAG API",
    version="1.0.0",
)

app.add_middleware(InMemoryRateLimitMiddleware)


# 解决前端跨域访问问题
# 允许 Vue 前端访问 FastAPI 后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(user_router)
app.include_router(health_router)
app.include_router(file_router)
app.include_router(rag_router)
