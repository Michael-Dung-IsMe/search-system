import {
  API_BASE_URL,
  ApiError,
  deleteConstraint,
  detectObjects,
  getProductDetail,
  getProductImageUrl,
  searchProducts,
  transcribeAudio,
} from '@/lib/api';

describe('API Client Library (web/src/lib/api.ts)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  test('ApiError holds status code and detail', () => {
    const err = new ApiError('Bad request', 400, 'Invalid parameters');
    expect(err.name).toBe('ApiError');
    expect(err.statusCode).toBe(400);
    expect(err.detail).toBe('Invalid parameters');
    expect(err.message).toBe('Bad request');
  });

  test('detectObjects calls POST /api/detect with FormData and returns boxes', async () => {
    const mockResponse = {
      image_hash: 'abc123hash',
      total_boxes: 1,
      boxes: [
        {
          box_id: 'box_1',
          label: 'Top',
          score: 0.95,
          box_2d: [0.1, 0.2, 0.5, 0.6],
        },
      ],
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const mockFile = new File(['dummy-bytes'], 'photo.jpg', { type: 'image/jpeg' });
    const result = await detectObjects(mockFile);

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/detect`,
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(result.total_boxes).toBe(1);
    expect(result.boxes[0].label).toBe('Top');
  });

  test('detectObjects throws ApiError when response is not ok', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Unsupported image type' }),
    });

    const mockFile = new File(['bad'], 'test.txt', { type: 'text/plain' });
    await expect(detectObjects(mockFile)).rejects.toThrow(ApiError);
  });

  test('transcribeAudio calls POST /api/transcribe and returns text', async () => {
    const mockResponse = { text: 'áo sơ mi trắng', language: 'vi' };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const mockBlob = new Blob(['audio-data'], { type: 'audio/webm' });
    const result = await transcribeAudio(mockBlob);

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/transcribe`,
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(result.text).toBe('áo sơ mi trắng');
  });

  test('searchProducts calls POST /api/search with all query parameters', async () => {
    const mockSearchResponse = {
      session_id: 'sess-123',
      turn_index: 1,
      total_results: 5,
      search_state: {
        session_id: 'sess-123',
        turn_index: 1,
        exclude_colors: [],
        exclude_materials: [],
        active_chips: [],
      },
      items: [],
      latency_ms: 120,
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSearchResponse,
    });

    const mockFile = new File(['img'], 'crop.jpg', { type: 'image/jpeg' });
    const res = await searchProducts({
      query_text: 'quần bò',
      session_id: 'sess-123',
      reference_article_id: '0123456789',
      crop_box: '[0, 0, 1, 1]',
      image: mockFile,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/search`,
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(res.session_id).toBe('sess-123');
  });

  test('deleteConstraint calls DELETE /api/search/{session_id}/constraint', async () => {
    const mockSearchResponse = {
      session_id: 'sess-123',
      turn_index: 2,
      total_results: 3,
      search_state: {
        session_id: 'sess-123',
        turn_index: 2,
        exclude_colors: [],
        exclude_materials: [],
        active_chips: [],
      },
      items: [],
      latency_ms: 80,
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSearchResponse,
    });

    const res = await deleteConstraint('sess-123', 'color:White');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/search/sess-123/constraint?chip_id=color%3AWhite'),
      expect.objectContaining({ method: 'DELETE' })
    );
    expect(res.turn_index).toBe(2);
  });

  test('getProductDetail calls GET /api/products/{id}', async () => {
    const mockProduct = {
      article_id: '0123456789',
      product_code: '0123456',
      prod_name: 'Oxford Shirt',
      price_vnd: 499000,
      gender: 'Menswear',
      color_code: '10',
      color_name: 'White',
      category_group: 'Garment Upper body',
      category_sub: 'Shirt',
      detail_desc: 'Classic cotton shirt',
      image_path: '012/0123456789.jpg',
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockProduct,
    });

    const res = await getProductDetail('0123456789');
    expect(res.prod_name).toBe('Oxford Shirt');
    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/products/0123456789`
    );
  });

  test('getProductImageUrl resolves various image path scenarios', () => {
    // 1. Direct http URL
    expect(getProductImageUrl('https://example.com/photo.jpg')).toBe(
      'https://example.com/photo.jpg'
    );

    // 2. Fallback placeholder when empty
    expect(getProductImageUrl('', '')).toContain('unsplash.com');

    // 3. Article ID formatting
    expect(getProductImageUrl('', '123456')).toBe(
      `${API_BASE_URL}/images/0000123456.jpg`
    );

    // 4. Relative path
    expect(getProductImageUrl('/uploads/crop.jpg')).toBe(
      `${API_BASE_URL}/uploads/crop.jpg`
    );
  });
});
