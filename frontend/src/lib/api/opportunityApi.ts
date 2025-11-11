import { AxiosResponse } from 'axios';
import { apiClient } from './client';

export type RiskLevel = 'low' | 'medium' | 'high' | 'very_high' | string;

export interface Opportunity {
  strategy_id: string;
  strategy_name: string;
  opportunity_type: string;
  symbol: string;
  exchange: string;
  profit_potential_usd: number;
  confidence_score: number;
  risk_level: RiskLevel;
  required_capital_usd: number;
  estimated_timeframe: string;
  entry_price?: number | null;
  exit_price?: number | null;
  metadata?: Record<string, any> | null;
  discovered_at: string;
}

export interface OpportunityDiscoveryRequest {
  force_refresh?: boolean;
  include_strategy_recommendations?: boolean;
  filter_by_risk_level?: string | null;
  min_profit_potential?: number | null;
  max_required_capital?: number | null;
  preferred_timeframes?: string[];
  opportunity_type?: string[];
  strategy_types?: string[];
  symbols?: string[];
  asset_tiers?: string[];
  strategy_ids?: string[];
}

export interface OpportunityScanProgress {
  strategies_completed: number;
  total_strategies: number;
  opportunities_found_so_far: number;
  percentage?: number;
}

export interface OpportunityScanFilters {
  symbols?: string[];
  asset_tiers?: string[];
  strategy_ids?: string[];
}

export interface OpportunityScanInitiation {
  success: boolean;
  scan_id: string;
  status: 'initiated' | 'scanning' | 'complete' | 'failed' | 'not_found';
  message?: string;
  estimated_completion_seconds?: number;
  poll_url?: string;
  results_url?: string;
  polling_interval_seconds?: number;
  instructions?: string;
  progress?: OpportunityScanProgress;
  filters?: OpportunityScanFilters;
}

export interface OpportunityScanStatusResponse {
  success: boolean;
  status: 'not_found' | 'scanning' | 'complete' | 'failed';
  scan_id?: string;
  message?: string;
  progress?: OpportunityScanProgress;
  partial_results?: Opportunity[];
  estimated_time_remaining_seconds?: number;
  total_opportunities?: number;
  results_url?: string;
}

export interface OpportunityDiscoveryResponse {
  success: boolean;
  scan_id: string;
  user_id: string;
  opportunities: Opportunity[];
  total_opportunities: number;
  signal_analysis?: Record<string, any> | null;
  threshold_transparency?: Record<string, any> | null;
  user_profile: Record<string, any>;
  strategy_performance: Record<string, any>;
  asset_discovery: Record<string, any>;
  strategy_recommendations: Array<Record<string, any>>;
  execution_time_ms: number;
  last_updated: string;
  error?: string;
  fallback_used?: boolean;
}

export interface OpportunityUserStatus {
  success: boolean;
  user_id: string;
  onboarding_status: {
    onboarded: boolean;
    [key: string]: any;
  };
  last_scan_info?: {
    last_scan: string | null;
    time_since_last_scan: number | null;
    parse_error?: string;
  } | null;
  discovery_available: boolean;
  recommendations?: {
    next_action?: string;
    estimated_opportunities?: string;
    [key: string]: any;
  };
}

export interface OpportunityOnboardingResponse {
  success: boolean;
  onboarding_id: string;
  user_id: string;
  results: Record<string, any>;
  execution_time_ms: number;
  onboarded_at: string;
  next_steps: string[];
}

export type OpportunityOnboardingParams = {
  referral_code?: string;
  welcome_package?: string;
};

export class OpportunityApiError extends Error {
  public code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = 'OpportunityApiError';
    this.code = code;
  }
}

const handleAxiosError = (error: any): never => {
  const message = error?.response?.data?.detail || error?.message || 'Opportunity API request failed';
  const code = error?.response?.status ? String(error.response.status) : undefined;
  throw new OpportunityApiError(message, code);
};

export const opportunityApi = {
  async discoverOpportunities(payload: OpportunityDiscoveryRequest = {}): Promise<OpportunityScanInitiation> {
    try {
      const response = await apiClient.post<OpportunityScanInitiation>('/opportunities/discover', payload);
      return response.data;
    } catch (error) {
      throw handleAxiosError(error);
    }
  },

  async getScanStatus(scanId: string): Promise<OpportunityScanStatusResponse> {
    try {
      const response = await apiClient.get<OpportunityScanStatusResponse>(`/opportunities/status/${scanId}`);
      return response.data;
    } catch (error) {
      throw handleAxiosError(error);
    }
  },

  async getScanResults(scanId: string): Promise<OpportunityDiscoveryResponse> {
    try {
      const response: AxiosResponse<OpportunityDiscoveryResponse> = await apiClient.get(`/opportunities/results/${scanId}`, {
        validateStatus: status => status >= 200 && status < 500,
      });

      if (response.status === 202) {
        throw new OpportunityApiError('Scan is still in progress. Please try again later.', 'SCAN_IN_PROGRESS');
      }

      if (response.status === 404) {
        throw new OpportunityApiError('No scan results found. Please initiate a new scan.', 'SCAN_NOT_FOUND');
      }

      if (response.status < 200 || response.status >= 300) {
        throw new OpportunityApiError('Unexpected response from opportunity results endpoint', String(response.status));
      }

      return response.data;
    } catch (error) {
      if (error instanceof OpportunityApiError) {
        throw error;
      }
      throw handleAxiosError(error);
    }
  },

  async getUserStatus(): Promise<OpportunityUserStatus> {
    try {
      const response = await apiClient.get<OpportunityUserStatus>('/opportunities/user-status');
      return response.data;
    } catch (error) {
      throw handleAxiosError(error);
    }
  },

  async triggerOnboarding(params: OpportunityOnboardingParams = {}): Promise<OpportunityOnboardingResponse> {
    try {
      const response = await apiClient.post<OpportunityOnboardingResponse>('/opportunities/onboard', null, {
        params,
      });
      return response.data;
    } catch (error) {
      throw handleAxiosError(error);
    }
  },
};
