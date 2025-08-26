import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthTokens, LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth';
import { apiClient } from '@/lib/api';

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  mfaRequired: boolean;
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  clearError: () => void;
  setUser: (user: User) => void;
  setTokens: (tokens: AuthTokens) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      mfaRequired: false,

      // Actions
      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null, mfaRequired: false });

        try {
          const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
          
          if (response.data.mfa_required) {
            set({ 
              isLoading: false, 
              mfaRequired: true,
              error: null 
            });
            return;
          }

          if (response.data.success && response.data.user && response.data.tokens) {
            set({
              user: response.data.user,
              tokens: response.data.tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
              mfaRequired: false,
            });

            // Set authorization header for future requests
            apiClient.defaults.headers.common['Authorization'] = 
              `Bearer ${response.data.tokens.access_token}`;
          } else {
            throw new Error(response.data.message || 'Login failed');
          }
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || 
                              error.response?.data?.message || 
                              error.message || 
                              'Login failed';
          
          set({
            isLoading: false,
            error: errorMessage,
            mfaRequired: false,
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });

        try {
          const response = await apiClient.post<AuthResponse>('/auth/register', data);
          
          if (response.data.success && response.data.user && response.data.tokens) {
            set({
              user: response.data.user,
              tokens: response.data.tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            // Set authorization header for future requests
            apiClient.defaults.headers.common['Authorization'] = 
              `Bearer ${response.data.tokens.access_token}`;
          } else {
            throw new Error(response.data.message || 'Registration failed');
          }
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || 
                              error.response?.data?.message || 
                              error.message || 
                              'Registration failed';
          
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      logout: () => {
        // Clear authorization header
        delete apiClient.defaults.headers.common['Authorization'];
        
        // Clear state
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
          mfaRequired: false,
        });

        // Optionally call logout endpoint
        apiClient.post('/auth/logout').catch(() => {
          // Ignore errors on logout
        });
      },

      refreshToken: async () => {
        const { tokens } = get();
        
        if (!tokens?.refresh_token) {
          get().logout();
          return;
        }

        try {
          const response = await apiClient.post<AuthResponse>('/auth/refresh', {
            refresh_token: tokens.refresh_token,
          });

          if (response.data.success && response.data.tokens) {
            set({
              tokens: response.data.tokens,
              error: null,
            });

            // Update authorization header
            apiClient.defaults.headers.common['Authorization'] = 
              `Bearer ${response.data.tokens.access_token}`;
          } else {
            throw new Error('Token refresh failed');
          }
        } catch (error) {
          // If refresh fails, logout user
          get().logout();
          throw error;
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setUser: (user: User) => {
        set({ user });
      },

      setTokens: (tokens: AuthTokens) => {
        set({ tokens });
        
        // Update authorization header
        apiClient.defaults.headers.common['Authorization'] = 
          `Bearer ${tokens.access_token}`;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Restore authorization header on app load
        if (state?.tokens?.access_token) {
          apiClient.defaults.headers.common['Authorization'] = 
            `Bearer ${state.tokens.access_token}`;
        }
      },
    }
  )
);

// Convenience hooks
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
export const useMfaRequired = () => useAuthStore((state) => state.mfaRequired);

// Auto token refresh setup
let refreshTimer: NodeJS.Timeout | null = null;

const setupTokenRefresh = () => {
  const { tokens, refreshToken, logout } = useAuthStore.getState();
  
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  if (!tokens?.access_token || !tokens?.expires_in) {
    return;
  }

  // Refresh token 5 minutes before expiry
  const refreshTime = (tokens.expires_in - 300) * 1000;
  
  if (refreshTime > 0) {
    refreshTimer = setTimeout(async () => {
      try {
        await refreshToken();
        setupTokenRefresh(); // Setup next refresh
      } catch (error) {
        console.error('Auto token refresh failed:', error);
        logout();
      }
    }, refreshTime);
  }
};

// Setup token refresh when store is rehydrated
useAuthStore.subscribe(
  (state) => state.tokens,
  (tokens) => {
    if (tokens) {
      setupTokenRefresh();
    }
  }
);

export default useAuthStore;