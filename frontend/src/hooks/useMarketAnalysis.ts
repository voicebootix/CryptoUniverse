import { useState, useEffect } from 'react';
import { tradingAPI } from '@/lib/api/client';
import { ArbitrageOpportunity } from './useArbitrage';

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
  loading: boolean;
  error: string | null;
  fetchMarketOverview: () => Promise<void>;
  fetchTechnicalAnalysis: (symbols: string[]) => Promise<void>;
  fetchArbitrageData: () => Promise<void>;
}

export const useMarketAnalysis = (): MarketAnalysisHookState => {
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<Record<string, TechnicalAnalysis>>({});
  const [arbitrageOpportunities, setArbitrageOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMarketOverview = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/market/overview');
      
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

  const fetchTechnicalAnalysis = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.post('/market/technical-analysis', {
        symbols
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
      const response = await tradingAPI.get('/arbitrage/scan');
      
      if (response.data && response.data.success !== false) {
        // Handle different response structures
        if (Array.isArray(response.data.data)) {
          setArbitrageOpportunities(response.data.data);
        } else if (Array.isArray(response.data)) {
          setArbitrageOpportunities(response.data);
        } else {
          setArbitrageOpportunities([]);
        }
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

  return {
    marketOverview,
    technicalAnalysis,
    arbitrageOpportunities,
    loading,
    error,
    fetchMarketOverview,
    fetchTechnicalAnalysis,
    fetchArbitrageData
  };
};
