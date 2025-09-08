/**
 * Shared Trading Constants
 * Centralized definitions to avoid duplication
 */

import {
  BarChart3,
  Brain,
  Shield,
  TrendingUp,
  Activity,
  MessageSquare,
  Clock,
  CheckCircle,
  LucideIcon
} from 'lucide-react';
import { ReactNode } from 'react';

// 5-Phase Execution Framework
export enum ExecutionPhase {
  IDLE = 'idle',
  ANALYSIS = 'analysis',
  CONSENSUS = 'consensus',
  VALIDATION = 'validation',
  EXECUTION = 'execution',
  MONITORING = 'monitoring',
  COMPLETED = 'completed'
}

// AI Personality Modes
export enum AIPersonality {
  CONSERVATIVE = 'conservative',
  BALANCED = 'balanced',
  AGGRESSIVE = 'aggressive',
  DEGEN = 'degen'
}

// Trading Modes
export enum TradingMode {
  PAPER = 'paper',
  LIVE = 'live'
}

// Trading Actions
export enum TradeAction {
  BUY = 'buy',
  SELL = 'sell',
  HOLD = 'hold'
}

// Chat Message Types
export enum MessageType {
  USER = 'user',
  AI = 'ai',
  SYSTEM = 'system',
  PHASE = 'phase',
  TRADE = 'trade',
  TRADE_NOTIFICATION = 'trade_notification',
  PORTFOLIO_UPDATE = 'portfolio_update',
  MARKET_ALERT = 'market_alert'
}

// Intent Types
export enum ChatIntent {
  GENERAL_QUERY = 'general_query',
  TRADE_EXECUTION = 'trade_execution',
  PORTFOLIO_ANALYSIS = 'portfolio_analysis',
  RISK_ASSESSMENT = 'risk_assessment',
  MARKET_OPPORTUNITY = 'market_opportunity',
  REBALANCING = 'rebalancing',
  EMERGENCY_COMMAND = 'emergency_command'
}

export interface PhaseMetrics {
  timeSpent: number; // seconds
  decisionsMade: number;
  confidence: number;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
}

export interface PhaseData {
  phase: ExecutionPhase;
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
  details?: string[];
  metrics?: PhaseMetrics;
  canOverride?: boolean;
  progress: number;
}

export interface TradeProposal {
  id: string;
  action: TradeAction;
  symbol: string;
  amount: number;
  price: number;
  confidence: number;
  reasoning: string[];
  risks: string[];
  expectedProfit: number;
  stopLoss?: number;
  takeProfit?: number;
  phase: ExecutionPhase;
  timestamp?: string;
}

export interface ConversationMemory {
  sessionId: string;
  context: Record<string, any>;
  preferences: Record<string, any>;
  lastActivity: string;
  trustScore: number;
  tradingHistory?: TradeProposal[];
  totalProfit?: number;
}

export interface ChatMessage {
  id: string;
  content: string;
  type: MessageType;
  timestamp: string;
  phase?: ExecutionPhase;
  tradeProposal?: TradeProposal;
  intent?: ChatIntent;
  confidence?: number;
  metadata?: Record<string, any>;
}

export interface PersonalityConfig {
  name: string;
  description: string;
  emoji: string;
  color: string;
  riskLevel: 'Low' | 'Medium' | 'High' | 'Very High';
  dailyTargetPct: number;
  maxDrawdownPct: number;
  maxLeverage: number;
  maxPositionPct: number;
}

