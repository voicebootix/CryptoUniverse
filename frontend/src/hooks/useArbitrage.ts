import { create } from 'zustand';
import { produce, Draft } from 'immer';
import { marketApi } from '@/lib/api/marketApi';

interface ArbitrageOpportunity {
  id: number;
  pair: string;
  buyExchange: string;
  sellExchange: string;
  buyPrice: number;
  sellPrice: number;
  spread: number;
  spreadPct: number;
  volume: number;
  profit: number;
  risk: 'low' | 'medium' | 'high';
}

interface OrderBookEntry {
  price: number;
  amount: number;
  total: number;
  exchange: string;
}

interface UnifiedOrderBook {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
}

interface ArbitrageState {
  opportunities: ArbitrageOpportunity[];
  orderBook: UnifiedOrderBook;
  crossExchangeComparison: Record<string, any>;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
  
  // Actions
  fetchArbitrageOpportunities: (symbols?: string, exchanges?: string, minProfitBps?: number) => Promise<void>;
  fetchCrossExchangeComparison: (symbols: string) => Promise<void>;
  fetchOrderBook: (symbol: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const useArbitrageStore = create<ArbitrageState>((set, get) => ({
  // Initial state
  opportunities: [],
  orderBook: { bids: [], asks: [] },
  crossExchangeComparison: {},
  isLoading: false,
  error: null,
  lastUpdated: null,

  // Fetch arbitrage opportunities
  fetchArbitrageOpportunities: async (
    symbols: string = 'BTC,ETH,SOL,ADA,DOT',
    exchanges: string = 'all',
    minProfitBps: number = 5
  ) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getArbitrageOpportunities(symbols, exchanges, minProfitBps);
      
      if (result.success) {
        // Transform API data to match UI expectations
        const opportunities = (result.data?.arbitrage_results || []).map((opp: any, index: number) => ({
          id: index + 1,
          pair: opp.symbol || `${symbols.split(',')[0]}/USDT`,
          buyExchange: opp.buy_exchange || 'Unknown',
          sellExchange: opp.sell_exchange || 'Unknown',
          buyPrice: opp.buy_price || 0,
          sellPrice: opp.sell_price || 0,
          spread: opp.sell_price - opp.buy_price || 0,
          spreadPct: opp.profit_percentage || 0,
          volume: opp.volume_constraint || 0,
          profit: opp.profit_percentage * (opp.volume_constraint || 1000) / 100 || 0,
          risk: opp.execution_complexity === 'LOW' ? 'low' as const : 
                opp.execution_complexity === 'HIGH' ? 'high' as const : 'medium' as const
        }));

        set(produce((draft: Draft<ArbitrageState>) => {
          draft.opportunities = opportunities;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch arbitrage opportunities', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch arbitrage opportunities', isLoading: false });
    }
  },

  // Fetch cross-exchange comparison
  fetchCrossExchangeComparison: async (symbols: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getCrossExchangeComparison(symbols);
      
      if (result.success) {
        set(produce((draft: Draft<ArbitrageState>) => {
          draft.crossExchangeComparison = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch cross-exchange comparison', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch cross-exchange comparison', isLoading: false });
    }
  },

  // Fetch unified order book (mock implementation for now)
  fetchOrderBook: async (symbol: string) => {
    set({ isLoading: true, error: null });
    try {
      // This would integrate with real exchange APIs to get order book data
      // For now, generate realistic-looking data based on current prices
      const priceResult = await marketApi.getSinglePrice(symbol);
      
      if (priceResult.success) {
        const basePrice = priceResult.data.price;
        const spread = basePrice * 0.001; // 0.1% spread
        
        const bids = Array.from({ length: 5 }, (_, i) => ({
          price: basePrice - spread * (i + 1),
          amount: Math.random() * 5 + 0.5,
          total: 0,
          exchange: ['Binance', 'Coinbase', 'Kraken', 'Bybit', 'OKX'][i]
        }));

        const asks = Array.from({ length: 5 }, (_, i) => ({
          price: basePrice + spread * (i + 1),
          amount: Math.random() * 5 + 0.5,
          total: 0,
          exchange: ['Binance', 'Coinbase', 'Kraken', 'Bybit', 'OKX'][i]
        }));

        // Calculate totals
        bids.forEach(bid => {
          bid.total = bid.price * bid.amount;
        });
        asks.forEach(ask => {
          ask.total = ask.price * ask.amount;
        });

        set(produce((draft: Draft<ArbitrageState>) => {
          draft.orderBook = { bids, asks };
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set(produce((draft: Draft<ArbitrageState>) => {
          draft.error = 'Failed to fetch price data for order book';
          draft.isLoading = false;
        }));
      }
    } catch (error: any) {
      set(produce((draft: Draft<ArbitrageState>) => {
        draft.error = error.message || 'Failed to fetch order book';
        draft.isLoading = false;
      }));
    }
  },

  // Refresh all data
  refreshAll: async () => {
    await Promise.allSettled([
      get().fetchArbitrageOpportunities(),
      get().fetchCrossExchangeComparison('BTC,ETH,SOL'),
      get().fetchOrderBook('BTC')
    ]);
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  }
}));

export const useArbitrage = () => {
  const store = useArbitrageStore();
  return store;
};

export default useArbitrage;