import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import { useToast } from '@/components/ui/use-toast';

const AI_ACRONYMS = new Set(['ai', 'ml', 'gpt', 'llm', 'nlp', 'mft']);
const STRATEGY_ID_HINTS = [
  'ai_',
  'spot_',
  'futures_',
  'options_',
  'risk_',
  'portfolio_',
  'hedge_',
  'pairs_',
  'scalping_',
  'statistical_',
  'strategy'
];

const looksLikeStrategyId = (value: unknown): boolean => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return true;
  }

  if (typeof value !== 'string') {
    return false;
  }

  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return false;
  }

  return STRATEGY_ID_HINTS.some((hint) => normalized.includes(hint));
};

export const formatStrategyDisplayName = (strategyId?: string, providedName?: string): string => {
  const normalizedId = strategyId?.trim();
  const preferredName = providedName?.trim();

  if (preferredName && preferredName.toLowerCase() !== normalizedId?.toLowerCase()) {
    return preferredName;
  }

  if (!normalizedId) {
    return preferredName || 'Strategy';
  }

  return normalizedId
    .split(/[_\-\s]+/)
    .filter(Boolean)
    .map((segment) => {
      const lower = segment.toLowerCase();
      if (AI_ACRONYMS.has(lower) || (segment.length <= 3 && /^[a-z]+$/i.test(segment))) {
        return segment.toUpperCase();
      }
      if (/^\d+$/.test(segment)) {
        return segment;
      }
      return segment.charAt(0).toUpperCase() + segment.slice(1);
    })
    .join(' ');
};

export interface TradingStrategy {
  strategy_id: string;
  name: string;
  status: string;
  is_active: boolean;
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  total_pnl: number;
  sharpe_ratio?: number;
  created_at: string;
  last_executed_at?: string;
  category?: string;
  risk_level?: string;
  description?: string;
}

export interface AvailableStrategy {
  name: string;
  category: string;
  description: string;
  risk_level: string;
  min_capital: number;
  parameters: string[];
}

export interface StrategyExecuteRequest {
  function: string;
  symbol?: string;
  parameters?: Record<string, any>;
  simulation_mode?: boolean;
}

export interface StrategyConfigRequest {
  strategy_name: string;
  parameters: Record<string, any>;
  risk_parameters: Record<string, any>;
  entry_conditions: Record<string, any>;
  exit_conditions: Record<string, any>;
  target_symbols?: string[];
  target_exchanges?: string[];
  max_positions?: number;
  max_risk_per_trade?: number;
  is_simulation?: boolean;
}

