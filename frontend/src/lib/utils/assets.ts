/**
 * Asset utilities for handling public assets
 */

/**
 * Get the full URL for a public asset
 */
export const getPublicAssetUrl = (path: string): string => {
  const baseUrl = import.meta.env.VITE_PUBLIC_URL || '';
  return `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
};
