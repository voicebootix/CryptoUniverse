import axios, { AxiosInstance, AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
// Note: useAuthStore imported dynamically to avoid circular dependency

// API configuration
// In production, always use the backend URL, not relative paths
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (window.location.hostname === 'cryptouniverse-frontend.onrender.com' 
    ? 'https://cryptouniverse.onrender.com/api/v1'
    : '/api/v1');  // Use backend URL in production, relative in dev

// Log the API URL being used (for debugging)
console.log('API Base URL:', API_BASE_URL);

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3 minutes default timeout for Render cold starts
  headers: {
    'Content-Type': 'application/json',
  },
});

// Note: Using globalThis.__authRefreshPromise for deduplication instead of module-level promise
// This ensures consistent deduplication across the entire app

// Request interceptor to add auth token with expiry checking
apiClient.interceptors.request.use(
  async (config) => {
    // Skip auth for certain endpoints
    const skipAuthEndpoints = [
      '/auth/login',
      '/auth/register',
      '/auth/forgot-password',
      '/auth/reset-password',
      '/auth/verify-email',
      '/auth/refresh',
      '/auth/logout',
      '/auth/oauth',
      '/auth/oauth/url',
      '/auth/oauth/callback'
    ];

    const shouldSkipAuth = skipAuthEndpoints.some(endpoint => 
      config.url?.includes(endpoint)
    );

    if (!shouldSkipAuth) {
      // Use dynamic import to avoid circular dependency
      const { useAuthStore } = await import('@/store/authStore');
      const { tokens, refreshToken, logout } = useAuthStore.getState();
      
      if (!tokens?.access_token) {
        console.log('No access token available');
        // Don't call logout() here to avoid recursive calls - let higher level handle
        throw new Error('Authentication required');
      }
      
      // Check if token is expired or expiring soon
      if (tokens?.expires_in) {
        const now = Math.floor(Date.now() / 1000);
        const expirationTime = tokens.expires_in; // Now always a timestamp
        const timeUntilExpiry = expirationTime - now;
        
        // If token expires in less than 30 seconds, try to refresh it
        if (timeUntilExpiry <= 30) {
          console.log('Token expiring soon, attempting refresh before request...');
          
          try {
            // Use global deduplication mechanism
            if (globalThis.__authRefreshPromise) {
              console.log('Refresh already in progress, awaiting...');
              await globalThis.__authRefreshPromise;
            } else {
              console.log('Starting new refresh from request interceptor...');
              await refreshToken();
            }
            
            // Get fresh tokens after refresh
            const freshTokens = useAuthStore.getState().tokens;
            if (freshTokens?.access_token) {
              config.headers.Authorization = `Bearer ${freshTokens.access_token}`;
            } else {
              throw new Error('No fresh token after refresh');
            }
          } catch (refreshError) {
            console.error('Pre-request token refresh failed:', refreshError);
            logout();
            throw new Error('Session expired. Please login again.');
          }
        } else {
          config.headers.Authorization = `Bearer ${tokens.access_token}`;
        }
      } else {
        config.headers.Authorization = `Bearer ${tokens.access_token}`;
      }
    }

    // Add request timestamp for debugging
    config.metadata = { ...(config.metadata || {}), startTime: Date.now() };
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log response time in development
    if (import.meta.env.DEV) {
      const startTime = response.config.metadata?.startTime;
      if (startTime) {
        const duration = Date.now() - startTime;
        // API request timing logged internally
      }
    }
    
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Unauthorized - token expired or invalid
          if (!originalRequest._retry) {
            originalRequest._retry = true;
            
            console.log('401 Unauthorized - attempting token refresh...');
            
            // Try to refresh token with deduplication
            try {
              const { useAuthStore } = await import('@/store/authStore');
              const authStore = useAuthStore.getState();
              
              // Check if we have a refresh token
              if (!authStore.tokens?.refresh_token) {
                console.log('No refresh token available, logging out...');
                authStore.logout();
                if (typeof window !== 'undefined') {
                  window.location.href = '/login';
                }
                return Promise.reject(new Error('Session expired. Please login again.'));
              }
              
              // Use the same global deduplication as everywhere else
              if (globalThis.__authRefreshPromise) {
                console.log('Refresh already in progress, awaiting...');
                await globalThis.__authRefreshPromise;
              } else {
                console.log('Starting new refresh from response interceptor...');
                await authStore.refreshToken();
              }
              
              // Retry original request with new token
              const newTokens = authStore.tokens;
              if (newTokens?.access_token) {
                originalRequest.headers = {
                  ...originalRequest.headers,
                  Authorization: `Bearer ${newTokens.access_token}`
                };
                console.log('Token refreshed successfully, retrying original request...');
                return apiClient(originalRequest);
              } else {
                throw new Error('Token refresh succeeded but no new token received');
              }
            } catch (refreshError) {
              // Refresh failed, logout user
              console.error('Token refresh failed in response interceptor:', refreshError);
              const { useAuthStore } = await import('@/store/authStore');
              useAuthStore.getState().logout();
              
              // Redirect to login if in browser
              if (typeof window !== 'undefined') {
                window.location.href = '/login';
              }
              
              return Promise.reject(new Error('Session expired. Please login again.'));
            }
          } else {
            // Already tried refresh, force logout
            console.log('Token refresh already attempted, forcing logout...');
            const { useAuthStore } = await import('@/store/authStore');
            useAuthStore.getState().logout();
            
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }
          break;

        case 403:
          // Forbidden - insufficient permissions
          console.error('Insufficient permissions:', data);
          break;

        case 429:
          // Rate limited
          const retryAfter = error.response.headers['retry-after'];
          if (retryAfter && !originalRequest._retry) {
            originalRequest._retry = true;
            
            // Wait and retry
            await new Promise(resolve => setTimeout(resolve, parseInt(retryAfter) * 1000));
            return apiClient(originalRequest);
          }
          break;

        case 500:
        case 502:
        case 503:
        case 504:
          // Server errors - could implement retry logic
          console.error('Server error:', status, data);
          break;

        default:
          console.error('API error:', status, data);
      }

      // Enhance error with more context
      const enhancedError = new Error(
        (data as any)?.message || 
        (data as any)?.error || 
        `API Error: ${status}`
      );
      
      enhancedError.name = 'APIError';
      (enhancedError as any).status = status;
      (enhancedError as any).data = data;
      
      return Promise.reject(enhancedError);
    }

    // Network errors
    if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      const networkError = new Error('Network error. Please check your connection.');
      networkError.name = 'NetworkError';
      return Promise.reject(networkError);
    }

    // Timeout errors
    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout detected:', error.config?.url);
      const timeoutError: any = new Error('Request timeout: Server is starting up. This may take up to 2 minutes on first request. Please wait and try again.');
      timeoutError.name = 'TimeoutError';
      timeoutError.code = 'ECONNABORTED'; // Preserve original error code
      timeoutError.isTimeout = true; // Add timeout flag for reliable detection
      return Promise.reject(timeoutError);
    }

    // Default error
    return Promise.reject(error);
  }
);

