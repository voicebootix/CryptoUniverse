import { useState, useEffect } from 'react';
import { exchangesAPI } from '@/lib/api/client';
import { useToast } from '@/components/ui/use-toast';

export interface ExchangeConnection {
  id: string;
  exchange: string;
  nickname?: string;
  api_key_masked: string;
  is_active: boolean;
  trading_enabled: boolean;
  sandbox: boolean;
  created_at: string;
  last_used?: string;
  permissions: string[];
  connection_status: 'connected' | 'syncing' | 'disconnected' | 'error';
  daily_volume_limit?: number;
  daily_volume_used: number;
  balance?: number;
  pnl_24h?: number;
  trades_24h?: number;
  latency?: string;
}

export interface ExchangeConnectionRequest {
  exchange: string;
  api_key: string;
  secret_key: string;
  passphrase?: string;
  sandbox?: boolean;
  nickname?: string;
}

export interface ExchangeBalances {
  exchange: string;
  balances: Array<{
    asset: string;
    free: number;
    locked: number;
    total: number;
    value_usd: number;
  }>;
  total_value_usd: number;
  last_updated: string;
}

export const useExchanges = () => {
  const [exchanges, setExchanges] = useState<ExchangeConnection[]>([]);
  const [balances, setBalances] = useState<Record<string, ExchangeBalances>>({});
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  // Fetch connected exchanges
  const fetchExchanges = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await exchangesAPI.get('/list');
      const data = response.data;
      
      if (data.connections) {
        // Map backend response to our interface
        const mappedExchanges = data.connections.map((conn: any) => ({
          id: conn.id,
          exchange: conn.exchange,
          nickname: conn.nickname,
          api_key_masked: conn.api_key_masked,
          is_active: conn.is_active,
          trading_enabled: conn.trading_enabled,
          sandbox: conn.sandbox,
          created_at: conn.created_at,
          last_used: conn.last_used,
          permissions: conn.permissions || [],
          connection_status: conn.is_active ? 'connected' : 'disconnected',
          daily_volume_limit: conn.daily_volume_limit,
          daily_volume_used: conn.daily_volume_used,
          latency: conn.connection_status === 'connected' ? '12ms' : '-'
        }));
        
        setExchanges(mappedExchanges);
        
        // Fetch balances for connected exchanges
        for (const exchange of mappedExchanges.filter((e: any) => e.is_active)) {
          await fetchExchangeBalances(exchange.exchange);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch exchanges');
      toast({
        title: "Error",
        description: "Failed to load exchange connections",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Connect new exchange
  const connectExchange = async (request: ExchangeConnectionRequest) => {
    try {
      setConnecting(true);
      setError(null);

      const response = await exchangesAPI.post('/connect', request);
      const newConnection = response.data;
      
      // Add to local state
      const mappedConnection: ExchangeConnection = {
        id: newConnection.id,
        exchange: newConnection.exchange,
        nickname: newConnection.nickname,
        api_key_masked: newConnection.api_key_masked,
        is_active: newConnection.is_active,
        trading_enabled: newConnection.trading_enabled,
        sandbox: newConnection.sandbox,
        created_at: newConnection.created_at,
        last_used: newConnection.last_used,
        permissions: newConnection.permissions || [],
        connection_status: newConnection.connection_status,
        daily_volume_limit: newConnection.daily_volume_limit,
        daily_volume_used: newConnection.daily_volume_used,
        latency: '12ms'
      };

      setExchanges(prev => [...prev, mappedConnection]);
      
      // Fetch initial balances
      if (mappedConnection.is_active) {
        await fetchExchangeBalances(mappedConnection.exchange);
      }

      toast({
        title: "Success",
        description: `${request.exchange} connected successfully`,
        variant: "default",
      });

      return mappedConnection;
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || `Failed to connect ${request.exchange}`;
      setError(errorMsg);
      
      toast({
        title: "Connection Failed",
        description: errorMsg,
        variant: "destructive",
      });
      
      throw err;
    } finally {
      setConnecting(false);
    }
  };

  // Test exchange connection
  const testConnection = async (exchangeId: string) => {
    try {
      const response = await exchangesAPI.post(`/${exchangeId}/test`);
      const testResult = response.data;
      
      // Update exchange status
      setExchanges(prev => prev.map(exchange => 
        exchange.id === exchangeId 
          ? { 
              ...exchange, 
              connection_status: testResult.connection_status,
              permissions: testResult.permissions,
              latency: `${Math.round(testResult.latency_ms)}ms`
            }
          : exchange
      ));

      if (testResult.connection_status === 'connected') {
        toast({
          title: "Connection Test Passed",
          description: `${testResult.exchange} is connected and working`,
          variant: "default",
        });
      } else {
        toast({
          title: "Connection Test Failed",
          description: testResult.error_message || 'Connection test failed',
          variant: "destructive",
        });
      }

      return testResult;
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Connection test failed';
      toast({
        title: "Test Failed",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Fetch balances for specific exchange
  const fetchExchangeBalances = async (exchange: string) => {
    try {
      const response = await exchangesAPI.get(`/${exchange}/balances`);
      const balanceData = response.data;
      
      setBalances(prev => ({
        ...prev,
        [exchange]: balanceData
      }));
      
      // Update exchange with balance totals
      setExchanges(prev => prev.map(ex => 
        ex.exchange === exchange 
          ? { 
              ...ex, 
              balance: balanceData.total_value_usd,
              // You might want to calculate these from recent trades
              pnl_24h: Math.random() * 1000 - 500, // TODO: Get real P&L
              trades_24h: Math.floor(Math.random() * 50) // TODO: Get real trade count
            }
          : ex
      ));
      
    } catch (err: any) {
      console.warn(`Failed to fetch balances for ${exchange}:`, err);
      // Don't show error toast for balance fetching, it's not critical
    }
  };

  // Disconnect exchange
  const disconnectExchange = async (exchangeId: string) => {
    try {
      await exchangesAPI.delete(`/${exchangeId}`);
      
      setExchanges(prev => prev.filter(ex => ex.id !== exchangeId));
      
      toast({
        title: "Exchange Disconnected",
        description: "Exchange connection removed successfully",
        variant: "default",
      });
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to disconnect exchange';
      toast({
        title: "Error",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Calculate aggregated stats
  const getAggregatedStats = () => {
    const connectedExchanges = exchanges.filter(ex => ex.is_active);
    
    return {
      totalBalance: connectedExchanges.reduce((sum, ex) => sum + (ex.balance || 0), 0),
      totalPnl24h: connectedExchanges.reduce((sum, ex) => sum + (ex.pnl_24h || 0), 0),
      totalTrades24h: connectedExchanges.reduce((sum, ex) => sum + (ex.trades_24h || 0), 0),
      connectedCount: connectedExchanges.length,
      totalCount: exchanges.length,
      exchanges: connectedExchanges.map(ex => ex.exchange)
    };
  };

  // Load exchanges on mount
  useEffect(() => {
    fetchExchanges();
  }, []);

  return {
    exchanges,
    balances,
    loading,
    connecting,
    error,
    aggregatedStats: getAggregatedStats(),
    actions: {
      connectExchange,
      disconnectExchange,
      testConnection,
      fetchExchanges,
      fetchExchangeBalances,
    }
  };
};
