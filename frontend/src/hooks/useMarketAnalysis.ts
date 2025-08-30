import { create } from 'zustand';
import { produce, Draft } from 'immer';
import { marketApi } from '@/lib/api/marketApi';

interface MarketAnalysisState {
  // Real-time data
  realtimePrices: Record<string, any>;
  technicalAnalysis: Record<string, any>;
  sentimentAnalysis: Record<string, any>;
  arbitrageOpportunities: any[];
  volatilityData: Record<string, any>;
  supportResistance: Record<string, any>;
  institutionalFlows: Record<string, any>;
  alphaSignals: Record<string, any>;
  
  // Market overview
  trendingCoins: any[];
  marketHealth: any;
  exchangeAssets: Record<string, any>;
  
  // State management
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
  
  // Actions
  fetchRealtimePrices: (symbols: string, exchanges?: string) => Promise<void>;
  fetchTechnicalAnalysis: (symbols: string, timeframe?: string, indicators?: string) => Promise<void>;
  fetchSentimentAnalysis: (symbols: string, timeframes?: string) => Promise<void>;
  fetchArbitrageOpportunities: (symbols?: string, exchanges?: string, minProfitBps?: number) => Promise<void>;
  fetchVolatilityAnalysis: (symbols: string, timeframes?: string) => Promise<void>;
  fetchSupportResistance: (symbols: string, timeframes?: string) => Promise<void>;
  fetchInstitutionalFlows: (symbols: string, timeframes?: string, flowTypes?: string) => Promise<void>;
  fetchAlphaSignals: (symbols: string, strategies?: string) => Promise<void>;
  fetchTrendingCoins: (limit?: number) => Promise<void>;
  fetchMarketHealth: () => Promise<void>;
  fetchExchangeAssets: (exchanges?: string, assetTypes?: string) => Promise<void>;
  fetchCompleteAssessment: (symbols: string, depth?: string) => Promise<any>;
  getSinglePrice: (symbol: string) => Promise<any>;
  getCrossExchangeComparison: (symbols: string) => Promise<any>;
  
