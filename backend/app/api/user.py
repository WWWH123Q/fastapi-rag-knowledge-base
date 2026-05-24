
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user_schema import UserResponse
# from app.services.

router = APIRouter() #APIRouter 就是一个“小型的 app”，专门管理一组接口。

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    if user_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="user_id 必须大于 0"
        )
    return UserResponse(user_id=user_id)