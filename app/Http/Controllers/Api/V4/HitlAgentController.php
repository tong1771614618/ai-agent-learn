<?php

namespace App\Http\Controllers\Api\V4;

use App\Http\Controllers\Controller;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 4: 售后 Agent (HITL) — 控制器
 *
 * 架构对比：
 *
 *   项目 1: PHP → Python (LLM 返回 JSON) → PHP 查 MySQL → 返回
 *   项目 2: PHP → Python (Agent Loop: LLM 调工具 → 执行 → 回答) → 返回
 *   项目 3: PHP → Python (Embedding → 向量检索 → 注入上下文 → LLM 生成) → 返回
 *   项目 4: PHP → Python (Agent + HITL: 工具调审批 → 暂停 → 用户决定 → 继续) → 返回
 *
 * 项目 4 的 PHP 控制器有两个端点：
 * 1. chat()      — 发送消息，可能返回审批请求
 * 2. approve()   — 提交审批决定，Agent 继续处理
 */
class HitlAgentController extends Controller
{
    public function chat(Request $request, AiService $aiService): JsonResponse
    {
        $request->validate([
            'message' => 'required|string|max:2000',
            'session_id' => 'nullable|string|max:64',
        ]);

        try {
            $result = $aiService->hitlChat(
                $request->input('message'),
                $request->input('session_id'),
            );
        } catch (\RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 503);
        }

        return response()->json($result);
    }

    public function approve(Request $request, AiService $aiService): JsonResponse
    {
        $request->validate([
            'session_id' => 'required|string|max:64',
            'approved' => 'required|boolean',
        ]);

        try {
            $result = $aiService->hitlApprove(
                $request->input('session_id'),
                $request->input('approved'),
            );
        } catch (\RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 503);
        }

        return response()->json($result);
    }
}
