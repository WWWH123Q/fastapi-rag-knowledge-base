from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.services.bm25_service import BM25Service
from app.services.document_loader import UnsupportedFileTypeError, extract_text_from_bytes
from app.services.embedding_service import EmbeddingService
from app.services.milvus_service import MilvusService
from app.services.rag_utils import merge_contexts_by_chunk_hash, parse_milvus_results
from app.services.text_splitter import split_text


class KnowledgeBaseService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        milvus_service: MilvusService,
    ):
        self.embedding_service = embedding_service
        self.milvus_service = milvus_service
        self.bm25_service = BM25Service()

    async def upload_document(self, file: UploadFile) -> dict:
        filename = Path(file.filename or "").name #获取文件名字，例：filename = "test.pdf"
        if not filename:
            raise ValueError("filename is required")

        content = await file.read() #这句是把上传文件的二进制内容读出来。 file.read() 是UploadFile 类 的内置函数
        if len(content) > settings.max_upload_bytes: #这句是防止用户上传太大的文件。
            raise ValueError(f"file is too large, max upload size is {settings.max_upload_mb} MB")

        file_hash = hashlib.sha256(content).hexdigest() #计算文件hash，唯一指纹。判断文件是否重复上传，删除文件，追溯文件。

        if self.milvus_service.file_exists(file_hash): #判断是否重复上传，在milvus里面检查，这个 file_hash 是否已经存在
            return { #如果存在，不再重复解析、不再重复向量化、不再重复插入 Milvus。
                "message": "Document already exists, skipped duplicate insert",
                "filename": filename,
                "file_hash": file_hash,
                "chunk_count": 0,
                "duplicated": True, #直接返回已经存在
            }

        try:#解析文件文本，真正从文件中提取文本。文件二进制内容 → 文本字符串
            text = extract_text_from_bytes(
                filename=filename,
                content=content,
            )
        except UnsupportedFileTypeError:
            raise
        except Exception as e:
            raise RuntimeError(f"document parse failed: {e}") from e

        if not text or not text.strip(): #检查是否提取到有效的文本内容，确保不是空文件
            return {
                "message": "No valid text extracted, nothing inserted",
                "filename": filename,
                "file_hash": file_hash,
                "chunk_count": 0,
                "duplicated": False,
            }

        file_ext = Path(filename).suffix.lower() #获取文件扩展名
        chunks = split_text(text, file_ext=file_ext)#切分chunk

        if not chunks: #如果没有chunk，就返回
            return {
                "message": "Document content is empty, nothing inserted",
                "filename": filename,
                "file_hash": file_hash,
                "chunk_count": 0,
                "duplicated": False,
            }

        vectors = self.embedding_service.embed_texts(chunks) #对每个chunk做embedding,把chunk向量化
        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")#记录上传时间
        data = []#准备要插入 Milvus 的数据。先创建一个空列表，用来存所有 chunk 的数据。

        for chunk, vector in zip(chunks, vectors): #遍历chunk和vector,因为每个chunk都有一个对应向量。zip(chunks, vectors) 就是把它们一一配对。
            chunk_hash = hashlib.sha256(  #给每一个chunk生成唯一id。file_hash + chunk内容 → chunk_hash
                f"{file_hash}_{chunk}".encode("utf-8")
            ).hexdigest() #file_hash是用来区分不同文件，chunk_hash是用来区别不同的chunk字段。

            data.append( #组装每个chunk数据，在准备插入 Milvus 的每一条数据
                {
                    "vector": vector, #chunk的向量
                    "text": chunk, #chunk原文
                    "filename": filename, #原来文件名字
                    "file_hash": file_hash,#原来文件的hash
                    "file_ext": file_ext, #文件扩展名
                    "uploaded_at": uploaded_at, #上传时间
                    "chunk_hash": chunk_hash,#当前chunk的唯一hash
                }
            )

        self.milvus_service.insert_chunks(data) #插入milvus数据库，真正把数据写入向量数据库。
        # 插入后milvus就有了chunk文本 + chunk向量 + 文件元数据。以后用户提问时，就可以从 Milvus 里检索相关 chunk。

        return { #返回上传结果
            "message": "Document uploaded, parsed, embedded, and stored",
            "filename": filename,
            "file_hash": file_hash,
            "chunk_count": len(chunks),
            "embedding_dimension": self.embedding_service.dimension,
            "duplicated": False,
            "file_ext": file_ext,
            "uploaded_at": uploaded_at,
        }

    def _clean_metadata_filter(self, metadata_filter: dict | None = None) -> dict:
        if not metadata_filter:
            return {}

        cleaned = {}
        for key in ("filename", "file_hash", "file_ext", "uploaded_after", "uploaded_before"):
            value = metadata_filter.get(key)
            if value:
                cleaned[key] = value
        return cleaned

    def _vector_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed_text(query) #1.把用户问题转成向量

        raw_results = self.milvus_service.search( #2.去 Milvus 搜索
            query_vector=query_vector,
            limit=top_k,
            metadata_filter=metadata_filter,
        )

        return parse_milvus_results(raw_results, retrieval_source="vector") #3.整理 Milvus 原始结果，把 Milvus 返回的结果，转成你前端容易展示的格式。

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        if not settings.enable_bm25:
            return []

        documents = self.milvus_service.query_chunks(
            metadata_filter=metadata_filter,
            limit=10000,
        )
        self.bm25_service.build_index(documents)
        return self.bm25_service.search(query=query, top_k=top_k)

    def search( #搜索业务入口
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: dict | None = None,
    ):
        contexts = self.retrieve_contexts( #帮我根据 query 找到最相关的上下文片段。
            query=query,
            top_k=top_k,
            metadata_filter=metadata_filter,
            use_bm25=False, #false:只用了向量检索，没有启用 BM25 关键词检索。 query → embedding → Milvus 向量相似度搜索
        )

        return {
            "query": query,
            "top_k": top_k,
            "embedding_dimension": self.embedding_service.dimension,
            "results": contexts,
        }

    def retrieve_contexts(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
        use_bm25: bool = True,
    ) -> list[dict]:
        metadata_filter = self._clean_metadata_filter(metadata_filter)
        vector_contexts = self._vector_search( #向量检索。
            query=query,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )

        if not use_bm25:
            return vector_contexts

        bm25_contexts = self._bm25_search(
            query=query,
            top_k=settings.bm25_top_k,
            metadata_filter=metadata_filter,
        )

        return merge_contexts_by_chunk_hash([vector_contexts, bm25_contexts])

    def hybrid_search(
        self,
        queries: list[str],
        candidate_k: int,
        bm25_top_k: int | None = None,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        metadata_filter = self._clean_metadata_filter(metadata_filter)
        bm25_top_k = bm25_top_k or settings.bm25_top_k
        context_groups = []

        for query in queries:
            context_groups.append(
                self._vector_search(
                    query=query,
                    top_k=candidate_k,
                    metadata_filter=metadata_filter,
                )
            )

        if settings.enable_bm25:
            bm25_query = " ".join(queries)
            context_groups.append(
                self._bm25_search(
                    query=bm25_query,
                    top_k=bm25_top_k,
                    metadata_filter=metadata_filter,
                )
            )

        return merge_contexts_by_chunk_hash(context_groups)

    def list_documents(self) -> dict:
        # 查询当前知识库里已经上传过哪些文档，并统计每个文档切成了多少个chunK
        documents = self.milvus_service.list_documents()

        return {
            "total": len(documents),
            "documents": documents,
        }

    def delete_document(self, file_hash: str) -> dict:
        documents = self.milvus_service.list_documents()

        target = None
        for doc in documents:
            if doc.get("file_hash") == file_hash:
                target = doc
                break

        if target is None:
            return {
                "found": False,
                "file_hash": file_hash,
            }

        self.milvus_service.delete_by_file_hash(file_hash)

        return {
            "found": True,
            "message": "Document and vectors deleted",
            "filename": target.get("filename", ""),
            "file_hash": file_hash,
            "deleted": True,
        }
