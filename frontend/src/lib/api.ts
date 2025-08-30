import axios from 'axios';
import { apiClient } from '@/lib/api/client';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.PROD 
    ? 'https://cryptouniverse.onrender.com/api/v1'
    : 'http://localhost:8000/api/v1'
);

// Create specialized API instances that use the same interceptors as the main client
export const tradingAPI = axios.create({
  baseURL: `${API_BASE_URL}/trading`,
  timeout: 30000,
});

export const exchangesAPI = axios.create({
  baseURL: `${API_BASE_URL}/exchanges`,
  timeout: 30000,
});

// Copy interceptors from main client to specialized instances
[tradingAPI, exchangesAPI].forEach(instance => {
  // Copy request interceptors
  apiClient.interceptors.request.handlers.forEach(handler => {
    if (handler.fulfilled) {
      instance.interceptors.request.use(handler.fulfilled, handler.rejected);
    }
  });

  // Copy response interceptors
  apiClient.interceptors.response.handlers.forEach(handler => {
    if (handler.fulfilled) {
      instance.interceptors.response.use(handler.fulfilled, handler.rejected);
    }
  });
});

// Export the main client as default
export default apiClient;