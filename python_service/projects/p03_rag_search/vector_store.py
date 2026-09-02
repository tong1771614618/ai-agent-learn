"""
==========================================================================
  AI 知识点: 向量数据库（ChromaDB）+ 相似度搜索
==========================================================================

  【概念 5: 向量数据库（Vector Database）】

  为什么需要向量数据库？
  - 普通数据库（MySQL）擅长精确匹配：WHERE name = 'PHP'
  - 向量数据库擅长相似匹配：找到和"PHP的GC"最像的文档

  ┌──────────────────────────────────────────────────────────────┐
  │ 向量数据库         │ 特点                                     │
  ├────────────────────┼──────────────────────────────────────────┤
  │ ChromaDB           │ 轻量,Python原生,本项目使用 ←             │
  │ FAISS              │ Meta出品,纯计算库,不是真正的数据库       │
  │ Pinecone           │ 云服务,适合生产环境                      │
  │ Milvus             │ 开源,适合大规模生产环境                  │
  │ Weaviate           │ 开源,支持混合搜索                        │
  └────────────────────┴──────────────────────────────────────────┘

  【概念 2: 余弦相似度（Cosine Similarity）】

  两个向量之间有多"像"？用余弦相似度衡量：
  - 1.0 = 完全相同方向（极其相似）
  - 0.0 = 正交（无关）
  - -1.0 = 完全相反方向（语义相反）

  知识库中的 chunk A 向量 = [0.1, 0.5, 0.3, ...]
  用户问题 Q 的向量       = [0.1, 0.4, 0.3, ...]
  cosine_sim(A, Q) = 0.95  → 非常相似！

  ChromaDB 默认使用 L2 距离（越小越相似），
  我们通过 1 - distance 转换为相似度分数（越大越相似）。

  上游：ai_service.py 调用 init_collection() 和 search_similar()
  下游：返回的 chunks + scores 用于构建 RAG Prompt

  【为什么这么做】
  ChromaDB persistent client 把数据存到磁盘，
  重启服务后知识库不需要重新 embedding，节省 API 调用费用。
==========================================================================
"""

import os
import chromadb
from typing import List, Dict, Optional
from python_service.config import settings


# ─── ChromaDB 持久化存储路径 ────────────────────────────────────
CHROMA_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'storage', 'chroma_p03'
)

# 全局单例
_client: Optional[chromadb.ClientAPI] = None
_collection = None


def _get_client() -> chromadb.ClientAPI:
    """获取 ChromaDB 客户端（单例）"""
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def init_collection():
    """初始化/获取向量集合"""
    global _collection
    client = _get_client()
    _collection = client.get_or_create_collection(
        name="interview_kb",
        metadata={"hnsw:space": "l2"},  # L2 距离（欧氏距离）
    )
    return _collection


def add_documents(
    texts: List[str],
    metadatas: List[Dict],
    ids: List[str],
):
    """
    批量添加文档到向量数据库

    ChromaDB 内置 ONNX embedding 模型（all-MiniLM-L6-v2, 384维），
    传入 documents 后自动完成向量化，无需手动调用 embedding API。

    Args:
        texts: 文档文本列表
        metadatas: 元数据列表（source, category 等）
        ids: 唯一 ID 列表
    """
    col = init_collection()
    # 先清空旧数据（重新初始化时）
    if col.count() > 0:
        col.delete(ids=col.get()["ids"])
    col.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
    )


def search_similar(
    query_text: str,
    top_k: int = 3,
) -> List[Dict]:
    """
    搜索与查询文本最相似的文档

    ChromaDB 内部自动把 query_text 转为向量再搜索。

    Args:
        query_text: 查询文本（用户的问题）
        top_k: 返回最相似的前 K 个结果

    Returns:
        List[Dict]: 每个 dict 包含 text, source, category, score
    """
    col = init_collection()

    if col.count() == 0:
        return []

    results = col.query(
        query_texts=[query_text],
        n_results=min(top_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results['documents'][0])):
        # ChromaDB L2 distance → 转换为相似度分数（越小越相似 → 越大越相似）
        distance = results['distances'][0][i]
        score = max(0, 1 - distance / 2)  # 简单归一化

        output.append({
            "text": results['documents'][0][i],
            "source": results['metadatas'][0][i].get('source', ''),
            "category": results['metadatas'][0][i].get('category', ''),
            "score": round(score, 4),
        })

    return output


def get_count() -> int:
    """获取知识库中的文档总数"""
    col = init_collection()
    return col.count()
