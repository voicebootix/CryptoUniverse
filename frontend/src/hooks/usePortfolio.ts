import { create } from 'zustand';
import { tradingAPI } from '@/lib/api/client';
import { produce, Draft } from 'immer';

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
  connectWebSocket: () => void;
}

let socket: WebSocket | null = null;

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
      set(produce((draft: Draft<PortfolioState>) => {
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
      set(produce((draft: Draft<PortfolioState>) => {
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
      set(produce((draft: Draft<PortfolioState>) => {
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
      set(produce((draft: Draft<PortfolioState>) => {
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
  connectWebSocket: () => {
    if (socket) {
      return;
    }

    // Use backend URL for WebSocket connection
    const wsUrl = import.meta.env.VITE_API_URL 
      ? `wss://${import.meta.env.VITE_API_URL.replace('https://', '').replace('/api/v1', '')}/api/v1/trading/ws`
      : `wss://cryptouniverse.onrender.com/api/v1/trading/ws`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('WebSocket connected');
      
      // Subscribe to market data for major cryptocurrencies
      const subscribeMessage = {
        type: 'subscribe_market',
        symbols: ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'LINK', 'UNI']
      };
      socket?.send(JSON.stringify(subscribeMessage));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        set(produce((draft: Draft<PortfolioState>) => {
          if (data.type === 'market_update') {
            // Update market data in real-time
            const existingIndex = draft.marketData.findIndex(item => item.symbol === data.symbol);
            if (existingIndex >= 0) {
              draft.marketData[existingIndex] = {
                symbol: data.symbol,
                price: data.data.price,
                change: data.data.change_24h,
                volume: data.data.volume_24h ? `${(data.data.volume_24h / 1e6).toFixed(0)}M` : 'N/A'
              };
            } else {
              draft.marketData.push({
                symbol: data.symbol,
                price: data.data.price,
                change: data.data.change_24h,
                volume: data.data.volume_24h ? `${(data.data.volume_24h / 1e6).toFixed(0)}M` : 'N/A'
              });
            }
          } else if (data.performance_today) {
            draft.dailyPnL = data.performance_today.profit_loss;
          }
        }));
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      socket = null;
      
      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        get().connectWebSocket();
      }, 5000);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  },
}));
