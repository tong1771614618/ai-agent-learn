<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * AI 服务 — 封装与 Python FastAPI AI Service 的通信
 *
 * 架构：
 *   Laravel (PHP) → HTTP POST → FastAPI (Python, port 8001) → Qwen LLM
 *
 * 这是后端工程师最熟悉的模式：
 *   Service A 调 Service B，只是 B 恰好是 Python 写的
 */
class AiService
{
    private string $baseUrl;

    public function __construct()
    {
        $this->baseUrl = config('services.ai_service.url', 'http://127.0.0.1:8001');
    }

    /**
     * 解析用户查询意图
     *
     * @param string $query 用户自然语言输入，如 "有没有适合夏天跑步的鞋？"
     * @return array 结构化结果: {intent, keywords, category, budget_min, budget_max, brands}
     * @throws \RuntimeException AI 服务调用失败时抛出
     */
    public function parseQuery(string $query): array
    {
        $response = Http::timeout(30)
            ->post("{$this->baseUrl}/p01/parse-query", [
                'query' => $query,
            ]);

        if ($response->failed()) {
            Log::error('AI Service 调用失败', [
                'status' => $response->status(),
                'body' => $response->body(),
                'query' => $query,
            ]);
            throw new \RuntimeException('AI 服务暂时不可用，请稍后再试');
        }

        return $response->json();
    }

    /**
     * 项目 2: Agent 聊天
     *
     * 与 parseQuery 的区别：
     * - parseQuery 调 /p01/parse-query，LLM 单次调用返回结构化 JSON
     * - agentChat 调 /p02/chat，Python 侧执行 Agent Loop（可能多轮 LLM 调用）
     *
     * 所以 timeout 更长（60s vs 30s），因为 Agent 可能要循环好几轮。
     */
    public function agentChat(string $message): array
    {
        $response = Http::timeout(60)
            ->post("{$this->baseUrl}/p02/chat", [
                'message' => $message,
            ]);

        if ($response->failed()) {
            Log::error('Agent Chat 调用失败', [
                'status' => $response->status(),
                'body' => $response->body(),
                'message' => $message,
            ]);
            throw new \RuntimeException('Agent 服务暂时不可用，请稍后再试');
        }

        return $response->json();
    }

    /**
     * 项目 3: RAG 搜索
     *
     * 与其他项目的区别：
     * - 项目 1: LLM 返回结构化 JSON（意图解析）
     * - 项目 2: Agent Loop（LLM 调工具 + 多轮对话）
     * - 项目 3: Embedding → 向量检索 → 注入上下文 → LLM 生成
     *
     * 流程在 Python 侧：embed query → search ChromaDB → build RAG prompt → LLM generate
     * timeout 设为 60s，因为 embedding + LLM 两次 API 调用。
     */
    public function ragSearch(string $query): array
    {
        $response = Http::timeout(60)
            ->post("{$this->baseUrl}/p03/search", [
                'query' => $query,
            ]);

        if ($response->failed()) {
            Log::error('RAG Search 调用失败', [
                'status' => $response->status(),
                'body' => $response->body(),
                'query' => $query,
            ]);
            throw new \RuntimeException('RAG 搜索服务暂时不可用，请稍后再试');
        }

        return $response->json();
    }

    /**
     * 项目 4: HITL 售后 Agent — 聊天
     *
     * 与其他项目的区别：
     * - 项目 2: Agent 自主完成全部操作
     * - 项目 4: Agent 遇到高风险操作时暂停，返回审批请求
     *
     * 返回值可能是普通回答，也可能是 pending_approval 状态 + 审批请求详情。
     */
    public function hitlChat(string $message, ?string $sessionId = null): array
    {
        $response = Http::timeout(60)
            ->post("{$this->baseUrl}/p04/chat", [
                'message' => $message,
                'session_id' => $sessionId,
            ]);

        if ($response->failed()) {
            Log::error('HITL Chat 调用失败', [
                'status' => $response->status(),
                'body' => $response->body(),
                'message' => $message,
            ]);
            throw new \RuntimeException('售后 Agent 服务暂时不可用，请稍后再试');
        }

        return $response->json();
    }

    /**
     * 项目 4: HITL 售后 Agent — 审批
     *
     * 用户对 Agent 的操作提案做出批准/拒绝决定后调用。
     * Python 侧会从数据库恢复对话状态，注入审批决定后继续 Agent Loop。
     */
    public function hitlApprove(string $sessionId, bool $approved): array
    {
        $response = Http::timeout(60)
            ->post("{$this->baseUrl}/p04/approve", [
                'session_id' => $sessionId,
                'approved' => $approved,
            ]);

        if ($response->failed()) {
            Log::error('HITL Approve 调用失败', [
                'status' => $response->status(),
                'body' => $response->body(),
                'session_id' => $sessionId,
            ]);
            throw new \RuntimeException('审批处理失败，请稍后再试');
        }

        return $response->json();
    }
}
