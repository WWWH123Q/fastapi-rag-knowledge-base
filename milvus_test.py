from pymilvus import MilvusClient


# 这里的 milvus_demo.db 就是本地轻量版向量数据库文件
client = MilvusClient("./milvus_demo.db")

collection_name = "demo_collection"

# 如果集合已经存在，先删除，方便重复测试
if client.has_collection(collection_name):
    client.drop_collection(collection_name)

# 创建集合
client.create_collection(
    collection_name=collection_name,
    dimension=4,  # 这里先用 4 维向量做测试
)

# 插入几条测试数据
data = [
    {
        "id": 1,
        "vector": [0.1, 0.2, 0.3, 0.4],
        "text": "这是第一段文本"
    },
    {
        "id": 2,
        "vector": [0.2, 0.1, 0.4, 0.3],
        "text": "这是第二段文本"
    },
    {
        "id": 3,
        "vector": [0.9, 0.8, 0.7, 0.6],
        "text": "这是第三段文本"
    },
]

client.insert(
    collection_name=collection_name,
    data=data,
)

# 查询相似向量
results = client.search(
    collection_name=collection_name,
    data=[[0.1, 0.2, 0.3, 0.4]],
    limit=2,
    output_fields=["text"],
)

print(results)