import { useState, useEffect } from 'react';
import { tradingAPI, apiClient } from '@/lib/api/client';
import { ArbitrageOpportunity } from '@/types/arbitrage';

export interface TechnicalAnalysis {
  symbol: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  rsi: number;
  macd: {
    line: number;
    signal: number;
    histogram: number;
  };
  movingAverages: {
    sma20: number;
    sma50: number;
    ema12: number;
    ema26: number;
  };
  support: number;
  resistance: number;
  recommendation: 'buy' | 'sell' | 'hold';
  confidence: number;
  timestamp: string;
}

export interface SupportResistanceData {
  symbol: string;
  support_levels: number[];
  resistance_levels: number[];
  current_price: number;
  strength_scores: {
    support: number[];
    resistance: number[];
  };
  pivot_points: {
    pivot: number;
    s1: number;
    s2: number;
    s3: number;
    r1: number;
    r2: number;
    r3: number;
  };
}

export interface InstitutionalFlow {
  timestamp: string;
  flow_type: 'inflow' | 'outflow';
  volume_usd: number;
  asset: string;
  exchange: string;
  confidence: number;
}

export interface AlphaSignal {
  id: string;
  symbol: string;
  signal_type: 'momentum' | 'mean_reversion' | 'breakout' | 'pattern';
  direction: 'long' | 'short';
  strength: number;
  confidence: number;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  timeframe: string;
  generated_at: string;
  expires_at: string;
}

export interface TrendingCoin {
  symbol: string;
  name: string;
  price: number;
  change_24h: number;
  volume_24h: number;
  market_cap: number;
  trending_score: number;
}

export interface MarketHealth {
  overall_score: number;
  volatility_index: number;
  correlation_breakdown: Record<string, number>;
  sector_health: Record<string, number>;
  risk_factors: string[];
  opportunities: string[];
  status: string;
}

export interface ExchangeAsset {
  symbol: string;
  name: string;
  balance: number;
  usd_value: number;
  available: number;
  locked: number;
  apy?: number;
  last_updated: string;
}

export interface MarketOverview {
  market_cap_change_24h: number;
  volume_change_24h: number;
  active_cryptocurrencies: number;
  market_dominance: {
    btc: number;
    eth: number;
  };
  fear_greed_index: number;
  trending_coins: Array<{
    symbol: string;
    name: string;
    price: number;
    change_24h: number;
  }>;
}

