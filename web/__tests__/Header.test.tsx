import React from 'react';
import { render, screen } from '@testing-library/react';
import { Header } from '@/components/Header';

describe('Header Component', () => {
  test('renders brand and navigation items', () => {
    render(<Header />);
    expect(screen.getByText('MIXI')).toBeInTheDocument();
    expect(screen.getByText('SEARCH')).toBeInTheDocument();
    expect(screen.getByText('Khám phá xu hướng')).toBeInTheDocument();
    expect(screen.getByText('Trợ giúp')).toBeInTheDocument();
    expect(screen.getByText('Tài khoản')).toBeInTheDocument();
  });
});
