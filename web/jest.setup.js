import '@testing-library/jest-dom';

// Polyfill window.alert, URL.createObjectURL, URL.revokeObjectURL for jsdom environment
if (typeof window !== 'undefined') {
  window.alert = jest.fn();
  window.URL.createObjectURL = jest.fn(() => 'blob:mock-preview-url');
  window.URL.revokeObjectURL = jest.fn();
}
