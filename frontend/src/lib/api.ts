import axios from 'axios';
import { apiClient } from '@/lib/api/client';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.PROD 
    ? 'https://cryptouniverse.onrender.com/api/v1'
    : 'http://localhost:8000/api/v1'
);

// Auth interceptor function (same as in client.ts)
const authInterceptor = (config: any) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

// Response interceptor function (same as in client.ts)
const setupResponseInterceptor = (instance: any) => {
  instance.interceptors.response.use(
    (response: any) => response,
    async (error: any) => {
      if (error.response?.status === 401 && error.response?.data?.detail === 'Token has expired') {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken
            });
            
            const { access_token, refresh_token: newRefreshToken } = response.data;
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', newRefreshToken);
            
            // Retry the original request
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return axios.request(error.config);
          } catch (refreshError) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
          }
        }
      }
      return Promise.reject(error);
    }
  );
};

// Create specialized API instances
export const tradingAPI = axios.create({
  baseURL: `${API_BASE_URL}/trading`,
  timeout: 30000,
});

export const exchangesAPI = axios.create({
  baseURL: `${API_BASE_URL}/exchanges`,
  timeout: 30000,
});

// Add interceptors to specialized instances
[tradingAPI, exchangesAPI].forEach(instance => {
  instance.interceptors.request.use(authInterceptor);
  setupResponseInterceptor(instance);
});

// Export the main client as default
export default apiClient;