<?php

namespace App\Http\Controllers\Api\V2;

use App\Http\Controllers\Controller;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 2: AI 商品搜索 Agent — 聊天控制器
 *
 * 与项目 1 的架构对比：
 *
 *   项目 1: PHP → Python (LLM 返回 JSON) → PHP 查 MySQL → 返回
 *   项目 2: PHP → Python (Agent Loop: LLM 决定调工具 → 执行 → LLM 回答) → 返回
 *
 * 项目 2 的 PHP 控制器更简单，因为 AI 逻辑全部在 Python 侧完成。
 * PHP 的角色变成了"代理"——接收请求、转发给 Python、返回结果。
 *
 * 这在实际项目中很常见：
 *   前端 → BFF (Backend for Frontend) → 微服务
 *   这里 PHP 就是 BFF，Python 是微服务。
 */
class AgentChatController extends Controller
{
    public function chat(Request $request, AiService $aiService): JsonResponse
    {
        $steps = [];

        // ─── 1. 校验输入 ──────────────────────────────
        $t = microtime(true);
        $request->validate([
            'message' => 'required|string|max:1000',
        ]);
        $steps[] = [
            'name' => '接收请求',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => ['message' => $request->input('message')],
        ];

        // ─── 2. 调用 Python Agent ─────────────────────
        $t = microtime(true);
        try {
            $result = $aiService->agentChat($request->input('message'));
        } catch (\RuntimeException $e) {
            return response()->json([
                'error' => $e->getMessage(),
            ], 503);
        }
        $steps[] = [
            'name' => 'Agent 执行',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => [
                'rounds' => $result['rounds'] ?? 1,
                'steps_count' => count($result['steps'] ?? []),
            ],
        ];

        // ─── 3. 返回结果 ──────────────────────────────
        return response()->json([
            '_steps' => $steps,
            'answer' => $result['answer'],
            'agent_steps' => $result['steps'] ?? [],
            'rounds' => $result['rounds'] ?? 1,
        ]);
    }
}
