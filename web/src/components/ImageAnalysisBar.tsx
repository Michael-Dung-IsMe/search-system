'use client';

import React, { useEffect, useState } from 'react';
import { Camera, Check, Eye, Layers, Loader2, Sparkles, X } from 'lucide-react';
import { DetectedBox } from '@/types/search';

interface ImageAnalysisBarProps {
  imageFile: File | null;
  boxes: DetectedBox[];
  isAnalyzing: boolean;
  selectedBoxId: string | null;
  onSelectBox: (box: DetectedBox | null) => void;
  onOpenModal: () => void;
  onClearImage: () => void;
}

const VI_LABEL_MAP: Record<string, { label: string; icon: string }> = {
  Jacket: { label: 'Áo khoác', icon: '🧥' },
  Pants: { label: 'Quần dài', icon: '👖' },
  Shoes: { label: 'Giày dép', icon: '👟' },
  Bag: { label: 'Túi xách', icon: '👜' },
  Dress: { label: 'Đầm / Váy liền', icon: '👗' },
  Top: { label: 'Áo', icon: '👕' },
  Skirt: { label: 'Chân váy', icon: '🩱' },
};

export const ImageAnalysisBar: React.FC<ImageAnalysisBarProps> = ({
  imageFile,
  boxes,
  isAnalyzing,
  selectedBoxId,
  onSelectBox,
  onOpenModal,
  onClearImage,
}) => {
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);

  useEffect(() => {
    if (imageFile) {
      const url = URL.createObjectURL(imageFile);
      setThumbnailUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setThumbnailUrl(null);
    }
  }, [imageFile]);

  if (!imageFile) return null;

  return (
    <div
      data-testid="image-analysis-bar"
      className="w-full max-w-3xl mx-auto p-3 bg-white border border-indigo-100 rounded-2xl shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fade-in"
    >
      {/* Left: Thumbnail & Source Indicator */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div
          onClick={onOpenModal}
          title="Nhấn để xem & tùy chỉnh vùng chọn"
          className="relative w-12 h-12 rounded-xl overflow-hidden border border-gray-200 shadow-inner cursor-pointer hover:ring-2 hover:ring-indigo-500 transition-all group flex-shrink-0 bg-gray-100"
        >
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt="Uploaded Outfit"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
            />
          )}
          <div className="absolute inset-0 bg-black/25 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
            <Eye size={16} />
          </div>
        </div>

        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 text-xs font-bold text-gray-900">
            <Camera size={14} className="text-indigo-600" />
            <span>Tìm kiếm theo hình ảnh</span>
          </div>
          <span className="text-[11px] text-gray-500 truncate max-w-[140px] sm:max-w-[180px]">
            {imageFile.name}
          </span>
        </div>
      </div>

      {/* Middle: Analysis Result Badges (Running in background) */}
      <div className="flex-1 w-full sm:w-auto flex flex-wrap items-center gap-1.5">
        {isAnalyzing ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-50 text-indigo-700 text-xs font-medium animate-pulse">
            <Loader2 size={14} className="animate-spin text-indigo-600" />
            <span>Đang nhận diện vật thể trong ảnh (OWL-ViT ngầm)...</span>
          </div>
        ) : boxes.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Whole image option */}
            <button
              type="button"
              onClick={() => onSelectBox(null)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                selectedBoxId === null
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Toàn bộ ảnh
            </button>

            {/* Detected Objects Chips */}
            {boxes.map((box) => {
              const info = VI_LABEL_MAP[box.label] || { label: box.label, icon: '🏷️' };
              const isSelected = selectedBoxId === box.box_id;
              const confidence = Math.round(box.score * 100);

              return (
                <button
                  key={box.box_id}
                  type="button"
                  onClick={() => onSelectBox(box)}
                  title={`Lọc theo ${info.label} (${confidence}% độ tự tin)`}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-emerald-600 text-white shadow-xs ring-2 ring-emerald-300'
                      : 'bg-indigo-50/80 text-indigo-800 hover:bg-indigo-100 border border-indigo-200/60'
                  }`}
                >
                  <span>{info.icon}</span>
                  <span>{info.label}</span>
                  <span className={`text-[10px] opacity-80 ${isSelected ? 'text-white' : 'text-indigo-600'}`}>
                    {confidence}%
                  </span>
                  {isSelected && <Check size={12} strokeWidth={3} className="ml-0.5" />}
                </button>
              );
            })}

            {/* Custom box selector trigger */}
            <button
              type="button"
              onClick={onOpenModal}
              title="Mở bảng vẽ vùng chọn chi tiết"
              className="p-1 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-gray-100 transition-colors ml-1"
            >
              <Layers size={15} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-50 px-2.5 py-1 rounded-lg">
            <Sparkles size={13} className="text-gray-400" />
            <span>Đã quét ảnh toàn diện (không tách riêng từng vật thể)</span>
          </div>
        )}
      </div>

      {/* Right: Clear Image Search CTA */}
      <button
        type="button"
        onClick={onClearImage}
        title="Hủy tìm bằng ảnh, quay lại tìm văn bản"
        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors self-end sm:self-center flex-shrink-0"
      >
        <X size={14} />
        <span>Hủy ảnh</span>
      </button>
    </div>
  );
};
