import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StateChipsBar } from '@/components/StateChipsBar';
import { ConstraintChip } from '@/types/search';

describe('StateChipsBar Component', () => {
  const mockChips: ConstraintChip[] = [
    {
      chip_id: 'color:White',
      label: 'Màu: Trắng',
      chip_type: 'color',
      value: 'White',
      is_removable: true,
    },
    {
      chip_id: 'price:500000',
      label: 'Giá: ≤ 500.000₫',
      chip_type: 'price',
      value: 500000,
      is_removable: true,
    },
    {
      chip_id: 'exclude_material:leather',
      label: '🚫 Loại trừ: Da',
      chip_type: 'exclude_material',
      value: 'leather',
      is_removable: true,
    },
  ];

  test('returns null when chips array is empty', () => {
    const { container } = render(
      <StateChipsBar chips={[]} onRemoveChip={jest.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  test('renders all chips with appropriate styling for negative constraints', () => {
    render(<StateChipsBar chips={mockChips} onRemoveChip={jest.fn()} />);
    expect(screen.getByText('Màu: Trắng')).toBeInTheDocument();
    expect(screen.getByText('Giá: ≤ 500.000₫')).toBeInTheDocument();
    expect(screen.getByText('🚫 Loại trừ: Da')).toBeInTheDocument();
  });

  test('calls onRemoveChip when close icon is clicked', () => {
    const handleRemove = jest.fn();
    render(<StateChipsBar chips={mockChips} onRemoveChip={handleRemove} />);

    const removeBtn = screen.getByTitle('Xóa điều kiện Màu: Trắng');
    fireEvent.click(removeBtn);

    expect(handleRemove).toHaveBeenCalledTimes(1);
    expect(handleRemove).toHaveBeenCalledWith('color:White');
  });

  test('renders Clear All button and handles click', () => {
    const handleClearAll = jest.fn();
    render(
      <StateChipsBar
        chips={mockChips}
        onRemoveChip={jest.fn()}
        onClearAll={handleClearAll}
      />
    );

    const clearAllBtn = screen.getByText('Xóa tất cả');
    expect(clearAllBtn).toBeInTheDocument();
    fireEvent.click(clearAllBtn);
    expect(handleClearAll).toHaveBeenCalledTimes(1);
  });
});
