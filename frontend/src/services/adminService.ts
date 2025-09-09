import axios from 'axios';
import { getAuthToken } from './authService';

// Debug flag - only enable in dev mode or when explicitly enabled
const DEBUG_HTTP = import.meta.env.DEV || import.meta.env.VITE_DEBUG_HTTP === 'true';

// Create axios instance with auth interceptor
const adminApi = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/admin`,
});

// Add auth token to requests
adminApi.interceptors.request.use((config) => {
  // Set start time for duration tracking
  config.metadata = { startTime: Date.now() };
  
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Only log in debug mode, and sanitize output
  if (DEBUG_HTTP) {
    console.debug('Admin API Request:', {
      method: config.method?.toUpperCase(),
      url: config.url,
      hasAuth: !!token,
      // Never log the actual token or headers
    });
  }
  
  return config;
}, (error) => {
  // Sanitized error logging
  if (DEBUG_HTTP) {
    console.debug('Admin API Request Error:', {
      message: error.message,
      // Don't log config or headers
    });
  }
  return Promise.reject(error);
});

// Add response interceptor for debugging
adminApi.interceptors.response.use((response) => {
  // Only log minimal metadata in debug mode
  if (DEBUG_HTTP) {
    const duration = Date.now() - (response.config.metadata?.startTime || Date.now());
    console.debug('Admin API Response:', {
      method: response.config.method?.toUpperCase(),
      url: response.config.url,
      status: response.status,
      duration: `${duration}ms`,
      requestId: response.headers['x-request-id'],
      // Never log response data which may contain PII
    });
  }
  return response;
}, (error) => {
  // Sanitized error logging
  if (DEBUG_HTTP) {
    const duration = Date.now() - (error.config?.metadata?.startTime || Date.now());
    console.debug('Admin API Error:', {
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      duration: `${duration}ms`,
      // Never log response.data which may contain sensitive error details
    });
  }
  return Promise.reject(error);
});

// User Management
export const adminService = {
  // Get all users with filters
  async getUsers(params?: {
    skip?: number;
    limit?: number;
    status_filter?: string;
    role_filter?: string;
    search?: string;
  }) {
    const response = await adminApi.get('/users', { params });
    return response.data;
  },

  // Get pending verification users
  async getPendingUsers() {
    const response = await adminApi.get('/users/pending-verification');
    return response.data;
  },

  // Verify a single user
  async verifyUser(userId: string) {
    const response = await adminApi.post(`/users/verify/${userId}`);
    return response.data;
  },

  // Verify multiple users
  async verifyUsersBatch(userIds: string[], reason?: string) {
    const response = await adminApi.post('/users/verify-batch', {
      user_ids: userIds,
      reason,
    });
    return response.data;
  },

  // Manage user (activate, deactivate, suspend, etc.)
  async manageUser(userId: string, action: string, reason?: string, creditAmount?: number) {
    const response = await adminApi.post('/users/manage', {
      user_id: userId,
      action,
      reason,
      credit_amount: creditAmount,
    });
    return response.data;
  },

  // System Metrics
  async getSystemStatus() {
    const response = await adminApi.get('/system/status');
    return response.data;
  },

  async getMetrics() {
    const response = await adminApi.get('/metrics');
    return response.data;
  },

  // Audit Logs
  async getAuditLogs(params?: {
    skip?: number;
    limit?: number;
    user_id?: string;
    action_filter?: string;
    start_date?: string;
    end_date?: string;
  }) {
    const response = await adminApi.get('/audit-logs', { params });
    return response.data;
  },

  // Emergency Controls
  async emergencyStopAll(reason: string) {
    const response = await adminApi.post('/emergency/stop-all', null, {
      params: { reason },
    });
    return response.data;
  },

  // System Configuration
  async configureSystem(config: any) {
    const response = await adminApi.post('/system/configure', config);
    return response.data;
  },
};

export default adminService;