// Utility functions for common API operations
export const apiUtils = {
  // Generic GET with pagination
  async getPaginated<T>(
    endpoint: string, 
    params?: Record<string, any>
  ): Promise<{
    data: T[];
    total: number;
    page: number;
    limit: number;
    has_next: boolean;
    has_prev: boolean;
  }> {
    const response = await apiClient.get(endpoint, { params });
    return response.data;
  },

  // File upload
  async uploadFile(
    endpoint: string, 
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(Math.round(progress));
        }
      },
    });

    return response.data;
  },

  // Download file
  async downloadFile(endpoint: string, filename?: string): Promise<void> {
    const response = await apiClient.get(endpoint, {
      responseType: 'blob',
    });

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || 'download');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Batch requests
  async batch<T>(requests: Array<() => Promise<T>>): Promise<T[]> {
    return Promise.all(requests.map(request => request()));
  },

  // Retry mechanism
  async retry<T>(
    operation: () => Promise<T>,
    maxAttempts: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt === maxAttempts) {
          throw lastError;
        }
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, delay * attempt));
      }
    }
    
    throw lastError!;
  }
};

// Health check function
export const healthCheck = async (): Promise<{
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version?: string;
  uptime?: number;
}> => {
  try {
    const response = await axios.get(`${API_BASE_URL.replace('/api/v1', '')}/health`, {
      timeout: 5000
    });
    return {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      ...response.data
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      timestamp: new Date().toISOString()
    };
  }
};

// Create specialized API instances using the same auth system
export const tradingAPI = axios.create({
  baseURL: `${API_BASE_URL}/trading`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const exchangesAPI = axios.create({
  baseURL: `${API_BASE_URL}/exchanges`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Apply the same interceptors to specialized instances
[tradingAPI, exchangesAPI].forEach(instance => {
  // Add auth interceptor (same as apiClient)
  instance.interceptors.request.use(
    async (config) => {
      const { useAuthStore } = await import('@/store/authStore');
      const authStore = useAuthStore.getState();
      const token = authStore.tokens?.access_token;
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );
  
  // Add response interceptor (same as apiClient)
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        
        try {
          const { useAuthStore } = await import('@/store/authStore');
          const authStore = useAuthStore.getState();
          await authStore.refreshToken();
          const newToken = authStore.tokens?.access_token;
          
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return instance(originalRequest);
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          const { useAuthStore } = await import('@/store/authStore');
          const authStore = useAuthStore.getState();
          authStore.logout();
          window.location.href = '/login';
        }
      }
      
      return Promise.reject(error);
    }
  );
});

// Export types for use in other files
export type APIError = {
  message: string;
  status: number;
  data?: any;
};

// Module augmentation moved to src/types/axios.d.ts
