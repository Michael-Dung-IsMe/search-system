'use client';

import React from 'react';
import { Bot } from 'lucide-react';
import { SearchState } from '@/types/search';

interface ConversationalFeedProps {
  state: SearchState | null;
  totalResults: number;
  latencyMs?: number;
}

export const ConversationalFeed: React.FC<ConversationalFeedProps> = ({
  state,
  totalResults,
  latencyMs = 0,
}) => {
  if (!state || state.turn_index === 0) return null;

  // Build natural language summary of active state
  const parts: string[] = [];
  if (state.category) parts.push(`danh mục "${state.category}"`);
  if (state.color) parts.push(`màu "${state.color}"`);
  if (state.max_price) parts.push(`giá dưới ${state.max_price.toLocaleString('vi-VN')}₫`);
  if (state.style) parts.push(`phong cách "${state.style}"`);
  if (state.material) parts.push(`chất liệu "${state.material}"`);
  if (state.exclude_materials?.length > 0) {
    parts.push(`loại trừ chất liệu [${state.exclude_materials.join(', ')}]`);
  }
  if (state.exclude_colors?.length > 0) {
    parts.push(`loại trừ màu [${state.exclude_colors.join(', ')}]`);
  }
  if (state.reference_article_id) {
    parts.push(`tham chiếu sản phẩm #${state.reference_article_id}`);
  }

  const summaryText =
    parts.length > 0
      ? `Đã lọc theo ${parts.join(', ')}.`
      : 'Đã tìm kiếm sản phẩm phù hợp nhất với dữ liệu đa phương thức.';

  return (
    <div className="w-full max-w-3xl mx-auto mt-3 p-3.5 bg-gray-50 border border-gray-200/80 rounded-2xl flex items-start gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-full bg-gray-900 text-white flex items-center justify-center flex-shrink-0 mt-0.5">
        <Bot size={15} />
      </div>

      <div className="flex-1 text-xs sm:text-sm text-gray-700 leading-relaxed">
        <span>{summaryText}</span>{' '}
        <span className="font-semibold text-gray-900">
          Tìm thấy {totalResults} sản phẩm
        </span>{' '}
        {latencyMs > 0 && (
          <span className="text-[11px] text-gray-400">({latencyMs}ms)</span>
        )}
      </div>
    </div>
  );
};
