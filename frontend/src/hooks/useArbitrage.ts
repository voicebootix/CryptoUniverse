import { useState, useEffect } from 'react';
import { tradingAPI } from '@/lib/api/client';

export interface ArbitrageOpportunity {
  id: string;
  pair: string;
  buyExchange: string;
  sellExchange: string;
  buyPrice: number;
  sellPrice: number;
  spread: number;
  spreadPct: number;
  volume: number;
  profit: number;
  risk: 'low' | 'medium' | 'high';
  timestamp: string;
}

interface ArbitrageHookState {
  opportunities: ArbitrageOpportunity[];
  loading: boolean;
  error: string | null;
  fetchOpportunities: () => Promise<void>;
  executeArbitrage: (opportunityId: string) => Promise<void>;
}

export const useArbitrage = (): ArbitrageHookState => {
  const [opportunities, setOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOpportunities = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/arbitrage/opportunities');
      
      // Handle different response structures
      if (response.data && Array.isArray(response.data)) {
        setOpportunities(response.data);
      } else if (response.data && response.data.data && Array.isArray(response.data.data)) {
        setOpportunities(response.data.data);
      } else if (response.data && response.data.success && Array.isArray(response.data.data)) {
        setOpportunities(response.data.data);
      } else {
        // If no opportunities property exists, use the entire response if it's an array
        setOpportunities(Array.isArray(response.data) ? response.data : []);
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch arbitrage opportunities';
      setError(errorMessage);
      setOpportunities([]);
    } finally {
      setLoading(false);
    }
  };

  const executeArbitrage = async (opportunityId: string): Promise<void> => {
    try {
      const response = await tradingAPI.post('/arbitrage/execute', {
        opportunity_id: opportunityId
      });
      
      if (response.data && !response.data.success) {
        throw new Error(response.data.message || 'Failed to execute arbitrage');
      }
      
      // Refresh opportunities after execution
      await fetchOpportunities();
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to execute arbitrage trade';
      throw new Error(errorMessage);
    }
  };

  useEffect(() => {
    fetchOpportunities();
    
    // Set up polling for real-time updates
    const interval = setInterval(fetchOpportunities, 30000); // Update every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  return {
    opportunities,
    loading,
    error,
    fetchOpportunities,
    executeArbitrage
  };
};
