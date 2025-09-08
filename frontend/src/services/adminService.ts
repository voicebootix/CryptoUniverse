import axios from 'axios';
import { getAuthToken } from './authService';

// Create axios instance with auth interceptor
const adminApi = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/admin`,
});

// Add auth token to requests
adminApi.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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