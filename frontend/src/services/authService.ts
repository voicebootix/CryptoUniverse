/**
 * Authentication service for managing tokens and auth state
 */

const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  role: string;
}

/**
 * Get stored auth token
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.debug('Failed to read auth token from localStorage:', error);
    return null;
  }
}

/**
 * Get stored refresh token
 */
export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    // SECURITY: Refresh tokens are ONLY stored in sessionStorage
    return sessionStorage.getItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.debug('Failed to read refresh token from sessionStorage:', error);
    return null;
  }
}

/**
 * Store authentication tokens
 */
export function setAuthTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  
  try {
    // Store access token in localStorage for persistence across sessions
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
  } catch (error) {
    console.debug('Failed to store access token in localStorage:', error);
  }
  
  try {
    // Store refresh token ONLY in sessionStorage for security
    sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  } catch (error) {
    console.debug('Failed to store refresh token in sessionStorage:', error);
    // SECURITY: Never fallback to localStorage for refresh tokens
    // Clear any partial auth state and trigger re-authentication
    try {
      localStorage.removeItem(TOKEN_KEY); // Clear access token too
    } catch (clearError) {
      console.debug('Failed to clear access token after sessionStorage failure:', clearError);
    }
    
    // Throw error to trigger re-auth flow
    throw new Error('Unable to securely store refresh token. Please log in again.');
  }
}

/**
 * Clear all authentication data
 */
export function clearAuthTokens(): void {
  if (typeof window === 'undefined') return;
  
  // Clear from localStorage
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  } catch (error) {
    console.debug('Failed to clear tokens from localStorage:', error);
  }
  
  // Clear from sessionStorage
  try {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  } catch (error) {
    console.debug('Failed to clear tokens from sessionStorage:', error);
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

export default {
  getAuthToken,
  getRefreshToken,
  setAuthTokens,
  clearAuthTokens,
  isAuthenticated,
};