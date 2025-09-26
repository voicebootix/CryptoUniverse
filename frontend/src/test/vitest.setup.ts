import '@testing-library/jest-dom';

// Provide a minimal ResizeObserver implementation for components using it in tests
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined' && !('ResizeObserver' in window)) {
  // @ts-expect-error - assign to window for test environment
  window.ResizeObserver = MockResizeObserver;
}

if (typeof window !== 'undefined' && typeof window.HTMLElement !== 'undefined') {
  if (typeof window.HTMLElement.prototype.scrollIntoView !== 'function') {
    window.HTMLElement.prototype.scrollIntoView = () => {};
  }
}
