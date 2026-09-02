"""
==========================================================================
  AI 知识点: Chunking（文本分块策略）
==========================================================================

  【概念 4: Chunking（文本分块）】

  为什么需要分块？
  - 一整篇文档太长（几千字），embedding 模型有输入长度限制
  - 大块文本的向量"稀释"了细节信息，搜索精度下降
  - 小块让检索更精准——用户问"PHP GC"，命中的是 GC 那一段，不是整篇 PHP 文档

  ┌──────────────────────────────────────────────────────────────────┐
  │ 分块策略         │ 说明                    │ 本项目              │
  ├──────────────────┼─────────────────────────┼─────────────────────┤
  │ 按 Q&A 分块     │ 每个问答对为一个chunk   │ ← 本项目使用         │
  │ 按段落分块      │ 每段为一个chunk         │ 适合文章类文档       │
  │ 固定长度分块     │ 每500字一个chunk        │ 最简单但语义可能断裂 │
  │ 滑动窗口分块     │ 500字+100字重叠         │ 避免边界信息丢失     │
  │ 递归分块         │ 按标题→段落→句子逐层    │ LangChain默认策略   │
  └──────────────────┴─────────────────────────┴─────────────────────┘

  本项目为什么按 Q&A 分块？
  知识库文件（php.md, linux.md 等）的格式是：
    ## Q: 问题
    回答内容...

  每个 "## Q:" 天然就是一个语义完整的单元。
  这种分块方式最干净，不需要复杂的文本切割逻辑。

  上游：routes.py 的 /p03/init-kb 端点调用 load_knowledge_base()
  下游：返回的 chunks 传给 embedding.py 生成向量 → 存入 vector_store.py
==========================================================================
"""

import os
from typing import List, Dict


# ─── 知识库文件目录 ─────────────────────────────────────────────
KB_DIR = os.path.expanduser("~/ai-work/interview-kb/knowledge")


def _parse_qa_chunks(filepath: str) -> List[Dict]:
    """
    解析单个 markdown 文件，按 ## Q: 分块

    每个 Q&A 对作为一个 chunk：
    - 包含完整的问 + 答
    - 语义边界清晰
    - 不会因为固定长度切割导致答案被截断
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    category = os.path.basename(filepath).replace('.md', '').upper()
    chunks = []

    current_q = None
    current_a_lines = []
    in_code_block = False  # 跟踪代码块状态，避免误判 ## 标记

    for line in content.split('\n'):
        # 跟踪代码块开/关
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # 只在非代码块内识别 Q 标题
        if line.startswith('## Q') and not in_code_block:
            # 保存上一个 Q&A
            if current_q is not None:
                answer = '\n'.join(current_a_lines).strip()
                if answer:
                    chunks.append({
                        "question": current_q,
                        "text": f"{current_q}\n{answer}",
                        "source": os.path.basename(filepath),
                        "category": category,
                    })
            # 开始新的 Q&A
            current_q = line.strip()
            current_a_lines = []
        elif current_q is not None:
            current_a_lines.append(line)

    # 别忘了最后一个 Q&A
    if current_q is not None:
        answer = '\n'.join(current_a_lines).strip()
        if answer:
            chunks.append({
                "question": current_q,
                "text": f"{current_q}\n{answer}",
                "source": os.path.basename(filepath),
                "category": category,
            })

    return chunks


def load_knowledge_base() -> List[Dict]:
    """
    加载知识库目录下所有 .md 文件，返回 Q&A chunk 列表

    Returns:
        List[Dict]: 每个 dict 包含 question, text, source, category
    """
    if not os.path.exists(KB_DIR):
        raise FileNotFoundError(f"知识库目录不存在: {KB_DIR}")

    all_chunks = []

    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(KB_DIR, filename)
        chunks = _parse_qa_chunks(filepath)
        all_chunks.extend(chunks)
        print(f"[KB] 加载 {filename}: {len(chunks)} 个 Q&A")

    return all_chunks
