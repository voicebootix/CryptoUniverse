import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { AuthState, User, AuthTokens, LoginRequest, RegisterRequest } from '@/types/auth';
import { authApi } from '@/lib/api/auth';

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (user: User) => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  checkAuthStatus: () => Promise<void>;
}

export const useAuthStore = create<AuthState & AuthActions>()(
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
        set({ isLoading: true, error: null });
        
        try {
          const response = await authApi.login(credentials);
          
          if (response.mfa_required) {
            set({ 
              mfaRequired: true,
              isLoading: false,
              error: null 
            });
            return;
          }

          if (response.success && response.user && response.tokens) {
            set({
              user: response.user,
              tokens: response.tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
              mfaRequired: false
            });
          } else {
            throw new Error(response.error || 'Login failed');
          }
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
            isAuthenticated: false,
            user: null,
            tokens: null
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await authApi.register(data);
          
          if (response.success && response.user && response.tokens) {
            set({
              user: response.user,
              tokens: response.tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null
            });
          } else {
            throw new Error(response.error || 'Registration failed');
          }
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Registration failed',
            isAuthenticated: false,
            user: null,
            tokens: null
          });
          throw error;
        }
      },

      logout: () => {
        // Call logout API (fire and forget)
        authApi.logout().catch(console.error);
        
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
          mfaRequired: false
        });
      },

      refreshToken: async () => {
        const { tokens } = get();
        
        if (!tokens?.refresh_token) {
          get().logout();
          return;
        }

        try {
          const response = await authApi.refreshToken(tokens.refresh_token);
          
          if (response.success && response.tokens) {
            set({
              tokens: response.tokens,
              error: null
            });
          } else {
            throw new Error('Token refresh failed');
          }
        } catch (error) {
          console.error('Token refresh failed:', error);
          get().logout();
        }
      },

      updateUser: (user: User) => {
        set({ user });
      },

      clearError: () => {
        set({ error: null });
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      checkAuthStatus: async () => {
        const { tokens, isAuthenticated } = get();
        
        if (!tokens || !isAuthenticated) {
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({ user });
        } catch (error) {
          console.error('Failed to check auth status:', error);
          get().logout();
        }
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated
      }),
    }
  )
);

// Token refresh middleware
let refreshPromise: Promise<void> | null = null;

export const getValidToken = async (): Promise<string | null> => {
  const { tokens, refreshToken, logout } = useAuthStore.getState();
  
  if (!tokens) return null;

  // Check if token is about to expire (5 minutes buffer)
  const expiryTime = new Date().getTime() + tokens.expires_in * 1000;
  const bufferTime = 5 * 60 * 1000; // 5 minutes
  
  if (expiryTime - bufferTime < Date.now()) {
    // Token is about to expire, refresh it
    if (!refreshPromise) {
      refreshPromise = refreshToken().finally(() => {
        refreshPromise = null;
      });
    }
    
    try {
      await refreshPromise;
      return useAuthStore.getState().tokens?.access_token || null;
    } catch (error) {
      logout();
      return null;
    }
  }

  return tokens.access_token;
};

// Selectors for easier access
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
export const useMfaRequired = () => useAuthStore((state) => state.mfaRequired);