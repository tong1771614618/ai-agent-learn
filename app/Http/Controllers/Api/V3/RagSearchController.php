<?php

namespace App\Http\Controllers\Api\V3;

use App\Http\Controllers\Controller;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 3: AI 搜索引擎 (RAG) — 搜索控制器
 *
 * 架构对比：
 *
 *   项目 1: PHP → Python (LLM 返回 JSON) → PHP 查 MySQL → 返回
 *   项目 2: PHP → Python (Agent Loop: LLM 调工具 → 执行 → 回答) → 返回
 *   项目 3: PHP → Python (Embedding → 向量检索 → 注入上下文 → LLM 生成) → 返回
 *
 * 项目 3 的 PHP 控制器依然保持"代理"角色：
 * 接收用户问题 → 调用 Python RAG 服务 → 返回答案 + 来源引用
 */
class RagSearchController extends Controller
{
    public function search(Request $request, AiService $aiService): JsonResponse
    {
        $steps = [];

        // ─── 1. 校验输入 ──────────────────────────────
        $t = microtime(true);
        $request->validate([
            'query' => 'required|string|max:1000',
        ]);
        $steps[] = [
            'name' => '接收请求',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => ['query' => $request->input('query')],
        ];

        // ─── 2. 调用 Python RAG 服务 ──────────────────
        $t = microtime(true);
        try {
            $result = $aiService->ragSearch($request->input('query'));
        } catch (\RuntimeException $e) {
            return response()->json([
                'error' => $e->getMessage(),
            ], 503);
        }
        $steps[] = [
            'name' => 'RAG 搜索',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => [
                'retrieved_count' => $result['retrieved_count'] ?? 0,
                'total_chunks' => $result['total_chunks'] ?? 0,
            ],
        ];

        // ─── 3. 格式化来源引用 ────────────────────────
        $sources = array_map(function ($s) {
            return [
                'source' => $s['source'] ?? '',
                'category' => $s['category'] ?? '',
                'score' => $s['score'] ?? 0,
                'text' => mb_substr($s['text'] ?? '', 0, 200),
            ];
        }, $result['sources'] ?? []);

        // ─── 4. 返回结果 ──────────────────────────────
        return response()->json([
            '_steps' => $steps,
            'answer' => $result['answer'],
            'sources' => $sources,
            'retrieved_count' => $result['retrieved_count'] ?? 0,
            'total_chunks' => $result['total_chunks'] ?? 0,
        ]);
    }
}
