import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Home from '@/app/page';
import * as api from '@/lib/api';
import { SearchResponse } from '@/types/search';

jest.mock('@/lib/api');

const mockInitialResponse: SearchResponse = {
  session_id: 'session-xyz-123',
  turn_index: 1,
  total_results: 2,
  search_state: {
    session_id: 'session-xyz-123',
    turn_index: 1,
    category: 'Shirt',
    color: 'White',
    exclude_colors: [],
    exclude_materials: ['leather'],
    active_chips: [
      {
        chip_id: 'cat:Shirt',
        label: 'Loại: Shirt',
        chip_type: 'category',
        value: 'Shirt',
        is_removable: true,
      },
      {
        chip_id: 'exclude_mat:leather',
        label: '🚫 Loại trừ: da',
        chip_type: 'exclude_material',
        value: 'leather',
        is_removable: true,
      },
    ],
  },
  items: [
    {
      article_id: '0108775015',
      prod_name: 'Strap top',
      price_vnd: 299000,
      gender: 'Ladieswear',
      color_code: '10',
      color_name: 'White',
      category_group: 'Garment Upper body',
      category_sub: 'Top',
      image_path: '010/0108775015.jpg',
      detail_desc: 'Jersey top',
      visual_similarity: 0.95,
      final_score: 0.9,
      explanation_badges: ['95% tương đồng'],
    },
  ],
  latency_ms: 110,
};

describe('Home Page Integration (web/src/app/page.tsx)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.searchProducts as jest.Mock).mockResolvedValue(mockInitialResponse);
  });

  test('executes initial search on mount and renders products and active chips', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ query_text: 'áo sơ mi' })
      );
      expect(screen.getByText('Strap top')).toBeInTheDocument();
      expect(screen.getByText('Loại: Shirt')).toBeInTheDocument();
      expect(screen.getByText('🚫 Loại trừ: da')).toBeInTheDocument();
    });
  });

  test('submits new text search from SearchBar', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Strap top')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Mô tả phong cách/i);
    fireEvent.change(searchInput, { target: { value: 'quần short' } });

    const searchBtn = screen.getByText('Tìm kiếm');
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ query_text: 'quần short' })
      );
    });
  });

  test('removes chip when close button is clicked', async () => {
    (api.deleteConstraint as jest.Mock).mockResolvedValue({
      ...mockInitialResponse,
      turn_index: 2,
      search_state: {
        ...mockInitialResponse.search_state,
        active_chips: [mockInitialResponse.search_state.active_chips[1]],
      },
    });

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Loại: Shirt')).toBeInTheDocument();
    });

    const removeBtn = screen.getByTitle('Xóa điều kiện Loại: Shirt');
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(api.deleteConstraint).toHaveBeenCalledWith('session-xyz-123', 'cat:Shirt');
    });
  });

  test('clears all removable chips when "Xóa tất cả" is clicked', async () => {
    (api.deleteConstraint as jest.Mock).mockResolvedValue(mockInitialResponse);

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Xóa tất cả')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Xóa tất cả'));

    await waitFor(() => {
      expect(api.deleteConstraint).toHaveBeenCalled();
    });
  });

  test('triggers visual similar search when card button is clicked', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Tìm tương tự')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Tìm tương tự'));

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({
          reference_article_id: '0108775015',
        })
      );
    });
  });

  test('submits refinement query from StickyRefineBar', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Tinh chỉnh thêm/i)).toBeInTheDocument();
    });

    const refineInput = screen.getByPlaceholderText(/Tinh chỉnh thêm/i);
    fireEvent.change(refineInput, { target: { value: 'chất liệu cotton mềm' } });

    const refineSubmit = screen.getByTitle('Gửi lượt tinh chỉnh');
    fireEvent.click(refineSubmit);

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ query_text: 'chất liệu cotton mềm' })
      );
    });
  });

  test('handles image upload, clears previous keyword, runs ViT in background and displays analysis bar', async () => {
    (api.detectObjects as jest.Mock).mockResolvedValue({
      image_hash: 'img123',
      total_boxes: 1,
      boxes: [
        {
          box_id: 'b1',
          label: 'Top',
          score: 0.85,
          box_2d: [0.1, 0.1, 0.5, 0.5],
        },
      ],
    });

    const { container } = render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Strap top')).toBeInTheDocument();
    });

    // Enter a previous keyword first to test that it gets cleared
    const searchInput = screen.getByPlaceholderText(/Mô tả phong cách/i) as HTMLInputElement;
    fireEvent.change(searchInput, { target: { value: 'áo sơ mi cũ' } });
    expect(searchInput.value).toBe('áo sơ mi cũ');

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy-bytes'], 'outfit.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // 1. Keyword should be cleared immediately
    expect(searchInput.value).toBe('');

    // 2. Initial image search should be triggered without old keyword
    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({
          image: file,
          query_text: undefined,
        })
      );
    });

    // 3. ViT detection runs in background and displays result line
    await waitFor(() => {
      expect(api.detectObjects).toHaveBeenCalledWith(file);
      expect(screen.getByTestId('image-analysis-bar')).toBeInTheDocument();
      expect(screen.getByText('Áo')).toBeInTheDocument();
    });

    // 4. Click detected object chip to focus search on that garment
    const topChip = screen.getByText('Áo');
    fireEvent.click(topChip);

    await waitFor(() => {
      expect(api.searchProducts).toHaveBeenCalledWith(
        expect.objectContaining({
          image: file,
          crop_box: '[0.1,0.1,0.5,0.5]',
        })
      );
    });
  });

  test('displays error message banner when search fails', async () => {
    (api.searchProducts as jest.Mock).mockRejectedValue(new Error('Network connection error'));

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Network connection error')).toBeInTheDocument();
    });

    const closeBtn = screen.getByText('Đóng');
    fireEvent.click(closeBtn);
    expect(screen.queryByText('Network connection error')).not.toBeInTheDocument();
  });

  test('handles voice search transcription successfully', async () => {
    (api.transcribeAudio as jest.Mock).mockResolvedValue({
      text: 'áo hoodie đen',
      language: 'vi',
    });

    const mockStream = {
      getTracks: jest.fn().mockReturnValue([{ stop: jest.fn() }]),
    };
    (window as any).MediaRecorder = jest.fn().mockImplementation(() => {
      const rec: any = {
        start: jest.fn(),
        stop: jest.fn().mockImplementation(() => {
          if (rec.onstop) rec.onstop();
        }),
        state: 'recording',
        mimeType: 'audio/webm',
        ondataavailable: null,
        onstop: null,
      };
      return rec;
    });
    window.navigator.mediaDevices = {
      getUserMedia: jest.fn().mockResolvedValue(mockStream),
    } as any;

    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('Strap top')).toBeInTheDocument();
    });

    const micBtn = screen.getByTitle(/Tìm bằng giọng nói/i);
    fireEvent.click(micBtn);

    const stopBtn = await screen.findByTitle(/Bấm để dừng ghi âm/i);
    fireEvent.click(stopBtn);

    await waitFor(() => {
      expect(api.transcribeAudio).toHaveBeenCalled();
    });
  });

  test('displays error message when constraint removal fails', async () => {
    (api.deleteConstraint as jest.Mock).mockRejectedValue(new Error('Constraint removal DB error'));

    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('Loại: Shirt')).toBeInTheDocument();
    });

    const removeBtn = screen.getByTitle('Xóa điều kiện Loại: Shirt');
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(screen.getByText('Constraint removal DB error')).toBeInTheDocument();
    });
  });
});
