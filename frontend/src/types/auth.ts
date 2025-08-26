export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  is_verified: boolean;
  mfa_enabled: boolean;
  last_login?: string;
  created_at: string;
  simulation_mode: boolean;
  avatar_url?: string;
}

export enum UserRole {
  ADMIN = 'admin',
  TRADER = 'trader',
  VIEWER = 'viewer',
  API_ONLY = 'api_only'
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING_VERIFICATION = 'pending_verification'
}

export interface LoginRequest {
  email: string;
  password: string;
  mfa_code?: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  terms_accepted: boolean;
  privacy_accepted: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  tokens?: AuthTokens;
  message?: string;
  mfa_required?: boolean;
  error?: string;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  mfaRequired: boolean;
}