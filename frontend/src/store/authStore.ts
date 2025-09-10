import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthTokens, LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth';
import { apiClient } from '@/lib/api/client';

// Extend globalThis for TypeScript
declare global {
  var __authRefreshPromise: Promise<void> | null;
}

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
          // Simple direct login with extended timeout for Render
          let response;
          
          try {
            // First attempt with very long timeout for Render cold starts
            console.log('Starting first login attempt with 3-minute timeout...');
            response = await apiClient.post('/auth/login', credentials, {
              timeout: 180000 // 3 minutes timeout for very slow Render cold starts
            });
          } catch (firstError: any) {
            // Log error for debugging
            console.error('First login attempt failed:', firstError.message);
            
            // Enhanced timeout detection with safety checks
            const isTimeoutError = firstError && (
              firstError.code === 'ECONNABORTED' || 
              firstError.name === 'TimeoutError' ||
              firstError.isTimeout === true ||
              /timeout/i.test(firstError.message || '') || 
              /timeouterror/i.test(firstError.message || '')
            );
            
            if (isTimeoutError) {
              console.log('Timeout detected, trying once more with warm service...');
              
              // Wait 3 seconds for service to warm up properly
              console.log('Waiting 3 seconds before retry...');
              await new Promise(resolve => setTimeout(resolve, 3000));
              
              try {
                // Second attempt - service should be warm now
                console.log('Starting second login attempt with 90-second timeout...');
                response = await apiClient.post('/auth/login', credentials, {
                  timeout: 90000 // 90 seconds for warm service
                });
              } catch (secondError: any) {
                console.error('Second login attempt also failed:', secondError.message);
                
                // If second attempt also fails, throw user-friendly error
                throw new Error('Unable to connect to login service. The server may be starting up. Please wait a moment and try again.');
              }
            } else {
              // Not a timeout error, throw original error
              throw firstError;
            }
          }
          
          // If no response after attempts
          if (!response) {
            throw new Error('Login service unavailable. Please try again later.');
          }
          
          if (response.data.mfa_required) {
            set({ 
              isLoading: false, 
              mfaRequired: true,
              error: null 
            });
            return;
          }

          // Handle the actual backend response format
          if (response.data.access_token) {
            // Create user object from response
            const user = {
              id: response.data.user_id,
              email: credentials.email,
              role: response.data.role,
              tenant_id: response.data.tenant_id,
              permissions: response.data.permissions || []
            };

            // Create tokens object with properly normalized expiration timestamp
            const now = Math.floor(Date.now() / 1000);
            const rawExpiresIn = Number(response.data.expires_in) || 28800; // Default 8 hours
            
            // Normalize expires_in: if it looks like absolute timestamp, use it; otherwise treat as duration
            const expirationTimestamp = rawExpiresIn > now 
              ? rawExpiresIn  // Already an absolute timestamp
              : now + rawExpiresIn;  // Duration, convert to timestamp
            
            const tokens = {
              access_token: response.data.access_token,
              refresh_token: response.data.refresh_token,
              expires_in: Math.floor(expirationTimestamp), // Store as integer timestamp
              token_type: response.data.token_type
            };

            set({
              user: user as any,
              tokens: tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
              mfaRequired: false,
            });

            // CRITICAL FIX: Force localStorage save immediately
            localStorage.setItem('auth_token', response.data.access_token);
            localStorage.setItem('refresh_token', response.data.refresh_token || '');
            localStorage.setItem('user_data', JSON.stringify(user));
            localStorage.setItem('auth_timestamp', Date.now().toString());

            // Set authorization header for future requests
            apiClient.defaults.headers.common['Authorization'] = 
              `Bearer ${response.data.access_token}`;
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
        // Clear global refresh promise to prevent hanging state
        globalThis.__authRefreshPromise = null;
        
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
        // Use global deduplication to prevent concurrent refresh calls
        if (globalThis.__authRefreshPromise) {
          console.log('Token refresh already in progress, awaiting existing promise...');
          return await globalThis.__authRefreshPromise;
        }

        const { tokens } = get();
        
        if (!tokens?.refresh_token) {
          get().logout();
          return;
        }

        // Create and store the refresh promise globally
        globalThis.__authRefreshPromise = (async () => {
          try {
            console.log('Starting token refresh...');
            const response = await apiClient.post<AuthResponse>('/auth/refresh', {
              refresh_token: tokens.refresh_token,
            });

            if (response.data.success && response.data.tokens) {
              // Update tokens with properly normalized expiration timestamp
              const now = Math.floor(Date.now() / 1000);
              const rawExpiresIn = Number(response.data.tokens.expires_in) || 28800; // Default 8 hours
              
              // Normalize expires_in: if it looks like absolute timestamp, use it; otherwise treat as duration
              const expirationTimestamp = rawExpiresIn > now 
                ? rawExpiresIn  // Already an absolute timestamp
                : now + rawExpiresIn;  // Duration, convert to timestamp
              
              const updatedTokens = {
                ...response.data.tokens,
                expires_in: Math.floor(expirationTimestamp) // Store as integer timestamp
              };
              
              set({
                tokens: updatedTokens,
                error: null,
              });

              // Update authorization header
              apiClient.defaults.headers.common['Authorization'] = 
                `Bearer ${response.data.tokens.access_token}`;
              
              console.log('Token refresh completed successfully');
            } else {
              throw new Error('Token refresh failed');
            }
          } catch (error) {
            console.error('Token refresh failed:', error);
            // Clear the promise before logout to prevent hanging state
            globalThis.__authRefreshPromise = null;
            // If refresh fails, logout user
            get().logout();
            throw error;
          } finally {
            // Always clear the global promise on completion
            globalThis.__authRefreshPromise = null;
          }
        })();

        return await globalThis.__authRefreshPromise;
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

// Auto token refresh setup with improved handling
let refreshTimer: NodeJS.Timeout | null = null;

const setupTokenRefresh = () => {
  const { tokens, refreshToken, logout } = useAuthStore.getState();
  
  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }

  if (!tokens?.access_token || !tokens?.expires_in) {
    console.log('No valid tokens for refresh setup');
    return;
  }

  // Calculate time until expiry (expires_in is now always a timestamp)
  const now = Math.floor(Date.now() / 1000);
  const expirationTime = tokens.expires_in; // Now always normalized as timestamp
  const timeUntilExpiry = expirationTime - now;
  
  // If token already expired or expires very soon, refresh immediately
  if (timeUntilExpiry <= 60) {
    console.log('Token expired or expiring soon, refreshing immediately...');
    
    // Use global deduplication for immediate refresh
    if (!globalThis.__authRefreshPromise) {
      refreshToken().catch((error) => {
        console.error('Immediate token refresh failed:', error);
        logout();
      });
    } else {
      console.log('Immediate refresh already in progress, skipping...');
    }
    return;
  }
  
  // Schedule refresh 2 minutes before expiry
  const refreshTime = Math.max(1000, (timeUntilExpiry - 120) * 1000);
  
  console.log(`Token refresh scheduled in ${Math.floor(refreshTime / 1000)} seconds`);
  
  refreshTimer = setTimeout(async () => {
    console.log('Executing automatic token refresh...');
    
    // Use global deduplication for scheduled refresh
    if (globalThis.__authRefreshPromise) {
      console.log('Scheduled refresh skipped - refresh already in progress');
      // Still need to schedule next refresh cycle
      try {
        await globalThis.__authRefreshPromise;
        console.log('Awaited existing refresh, scheduling next cycle...');
        setupTokenRefresh(); // Setup next refresh cycle
      } catch (error) {
        console.error('Awaited refresh failed:', error);
        logout();
      }
      return;
    }
    
    try {
      await refreshToken();
      console.log('Automatic token refresh successful');
      setupTokenRefresh(); // Setup next refresh cycle
    } catch (error) {
      console.error('Auto token refresh failed:', error);
      logout();
    }
  }, refreshTime);
};

// Function to check if token is expired or expiring soon
const isTokenExpiredOrExpiring = () => {
  const { tokens } = useAuthStore.getState();
  
  if (!tokens?.access_token || !tokens?.expires_in) {
    return true;
  }
  
  const now = Math.floor(Date.now() / 1000);
  const expirationTime = tokens.expires_in; // Now always normalized as timestamp
  const timeUntilExpiry = expirationTime - now;
  
  // Consider expired if less than 1 minute remaining
  return timeUntilExpiry <= 60;
};

// Setup token refresh when store changes
useAuthStore.subscribe(
  (state) => {
    if (state.tokens && state.isAuthenticated) {
      setupTokenRefresh();
    } else if (!state.isAuthenticated && refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
  }
);

// Export utility function
export { isTokenExpiredOrExpiring };

export default useAuthStore;