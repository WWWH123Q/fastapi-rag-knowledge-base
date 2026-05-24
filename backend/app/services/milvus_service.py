from __future__ import annotations

import uuid

from pymilvus import MilvusClient


class MilvusService:
    def __init__(
        self,
        db_path: str = "./milvus_demo.db",
        collection_name: str = "document_chunks",
        dimension: int = 384,
    ):
        self.client = MilvusClient(db_path)
        self.collection_name = collection_name
        self.dimension = dimension
        self._init_collection()

    def _init_collection(self):
        if not self.client.has_collection(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.dimension,
            )

        self.client.load_collection(collection_name=self.collection_name)

    def _build_filter_expr(self, metadata_filter: dict | None = None) -> str:
        if not metadata_filter:
            return ""

        parts = []
        for field in ("file_hash", "file_ext", "filename"):
            value = metadata_filter.get(field)
            if value:
                escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
                parts.append(f'{field} == "{escaped}"')

        return " and ".join(parts)

    def insert_chunks(self, chunks: list[dict]):
        data = []

        for chunk in chunks:
            data.append(
                {
                    "id": uuid.uuid4().int % (2**63 - 1),
                    "vector": chunk["vector"],
                    "text": chunk["text"],
                    "filename": chunk.get("filename", ""),
                    "file_hash": chunk.get("file_hash", ""),
                    "file_ext": chunk.get("file_ext", ""),
                    "uploaded_at": chunk.get("uploaded_at", ""),
                    "chunk_hash": chunk.get("chunk_hash", ""),
                }
            )

        result = self.client.insert( #插入 Milvus
            collection_name=self.collection_name, #插入到哪个 collection，默认document_chunks，也就是专门存文档 chunk 的集合
            data=data,
        )

        self.client.load_collection(collection_name=self.collection_name) #确保这个 collection 处于可查询状态。

        return {
            "insert_count": len(data),
            "result": result,
        }

    def search(
        self,
        query_vector: list[float],
        limit: int = 3,
        metadata_filter: dict | None = None,
    ):
        self.client.load_collection(collection_name=self.collection_name)
        filter_expr = self._build_filter_expr(metadata_filter)

        kwargs = {}
        if filter_expr:
            kwargs["filter"] = filter_expr

        return self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=limit,
            output_fields=[
                "text",
                "filename",
                "file_hash",
                "file_ext",
                "uploaded_at",
                "chunk_hash",
            ],
            **kwargs,
        )

    def query_chunks( #从 Milvus 向量数据库里查询 chunk 记录，并返回这些 chunk 的文本和元数据。
        self,          #条件查询：query_chunks()= 从 Milvus 里把符合条件的 chunk 查出来
        metadata_filter: dict | None = None,
        limit: int = 10000,
    ) -> list[dict]:
        self.client.load_collection(collection_name=self.collection_name)
        filter_expr = self._build_filter_expr(metadata_filter)

        return self.client.query(
            collection_name=self.collection_name,
            filter=filter_expr,
            output_fields=[
                "text",
                "filename",
                "file_hash",
                "file_ext",
                "uploaded_at",
                "chunk_hash",
            ],
            limit=limit,
        )

    def list_collections(self):
        return self.client.list_collections()

    def file_exists(self, file_hash: str) -> bool:
        self.client.load_collection(collection_name=self.collection_name)

        results = self.client.query(
            collection_name=self.collection_name,
            filter=f'file_hash == "{file_hash}"',
            output_fields=["file_hash", "filename"],
            limit=1,
        )

        return len(results) > 0

    def list_documents(self) -> list[dict]:
        # Milvus里面存的是一条条chunk，不是一个个完整文档。所以要把属于同一个文件的chunk合并统计成一个文档。
        results = self.query_chunks(limit=10000)

        documents = {}
        for item in results:
            file_hash = item.get("file_hash", "")
            if not file_hash: #如果没有 file_hash，就跳过
                continue

            if file_hash not in documents: #第一次遇到某个文件时，创建文档记录
                documents[file_hash] = {
                    "filename": item.get("filename", ""),
                    "file_hash": file_hash,
                    "file_ext": item.get("file_ext", ""),
                    "uploaded_at": item.get("uploaded_at", ""),
                    "chunk_count": 0,
                }

            documents[file_hash]["chunk_count"] += 1 #每遇到一个 chunk，chunk_count 加 1

        return list(documents.values())

    def delete_by_file_hash(self, file_hash: str):
        self.client.load_collection(collection_name=self.collection_name)
        #先把 Milvus 中的 collection 加载好，准备执行删除操作。collection_name="document_chunks"

        result = self.client.delete( #根据 file_hash 删除数据，
            # 删除document_chunks这个collection里所有file_hash等于指定值的记录。
            collection_name=self.collection_name,
            filter=f'file_hash == "{file_hash}"',
        )

        self.client.load_collection(collection_name=self.collection_name)
        return result
