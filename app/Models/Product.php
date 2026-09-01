<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Product extends Model
{
    use HasFactory;

    protected $fillable = [
        'name', 'description', 'category', 'brand', 'price', 'tags', 'stock', 'status','urgency'
    ];

    protected $casts = [
        'tags' => 'array',
        'price' => 'decimal:2',
        'stock' => 'integer',
        'status' => 'integer',
        'urgency' => 'integer',
    ];

    // ─── Query Scopes ────────────────────────────────────
    // 这些 scope 让控制器里的查询代码可读性更好

    /** 只查上架商品 */
    public function scopeActive($query)
    {
        return $query->where('status', 1);
    }

    /** 按分类筛选 */
    public function scopeInCategory($query, ?string $category)
    {
        if ($category) {
            $query->where('category', $category);
        }
        return $query;
    }

    /** 按预算上限筛选 */
    public function scopeInBudget($query, ?float $maxPrice)
    {
        if ($maxPrice) {
            $query->where('price', '<=', $maxPrice);
        }
        return $query;
    }

    /** 按品牌筛选 */
    public function scopeInBrands($query, array $brands)
    {
        if (!empty($brands)) {
            $query->whereIn('brand', $brands);
        }
        return $query;
    }

    /** 按紧急程度筛选 */
    public function scopeInUrgency($query, ?string $urgency)
    {
        if (!empty($urgency)) {
            $type = $urgency == '急' ? 1 : 0;
            $query->where('urgency', $type);
        }
        return $query;
    }

    /** 按关键词模糊搜索(名称+描述+标签) */
    public function scopeMatchKeywords($query, array $keywords)
    {
        if (!empty($keywords)) {
            $query->where(function ($q) use ($keywords) {
                foreach ($keywords as $keyword) {
                    $q->orWhere('name', 'LIKE', "%{$keyword}%")
                      ->orWhere('description', 'LIKE', "%{$keyword}%")
                      ->orWhereJsonContains('tags', $keyword);
                }
            });
        }
        return $query;
    }
}
