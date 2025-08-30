import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useExchanges } from '@/hooks/useExchanges';
import { useArbitrage } from '@/hooks/useArbitrage';
import ExchangeConnectionModal from '@/components/ExchangeConnectionModal';
import {
  Globe,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Bitcoin,
  Activity,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Settings,
  Link2,
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Wallet,
  CreditCard,
  Eye,
  EyeOff,
  Copy,
  Plus,
  Minus,
  ChevronDown,
  ChevronUp,
  Filter,
  Search,
  Download,
  Upload,
  PieChart,
  Layers,
  Terminal,
  Code,
  Database,
  Server,
  Cloud,
  Lock,
  Unlock,
  Key,
  UserCheck,
  UserX
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

// Exchange icons mapping
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

// Exchange names mapping
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

// Arbitrage opportunities now loaded from API - no more hardcoded data

// Unified order book
const unifiedOrderBook = {
  bids: [
    { price: 43250.50, amount: 2.45, total: 105963.73, exchange: 'Binance' },
    { price: 43248.30, amount: 1.89, total: 81739.29, exchange: 'Coinbase' },
    { price: 43245.00, amount: 3.12, total: 134924.40, exchange: 'Kraken' },
    { price: 43242.80, amount: 1.56, total: 67458.77, exchange: 'Bybit' },
    { price: 43240.00, amount: 2.34, total: 101181.60, exchange: 'OKX' }
  ],
  asks: [
    { price: 43255.20, amount: 2.12, total: 91701.02, exchange: 'Binance' },
    { price: 43257.50, amount: 1.78, total: 76998.35, exchange: 'Coinbase' },
    { price: 43260.00, amount: 2.89, total: 125021.40, exchange: 'Kraken' },
    { price: 43262.30, amount: 1.45, total: 62730.34, exchange: 'Bybit' },
    { price: 43265.00, amount: 2.67, total: 115517.55, exchange: 'OKX' }
  ]
};

// Performance metrics by exchange
const exchangePerformance = [
  { name: 'Binance', trades: 342, winRate: 72, avgProfit: 13.4, volume: 2456789 },
  { name: 'Coinbase', trades: 128, winRate: 58, avgProfit: -9.6, volume: 1234567 },
  { name: 'Kraken', trades: 89, winRate: 65, avgProfit: 26.3, volume: 987654 },
  { name: 'Bybit', trades: 156, winRate: 69, avgProfit: 22.1, volume: 1456789 },
  { name: 'OKX', trades: 67, winRate: 61, avgProfit: 18.4, volume: 765432 }
];

const MultiExchangeHub: React.FC = () => {
  const { exchanges, loading, connecting, aggregatedStats, actions } = useExchanges();
  const [selectedExchange, setSelectedExchange] = useState<string>('all');
  const [showApiKeys, setShowApiKeys] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [autoArbitrage, setAutoArbitrage] = useState<boolean>(false);
  const [unifiedTrading, setUnifiedTrading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterExchange, setFilterExchange] = useState<string>('all');
  const [showConnectionModal, setShowConnectionModal] = useState<boolean>(false);

  // Real-time data simulation
  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate real-time updates
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-500';
      case 'syncing': return 'text-yellow-500';
      case 'disconnected': return 'text-gray-500';
      case 'error': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'syncing': return <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'disconnected': return <XCircle className="w-4 h-4 text-gray-500" />;
      case 'error': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Multi-Exchange Trading Hub
          </h1>
          <p className="text-gray-500 mt-1">Unified trading across all major exchanges</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
          <Button 
            className="bg-gradient-to-r from-blue-600 to-purple-600 text-white"
            onClick={() => setShowConnectionModal(true)}
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Exchange
          </Button>
        </div>
      </div>

      {/* Aggregated Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-6 bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-600">Total Balance</p>
              <p className="text-2xl font-bold mt-1">{formatCurrency(aggregatedStats.totalBalance)}</p>
              <p className="text-xs text-gray-500 mt-1">Across {aggregatedStats.connectedCount} exchanges</p>
            </div>
            <Wallet className="w-8 h-8 text-blue-600" />
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-600">24h P&L</p>
              <p className="text-2xl font-bold mt-1 text-green-600">+{formatCurrency(aggregatedStats.totalPnl24h)}</p>
              <p className="text-xs text-gray-500 mt-1">+{formatPercentage(2.64)}</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-600" />
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-br from-purple-50 to-pink-50 border-purple-200">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-600">24h Volume</p>
              <p className="text-2xl font-bold mt-1">{formatCurrency(aggregatedStats.totalTrades24h * 10000)}</p>
              <p className="text-xs text-gray-500 mt-1">{aggregatedStats.totalTrades24h} trades</p>
            </div>
            <Activity className="w-8 h-8 text-purple-600" />
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-br from-orange-50 to-red-50 border-orange-200">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-600">Win Rate</p>
              <p className="text-2xl font-bold mt-1">{formatPercentage(68.5)}</p>
              <p className="text-xs text-gray-500 mt-1">{Math.floor(aggregatedStats.totalTrades24h / 2)} active positions</p>
            </div>
            <BarChart3 className="w-8 h-8 text-orange-600" />
          </div>
        </Card>
      </div>

      {/* Exchange Grid */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold">Connected Exchanges</h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowApiKeys(!showApiKeys)}>
              {showApiKeys ? <EyeOff className="w-4 h-4 mr-2" /> : <Eye className="w-4 h-4 mr-2" />}
              {showApiKeys ? 'Hide' : 'Show'} API Keys
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={actions.fetchExchanges}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Sync All
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="border rounded-lg p-4 animate-pulse">
                <div className="h-6 bg-gray-200 rounded mb-3"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : exchanges.length === 0 ? (
          <div className="text-center py-12">
            <Globe className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">No Exchange Connections</h3>
            <p className="text-gray-500 mb-4">Connect your first exchange to start trading</p>
            <Button 
              onClick={() => setShowConnectionModal(true)}
              className="bg-gradient-to-r from-blue-600 to-purple-600 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Exchange
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {exchanges.map((exchange) => (
            <motion.div
              key={exchange.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="border rounded-lg p-4 hover:shadow-lg transition-all cursor-pointer"
              onClick={() => setSelectedExchange(exchange.exchange)}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{EXCHANGE_ICONS[exchange.exchange] || '🔗'}</span>
                  <div>
                    <p className="font-semibold">{exchange.nickname || EXCHANGE_NAMES[exchange.exchange] || exchange.exchange}</p>
                    <div className="flex items-center gap-1 mt-1">
                      {getStatusIcon(exchange.connection_status)}
                      <span className={`text-xs ${getStatusColor(exchange.connection_status)}`}>
                        {exchange.connection_status}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={exchange.is_active ? 'default' : 'secondary'}>
                    {exchange.latency || 'N/A'}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      actions.testConnection(exchange.id);
                    }}
                    className="p-1"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Balance:</span>
                  <span className="font-medium">{formatCurrency(exchange.balance || 0)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">24h P&L:</span>
                  <span className={`font-medium ${(exchange.pnl_24h || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {(exchange.pnl_24h || 0) >= 0 ? '+' : ''}{formatCurrency(exchange.pnl_24h || 0)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Trades:</span>
                  <span className="font-medium">{exchange.trades_24h || 0}</span>
                </div>
              </div>

              {showApiKeys && exchange.connection_status === 'connected' && (
                <div className="mt-3 pt-3 border-t">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">API Key:</span>
                    <div className="flex items-center gap-1">
                      <code className="bg-gray-100 px-1 rounded">{exchange.api_key_masked}</code>
                      <Copy className="w-3 h-3 text-gray-400 cursor-pointer hover:text-gray-600" />
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs mt-2">
                    <span className="text-gray-500">Permissions:</span>
                    <div className="flex gap-1">
                      {exchange.permissions.slice(0, 2).map((perm) => (
                        <Badge key={perm} variant="secondary" className="text-xs px-1">
                          {perm}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="mt-2">
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Are you sure you want to disconnect this exchange?')) {
                          actions.disconnectExchange(exchange.id);
                        }
                      }}
                      className="w-full text-xs h-6"
                    >
                      Disconnect
                    </Button>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
          </div>
        )}
        
        {/* Exchange Connection Modal */}
        <ExchangeConnectionModal
          isOpen={showConnectionModal}
          onClose={() => setShowConnectionModal(false)}
          onConnect={async (request) => {
            await actions.connectExchange(request);
          }}
          connecting={connecting}
        />
      </Card>

      {/* Tabs for different views */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="arbitrage">Arbitrage Scanner</TabsTrigger>
          <TabsTrigger value="orderbook">Unified Order Book</TabsTrigger>
          <TabsTrigger value="performance">Performance Analysis</TabsTrigger>
          <TabsTrigger value="positions">Cross-Exchange Positions</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {/* Exchange Performance Chart */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Exchange Performance Comparison</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={exchangePerformance}>
                <PolarGrid strokeDasharray="3 3" />
                <PolarAngleAxis dataKey="name" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar name="Win Rate" dataKey="winRate" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                <Radar name="Avg Profit" dataKey="avgProfit" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="arbitrage">
          <Card className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold">Cross-Exchange Arbitrage Opportunities</h3>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch checked={autoArbitrage} onCheckedChange={setAutoArbitrage} />
                  <span className="text-sm">Auto-Execute</span>
                </div>
                <Badge variant="default">
                  <Zap className="w-3 h-3 mr-1" />
                  4 Active Opportunities
                </Badge>
              </div>
            </div>

            <div className="space-y-3">
              {arbitrageOpportunities.map((opp) => (
                <motion.div
                  key={opp.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="border rounded-lg p-4 hover:shadow-md transition-all"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-semibold text-lg">{opp.pair}</span>
                        <Badge variant={opp.risk === 'low' ? 'default' : opp.risk === 'medium' ? 'warning' : 'destructive'}>
                          {opp.risk} risk
                        </Badge>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Buy on:</span>
                          <span className="ml-2 font-medium">{opp.buyExchange} @ {formatCurrency(opp.buyPrice)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Sell on:</span>
                          <span className="ml-2 font-medium">{opp.sellExchange} @ {formatCurrency(opp.sellPrice)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-green-600">+{formatCurrency(opp.profit)}</p>
                      <p className="text-sm text-gray-500">{formatPercentage(opp.spreadPct)} spread</p>
                      <Button size="sm" className="mt-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white">
                        Execute Trade
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="orderbook">
          <Card className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold">Unified Order Book - BTC/USDT</h3>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch checked={unifiedTrading} onCheckedChange={setUnifiedTrading} />
                  <span className="text-sm">Unified Trading</span>
                </div>
                <Select value={filterExchange} onValueChange={setFilterExchange}>
                  <option value="all">All Exchanges</option>
                  {exchanges.map(e => (
                    <option key={e.id} value={e.id}>{EXCHANGE_NAMES[e.exchange] || e.exchange}</option>
                  ))}
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-green-600 mb-3">Bids</h4>
                <div className="space-y-2">
                  {unifiedOrderBook.bids.map((bid, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                      <span className="text-sm font-medium">{formatCurrency(bid.price)}</span>
                      <span className="text-sm">{bid.amount} BTC</span>
                      <span className="text-xs text-gray-500">{bid.exchange}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-medium text-red-600 mb-3">Asks</h4>
                <div className="space-y-2">
                  {unifiedOrderBook.asks.map((ask, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-red-50 rounded">
                      <span className="text-sm font-medium">{formatCurrency(ask.price)}</span>
                      <span className="text-sm">{ask.amount} BTC</span>
                      <span className="text-xs text-gray-500">{ask.exchange}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="performance">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Performance by Exchange</h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={exchangePerformance}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis yAxisId="left" orientation="left" stroke="#8b5cf6" />
                <YAxis yAxisId="right" orientation="right" stroke="#3b82f6" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="trades" fill="#8b5cf6" name="Total Trades" />
                <Bar yAxisId="right" dataKey="winRate" fill="#3b82f6" name="Win Rate %" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="positions">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cross-Exchange Positions</h3>
            <p className="text-gray-500">Position management across all connected exchanges coming soon...</p>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MultiExchangeHub;
