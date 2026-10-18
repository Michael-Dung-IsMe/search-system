'use client';

import React from 'react';
import { Ban, X } from 'lucide-react';
import { ConstraintChip } from '@/types/search';

interface StateChipsBarProps {
  chips: ConstraintChip[];
  onRemoveChip: (chipId: string) => void;
  onClearAll?: () => void;
}

export const StateChipsBar: React.FC<StateChipsBarProps> = ({
  chips,
  onRemoveChip,
  onClearAll,
}) => {
  if (!chips || chips.length === 0) return null;

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-wrap items-center gap-2 pt-2 animate-fade-in">
      <span className="text-xs font-bold uppercase tracking-wider text-gray-400 mr-1">
        Đang áp dụng:
      </span>

      {chips.map((chip) => {
        const isNegative =
          chip.chip_type === 'exclude_color' || chip.chip_type === 'exclude_material';

        return (
          <span
            key={chip.chip_id}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
              isNegative
                ? 'bg-red-50 text-red-700 border-red-200 hover:border-red-300'
                : 'bg-gray-100 text-gray-800 border-gray-200 hover:border-gray-300'
            }`}
          >
            {isNegative && <Ban size={12} className="text-red-500 flex-shrink-0" />}
            <span>{chip.label}</span>
            {chip.is_removable && (
              <button
                type="button"
                onClick={() => onRemoveChip(chip.chip_id)}
                title={`Xóa điều kiện ${chip.label}`}
                className="w-4 h-4 rounded flex items-center justify-center text-gray-400 hover:text-red-600 hover:bg-gray-200/50 transition-colors ml-0.5"
              >
                <X size={12} />
              </button>
            )}
          </span>
        );
      })}

      {chips.length > 1 && onClearAll && (
        <button
          type="button"
          onClick={onClearAll}
          className="text-xs text-gray-400 hover:text-gray-900 underline ml-2 py-1 transition-colors"
        >
          Xóa tất cả
        </button>
      )}
    </div>
  );
};