interface MarketAnalysisHookState {
  marketOverview: MarketOverview | null;
  technicalAnalysis: Record<string, TechnicalAnalysis>;
  arbitrageOpportunities: ArbitrageOpportunity[];
  supportResistanceData: Record<string, SupportResistanceData>;
  supportResistance: Record<string, SupportResistanceData>;
  institutionalFlows: InstitutionalFlow[];
  alphaSignals: AlphaSignal[];
  trendingCoins: TrendingCoin[];
  marketHealth: MarketHealth | null;
  exchangeAssets: Record<string, ExchangeAsset[]>;
  realtimePrices: Record<string, any>;
  sentimentAnalysis: Record<string, any>;
  volatilityData: Record<string, any>;
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
  fetchMarketOverview: () => Promise<void>;
  fetchTechnicalAnalysis: (symbols: string[] | string) => Promise<void>;
  fetchArbitrageData: () => Promise<void>;
  fetchSupportResistance: (symbol: string) => Promise<void>;
  fetchInstitutionalFlows: () => Promise<void>;
  fetchAlphaSignals: () => Promise<void>;
  fetchTrendingCoins: () => Promise<void>;
  fetchMarketHealth: () => Promise<void>;
  fetchExchangeAssets: (exchange: string) => Promise<void>;
  fetchRealtimePrices: (symbols: string[]) => Promise<void>;
  fetchSentimentAnalysis: (symbols: string[]) => Promise<void>;
  fetchArbitrageOpportunities: () => Promise<void>;
  fetchVolatilityAnalysis: (symbols: string[]) => Promise<void>;
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const useMarketAnalysis = (): MarketAnalysisHookState => {
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<Record<string, TechnicalAnalysis>>({});
  const [arbitrageOpportunities, setArbitrageOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [supportResistanceData, setSupportResistanceData] = useState<Record<string, SupportResistanceData>>({});
  const [institutionalFlows, setInstitutionalFlows] = useState<InstitutionalFlow[]>([]);
  const [alphaSignals, setAlphaSignals] = useState<AlphaSignal[]>([]);
  const [trendingCoins, setTrendingCoins] = useState<TrendingCoin[]>([]);
  const [marketHealth, setMarketHealth] = useState<MarketHealth | null>(null);
  const [exchangeAssets, setExchangeAssets] = useState<Record<string, ExchangeAsset[]>>({});
  const [realtimePrices, setRealtimePrices] = useState<Record<string, any>>({});
  const [sentimentAnalysis, setSentimentAnalysis] = useState<Record<string, any>>({});
  const [volatilityData, setVolatilityData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchMarketOverview = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/market-overview');
      
      if (response.data && response.data.success !== false) {
        // Handle different response structures
        if (response.data.data) {
          setMarketOverview(response.data.data);
        } else if (response.data.metadata && response.data.data) {
          setMarketOverview(response.data.data);
        } else {
          setMarketOverview(response.data);
        }
      } else {
        throw new Error(response.data?.message || 'Failed to fetch market overview');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch market overview';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchTechnicalAnalysis = async (symbols: string[] | string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const symbolsArray = Array.isArray(symbols) ? symbols : [symbols];
      const response = await apiClient.post('/market/technical-analysis', {
        symbols: symbolsArray
      });
      
      if (response.data && response.data.success !== false) {
        // Handle different response structures
        if (response.data.data) {
          setTechnicalAnalysis(response.data.data);
        } else {
          setTechnicalAnalysis(response.data);
        }
      } else {
        throw new Error(response.data?.message || 'Failed to fetch technical analysis');
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch technical analysis';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchArbitrageData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post('/market/arbitrage-opportunities', {
        symbols: 'BTC,ETH,SOL,ADA',
        exchanges: 'binance,kraken,kucoin',
        min_profit_bps: 5
      });
      
      if (response.data && response.data.success !== false) {
        // Handle different response structures
        const opportunities = Array.isArray(response.data.data) ? response.data.data : 
                             response.data.data?.opportunities || 
                             response.data.opportunities || [];
        
        setArbitrageOpportunities(opportunities.map((opp: any) => ({
          id: opp.id || Math.random().toString(36).substr(2, 9),
          symbol: opp.symbol || 'UNKNOWN',
          buyExchange: opp.buyExchange || opp.buy_exchange || 'UNKNOWN',
          sellExchange: opp.sellExchange || opp.sell_exchange || 'UNKNOWN',
          buyPrice: parseFloat(opp.buyPrice || opp.buy_price || 0),
          sellPrice: parseFloat(opp.sellPrice || opp.sell_price || 0),
          profitBps: parseFloat(opp.profitBps || opp.profit_bps || 0),
          profitUsd: parseFloat(opp.profitUsd || opp.profit_usd || 0),
          volume: parseFloat(opp.volume || 0),
          confidence: parseFloat(opp.confidence || 0.5)
        })));
      } else {
        throw new Error(response.data?.message || 'Failed to fetch arbitrage data');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch arbitrage opportunities';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketOverview();
    fetchArbitrageData();
    
    // Fetch technical analysis for major pairs
    fetchTechnicalAnalysis(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT']);
    
    // Set up polling for real-time updates
    const interval = setInterval(() => {
      fetchMarketOverview();
      fetchArbitrageData();
    }, 60000); // Update every minute
    
    return () => clearInterval(interval);
  }, []);

  const fetchSupportResistance = async (symbol: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get(`/market/support-resistance/${symbol}`);
      
      if (response.data && response.data.success !== false) {
        const data = response.data.data || response.data;
        setSupportResistanceData(prev => ({
          ...prev,
          [symbol]: {
            symbol,
            support_levels: data.support_levels || [],
            resistance_levels: data.resistance_levels || [],
            current_price: data.current_price || 0,
            strength_scores: data.strength_scores || { support: [], resistance: [] },
            pivot_points: data.pivot_points || {
              pivot: 0, s1: 0, s2: 0, s3: 0, r1: 0, r2: 0, r3: 0
            }
          }
        }));
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch support/resistance data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchInstitutionalFlows = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/market/institutional-flows');
      
      if (response.data && response.data.success !== false) {
        const flows = Array.isArray(response.data) ? response.data : 
                     Array.isArray(response.data.data) ? response.data.data : [];
        
        setInstitutionalFlows(flows.map((flow: any) => ({
          timestamp: flow.timestamp || new Date().toISOString(),
          flow_type: flow.flow_type || flow.type || 'inflow',
          volume_usd: parseFloat(flow.volume_usd || flow.volume || 0),
          asset: flow.asset || flow.symbol || 'UNKNOWN',
          exchange: flow.exchange || 'UNKNOWN',
          confidence: parseFloat(flow.confidence || 0.5)
        })));
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch institutional flows';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlphaSignals = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/market/alpha-signals');
      
      if (response.data && response.data.success !== false) {
        const signals = Array.isArray(response.data) ? response.data : 
                       Array.isArray(response.data.data) ? response.data.data : [];
        
        setAlphaSignals(signals.map((signal: any) => ({
          id: signal.id || signal.signal_id || Math.random().toString(36).substr(2, 9),
          symbol: signal.symbol || 'UNKNOWN',
          signal_type: signal.signal_type || signal.type || 'momentum',
          direction: signal.direction || 'long',
          strength: parseFloat(signal.strength || 0),
          confidence: parseFloat(signal.confidence || 0),
          entry_price: parseFloat(signal.entry_price || signal.price || 0),
          target_price: parseFloat(signal.target_price || signal.target || 0),
          stop_loss: parseFloat(signal.stop_loss || signal.stop || 0),
          timeframe: signal.timeframe || '1h',
          generated_at: signal.generated_at || signal.timestamp || new Date().toISOString(),
          expires_at: signal.expires_at || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        })));
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch alpha signals';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrendingCoins = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/market/trending-coins');
      
      if (response.data && response.data.success !== false) {
        const coins = Array.isArray(response.data) ? response.data : 
                     Array.isArray(response.data.data) ? response.data.data : 
                     response.data.trending_coins || [];
        
        setTrendingCoins(coins.map((coin: any) => ({
          symbol: coin.symbol || coin.id || 'UNKNOWN',
          name: coin.name || coin.symbol || 'Unknown Coin',
          price: parseFloat(coin.price || coin.current_price || 0),
          change_24h: parseFloat(coin.change_24h || coin.price_change_percentage_24h || 0),
          volume_24h: parseFloat(coin.volume_24h || coin.total_volume || 0),
          market_cap: parseFloat(coin.market_cap || 0),
          trending_score: parseFloat(coin.trending_score || coin.score || Math.random() * 100)
        })));
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch trending coins';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchMarketHealth = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/market/health');
      
      if (response.data && response.data.success !== false) {
        const health = response.data.data || response.data;
        setMarketHealth({
          overall_score: parseFloat(health.overall_score || health.score || 50),
          volatility_index: parseFloat(health.volatility_index || health.volatility || 0),
          correlation_breakdown: health.correlation_breakdown || health.correlations || {},
          sector_health: health.sector_health || health.sectors || {},
          risk_factors: Array.isArray(health.risk_factors) ? health.risk_factors : 
                      Array.isArray(health.risks) ? health.risks : [],
          opportunities: Array.isArray(health.opportunities) ? health.opportunities : [],
          status: health.status || 'healthy'
        });
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch market health';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchExchangeAssets = async (exchange: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get(`/exchanges/${exchange}/assets`);
      
      if (response.data && response.data.success !== false) {
        const assets = Array.isArray(response.data) ? response.data : 
                      Array.isArray(response.data.data) ? response.data.data : 
                      response.data.assets || [];
        
        setExchangeAssets(prev => ({
          ...prev,
          [exchange]: assets.map((asset: any) => ({
            symbol: asset.symbol || asset.asset || 'UNKNOWN',
            name: asset.name || asset.symbol || 'Unknown Asset',
            balance: parseFloat(asset.balance || asset.total || 0),
            usd_value: parseFloat(asset.usd_value || asset.value_usd || 0),
            available: parseFloat(asset.available || asset.free || asset.balance || 0),
            locked: parseFloat(asset.locked || asset.used || 0),
            apy: asset.apy ? parseFloat(asset.apy) : undefined,
            last_updated: asset.last_updated || asset.timestamp || new Date().toISOString()
          }))
        }));
      } else {
        throw new Error(response.data?.message || 'Invalid response format');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch exchange assets';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchRealtimePrices = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.post('/market/realtime-prices', { symbols });
      if (response.data && response.data.success !== false) {
        const prices = response.data.data || response.data;
        setRealtimePrices(prices);
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch realtime prices');
    } finally {
      setLoading(false);
    }
  };

  const fetchSentimentAnalysis = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.post('/market/sentiment', { symbols });
      if (response.data && response.data.success !== false) {
        const sentiment = response.data.data || response.data;
        setSentimentAnalysis(sentiment);
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch sentiment analysis');
    } finally {
      setLoading(false);
    }
  };

  const fetchArbitrageOpportunities = async (): Promise<void> => {
    await fetchArbitrageData();
  };

  const fetchVolatilityAnalysis = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.post('/market/volatility', { symbols });
      if (response.data && response.data.success !== false) {
        const volatility = response.data.data || response.data;
        setVolatilityData(volatility);
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch volatility analysis');
    } finally {
      setLoading(false);
    }
  };

  const refreshAll = async (): Promise<void> => {
    await Promise.all([
      fetchMarketOverview(),
      fetchArbitrageData(),
      fetchTechnicalAnalysis(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT'])
    ]);
  };

  const clearError = (): void => {
    setError(null);
  };

  return {
    marketOverview,
    technicalAnalysis,
    arbitrageOpportunities,
    supportResistanceData,
    supportResistance: supportResistanceData,
    institutionalFlows,
    alphaSignals,
    trendingCoins,
    marketHealth,
    exchangeAssets,
    realtimePrices,
    sentimentAnalysis,
    volatilityData,
    loading,
    isLoading: loading,
    error,
    lastUpdated,
    fetchMarketOverview,
    fetchTechnicalAnalysis,
    fetchArbitrageData,
    fetchSupportResistance,
    fetchInstitutionalFlows,
    fetchAlphaSignals,
    fetchTrendingCoins,
    fetchMarketHealth,
    fetchExchangeAssets,
    fetchRealtimePrices,
    fetchSentimentAnalysis,
    fetchArbitrageOpportunities,
    fetchVolatilityAnalysis,
    refreshAll,
    clearError
  };
};
