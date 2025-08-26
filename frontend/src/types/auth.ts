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

export interface ResetPasswordRequest {
  email: string;
}

export interface ConfirmResetRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface EnableMFARequest {
  password: string;
}

export interface VerifyMFARequest {
  token: string;
  backup_code?: string;
}

export interface MFASetupResponse {
  qr_code: string;
  secret_key: string;
  backup_codes: string[];
}

export interface UserProfile {
  first_name?: string;
  last_name?: string;
  phone?: string;
  country?: string;
  timezone: string;
  language: string;
  avatar_url?: string;
  bio?: string;
  website?: string;
  notification_preferences: NotificationPreferences;
  trading_preferences: TradingPreferences;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  trade_notifications: boolean;
  security_alerts: boolean;
  market_updates: boolean;
  system_announcements: boolean;
}

export interface TradingPreferences {
  default_exchange: string;
  preferred_trading_pairs: string[];
  risk_tolerance: 'low' | 'medium' | 'high';
  auto_compound: boolean;
  stop_loss_default: number;
  take_profit_default: number;
  max_daily_loss: number;
  max_position_size: number;
}

export interface Session {
  id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_used: string;
  expires_at: string;
  is_current: boolean;
  location?: string;
  device_info?: string;
}

export interface LoginHistory {
  id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  success: boolean;
  failure_reason?: string;
  location?: string;
  created_at: string;
}

export interface SecurityEvent {
  id: string;
  user_id: string;
  event_type: SecurityEventType;
  description: string;
  ip_address: string;
  user_agent: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  resolved: boolean;
}

export enum SecurityEventType {
  LOGIN_FAILURE = 'login_failure',
  PASSWORD_CHANGE = 'password_change',
  MFA_ENABLED = 'mfa_enabled',
  MFA_DISABLED = 'mfa_disabled',
  API_KEY_CREATED = 'api_key_created',
  API_KEY_DELETED = 'api_key_deleted',
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  ACCOUNT_LOCKED = 'account_locked',
  ACCOUNT_UNLOCKED = 'account_unlocked'
}