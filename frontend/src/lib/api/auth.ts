import { 
  LoginRequest, 
  RegisterRequest, 
  AuthResponse, 
  User,
  ResetPasswordRequest,
  ConfirmResetRequest,
  ChangePasswordRequest,
  EnableMFARequest,
  VerifyMFARequest,
  MFASetupResponse,
  Session,
  LoginHistory,
  SecurityEvent
} from '@/types/auth';
import { apiClient } from './client';

export const authApi = {
  // Authentication
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/login', credentials);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/register', data);
    return response.data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },

  async refreshToken(refresh_token: string): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/refresh', { refresh_token });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  async verifyEmail(token: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/verify-email', { token });
    return response.data;
  },

  async resendVerification(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/resend-verification');
    return response.data;
  },

  // Password Management
  async requestPasswordReset(data: ResetPasswordRequest): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/forgot-password', data);
    return response.data;
  },

  async confirmPasswordReset(data: ConfirmResetRequest): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/reset-password', data);
    return response.data;
  },

  async changePassword(data: ChangePasswordRequest): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/change-password', data);
    return response.data;
  },

  // Multi-Factor Authentication
  async setupMFA(data: EnableMFARequest): Promise<MFASetupResponse> {
    const response = await apiClient.post('/auth/mfa/setup', data);
    return response.data;
  },

  async enableMFA(data: VerifyMFARequest): Promise<{ success: boolean; backup_codes: string[] }> {
    const response = await apiClient.post('/auth/mfa/enable', data);
    return response.data;
  },

  async disableMFA(data: VerifyMFARequest): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/mfa/disable', data);
    return response.data;
  },

  async verifyMFA(data: VerifyMFARequest): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/mfa/verify', data);
    return response.data;
  },

  async generateBackupCodes(): Promise<{ backup_codes: string[] }> {
    const response = await apiClient.post('/auth/mfa/backup-codes');
    return response.data;
  },

  // Session Management
  async getSessions(): Promise<Session[]> {
    const response = await apiClient.get('/auth/sessions');
    return response.data;
  },

  async revokeSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/auth/sessions/${sessionId}`);
    return response.data;
  },

  async revokeAllSessions(): Promise<{ success: boolean; message: string; revoked_count: number }> {
    const response = await apiClient.delete('/auth/sessions');
    return response.data;
  },

  // Security & Audit
  async getLoginHistory(limit?: number): Promise<LoginHistory[]> {
    const response = await apiClient.get('/auth/login-history', {
      params: { limit }
    });
    return response.data;
  },

  async getSecurityEvents(): Promise<SecurityEvent[]> {
    const response = await apiClient.get('/auth/security-events');
    return response.data;
  },

  async checkCompromisedPassword(password: string): Promise<{ is_compromised: boolean; breach_count: number }> {
    const response = await apiClient.post('/auth/check-password', { password });
    return response.data;
  },

  // Account Management
  async updateProfile(profile: Partial<User>): Promise<User> {
    const response = await apiClient.patch('/auth/profile', profile);
    return response.data;
  },

  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const formData = new FormData();
    formData.append('avatar', file);
    
    const response = await apiClient.post('/auth/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async deleteAccount(password: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete('/auth/account', {
      data: { password }
    });
    return response.data;
  },

  // API Keys (for programmatic access)
  async getApiKeys(): Promise<Array<{
    id: string;
    name: string;
    key_preview: string;
    permissions: string[];
    last_used?: string;
    created_at: string;
    expires_at?: string;
  }>> {
    const response = await apiClient.get('/auth/api-keys');
    return response.data;
  },

  async createApiKey(data: {
    name: string;
    permissions: string[];
    expires_at?: string;
  }): Promise<{
    id: string;
    name: string;
    api_key: string;
    permissions: string[];
    expires_at?: string;
  }> {
    const response = await apiClient.post('/auth/api-keys', data);
    return response.data;
  },

  async revokeApiKey(keyId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/auth/api-keys/${keyId}`);
    return response.data;
  },

  // Admin functions (requires admin role)
  async getAllUsers(params?: {
    page?: number;
    limit?: number;
    search?: string;
    role?: string;
    status?: string;
  }): Promise<{
    users: User[];
    total: number;
    page: number;
    limit: number;
  }> {
    const response = await apiClient.get('/auth/admin/users', { params });
    return response.data;
  },

  async updateUserStatus(userId: string, status: string): Promise<User> {
    const response = await apiClient.patch(`/auth/admin/users/${userId}/status`, { status });
    return response.data;
  },

  async updateUserRole(userId: string, role: string): Promise<User> {
    const response = await apiClient.patch(`/auth/admin/users/${userId}/role`, { role });
    return response.data;
  },

  async lockUser(userId: string, reason: string, duration?: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/auth/admin/users/${userId}/lock`, { reason, duration });
    return response.data;
  },

  async unlockUser(userId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/auth/admin/users/${userId}/unlock`);
    return response.data;
  },

  async impersonateUser(userId: string): Promise<AuthResponse> {
    const response = await apiClient.post(`/auth/admin/users/${userId}/impersonate`);
    return response.data;
  },

  async stopImpersonation(): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/admin/stop-impersonate');
    return response.data;
  }
};
