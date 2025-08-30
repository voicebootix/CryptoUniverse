import { apiClient } from './client';

// Market Analysis API Client
export interface MarketDataItem {
  symbol: string;
  price: number;
  change: number;
  volume: string;
}

export interface PriceData {
  symbol: string;
  price: number;
  change_24h: number;
  volume_24h: number;
  market_cap?: number;
  timestamp: string;
  source: string;
}

export interface TechnicalAnalysis {
  symbol: string;
  timeframe: string;
  analysis: {
    trend: {
      direction: string;
      strength: number;
      sma_20: number;
      sma_50: number;
      ema_12: number;
      ema_26: number;
    };
    momentum: {
      rsi: number;
      macd: {
        macd: number;
        signal: number;
        histogram: number;
        trend: string;
      };
    };
  };
  signals: {
    buy: number;
    sell: number;
    neutral: number;
  };
  confidence: number;
  timestamp: string;
}

export interface ArbitrageOpportunity {
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  profit_percentage: number;
  profit_bps: number;
  volume_constraint: number;
  execution_complexity: string;
}

export interface MarketAssessment {
  assessment: {
    price_tracking: any;
    technical_analysis: any;
    market_sentiment: any;
    arbitrage_opportunities: any;
    alpha_signals: any;
  };
  market_score: number;
  executive_summary: string;
}

// Market Analysis API Functions
export const marketApi = {
  // Real-time price tracking
  async getRealtimePrices(symbols: string, exchanges: string = 'all'): Promise<any> {
    const response = await apiClient.get('/market/realtime-prices', {
      params: { symbols, exchanges }
    });
    return response.data;
  },

  // Technical analysis
  async getTechnicalAnalysis(
    symbols: string, 
    timeframe: string = '1h', 
    indicators?: string
  ): Promise<{ success: boolean; data: Record<string, TechnicalAnalysis> }> {
    const response = await apiClient.post('/market/technical-analysis', {
      symbols,
      timeframe,
      indicators
    });
    return response.data;
  },

  // Market sentiment
  async getSentimentAnalysis(
    symbols: string, 
    timeframes?: string
  ): Promise<any> {
    const response = await apiClient.post('/market/sentiment-analysis', {
      symbols,
      timeframes
    });
    return response.data;
  },

  // Arbitrage opportunities
  async getArbitrageOpportunities(
    symbols: string = 'BTC,ETH,SOL',
    exchanges: string = 'all',
    min_profit_bps: number = 5
  ): Promise<{ success: boolean; data: ArbitrageOpportunity[] }> {
    const response = await apiClient.post('/market/arbitrage-opportunities', {
      symbols,
      exchanges,
      min_profit_bps
    });
    return response.data;
  },

  // Complete market assessment
  async getCompleteMarketAssessment(
    symbols: string,
    depth: string = 'comprehensive'
  ): Promise<{ success: boolean; data: MarketAssessment }> {
    const response = await apiClient.post('/market/complete-assessment', {
      symbols,
      depth
    });
    return response.data;
  },

  // Volatility analysis
  async getVolatilityAnalysis(
    symbols: string,
    timeframes: string = '1h,4h,1d'
  ): Promise<any> {
    const response = await apiClient.get('/market/volatility-analysis', {
      params: { symbols, timeframes }
    });
    return response.data;
  },

  // Support and resistance levels
  async getSupportResistance(
    symbols: string,
    timeframes: string = '1h,4h,1d'
  ): Promise<any> {
    const response = await apiClient.get('/market/support-resistance', {
      params: { symbols, timeframes }
    });
    return response.data;
  },

  // Institutional flows
  async getInstitutionalFlows(
    symbols: string,
    timeframes: string = '1h,4h,1d',
    flow_types: string = 'whale_tracking,institutional_trades,etf_flows'
  ): Promise<any> {
    const response = await apiClient.get('/market/institutional-flows', {
      params: { symbols, timeframes, flow_types }
    });
    return response.data;
  },

  // Alpha signals
  async getAlphaSignals(
    symbols: string,
    strategies: string = 'momentum,mean_reversion,breakout'
  ): Promise<any> {
    const response = await apiClient.get('/market/alpha-signals', {
      params: { symbols, strategies }
    });
    return response.data;
  },

  // Exchange assets discovery
  async getExchangeAssets(
    exchanges: string = 'all',
    asset_types: string = 'spot,futures,options'
  ): Promise<any> {
    const response = await apiClient.get('/market/exchange-assets', {
      params: { exchanges, asset_types }
    });
    return response.data;
  },

  // Trending coins
  async getTrendingCoins(limit: number = 10): Promise<any> {
    const response = await apiClient.get('/market/trending-coins', {
      params: { limit }
    });
    return response.data;
  },

  // Market health
  async getMarketHealth(): Promise<any> {
    const response = await apiClient.get('/market/market-health');
    return response.data;
  },

  // Single crypto price
  async getSinglePrice(symbol: string): Promise<{ success: boolean; data: PriceData }> {
    const response = await apiClient.get(`/market/single-price/${symbol}`);
    return response.data;
  },

  // Cross-exchange comparison
  async getCrossExchangeComparison(symbols: string): Promise<any> {
    const response = await apiClient.get('/market/cross-exchange-comparison', {
      params: { symbols }
    });
    return response.data;
  }
};

export default marketApi;