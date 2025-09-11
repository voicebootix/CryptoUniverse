import { useState, useEffect, useRef } from 'react';
import pipelineApi, { PipelineResult } from '@/lib/api/pipelineApi';
import { ArbitrageOpportunity } from '@/types/arbitrage';

// Enhanced interfaces using pipeline data
export interface PipelineMarketAnalysis {
  pipeline_id: string;
  market_analysis: Record<string, any>;
  trading_strategies: Record<string, any>;
  portfolio_risk: Record<string, any>;
  ai_consensus: Record<string, any>;
  trade_execution: Record<string, any>;
  execution_time: number;
  phase_timings: Record<string, number>;
  last_updated: string;
}

export interface PipelineTechnicalAnalysis {
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
  ai_consensus_score: number;
  pipeline_source: boolean;
  timestamp: string;
}

interface PipelineAnalysisHookState {
  marketOverview: any | null;
  technicalAnalysis: Record<string, PipelineTechnicalAnalysis>;
  arbitrageOpportunities: ArbitrageOpportunity[];
  supportResistanceData: Record<string, any>;
  institutionalFlows: any[];
  alphaSignals: any[];
  trendingCoins: any[];
  marketHealth: any | null;
  realtimePrices: Record<string, any>;
  sentimentAnalysis: Record<string, any>;
  volatilityData: Record<string, any>;
  autonomousStatus: any | null;
  systemMetrics: any | null;
  pipelineHistory: any[];
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
  
  // Pipeline-specific methods
  fetchMarketOverview: () => Promise<void>;
  fetchTechnicalAnalysis: (symbols: string[] | string) => Promise<void>;
  fetchArbitrageData: () => Promise<void>;
  fetchSupportResistance: (symbol: string) => Promise<void>;
  fetchInstitutionalFlows: () => Promise<void>;
  fetchAlphaSignals: () => Promise<void>;
  fetchRealtimePrices: (symbols: string[]) => Promise<void>;
  fetchSentimentAnalysis: (symbols: string[]) => Promise<void>;
  fetchVolatilityAnalysis: (symbols: string[]) => Promise<void>;
  fetchTradingOpportunities: (riskTolerance?: string) => Promise<void>;
  fetchAssetAnalysis: (symbol: string) => Promise<void>;
  
  // Autonomous mode controls
  startAutonomousMode: (config?: Record<string, any>) => Promise<void>;
  stopAutonomousMode: () => Promise<void>;
  fetchAutonomousStatus: () => Promise<void>;
  
  // System monitoring
  fetchSystemMetrics: () => Promise<void>;
  fetchPipelineHistory: (limit?: number) => Promise<void>;
  
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const usePipelineAnalysis = (userId: string = 'frontend'): PipelineAnalysisHookState => {
  const [marketOverview, setMarketOverview] = useState<any | null>(null);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<Record<string, PipelineTechnicalAnalysis>>({});
  const [arbitrageOpportunities, setArbitrageOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [supportResistanceData, setSupportResistanceData] = useState<Record<string, any>>({});
  const [institutionalFlows, setInstitutionalFlows] = useState<any[]>([]);
  const [alphaSignals, setAlphaSignals] = useState<any[]>([]);
  const [trendingCoins, setTrendingCoins] = useState<any[]>([]);
  const [marketHealth, setMarketHealth] = useState<any | null>(null);
  const [realtimePrices, setRealtimePrices] = useState<Record<string, any>>({});
  const [sentimentAnalysis, setSentimentAnalysis] = useState<Record<string, any>>({});
  const [volatilityData, setVolatilityData] = useState<Record<string, any>>({});
  const [autonomousStatus, setAutonomousStatus] = useState<any | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<any | null>(null);
  const [pipelineHistory, setPipelineHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isRefreshingRef = useRef<boolean>(false);

  const extractPipelineData = (result: PipelineResult) => {
    return {
      marketAnalysis: result.pipeline_results.market_analysis || {},
      tradingStrategies: result.pipeline_results.trading_strategies || {},
      portfolioRisk: result.pipeline_results.portfolio_risk || {},
      aiConsensus: result.pipeline_results.ai_consensus || {},
      tradeExecution: result.pipeline_results.trade_execution || {},
      executionTime: result.execution_time,
      phaseTimings: result.phase_timings
    };
  };

  const fetchMarketOverview = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      // Separate API call handling from processing
      const result = await pipelineApi.getMarketOverview(
        'BTC,ETH,BNB,SOL,ADA,XRP,MATIC,DOT,AVAX,LINK',
        '1h,4h,1d',
        userId
      );
      
      if (!result.success) {
        throw new Error('API call failed: Pipeline could not fetch market overview');
      }
      
      // Process response in separate try/catch
      try {
        const pipelineData = extractPipelineData(result);
        setMarketOverview({
          ...pipelineData.marketAnalysis,
          ai_consensus: pipelineData.aiConsensus,
          execution_time: pipelineData.executionTime,
          pipeline_source: true
        });
      } catch (processingError: any) {
        console.error('Data processing error:', processingError);
        setError(`Data processing failed: ${processingError.message}`);
      }
      
    } catch (apiError: any) {
      console.error('API error:', apiError);
      setError(`API request failed: ${apiError.message}`);
    }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline market overview');
    } finally {
      setLoading(false);
    }
  };

