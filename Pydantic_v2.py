from typing import Optional

from pydantic import BaseModel, ConfigDict

from main import app


class Item(BaseModel):
    name: str
    price: float

    # Pydantic v2 的配置方式
    model_config = ConfigDict( #是 Pydantic v2 里专门用来写模型配置的工具。
        json_schema_extra={  # 在 API 文档中显示示例。意思是给自动生成的 JSON Schema 额外加一点信息。
            "examples": [
                {
                    "name": "Foo",
                    "price": 35.4
                }
            ]
        }
    )

#pydantic支持继承
from pydantic import BaseModel, EmailStr


# 基础模型
class UserBase(BaseModel):
    username: str       # 必填
    email: EmailStr     # 必填，自动校验邮箱格式
    full_name: Optional[str] = None  # 可选


# 创建用户时的输入模型（包含密码）
class UserCreate(UserBase):
    password: str       # 必填


# 返回用户信息时的输出模型（不包含密码）
class UserOut(UserBase):
    id: int             # 由服务器生成


# 使用示例
@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    # 函数接收 UserCreate（含密码），但响应使用 UserOut（不含密码）
    # 这样密码就不会出现在 API 响应中
    return {"id": 1, **user.model_dump(exclude={"password"})}