import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ImageAnalysisBar } from '@/components/ImageAnalysisBar';
import { DetectedBox } from '@/types/search';

describe('ImageAnalysisBar Component', () => {
  const dummyFile = new File(['fake-image'], 'outfit.jpg', { type: 'image/jpeg' });
  const mockBoxes: DetectedBox[] = [
    {
      box_id: 'box_1',
      label: 'UpperGarment',
      score: 0.94,
      box_2d: [0.1, 0.1, 0.6, 0.8],
    },
    {
      box_id: 'box_2',
      label: 'Pants',
      score: 0.88,
      box_2d: [0.5, 0.2, 0.9, 0.7],
    },
  ];

  test('returns null when imageFile is null', () => {
    const { container } = render(
      <ImageAnalysisBar
        imageFile={null}
        boxes={[]}
        isAnalyzing={false}
        selectedBoxId={null}
        onSelectBox={jest.fn()}
        onOpenModal={jest.fn()}
        onClearImage={jest.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  test('displays loading pulse state when isAnalyzing is true', () => {
    render(
      <ImageAnalysisBar
        imageFile={dummyFile}
        boxes={[]}
        isAnalyzing={true}
        selectedBoxId={null}
        onSelectBox={jest.fn()}
        onOpenModal={jest.fn()}
        onClearImage={jest.fn()}
      />
    );

    expect(screen.getByText(/Đang nhận diện vật thể trong ảnh/i)).toBeInTheDocument();
    expect(screen.getByText('outfit.jpg')).toBeInTheDocument();
  });

  test('displays detected objects chips with confidence percentages', () => {
    const onSelectBox = jest.fn();
    render(
      <ImageAnalysisBar
        imageFile={dummyFile}
        boxes={mockBoxes}
        isAnalyzing={false}
        selectedBoxId="box_1"
        onSelectBox={onSelectBox}
        onOpenModal={jest.fn()}
        onClearImage={jest.fn()}
      />
    );

    expect(screen.getByText('Áo')).toBeInTheDocument();
    expect(screen.getByText('94%')).toBeInTheDocument();
    expect(screen.getByText('Quần')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText('Toàn bộ ảnh')).toBeInTheDocument();

    // Click Pants chip
    fireEvent.click(screen.getByText('Quần'));
    expect(onSelectBox).toHaveBeenCalledWith(mockBoxes[1]);

    // Click Toàn bộ ảnh
    fireEvent.click(screen.getByText('Toàn bộ ảnh'));
    expect(onSelectBox).toHaveBeenCalledWith(null);
  });

  test('triggers onClearImage when clear button is clicked', () => {
    const onClear = jest.fn();
    render(
      <ImageAnalysisBar
        imageFile={dummyFile}
        boxes={mockBoxes}
        isAnalyzing={false}
        selectedBoxId={null}
        onSelectBox={jest.fn()}
        onOpenModal={jest.fn()}
        onClearImage={onClear}
      />
    );

    const clearBtn = screen.getByText('Hủy ảnh');
    fireEvent.click(clearBtn);
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  test('does not present a low-confidence label as certain', () => {
    render(
      <ImageAnalysisBar
        imageFile={dummyFile}
        boxes={[{ box_id: 'uncertain', label: 'Top', score: 0.25, box_2d: [0.1, 0.1, 0.9, 0.9] }]}
        isAnalyzing={false}
        selectedBoxId={null}
        onSelectBox={jest.fn()}
        onOpenModal={jest.fn()}
        onClearImage={jest.fn()}
      />
    );

    expect(screen.getByText('Chưa xác định')).toBeInTheDocument();
    expect(screen.getByText('25%')).toBeInTheDocument();
  });
});
