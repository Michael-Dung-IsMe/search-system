'use client';

import React, { useCallback, useState } from 'react';
import { Header } from '@/components/Header';
import { SearchBar } from '@/components/SearchBar';
import { ProductGrid } from '@/components/ProductGrid';
import { ObjectSelectModal } from '@/components/ObjectSelectModal';
import { ImageAnalysisBar } from '@/components/ImageAnalysisBar';
import { FacetSidebar, FacetFilterState } from '@/components/FacetSidebar';
import { RecommendedPills } from '@/components/RecommendedPills';
import {
  detectObjects,
  searchProducts,
  transcribeAudio,
} from '@/lib/api';
import {
  DetectedBox,
  SearchResultItem,
} from '@/types/search';
import { AlertCircle, Flame } from 'lucide-react';

const RECOMMENDED_CATEGORIES = [
  'Tất cả',
  'T-shirt',
  'Blouse',
  'Sweater',
  'Top',
  'Blazer',
  'Hoodie',
  'Jacket',
  'Dress',
];

const TRENDING_SEARCHES = [
  'Áo sơ mi trắng công sở',
  'Váy dạ hội Dark Blue',
  'Áo len cashmere',
  'Blazer nữ dáng suông',
  'T-shirt cotton basic',
  'Áo khoác bomber',
  'Đầm satin wrapover',
  'Quần tây ống rộng',
];

