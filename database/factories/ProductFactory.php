<?php

namespace Database\Factories;

use App\Models\Product;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Product>
 */
class ProductFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $brands = ['Nike', 'Adidas', 'Asics', 'New Balance', 'Li-Ning', 'Anta', 'Saucony', 'HOKA'];
        $categories = ['running', 'basketball', 'casual', 'hiking', 'training', 'swimming'];
        $tagPool = ['夏天', '冬天', '轻便', '防水', '缓震', '越野', '公路', '室内', '户外', '入门', '专业', '透气', '耐磨', '防滑', '支撑'];

        $brand = fake()->randomElement($brands);
        $category = fake()->randomElement($categories);

        return [
            'name' => $brand . ' ' . fake()->words(2, true),
            'description' => fake()->sentence(10),
            'category' => $category,
            'brand' => $brand,
            'price' => fake()->randomFloat(2, 199, 1999),
            'tags' => fake()->randomElements($tagPool, fake()->numberBetween(2, 5)),
            'stock' => fake()->numberBetween(0, 200),
            'status' => 1,
        ];
    }
}
