import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiClient } from '@/lib/api/client';
import { toast } from '@/components/ui/use-toast';

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
              
              toast({
                title: "Paper Mode Activated",
                description: "You're now trading with virtual funds. Perfect for practice!",
                duration: 3000,
              });
              
              // Fetch initial stats
              await get().fetchPaperStats();
            }
          } else {
            // Switching to real mode
            set({ isPaperMode: false });
            
            toast({
              title: "Real Trading Mode",
              description: "You're now trading with real funds. Trade carefully!",
              variant: "destructive",
              duration: 3000,
            });
          }
        } catch (error) {
          console.error('Failed to toggle paper mode:', error);
          toast({
            title: "Error",
            description: "Failed to change trading mode. Please try again.",
            variant: "destructive",
          });
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
          console.error('Failed to fetch paper stats:', error);
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
            
            toast({
              title: "Paper Account Reset",
              description: "Your paper trading account has been reset to $10,000",
              duration: 3000,
            });
            
            await get().fetchPaperStats();
          }
        } catch (error) {
          console.error('Failed to reset paper account:', error);
          toast({
            title: "Error",
            description: "Failed to reset paper account. Please try again.",
            variant: "destructive",
          });
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