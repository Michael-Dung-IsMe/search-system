'use client';

import React from 'react';
import { SearchResultItem } from '@/types/search';
import { ProductCard } from './ProductCard';
import { Bot, Shirt } from 'lucide-react';

interface ProductGridProps {
  items: SearchResultItem[];
  exactItems?: SearchResultItem[];
  similarItems?: SearchResultItem[];
  hasExactMatch?: boolean;
  message?: string | null;
  responseType?: 'search_results' | 'conversation';
  isLoading?: boolean;
  onFindSimilar: (articleId: string, prodName: string) => void;
  onProductClick?: (item: SearchResultItem) => void;
}

export const ProductGrid: React.FC<ProductGridProps> = ({
  items,
  exactItems = [],
  similarItems = [],
  hasExactMatch = true,
  message,
  responseType = 'search_results',
  isLoading = false,
  onFindSimilar,
  onProductClick,
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6 py-6">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="flex flex-col gap-3 animate-pulse">
            <div className="aspect-[3/4] bg-gray-200 rounded-2xl w-full" />
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
            <div className="h-4 bg-gray-200 rounded w-1/3" />
          </div>
        ))}
      </div>
    );
  }

  if (responseType === 'conversation') {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center px-4 animate-fade-in">
        <div className="w-16 h-16 rounded-3xl bg-indigo-50 flex items-center justify-center text-indigo-600 mb-4 shadow-xs">
          <Bot size={28} />
        </div>
        <h3 className="text-base font-bold text-gray-900 mb-1">
          Trợ lý tìm kiếm thời trang
        </h3>
        <p className="text-xs sm:text-sm text-gray-500 max-w-md">
          {message || 'Hãy mô tả sản phẩm thời trang mà bạn muốn tìm.'}
        </p>
      </div>
    );
  }

  // Determine lists to render
  const effectiveExact = exactItems.length > 0 ? exactItems : (hasExactMatch ? items : []);
  const effectiveSimilar = similarItems.length > 0 ? similarItems : (!hasExactMatch ? items : []);

  // Case 1: Both exact and similar are empty -> Zero-result stop state
  if (effectiveExact.length === 0 && effectiveSimilar.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center px-4 animate-fade-in">
        <div className="w-16 h-16 rounded-3xl bg-gray-100 flex items-center justify-center text-gray-400 mb-4 shadow-xs">
          <Shirt size={28} />
        </div>
        <h3 className="text-base font-bold text-gray-900 mb-1">
          Không tìm thấy sản phẩm phù hợp
        </h3>
        <p className="text-xs sm:text-sm text-gray-500 max-w-md">
          {message || 'Hệ thống đã dừng tìm kiếm do không còn sản phẩm nào đáp ứng tiêu chí kể cả trong danh mục mở rộng. Vui lòng nới lỏng bộ lọc hoặc đổi từ khóa.'}
        </p>
      </div>
    );
  }

  // Case 2: No exact match -> Show clear Empty notification block followed by Similar Recommendations
  if (!hasExactMatch || effectiveExact.length === 0) {
    return (
      <div className="flex flex-col gap-6 py-4 animate-fade-in">
        {/* Exact Match Empty State Notification */}
        <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/90 border border-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0">
              <Shirt size={20} />
            </div>
            <div>
              <h4 className="text-sm font-bold text-amber-900">
                Không có sản phẩm khớp chính xác 100%
              </h4>
              <p className="text-xs text-amber-700 mt-0.5">
                {message || 'Không tìm thấy sản phẩm khớp đúng với truy vấn của bạn. Dưới đây là các sản phẩm tương tự cùng danh mục và họ màu gần nhất:'}
              </p>
            </div>
          </div>
          <span className="text-[11px] font-semibold uppercase px-2.5 py-1 rounded-full bg-amber-200/80 text-amber-900 tracking-wider flex-shrink-0">
            Gợi ý tương tự
          </span>
        </div>

        {/* Similar items grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-5 gap-y-8">
          {effectiveSimilar.map((item) => (
            <ProductCard
              key={item.article_id}
              item={item}
              onFindSimilar={onFindSimilar}
              onClick={onProductClick}
            />
          ))}
        </div>
      </div>
    );
  }

  // Case 3: Has exact matches (with optional secondary similar items below)
  return (
    <div className="flex flex-col gap-10 py-6 animate-fade-in">
      {/* Primary Partition: Exact Matches */}
      <div>
        {effectiveSimilar.length > 0 && (
          <div className="flex items-center gap-2 mb-4">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700">
              Sản phẩm khớp chính xác ({effectiveExact.length})
            </h3>
          </div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-5 gap-y-8">
          {effectiveExact.map((item) => (
            <ProductCard
              key={item.article_id}
              item={item}
              onFindSimilar={onFindSimilar}
              onClick={onProductClick}
            />
          ))}
        </div>
      </div>

      {/* Secondary Partition: Similar Recommendations (if any) */}
      {effectiveSimilar.length > 0 && (
        <div className="pt-8 border-t border-gray-200/80">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700">
                Gợi ý tương tự bạn có thể quan tâm ({effectiveSimilar.length})
              </h3>
            </div>
            <span className="text-xs text-gray-400">Được gợi ý theo họ màu & danh mục</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-5 gap-y-8">
            {effectiveSimilar.map((item) => (
              <ProductCard
                key={item.article_id}
                item={item}
                onFindSimilar={onFindSimilar}
                onClick={onProductClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
