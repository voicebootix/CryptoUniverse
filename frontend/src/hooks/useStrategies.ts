import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import { useToast } from '@/components/ui/use-toast';

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
  const [availableStrategies, setAvailableStrategies] = useState<Record<string, AvailableStrategy>>({});
  const [loading, setLoading] = useState(false);
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
        await fetchStrategies();
        
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
        await fetchStrategies();
        
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
    fetchAvailableStrategies();
  }, []);

  return {
    strategies,
    availableStrategies,
    loading,
    executing,
    error,
    actions: {
      fetchStrategies,
      executeStrategy,
      configureStrategy,
      activateStrategy,
      deactivateStrategy,
      getStrategyPerformance,
    }
  };
};