import { create } from 'zustand';
import { apiClient } from '@/lib/api/client';

interface RiskMetricsSnapshot {
  var95: number;
  var95Percent: number;
  var99: number;
  var99Percent: number;
  expectedShortfall: number;
  expectedShortfallPercent: number;
  volatilityAnnual: number;
  volatilityPercent: number;
  sharpeRatio: number;
  sortinoRatio: number;
  beta: number;
  alpha: number;
  correlationToMarket: number;
  maximumDrawdown: number;
  maximumDrawdownPercent: number;
}

export interface PositionSizingPayload {
  symbol: string;
  expectedReturn: number;
  confidence: number;
  mode: string;
  stopLossPct?: number;
  takeProfitPct?: number;
}

export interface PositionSizingResult {
  symbol?: string;
  recommended_size?: number;
  position_value_usd?: number;
  kelly_size?: number;
  mode_adjusted_size?: number;
  risk_adjusted_size?: number;
  trading_mode?: string;
  confidence_used?: number;
  expected_return_used?: number;
  risk_metrics?: Record<string, any>;
  constraints_applied?: Record<string, any>;
  execution_guidance?: Record<string, any>;
  [key: string]: any;
}

export interface EmergencyPolicy {
  level: string;
  loss_threshold_pct: number;
  default_loss_threshold_pct: number;
  action: string;
  reduction_pct: number;
  halt_new_trades: boolean;
  description: string;
}

export interface EmergencyPolicyState {
  opt_in: boolean;
  policies: EmergencyPolicy[];
  last_updated: string | null;
}

export interface EmergencyPolicyUpdatePayload {
  optIn?: boolean;
  thresholds?: Partial<Record<'warning' | 'critical' | 'emergency', number>>;
}

interface PositionSizingState {
  result: PositionSizingResult | null;
  guidelines: string[];
  riskControls: Record<string, any> | null;
}

interface RiskDashboardState {
  loading: boolean;
  error: string | null;
  metrics: RiskMetricsSnapshot | null;
  guidelines: string[];
  riskAlerts: Record<string, any>[];
  portfolioValue: number;
  analysisParameters: Record<string, any> | null;
  lastUpdated: string | null;
  positionSizing: PositionSizingState;
  positionSizingLoading: boolean;
  emergencyPolicies: EmergencyPolicyState | null;
  policiesUpdating: boolean;
  fetchDashboard: () => Promise<void>;
  computePositionSizing: (payload: PositionSizingPayload) => Promise<void>;
  fetchEmergencyPolicies: () => Promise<void>;
  updateEmergencyPolicies: (payload: EmergencyPolicyUpdatePayload) => Promise<void>;
  clearError: () => void;
}

const fallbackGuidelines = [
  'Limit any single asset to 10% or less of total trading capital.',
  'Always attach stop-loss orders at or tighter than the recommended threshold.',
  'Target a minimum 2:1 reward-to-risk ratio before entering new positions.',
  'Reduce leverage when portfolio volatility spikes.',
];

const parseError = (error: any): string => {
  if (error?.response?.data?.detail) {
    return error.response.data.detail as string;
  }
  if (error?.message) {
    return error.message as string;
  }
  return 'Unexpected error while processing risk request.';
};

const mapMetrics = (metrics: Record<string, any> | null | undefined): RiskMetricsSnapshot | null => {
  if (!metrics) {
    return null;
  }

  return {
    var95: Number(metrics.var_95 ?? 0),
    var95Percent: Number(metrics.var_95_percent ?? 0),
    var99: Number(metrics.var_99 ?? 0),
    var99Percent: Number(metrics.var_99_percent ?? 0),
    expectedShortfall: Number(metrics.expected_shortfall ?? 0),
    expectedShortfallPercent: Number(metrics.expected_shortfall_percent ?? 0),
    volatilityAnnual: Number(metrics.volatility_annual ?? 0),
    volatilityPercent: Number(metrics.volatility_percent ?? 0),
    sharpeRatio: Number(metrics.sharpe_ratio ?? 0),
    sortinoRatio: Number(metrics.sortino_ratio ?? 0),
    beta: Number(metrics.beta ?? 0),
    alpha: Number(metrics.alpha ?? 0),
    correlationToMarket: Number(metrics.correlation_to_market ?? 0),
    maximumDrawdown: Number(metrics.maximum_drawdown ?? 0),
    maximumDrawdownPercent: Number(metrics.maximum_drawdown_percent ?? 0),
  };
};

