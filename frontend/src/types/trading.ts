/**
 * Trading TypeScript Type Definitions
 */

import { ExecutionPhase, TradeProposal } from '@/constants/trading';

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp?: string;
}

// Chat Statistics
export interface ChatStats {
  totalConversations: number;
  todayConversations: number;
  avgResponseTime: number;
  successfulTrades: number;
  portfolioOptimizations: number;
  riskAssessments: number;
  totalProfit: number;
  aiAccuracy: number;
}

// Recent Action
export interface RecentAction {
  id: number | string;
  type: 'trade_execution' | 'portfolio_rebalance' | 'risk_assessment' | 'opportunity_discovery';
  action: string;
  amount: number;
  timestamp: string;
  status: 'completed' | 'pending' | 'failed';
  profit?: number;
}

// Paper Trading Statistics
export interface PaperTradingStats {
  totalTrades: number;
  winRate: number;
  totalProfit: number;
  bestTrade: number;
  worstTrade: number;
  readyForLive: boolean;
  startDate?: string;
  lastTradeDate?: string;
}

// User Preferences
export interface UserPreferences {
  paper_trading_enabled: boolean;
  default_personality: string;
  risk_tolerance: 'low' | 'medium' | 'high' | 'very_high';
  notification_preferences: {
    email: boolean;
    telegram: boolean;
    push: boolean;
  };
  trading_limits: {
    max_daily_trades: number;
    max_position_size: number;
    max_daily_loss: number;
  };
}

// Trade Execution Request
export interface TradeExecutionRequest {
  action: 'buy' | 'sell';
  symbol: string;
  amount: number;
  price?: number;
  order_type: 'market' | 'limit';
  stop_loss?: number;
  take_profit?: number;
  metadata?: Record<string, any>;
}

// Action Type Union
export type ActionType = 'buy' | 'sell' | 'hold';

// Trade Execution Response DTO (from API)
export interface TradeExecutionResponseDTO {
  success: boolean;
  trade_id: string;
  action: ActionType;
  symbol: string;
  amount: number;
  price: number;
  fees: number;
  timestamp: string;
  status: 'executed' | 'pending' | 'failed';
  error?: string;
}

// Trade Execution Response (frontend)
export interface TradeExecutionResponse {
  success: boolean;
  tradeId: string;
  action: ActionType;
  symbol: string;
  amount: number;
  price: number;
  fees: number;
  timestamp: string;
  status: 'executed' | 'pending' | 'failed';
  error?: string;
}

// Position DTO (from API)
export interface PositionDTO {
  id: string;
  symbol: string;
  amount: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  opened_at: string;
  stop_loss?: number;
  take_profit?: number;
}

// Position (frontend)
export interface Position {
  id: string;
  symbol: string;
  amount: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercentage: number;
  openedAt: string;
  stopLoss?: number;
  takeProfit?: number;
}

// Market Data DTO (from API)
export interface MarketDataDTO {
  symbol: string;
  price: number;
  change_24h: number;
  change_percentage_24h: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  market_cap?: number;
  last_updated: string;
}

// Market Data (frontend)
export interface MarketData {
  symbol: string;
  price: number;
  change24h: number;
  changePercentage24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  marketCap?: number;
  lastUpdated: string;
}

// Market Opportunity DTO (from API)
export interface MarketOpportunityDTO {
  id: string;
  type: 'arbitrage' | 'trend' | 'breakout' | 'reversal';
  symbol: string;
  confidence: number;
  expected_profit: number;
  risk_level: 'low' | 'medium' | 'high';
  time_window: string;
  description: string;
  signals: string[];
}

// Market Opportunity (frontend)
export interface MarketOpportunity {
  id: string;
  type: 'arbitrage' | 'trend' | 'breakout' | 'reversal';
  symbol: string;
  confidence: number;
  expectedProfit: number;
  riskLevel: 'low' | 'medium' | 'high';
  timeWindow: string;
  description: string;
  signals: string[];
}

// AI Consensus Result DTO (from API)
export interface AIConsensusResultDTO {
  consensus: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  confidence: number;
  models: {
    gpt4: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
    claude: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
    gemini: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
  };
  weighted_score: number;
  risk_assessment: string;
  recommended_position_size: number;
}