export const useStrategies = () => {
  const [strategies, setStrategies] = useState<TradingStrategy[]>([]);
  const [portfolioStrategies, setPortfolioStrategies] = useState<TradingStrategy[]>([]);
  const [portfolioStrategySet, setPortfolioStrategySet] = useState<Record<string, TradingStrategy>>({});
  const [availableStrategies, setAvailableStrategies] = useState<Record<string, AvailableStrategy>>({});
  const [loading, setLoading] = useState(false);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  // Fetch user's configured strategies
  const fetchStrategies = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get('/strategies/list');
      setStrategies(response.data);

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to fetch strategies';
      setError(errorMsg);
      toast({
        title: "Error",
        description: "Failed to load trading strategies",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchPortfolioStrategies = async () => {
    try {
      setPortfolioLoading(true);
      setError(null);

      const response = await apiClient.get('/strategies/my-portfolio');
      const data = response.data ?? {};

      const candidateLists: any[][] = [];
      const registerList = (list?: any) => {
        if (Array.isArray(list) && list.length) {
          candidateLists.push(list);
        }
      };

      registerList(data.active_strategies);
      registerList(data.strategies);
      registerList(data.provisioned_strategies);
      registerList(data.available_strategies);
      registerList(data.summary?.strategies);
      registerList(data.portfolio?.strategies);
      registerList(data.portfolio?.active_strategies);
      registerList(data.portfolio?.available_strategies);
      registerList(data.collections?.strategies);
      registerList(data.collections?.active_strategies);

      const discoverStrategyArrays = (value: any, keyHint?: string) => {
        if (Array.isArray(value)) {
          if (!value.length) {
            return;
          }
          const keyIncludesStrategy = (keyHint || '').toLowerCase().includes('strategy');
          const hasStrategyLikeObject = value.some((item) =>
            item && typeof item === 'object' && (
              'strategy_id' in item ||
              'strategyId' in item ||
              'strategy_name' in item ||
              'strategy' in item ||
              'name' in item
            )
          );
          const hasStrategyStrings = value.some(
            (item) => typeof item === 'string' && (keyIncludesStrategy || looksLikeStrategyId(item))
          );

          if (hasStrategyLikeObject || hasStrategyStrings) {
            candidateLists.push(value);
            return;
          }

          value.forEach((child) => discoverStrategyArrays(child, keyHint));
          return;
        }

        if (value && typeof value === 'object') {
          Object.entries(value).forEach(([key, child]) => discoverStrategyArrays(child, key));
        }
      };

      discoverStrategyArrays(data);

      const normalizedMap = new Map<string, TradingStrategy>();

      const coerceNumber = (value: any, fallback = 0) => {
        if (value === undefined || value === null) {
          return fallback;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
      };

      const processCandidate = (entry: any) => {
        if (!entry) {
          return;
        }

        if (Array.isArray(entry)) {
          entry.forEach(processCandidate);
          return;
        }

        if (typeof entry === 'string') {
          const strategyId = entry.trim();
          if (!strategyId) {
            return;
          }
          if (!normalizedMap.has(strategyId)) {
            normalizedMap.set(strategyId, {
              strategy_id: strategyId,
              name: formatStrategyDisplayName(strategyId),
              status: 'active',
              is_active: true,
              total_trades: 0,
              winning_trades: 0,
              win_rate: 0,
              total_pnl: 0,
              created_at: '1970-01-01T00:00:00.000Z',
            });
          }
          return;
        }

        if (typeof entry !== 'object') {
          return;
        }

        const candidate =
          entry && entry.strategy !== null && typeof entry.strategy === 'object'
            ? entry.strategy
            : entry;
        const rawId =
          candidate.strategy_id ||
          candidate.strategyId ||
          candidate.strategy_identifier ||
          candidate.id ||
          entry.strategy_id ||
          entry.strategyId ||
          entry.strategy_identifier ||
          entry.id ||
          (typeof entry.strategy === 'string' ? entry.strategy : null);

        const strategyId =
          typeof rawId === 'string'
            ? rawId
            : typeof rawId === 'number' && Number.isFinite(rawId)
              ? String(rawId)
              : null;

        if (!strategyId) {
          return;
        }

        const existing = normalizedMap.get(strategyId);
        const metricsSources = [candidate.metrics, candidate.performance, candidate.stats, entry.metrics, entry.performance, entry.stats];
        const pickMetric = (key: string) => {
          for (const source of metricsSources) {
            if (source && source[key] !== undefined && source[key] !== null) {
              return source[key];
            }
          }
          return undefined;
        };

        const derivedStatus =
          typeof candidate.status === 'string'
            ? candidate.status
            : typeof entry.status === 'string'
              ? entry.status
              : candidate.is_active === false || entry.is_active === false
                ? 'inactive'
                : existing?.status ?? 'active';

        const normalizedStatus =
          typeof derivedStatus === 'string' ? derivedStatus.toLowerCase() : 'active';

        const normalized: TradingStrategy = {
          strategy_id: strategyId,
          name: formatStrategyDisplayName(strategyId, candidate.name || candidate.strategy_name || entry.name),
          status: derivedStatus,
          is_active:
            candidate.is_active ??
            entry.is_active ??
            existing?.is_active ??
            normalizedStatus !== 'inactive',
          total_trades: coerceNumber(
            candidate.total_trades ??
              entry.total_trades ??
              pickMetric('total_trades') ??
              existing?.total_trades,
            0
          ),
          winning_trades: coerceNumber(
            candidate.winning_trades ??
              entry.winning_trades ??
              pickMetric('winning_trades') ??
              existing?.winning_trades,
            0
          ),
          win_rate: coerceNumber(
            candidate.win_rate ??
              entry.win_rate ??
              pickMetric('win_rate') ??
              existing?.win_rate,
            0
          ),
          total_pnl: coerceNumber(
            candidate.total_pnl_usd ??
              candidate.total_pnl ??
              entry.total_pnl_usd ??
              entry.total_pnl ??
              pickMetric('total_pnl_usd') ??
              pickMetric('total_pnl') ??
              existing?.total_pnl,
            0
          ),
          sharpe_ratio:
            candidate.sharpe_ratio ??
            pickMetric('sharpe_ratio') ??
            existing?.sharpe_ratio,
          created_at:
            candidate.activated_at ||
            candidate.created_at ||
            entry.activated_at ||
            entry.created_at ||
            existing?.created_at ||
            '1970-01-01T00:00:00.000Z',
          last_executed_at:
            candidate.last_executed_at ||
            candidate.last_execution_at ||
            entry.last_executed_at ||
            entry.last_execution_at ||
            existing?.last_executed_at,
          category: candidate.category || entry.category || existing?.category,
          risk_level: candidate.risk_level || entry.risk_level || existing?.risk_level,
          description: candidate.description || entry.description || existing?.description,
        };

        normalizedMap.set(strategyId, normalized);
      };

      candidateLists.forEach((list) => list.forEach(processCandidate));

      const normalizedRecord: Record<string, TradingStrategy> = {};
      normalizedMap.forEach((value, key) => {
        normalizedRecord[key] = value;
      });

      const normalizedStrategies = Object.values(normalizedRecord).sort((a, b) =>
        a.name.localeCompare(b.name)
      );

      setPortfolioStrategySet(normalizedRecord);
      setPortfolioStrategies(normalizedStrategies);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to fetch portfolio strategies';
      setError(errorMsg);
      toast({
        title: "Error",
        description: "Failed to load portfolio strategies",
        variant: "destructive",
      });
      console.warn('Failed to fetch portfolio strategies:', err?.response?.data ?? err);
    } finally {
      setPortfolioLoading(false);
    }
  };

  // Fetch available strategies from unified marketplace
  const fetchAvailableStrategies = async () => {
    try {
      const response = await apiClient.get('/strategies/marketplace');
      if (response.data.success) {
        // Transform marketplace data to legacy format for compatibility
        const strategies: Record<string, AvailableStrategy> = {};
        
        response.data.strategies.forEach((strategy: any) => {
          strategies[strategy.strategy_id] = {
            name: strategy.name,
            category: strategy.category,
            description: strategy.description,
            risk_level: strategy.risk_level,
            min_capital: strategy.min_capital_usd,
            parameters: strategy.timeframes || []
          };
        });
        
        setAvailableStrategies(strategies);
      }
    } catch (err: any) {
      console.warn('Failed to fetch marketplace strategies:', err);
    }
  };

  // Execute a strategy function
  const executeStrategy = async (request: StrategyExecuteRequest) => {
    try {
      setExecuting(true);
      setError(null);

      const response = await apiClient.post('/strategies/execute', {
        function: request.function,
        symbol: request.symbol || 'BTC/USDT',
        parameters: request.parameters || {},
        simulation_mode: request.simulation_mode ?? true
      });

      const result = response.data;
      
      if (result.success) {
        toast({
          title: "Strategy Executed",
          description: `${request.function} executed successfully${result.credits_used > 0 ? ` (${result.credits_used} credits used)` : ''}`,
          variant: "default",
        });

        // Refresh strategies list to update metrics
        await Promise.all([fetchStrategies(), fetchPortfolioStrategies()]);
        
        return result;
      } else {
        throw new Error(result.error || 'Strategy execution failed');
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Strategy execution failed';
      setError(errorMsg);
      
      toast({
        title: "Execution Failed",
        description: errorMsg,
        variant: "destructive",
      });
      
      throw err;
    } finally {
      setExecuting(false);
    }
  };

  // Configure a new strategy
  const configureStrategy = async (request: StrategyConfigRequest) => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post('/strategies/configure', request);
      
      if (response.data.success) {
        toast({
          title: "Strategy Configured",
          description: `${request.strategy_name} configured successfully`,
          variant: "default",
        });

        // Refresh strategies list
        await Promise.all([fetchStrategies(), fetchPortfolioStrategies()]);
        
        return response.data;
      } else {
        throw new Error(response.data.error || 'Strategy configuration failed');
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to configure strategy';
      setError(errorMsg);
      
      toast({
        title: "Configuration Failed",
        description: errorMsg,
        variant: "destructive",
      });
      
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Activate a strategy
  const activateStrategy = async (strategyId: string) => {
    try {
      const response = await apiClient.post(`/strategies/${strategyId}/activate`);
      
      if (response.data.success) {
        toast({
          title: "Strategy Activated",
          description: response.data.message,
          variant: "default",
        });

        // Update local state
        setStrategies(prev => prev.map(strategy =>
          strategy.strategy_id === strategyId
            ? { ...strategy, is_active: true, status: 'active' }
            : strategy
        ));

        await fetchPortfolioStrategies();

        return response.data;
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to activate strategy';
      toast({
        title: "Activation Failed",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Deactivate a strategy
  const deactivateStrategy = async (strategyId: string) => {
    try {
      const response = await apiClient.post(`/strategies/${strategyId}/deactivate`);
      
      if (response.data.success) {
        toast({
          title: "Strategy Deactivated",
          description: response.data.message,
          variant: "default",
        });

        // Update local state
        setStrategies(prev => prev.map(strategy =>
          strategy.strategy_id === strategyId
            ? { ...strategy, is_active: false, status: 'inactive' }
            : strategy
        ));

        await fetchPortfolioStrategies();

        return response.data;
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to deactivate strategy';
      toast({
        title: "Deactivation Failed", 
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Get strategy performance
  const getStrategyPerformance = async (strategyId: string) => {
    try {
      const response = await apiClient.get(`/strategies/${strategyId}/performance`);
      return response.data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to get strategy performance';
      toast({
        title: "Error",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Load data on mount
  useEffect(() => {
    fetchStrategies();
    fetchPortfolioStrategies();
    fetchAvailableStrategies();
  }, []);

  return {
    strategies,
    portfolioStrategies,
    portfolioStrategySet,
    availableStrategies,
    loading,
    executing,
    portfolioLoading,
    error,
    actions: {
      fetchStrategies,
      fetchPortfolioStrategies,
      executeStrategy,
      configureStrategy,
      activateStrategy,
      deactivateStrategy,
      getStrategyPerformance,
    }
  };
};