export const useRiskDashboard = create<RiskDashboardState>((set, get) => ({
  loading: false,
  error: null,
  metrics: null,
  guidelines: fallbackGuidelines,
  riskAlerts: [],
  portfolioValue: 0,
  analysisParameters: null,
  lastUpdated: null,
  positionSizing: {
    result: null,
    guidelines: [],
    riskControls: null,
  },
  positionSizingLoading: false,
  emergencyPolicies: null,
  policiesUpdating: false,

  fetchDashboard: async () => {
    set({ loading: true, error: null });

    try {
      const response = await apiClient.get('/risk/dashboard');
      const data = response.data ?? {};

      set({
        loading: false,
        metrics: mapMetrics(data.metrics),
        guidelines: Array.isArray(data.guidelines) && data.guidelines.length > 0 ? data.guidelines : fallbackGuidelines,
        riskAlerts: Array.isArray(data.risk_alerts) ? data.risk_alerts : [],
        portfolioValue: Number(data.portfolio_value ?? 0),
        analysisParameters: data.analysis_parameters ?? null,
        lastUpdated: data.last_updated ?? null,
        emergencyPolicies: data.emergency_policies ?? null,
      });
    } catch (error: any) {
      set({ loading: false, error: parseError(error) });
    }
  },

  computePositionSizing: async (payload: PositionSizingPayload) => {
    set({ positionSizingLoading: true, error: null });

    try {
      const response = await apiClient.post('/risk/position-sizing', {
        symbol: payload.symbol,
        expected_return: payload.expectedReturn,
        confidence: payload.confidence,
        mode: payload.mode,
        stop_loss_pct: payload.stopLossPct,
        take_profit_pct: payload.takeProfitPct,
      });

      const data = response.data ?? {};

      set({
        positionSizingLoading: false,
        positionSizing: {
          result: data.position_sizing ?? null,
          guidelines: Array.isArray(data.guidelines) ? data.guidelines : [],
          riskControls: data.risk_controls ?? null,
        },
      });
    } catch (error: any) {
      set({ positionSizingLoading: false, error: parseError(error) });
    }
  },

  fetchEmergencyPolicies: async () => {
    // Avoid redundant network requests if dashboard already loaded policies recently
    if (get().emergencyPolicies) {
      return;
    }

    try {
      const response = await apiClient.get('/risk/emergency-policies');
      const data = response.data ?? {};
      set({ emergencyPolicies: {
        opt_in: Boolean(data.opt_in),
        policies: Array.isArray(data.policies) ? data.policies : [],
        last_updated: data.last_updated ?? null,
      } });
    } catch (error: any) {
      set({ error: parseError(error) });
    }
  },

  updateEmergencyPolicies: async (payload: EmergencyPolicyUpdatePayload) => {
    set({ policiesUpdating: true, error: null });

    try {
      const response = await apiClient.post('/risk/emergency-policies', {
        opt_in: payload.optIn,
        thresholds: payload.thresholds,
      });

      const data = response.data ?? {};
      set({
        policiesUpdating: false,
        emergencyPolicies: {
          opt_in: Boolean(data.opt_in),
          policies: Array.isArray(data.policies) ? data.policies : [],
          last_updated: data.last_updated ?? null,
        },
      });
    } catch (error: any) {
      set({ policiesUpdating: false, error: parseError(error) });
    }
  },

  clearError: () => set({ error: null }),
}));
