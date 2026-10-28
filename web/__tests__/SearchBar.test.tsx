import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SearchBar } from '@/components/SearchBar';

describe('SearchBar Component', () => {
  test('updates value on change and fires onSearch on Enter key', () => {
    const handleChange = jest.fn();
    const handleSearch = jest.fn();

    render(
      <SearchBar
        value="quần jean"
        onChange={handleChange}
        onSearch={handleSearch}
        onImageSelected={jest.fn()}
        onVoiceRecorded={jest.fn()}
      />
    );

    const input = screen.getByDisplayValue('quần jean');
    fireEvent.change(input, { target: { value: 'quần jean xanh' } });
    expect(handleChange).toHaveBeenCalledWith('quần jean xanh');

    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(handleSearch).toHaveBeenCalledWith('quần jean');
  });

  test('calls onSearch when search button is clicked', () => {
    const handleSearch = jest.fn();
    render(
      <SearchBar
        value="áo sơ mi"
        onChange={jest.fn()}
        onSearch={handleSearch}
        onImageSelected={jest.fn()}
        onVoiceRecorded={jest.fn()}
      />
    );

    const searchBtn = screen.getByText('Tìm kiếm');
    fireEvent.click(searchBtn);
    expect(handleSearch).toHaveBeenCalledWith('áo sơ mi');
  });

  test('triggers file input click when camera button is clicked', () => {
    const handleImageSelected = jest.fn();
    const { container } = render(
      <SearchBar
        value=""
        onChange={jest.fn()}
        onSearch={jest.fn()}
        onImageSelected={handleImageSelected}
        onVoiceRecorded={jest.fn()}
      />
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['content'], 'outfit.jpg', { type: 'image/jpeg' });

    fireEvent.change(fileInput, { target: { files: [file] } });
    expect(handleImageSelected).toHaveBeenCalledWith(file);
  });

  test('handles voice toggle and starts 20s countdown when MediaRecorder is mocked', async () => {
    // Mock navigator.mediaDevices.getUserMedia
    const mockStream = {
      getTracks: jest.fn().mockReturnValue([{ stop: jest.fn() }]),
    };

    const mockRecorder = {
      start: jest.fn(),
      stop: jest.fn(),
      state: 'recording',
      mimeType: 'audio/webm',
      ondataavailable: null as any,
      onstop: null as any,
    };

    window.navigator.mediaDevices = {
      getUserMedia: jest.fn().mockResolvedValue(mockStream),
    } as any;

    (window as any).MediaRecorder = jest.fn().mockImplementation(() => mockRecorder);

    const handleVoiceRecorded = jest.fn();
    render(
      <SearchBar
        value=""
        onChange={jest.fn()}
        onSearch={jest.fn()}
        onImageSelected={jest.fn()}
        onVoiceRecorded={handleVoiceRecorded}
      />
    );

    const micBtn = screen.getByTitle(/Tìm bằng giọng nói/i);
    fireEvent.click(micBtn);

    await waitFor(() => {
      expect(screen.getByText(/Đang lắng nghe giọng nói của bạn/i)).toBeInTheDocument();
      expect(screen.getByText('20s')).toBeInTheDocument();
    });

    // Click again to stop
    fireEvent.click(micBtn);
    expect(mockRecorder.stop).toHaveBeenCalled();
  });
});
