import React from 'react';
import { render, screen } from '@testing-library/react';
import { Header } from '@/components/Header';

describe('Header Component', () => {
  test('renders brand title and default status text', () => {
    render(<Header />);
    expect(screen.getByText(/Atelier Search/i)).toBeInTheDocument();
    expect(screen.getByText(/AI Multimodal/i)).toBeInTheDocument();
    expect(screen.getByText(/H&M Fashion Engine/i)).toBeInTheDocument();
  });

  test('renders custom status and offline indicator', () => {
    render(<Header statusText="Offline Mode" isOnline={false} />);
    expect(screen.getByText('Offline Mode')).toBeInTheDocument();
  });
});
