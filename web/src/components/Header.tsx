'use client';

import React from 'react';

interface HeaderProps {
  statusText?: string;
  isOnline?: boolean;
}

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/" className="flex items-center gap-2 group">
            <span className="text-xl font-extrabold tracking-widest uppercase text-gray-900 font-sans group-hover:text-gray-700 transition-colors">
              ATELIER
            </span>
            <span className="text-[10px] font-bold tracking-wider uppercase bg-gray-900 text-white px-2 py-0.5 rounded-full">
              SEARCH
            </span>
          </a>
        </div>

        <div className="flex items-center gap-6 text-xs font-medium text-gray-600">
          <span className="hidden md:inline hover:text-gray-900 cursor-pointer transition-colors">
            Khám phá xu hướng
          </span>
          <span className="hidden sm:inline hover:text-gray-900 cursor-pointer transition-colors">
            Trợ giúp
          </span>
          <div className="flex items-center gap-1.5 py-1 px-3 rounded-full bg-gray-100 text-gray-800 font-semibold text-xs hover:bg-gray-200 cursor-pointer transition-colors">
            <span>Tài khoản</span>
          </div>
        </div>
      </div>
    </header>
  );
};
