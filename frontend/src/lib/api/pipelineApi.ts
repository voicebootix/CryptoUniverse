import { apiClient } from './client';

// Pipeline API Client for 5-Phase System Integration
// Replaces direct market analysis calls with coordinated pipeline triggers

export interface PipelineResult {
  success: boolean;
  pipeline_id: string;
  pipeline_results: {
    market_analysis: Record<string, any>;
    trading_strategies: Record<string, any>;
    portfolio_risk: Record<string, any>;
    ai_consensus: Record<string, any>;
    trade_execution: Record<string, any>;
  };
  execution_time: number;
  phase_timings: Record<string, number>;
  last_updated: string;
}

export interface PipelineTriggerOptions {
  analysis_type: string;
  symbols: string;
  timeframes?: string;
  user_id: string;
  risk_tolerance?: string;
  exchanges?: string;
  depth?: string;
  [key: string]: any;
}

// Master Controller Pipeline API
export const pipelineApi = {
  // Trigger comprehensive pipeline analysis
  async triggerPipeline(options: PipelineTriggerOptions): Promise<PipelineResult> {
    try {
      const response = await apiClient.post('/master-controller/trigger-pipeline', options);
      return response.data;
    } catch (error: any) {
      console.error('Pipeline trigger failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Pipeline request failed';
      const statusCode = error?.response?.status;
      throw new Error(`Pipeline API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  },

  // Get real-time prices via pipeline
  async getRealtimePrices(symbols: string, exchanges: string = 'all', user_id: string = 'frontend'): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'price_tracking',
      symbols,
      exchanges,
      user_id
    });
  },

  // Get technical analysis via pipeline
  async getTechnicalAnalysis(
    symbols: string, 
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'technical_analysis',
      symbols,
      timeframes,
      user_id
    });
  },

  // Get market sentiment via pipeline
  async getSentimentAnalysis(
    symbols: string, 
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'sentiment_analysis',
      symbols,
      timeframes,
      user_id
    });
  },

  // Get arbitrage opportunities via pipeline
  async getArbitrageOpportunities(
    symbols: string = 'BTC,ETH,SOL',
    exchanges: string = 'all',
    min_profit_bps: number = 5,
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'arbitrage_opportunities',
      symbols,
      exchanges,
      min_profit_bps,
      user_id
    });
  },

  // Get complete market assessment via pipeline
  async getCompleteMarketAssessment(
    symbols: string,
    depth: string = 'comprehensive',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'complete_assessment',
      symbols,
      depth,
      user_id
    });
  },

  // Get volatility analysis via pipeline
  async getVolatilityAnalysis(
    symbols: string,
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'volatility_analysis',
      symbols,
      timeframes,
      user_id
    });
  },

  // Get support and resistance via pipeline
  async getSupportResistance(
    symbols: string,
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'support_resistance',
      symbols,
      timeframes,
      user_id
    });
  },

  // Get institutional flows via pipeline
  async getInstitutionalFlows(
    symbols: string,
    timeframes: string = '1h,4h,1d',
    flow_types: string = 'whale_moves,institutional_trades,etf_flows',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'institutional_flows',
      symbols,
      timeframes,
      flow_types,
      user_id
    });
  },

  // Get alpha signals via pipeline
  async getAlphaSignals(
    symbols: string,
    strategies: string = 'momentum,mean_reversion,breakout',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'alpha_signals',
      symbols,
      strategies,
      user_id
    });
  },

  // Get market overview via pipeline
  async getMarketOverview(
    symbols: string = 'BTC,ETH,BNB,SOL,ADA,XRP,MATIC,DOT,AVAX,LINK',
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'market_overview',
      symbols,
      timeframes,
      user_id
    });
  },

  // Get trading opportunities via pipeline
  async getTradingOpportunities(
    symbols: string = 'BTC,ETH,SOL,MATIC,LINK,UNI,AVAX,DOT',
    risk_tolerance: string = 'balanced',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'opportunity_discovery',
      symbols,
      risk_tolerance,
      user_id
    });
  },

  // Get asset analysis via pipeline
  async getAssetAnalysis(
    symbol: string,
    timeframes: string = '1h,4h,1d',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'asset_analysis',
      symbols: symbol,
      timeframes,
      user_id
    });
  },

  // Get market inefficiencies via pipeline
  async getMarketInefficiencies(
    symbols: string = 'BTC,ETH,SOL',
    scan_types: string = 'spread,volume,time',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'market_inefficiencies',
      symbols,
      scan_types,
      user_id
    });
  },

  // Get cross-asset arbitrage via pipeline
  async getCrossAssetArbitrage(
    asset_pairs: string = 'BTC-ETH,ETH-BNB,BTC-SOL',
    exchanges: string = 'all',
    min_profit_bps: number = 5,
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'cross_asset_arbitrage',
      symbols: asset_pairs, // Add required symbols field
      asset_pairs,
      exchanges,
      min_profit_bps,
      user_id
    });
  },

  // Get spread monitoring via pipeline
  async getSpreadMonitoring(
    symbols: string = 'BTC,ETH,SOL',
    exchanges: string = 'all',
    user_id: string = 'frontend'
  ): Promise<PipelineResult> {
    return this.triggerPipeline({
      analysis_type: 'spread_monitoring',
      symbols,
      exchanges,
      user_id
    });
  },

  // Get autonomous mode status
  async getAutonomousStatus(): Promise<any> {
    try {
      const response = await apiClient.get('/master-controller/autonomous-status');
      return response.data;
    } catch (error: any) {
      console.error('Get autonomous status failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to get autonomous status';
      const statusCode = error?.response?.status;
      throw new Error(`Autonomous Status API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  },

  // Start autonomous mode
  async startAutonomousMode(config: Record<string, any> = {}): Promise<any> {
    try {
      const response = await apiClient.post('/master-controller/start-autonomous', config);
      return response.data;
    } catch (error: any) {
      console.error('Start autonomous mode failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to start autonomous mode';
      const statusCode = error?.response?.status;
      throw new Error(`Start Autonomous API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  },

  // Stop autonomous mode
  async stopAutonomousMode(): Promise<any> {
    try {
      const response = await apiClient.post('/master-controller/stop-autonomous');
      return response.data;
    } catch (error: any) {
      console.error('Stop autonomous mode failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to stop autonomous mode';
      const statusCode = error?.response?.status;
      throw new Error(`Stop Autonomous API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  },

  // Get pipeline execution history
  async getPipelineHistory(limit: number = 50): Promise<any> {
    try {
      const response = await apiClient.get('/master-controller/execution-history', {
        params: { limit }
      });
      return response.data;
    } catch (error: any) {
      console.error('Get pipeline history failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to get pipeline history';
      const statusCode = error?.response?.status;
      throw new Error(`Pipeline History API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  },

  // Get system performance metrics
  async getSystemMetrics(): Promise<any> {
    try {
      const response = await apiClient.get('/master-controller/system-metrics');
      return response.data;
    } catch (error: any) {
      console.error('Get system metrics failed:', error);
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to get system metrics';
      const statusCode = error?.response?.status;
      throw new Error(`System Metrics API Error${statusCode ? ` (${statusCode})` : ''}: ${errorMessage}`);
    }
  }
};

export default pipelineApi;