// AI Consensus Result (frontend)
export interface AIConsensusResult {
  consensus: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  confidence: number;
  models: {
    gpt4: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
    claude: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
    gemini: {
      recommendation: string;
      confidence: number;
      reasoning: string;
    };
  };
  weightedScore: number;
  riskAssessment: string;
  recommendedPositionSize: number;
}

// WebSocket Message Types - normalized with server events
export type WSMessageType = 
  | 'connect'
  | 'disconnect' 
  | 'error'
  | 'chat_message'
  | 'chat_response'
  | 'phase_update'
  | 'trade_proposal'
  | 'trade_executed'
  | 'trade_failed'
  | 'price_update'
  | 'market_alert'
  | 'system_status'
  | 'emergency_stop'
  | 'user_message'
  | 'execute_trade'
  | 'config_update'
  | 'ai_response'
  | 'execution_result';

// WebSocket Message - Discriminated Union
export type WSMessage = 
  | { type: 'phase_update'; phase: ExecutionPhase; details: string; timestamp: string; id?: string; }
  | { type: 'trade_proposal'; proposal: TradeProposal; timestamp: string; id?: string; }
  | { type: 'ai_response' | 'chat_response'; content: string; metadata?: any; timestamp: string; id?: string; }
  | { type: 'execution_result'; success: boolean; trade_id?: string; action?: string; symbol?: string; amount?: number; price?: number; error?: string; timestamp: string; id?: string; }
  | { type: 'price_update'; symbol: string; price: number; change?: number; timestamp: string; id?: string; }
  | { type: 'system_status'; status: 'healthy' | 'degraded' | 'down'; services?: Record<string, boolean>; timestamp: string; id?: string; }
  | { type: 'market_alert'; symbol: string; alertType: string; message: string; timestamp: string; id?: string; }
  | { type: 'user_message' | 'execute_trade' | 'config_update'; [key: string]: any; timestamp: string; id?: string; };

// Phase Update Event
export interface PhaseUpdateEvent {
  phase: ExecutionPhase;
  details: string;
  progress: number;
  metrics?: {
    timeSpent: number;
    decisionsMade: number;
    confidence: number;
  };
}

// Trade Proposal Event
export interface TradeProposalEvent {
  proposal: {
    id: string;
    action: 'buy' | 'sell';
    symbol: string;
    amount: number;
    price: number;
    confidence: number;
    reasoning: string[];
    risks: string[];
    expectedProfit: number;
    stopLoss?: number;
    takeProfit?: number;
  };
}

// System Status
export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'down';
  services: {
    api: boolean;
    websocket: boolean;
    database: boolean;
    redis: boolean;
    ai_consensus: boolean;
    exchanges: boolean;
  };
  latency: {
    api: number;
    database: number;
    redis: number;
  };
  uptime: number;
  version: string;
}

// Trust Score Details
export interface TrustScoreDetails {
  score: number;
  level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  total_trades: number;
  successful_trades: number;
  total_profit: number;
  risk_management_score: number;
  consistency_score: number;
  position_limit: number;
  next_milestone: {
    score: number;
    trades_needed: number;
    profit_needed: number;
  };
}

// Strategy
export interface Strategy {
  id: string;
  name: string;
  description: string;
  category: 'trend_following' | 'mean_reversion' | 'arbitrage' | 'momentum' | 'ai_driven';
  performance: {
    win_rate: number;
    avg_profit: number;
    total_trades: number;
    sharpe_ratio: number;
  };
  risk_level: 'low' | 'medium' | 'high';
  credit_cost: number;
  is_active: boolean;
  created_by: 'system' | 'community';
  publisher?: {
    id: string;
    name: string;
    reputation: number;
  };
}

// Credit Transaction
export interface CreditTransaction {
  id: string;
  type: 'purchase' | 'earning' | 'spending' | 'refund';
  amount: number;
  balance_after: number;
  description: string;
  related_entity?: {
    type: 'trade' | 'strategy' | 'subscription';
    id: string;
  };
  timestamp: string;
}

// Notification
export interface Notification {
  id: string;
  type: 'trade' | 'alert' | 'system' | 'achievement';
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  read: boolean;
  timestamp: string;
  action?: {
    label: string;
    url: string;
  };
}

// Portfolio Summary
export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percentage: number;
  positions: Position[];
  allocation: {
    symbol: string;
    percentage: number;
    value: number;
  }[];
  performance: {
    day: number;
    week: number;
    month: number;
    year: number;
    all_time: number;
  };
}

// Error Response
export interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
  timestamp: string;
  request_id?: string;
}