  const fetchTechnicalAnalysis = async (symbols: string[] | string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const symbolsStr = Array.isArray(symbols) ? symbols.join(',') : symbols;
      const result = await pipelineApi.getTechnicalAnalysis(symbolsStr, '1h,4h,1d', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        const analysisData = pipelineData.marketAnalysis;
        const aiData = pipelineData.aiConsensus;
        
        // Transform pipeline data to match expected format
        const transformedAnalysis: Record<string, PipelineTechnicalAnalysis> = {};
        
        Object.keys(analysisData).forEach(symbol => {
          const marketData = analysisData[symbol] ?? {};
          const aiConsensus = aiData[symbol] ?? {};
          const techIndicators = marketData.technical_indicators ?? {};
          const supportLevels = Array.isArray(marketData.support_levels) ? marketData.support_levels : [];
          const resistanceLevels = Array.isArray(marketData.resistance_levels) ? marketData.resistance_levels : [];
          
          transformedAnalysis[symbol] = {
            symbol,
            trend: aiConsensus.trend_direction ?? marketData.trend ?? 'neutral',
            rsi: techIndicators.rsi ?? 50,
            macd: {
              line: techIndicators.macd ?? 0,
              signal: techIndicators.macd_signal ?? 0,
              histogram: techIndicators.macd_histogram ?? 0
            },
            movingAverages: {
              sma20: techIndicators.sma_20 ?? 0,
              sma50: techIndicators.sma_50 ?? 0,
              ema12: techIndicators.ema_12 ?? 0,
              ema26: techIndicators.ema_26 ?? 0
            },
            support: supportLevels[0] ?? 0,
            resistance: resistanceLevels[0] ?? 0,
            recommendation: aiConsensus.recommendation ?? 'hold',
            confidence: aiConsensus.confidence_score ?? 0.5,
            ai_consensus_score: aiConsensus.consensus_score ?? 0.5,
            pipeline_source: true,
            timestamp: result?.last_updated ?? Date.now()
          };
        });
        
        setTechnicalAnalysis(transformedAnalysis);
      } else {
        throw new Error('Pipeline failed to fetch technical analysis');
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline technical analysis');
    } finally {
      setLoading(false);
    }
  };

