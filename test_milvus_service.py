from app.services.milvus_service import MilvusService


milvus_service = MilvusService(
    db_path="backend/milvus_demo.db",
    collection_name="document_chunks",
    dimension=4,
)

data = [
    {
        "id": 101,
        "vector": [0.1, 0.2, 0.3, 0.4],
        "text": "FastAPI 是一个高性能 Python Web 框架"
    },
    {
        "id": 102,
        "vector": [0.9, 0.8, 0.7, 0.6],
        "text": "Milvus 是一个向量数据库，用于相似度检索"
    },
]

milvus_service.insert_chunks(data)

results = milvus_service.search(
    query_vector=[0.1, 0.2, 0.3, 0.4],
    limit=2,
)

print(results)