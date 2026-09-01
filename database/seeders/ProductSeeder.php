<?php

namespace Database\Seeders;

use App\Models\Product;
use Illuminate\Database\Seeder;

class ProductSeeder extends Seeder
{
    public function run(): void
    {
        // ─── 手工精选商品（保证测试结果可预测）────────────────
        $curated = [
            [
                'name' => 'Nike Air Zoom Pegasus 40 跑步鞋',
                'description' => '经典公路跑鞋，透气网面鞋面，React泡棉中底，适合日常训练和夏天跑步',
                'category' => 'running', 'brand' => 'Nike', 'price' => 899.00,
                'tags' => ['夏天', '跑步', '透气', '公路', '缓震'], 'stock' => 50, 'status' => 1,
            ],
            [
                'name' => 'HOKA Clifton 9 跑步鞋',
                'description' => '极致缓震轻量跑鞋，工程网眼鞋面透气性佳，适合长距离慢跑',
                'category' => 'running', 'brand' => 'HOKA', 'price' => 1199.00,
                'tags' => ['夏天', '跑步', '缓震', '轻便', '公路'], 'stock' => 30, 'status' => 1,
            ],
            [
                'name' => 'Asics GEL-KAYANO 30 支撑跑鞋',
                'description' => '顶级支撑稳定跑鞋，适合扁平足和大体重跑者',
                'category' => 'running', 'brand' => 'Asics', 'price' => 1290.00,
                'tags' => ['跑步', '支撑', '缓震', '专业'], 'stock' => 25, 'status' => 1,
            ],
            [
                'name' => 'Nike LeBron 21 篮球鞋',
                'description' => '全掌Zoom Air气垫，强力缓震，适合锋线球员',
                'category' => 'basketball', 'brand' => 'Nike', 'price' => 1399.00,
                'tags' => ['篮球', '缓震', '室内', '专业'], 'stock' => 40, 'status' => 1,
            ],
            [
                'name' => 'Adidas Harden Vol.8 篮球鞋',
                'description' => 'Lightstrike中底，轻质灵活，适合后卫球员',
                'category' => 'basketball', 'brand' => 'Adidas', 'price' => 999.00,
                'tags' => ['篮球', '轻便', '室内'], 'stock' => 35, 'status' => 1,
            ],
            [
                'name' => 'Li-Ning 韦德之道 10 篮球鞋',
                'description' => '全掌䨻科技+碳板，国产顶级篮球鞋',
                'category' => 'basketball', 'brand' => 'Li-Ning', 'price' => 1199.00,
                'tags' => ['篮球', '专业', '缓震', '室内'], 'stock' => 20, 'status' => 1,
            ],
            [
                'name' => 'Salomon XA Pro 3D 越野跑鞋',
                'description' => '经典越野跑鞋，Contagrip大底防滑耐磨，适合山地越野',
                'category' => 'hiking', 'brand' => 'Salomon', 'price' => 899.00,
                'tags' => ['越野', '户外', '防滑', '防水', '耐磨'], 'stock' => 30, 'status' => 1,
            ],
            [
                'name' => 'Anta 氢跑 5 跑步鞋',
                'description' => '超轻跑鞋，氮科技中底，夏天穿透气不闷脚，性价比之选',
                'category' => 'running', 'brand' => 'Anta', 'price' => 399.00,
                'tags' => ['夏天', '跑步', '轻便', '透气', '入门'], 'stock' => 100, 'status' => 1,
            ],
            [
                'name' => 'Li-Ning 赤兔 7 Pro 跑步鞋',
                'description' => '全掌䨻科技，万金油跑鞋，兼顾日常跑步和通勤',
                'category' => 'running', 'brand' => 'Li-Ning', 'price' => 499.00,
                'tags' => ['跑步', '夏天', '透气', '入门', '轻便'], 'stock' => 80, 'status' => 1,
            ],
            [
                'name' => 'Saucony Kinvara 15 跑步鞋',
                'description' => '极致轻薄跑鞋，轻量化设计，夏天穿透气性一流',
                'category' => 'running', 'brand' => 'Saucony', 'price' => 799.00,
                'tags' => ['夏天', '跑步', '轻便', '透气', '公路'], 'stock' => 45, 'status' => 1,
            ],
            [
                'name' => 'New Balance Fresh Foam 1080v13 跑步鞋',
                'description' => 'Fresh Foam X中底，柔软舒适，适合日常慢跑',
                'category' => 'running', 'brand' => 'New Balance', 'price' => 1099.00,
                'tags' => ['跑步', '缓震', '舒适', '公路'], 'stock' => 35, 'status' => 1,
            ],
            [
                'name' => 'Adidas Ultraboost Light 跑步鞋',
                'description' => 'Light Boost中底，能量回馈出色，经典公路跑鞋',
                'category' => 'running', 'brand' => 'Adidas', 'price' => 1299.00,
                'tags' => ['跑步', '缓震', '公路', '专业'], 'stock' => 40, 'status' => 1,
            ],
            [
                'name' => 'Columbia Redmond 防水登山鞋',
                'description' => 'Omni-Tech防水透气，Vibram大底，适合徒步登山',
                'category' => 'hiking', 'brand' => 'Columbia', 'price' => 699.00,
                'tags' => ['户外', '防水', '越野', '耐磨', '冬天'], 'stock' => 50, 'status' => 1,
            ],
            [
                'name' => 'Nike Metcon 9 训练鞋',
                'description' => 'CrossFit训练鞋，稳定支撑，适合健身房综合训练',
                'category' => 'training', 'brand' => 'Nike', 'price' => 899.00,
                'tags' => ['训练', '室内', '支撑', '专业'], 'stock' => 30, 'status' => 1,
            ],
            [
                'name' => 'Speedo Fastskin 竞速泳镜',
                'description' => '专业竞速泳镜，防雾防紫外线，低阻力设计',
                'category' => 'swimming', 'brand' => 'Speedo', 'price' => 299.00,
                'tags' => ['游泳', '专业', '防水'], 'stock' => 60, 'status' => 1,
            ],
        ];

        foreach ($curated as $product) {
            Product::create($product);
        }

        // ─── 随机生成补充商品 ─────────────────────────────
        Product::factory()->count(15)->create();
    }
}
