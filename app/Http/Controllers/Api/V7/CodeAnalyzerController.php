<?php

namespace App\Http\Controllers\Api\V7;

use App\Http\Controllers\Controller;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 7: AI 代码分析器 — 控制器
 *
 * 架构演进：
 *   项目 1-4: PHP → Python → LLM → 返回 JSON（同步等待）
 *   项目 7:   PHP → Python → LLM → 返回 JSON（非流式，走 PHP）
 *                              或 → StreamingResponse（流式，前端直连 Python）
 *
 * 注意：流式审查（review-stream）前端直接调 Python FastAPI，
 * 因为 PHP Http client 不方便处理 SSE 流。
 * 非流式审查（review）走 PHP → Python 的标准路径。
 */
class CodeAnalyzerController extends Controller
{
    public function review(Request $request, AiService $aiService): JsonResponse
    {
        $request->validate([
            'code' => 'required|string|max:50000',
            'language' => 'nullable|string|max:20',
            'focus' => 'nullable|string|in:security,performance,style',
        ]);

        try {
            $result = $aiService->codeReview(
                $request->input('code'),
                $request->input('language'),
                $request->input('focus'),
            );
        } catch (\RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 503);
        }

        return response()->json($result);
    }
}
