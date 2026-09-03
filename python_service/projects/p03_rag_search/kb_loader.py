"""
==========================================================================
  AI 知识点: Chunking（文本分块策略）
==========================================================================

  【概念 4: Chunking（文本分块）】

  为什么需要分块？
  - 一整篇文档太长（几千字），embedding 模型有输入长度限制
  - 大块文本的向量"稀释"了细节信息，搜索精度下降
  - 小块让检索更精准——用户问"退货政策"，命中的是退换货那一节，不是整篇文档

  ┌──────────────────────────────────────────────────────────────────┐
  │ 分块策略         │ 说明                    │ 本项目              │
  ├──────────────────┼─────────────────────────┼─────────────────────┤
  │ 按 H2 段落分块  │ 每个二级标题为一个chunk │ ← 本项目使用        │
  │ 按 Q&A 分块     │ 每个问答对为一个chunk   │ 适合面试题库        │
  │ 固定长度分块     │ 每500字一个chunk        │ 最简单但语义可能断裂 │
  │ 滑动窗口分块     │ 500字+100字重叠         │ 避免边界信息丢失     │
  │ 递归分块         │ 按标题→段落→句子逐层    │ LangChain默认策略   │
  └──────────────────┴─────────────────────────┴─────────────────────┘

  本项目为什么按 H2 段落分块？
  知识库文件（policies.md, product-faq.md 等）是按章节组织的：
    ## 退换货政策
    ### 七天无理由退货
    ### 质量问题换货
    ## 物流配送政策
    ...

  每个 H2 章节是一个语义完整的主题单元。
  如果章节过长（>1500字符），会进一步按 H3 子标题拆分。

  上游：routes.py 的 /p03/init-kb 端点调用 load_knowledge_base()
  下游：返回的 chunks 传入 ChromaDB → 存入 vector_store.py
==========================================================================
"""

import os
from typing import List, Dict, Tuple


# ─── 知识库文件目录（项目根目录/knowledge/ecommerce/）────────────
KB_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'knowledge', 'ecommerce'
)

# 文件名 → 分类标签（前端展示用）
CATEGORY_MAP = {
    "policies": "POLICY",
    "product-faq": "FAQ",
    "category-knowledge": "KNOWLEDGE",
}

# 段落过长时按 H3 拆分的阈值
MAX_CHUNK_CHARS = 1500


def _parse_section_chunks(filepath: str) -> List[Dict]:
    """
    解析单个 markdown 文件，按 H2 (## ) 分块

    每个 H2 章节作为一个 chunk：
    - 包含标题 + 正文内容
    - 语义边界清晰（一个主题一个 chunk）
    - 过长的章节按 H3 (### ) 进一步拆分

    与旧版按 Q&A 分块的区别：
    - 旧版：只适合 "## Q:" 格式的面试题库
    - 新版：适合任何按章节组织的通用文档
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(filepath)
    base_name = filename.replace('.md', '')
    category = CATEGORY_MAP.get(base_name, base_name.upper())

    chunks = []
    current_h2 = None      # 当前 H2 标题
    current_lines = []     # 当前 H2 下的所有行
    in_code_block = False  # 跟踪代码块状态，避免误判 ## 标记

    for line in content.split('\n'):
        # 跟踪代码块开/关
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # 只在非代码块内识别 H2 标题
        if line.startswith('## ') and not in_code_block:
            # 保存上一个 H2 章节
            if current_h2 is not None:
                section_text = '\n'.join(current_lines).strip()
                if section_text:
                    _add_chunks(chunks, current_h2, section_text, filename, category)
            # 开始新的 H2 章节
            current_h2 = line.strip()
            current_lines = []
        elif current_h2 is not None:
            current_lines.append(line)

    # 别忘了最后一个 H2 章节
    if current_h2 is not None:
        section_text = '\n'.join(current_lines).strip()
        if section_text:
            _add_chunks(chunks, current_h2, section_text, filename, category)

    return chunks


def _add_chunks(
    chunks: List[Dict],
    h2_title: str,
    section_text: str,
    filename: str,
    category: str,
):
    """
    将一个 H2 章节添加到 chunks 列表中

    如果章节过长（> MAX_CHUNK_CHARS），按 H3 子标题进一步拆分。
    这样既保证了语义完整性，又不会因为单个 chunk 太长而稀释向量精度。
    """
    full_text = f"{h2_title}\n{section_text}"

    if len(full_text) <= MAX_CHUNK_CHARS:
        # 章节长度适中，作为一个完整 chunk
        chunks.append({
            "text": full_text,
            "source": filename,
            "category": category,
        })
    else:
        # 章节过长，尝试按 H3 拆分
        sub_chunks = _split_by_h3(h2_title, section_text)
        if len(sub_chunks) == 1:
            # 没有 H3 子标题可以拆，就保持为一个 chunk（虽然长但语义完整）
            chunks.append({
                "text": full_text,
                "source": filename,
                "category": category,
            })
        else:
            for sub_title, sub_text in sub_chunks:
                chunks.append({
                    "text": f"{sub_title}\n{sub_text}",
                    "source": filename,
                    "category": category,
                })


def _split_by_h3(h2_title: str, section_text: str) -> List[Tuple[str, str]]:
    """
    将过长的 H2 章节按 H3 子标题拆分

    返回: [(标题, 内容), ...]
    如果没有 H3 子标题，返回 [(h2_title, section_text)]
    """
    sub_chunks = []
    current_h3 = None
    current_lines = []
    intro_lines = []  # H3 之前的引言段落
    in_code_block = False

    for line in section_text.split('\n'):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        if line.startswith('### ') and not in_code_block:
            # 保存上一个 H3 子节
            if current_h3 is not None:
                sub_text = '\n'.join(current_lines).strip()
                if sub_text:
                    sub_chunks.append((current_h3, sub_text))
            elif intro_lines:
                # H2 下、第一个 H3 之前的引言段落
                intro_text = '\n'.join(intro_lines).strip()
                if intro_text:
                    sub_chunks.append((h2_title, intro_text))
            current_h3 = line.strip()
            current_lines = []
        elif current_h3 is not None:
            current_lines.append(line)
        else:
            intro_lines.append(line)

    # 最后一个 H3 子节
    if current_h3 is not None:
        sub_text = '\n'.join(current_lines).strip()
        if sub_text:
            sub_chunks.append((current_h3, sub_text))

    # 如果没有找到任何 H3，返回原文
    if not sub_chunks:
        return [(h2_title, section_text)]

    return sub_chunks


def load_knowledge_base() -> List[Dict]:
    """
    加载知识库目录下所有 .md 文件，返回分块后的 chunk 列表

    Returns:
        List[Dict]: 每个 dict 包含 text, source, category
    """
    if not os.path.exists(KB_DIR):
        raise FileNotFoundError(f"知识库目录不存在: {KB_DIR}")

    all_chunks = []

    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(KB_DIR, filename)
        chunks = _parse_section_chunks(filepath)
        all_chunks.extend(chunks)
        print(f"[KB] 加载 {filename}: {len(chunks)} 个 chunks")

    return all_chunks
