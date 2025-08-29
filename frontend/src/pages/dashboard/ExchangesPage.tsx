import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  BarChart3, 
  Plus, 
  Settings, 
  Globe, 
  Shield,
  CheckCircle,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useExchanges } from '@/hooks/useExchanges';
import ExchangeConnectionModal from '@/components/ExchangeConnectionModal';
import { formatCurrency } from '@/lib/utils';

const EXCHANGE_ICONS: Record<string, string> = {
  binance: '🔶',
  coinbase: '🔵',
  kraken: '🐙',
  kucoin: '🟢',
  bybit: '🟠',
  okx: '⭕',
  bitget: '🔷',
  gateio: '🔴'
};

const EXCHANGE_NAMES: Record<string, string> = {
  binance: 'Binance',
  coinbase: 'Coinbase',
  kraken: 'Kraken',
  kucoin: 'KuCoin',
  bybit: 'Bybit',
  okx: 'OKX',
  bitget: 'Bitget',
  gateio: 'Gate.io'
};

const ExchangesPage: React.FC = () => {
  const { exchanges, loading, connecting, aggregatedStats, actions } = useExchanges();
  const [showConnectionModal, setShowConnectionModal] = useState(false);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'syncing': return <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'disconnected': return <Globe className="w-4 h-4 text-gray-500" />;
      case 'error': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-6"
      >
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-64 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-96"></div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border rounded-lg p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Exchange Management</h1>
          <p className="text-muted-foreground">
            Connect and manage your exchange API keys, view balances, and configure trading preferences.
          </p>
        </div>
        <Button 
          onClick={() => setShowConnectionModal(true)}
          className="bg-gradient-to-r from-blue-600 to-purple-600 text-white"
        >
          <Plus className="w-4 w-4 mr-2" />
          Add Exchange
        </Button>
      </div>

      {/* Stats Overview */}
      {exchanges.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(aggregatedStats.totalBalance)}</div>
              <p className="text-xs text-muted-foreground">
                Across {aggregatedStats.connectedCount} connected exchanges
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Connected Exchanges</CardTitle>
              <Globe className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{aggregatedStats.connectedCount}</div>
              <p className="text-xs text-muted-foreground">
                {aggregatedStats.totalCount - aggregatedStats.connectedCount} pending connection
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">24h Trades</CardTitle>
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{aggregatedStats.totalTrades24h}</div>
              <p className="text-xs text-muted-foreground">
                Across all exchanges
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Security Status</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">Secure</div>
              <p className="text-xs text-muted-foreground">
                All keys encrypted
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Exchange List */}
      {exchanges.length === 0 ? (
        <Card className="p-12 text-center">
          <Globe className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-600 mb-2">No Exchange Connections</h3>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">
            Connect your first exchange account to start automated trading. 
            Your API keys are encrypted and stored securely.
          </p>
          <Button 
            onClick={() => setShowConnectionModal(true)}
            className="bg-gradient-to-r from-blue-600 to-purple-600 text-white"
          >
            <Plus className="w-4 w-4 mr-2" />
            Connect Your First Exchange
          </Button>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Connected Exchanges</CardTitle>
                <CardDescription>Manage your exchange connections and API keys</CardDescription>
              </div>
              <Button 
                variant="outline" 
                onClick={actions.fetchExchanges}
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {exchanges.map((exchange) => (
                <motion.div
                  key={exchange.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between p-4 border rounded-lg hover:shadow-md transition-all"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-2xl">{EXCHANGE_ICONS[exchange.exchange] || '🔗'}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">
                          {exchange.nickname || EXCHANGE_NAMES[exchange.exchange] || exchange.exchange}
                        </h3>
                        {getStatusIcon(exchange.connection_status)}
                        <span className="text-sm text-gray-500 capitalize">
                          {exchange.connection_status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {exchange.api_key_masked}
                        </Badge>
                        {exchange.sandbox && (
                          <Badge variant="secondary" className="text-xs">
                            Sandbox
                          </Badge>
                        )}
                        {exchange.trading_enabled && (
                          <Badge variant="default" className="text-xs">
                            Trading Enabled
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-medium">{formatCurrency(exchange.balance || 0)}</div>
                      <div className="text-sm text-gray-500">
                        {exchange.trades_24h || 0} trades today
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => actions.testConnection(exchange.id)}
                      >
                        <RefreshCw className="w-3 h-3 mr-1" />
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                      >
                        <Settings className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Connection Modal */}
      <ExchangeConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onConnect={async (request) => {
          await actions.connectExchange(request);
        }}
        connecting={connecting}
      />
    </motion.div>
  );
};

export default ExchangesPage;