// Phase Configuration with Icons
export const PHASE_CONFIG: Record<ExecutionPhase, Omit<PhaseData, 'metrics'>> = {
  [ExecutionPhase.IDLE]: {
    phase: ExecutionPhase.IDLE,
    title: 'Ready',
    description: 'System idle, waiting for instructions',
    icon: Clock,
    color: 'text-gray-500',
    progress: 0
  },
  [ExecutionPhase.ANALYSIS]: {
    phase: ExecutionPhase.ANALYSIS,
    title: 'Market Analysis',
    description: 'Scanning markets, identifying patterns and opportunities',
    icon: BarChart3,
    color: 'text-blue-500',
    progress: 20,
    details: [
      'Technical indicators analysis',
      'Volume and liquidity assessment',
      'Cross-exchange price comparison',
      'Sentiment analysis'
    ],
    canOverride: true
  },
  [ExecutionPhase.CONSENSUS]: {
    phase: ExecutionPhase.CONSENSUS,
    title: 'AI Consensus',
    description: 'Multiple AI models evaluating the opportunity',
    icon: Brain,
    color: 'text-purple-500',
    progress: 40,
    details: [
      'GPT-4 analysis and scoring',
      'Claude evaluation and reasoning',
      'Gemini market assessment',
      'Weighted consensus calculation'
    ],
    canOverride: false
  },
  [ExecutionPhase.VALIDATION]: {
    phase: ExecutionPhase.VALIDATION,
    title: 'Risk Validation',
    description: 'Checking risk parameters and position sizing',
    icon: Shield,
    color: 'text-yellow-500',
    progress: 60,
    details: [
      'Portfolio exposure limits',
      'Risk/reward ratio validation',
      'Stop-loss and take-profit levels',
      'Circuit breaker checks'
    ],
    canOverride: true
  },
  [ExecutionPhase.EXECUTION]: {
    phase: ExecutionPhase.EXECUTION,
    title: 'Trade Execution',
    description: 'Placing and managing orders on exchanges',
    icon: TrendingUp,
    color: 'text-green-500',
    progress: 80,
    details: [
      'Order placement',
      'Slippage minimization',
      'Smart order routing',
      'Execution confirmation'
    ],
    canOverride: false
  },
  [ExecutionPhase.MONITORING]: {
    phase: ExecutionPhase.MONITORING,
    title: 'Position Monitoring',
    description: 'Tracking performance and managing position',
    icon: Activity,
    color: 'text-indigo-500',
    progress: 100,
    details: [
      'Real-time P&L tracking',
      'Market condition monitoring',
      'Stop-loss/take-profit management',
      'Exit strategy optimization'
    ],
    canOverride: true
  },
  [ExecutionPhase.COMPLETED]: {
    phase: ExecutionPhase.COMPLETED,
    title: 'Completed',
    description: 'Trade cycle completed successfully',
    icon: CheckCircle,
    color: 'text-green-600',
    progress: 100
  }
};

// AI Personality Configuration
export const PERSONALITY_CONFIG: Record<AIPersonality, PersonalityConfig> = {
  [AIPersonality.CONSERVATIVE]: {
    name: 'Conservative Carl',
    description: 'Protects capital first, slow and steady',
    emoji: '🛡️',
    color: 'text-blue-500',
    riskLevel: 'Low',
    dailyTargetPct: 0.5,
    maxDrawdownPct: 5,
    maxLeverage: 1,
    maxPositionPct: 10
  },
  [AIPersonality.BALANCED]: {
    name: 'Balanced Beth',
    description: 'Steady growth with managed risk',
    emoji: '⚖️',
    color: 'text-green-500',
    riskLevel: 'Medium',
    dailyTargetPct: 1.5,
    maxDrawdownPct: 10,
    maxLeverage: 2,
    maxPositionPct: 20
  },
  [AIPersonality.AGGRESSIVE]: {
    name: 'Aggressive Alex',
    description: 'Maximum gains, higher risk tolerance',
    emoji: '🚀',
    color: 'text-orange-500',
    riskLevel: 'High',
    dailyTargetPct: 3,
    maxDrawdownPct: 20,
    maxLeverage: 5,
    maxPositionPct: 30
  },
  [AIPersonality.DEGEN]: {
    name: 'Degen Mode',
    description: 'YOLO with guardrails',
    emoji: '🎲',
    color: 'text-red-500',
    riskLevel: 'Very High',
    dailyTargetPct: 5,
    maxDrawdownPct: 30,
    maxLeverage: 10,
    maxPositionPct: 50
  }
};

