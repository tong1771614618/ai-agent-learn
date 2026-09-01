<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->string('name', 200)->comment('商品名称');
            $table->text('description')->nullable()->comment('商品描述');
            $table->string('category', 50)->index()->comment('分类: running/basketball/casual/hiking/training/swimming');
            $table->string('brand', 50)->index()->comment('品牌');
            $table->decimal('price', 10, 2)->comment('价格(元)');
            $table->json('tags')->nullable()->comment('标签: ["夏天","跑步","轻便"]');
            $table->integer('stock')->default(0)->comment('库存');
            $table->tinyInteger('status')->default(1)->comment('1=上架 0=下架');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
