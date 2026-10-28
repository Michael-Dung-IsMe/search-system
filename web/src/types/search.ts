/**
 * TypeScript Type Definitions for Multimodal Fashion Search Engine.
 * Strict contract-based models matching FastAPI Pydantic schemas.
 */

export interface SearchState {
  category?: string | null;
  gender?: string | null;
  color?: string | null;
  min_price?: number | null;
  max_price?: number | null;
  material?: string | null;
  style?: string | null;
  purpose?: string | null;
  exclude_colors: string[];
  exclude_materials: string[];
  reference_article_id?: string | null;
}

export interface SearchResultItem {
  article_id: string;
  prod_name: string;
  price_vnd: number;
  gender: string;
  color_code: string;
  color_name: string;
  category_group: string;
  category_sub: string;
  image_path: string;
  detail_desc: string;
  visual_similarity: number;
  final_score: number;
  explanation_badges: string[];
  match_type?: 'exact' | 'similar';
  similarity_reason?: string | null;
}

export interface SearchResponse {
  total_results: number;
  search_state: SearchState;
  items: SearchResultItem[];
  has_exact_match: boolean;
  exact_items: SearchResultItem[];
  similar_items: SearchResultItem[];
  message?: string | null;
  response_type?: 'search_results' | 'conversation';
  query_type?: 'text' | 'image' | 'voice';
  latency_ms: number;
  query_id?: string;
}

export interface DetectedBox {
  box_id: string;
  label: string;
  score: number;
  box_2d: [number, number, number, number]; // [ymin, xmin, ymax, xmax] normalized to [0.0, 1.0]
  polygon?: [number, number][]; // [[x, y], ...] normalized coordinates
}

export interface DetectResponse {
  image_hash: string;
  total_boxes: number;
  boxes: DetectedBox[];
}

export interface TranscribeResponse {
  text: string;
  language: string;
}

export interface ProductDetailResponse {
  article_id: string;
  product_code: string;
  prod_name: string;
  price_vnd: number;
  gender: string;
  color_code: string;
  color_name: string;
  category_group: string;
  category_sub: string;
  detail_desc: string;
  image_path: string;
}

export interface SearchQueryParams {
  query_text?: string;
  reference_article_id?: string;
  crop_box?: string; // JSON string of [ymin, xmin, ymax, xmax]
  image?: File | Blob;
  query_type?: 'text' | 'image' | 'voice';
}
