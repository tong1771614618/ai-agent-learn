<?php

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes — AI Agent 学习项目
|--------------------------------------------------------------------------
|
| 项目索引（Python AI 服务路由前缀）：
|
|   项目 1: AI 商品客服        /api/v1/products/*  →  Python /p01/*
|   项目 2: Tool Calling Agent /api/v2/*           →  Python /p02/*
|   项目 3: AI 搜索引擎(RAG)   /api/v3/*           →  Python /p03/*
|   项目 4: 售后 Agent (HITL)  /api/v4/*           →  Python /p04/*
|   项目 5: RAG 知识库         /api/v5/*           →  Python /p05/*
|   项目 6: RAG + Agent        /api/v6/*           →  Python /p06/*
|   项目 7: Text-to-SQL        /api/v7/*           →  Python /p07/*
|   项目 8: Code Review Bot    /api/v8/*           →  Python /p08/*
|   项目 9: MCP Server         /api/v9/*           →  Python /p09/*
|   项目10: SRE Agent          /api/v10/*          →  Python /p10/*
|   项目11: Multi-Agent        /api/v11/*          →  Python /p11/*
|   项目12: DevPilot           /api/v12/*          →  Python /p12/*
|
| 每个项目的路由在对应区块内添加，保持清晰。
|
*/

// 健康检查 - 验证所有基础组件状态
Route::get('/health', function () {
    $checks = [];

    // 数据库检查
    try {
        DB::connection()->getPdo();
        $checks['database'] = 'ok';
    } catch (\Exception $e) {
        $checks['database'] = 'fail: ' . $e->getMessage();
    }

    // Redis 检查
    if (!class_exists(\Redis::class)) {
        $checks['redis'] = 'not_installed (phpredis extension missing)';
    } else {
        try {
            $redis = new \Redis();
            $redis->connect(config('database.redis.default.host'), config('database.redis.default.port'));
            $redis->ping();
            $checks['redis'] = 'ok';
        } catch (\Exception $e) {
            $checks['redis'] = 'fail: ' . $e->getMessage();
        }
    }

    return response()->json([
        'status' => 'ok',
        'app' => config('app.name'),
        'version' => '0.1.0',
        'php' => PHP_VERSION,
        'laravel' => app()->version(),
        'checks' => $checks,
    ]);
});

// ─── 项目 1: AI 商品客服 ────────────────────────────────
Route::prefix('v1/products')->group(function () {
    Route::post('/search', [\App\Http\Controllers\Api\V1\ProductSearchController::class, 'search']);
});

// ─── 项目 2: AI 商品搜索 Agent ───────────────────────────
Route::prefix('v2')->group(function () {
    Route::post('/chat', [\App\Http\Controllers\Api\V2\AgentChatController::class, 'chat']);
});

// ─── 项目 3: AI 搜索引擎 (RAG) ──────────────────────────
Route::prefix('v3')->group(function () {
    Route::post('/search', [\App\Http\Controllers\Api\V3\RagSearchController::class, 'search']);
});
