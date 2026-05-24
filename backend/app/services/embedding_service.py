from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model_name
        self.model = SentenceTransformer(self.model_name) #真正加载模型，self.model 就是一个可以把文本转成向量的模型对象。
        self.dimension = self.model.get_sentence_embedding_dimension()
        # 默认使用的embedding模型是BAAI / bge - m3
        # BAAI / bge - m3是一个常用的embedding模型，可以把中文、英文、多语言文本转成向量。
        # 你不用自己训练它，只需要加载后调用encode()

        print(
            f"[EmbeddingService] model={self.model_name}, dimension={self.dimension}. "
            "If this differs from the existing Milvus collection dimension, "
            "rebuild the collection or delete milvus_demo.db."
        )
        # 加载一个embedding模型，然后提供两个方法：
        # 一个用于把单条文本转成向量，另一个用于把多条文本批量转成向量。


    def embed_text(self, text: str) -> list[float]: #单条文本向量化：embed_text，一条文本转成一个向量。
        vector = self.model.encode( #让 embedding 模型编码文本
            text,
            normalize_embeddings=True, #输出向量做归一化，把向量的长度统一变成 1。
        )
        return vector.tolist() #self.model.encode() 返回的通常是 NumPy 数组，.tolist() 会把它变成普通列表

    def embed_texts(self, texts: list[str]) -> list[list[float]]:#多条文本向量化
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )
        return vectors.tolist()
