import { create } from 'zustand';
import { tradingAPI } from '@/lib/api'; // Assuming tradingAPI is set up for trading endpoints
import { produce } from 'immer';

interface Position {
  symbol: string;
  name: string;
  amount: number;
  value: number;
  price: number;
  change24h: number;
  unrealizedPnL: number;
  side: 'long' | 'short';
}

interface PortfolioState {
  totalValue: number;
  availableBalance: number;
  totalPnL: number;
  dailyPnL: number;
  dailyPnLPercent: number;
  totalPnLPercent: number;
  positions: Position[];
  isLoading: boolean;
  error: string | null;
  fetchPortfolio: () => Promise<void>;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  totalValue: 0,
  availableBalance: 0,
  totalPnL: 0,
  dailyPnL: 0,
  dailyPnLPercent: 0,
  totalPnLPercent: 0,
  positions: [],
  isLoading: false,
  error: null,
  fetchPortfolio: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await tradingAPI.get('/portfolio'); // Endpoint from trading.py
      const data = response.data;
      set(produce(draft => {
        draft.totalValue = data.total_value;
        draft.availableBalance = data.available_balance;
        draft.totalPnL = data.total_pnl;
        draft.dailyPnL = data.daily_pnl;
        draft.dailyPnLPercent = data.daily_pnl_pct;
        draft.totalPnLPercent = data.total_pnl_pct;
        draft.positions = data.positions.map((p: any) => ({
          symbol: p.symbol,
          name: p.name || p.symbol, // Backend might not send full name
          amount: p.amount,
          value: p.value_usd,
          price: p.entry_price,
          change24h: p.change_24h_pct,
          unrealizedPnL: p.unrealized_pnl,
          side: p.side,
        }));
        draft.isLoading = false;
      }));
    } catch (error: any) {
      set({ isLoading: false, error: error.message || 'Failed to fetch portfolio' });
    }
  },
}));
