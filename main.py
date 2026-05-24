# from typing import Optional
# from pydantic import BaseModel
# from fastapi import FastAPI
#
# # app = FastAPI() #创建应用实例
# app = FastAPI(
#     title="我的 API",                    # API 标题
#     description="这是一个示例 API，展示文档自定义功能",  # API 描述
#     version="1.0.0",                    # API 版本
#     terms_of_service="http://example.com/terms/",  # 服务条款 URL
#     contact={                           # 联系信息
#         "name": "开发者",
#         "url": "http://example.com/contact/",
#         "email": "dev@example.com",
#     },
#     license_info={                      # 许可证信息
#         "name": "MIT",
#         "url": "https://opensource.org/licenses/MIT",
#     },
# )
#
# class Item(BaseModel):
#     name:str
#     description: Optional[str] =None
#     price:float
#     tax: Optional[float] =None
#
# @app.get(
#     "/items/{item_id}",
#     summary="获取商品信息",              # 简短摘要
#     description="根据商品 ID 获取商品的详细信息",  # 详细描述
#     response_description="商品信息对象",   # 响应描述
#     tags=["商品管理"],                   # 分组标签
# )
#
# @app.get("/") #定义路径操作装饰器。当用户通过get方法访问根路径 / 时候，就执行下面的函数
# async def root(): #路径操作函数，每当FastAPI接收到GET/请求时候就调用它
#     return {"message":"Hello World"}
#     #返回相应内容，函数返回一个字典，fastapi会把它自动转换成JSON响应格式。
#     #可以返回list、dict、str、int等，FastAPI都会自动处理JSON转换
#
# @app.get("/items/{item_id}")
# async def read_item(item_id:int, q: Optional[str] =None):
#     """ 根据ID获得条目，支持可选的查询参数q"""
#     return {"item_id":item_id,"q":q}
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# 1. 定义请求体格式
class ChatRequest(BaseModel):
    question: str


# 2. 健康检查接口
@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "服务正常运行"
    }


# 3. 查询参数示例
@app.get("/search")
def search(keyword: str, top_k: int = 5):
    return {
        "keyword": keyword,
        "top_k": top_k,
        "result": f"你搜索的是：{keyword}，返回前 {top_k} 条结果"
    }


# 4. 路径参数示例
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {
        "user_id": user_id,
        "name": "测试用户"
    }


# 5. 请求体示例：最像 RAG / Agent 的接口
@app.post("/chat")
def chat(req: ChatRequest):
    return {
        "question": req.question,
        "answer": f"你问的是：{req.question}"
    }