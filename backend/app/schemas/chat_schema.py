"""
专门放请求体和响应体模型。
ChatRequest：前端要传进来什么
ChatResponse：后端要返回什么
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    question: str
    answer: str