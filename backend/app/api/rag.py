from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.schemas.rag_schema import (
    AskRequest,
    AskResponse,
    DeleteDocumentResponse,
    DocumentListResponse,
    HybridAskRequest,
    HybridAskResponse,
    SearchRequest,
    SearchResponse,
    UploadResponse,
    WebAskResponse,
    WebSearchRequest,
)
from app.security import require_api_key
from app.services.document_loader import UnsupportedFileTypeError
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.llm_service import LLMService
from app.services.milvus_service import MilvusService
from app.services.rag_pipeline_service import RAGPipelineService
from app.services.web_search_service import WebSearchService


router = APIRouter(
    prefix="/rag",
    tags=["RAG"], #自动生成接口文档，标签，下面的所有接口都会被归到RAG这一标签下面。
    dependencies=[Depends(require_api_key)], #这个表示：这个 router 下面的所有接口，都必须先执行 require_api_key 这个依赖。
    #前端请求接口时候，需要带上X-API-Key: your-api-key，如果没有带或者key不正确，就不允许访问。
) #路由定义，这表示创建一个 FastAPI 的路由对象。

embedding_service = EmbeddingService() #创建向量化函数

milvus_service = MilvusService( #创建Milvus向量数据库服务，负责存储和检索文档 chunk 的向量
    db_path="./milvus_demo.db", #本地 Milvus Lite 的数据库文件路径。
    collection_name="document_chunks", #集合名字。document_chunks = 专门存文档切片向量的表
    dimension=embedding_service.dimension, #维度和embedding的保持一致
)

llm_service = LLMService() #创建大模型服务
web_search_service = WebSearchService() #创建互联网搜索服务，访问互联网搜索结果

knowledge_base_service = KnowledgeBaseService(  #创建本地知识库服务。这个是把 EmbeddingService 和 MilvusService 组合起来
    embedding_service=embedding_service, #它负责完整的本地知识库流程。
    milvus_service=milvus_service,
)#管理本地知识库的上传、入库、删除、检索等操作。
# 比如上传文件时：文件文本 → 切 chunk → embedding 向量化 → 存入 Milvus
# 搜索文档时：用户问题 → embedding 向量化 → 去 Milvus 里相似度检索 → 返回相关 chunk

rag_pipeline_service = RAGPipelineService(
    knowledge_base_service=knowledge_base_service,
    llm_service=llm_service,
    web_search_service=web_search_service,
)#创建rag流程服务，它把前面的几个组件组合起来，形成完整问答流程。是总调度
#用户问题-->本地知识库检索-->可选：联网搜索-->拼接上下文-->交给大模型生成答案-->返回答案和来源


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):#UploadFile是FastAPI的类型，file.filename、 文件名file.content_type、文件类型await file.read()   # 读取文件内容
    try:
        return await knowledge_base_service.upload_document(file)
    except UnsupportedFileTypeError as e: #文件类型不支持
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:#用户输入错误
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:#系统内部错误
        raise HTTPException(status_code=500, detail="Document upload failed") from e


@router.get("/documents", response_model=DocumentListResponse)
def list_documents():
    return knowledge_base_service.list_documents()


@router.delete("/documents/{file_hash}", response_model=DeleteDocumentResponse)
def delete_document(file_hash: str):
    result = knowledge_base_service.delete_document(file_hash)

    if not result.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"Document not found for file_hash={file_hash}",
        )

    return result


@router.post("/search", response_model=SearchResponse)
def search_document(request: SearchRequest):
    return knowledge_base_service.search(
        query=request.query,
        top_k=request.top_k,
        metadata_filter=request.metadata_filter(),
    )


@router.post("/ask", response_model=AskResponse)
def ask_document(request: AskRequest):
    return rag_pipeline_service.ask_local(
        query=request.query,
        top_k=request.top_k,
        metadata_filter=request.metadata_filter(),
    )


@router.post("/web-search")
def web_search(request: WebSearchRequest):
    return rag_pipeline_service.web_search_only(
        query=request.query,
        top_k=request.top_k,
        provider=request.provider,
    )


@router.post("/ask-web", response_model=WebAskResponse)
def ask_web(request: WebSearchRequest):
    return rag_pipeline_service.ask_web(
        query=request.query,
        top_k=request.top_k,
        provider=request.provider,
    )


@router.post("/ask-hybrid", response_model=HybridAskResponse)
def ask_hybrid(request: HybridAskRequest):
    return rag_pipeline_service.ask_hybrid(
        query=request.query,
        local_top_k=request.local_top_k,
        web_top_k=request.web_top_k,
        provider=request.provider,
        metadata_filter=request.metadata_filter(),
    )
