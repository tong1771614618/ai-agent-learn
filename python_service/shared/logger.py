"""
==========================================================================
  AI 知识点: Agent 统一日志系统
==========================================================================

  所有项目的 AI 调用日志统一从这里输出。
  目的：实时观察 Agent 的思考过程，辅助学习和调试。

  输出两个目标：
    1. 终端（彩色，实时）
    2. 文件 storage/logs/agent.log（纯文本，事后查看）

  覆盖场景（P01-P12 全部适用）：
    - request/complete: 请求开始/结束
    - llm: LLM 调用参数 + Token 消耗
    - tool_decision/tool_result: 工具调用决策和执行结果
    - guardrail: 安全检查（P04+）
    - hitl: 人工审批（P04+）
    - rag: 向量检索（P05+）
    - sql: Text-to-SQL（P07+）
    - agent: 多 Agent 委派（P11+）
    - context: 上下文/Memory（P03+）

  使用方式：
    from python_service.shared.logger import agent_log
    log = agent_log("P02")
    log.request("推荐500以内的篮球鞋")
    log.llm(round=1, model="qwen3.7-plus", temp=0.3, usage=usage_obj)
    ...
    log.complete(rounds=2, tokens=695, time=8.2)
==========================================================================
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Any


# ─── 日志文件路径 ──────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'storage', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'agent.log')

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# ─── 文件 logger（纯文本，不染色）─────────────────────────────
_file_logger = logging.getLogger('agent_file')
_file_logger.setLevel(logging.DEBUG)
_file_logger.propagate = False

if not _file_logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(message)s'))
    _file_logger.addHandler(fh)


# ─── ANSI 颜色 ─────────────────────────────────────────────────
class C:
    """终端颜色"""
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    CYAN    = '\033[36m'
    GREEN   = '\033[32m'
    YELLOW  = '\033[33m'
    RED     = '\033[31m'
    MAGENTA = '\033[35m'
    BLUE    = '\033[34m'
    WHITE   = '\033[37m'
    GRAY    = '\033[90m'


def _strip_ansi(text: str) -> str:
    """去掉 ANSI 颜色码，用于写入文件"""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)


def _out(colored: str):
    """同时输出到终端（彩色）和文件（纯文本）"""
    print(colored, flush=True)
    _file_logger.info(_strip_ansi(colored))


def _kv(key: str, val: Any, color: str = '') -> str:
    """格式化 key=value 对"""
    v = f'{val}'
    if isinstance(val, float):
        v = f'{val:.1f}'
    return f'{C.GRAY}{key}={color}{v}{C.RESET}'


def _preview(text: str, max_len: int = 60) -> str:
    """截断长文本"""
    text = str(text).replace('\n', ' ').strip()
    if len(text) > max_len:
        return text[:max_len] + '...'
    return text


class AgentLogger:
    """
    Agent 日志器 — 每个项目创建一个实例

    用法:
        log = AgentLogger("P02")
        log.request("用户消息")
        log.llm(round=1, ...)
        log.complete(rounds=2, ...)
    """

    def __init__(self, project: str):
        self.project = project
        self._req_id: Optional[str] = None
        self._start_time: float = 0
        self._total_tokens: int = 0

    def _gen_id(self) -> str:
        """生成短请求 ID"""
        import hashlib
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:4]

    # ══════════════════════════════════════════════════════════
    #  核心方法（P01-P12 都会用）
    # ══════════════════════════════════════════════════════════

    def request(self, message: str):
        """记录请求开始"""
        self._req_id = self._gen_id()
        self._start_time = time.time()
        self._total_tokens = 0
        now = datetime.now().strftime('%H:%M:%S')
        _out(f'\n{C.DIM}━━━ {C.RESET}{C.CYAN}[{self.project}]{C.RESET} {C.BOLD}#{self._req_id}{C.RESET} '
             f'{C.WHITE}"{_preview(message, 40)}"{C.RESET}  {C.GRAY}{now}{C.RESET}{C.DIM} ━━━{C.RESET}')

    def llm(self, round: int = 1, model: str = '', temp: float = 0,
            usage: Any = None, decision: str = '', context_tokens: int = 0):
        """
        记录一次 LLM 调用

        Args:
            round: 当前 Agent 循环轮次
            model: 模型名
            temp: temperature
            usage: OpenAI usage 对象 或 dict {prompt_tokens, completion_tokens, total_tokens}
            decision: 预设决策标记 ("tool"/"answer"/"")
            context_tokens: 上下文 token 数（用于 Memory 场景）
        """
        # 解析 token
        in_tok = out_tok = total_tok = 0
        if usage:
            if hasattr(usage, 'prompt_tokens'):
                in_tok = usage.prompt_tokens or 0
                out_tok = usage.completion_tokens or 0
                total_tok = usage.total_tokens or 0
            elif isinstance(usage, dict):
                in_tok = usage.get('prompt_tokens', 0) or 0
                out_tok = usage.get('completion_tokens', 0) or 0
                total_tok = usage.get('total_tokens', 0) or 0
        self._total_tokens += total_tok

        parts = [f'{C.DIM}[R{round}]{C.RESET} {C.BOLD}LLM{C.RESET}']
        if model:
            parts.append(_kv('model', model, C.BLUE))
        if temp:
            parts.append(_kv('temp', temp))

        line = '  '.join(parts)
        _out(line)

        if context_tokens:
            _out(f'     {_kv("ctx", str(context_tokens) + " tokens")}')

    def tool_decision(self, name: str, args: dict):
        """记录 LLM 决定调用工具"""
        args_str = ', '.join(f'{C.GRAY}{k}={C.MAGENTA}{v}{C.RESET}' for k, v in args.items() if v)
        _out(f'     {C.GREEN}→{C.RESET} tool: {C.BOLD}{name}{C.RESET}({args_str})')

    def tool_tokens(self, usage: Any):
        """记录 LLM 调用的 token 消耗（单独一行）"""
        in_tok = out_tok = total_tok = 0
        if usage:
            if hasattr(usage, 'prompt_tokens'):
                in_tok = usage.prompt_tokens or 0
                out_tok = usage.completion_tokens or 0
                total_tok = usage.total_tokens or 0
            elif isinstance(usage, dict):
                in_tok = usage.get('prompt_tokens', 0) or 0
                out_tok = usage.get('completion_tokens', 0) or 0
                total_tok = usage.get('total_tokens', 0) or 0
        self._total_tokens += total_tok
        _out(f'     {C.GRAY}⏱ in={in_tok} out={out_tok} total={total_tok}{C.RESET}')

    def tool_result(self, name: str, duration_ms: float, summary: str,
                    preview: Optional[List[dict]] = None):
        """
        记录工具执行结果

        Args:
            name: 工具名
            duration_ms: 执行耗时
            summary: 一句话结果摘要（如 "3 件商品"）
            preview: 结果预览列表（每项是 dict，只展示关键字段）
        """
        _out(f'{C.DIM}[T]{C.RESET} {C.BOLD}{name}{C.RESET}  {C.YELLOW}{duration_ms:.0f}ms{C.RESET}')
        _out(f'     结果: {C.GREEN}{summary}{C.RESET}')
        if preview:
            for i, item in enumerate(preview[:3]):  # 最多展示 3 条
                prefix = '└' if i == len(preview[:3]) - 1 else '┌' if i == 0 else '├'
                parts = ' | '.join(str(v) for v in item.values() if v is not None)
                _out(f'     {C.GRAY}{prefix}{C.RESET} {_preview(parts, 60)}')

    def answer(self, round: int, usage: Any = None, preview: str = ''):
        """记录 LLM 生成最终回答"""
        in_tok = out_tok = total_tok = 0
        if usage:
            if hasattr(usage, 'prompt_tokens'):
                in_tok = usage.prompt_tokens or 0
                out_tok = usage.completion_tokens or 0
                total_tok = usage.total_tokens or 0
            elif isinstance(usage, dict):
                in_tok = usage.get('prompt_tokens', 0) or 0
                out_tok = usage.get('completion_tokens', 0) or 0
                total_tok = usage.get('total_tokens', 0) or 0
        self._total_tokens += total_tok

        _out(f'{C.DIM}[R{round}]{C.RESET} {C.BOLD}LLM{C.RESET}')
        _out(f'     {C.GREEN}→ answer{C.RESET}')
        _out(f'     {C.GRAY}⏱ in={in_tok} out={out_tok} total={total_tok}{C.RESET}')
        if preview:
            _out(f'     预览: {C.WHITE}{_preview(preview, 50)}{C.RESET}')

    def complete(self, rounds: int = 1, tokens: int = 0, time_s: float = 0,
                 agents: int = 0):
        """记录请求完成"""
        elapsed = time_s or (time.time() - self._start_time)
        total = tokens or self._total_tokens
        parts = [f'{C.GREEN}✓{C.RESET} {rounds}轮']
        if agents:
            parts.append(f'{agents} agents')
        parts.append(f'{C.CYAN}{total}{C.RESET} tokens')
        parts.append(f'{C.YELLOW}{elapsed:.1f}s{C.RESET}')
        _out(f'{C.DIM}━━━ {" | ".join(parts)} ━━━━━━━━━━━━━━━━━━━{C.RESET}\n')

    # ══════════════════════════════════════════════════════════
    #  扩展方法（P04+ 项目使用，先预留接口）
    # ══════════════════════════════════════════════════════════

    def guardrail(self, name: str, passed: bool, rule: str = ''):
        """记录 Guardrail 安全检查（P04+）"""
        icon = f'{C.GREEN}PASS{C.RESET}' if passed else f'{C.RED}BLOCK{C.RESET}'
        _out(f'{C.DIM}[⛔]{C.RESET} Guardrail: {C.BOLD}{name}{C.RESET}  {icon}')
        if rule:
            _out(f'     规则: {C.GRAY}{rule}{C.RESET}')

    def hitl(self, reason: str, resolved: bool = False):
        """记录 Human-in-the-Loop 审批（P04+）"""
        if resolved:
            _out(f'{C.DIM}[👤]{C.RESET} HITL: {C.GREEN}{reason}{C.RESET}')
        else:
            _out(f'{C.DIM}[👤]{C.RESET} HITL: {C.YELLOW}等待审批{C.RESET} — {reason}')

    def rag(self, query: str = '', total_chunks: int = 0, retrieved: int = 0,
            model: str = '', top_results: Optional[List[dict]] = None):
        """记录 RAG 检索过程（P05+）"""
        _out(f'{C.DIM}[RAG]{C.RESET} {C.BOLD}检索{C.RESET}')
        if model:
            _out(f'      {_kv("model", model, C.BLUE)}')
        if query:
            _out(f'      query: {C.WHITE}"{_preview(query, 40)}"{C.RESET}')
        if total_chunks:
            _out(f'      召回 {C.GREEN}{retrieved}{C.RESET}/{total_chunks} chunks')
        if top_results:
            for i, r in enumerate(top_results[:3]):
                score = r.get('score', 0)
                text = r.get('text', '')
                prefix = '└' if i == len(top_results[:3]) - 1 else '┌' if i == 0 else '├'
                _out(f'      {C.GRAY}{prefix}{C.RESET} [{score:.2f}] {_preview(text, 50)}')

    def sql(self, query: str, valid: bool = True, note: str = ''):
        """记录 Text-to-SQL（P07+）"""
        status = f'{C.GREEN}SAFE{C.RESET}' if valid else f'{C.RED}UNSAFE{C.RESET}'
        _out(f'{C.DIM}[SQL]{C.RESET} {C.BOLD}{status}{C.RESET}')
        _out(f'      {C.GRAY}{_preview(query, 70)}{C.RESET}')
        if note:
            _out(f'      备注: {note}')

    def agent(self, name: str, action: str = '接管', reason: str = ''):
        """记录 Multi-Agent 委派（P11+）"""
        _out(f'{C.DIM}[🤖]{C.RESET} {C.BOLD}{name}{C.RESET}  {action}')
        if reason:
            _out(f'      原因: {C.GRAY}{reason}{C.RESET}')

    def context(self, total_tokens: int = 0, limit: int = 0, turns: int = 0):
        """记录上下文/Memory 信息（P03+）"""
        parts = []
        if total_tokens:
            parts.append(f'{C.GRAY}ctx={C.CYAN}{total_tokens}{C.RESET}')
        if limit:
            parts.append(f'{C.GRAY}limit={limit}{C.RESET}')
        if turns:
            parts.append(f'{C.GRAY}turns={turns}{C.RESET}')
        _out(f'{C.DIM}[CTX]{C.RESET} {" ".join(parts)}')


def agent_log(project: str) -> AgentLogger:
    """创建 Agent 日志器（工厂函数）"""
    return AgentLogger(project)
