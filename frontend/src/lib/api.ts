import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { AuthTokens } from '@/types/auth';

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now(),
      };
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle 401 errors (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (refreshToken) {
          const response = await axios.post<{ tokens: AuthTokens }>('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          });

          const { tokens } = response.data;
          
          // Update stored tokens
          localStorage.setItem('access_token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
          
          // Update default header
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`;
          
          // Retry original request
          if (originalRequest.headers) {
            originalRequest.headers['Authorization'] = `Bearer ${tokens.access_token}`;
          }
          
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        delete apiClient.defaults.headers.common['Authorization'];
        
        // Redirect to login page
        window.location.href = '/auth/login';
        return Promise.reject(refreshError);
      }
    }

    // Handle rate limiting
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const delay = retryAfter ? parseInt(retryAfter) * 1000 : 5000;
      
      // Show rate limit message
      console.warn(`Rate limited. Retrying after ${delay}ms`);
      
      // Retry after delay
      await new Promise(resolve => setTimeout(resolve, delay));
      return apiClient(originalRequest);
    }

    // Handle maintenance mode
    if (error.response?.status === 503) {
      // Show maintenance message
      console.warn('System is in maintenance mode');
    }

    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (credentials: { email: string; password: string; mfa_code?: string }) =>
    apiClient.post('/auth/login', credentials),
  
  register: (data: { email: string; password: string; full_name: string }) =>
    apiClient.post('/auth/register', data),
  
  logout: () =>
    apiClient.post('/auth/logout'),
  
  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  
  profile: () =>
    apiClient.get('/auth/profile'),
  
  updateProfile: (data: any) =>
    apiClient.put('/auth/profile', data),
};

export const tradingAPI = {
  getPortfolio: () =>
    apiClient.get('/trading/portfolio'),
  
  getPositions: () =>
    apiClient.get('/trading/positions'),
  
  executeTrade: (trade: any) =>
    apiClient.post('/trading/execute', trade),
  
  getTrades: (params?: any) =>
    apiClient.get('/trading/trades', { params }),
  
  getSystemStatus: () =>
    apiClient.get('/trading/system-status'),
  
  startAutonomous: (config: any) =>
    apiClient.post('/trading/autonomous/start', config),
  
  stopAutonomous: () =>
    apiClient.post('/trading/autonomous/stop'),
  
  getAutonomousStatus: () =>
    apiClient.get('/trading/autonomous/status'),
};

export const marketAPI = {
  getPrices: (symbols?: string[]) =>
    apiClient.get('/market/prices', { params: { symbols: symbols?.join(',') } }),
  
  getCandles: (symbol: string, interval: string, limit?: number) =>
    apiClient.get(`/market/candles/${symbol}`, { params: { interval, limit } }),
  
  getOrderbook: (symbol: string) =>
    apiClient.get(`/market/orderbook/${symbol}`),
  
  getTicker: (symbol: string) =>
    apiClient.get(`/market/ticker/${symbol}`),
};

export const exchangesAPI = {
  getConnected: () =>
    apiClient.get('/exchanges'),
  
  connect: (exchange: string, credentials: any) =>
    apiClient.post('/exchanges/connect', { exchange, ...credentials }),
  
  disconnect: (exchangeId: string) =>
    apiClient.delete(`/exchanges/${exchangeId}`),
  
  testConnection: (exchangeId: string) =>
    apiClient.post(`/exchanges/${exchangeId}/test`),
  
  getBalances: (exchangeId?: string) =>
    apiClient.get('/exchanges/balances', { params: { exchange_id: exchangeId } }),
};

export const adminAPI = {
  getUsers: (params?: any) =>
    apiClient.get('/admin/users', { params }),
  
  getSystemMetrics: () =>
    apiClient.get('/admin/system/metrics'),
  
  getSystemStatus: () =>
    apiClient.get('/admin/system/status'),
  
  configureSystem: (config: any) =>
    apiClient.post('/admin/system/configure', config),
  
  emergencyStop: (userId?: string) =>
    apiClient.post('/admin/emergency-stop', { user_id: userId }),
  
  getAuditLogs: (params?: any) =>
    apiClient.get('/admin/audit-logs', { params }),
};

// Utility functions
export const handleApiError = (error: AxiosError): string => {
  if (error.response?.data) {
    const data = error.response.data as any;
    return data.detail || data.message || 'An error occurred';
  }
  
  if (error.message) {
    return error.message;
  }
  
  return 'Network error occurred';
};

export const isApiError = (error: any): error is AxiosError => {
  return error.isAxiosError === true;
};

// WebSocket connection for real-time data
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(private url: string) {}

  connect(token?: string) {
    try {
      const wsUrl = this.url + (token ? `?token=${token}` : '');
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.reconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.reconnect();
    }
  }

  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      setTimeout(() => {
        console.log(`Reconnecting WebSocket (attempt ${this.reconnectAttempts})`);
        this.connect();
      }, delay);
    }
  }

  private handleMessage(data: any) {
    const { type, payload } = data;
    const listeners = this.listeners.get(type);
    
    if (listeners) {
      listeners.forEach(callback => callback(payload));
    }
  }

  subscribe(type: string, callback: (data: any) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    
    this.listeners.get(type)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(type);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          this.listeners.delete(type);
        }
      }
    };
  }

  send(type: string, payload: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }
}

// Create WebSocket manager instance
const getWebSocketUrl = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
  const baseUrl = apiUrl.replace('/api/v1', '').replace('http://', '').replace('https://', '');
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${baseUrl}/ws`;
};

export const wsManager = new WebSocketManager(getWebSocketUrl());

export default apiClient;
