'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Check, Layers, Sparkles, X } from 'lucide-react';
import { DetectedBox } from '@/types/search';

interface ObjectSelectModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageFile: File | null;
  boxes: DetectedBox[];
  isLoadingBoxes?: boolean;
  initialSelectedBoxId?: string | null;
  onConfirm: (payload: {
    selectedBox: DetectedBox | null;
    optionalText: string;
    imageFile: File;
  }) => void;
}

const RELIABLE_DETECTION_SCORE = 0.35;

const VI_LABEL_MAP: Record<string, string> = {
  UpperGarment: 'Áo',
  Pants: 'Quần',
  Skirt: 'Chân váy',
  Dress: 'Váy / Đầm',
  Shoes: 'Giày',
};

const displayBoxLabel = (box: DetectedBox) =>
  box.score >= RELIABLE_DETECTION_SCORE
    ? VI_LABEL_MAP[box.label] || box.label
    : 'Chưa xác định';

export const ObjectSelectModal: React.FC<ObjectSelectModalProps> = ({
  isOpen,
  onClose,
  imageFile,
  boxes,
  isLoadingBoxes = false,
  initialSelectedBoxId = null,
  onConfirm,
}) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(initialSelectedBoxId || null);
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);
  const [optionalText, setOptionalText] = useState('');

  // Generate preview URL on image file change
  useEffect(() => {
    if (imageFile) {
      const url = URL.createObjectURL(imageFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [imageFile]);

  // Sort boxes descending by confidence score
  const sortedBoxes = useMemo(() => {
    return [...boxes].sort((a, b) => b.score - a.score);
  }, [boxes]);

  // Default selection: If boxes loaded and no box selected, pick top confidence box
  useEffect(() => {
    const bestReliableBox = sortedBoxes.find(
      (box) => box.score >= RELIABLE_DETECTION_SCORE
    );
    if (bestReliableBox && !selectedBoxId) {
      setSelectedBoxId(bestReliableBox.box_id);
    }
  }, [sortedBoxes, selectedBoxId]);

  if (!isOpen || !imageFile) return null;

  const activeBox = sortedBoxes.find((b) => b.box_id === selectedBoxId) || null;

  const handleBoxSelect = (box: DetectedBox) => {
    setSelectedBoxId(box.box_id);
  };

  const handleSubmit = () => {
    onConfirm({
      selectedBox: activeBox,
      optionalText: optionalText.trim(),
      imageFile,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Layers size={18} />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 text-base sm:text-lg">
                Phân tích Trang phục từ Ảnh
              </h3>
              <p className="text-xs text-gray-500">
                Di chuột vào từng trang phục để viền phát sáng và chọn vùng tìm kiếm
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Image with SVG Glow Contour & Bounding Boxes */}
            <div className="relative aspect-[3/4] bg-gray-100 rounded-2xl overflow-hidden border border-gray-200 shadow-inner flex items-center justify-center group">
              {previewUrl && (
                <img
                  src={previewUrl}
                  alt="Outfit Preview"
                  className="w-full h-full object-cover select-none"
                />
              )}

              {/* Interactive SVG Contour Layer (0% server load, renders crisp at 60fps) */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox="0 0 1000 1000"
                preserveAspectRatio="none"
              >
                <defs>
                  <filter id="glow-hover" x="-25%" y="-25%" width="150%" height="150%">
                    <feDropShadow dx="0" dy="0" stdDeviation="7" floodColor="#3b82f6" floodOpacity="0.85" />
                  </filter>
                  <filter id="glow-selected" x="-25%" y="-25%" width="150%" height="150%">
                    <feDropShadow dx="0" dy="0" stdDeviation="9" floodColor="#10b981" floodOpacity="0.95" />
                  </filter>
                </defs>

                {sortedBoxes.map((box) => {
                  const isSelected = box.box_id === selectedBoxId;
                  const isHovered = box.box_id === hoveredBoxId;

                  // Normalized [x, y] to SVG 1000x1000 coordinates
                  const pointsStr = (box.polygon && box.polygon.length >= 3
                    ? box.polygon
                    : [
                        [box.box_2d[1], box.box_2d[0]],
                        [box.box_2d[3], box.box_2d[0]],
                        [box.box_2d[3], box.box_2d[2]],
                        [box.box_2d[1], box.box_2d[2]],
                      ]
                  )
                    .map(([x, y]) => `${Math.round(x * 1000)},${Math.round(y * 1000)}`)
                    .join(' ');

                  return (
                    <polygon
                      key={`contour-${box.box_id}`}
                      points={pointsStr}
                      className="transition-all duration-200"
                      fill={
                        isSelected
                          ? 'rgba(16, 185, 129, 0.22)'
                          : isHovered
                          ? 'rgba(59, 130, 246, 0.20)'
                          : 'rgba(99, 102, 241, 0.04)'
                      }
                      stroke={
                        isSelected
                          ? '#10b981'
                          : isHovered
                          ? '#3b82f6'
                          : 'rgba(99, 102, 241, 0.35)'
                      }
                      strokeWidth={isSelected ? 4 : isHovered ? 3.5 : 1.5}
                      strokeDasharray={isSelected || isHovered ? 'none' : '4 3'}
                      filter={isSelected ? 'url(#glow-selected)' : isHovered ? 'url(#glow-hover)' : undefined}
                    />
                  );
                })}
              </svg>

              {/* Bounding Box Interaction Hitboxes */}
              {sortedBoxes.map((box) => {
                const [ymin, xmin, ymax, xmax] = box.box_2d;
                const isSelected = box.box_id === selectedBoxId;
                const isHovered = box.box_id === hoveredBoxId;
                const top = `${ymin * 100}%`;
                const left = `${xmin * 100}%`;
                const width = `${(xmax - xmin) * 100}%`;
                const height = `${(ymax - ymin) * 100}%`;

                return (
                  <div
                    key={box.box_id}
                    onClick={() => handleBoxSelect(box)}
                    onMouseEnter={() => setHoveredBoxId(box.box_id)}
                    onMouseLeave={() => setHoveredBoxId(null)}
                    style={{ top, left, width, height }}
                    className="absolute cursor-pointer transition-all duration-200 z-10"
                  >
                    <span
                      className={`absolute -top-6 left-0 text-[11px] font-semibold px-2 py-0.5 rounded shadow-sm whitespace-nowrap transition-all duration-200 ${
                        isSelected
                          ? 'bg-emerald-600 text-white scale-105'
                          : isHovered
                          ? 'bg-blue-600 text-white scale-105 ring-2 ring-blue-300'
                          : 'bg-gray-900/80 text-white opacity-85'
                      }`}
                    >
                      {displayBoxLabel(box)} ({Math.round(box.score * 100)}%)
                    </span>
                  </div>
                );
              })}

              {isLoadingBoxes && (
                <div className="absolute inset-0 bg-white/70 backdrop-blur-xs flex flex-col items-center justify-center gap-2 text-indigo-600">
                  <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs font-semibold">Đang nhận diện vật thể...</span>
                </div>
              )}
            </div>

            {/* Right: Controls & Options */}
            <div className="flex flex-col justify-between gap-5">
              <div className="flex flex-col gap-4">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
                    Các vật thể đã quét tự động:
                  </h4>
                  <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                    {sortedBoxes.length === 0 && !isLoadingBoxes && (
                      <div className="text-xs text-gray-500 italic p-3 bg-gray-50 rounded-xl">
                        Không phát hiện rõ vật thể riêng biệt. Hệ thống sẽ tìm theo toàn bộ ảnh.
                      </div>
                    )}
                    {sortedBoxes.map((box) => {
                      const isSelected = box.box_id === selectedBoxId;
                      const isHovered = box.box_id === hoveredBoxId;
                      return (
                        <div
                          key={box.box_id}
                          onClick={() => handleBoxSelect(box)}
                          onMouseEnter={() => setHoveredBoxId(box.box_id)}
                          onMouseLeave={() => setHoveredBoxId(null)}
                          className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-emerald-50/80 border-emerald-400 shadow-sm ring-1 ring-emerald-300'
                              : isHovered
                              ? 'bg-blue-50/80 border-blue-400 shadow-sm'
                              : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-5 h-5 rounded-md flex items-center justify-center text-xs ${
                                isSelected ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-400'
                              }`}
                            >
                              {isSelected ? <Check size={12} strokeWidth={3} /> : null}
                            </div>
                            <span className="text-sm font-semibold text-gray-900">
                              {displayBoxLabel(box)}
                            </span>
                          </div>
                          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                            {Math.round(box.score * 100)}% Tự tin
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Optional Text Query Input */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                    <Sparkles size={14} className="text-indigo-600" />
                    Mô tả thêm (Tùy chọn):
                  </label>
                  <input
                    type="text"
                    value={optionalText}
                    onChange={(e) => setOptionalText(e.target.value)}
                    placeholder="VD: 'áo sơ mi xanh', 'quần sáng màu', 'dưới 500k'..."
                    className="w-full px-3.5 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:bg-white focus:border-gray-900 transition-all placeholder-gray-400"
                  />
                </div>

                {/* Logic Explanation Box */}
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs text-gray-600 space-y-1">
                  <p className="font-semibold text-gray-900">Cơ chế ưu tiên theo yêu cầu:</p>
                  <p>• <strong>Có mô tả:</strong> Ưu tiên khớp từ khóa với vật thể trong ảnh.</p>
                  <p>• <strong>Để trống:</strong> Tự động tìm theo vật thể có độ tự tin cao nhất.</p>
                </div>
              </div>

              {/* Submit CTA */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl border border-gray-200 text-gray-700 font-medium text-sm hover:bg-gray-50 transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="px-6 py-2.5 rounded-xl bg-gray-900 hover:bg-gray-800 text-white font-semibold text-sm shadow-sm transition-all active:scale-95"
                >
                  Bắt đầu tìm kiếm
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
