import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProductCard } from '@/components/ProductCard';
import { ProductGrid } from '@/components/ProductGrid';
import { SearchResultItem } from '@/types/search';

const mockProduct: SearchResultItem = {
  article_id: '0108775015',
  prod_name: 'Strap top',
  price_vnd: 299000,
  gender: 'Ladieswear',
  color_code: '10',
  color_name: 'White',
  category_group: 'Garment Upper body',
  category_sub: 'Top',
  image_path: '010/0108775015.jpg',
  detail_desc: 'Jersey top with narrow shoulder straps.',
  visual_similarity: 0.92,
  final_score: 0.88,
  explanation_badges: ['92% tương đồng ảnh', '✓ Màu White'],
};

describe('ProductCard Component', () => {
  test('renders product name, color, and formatted VND price', () => {
    render(
      <ProductCard item={mockProduct} onFindSimilar={jest.fn()} />
    );

    expect(screen.getByText('Strap top')).toBeInTheDocument();
    expect(screen.getByText(/White • Garment Upper body/i)).toBeInTheDocument();
    expect(screen.getByText('299.000 ₫')).toBeInTheDocument();
  });

  test('calls onFindSimilar when hover button is clicked', () => {
    const handleFindSimilar = jest.fn();
    render(
      <ProductCard item={mockProduct} onFindSimilar={handleFindSimilar} />
    );

    const similarBtn = screen.getByText('Tìm tương tự');
    fireEvent.click(similarBtn);

    expect(handleFindSimilar).toHaveBeenCalledTimes(1);
    expect(handleFindSimilar).toHaveBeenCalledWith('0108775015', 'Strap top');
  });

  test('calls onClick when card container is clicked', () => {
    const handleClick = jest.fn();
    render(
      <ProductCard
        item={mockProduct}
        onFindSimilar={jest.fn()}
        onClick={handleClick}
      />
    );

    fireEvent.click(screen.getByText('Strap top'));
    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(mockProduct);
  });

  test('shows image similarity only for image-ranked results', () => {
    const { rerender } = render(
      <ProductCard item={mockProduct} onFindSimilar={jest.fn()} />
    );

    expect(screen.queryByText('92% khớp ảnh')).not.toBeInTheDocument();

    rerender(
      <ProductCard
        item={mockProduct}
        onFindSimilar={jest.fn()}
        showImageSimilarity={true}
      />
    );

    expect(screen.getByText('92% khớp ảnh')).toBeInTheDocument();
  });
});

describe('ProductGrid Component', () => {
  test('renders loading skeleton when isLoading is true', () => {
    const { container } = render(
      <ProductGrid items={[]} isLoading={true} onFindSimilar={jest.fn()} />
    );
    expect(container.getElementsByClassName('animate-pulse').length).toBeGreaterThan(0);
  });

  test('renders empty state when items array is empty and not loading', () => {
    render(
      <ProductGrid items={[]} isLoading={false} onFindSimilar={jest.fn()} />
    );
    expect(screen.getByText('Không tìm thấy sản phẩm phù hợp')).toBeInTheDocument();
  });

  test('renders assistant response without a product empty-state message', () => {
    render(
      <ProductGrid
        items={[]}
        responseType="conversation"
        message="Xin chào! Tôi có thể giúp bạn tìm sản phẩm thời trang."
        onFindSimilar={jest.fn()}
      />
    );

    expect(screen.getByText('Trợ lý tìm kiếm thời trang')).toBeInTheDocument();
    expect(screen.getByText(/Xin chào!/i)).toBeInTheDocument();
    expect(screen.queryByText('Không tìm thấy sản phẩm phù hợp')).not.toBeInTheDocument();
  });

  test('renders product cards when items are provided', () => {
    render(
      <ProductGrid
        items={[mockProduct]}
        isLoading={false}
        onFindSimilar={jest.fn()}
      />
    );
    expect(screen.getByText('Strap top')).toBeInTheDocument();
  });
});
