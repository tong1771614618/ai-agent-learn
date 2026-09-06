<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('approval_requests', function (Blueprint $table) {
            $table->id();
            $table->string('session_id')->comment('会话标识');
            $table->string('action_type')->comment('操作类型: refund/replacement/coupon');
            $table->json('action_params')->comment('操作参数');
            $table->text('reason')->comment('Agent 给出的理由');
            $table->string('status')->default('pending')->comment('pending/approved/rejected');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('approval_requests');
    }
};
