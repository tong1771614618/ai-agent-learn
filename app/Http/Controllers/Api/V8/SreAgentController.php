<?php

namespace App\Http\Controllers\Api\V8;

use App\Http\Controllers\Controller;
use App\Services\AiService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * 项目 8: MCP + SRE Agent — 控制器
 *
 * 架构：
 *   前端 → PHP → Python (SRE Agent) → MCP Client → MCP Server (8002端口)
 *                                                    ↓
 *                                              系统运维工具
 */
class SreAgentController extends Controller
{
    public function diagnose(Request $request, AiService $aiService): JsonResponse
    {
        $request->validate([
            'message' => 'required|string|max:2000',
            'session_id' => 'nullable|string|max:64',
        ]);

        try {
            $result = $aiService->sreDiagnose(
                $request->input('message'),
                $request->input('session_id'),
            );
        } catch (\RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 503);
        }

        return response()->json($result);
    }

    public function confirm(Request $request, AiService $aiService): JsonResponse
    {
        $request->validate([
            'session_id' => 'required|string|max:64',
            'confirmed' => 'required|boolean',
        ]);

        try {
            $result = $aiService->sreConfirm(
                $request->input('session_id'),
                $request->input('confirmed'),
            );
        } catch (\RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 503);
        }

        return response()->json($result);
    }
}
