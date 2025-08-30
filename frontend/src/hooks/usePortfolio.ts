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

interface PerformanceDataPoint {
  time: string;
  value: number;
}

interface MarketDataItem {
  symbol: string;
  price: number;
  change: number;
  volume: string;
}

interface RecentTrade {
  id: number;
  symbol: string;
  side: 'buy' | 'sell';
  amount: number;
  price: number;
  time: string;
  status: 'completed' | 'pending';
  pnl: number;
}

interface PortfolioState {
  totalValue: number;
  availableBalance: number;
  totalPnL: number;
  dailyPnL: number;
  dailyPnLPercent: number;
  totalPnLPercent: number;
  positions: Position[];
  performanceHistory: PerformanceDataPoint[];
  marketData: MarketDataItem[];
  recentTrades: RecentTrade[];
  isLoading: boolean;
  error: string | null;
  fetchPortfolio: () => Promise<void>;
  fetchStatus: () => Promise<void>;
  fetchMarketData: () => Promise<void>;
  fetchRecentTrades: () => Promise<void>;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  totalValue: 0,
  availableBalance: 0,
  totalPnL: 0,
  dailyPnL: 0,
  dailyPnLPercent: 0,
  totalPnLPercent: 0,
  positions: [],
  performanceHistory: [],
  marketData: [],
  recentTrades: [],
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
  fetchStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await tradingAPI.get('/status');
      const data = response.data;
      set(produce(draft => {
        if (data.performance_today && Array.isArray(data.performance_today.history)) {
          draft.performanceHistory = data.performance_today.history.map((h: any) => ({
            time: new Date(h.timestamp).toLocaleTimeString(),
            value: h.portfolio_value_usd,
          }));
        }
        draft.isLoading = false;
      }));
    } catch (error: any) {
      set({ isLoading: false, error: error.message || 'Failed to fetch system status' });
    }
  },
  fetchMarketData: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await tradingAPI.get('/market-overview');
      const data = response.data;
      set(produce(draft => {
        draft.marketData = data.market_data.map((item: any) => ({
          ...item,
          price: parseFloat(item.price),
        }));
        draft.isLoading = false;
      }));
    } catch (error: any) {
      set({ isLoading: false, error: error.message || 'Failed to fetch market data' });
    }
  },
  fetchRecentTrades: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await tradingAPI.get('/recent-trades');
      const data = response.data;
      set(produce(draft => {
        draft.recentTrades = data.recent_trades.map((trade: any) => ({
          ...trade,
          amount: parseFloat(trade.amount),
          price: parseFloat(trade.price),
          pnl: parseFloat(trade.pnl),
        }));
        draft.isLoading = false;
      }));
    } catch (error: any) {
      set({ isLoading: false, error: error.message || 'Failed to fetch recent trades' });
    }
  },
}));
