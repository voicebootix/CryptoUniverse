import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiClient } from '@/lib/api/client';
// Note: Toast notifications removed from store - should be handled in components

interface PaperModeState {
  isPaperMode: boolean;
  paperBalance: number;
  paperStats: {
    totalTrades: number;
    winRate: number;
    totalProfit: number;
    bestTrade: number;
    worstTrade: number;
    readyForLive: boolean;
  } | null;
  isLoading: boolean;
  
  // Actions
  togglePaperMode: () => Promise<void>;
  fetchPaperStats: () => Promise<void>;
  setPaperMode: (enabled: boolean) => Promise<void>;
  resetPaperAccount: () => Promise<void>;
}

export const usePaperModeStore = create<PaperModeState>()(
  persist(
    (set, get) => ({
      isPaperMode: false,
      paperBalance: 10000, // Default paper balance
      paperStats: null,
      isLoading: false,

      togglePaperMode: async () => {
        const currentMode = get().isPaperMode;
        await get().setPaperMode(!currentMode);
      },

      setPaperMode: async (enabled: boolean) => {
        set({ isLoading: true });
        
        try {
          if (enabled) {
            // Initialize paper trading account if needed
            const response = await apiClient.post('/api/v1/paper-trading/setup');
            
            if (response.data.success) {
              set({ 
                isPaperMode: true,
                paperBalance: response.data.data.balance || 10000
              });
              
              // Toast notification handled in component
              
              // Fetch initial stats
              await get().fetchPaperStats();
            }
          } else {
            // Switching to real mode
            set({ isPaperMode: false });
            
            // Toast notification handled in component
          }
        } catch (error) {
          // Error handling delegated to component layer
        } finally {
          set({ isLoading: false });
        }
      },

      fetchPaperStats: async () => {
        try {
          const response = await apiClient.get('/api/v1/paper-trading/stats');
          
          if (response.data.success) {
            set({ 
              paperStats: response.data.data,
              paperBalance: response.data.data.currentBalance || get().paperBalance
            });
          }
        } catch (error) {
          // Error handling delegated to component layer
        }
      },

      resetPaperAccount: async () => {
        set({ isLoading: true });
        
        try {
          const response = await apiClient.post('/api/v1/paper-trading/reset');
          
          if (response.data.success) {
            set({
              paperBalance: 10000,
              paperStats: null
            });
            
            // Toast notification handled in component
            
            await get().fetchPaperStats();
          }
        } catch (error) {
          // Error handling delegated to component layer
        } finally {
          set({ isLoading: false });
        }
      }
    }),
    {
      name: 'paper-mode-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        isPaperMode: state.isPaperMode,
        paperBalance: state.paperBalance 
      }),
    }
  )
);

// Hook for easy access to paper mode status
export const useIsPaperMode = () => usePaperModeStore((state) => state.isPaperMode);

// Hook for paper mode stats
export const usePaperStats = () => usePaperModeStore((state) => state.paperStats);