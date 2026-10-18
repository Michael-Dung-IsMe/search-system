'use client';

import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

export interface FacetFilterState {
  category?: string | null;
  minPrice?: number | null;
  maxPrice?: number | null;
  color?: string | null;
}

interface FacetSidebarProps {
  filters: FacetFilterState;
  onFilterChange: (newFilters: FacetFilterState) => void;
  onResetFilters: () => void;
}

const CATEGORY_OPTIONS = [
  { label: 'Tất cả sản phẩm', value: '' },
  { label: 'Áo thun (T-shirt)', value: 'T-shirt' },
  { label: 'Áo Blouse & Sơ mi', value: 'Blouse' },
  { label: 'Áo len (Sweater)', value: 'Sweater' },
  { label: 'Áo kiểu (Top)', value: 'Top' },
  { label: 'Áo khoác (Jacket)', value: 'Jacket' },
  { label: 'Áo Blazer', value: 'Blazer' },
  { label: 'Váy & Đầm (Dress)', value: 'Dress' },
];

const PRICE_PRESETS = [
  { label: 'Tất cả mức giá', min: null, max: null },
  { label: 'Dưới 300.000 ₫', min: null, max: 300000 },
  { label: '300.000 ₫ - 700.000 ₫', min: 300000, max: 700000 },
  { label: '700.000 ₫ - 1.200.000 ₫', min: 700000, max: 1200000 },
  { label: 'Trên 1.200.000 ₫', min: 1200000, max: null },
];

const COLOR_OPTIONS = [
  { label: 'Tất cả', value: '', hex: '', isAll: true },
  { label: 'Đen', value: 'black', hex: '#111827' },
  { label: 'Trắng', value: 'white', hex: '#ffffff', isBordered: true },
  { label: 'Xám', value: 'grey', hex: '#6b7280' },
  { label: 'Xanh lam', value: 'blue', hex: '#2563eb' },
  { label: 'Be', value: 'beige', hex: '#d4b896' },
  { label: 'Đỏ', value: 'red', hex: '#dc2626' },
  { label: 'Vàng', value: 'yellow', hex: '#eab308' },
  { label: 'Hồng', value: 'pink', hex: '#ec4899' },
  { label: 'Khaki', value: 'khaki', hex: '#78716c' },
];

export const FacetSidebar: React.FC<FacetSidebarProps> = ({
  filters,
  onFilterChange,
  onResetFilters,
}) => {
  const [customMin, setCustomMin] = useState<string>(
    filters.minPrice ? filters.minPrice.toString() : ''
  );
  const [customMax, setCustomMax] = useState<string>(
    filters.maxPrice ? filters.maxPrice.toString() : ''
  );

  const handleCategorySelect = (val: string) => {
    onFilterChange({
      ...filters,
      category: val || null,
    });
  };

  const handlePricePresetSelect = (min: number | null, max: number | null) => {
    setCustomMin(min ? min.toString() : '');
    setCustomMax(max ? max.toString() : '');
    onFilterChange({
      ...filters,
      minPrice: min,
      maxPrice: max,
    });
  };

  const handleApplyCustomPrice = (e: React.FormEvent) => {
    e.preventDefault();
    const min = customMin ? parseInt(customMin.replace(/\D/g, ''), 10) : null;
    const max = customMax ? parseInt(customMax.replace(/\D/g, ''), 10) : null;

    onFilterChange({
      ...filters,
      minPrice: min,
      maxPrice: max,
    });
  };

  const handleColorSelect = (colorVal: string) => {
    onFilterChange({
      ...filters,
      color: colorVal || null,
    });
  };

  return (
    <aside className="w-full lg:w-64 flex-shrink-0 flex flex-col gap-6 bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
      {/* Title & Reset Button */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <h3 className="text-sm font-bold uppercase tracking-wider text-gray-900">
          Bộ lọc tìm kiếm
        </h3>
        <button
          type="button"
          onClick={onResetFilters}
          title="Xóa tất cả bộ lọc"
          className="text-xs text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors"
        >
          <RotateCcw size={12} />
          <span>Đặt lại</span>
        </button>
      </div>

      {/* 1. Category Filter */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-800 mb-3">
          Danh mục sản phẩm
        </h4>
        <div className="flex flex-col">
          {CATEGORY_OPTIONS.map((item) => {
            const isChecked = item.value === ''
              ? !filters.category
              : filters.category?.toLowerCase() === item.value.toLowerCase();

            return (
              <label key={item.label} className="sidebar-label-container">
                <input
                  type="radio"
                  name="sidebar-category"
                  checked={isChecked}
                  onChange={() => handleCategorySelect(item.value)}
                />
                <span className="checkmark" />
                <span className={isChecked ? 'font-semibold text-gray-900' : ''}>
                  {item.label}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <hr className="border-gray-100" />

      {/* 2. Price Range Filter */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-800 mb-3">
          Khoảng giá (VNĐ)
        </h4>

        {/* Radio Presets */}
        <div className="flex flex-col mb-3">
          {PRICE_PRESETS.map((preset) => {
            const isChecked =
              filters.minPrice === preset.min && filters.maxPrice === preset.max;

            return (
              <label key={preset.label} className="sidebar-label-container">
                <input
                  type="radio"
                  name="sidebar-price"
                  checked={isChecked}
                  onChange={() => handlePricePresetSelect(preset.min, preset.max)}
                />
                <span className="checkmark" />
                <span className={isChecked ? 'font-semibold text-gray-900' : ''}>
                  {preset.label}
                </span>
              </label>
            );
          })}
        </div>

        {/* Custom Price Range Input */}
        <form onSubmit={handleApplyCustomPrice} className="flex flex-col gap-2 pt-1">
          <span className="text-[11px] text-gray-500">Hoặc tự nhập khoảng giá:</span>
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="Từ ₫"
              value={customMin}
              onChange={(e) => setCustomMin(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-gray-50 border border-gray-200 focus:bg-white focus:border-gray-900 outline-none"
            />
            <span className="text-gray-400">-</span>
            <input
              type="number"
              placeholder="Đến ₫"
              value={customMax}
              onChange={(e) => setCustomMax(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-gray-50 border border-gray-200 focus:bg-white focus:border-gray-900 outline-none"
            />
          </div>
          <button
            type="submit"
            className="w-full mt-1 py-1.5 px-3 bg-gray-900 text-white rounded-lg text-xs font-semibold hover:bg-gray-800 transition-colors"
          >
            Áp dụng giá
          </button>
        </form>
      </div>

      <hr className="border-gray-100" />

      {/* 3. Colors Palette */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-gray-800">
            Màu sắc
          </h4>
          {filters.color && (
            <span className="text-[11px] font-semibold text-gray-900 capitalize">
              {filters.color}
            </span>
          )}
        </div>

        <div className="grid grid-cols-5 gap-2">
          {COLOR_OPTIONS.map((col) => {
            const isSelected = col.value === ''
              ? !filters.color
              : filters.color?.toLowerCase() === col.value.toLowerCase();

            return (
              <button
                key={col.label}
                type="button"
                onClick={() => handleColorSelect(col.value)}
                title={col.label}
                className={`color-circle-btn ${isSelected ? 'active' : ''}`}
              >
                {col.isAll ? (
                  <span className="checkmark all-colors !position-static !transform-none !h-full !w-full" />
                ) : (
                  <span
                    style={{ backgroundColor: col.hex }}
                    className={`border ${
                      col.isBordered ? 'border-gray-300' : 'border-transparent'
                    }`}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
