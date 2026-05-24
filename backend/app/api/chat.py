from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import generate_answer

router = APIRouter() #APIRouter 就是一个“小型的 app”，专门管理一组接口。


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    answer = generate_answer(req.question)

    return ChatResponse(
        question=req.question,
        answer=answer
    )