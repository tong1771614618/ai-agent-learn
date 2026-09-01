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
}
