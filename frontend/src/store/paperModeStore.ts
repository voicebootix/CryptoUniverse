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
            const response = await apiClient.post('/paper-trading/setup');

            if (response.data.success) {
              const portfolio =
                response.data.virtual_portfolio || response.data.paper_portfolio || response.data.portfolio || {};

              set({
                isPaperMode: true,
                paperBalance: portfolio.cash_balance ?? portfolio.balance ?? 10000
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
          const response = await apiClient.get('/paper-trading/stats');

          if (response.data.success) {
            const portfolio = response.data.virtual_portfolio || response.data.paper_portfolio || {};
            const stats = response.data.stats || {};
            const performance = portfolio.performance_metrics || {};

            set({
              paperStats: {
                totalTrades: stats.total_trades ?? performance.total_trades ?? 0,
                winRate: stats.win_rate ?? performance.win_rate ?? 0,
                totalProfit: stats.total_profit ?? performance.total_profit_loss ?? 0,
                bestTrade: stats.best_trade ?? performance.best_trade ?? 0,
                worstTrade: stats.worst_trade ?? performance.worst_trade ?? 0,
                readyForLive: response.data.ready_for_live_trading ?? false
              },
              paperBalance: portfolio.cash_balance ?? get().paperBalance
            });
          }
        } catch (error) {
          // Error handling delegated to component layer
        }
      },

      resetPaperAccount: async () => {
        set({ isLoading: true });

        try {
          const response = await apiClient.post('/paper-trading/reset');

          if (response.data.success) {
            const portfolio = response.data.virtual_portfolio || {};

            set({
              paperBalance: portfolio.cash_balance ?? 10000,
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