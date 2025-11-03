export interface OpportunityValidation {
  approved: boolean;
  consensus_score: number;
  confidence: number;
  reason?: string;
  model_responses?: Array<{
    model: string;
    recommendation: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
  }>;
  risk_assessment?: {
    level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    max_loss: number;
    max_loss_percent: number;
  };
}

export interface Opportunity {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  strategy: string;
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  suggested_position_size: number;
  position_size_percent: number;
  max_risk: number;
  max_risk_percent: number;
  potential_gain: number;
  potential_gain_percent: number;
  risk_reward_ratio: number;
  timeframe: string;
  reasoning?: string;
  indicators?: Record<string, any>;
  timestamp: string;
  expires_at: string; // Opportunities expire after 5 minutes
  aiValidated: boolean;
  validation?: OpportunityValidation;
  validationReason?: string;
}

export interface OpportunitiesData {
  validated: Opportunity[];
  nonValidated: Opportunity[];
  totalCount: number;
  validatedCount: number;
  scanCost: number;
  executionCostPerTrade: number;
}

export interface OpportunitiesDrawerState {
  open: boolean;
  data: OpportunitiesData | null;
  executing: Set<string>; // Track which opportunities are being executed
  validating: Set<string>; // Track which opportunities are being validated
}

export type OpportunityFilter = 'all' | 'validated' | 'high' | 'medium' | 'low';
export type OpportunitySort = 'confidence' | 'potential_gain' | 'risk_reward';
