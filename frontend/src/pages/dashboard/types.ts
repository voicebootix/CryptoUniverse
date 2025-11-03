import type { AIModelResponse } from '@/components/trading/AIConsensusCard';

export interface ConsensusData {
  consensus_score: number;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  confidence_threshold_met: boolean;
  model_responses: AIModelResponse[];
  cost_summary?: {
    total_cost: number;
    breakdown?: Record<string, number>;
  };
  reasoning?: string;
  timestamp?: string;
}

export interface MarketContext {
  symbols: string[];
  trend: 'bullish' | 'bearish' | 'neutral';
  sentiment: 'positive' | 'negative' | 'neutral';
  avgChange: number;
  topGainers?: Array<{
    symbol: string;
    change?: number;
    price?: number;
    volume?: number | string;
  }>;
  topLosers?: Array<{
    symbol: string;
    change?: number;
    price?: number;
    volume?: number | string;
  }>;
}

export interface AIPricingConfig {
  opportunity_scan_cost: number;
  validation_cost: number;
  execution_cost: number;
  per_call_estimate: number;
}