export default function Home() {
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [queryText, setQueryText] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [items, setItems] = useState<SearchResultItem[]>([]);
  const [exactItems, setExactItems] = useState<SearchResultItem[]>([]);
  const [similarItems, setSimilarItems] = useState<SearchResultItem[]>([]);
  const [hasExactMatch, setHasExactMatch] = useState<boolean>(true);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [responseType, setResponseType] = useState<'search_results' | 'conversation'>('search_results');
  const [queryType, setQueryType] = useState<'text' | 'image' | 'voice'>('text');
  const [totalResults, setTotalResults] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Facet Sidebar State
  const [facetFilters, setFacetFilters] = useState<FacetFilterState>({
    category: null,
    minPrice: null,
    maxPrice: null,
    color: null,
  });

  // Object Detection & Background Image Analysis State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [detectedBoxes, setDetectedBoxes] = useState<DetectedBox[]>([]);
  const [isAnalyzingImage, setIsAnalyzingImage] = useState<boolean>(false);
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);

  // 1. Unified Search Handler
  const executeSearch = useCallback(
    async (params: {
      text?: string;
      image?: File;
      cropBoxCoords?: [number, number, number, number] | null;
      referenceId?: string;
      queryType?: 'text' | 'image' | 'voice';
    }) => {
      setIsProcessing(true);
      setErrorMessage(null);

      try {
        const cropBoxJson = params.cropBoxCoords
          ? JSON.stringify(params.cropBoxCoords)
          : undefined;

        let textToSend: string | undefined;
        if (params.text !== undefined) {
          textToSend = params.text;
        } else if (params.image) {
          textToSend = undefined;
        } else {
          textToSend = queryText || undefined;
        }

        const res = await searchProducts({
          query_text: textToSend,
          reference_article_id: params.referenceId,
          image: params.image,
          crop_box: cropBoxJson,
          query_type: params.queryType,
        });

        setHasSearched(true);
        setFacetFilters({
          category: res.search_state.category || null,
          color: res.search_state.color || null,
          minPrice: res.search_state.min_price || null,
          maxPrice: res.search_state.max_price || null,
        });
        setItems(res.items || []);
        setExactItems(res.exact_items || []);
        setSimilarItems(res.similar_items || []);
        setHasExactMatch(res.has_exact_match !== undefined ? res.has_exact_match : true);
        setSearchMessage(res.message || null);
        setResponseType(res.response_type || 'search_results');
        setQueryType(res.query_type || 'text');
        setTotalResults(res.total_results);
        setLatencyMs(res.latency_ms);
      } catch (err: unknown) {
        console.error('Search execution failed:', err);
        const msg = err instanceof Error ? err.message : 'Lỗi kết nối khi tìm kiếm. Vui lòng thử lại.';
        setErrorMessage(msg);
      } finally {
        setIsProcessing(false);
      }
    },
    [queryText]
  );

  // 2. Voice Input Handler
  const handleVoiceRecorded = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await transcribeAudio(audioBlob, 'voice_query.webm');
      if (res.text) {
        setQueryText(res.text);
        await executeSearch({ text: res.text, queryType: 'voice' });
      }
    } catch (err: unknown) {
      console.error('Voice transcription failed:', err);
      const msg = err instanceof Error ? err.message : 'Không thể nhận diện giọng nói.';
      setErrorMessage(`Lỗi ghi âm: ${msg}`);
      setIsProcessing(false);
    }
  };

  // 3. Image Upload
  const handleImageSelected = async (file: File) => {
    setQueryText('');
    setSelectedImageFile(file);
    setSelectedBoxId(null);
    setDetectedBoxes([]);
    setIsAnalyzingImage(true);

    executeSearch({
      image: file,
      text: undefined,
      queryType: 'image',
    });

    try {
      const res = await detectObjects(file);
      setDetectedBoxes(res.boxes || []);
    } catch (err: unknown) {
      console.warn('Object detection returned error or empty:', err);
      setDetectedBoxes([]);
    } finally {
      setIsAnalyzingImage(false);
    }
  };

  // 4. Select a detected object box to refine search
  const handleSelectBox = (box: DetectedBox | null) => {
    setSelectedBoxId(box ? box.box_id : null);
    if (!selectedImageFile) return;

    executeSearch({
      image: selectedImageFile,
      cropBoxCoords: box ? box.box_2d : null,
      text: queryText || undefined,
    });
  };

  // 5. Clear image search & return to text search
  const handleClearImage = () => {
    setSelectedImageFile(null);
    setDetectedBoxes([]);
    setSelectedBoxId(null);
    setIsAnalyzingImage(false);
    if (queryText) {
      executeSearch({ text: queryText });
    } else {
      setHasSearched(false);
      setItems([]);
      setExactItems([]);
      setSimilarItems([]);
    }
  };

  // 6. Modal Confirm: Search with selected box
  const handleModalConfirm = ({
    selectedBox,
    optionalText,
    imageFile,
  }: {
    selectedBox: DetectedBox | null;
    optionalText: string;
    imageFile: File;
  }) => {
    if (optionalText) {
      setQueryText(optionalText);
    }
    setSelectedBoxId(selectedBox ? selectedBox.box_id : null);

    executeSearch({
      text: optionalText || undefined,
      image: imageFile,
      cropBoxCoords: selectedBox?.box_2d || null,
    });
  };

  // 7. Visual Similar Search on Card
  const handleFindSimilar = (articleId: string, prodName: string) => {
    setQueryText(`Sản phẩm tương tự ${prodName}`);
    executeSearch({
      referenceId: articleId,
      text: undefined,
      queryType: 'image',
    });
  };

  const buildFacetQuery = (filters: FacetFilterState): string => {
    const parts: string[] = [];
    if (filters.category) parts.push(`loại ${filters.category}`);
    if (filters.color) parts.push(`màu ${filters.color}`);
    if (filters.minPrice && filters.maxPrice) {
      parts.push(`giá từ ${filters.minPrice} đến ${filters.maxPrice} đồng`);
    } else if (filters.maxPrice) {
      parts.push(`giá dưới ${filters.maxPrice} đồng`);
    } else if (filters.minPrice) {
      parts.push(`giá trên ${filters.minPrice} đồng`);
    }
    return parts.join(', ');
  };

  const searchWithFacets = (filters: FacetFilterState) => {
    const text = buildFacetQuery(filters);
    if (!text && !selectedImageFile) {
      setHasSearched(false);
      setItems([]);
      setExactItems([]);
      setSimilarItems([]);
      setTotalResults(0);
      return;
    }
    executeSearch({
      text: text || undefined,
      image: selectedImageFile || undefined,
      queryType: selectedImageFile ? 'image' : 'text',
    });
  };

  // 8. Category shortcuts send a complete, independent filter request.
  const handleSelectRecommendedCategory = (category: string) => {
    const nextFilters = { ...facetFilters, category: category || null };
    setFacetFilters(nextFilters);
    searchWithFacets(nextFilters);
  };

  // 9. Sidebar always submits all selected filters in one request.
  const handleFacetFilterChange = (newFilters: FacetFilterState) => {
    setFacetFilters(newFilters);
    searchWithFacets(newFilters);
  };

  const handleResetFilters = () => {
    const emptyFilters = { category: null, minPrice: null, maxPrice: null, color: null };
    setFacetFilters(emptyFilters);
    searchWithFacets(emptyFilters);
  };

  const handleTrendingClick = (term: string) => {
    setQueryText(term);
    executeSearch({ text: term });
  };

  // Determine whether we are in initial state or active results state
  const isInitialState = !hasSearched && !selectedImageFile;

  return (
    <div className="min-h-screen bg-[#fafafa] text-[#111827] flex flex-col">
      <Header />

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6 flex-1">
        {/* Error Banner */}
        {errorMessage && (
          <div className="w-full max-w-3xl mx-auto p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3 text-red-700 text-sm animate-fade-in">
            <AlertCircle size={18} className="flex-shrink-0" />
            <span className="flex-1">{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-red-500 hover:text-red-800 font-semibold underline"
            >
              Đóng
            </button>
          </div>
        )}

        {/* ===================================================================
            TRẠNG THÁI 1: KHI MỞ LẦN ĐẦU (INITIAL / EMPTY STATE)
            Không hiển thị bất kỳ sản phẩm nào, tập trung vào thanh tìm kiếm lớn
           =================================================================== */}
        {isInitialState ? (
          <div className="flex flex-col items-center justify-center my-auto py-16 sm:py-24 max-w-3xl mx-auto w-full text-center animate-fade-in">
            {/* Headline */}
            <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-gray-900 mb-3">
              Tìm kiếm phong cách thời trang bạn mong muốn
            </h1>
            <p className="text-sm sm:text-base text-gray-500 mb-8 max-w-xl mx-auto">
              Nhập từ khóa mô tả, bấm biểu tượng mic để nói tự nhiên hoặc tải ảnh trang phục lên để tìm kiếm sản phẩm tương đồng.
            </p>

            {/* Hero Omni-Search Bar */}
            <div className="w-full mb-6">
              <SearchBar
                value={queryText}
                onChange={setQueryText}
                onSearch={(text) => executeSearch({ text })}
                onImageSelected={handleImageSelected}
                onVoiceRecorded={handleVoiceRecorded}
                isProcessing={isProcessing}
                placeholder="Nhập tên sản phẩm, chất liệu, màu sắc, phong cách..."
              />
            </div>

            {/* Trending Searches */}
            <div className="flex flex-col items-center gap-3 w-full">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                <Flame size={14} className="text-amber-500" />
                <span>Xu hướng tìm kiếm</span>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
                {TRENDING_SEARCHES.map((term) => (
                  <button
                    key={term}
                    type="button"
                    onClick={() => handleTrendingClick(term)}
                    className="btns text-xs !py-1.5 !px-3 hover:!border-gray-900 transition-all"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* ===================================================================
              TRẠNG THÁI 2: SAU KHI TÌM KIẾM (ACTIVE / RESULTS STATE)
              Layout 2 cột chuyên nghiệp: Facet Sidebar bên trái + Product Grid bên phải
             =================================================================== */
          <div className="flex flex-col gap-5 animate-fade-in">
            {/* Top Compact Search Bar */}
            <div className="flex flex-col gap-3">
              <SearchBar
                value={queryText}
                onChange={setQueryText}
                onSearch={(text) => executeSearch({ text, image: selectedImageFile || undefined })}
                onImageSelected={handleImageSelected}
                onVoiceRecorded={handleVoiceRecorded}
                isProcessing={isProcessing}
                placeholder="Mô tả phong cách, tải ảnh outfit hoặc nói yêu cầu..."
              />

              {/* Background ViT Image Analysis Status Bar */}
              <ImageAnalysisBar
                imageFile={selectedImageFile}
                boxes={detectedBoxes}
                isAnalyzing={isAnalyzingImage}
                selectedBoxId={selectedBoxId}
                onSelectBox={handleSelectBox}
                onOpenModal={() => setIsModalOpen(true)}
                onClearImage={handleClearImage}
              />
            </div>

            {/* Quick Recommended Category Pills */}
            <RecommendedPills
              categories={RECOMMENDED_CATEGORIES}
              selectedCategory={facetFilters.category || null}
              onSelectCategory={handleSelectRecommendedCategory}
            />

            {/* Main 2-Column E-Commerce Layout */}
            <div className="flex flex-col lg:flex-row items-start gap-8 mt-2">
              {/* Left Column: Facet Sidebar */}
              <FacetSidebar
                filters={facetFilters}
                onFilterChange={handleFacetFilterChange}
                onResetFilters={handleResetFilters}
              />

              {/* Right Column: Search Results Header & Product Grid */}
              <div className="flex-1 w-full flex flex-col">
                {/* Results Meta Bar */}
                <div className="flex items-center justify-between pb-3 border-b border-gray-200">
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-base sm:text-lg font-bold text-gray-900">
                      {responseType === 'conversation'
                        ? 'Trợ lý thời trang'
                        : totalResults > 0
                          ? `${totalResults} sản phẩm phù hợp`
                          : 'Kết quả tìm kiếm'}
                    </h2>
                    {latencyMs > 0 && (
                      <span className="text-xs text-gray-400">• {latencyMs}ms</span>
                    )}
                  </div>
                  {responseType === 'search_results' && (
                    <span className="text-xs text-gray-500">
                      Sắp xếp: <strong className="text-gray-900">Liên quan nhất</strong>
                    </span>
                  )}
                </div>

                {/* Product Grid */}
                <ProductGrid
                  items={items}
                  exactItems={exactItems}
                  similarItems={similarItems}
                  hasExactMatch={hasExactMatch}
                  message={searchMessage}
                  responseType={responseType}
                  showImageSimilarity={queryType === 'image'}
                  isLoading={isProcessing && items.length === 0 && exactItems.length === 0}
                  onFindSimilar={handleFindSimilar}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Interactive Object Bounding Box Modal for Outfit Photos */}
      <ObjectSelectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        imageFile={selectedImageFile}
        boxes={detectedBoxes}
        initialSelectedBoxId={selectedBoxId}
        onConfirm={handleModalConfirm}
      />
    </div>
  );
}
