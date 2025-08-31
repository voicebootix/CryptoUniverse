import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import { useToast } from '@/components/ui/use-toast';

export interface CreditBalance {
  available_credits: number;
  total_purchased_credits: number;
  total_used_credits: number;
  profit_potential: number;
  profit_earned_to_date: number;
  remaining_potential: number;
  utilization_percentage: number;
  needs_more_credits: boolean;
}

export interface ProfitPotential {
  current_profit_earned: number;
  profit_potential: number;
  remaining_potential: number;
  utilization_percentage: number;
  active_strategies: number;
  earning_velocity: string;
  estimated_days_to_ceiling?: number;
}

export interface CreditPurchaseOption {
  package_name: string;
  usd_cost: number;
  credits: number;
  profit_potential: number;
  bonus_credits: number;
  strategies_included: number;
  popular: boolean;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  transaction_type: string;
  description: string;
  status: string;
  created_at: string;
  processed_at?: string;
}

export const useCredits = () => {
  const [balance, setBalance] = useState<CreditBalance>({
    available_credits: 0,
    total_purchased_credits: 0,
    total_used_credits: 0,
    profit_potential: 0,
    profit_earned_to_date: 0,
    remaining_potential: 0,
    utilization_percentage: 0,
    needs_more_credits: false
  });
  
  const [profitPotential, setProfitPotential] = useState<ProfitPotential>({
    current_profit_earned: 0,
    profit_potential: 0,
    remaining_potential: 0,
    utilization_percentage: 0,
    active_strategies: 0,
    earning_velocity: 'slow',
    estimated_days_to_ceiling: undefined
  });
  
  const [purchaseOptions, setPurchaseOptions] = useState<CreditPurchaseOption[]>([]);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  // Fetch credit balance
  const fetchBalance = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get('/credits/balance');
      setBalance(response.data);
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to fetch credit balance';
      setError(errorMsg);
      toast({
        title: "Error",
        description: "Failed to load credit balance",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch profit potential status
  const fetchProfitPotential = async () => {
    try {
      const response = await apiClient.get('/credits/profit-potential');
      setProfitPotential(response.data);
      
    } catch (err: any) {
      console.warn('Failed to fetch profit potential:', err);
    }
  };

  // Fetch purchase options
  const fetchPurchaseOptions = async () => {
    try {
      const response = await apiClient.get('/credits/purchase-options');
      if (response.data.success) {
        setPurchaseOptions(response.data.purchase_options);
      }
    } catch (err: any) {
      console.warn('Failed to fetch purchase options:', err);
    }
  };

  // Fetch transaction history
  const fetchTransactions = async () => {
    try {
      const response = await apiClient.get('/credits/transaction-history');
      if (response.data.success) {
        setTransactions(response.data.transactions);
      }
    } catch (err: any) {
      console.warn('Failed to fetch transaction history:', err);
    }
  };

  // Purchase credits
  const purchaseCredits = async (amountUsd: number, paymentMethod: string) => {
    try {
      setPurchasing(true);
      setError(null);

      const response = await apiClient.post('/credits/purchase', {
        amount_usd: amountUsd,
        payment_method: paymentMethod
      });

      if (response.data.payment_id) {
        toast({
          title: "Payment Created",
          description: `Pay ${response.data.crypto_amount} ${response.data.crypto_currency} to complete purchase`,
          variant: "default",
        });

        // Return payment details for QR code display
        return response.data;
      } else {
        throw new Error('Payment creation failed');
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to create payment';
      setError(errorMsg);
      
      toast({
        title: "Purchase Failed",
        description: errorMsg,
        variant: "destructive",
      });
      
      throw err;
    } finally {
      setPurchasing(false);
    }
  };

  // Purchase strategy access
  const purchaseStrategy = async (strategyId: string, subscriptionType: string = 'monthly') => {
    try {
      const response = await apiClient.post('/strategies/purchase', {
        strategy_id: strategyId,
        subscription_type: subscriptionType
      });

      if (response.data.success) {
        toast({
          title: "Strategy Purchased",
          description: `Strategy access granted for ${response.data.cost} credits`,
          variant: "default",
        });

        // Refresh balance and strategies
        await fetchBalance();
        
        return response.data;
      } else {
        throw new Error(response.data.error || 'Strategy purchase failed');
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to purchase strategy';
      
      toast({
        title: "Purchase Failed",
        description: errorMsg,
        variant: "destructive",
      });
      
      throw err;
    }
  };

  // Get user's strategy portfolio
  const fetchStrategyPortfolio = async () => {
    try {
      const response = await apiClient.get('/strategies/my-portfolio');
      return response.data;
    } catch (err: any) {
      console.warn('Failed to fetch strategy portfolio:', err);
      return { active_strategies: [], total_strategies: 0, total_monthly_cost: 0 };
    }
  };

  // Calculate earning velocity
  const getEarningVelocityInfo = () => {
    const velocityInfo = {
      slow: { 
        color: 'text-gray-500', 
        description: 'Basic strategies, steady growth',
        icon: '🐌'
      },
      medium: { 
        color: 'text-blue-500', 
        description: 'Balanced strategy mix',
        icon: '🚶‍♂️'
      },
      fast: { 
        color: 'text-green-500', 
        description: 'Advanced strategies, accelerated growth',
        icon: '🏃‍♂️'
      },
      maximum: { 
        color: 'text-purple-500', 
        description: 'All strategies, maximum speed',
        icon: '🚀'
      }
    };
    
    return velocityInfo[profitPotential.earning_velocity as keyof typeof velocityInfo] || velocityInfo.slow;
  };

  // Load data on mount
  useEffect(() => {
    fetchBalance();
    fetchProfitPotential();
    fetchPurchaseOptions();
    fetchTransactions();
  }, []);

  return {
    balance,
    profitPotential,
    purchaseOptions,
    transactions,
    loading,
    purchasing,
    error,
    earningVelocityInfo: getEarningVelocityInfo(),
    actions: {
      fetchBalance,
      fetchProfitPotential,
      purchaseCredits,
      purchaseStrategy,
      fetchStrategyPortfolio,
      fetchTransactions
    }
  };
};