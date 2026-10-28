/**
 * API Client for Multimodal Fashion Search Engine.
 * Interacts with FastAPI backend endpoints.
 */

import {
  DetectResponse,
  ProductDetailResponse,
  SearchQueryParams,
  SearchResponse,
  TranscribeResponse,
} from '@/types/search';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  statusCode: number;
  detail?: string;

  constructor(message: string, statusCode: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // Body not JSON
    }
    throw new ApiError(
      `API request failed with status ${res.status}: ${errorDetail}`,
      res.status,
      errorDetail
    );
  }
  return res.json() as Promise<T>;
}

/**
 * Detect garments in outfit image using OWL-ViT via POST /api/detect
 */
export async function detectObjects(imageFile: File | Blob): Promise<DetectResponse> {
  const formData = new FormData();
  formData.append('file', imageFile, 'outfit.jpg');

  const res = await fetch(`${API_BASE_URL}/api/detect`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<DetectResponse>(res);
}

/**
 * Transcribe recorded speech audio via POST /api/transcribe
 */
export async function transcribeAudio(
  audioBlob: Blob,
  filename = 'recording.webm'
): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append('file', audioBlob, filename);

  const res = await fetch(`${API_BASE_URL}/api/transcribe`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<TranscribeResponse>(res);
}

/**
 * Execute one independent multimodal search via POST /api/search
 */
export async function searchProducts(
  params: SearchQueryParams
): Promise<SearchResponse> {
  const formData = new FormData();

  if (params.query_text) {
    formData.append('query_text', params.query_text);
  }
  if (params.reference_article_id) {
    formData.append('reference_article_id', params.reference_article_id);
  }
  if (params.crop_box) {
    formData.append('crop_box', params.crop_box);
  }
  if (params.image) {
    formData.append('image', params.image);
  }
  if (params.query_type) {
    formData.append('query_type', params.query_type);
  }

  const res = await fetch(`${API_BASE_URL}/api/search`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<SearchResponse>(res);
}

/**
 * Fetch full product detail by article ID via GET /api/products/{id}
 */
export async function getProductDetail(
  articleId: string
): Promise<ProductDetailResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/products/${encodeURIComponent(articleId)}`
  );

  return handleResponse<ProductDetailResponse>(res);
}

/**
 * Helper to resolve static image URL from API or placeholder
 */
export function getProductImageUrl(imagePath?: string, articleId?: string): string {
  if (!imagePath && !articleId) {
    return 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=600&q=80';
  }

  if (imagePath && (imagePath.startsWith('http://') || imagePath.startsWith('https://'))) {
    return imagePath;
  }

  if (articleId) {
    const cleanId = articleId.trim().padStart(10, '0');
    return `${API_BASE_URL}/images/${cleanId}.jpg`;
  }

  return `${API_BASE_URL}/${imagePath?.replace(/^\//, '')}`;
}
