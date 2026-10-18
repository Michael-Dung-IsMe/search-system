import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationalFeed } from '@/components/ConversationalFeed';
import { StickyRefineBar } from '@/components/StickyRefineBar';
import { SearchState } from '@/types/search';

describe('ConversationalFeed Component', () => {
  test('returns null when state is null or turn_index is 0', () => {
    const { container: c1 } = render(
      <ConversationalFeed state={null} totalResults={0} />
    );
    expect(c1.firstChild).toBeNull();

    const emptyState: SearchState = {
      session_id: 's1',
      turn_index: 0,
      exclude_colors: [],
      exclude_materials: [],
      active_chips: [],
    };
    const { container: c2 } = render(
      <ConversationalFeed state={emptyState} totalResults={0} />
    );
    expect(c2.firstChild).toBeNull();
  });

  test('synthesizes multi-attribute summary text properly', () => {
    const mockState: SearchState = {
      session_id: 's1',
      turn_index: 2,
      category: 'Áo sơ mi',
      color: 'Trắng',
      max_price: 500000,
      exclude_materials: ['da'],
      exclude_colors: ['đen'],
      active_chips: [],
    };

    render(
      <ConversationalFeed state={mockState} totalResults={12} latencyMs={150} />
    );

    expect(screen.getByText(/danh mục "Áo sơ mi"/i)).toBeInTheDocument();
    expect(screen.getByText(/màu "Trắng"/i)).toBeInTheDocument();
    expect(screen.getByText(/giá dưới 500\.000₫/i)).toBeInTheDocument();
    expect(screen.getByText(/loại trừ chất liệu \[da\]/i)).toBeInTheDocument();
    expect(screen.getByText(/loại trừ màu \[đen\]/i)).toBeInTheDocument();
    expect(screen.getByText('Tìm thấy 12 sản phẩm')).toBeInTheDocument();
    expect(screen.getByText('(150ms)')).toBeInTheDocument();
  });
});

describe('StickyRefineBar Component', () => {
  test('renders input and submits text on submit', () => {
    const handleRefine = jest.fn();
    render(<StickyRefineBar onRefine={handleRefine} />);

    const input = screen.getByPlaceholderText(/Tinh chỉnh thêm/i);
    fireEvent.change(input, { target: { value: 'đổi sang màu xanh' } });

    const submitBtn = screen.getByTitle('Gửi lượt tinh chỉnh');
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    expect(handleRefine).toHaveBeenCalledTimes(1);
    expect(handleRefine).toHaveBeenCalledWith('đổi sang màu xanh');
  });

  test('calls onVoiceTrigger when voice icon is clicked', () => {
    const handleVoice = jest.fn();
    render(<StickyRefineBar onRefine={jest.fn()} onVoiceTrigger={handleVoice} />);

    const voiceBtn = screen.getByTitle('Nói yêu cầu tinh chỉnh');
    fireEvent.click(voiceBtn);
    expect(handleVoice).toHaveBeenCalledTimes(1);
  });
});
