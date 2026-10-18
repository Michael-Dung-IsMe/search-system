'use client';

import React, { useState } from 'react';
import { Sparkles, Star } from 'lucide-react';
import { SearchResultItem } from '@/types/search';
import { getProductImageUrl } from '@/lib/api';

interface ProductCardProps {
  item: SearchResultItem;
  onFindSimilar: (articleId: string, prodName: string) => void;
  onClick?: (item: SearchResultItem) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  item,
  onFindSimilar,
  onClick,
}) => {
  const [imgError, setImgError] = useState(false);
  const imageUrl = imgError
    ? 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=600&q=80'
    : getProductImageUrl(item.image_path, item.article_id);

  const formattedPrice = item.price_vnd
    ? `${item.price_vnd.toLocaleString('vi-VN')} ₫`
    : 'Liên hệ';

  // Deterministic mock rating between 4.2 and 5.0 for clean visual e-commerce look
  const ratingVal = 4 + (item.article_id.charCodeAt(item.article_id.length - 1) % 10) / 10;
  const reviewCount = 20 + (item.article_id.charCodeAt(0) * 3) % 150;

  return (
    <div
      onClick={() => onClick?.(item)}
      className="group flex flex-col bg-white border-2 border-[#ededed] hover:border-gray-400 p-3.5 rounded-2xl cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-md"
    >
      {/* Product Image Container */}
      <div className="relative aspect-[3/4] w-full bg-gray-50 rounded-xl overflow-hidden">
        <img
          src={imageUrl}
          alt={item.prod_name}
          onError={() => setImgError(true)}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Visual Similarity Match Badge */}
        {item.visual_similarity && item.visual_similarity > 0.5 && (
          <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-full bg-white/95 backdrop-blur-xs text-[10px] font-bold text-gray-800 shadow-xs border border-gray-200">
            {Math.round(item.visual_similarity * 100)}% khớp ảnh
          </div>
        )}

        {/* Hover Action Overlay: "Tìm tương tự" */}
        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center p-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onFindSimilar(item.article_id, item.prod_name);
            }}
            className="w-full py-2 px-3 bg-white/95 backdrop-blur-md text-gray-900 font-semibold text-xs rounded-full shadow-lg flex items-center justify-center gap-1.5 hover:bg-gray-900 hover:text-white transition-all transform hover:scale-[1.02] active:scale-95"
          >
            <Sparkles size={13} />
            <span>Tìm tương tự</span>
          </button>
        </div>
      </div>

      {/* Card Details: Clean Minimalist E-Commerce Style */}
      <div className="pt-3 pb-1 flex flex-col gap-1">
        <h4 className="text-sm font-semibold text-gray-900 truncate" title={item.prod_name}>
          {item.prod_name}
        </h4>
        
        {/* Rating Stars matching Card.js */}
        <div className="flex items-center gap-1 text-[#d5ab55]">
          <div className="flex items-center">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                size={12}
                fill={i < Math.floor(ratingVal) ? '#d5ab55' : 'none'}
                stroke="#d5ab55"
              />
            ))}
          </div>
          <span className="text-[11px] text-gray-400 font-medium">({reviewCount})</span>
        </div>

        <div className="text-xs text-gray-500 truncate">
          {item.color_name || 'Đa sắc'} • {item.category_group || item.gender}
        </div>
        
        <div className="text-sm font-bold text-gray-900 pt-1">
          {formattedPrice}
        </div>
      </div>
    </div>
  );
};
