'use client';

import React, { useState } from 'react';
import { ArrowUp, Mic } from 'lucide-react';

interface StickyRefineBarProps {
  onRefine: (text: string) => void;
  onVoiceTrigger?: () => void;
  isProcessing?: boolean;
  placeholder?: string;
}

export const StickyRefineBar: React.FC<StickyRefineBarProps> = ({
  onRefine,
  onVoiceTrigger,
  isProcessing = false,
  placeholder = "Nhập tinh chỉnh: 'Đổi sang màu đen', 'Rẻ hơn nữa'...",
}) => {
  const [refineText, setRefineText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (refineText.trim()) {
      onRefine(refineText.trim());
      setRefineText('');
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-2xl z-40 animate-fade-in-up">
      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 bg-white/95 backdrop-blur-lg border rounded-full px-4 py-2 shadow-xl transition-all duration-300 ${
          isProcessing
            ? 'border-indigo-500 shadow-[0_0_20px_rgba(99,102,241,0.25)]'
            : 'border-gray-200/90 focus-within:border-gray-900 focus-within:shadow-2xl'
        }`}
      >
        <input
          type="text"
          value={refineText}
          onChange={(e) => setRefineText(e.target.value)}
          placeholder="Tinh chỉnh thêm: 'đổi sang màu đen', 'giá dưới 300k', 'kiểu thể thao'..."
          className="flex-1 bg-transparent border-none outline-none text-xs sm:text-sm text-gray-900 placeholder-gray-400 py-1"
        />

        <div className="flex items-center gap-1.5">
          {onVoiceTrigger && (
            <button
              type="button"
              onClick={onVoiceTrigger}
              title="Nói yêu cầu tinh chỉnh"
              className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            >
              <Mic size={16} />
            </button>
          )}

          <button
            type="submit"
            disabled={!refineText.trim() || isProcessing}
            title="Gửi lượt tinh chỉnh"
            className="w-8 h-8 rounded-full bg-gray-900 text-white flex items-center justify-center disabled:opacity-40 hover:bg-gray-800 transition-all active:scale-95"
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </div>
      </form>
    </div>
  );
};