// Trading Phase Order
export const PHASE_ORDER: ExecutionPhase[] = [
  ExecutionPhase.ANALYSIS,
  ExecutionPhase.CONSENSUS,
  ExecutionPhase.VALIDATION,
  ExecutionPhase.EXECUTION,
  ExecutionPhase.MONITORING
];

// API Endpoints
export const API_ENDPOINTS = {
  // Chat Endpoints
  CHAT_SESSION: '/api/v1/chat/session/new',
  CHAT_MESSAGE: '/api/v1/chat/message',
  CHAT_HISTORY: '/api/v1/chat/history',
  CHAT_STATS: '/api/v1/chat/stats',
  CHAT_RECENT_ACTIONS: '/api/v1/chat/recent-actions',
  
  // Trading Endpoints
  TRADE_EXECUTE: '/api/v1/trading/execute',
  TRADE_HISTORY: '/api/v1/trading/history',
  TRADE_POSITIONS: '/api/v1/trading/positions',
  
  // Paper Trading Endpoints
  PAPER_TRADING_EXECUTE: '/api/v1/paper-trading/execute',
  PAPER_TRADING_STATS: '/api/v1/paper-trading/stats',
  PAPER_TRADING_HISTORY: '/api/v1/paper-trading/history',
  
  // User Preferences
  USER_PREFERENCES: '/api/v1/user/preferences',
  USER_TRUST_SCORE: '/api/v1/user/trust-score',
  
  // Market Data
  MARKET_PRICES: '/api/v1/market/realtime-prices',
  MARKET_OPPORTUNITIES: '/api/v1/market/opportunities',
  
  // AI Consensus
  AI_CONSENSUS: '/api/v1/ai-consensus/analyze',
  AI_CONSENSUS_STATUS: '/api/v1/ai-consensus/status'
};

// WebSocket Events
export const WS_EVENTS = {
  // Connection Events
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  
  // Chat Events
  CHAT_MESSAGE: 'chat_message',
  CHAT_RESPONSE: 'chat_response',
  
  // Trading Events
  PHASE_UPDATE: 'phase_update',
  TRADE_PROPOSAL: 'trade_proposal',
  TRADE_EXECUTED: 'trade_executed',
  TRADE_FAILED: 'trade_failed',
  
  // Market Events
  PRICE_UPDATE: 'price_update',
  MARKET_ALERT: 'market_alert',
  
  // System Events
  SYSTEM_STATUS: 'system_status',
  EMERGENCY_STOP: 'emergency_stop'
};

// Trust Score Thresholds
export const TRUST_THRESHOLDS = {
  BEGINNER: 0,
  INTERMEDIATE: 30,
  ADVANCED: 60,
  EXPERT: 90
};

// Position Limits by Trust Score
export const POSITION_LIMITS = {
  [TRUST_THRESHOLDS.BEGINNER]: 100,
  [TRUST_THRESHOLDS.INTERMEDIATE]: 1000,
  [TRUST_THRESHOLDS.ADVANCED]: 10000,
  [TRUST_THRESHOLDS.EXPERT]: 100000
};

// Time Constants
export const TIMEOUTS = {
  API_REQUEST: 30000, // 30 seconds
  WS_RECONNECT: 5000, // 5 seconds
  PHASE_TIMEOUT: 60000, // 1 minute per phase
  TRADE_CONFIRMATION: 30000 // 30 seconds to confirm trade
};

// Validation Rules
export const VALIDATION = {
  MIN_TRADE_AMOUNT: 10,
  MAX_TRADE_AMOUNT: 1000000,
  MIN_CONFIDENCE: 0.6,
  MAX_SLIPPAGE: 0.02,
  MAX_DAILY_TRADES: 100
};