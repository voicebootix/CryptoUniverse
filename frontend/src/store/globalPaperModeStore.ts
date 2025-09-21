import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiClient } from '@/lib/api/client';

// Global Paper Mode Store - affects ALL components across the entire app
interface GlobalPaperModeState {
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
  setGlobalPaperMode: (enabled: boolean) => Promise<void>;
  toggleGlobalPaperMode: () => Promise<void>;
  fetchPaperStats: () => Promise<void>;
  resetPaperAccount: () => Promise<void>;
  
  // Theme management based on paper mode
  getThemeColor: () => 'paper' | 'live';
}

export const useGlobalPaperModeStore = create<GlobalPaperModeState>()(
  persist(
    (set, get) => ({
      isPaperMode: false,
      paperBalance: 10000,
      paperStats: null,
      isLoading: false,

      setGlobalPaperMode: async (enabled: boolean) => {
        set({ isLoading: true });

        try {
          if (enabled) {
            // Initialize paper trading
            const response = await apiClient.post('/paper-trading/setup');

            if (response.data.success) {
              const portfolio =
                response.data.virtual_portfolio || response.data.paper_portfolio || response.data.portfolio || {};

              set({
                isPaperMode: true,
                paperBalance: portfolio?.cash_balance ?? portfolio?.balance ?? 10000
              });

              // Fetch initial stats
              await get().fetchPaperStats();
            }
          } else {
            // Switch to live mode
            set({ isPaperMode: false });
          }
          
          // Update document theme for global color scheme
          document.documentElement.setAttribute(
            'data-trading-mode', 
            enabled ? 'paper' : 'live'
          );
          
        } catch (error) {
          console.error('Failed to set paper mode:', error);
        } finally {
          set({ isLoading: false });
        }
      },

      toggleGlobalPaperMode: async () => {
        const currentMode = get().isPaperMode;
        await get().setGlobalPaperMode(!currentMode);
      },

      fetchPaperStats: async () => {
        try {
          const response = await apiClient.get('/paper-trading/stats');

          if (response.data.success) {
            const portfolio = response.data.virtual_portfolio || response.data.paper_portfolio || {};
            const stats = response.data.stats || {};
            const performance = portfolio?.performance_metrics || {};

            set({
              paperStats: {
                totalTrades: stats.total_trades ?? performance.total_trades ?? 0,
                winRate: stats.win_rate ?? performance.win_rate ?? 0,
                totalProfit: stats.total_profit ?? performance.total_profit_loss ?? 0,
                bestTrade: stats.best_trade ?? performance.best_trade ?? 0,
                worstTrade: stats.worst_trade ?? performance.worst_trade ?? 0,
                readyForLive: response.data.ready_for_live_trading ?? false
              },
              paperBalance: portfolio?.cash_balance ?? get().paperBalance
            });
          }
        } catch (error) {
          console.error('Failed to fetch paper stats:', error);
        }
      },

      resetPaperAccount: async () => {
        set({ isLoading: true });

        try {
          const response = await apiClient.post('/paper-trading/reset');

          if (response.data.success) {
            const portfolio = response.data.virtual_portfolio || {};

            set({
              paperBalance: portfolio?.cash_balance ?? 10000,
              paperStats: null
            });

            await get().fetchPaperStats();
          }
        } catch (error) {
          console.error('Failed to reset paper account:', error);
        } finally {
          set({ isLoading: false });
        }
      },

      getThemeColor: () => {
        return get().isPaperMode ? 'paper' : 'live';
      }
    }),
    {
      name: 'global-paper-mode-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        isPaperMode: state.isPaperMode,
        paperBalance: state.paperBalance,
        paperStats: state.paperStats 
      }),
    }
  )
);

// Convenience hooks
export const useGlobalPaperMode = () => useGlobalPaperModeStore((state) => state.isPaperMode);
export const useGlobalPaperModeActions = () => useGlobalPaperModeStore((state) => ({
  setGlobalPaperMode: state.setGlobalPaperMode,
  toggleGlobalPaperMode: state.toggleGlobalPaperMode,
  fetchPaperStats: state.fetchPaperStats,
  resetPaperAccount: state.resetPaperAccount,
}));
export const useGlobalPaperStats = () => useGlobalPaperModeStore((state) => state.paperStats);
export const useGlobalThemeColor = () => useGlobalPaperModeStore((state) => state.getThemeColor());