  // Additional analysis methods
  fetchTrendAnalysis: (symbols: string, timeframes?: string) => Promise<void>;
  fetchVolumeAnalysis: (symbols: string, timeframes?: string) => Promise<void>;
  fetchMomentumIndicators: (symbols: string, timeframes?: string, indicators?: string) => Promise<void>;
  fetchMarketInefficiencies: (symbols?: string, inefficiencyTypes?: string) => Promise<void>;
  fetchCrossAssetArbitrage: (assetPairs?: string, exchanges?: string, minProfitBps?: number) => Promise<void>;
  fetchSpreadMonitoring: (symbols?: string, exchanges?: string) => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  
  // Utility actions
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const useMarketAnalysisStore = create<MarketAnalysisState>((set, get) => ({
  // Initial state
  realtimePrices: {},
  technicalAnalysis: {},
  sentimentAnalysis: {},
  arbitrageOpportunities: [],
  volatilityData: {},
  supportResistance: {},
  institutionalFlows: {},
  alphaSignals: {},
  trendingCoins: [],
  marketHealth: {},
  exchangeAssets: {},
  isLoading: false,
  error: null,
  lastUpdated: null,

  // Real-time prices
  fetchRealtimePrices: async (symbols: string, exchanges: string = 'all') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getRealtimePrices(symbols, exchanges);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.realtimePrices = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch real-time prices', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch real-time prices', isLoading: false });
    }
  },

  // Technical analysis
  fetchTechnicalAnalysis: async (symbols: string, timeframe: string = '1h', indicators?: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getTechnicalAnalysis(symbols, timeframe, indicators);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.technicalAnalysis = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch technical analysis', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch technical analysis', isLoading: false });
    }
  },

  // Market sentiment
  fetchSentimentAnalysis: async (symbols: string, timeframes?: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getSentimentAnalysis(symbols, timeframes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.sentimentAnalysis = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch sentiment analysis', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch sentiment analysis', isLoading: false });
    }
  },

  // Arbitrage opportunities
  fetchArbitrageOpportunities: async (symbols: string = 'BTC,ETH,SOL', exchanges: string = 'all', minProfitBps: number = 5) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getArbitrageOpportunities(symbols, exchanges, minProfitBps);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.arbitrageOpportunities = result.data || [];
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

  // Volatility analysis
  fetchVolatilityAnalysis: async (symbols: string, timeframes: string = '1h,4h,1d') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getVolatilityAnalysis(symbols, timeframes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.volatilityData = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch volatility analysis', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch volatility analysis', isLoading: false });
    }
  },

  // Support and resistance
  fetchSupportResistance: async (symbols: string, timeframes: string = '1h,4h,1d') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getSupportResistance(symbols, timeframes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.supportResistance = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch support/resistance data', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch support/resistance data', isLoading: false });
    }
  },

  // Institutional flows
  fetchInstitutionalFlows: async (symbols: string, timeframes: string = '1h,4h,1d', flowTypes?: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getInstitutionalFlows(symbols, timeframes, flowTypes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.institutionalFlows = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch institutional flows', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch institutional flows', isLoading: false });
    }
  },

  // Alpha signals
  fetchAlphaSignals: async (symbols: string, strategies?: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getAlphaSignals(symbols, strategies);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.alphaSignals = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch alpha signals', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch alpha signals', isLoading: false });
    }
  },

  // Trending coins
  fetchTrendingCoins: async (limit: number = 10) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getTrendingCoins(limit);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.trendingCoins = result.data || [];
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch trending coins', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch trending coins', isLoading: false });
    }
  },

  // Market health
  fetchMarketHealth: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getMarketHealth();
      set(produce((draft: Draft<MarketAnalysisState>) => {
        draft.marketHealth = result;
        draft.lastUpdated = new Date().toISOString();
        draft.isLoading = false;
      }));
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch market health', isLoading: false });
    }
  },

  // Exchange assets
  fetchExchangeAssets: async (exchanges: string = 'all', assetTypes?: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getExchangeAssets(exchanges, assetTypes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          draft.exchangeAssets = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch exchange assets', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch exchange assets', isLoading: false });
    }
  },

  // Complete market assessment
  fetchCompleteAssessment: async (symbols: string, depth: string = 'comprehensive') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getCompleteMarketAssessment(symbols, depth);
      set({ isLoading: false });
      return result;
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch complete assessment', isLoading: false });
      throw error;
    }
  },

  // Single price lookup
  getSinglePrice: async (symbol: string) => {
    try {
      const result = await marketApi.getSinglePrice(symbol);
      return result;
    } catch (error: any) {
      throw new Error(error.message || `Failed to fetch price for ${symbol}`);
    }
  },

  // Cross-exchange comparison
  getCrossExchangeComparison: async (symbols: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getCrossExchangeComparison(symbols);
      set({ isLoading: false });
      return result;
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch cross-exchange comparison', isLoading: false });
      throw error;
    }
  },

  // Refresh all data
  refreshAll: async () => {
    const symbols = 'BTC,ETH,SOL,ADA,DOT,MATIC,LINK,UNI';
    await Promise.allSettled([
      get().fetchRealtimePrices(symbols),
      get().fetchTechnicalAnalysis(symbols),
      get().fetchSentimentAnalysis(symbols),
      get().fetchArbitrageOpportunities(),
      get().fetchTrendingCoins(),
      get().fetchMarketHealth()
    ]);
  },

  // Trend analysis
  fetchTrendAnalysis: async (symbols: string, timeframes: string = '1h,4h,1d') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getTrendAnalysis(symbols, timeframes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          // Store in a new state property
          (draft as any).trendAnalysis = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch trend analysis', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch trend analysis', isLoading: false });
    }
  },

  // Volume analysis
  fetchVolumeAnalysis: async (symbols: string, timeframes: string = '1h,4h,1d') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getVolumeAnalysis(symbols, timeframes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).volumeAnalysis = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch volume analysis', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch volume analysis', isLoading: false });
    }
  },

  // Momentum indicators
  fetchMomentumIndicators: async (symbols: string, timeframes: string = '1h,4h,1d', indicators: string = 'rsi,macd,stoch') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getMomentumIndicators(symbols, timeframes, indicators);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).momentumIndicators = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch momentum indicators', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch momentum indicators', isLoading: false });
    }
  },

  // Market inefficiencies
  fetchMarketInefficiencies: async (symbols: string = 'BTC,ETH,SOL', inefficiencyTypes: string = 'spread,volume,time') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getMarketInefficiencies(symbols, inefficiencyTypes);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).marketInefficiencies = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch market inefficiencies', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch market inefficiencies', isLoading: false });
    }
  },

  // Cross-asset arbitrage
  fetchCrossAssetArbitrage: async (assetPairs: string = 'BTC-ETH,ETH-BNB,BTC-SOL', exchanges: string = 'all', minProfitBps: number = 5) => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getCrossAssetArbitrage(assetPairs, exchanges, minProfitBps);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).crossAssetArbitrage = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch cross-asset arbitrage', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch cross-asset arbitrage', isLoading: false });
    }
  },

  // Spread monitoring
  fetchSpreadMonitoring: async (symbols: string = 'BTC,ETH,SOL', exchanges: string = 'all') => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getSpreadMonitoring(symbols, exchanges);
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).spreadMonitoring = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch spread monitoring', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch spread monitoring', isLoading: false });
    }
  },

  // System status
  fetchSystemStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await marketApi.getSystemStatus();
      if (result.success) {
        set(produce((draft: Draft<MarketAnalysisState>) => {
          (draft as any).systemStatus = result.data;
          draft.lastUpdated = new Date().toISOString();
          draft.isLoading = false;
        }));
      } else {
        set({ error: result.error || 'Failed to fetch system status', isLoading: false });
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch system status', isLoading: false });
    }
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  }
}));

// Export hook for easy use
export const useMarketAnalysis = () => {
  const store = useMarketAnalysisStore();
  return store;
};

export default useMarketAnalysis;