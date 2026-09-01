<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Product;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 1: AI 商品客服 — 搜索控制器
 *
 * 完整流程：
 *   用户输入 "有没有适合夏天跑步的鞋？"
 *       ↓
 *   AiService → Python FastAPI → Qwen LLM
 *       ↓
 *   结构化结果: {intent: "search", keywords: ["跑步","鞋","夏天"], category: "running"}
 *       ↓
 *   Eloquent 查询 MySQL
 *       ↓
 *   返回匹配商品
 */
class ProductSearchController extends Controller
{
    public function search(Request $request, AiService $aiService): JsonResponse
    {
        // ─── _steps: 前端折叠步骤面板的数据来源 ─────────
        // 每个项目都可以复用这个模式：记录每步的名称、耗时、详情
        $steps = [];

        // ─── 1. 校验输入 ──────────────────────────────
        $t = microtime(true);
        $request->validate([
            'query' => 'required|string|max:500',
        ]);
        $steps[] = [
            'name' => '接收请求',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => ['query' => $request->input('query')],
        ];

        $userQuery = $request->input('query');

        // ─── 2. 调用 AI 解析用户意图 ─────────────────
        $t = microtime(true);
        try {
            $parsed = $aiService->parseQuery($userQuery);
        } catch (\RuntimeException $e) {
            return response()->json([
                'error' => $e->getMessage(),
            ], 503);
        }
        // 记录 AI 调用耗时 — 前端会展示为一个可折叠步骤
        $steps[] = [
            'name' => 'AI 意图解析',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => $parsed,  // 把 LLM 返回的完整结构化数据放进去
        ];

        // ─── 3. 用结构化数据查询 MySQL ────────────────
        // 这就是项目 1 的核心认知：
        // LLM 不做业务逻辑，它只是把自然语言转成结构化数据
        // 真正的查询逻辑仍然由 PHP + MySQL 完成
        $t = microtime(true);
        $query = Product::query()
            ->active()                          // 只查上架商品
            ->inCategory($parsed['category'])   // 按分类筛选
            ->inBudget($parsed['budget_max'])   // 按预算筛选
            ->inBrands($parsed['brands'] ?? []) // 按品牌筛选
            ->inUrgency($parsed['urgency'][0] ?? null) // 按紧急程度筛选（取第一个值）
            ->matchKeywords($parsed['keywords'] ?? []); // 关键词搜索

        $products = $query->limit(20)->get();
        $steps[] = [
            'name' => '查询商品',
            'duration_ms' => round((microtime(true) - $t) * 1000),
            'detail' => [
                'filters' => [
                    'category' => $parsed['category'],
                    'budget_max' => $parsed['budget_max'],
                    'brands' => $parsed['brands'] ?? [],
                    'keywords' => $parsed['keywords'] ?? [],
                    'urgency' => $parsed['urgency'] ?? [],
                ],
                'total' => $products->count(),
            ],
        ];

        // ─── 4. 返回结果 ──────────────────────────────
        return response()->json([
            '_steps' => $steps,           // 步骤数据（供前端折叠面板使用）
            'ai_analysis' => $parsed,     // 展示 AI 解析结果（学习用）
            'products' => $products,      // 匹配的商品列表
            'total' => $products->count(), // 结果数量
        ]);
    }
}
