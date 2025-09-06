import axios, { AxiosInstance, AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { useAuthStore } from '@/store/authStore';

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
  timeout: 120000, // 2 minutes default timeout for Render cold starts
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    // Skip auth for certain endpoints
    const skipAuthEndpoints = [
      '/auth/login',
      '/auth/register',
      '/auth/forgot-password',
      '/auth/reset-password',
      '/auth/verify-email'
    ];

    const shouldSkipAuth = skipAuthEndpoints.some(endpoint => 
      config.url?.includes(endpoint)
    );

    if (!shouldSkipAuth) {
      const token = useAuthStore.getState().tokens?.access_token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    // Add request timestamp for debugging
    config.metadata = { startTime: new Date() };
    
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
        const duration = new Date().getTime() - startTime.getTime();
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
            
            // Try to refresh token
            try {
              const { useAuthStore } = await import('@/store/authStore');
              await useAuthStore.getState().refreshToken();
              
              // Retry original request with new token
              const token = useAuthStore.getState().tokens?.access_token;
              if (token) {
                originalRequest.headers = {
                  ...originalRequest.headers,
                  Authorization: `Bearer ${token}`
                };
                return apiClient(originalRequest);
              }
            } catch (refreshError) {
              // Refresh failed, logout user
              const { useAuthStore } = await import('@/store/authStore');
              useAuthStore.getState().logout();
              
              // Redirect to login if in browser
              if (typeof window !== 'undefined') {
                window.location.href = '/login';
              }
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
    (config) => {
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
          const authStore = useAuthStore.getState();
          await authStore.refreshToken();
          const newToken = authStore.tokens?.access_token;
          
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return instance(originalRequest);
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
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

// Declare module augmentation for metadata
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}
