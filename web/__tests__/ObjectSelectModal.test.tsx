import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ObjectSelectModal } from '@/components/ObjectSelectModal';
import { DetectedBox } from '@/types/search';

const mockBoxes: DetectedBox[] = [
  {
    box_id: 'box_shirt',
    label: 'Áo sơ mi',
    score: 0.6,
    box_2d: [0.15, 0.2, 0.5, 0.7],
  },
  {
    box_id: 'box_pants',
    label: 'Quần bò',
    score: 0.3,
    box_2d: [0.5, 0.25, 0.85, 0.65],
  },
  {
    box_id: 'box_shoes',
    label: 'Giày thể thao',
    score: 0.1,
    box_2d: [0.85, 0.3, 0.95, 0.6],
  },
];

describe('ObjectSelectModal Component', () => {
  const dummyFile = new File(['mock'], 'outfit.jpg', { type: 'image/jpeg' });

  test('returns null when isOpen is false or imageFile is null', () => {
    const { container: c1 } = render(
      <ObjectSelectModal
        isOpen={false}
        onClose={jest.fn()}
        imageFile={dummyFile}
        boxes={[]}
        onConfirm={jest.fn()}
      />
    );
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(
      <ObjectSelectModal
        isOpen={true}
        onClose={jest.fn()}
        imageFile={null}
        boxes={[]}
        onConfirm={jest.fn()}
      />
    );
    expect(c2.firstChild).toBeNull();
  });

  test('renders modal title, image preview, detected boxes with confidence percentages', () => {
    render(
      <ObjectSelectModal
        isOpen={true}
        onClose={jest.fn()}
        imageFile={dummyFile}
        boxes={mockBoxes}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText('Phân tích Trang phục từ Ảnh')).toBeInTheDocument();
    expect(screen.getByText('60% Tự tin')).toBeInTheDocument();
    expect(screen.getByText('30% Tự tin')).toBeInTheDocument();
    expect(screen.getByText('10% Tự tin')).toBeInTheDocument();
  });

  test('handles box selection and confirms with selected box and optional text', () => {
    const handleConfirm = jest.fn();
    const handleClose = jest.fn();

    render(
      <ObjectSelectModal
        isOpen={true}
        onClose={handleClose}
        imageFile={dummyFile}
        boxes={mockBoxes}
        onConfirm={handleConfirm}
      />
    );

    // Switch selection to pants
    const pantsRow = screen.getByText('Quần bò');
    fireEvent.click(pantsRow);

    // Enter optional text query
    const input = screen.getByPlaceholderText(/VD: 'áo sơ mi xanh'/i);
    fireEvent.change(input, { target: { value: 'quần jean xanh đậm' } });

    // Click confirm button
    const confirmBtn = screen.getByText('Bắt đầu tìm kiếm');
    fireEvent.click(confirmBtn);

    expect(handleConfirm).toHaveBeenCalledTimes(1);
    expect(handleConfirm).toHaveBeenCalledWith({
      selectedBox: expect.objectContaining({ box_id: 'box_pants' }),
      optionalText: 'quần jean xanh đậm',
      imageFile: dummyFile,
    });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
