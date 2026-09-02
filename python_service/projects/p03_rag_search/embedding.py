"""
==========================================================================
  AI 知识点: Embedding（文本向量化）
==========================================================================

  【概念 1: Embedding（嵌入/向量化）】

  什么是 Embedding？
  把一段文本"压缩"成一个固定长度的数字数组（向量）。
  含义相近的文本，向量也相近（在向量空间中距离近）。

  例：
    "PHP的垃圾回收" → [0.12, -0.34, 0.56, ..., 0.78]  (384个数字)
    "PHP GC机制"    → [0.11, -0.33, 0.55, ..., 0.77]  (非常接近!)
    "今天天气不错"  → [0.89, 0.12, -0.67, ..., 0.03]  (完全不同)

  ┌──────────────────────────────────────────────────────────────┐
  │ Embedding 方式              │ 维度  │ 说明                  │
  ├─────────────────────────────┼───────┼────────────────────────┤
  │ sentence-transformers (本地) │ 384   │ 本项目使用 ←          │
  │ Qwen text-embedding-v3      │ 1024  │ 云端API(需Token Plan) │
  │ OpenAI text-embedding-3     │ 1536  │ 云端API(需付费)      │
  └─────────────────────────────┴───────┴────────────────────────┘

  为什么用本地模型？
  - Token Plan API 不支持 Embedding 模型
  - 本地模型零延迟、零费用、可离线
  - 对小型知识库来说精度完全够用

  模型选择：paraphrase-multilingual-MiniLM-L12-v2
  - 384 维（轻量快速）
  - 支持中文（multilingual）
  - 首次使用自动下载（~120MB），之后走缓存

  【Embedding 在 RAG 中的角色】

  建库阶段：文档 → Embedding → 存入向量数据库
  查询阶段：问题 → Embedding → 在向量数据库中搜索最相似的文档

  上游：ai_service.py 调用 get_embedding() 和 get_embeddings()
  下游：返回的向量传给 vector_store.py 进行存储或搜索
==========================================================================
"""

from typing import List, Optional

# ─── 全局单例（模型只加载一次）──────────────────────────────────
_model = None
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  # 该模型的向量维度


def _get_model():
    """懒加载 sentence-transformers 模型（单例）"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[Embedding] 加载模型: {MODEL_NAME} (首次可能需要下载 ~120MB)")
        _model = SentenceTransformer(MODEL_NAME)
        print(f"[Embedding] 模型加载完成, 维度: {EMBEDDING_DIM}")
    return _model


def get_embedding(text: str) -> List[float]:
    """
    将单段文本转为向量

    Args:
        text: 输入文本（一段知识、一个问题等）

    Returns:
        List[float]: 384 维的浮点数向量
    """
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    批量将多段文本转为向量

    Args:
        texts: 输入文本列表

    Returns:
        List[List[float]]: 每段文本对应一个 384 维向量

    sentence-transformers 的 encode() 支持批量处理，
    内部会自动优化 batch size，比逐条调用快得多。
    """
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return [e.tolist() for e in embeddings]
