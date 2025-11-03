import { apiClient } from '@/lib/api/client';

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
    const response = await apiClient.get('/admin/users', { params });
    return response.data;
  },

  // Get pending verification users
  async getPendingUsers() {
    const response = await apiClient.get('/admin/users/pending-verification');
    return response.data;
  },

  // Verify a single user
  async verifyUser(userId: string) {
    const response = await apiClient.post(`/admin/users/verify/${userId}`);
    return response.data;
  },

  // Verify multiple users
  async verifyUsersBatch(userIds: string[], reason?: string) {
    const response = await apiClient.post('/admin/users/verify-batch', {
      user_ids: userIds,
      reason,
    });
    return response.data;
  },

  // Manage user (activate, deactivate, suspend, etc.)
  async manageUser(userId: string, action: string, reason?: string, creditAmount?: number) {
    const response = await apiClient.post('/admin/users/manage', {
      user_id: userId,
      action,
      reason,
      credit_amount: creditAmount,
    });
    return response.data;
  },

  // System Metrics
  async getSystemStatus() {
    const response = await apiClient.get('/admin/system/status');
    return response.data;
  },

  async getMetrics() {
    const response = await apiClient.get('/admin/metrics');
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
    const response = await apiClient.get('/admin/audit-logs', { params });
    return response.data;
  },

  // Emergency Controls
  async emergencyStopAll(reason: string) {
    const response = await apiClient.post('/admin/emergency/stop-all', null, {
      params: { reason },
    });
    return response.data;
  },

  // System Configuration
  async configureSystem(config: any) {
    const response = await apiClient.post('/admin/system/configure', config);
    return response.data;
  },

  async getOpportunityPolicies() {
    const response = await apiClient.get('/admin/opportunity-policies');
    return response.data;
  },

  async updateOpportunityPolicy(
    strategyKey: string,
    payload: {
      max_symbols?: number | null;
      chunk_size?: number | null;
      priority?: number | null;
      enabled?: boolean;
    },
  ) {
    const response = await apiClient.put(
      `/admin/opportunity-policies/${encodeURIComponent(strategyKey)}`,
      payload,
    );
    return response.data;
  },

  async resetOpportunityPolicy(strategyKey: string) {
    const response = await apiClient.delete(
      `/admin/opportunity-policies/${encodeURIComponent(strategyKey)}`,
    );
    return response.data;
  },
};

export default adminService;
