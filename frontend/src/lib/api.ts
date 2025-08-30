import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { AuthTokens } from '@/types/auth';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.PROD 
    ? 'https://cryptouniverse.onrender.com/api/v1'  // Production backend URL
    : 'http://localhost:8000/api/v1'  // Local development
);

// Create base axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
const authInterceptor = (config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

// Response interceptor
const setupResponseInterceptor = (instance: AxiosInstance) => {
  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            const response = await axios.post<{ tokens: AuthTokens }>(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            });
            const { tokens } = response.data;
            localStorage.setItem('access_token', tokens.access_token);
            localStorage.setItem('refresh_token', tokens.refresh_token);
            
            const { useAuthStore } = await import('@/store/authStore');
            useAuthStore.getState().setTokens(tokens);

            instance.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`;
            if (originalRequest.headers) {
              originalRequest.headers['Authorization'] = `Bearer ${tokens.access_token}`;
            }
            return instance(originalRequest);
          }
        } catch (refreshError) {
          // Handle failed refresh
        }
      }
      return Promise.reject(error);
    }
  );
};

// Apply interceptors
apiClient.interceptors.request.use(authInterceptor);
setupResponseInterceptor(apiClient);

export const tradingAPI = axios.create({
  baseURL: `${API_BASE_URL}/trading`,
});
tradingAPI.interceptors.request.use(authInterceptor);
setupResponseInterceptor(tradingAPI);

export const exchangesAPI = axios.create({
  baseURL: `${API_BASE_URL}/exchanges`,
});
exchangesAPI.interceptors.request.use(authInterceptor);
setupResponseInterceptor(exchangesAPI);

export {
  apiClient,
  tradingAPI,
  exchangesAPI,
  authAPI,
  marketAPI,
  wsManager,
};
