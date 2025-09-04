import { useState, useEffect } from 'react';
import { tradingAPI } from '@/lib/api/client';
import { 
  ArbitrageOpportunity, 
  ArbitrageOpportunityAPI, 
  ArbitrageDataTransformer 
} from '@/types/arbitrage';

interface ArbitrageHookState {
  opportunities: ArbitrageOpportunity[];
  loading: boolean;
  error: string | null;
  orderBook: any;
  crossExchangeComparison: any;
  isLoading: boolean;
  fetchOpportunities: () => Promise<void>;
  executeArbitrage: (opportunityId: string) => Promise<void>;
  fetchArbitrageOpportunities: () => Promise<void>;
  fetchCrossExchangeComparison: () => Promise<void>;
  fetchOrderBook: (symbol: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const useArbitrage = (): ArbitrageHookState => {
  const [opportunities, setOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [orderBook, setOrderBook] = useState<any>(null);
  const [crossExchangeComparison, setCrossExchangeComparison] = useState<any>(null);

  const fetchOpportunities = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/arbitrage/opportunities');
      
      // Enterprise-grade response handling with robust data transformation
      let rawOpportunities: ArbitrageOpportunityAPI[] = [];
      
      if (response.data && response.data.success && response.data.data) {
        // Standard API wrapper response
        rawOpportunities = response.data.data.opportunities || response.data.data || [];
      } else if (response.data && response.data.data && Array.isArray(response.data.data)) {
        // Direct data array response
        rawOpportunities = response.data.data;
      } else if (Array.isArray(response.data)) {
        // Raw array response
        rawOpportunities = response.data;
      } else if (response.data && Array.isArray(response.data.opportunities)) {
        // Opportunities property response
        rawOpportunities = response.data.opportunities;
      } else {
        console.warn('Unexpected API response structure:', response.data);
        rawOpportunities = [];
      }

      // Transform API response to frontend format with enterprise error handling
      const transformedOpportunities = ArbitrageDataTransformer.transformArrayFromAPI(rawOpportunities);
      setOpportunities(transformedOpportunities);
      
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

  const fetchArbitrageOpportunities = async (): Promise<void> => {
    await fetchOpportunities();
  };

  const fetchCrossExchangeComparison = async (symbols?: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get('/arbitrage/cross-exchange-comparison');
      
      if (response.data && Array.isArray(response.data)) {
        setCrossExchangeComparison(response.data);
      } else if (response.data && response.data.data) {
        setCrossExchangeComparison(response.data.data);
      } else {
        setCrossExchangeComparison([]);
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch cross-exchange comparison';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrderBook = async (symbol: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.get(`/arbitrage/orderbook/${symbol}`);
      
      if (response.data) {
        setOrderBook(response.data);
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || 
                          err?.response?.data?.error || 
                          err?.message || 
                          'Failed to fetch order book';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const refreshAll = async (): Promise<void> => {
    await Promise.all([
      fetchOpportunities(),
      fetchCrossExchangeComparison()
    ]);
  };

  const clearError = (): void => {
    setError(null);
  };

  return {
    opportunities,
    loading,
    error,
    orderBook,
    crossExchangeComparison,
    isLoading: loading,
    fetchOpportunities,
    executeArbitrage,
    fetchArbitrageOpportunities,
    fetchCrossExchangeComparison,
    fetchOrderBook,
    refreshAll,
    clearError
  };
};
