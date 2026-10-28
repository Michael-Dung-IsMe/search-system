import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import Home from '@/app/page';
import * as api from '@/lib/api';
import { SearchResponse } from '@/types/search';

jest.mock('@/lib/api');

const mockResponse: SearchResponse = {
  total_results: 1,
  search_state: {
    category: 'T-shirt',
    color: 'White',
    max_price: 500_000,
    exclude_colors: [],
    exclude_materials: [],
  },
  items: [
    {
      article_id: '0108775015',
      prod_name: 'Strap top',
      price_vnd: 299_000,
      gender: 'Ladieswear',
      color_code: '10',
      color_name: 'White',
      category_group: 'Garment Upper body',
      category_sub: 'T-shirt',
      image_path: '0108775015.jpg',
      detail_desc: 'Jersey top',
      visual_similarity: 0.95,
      final_score: 0.9,
      explanation_badges: [],
      match_type: 'exact',
    },
  ],
  has_exact_match: true,
  exact_items: [],
  similar_items: [],
  response_type: 'search_results',
  query_type: 'text',
  latency_ms: 110,
};

describe('Home page independent search flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.searchProducts as jest.Mock).mockResolvedValue(mockResponse);
    (api.detectObjects as jest.Mock).mockResolvedValue({
      image_hash: 'img123',
      total_boxes: 1,
      boxes: [
        { box_id: 'b1', label: 'Pants', score: 0.85, box_2d: [0.1, 0.1, 0.8, 0.8] },
      ],
    });
  });

  test('starts empty and does not render the removed refinement bar', () => {
    render(<Home />);

    expect(api.searchProducts).not.toHaveBeenCalled();
    expect(screen.queryByPlaceholderText(/Tinh chỉnh thêm/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Tìm kiếm phong cách thời trang/i)).toBeInTheDocument();
  });

  test('submits a self-contained text search without session_id', async () => {
    render(<Home />);

    const input = screen.getByPlaceholderText(/Nhập tên sản phẩm/i);
    fireEvent.change(input, { target: { value: 'áo thun trắng dưới 500k' } });
    fireEvent.click(screen.getByRole('button', { name: /^Tìm kiếm$/i }));

    await waitFor(() => expect(screen.getByText('Strap top')).toBeInTheDocument());
    expect(api.searchProducts).toHaveBeenCalledWith(
      expect.objectContaining({ query_text: 'áo thun trắng dưới 500k' })
    );
    const request = (api.searchProducts as jest.Mock).mock.calls[0][0];
    expect(request.session_id).toBeUndefined();
    expect(screen.queryByPlaceholderText(/Tinh chỉnh thêm/i)).not.toBeInTheDocument();
  });

  test('submits all selected sidebar facets in one request', async () => {
    render(<Home />);
    const input = screen.getByPlaceholderText(/Nhập tên sản phẩm/i);
    fireEvent.change(input, { target: { value: 'áo thun trắng dưới 500k' } });
    fireEvent.click(screen.getByRole('button', { name: /^Tìm kiếm$/i }));
    await waitFor(() => expect(screen.getByText('Strap top')).toBeInTheDocument());

    fireEvent.click(screen.getByTitle('Hồng'));

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenLastCalledWith(
        expect.objectContaining({
          query_text: expect.stringMatching(/loại T-shirt.*màu pink.*giá dưới 500000 đồng/i),
        })
      );
    });
  });

  test('uploads an image and performs image search without session state', async () => {
    const { container } = render(<Home />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy-bytes'], 'outfit.jpg', { type: 'image/jpeg' });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ image: file, query_type: 'image' })
      );
      expect(api.detectObjects).toHaveBeenCalledWith(file);
    });
    const request = (api.searchProducts as jest.Mock).mock.calls[0][0];
    expect(request.session_id).toBeUndefined();
  });

  test('shows an API error after the user submits a search', async () => {
    (api.searchProducts as jest.Mock).mockRejectedValue(new Error('Network connection error'));
    render(<Home />);

    const input = screen.getByPlaceholderText(/Nhập tên sản phẩm/i);
    fireEvent.change(input, { target: { value: 'áo khoác' } });
    fireEvent.click(screen.getByRole('button', { name: /^Tìm kiếm$/i }));

    await waitFor(() => {
      expect(screen.getByText('Network connection error')).toBeInTheDocument();
    });
  });
});