  const fetchArbitrageData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getArbitrageOpportunities('BTC,ETH,SOL,ADA', 'all', 5, userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        const opportunities = pipelineData.tradingStrategies.arbitrage_opportunities || [];
        
        setArbitrageOpportunities(opportunities.map((opp: any) => {
          const buyPriceNum = Number(opp.buy_price ?? 0) || 0;
          const sellPriceNum = Number(opp.sell_price ?? 0) || 0;
          const profitBpsNum = Number(opp.profit_bps ?? 0) || 0;
          const profitUsdNum = Number(opp.profit_usd ?? 0) || 0;
          const volumeNum = Number(opp.volume ?? 0) || 0;
          const confidenceNum = Number(opp.confidence ?? 0.5) || 0.5;
          
          return {
            id: opp.id || Math.random().toString(36).substr(2, 9),
            symbol: opp.symbol || 'UNKNOWN',
            buyExchange: opp.buy_exchange || 'UNKNOWN',
            sellExchange: opp.sell_exchange || 'UNKNOWN',
            buyPrice: buyPriceNum,
            sellPrice: sellPriceNum,
            profitBps: profitBpsNum,
            profitUsd: profitUsdNum,
            volume: volumeNum,
            confidence: confidenceNum,
            pipeline_source: true
          };
        }));
      } else {
        throw new Error('Pipeline failed to fetch arbitrage opportunities');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline arbitrage data');
    } finally {
      setLoading(false);
    }
  };

  const fetchSupportResistance = async (symbol: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getSupportResistance(symbol, '1h,4h,1d', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        const data = pipelineData.marketAnalysis[symbol] || {};
        
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
            },
            pipeline_source: true
          }
        }));
      } else {
        throw new Error('Pipeline failed to fetch support/resistance data');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline support/resistance data');
    } finally {
      setLoading(false);
    }
  };

  const fetchInstitutionalFlows = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getInstitutionalFlows(
        'BTC,ETH,SOL',
        '1h,4h,1d',
        'whale_moves,institutional_trades,etf_flows',
        userId
      );
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        const flows = pipelineData.marketAnalysis.institutional_flows || [];
        
        setInstitutionalFlows(flows.map((flow: any) => ({
          timestamp: flow.timestamp || new Date().toISOString(),
          flow_type: flow.flow_type || 'inflow',
          volume_usd: Number(flow.volume_usd ?? 0) || 0,
          asset: flow.asset || 'UNKNOWN',
          exchange: flow.exchange || 'UNKNOWN',
          confidence: Number(flow.confidence ?? 0.5) || 0.5,
          pipeline_source: true
        })));
      } else {
        throw new Error('Pipeline failed to fetch institutional flows');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline institutional flows');
    } finally {
      setLoading(false);
    }
  };

  const fetchAlphaSignals = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getAlphaSignals(
        'BTC,ETH,SOL',
        'momentum,mean_reversion,breakout',
        userId
      );
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        const signals = pipelineData.tradingStrategies.alpha_signals || [];
        
        setAlphaSignals(signals.map((signal: any) => ({
          id: signal.id || Math.random().toString(36).substr(2, 9),
          symbol: signal.symbol || 'UNKNOWN',
          signal_type: signal.signal_type || 'momentum',
          direction: signal.direction || 'long',
          strength: Number(signal.strength ?? 0) || 0,
          confidence: Number(signal.confidence ?? 0) || 0,
          entry_price: Number(signal.entry_price ?? 0) || 0,
          target_price: Number(signal.target_price ?? 0) || 0,
          stop_loss: Number(signal.stop_loss ?? 0) || 0,
          timeframe: signal.timeframe || '1h',
          generated_at: signal.generated_at || new Date().toISOString(),
          expires_at: signal.expires_at || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          pipeline_source: true
        })));
      } else {
        throw new Error('Pipeline failed to fetch alpha signals');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline alpha signals');
    } finally {
      setLoading(false);
    }
  };

  const fetchRealtimePrices = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getRealtimePrices(symbols.join(','), 'all', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        setRealtimePrices({
          ...pipelineData.marketAnalysis.price_data,
          pipeline_source: true,
          execution_time: pipelineData.executionTime
        });
      } else {
        throw new Error('Pipeline failed to fetch realtime prices');
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline realtime prices');
    } finally {
      setLoading(false);
    }
  };

  const fetchSentimentAnalysis = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getSentimentAnalysis(symbols.join(','), '1h,4h,1d', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        setSentimentAnalysis({
          ...pipelineData.marketAnalysis.sentiment_analysis,
          ai_consensus: pipelineData.aiConsensus,
          pipeline_source: true
        });
      } else {
        throw new Error('Pipeline failed to fetch sentiment analysis');
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline sentiment analysis');
    } finally {
      setLoading(false);
    }
  };

  const fetchVolatilityAnalysis = async (symbols: string[]): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getVolatilityAnalysis(symbols.join(','), '1h,4h,1d', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        setVolatilityData({
          ...pipelineData.marketAnalysis.volatility_analysis,
          pipeline_source: true
        });
      } else {
        throw new Error('Pipeline failed to fetch volatility analysis');
      }
      setLastUpdated(new Date().toISOString());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline volatility analysis');
    } finally {
      setLoading(false);
    }
  };

  const fetchTradingOpportunities = async (riskTolerance: string = 'balanced'): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getTradingOpportunities(
        'BTC,ETH,SOL,MATIC,LINK,UNI,AVAX,DOT',
        riskTolerance,
        userId
      );
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        // Store opportunities in alphaSignals for now (could create separate state)
        const opportunities = pipelineData.tradingStrategies.opportunities || [];
        setAlphaSignals(prev => [...prev, ...opportunities.map((opp: any) => ({
          ...opp,
          id: opp.id || Math.random().toString(36).substr(2, 9),
          pipeline_source: true,
          signal_type: 'opportunity'
        }))]);
      } else {
        throw new Error('Pipeline failed to fetch trading opportunities');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline trading opportunities');
    } finally {
      setLoading(false);
    }
  };

  const fetchAssetAnalysis = async (symbol: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.getAssetAnalysis(symbol, '1h,4h,1d', userId);
      
      if (result.success) {
        const pipelineData = extractPipelineData(result);
        // Update multiple state variables with comprehensive asset data
        const assetData = pipelineData.marketAnalysis[symbol] || {};
        
        setTechnicalAnalysis(prev => ({
          ...prev,
          [symbol]: {
            symbol,
            trend: pipelineData.aiConsensus.trend_direction || 'neutral',
            rsi: assetData.technical_indicators?.rsi || 50,
            macd: {
              line: assetData.technical_indicators?.macd || 0,
              signal: assetData.technical_indicators?.macd_signal || 0,
              histogram: assetData.technical_indicators?.macd_histogram || 0
            },
            movingAverages: {
              sma20: assetData.technical_indicators?.sma_20 || 0,
              sma50: assetData.technical_indicators?.sma_50 || 0,
              ema12: assetData.technical_indicators?.ema_12 || 0,
              ema26: assetData.technical_indicators?.ema_26 || 0
            },
            support: assetData.support_levels?.[0] || 0,
            resistance: assetData.resistance_levels?.[0] || 0,
            recommendation: pipelineData.aiConsensus.recommendation || 'hold',
            confidence: pipelineData.aiConsensus.confidence_score || 0.5,
            ai_consensus_score: pipelineData.aiConsensus.consensus_score || 0.5,
            pipeline_source: true,
            timestamp: result.last_updated
          }
        }));
      } else {
        throw new Error('Pipeline failed to fetch asset analysis');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch pipeline asset analysis');
    } finally {
      setLoading(false);
    }
  };

  const startAutonomousMode = async (config: Record<string, any> = {}): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.startAutonomousMode(config);
      if (result.success) {
        setAutonomousStatus({ ...result, active: true });
      } else {
        throw new Error('Failed to start autonomous mode');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to start autonomous mode');
    } finally {
      setLoading(false);
    }
  };

  const stopAutonomousMode = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.stopAutonomousMode();
      if (result.success) {
        setAutonomousStatus({ ...result, active: false });
      } else {
        throw new Error('Failed to stop autonomous mode');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to stop autonomous mode');
    } finally {
      setLoading(false);
    }
  };

  const fetchAutonomousStatus = async (): Promise<void> => {
    try {
      const result = await pipelineApi.getAutonomousStatus();
      if (result.success) {
        setAutonomousStatus(result.data || result);
      }
    } catch (err: any) {
      // Don't set error for status checks
      console.warn('Failed to fetch autonomous status:', err.message);
    }
  };

  const fetchSystemMetrics = async (): Promise<void> => {
    try {
      const result = await pipelineApi.getSystemMetrics();
      if (result.success) {
        setSystemMetrics(result.data || result);
      }
    } catch (err: any) {
      console.warn('Failed to fetch system metrics:', err.message);
    }
  };

  const fetchPipelineHistory = async (limit: number = 50): Promise<void> => {
    try {
      const result = await pipelineApi.getPipelineHistory(limit);
      if (result.success) {
        setPipelineHistory(result.data?.history || result.history || []);
      }
    } catch (err: any) {
      console.warn('Failed to fetch pipeline history:', err.message);
    }
  };

  const refreshAll = async (): Promise<void> => {
    // Guard against concurrent refresh calls
    if (isRefreshingRef.current) {
      return;
    }
    
    isRefreshingRef.current = true;
    setLoading(true);
    
    try {
      // Use Promise.allSettled to handle individual failures gracefully
      const results = await Promise.allSettled([
        fetchMarketOverview(),
        fetchTechnicalAnalysis(['BTC', 'ETH', 'SOL', 'AVAX']),
        fetchArbitrageData(),
        fetchAutonomousStatus(),
        fetchSystemMetrics()
      ]);
      
      // Log any failed operations
      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          const operations = ['market overview', 'technical analysis', 'arbitrage data', 'autonomous status', 'system metrics'];
          console.warn(`Failed to fetch ${operations[index]}:`, result.reason);
        }
      });
      
    } catch (error: any) {
      console.error('Refresh all failed:', error);
      setError(`Refresh failed: ${error.message}`);
    } finally {
      setLoading(false);
      isRefreshingRef.current = false;
    }
  };

  const clearError = (): void => {
    setError(null);
  };

  // Initialize pipeline data on mount
  useEffect(() => {
    // Clear any existing interval first
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    refreshAll();
    
    // Set up polling for pipeline updates (less frequent than direct API)
    intervalRef.current = setInterval(() => {
      // Guard against stale closure issues
      if (!isRefreshingRef.current) {
        refreshAll();
      }
    }, 120000); // Update every 2 minutes (pipeline coordination)
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [userId]);

  return {
    marketOverview,
    technicalAnalysis,
    arbitrageOpportunities,
    supportResistanceData,
    institutionalFlows,
    alphaSignals,
    trendingCoins,
    marketHealth,
    realtimePrices,
    sentimentAnalysis,
    volatilityData,
    autonomousStatus,
    systemMetrics,
    pipelineHistory,
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
    fetchRealtimePrices,
    fetchSentimentAnalysis,
    fetchVolatilityAnalysis,
    fetchTradingOpportunities,
    fetchAssetAnalysis,
    startAutonomousMode,
    stopAutonomousMode,
    fetchAutonomousStatus,
    fetchSystemMetrics,
    fetchPipelineHistory,
    refreshAll,
    clearError
  };
};