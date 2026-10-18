'use client';

import React from 'react';

interface RecommendedPillsProps {
  categories: string[];
  selectedCategory: string | null;
  onSelectCategory: (category: string) => void;
}

export const RecommendedPills: React.FC<RecommendedPillsProps> = ({
  categories,
  selectedCategory,
  onSelectCategory,
}) => {
  return (
    <div className="w-full flex items-center gap-2 overflow-x-auto py-2 scrollbar-none">
      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap mr-1">
        Gợi ý:
      </span>
      {categories.map((cat) => {
        const isAll = cat === 'Tất cả';
        const isActive = isAll ? !selectedCategory : selectedCategory?.toLowerCase() === cat.toLowerCase();

        return (
          <button
            key={cat}
            type="button"
            onClick={() => onSelectCategory(isAll ? '' : cat)}
            className={`btns ${isActive ? 'active' : ''}`}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
};
