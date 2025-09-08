import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Store,
  TrendingUp,
  TrendingDown,
  Zap,
  Target,
  BarChart3,
  Activity,
  Shield,
  Clock,
  DollarSign,
  Star,
  Play,
  Pause,
  Settings,
  Eye,
  Filter,
  Search,
  ChevronDown,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  Cpu,
  Brain,
  Flame,
  Crown,
  Rocket,
  Timer,
  Bot,
  Crosshair,
  Gauge,
  Sparkles,
  LineChart,
  CheckCircle,
  ShoppingCart,
  X,
  Users,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';
import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useStrategies } from '@/hooks/useStrategies';
import { useCredits } from '@/hooks/useCredits';
import StrategyExecutionModal from '@/components/modals/StrategyExecutionModal';
import StrategyPurchaseModal from '@/components/modals/StrategyPurchaseModal';

// Trading Strategies Data based on your backend
const tradingStrategies = [
  // Derivatives Trading
  {
    id: 'futures_trade',
    name: 'Futures Trading',
    category: 'derivatives',
    icon: Rocket,
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    description: 'Advanced futures contract trading with leverage management',
    riskLevel: 'High',
    avgReturn: '45-80%',
    winRate: 78.5,
    activeUsers: 247,
    minCapital: 5000,
    maxLeverage: '20x',
    timeframe: '1m-4h',
    features: ['Leverage control', 'Risk management', 'Auto-liquidation protection'],
    performance: [
      { date: '2024-01', return: 12.5 },
      { date: '2024-02', return: 18.2 },
      { date: '2024-03', return: -3.1 },
      { date: '2024-04', return: 24.7 },
      { date: '2024-05', return: 31.2 },
      { date: '2024-06', return: 28.9 }
    ],
    status: 'active',
    tier: 'pro'
  },
  {
    id: 'options_trade',
    name: 'Options Trading',
    category: 'derivatives',
    icon: Target,
    color: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    description: 'Sophisticated options strategies with Greeks calculation',
    riskLevel: 'High',
    avgReturn: '35-65%',
    winRate: 82.1,
    activeUsers: 156,
    minCapital: 10000,
    maxLeverage: '10x',
    timeframe: '1d-1w',
    features: ['Greeks calculation', 'Volatility analysis', 'Multi-leg strategies'],
    performance: [
      { date: '2024-01', return: 8.7 },
      { date: '2024-02', return: 15.4 },
      { date: '2024-03', return: 22.1 },
      { date: '2024-04', return: 18.9 },
      { date: '2024-05', return: 29.3 },
      { date: '2024-06', return: 34.8 }
    ],
    status: 'active',
    tier: 'enterprise'
  },
  {
    id: 'perpetual_trade',
    name: 'Perpetual Swaps',
    category: 'derivatives',
    icon: Layers,
    color: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    description: 'Perpetual contract trading with funding rate optimization',
    riskLevel: 'High',
    avgReturn: '40-70%',
    winRate: 75.8,
    activeUsers: 389,
    minCapital: 2000,
    maxLeverage: '50x',
    timeframe: '5m-1h',
    features: ['Funding rate arbitrage', 'Cross-margin', 'Auto-deleveraging'],
    performance: [
      { date: '2024-01', return: 16.3 },
      { date: '2024-02', return: 21.7 },
      { date: '2024-03', return: 12.4 },
      { date: '2024-04', return: 28.9 },
      { date: '2024-05', return: 35.2 },
      { date: '2024-06', return: 41.6 }
    ],
    status: 'active',
    tier: 'pro'
  },
  // Spot Algorithms
  {
    id: 'spot_momentum',
    name: 'Spot Momentum',
    category: 'spot',
    icon: TrendingUp,
    color: 'bg-green-500/10 text-green-500 border-green-500/20',
    description: 'Momentum-based spot trading with trend confirmation',
    riskLevel: 'Medium',
    avgReturn: '25-45%',
    winRate: 84.2,
    activeUsers: 1247,
    minCapital: 500,
    maxLeverage: '3x',
    timeframe: '15m-4h',
    features: ['Trend analysis', 'Volume confirmation', 'Breakout detection'],
    performance: [
      { date: '2024-01', return: 7.8 },
      { date: '2024-02', return: 12.3 },
      { date: '2024-03', return: 18.7 },
      { date: '2024-04', return: 15.2 },
      { date: '2024-05', return: 22.9 },
      { date: '2024-06', return: 26.4 }
    ],
    status: 'active',
    tier: 'basic'
  },
  {
    id: 'mean_reversion',
    name: 'Mean Reversion',
    category: 'spot',
    icon: Activity,
    color: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
    description: 'Statistical mean reversion with Bollinger Band analysis',
    riskLevel: 'Medium',
    avgReturn: '20-35%',
    winRate: 87.6,
    activeUsers: 892,
    minCapital: 1000,
    maxLeverage: '2x',
    timeframe: '1h-1d',
    features: ['Statistical analysis', 'Bollinger Bands', 'RSI confirmation'],
    performance: [
      { date: '2024-01', return: 5.4 },
      { date: '2024-02', return: 9.8 },
      { date: '2024-03', return: 14.2 },
      { date: '2024-04', return: 11.7 },
      { date: '2024-05', return: 18.9 },
      { date: '2024-06', return: 21.3 }
    ],
    status: 'active',
    tier: 'basic'
  },
  {
    id: 'breakout_strategy',
    name: 'Breakout Trading',
    category: 'spot',
    icon: Zap,
    color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    description: 'Support/resistance breakout with volume validation',
    riskLevel: 'Medium',
    avgReturn: '30-50%',
    winRate: 79.3,
    activeUsers: 634,
    minCapital: 750,
    maxLeverage: '4x',
    timeframe: '30m-2h',
    features: ['S/R levels', 'Volume analysis', 'False breakout filter'],
    performance: [
      { date: '2024-01', return: 9.1 },
      { date: '2024-02', return: 16.8 },
      { date: '2024-03', return: 23.4 },
      { date: '2024-04', return: 19.7 },
      { date: '2024-05', return: 27.2 },
      { date: '2024-06', return: 32.6 }
    ],
    status: 'active',
    tier: 'pro'
  },
  // Algorithmic Trading
  {
    id: 'pairs_trading',
    name: 'Pairs Trading',
    category: 'algorithmic',
    icon: Layers,
    color: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
    description: 'Statistical arbitrage between correlated pairs',
    riskLevel: 'Low',
    avgReturn: '15-25%',
    winRate: 91.2,
    activeUsers: 445,
    minCapital: 2000,
    maxLeverage: '2x',
    timeframe: '4h-1d',
    features: ['Correlation analysis', 'Z-score calculation', 'Market neutral'],
    performance: [
      { date: '2024-01', return: 3.8 },
      { date: '2024-02', return: 6.2 },
      { date: '2024-03', return: 9.7 },
      { date: '2024-04', return: 12.4 },
      { date: '2024-05', return: 15.8 },
      { date: '2024-06', return: 18.9 }
    ],
    status: 'active',
    tier: 'pro'
  },
  {
    id: 'statistical_arbitrage',
    name: 'Statistical Arbitrage',
    category: 'algorithmic',
    icon: BarChart3,
    color: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    description: 'Advanced statistical models for price inefficiencies',
    riskLevel: 'Medium',
    avgReturn: '28-42%',
    winRate: 85.7,
    activeUsers: 278,
    minCapital: 5000,
    maxLeverage: '3x',
    timeframe: '1h-8h',
    features: ['ML models', 'Price prediction', 'Risk parity'],
    performance: [
      { date: '2024-01', return: 6.9 },
      { date: '2024-02', return: 11.4 },
      { date: '2024-03', return: 17.8 },
      { date: '2024-04', return: 24.2 },
      { date: '2024-05', return: 29.7 },
      { date: '2024-06', return: 35.1 }
    ],
    status: 'active',
    tier: 'enterprise'
  },
  {
    id: 'market_making',
    name: 'Market Making',
    category: 'algorithmic',
    icon: Crosshair,
    color: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
    description: 'Automated market making with spread optimization',
    riskLevel: 'Low',
    avgReturn: '18-30%',
    winRate: 88.9,
    activeUsers: 167,
    minCapital: 10000,
    maxLeverage: '2x',
    timeframe: '1s-5m',
    features: ['Spread optimization', 'Inventory management', 'Latency arbitrage'],
    performance: [
      { date: '2024-01', return: 4.2 },
      { date: '2024-02', return: 7.8 },
      { date: '2024-03', return: 11.6 },
      { date: '2024-04', return: 15.9 },
      { date: '2024-05', return: 20.3 },
      { date: '2024-06', return: 24.7 }
    ],
    status: 'active',
    tier: 'enterprise'
  },
  {
    id: 'scalping_strategy',
    name: 'Scalping',
    category: 'algorithmic',
    icon: Timer,
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
    description: 'High-frequency scalping with micro-profit targeting',
    riskLevel: 'Medium',
    avgReturn: '35-55%',
    winRate: 76.4,
    activeUsers: 523,
    minCapital: 1000,
    maxLeverage: '10x',
    timeframe: '1s-1m',
    features: ['HFT execution', 'Micro-profits', 'Low latency'],
    performance: [
      { date: '2024-01', return: 11.7 },
      { date: '2024-02', return: 19.3 },
      { date: '2024-03', return: 26.8 },
      { date: '2024-04', return: 31.2 },
      { date: '2024-05', return: 38.7 },
      { date: '2024-06', return: 44.9 }
    ],
    status: 'active',
    tier: 'pro'
  }
];

const categories = [
  { id: 'all', name: 'All Strategies', count: tradingStrategies.length },
  { id: 'derivatives', name: 'Derivatives', count: tradingStrategies.filter(s => s.category === 'derivatives').length },
  { id: 'spot', name: 'Spot Trading', count: tradingStrategies.filter(s => s.category === 'spot').length },
  { id: 'algorithmic', name: 'Algorithmic', count: tradingStrategies.filter(s => s.category === 'algorithmic').length },
];

const tiers = [
  { id: 'all', name: 'All Tiers' },
  { id: 'basic', name: 'Basic', color: 'bg-gray-500' },
  { id: 'pro', name: 'Pro', color: 'bg-blue-500' },
  { id: 'enterprise', name: 'Enterprise', color: 'bg-purple-500' },
];

const StrategyMarketplace: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedTier, setSelectedTier] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('winRate');
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [showExecutionModal, setShowExecutionModal] = useState(false);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [strategyToExecute, setStrategyToExecute] = useState<any>(null);
  
  const { strategies, availableStrategies, loading, executing, actions } = useStrategies();
  const { balance, profitPotential, actions: creditActions } = useCredits();

  const filteredStrategies = tradingStrategies.filter(strategy => {
    const matchesCategory = selectedCategory === 'all' || strategy.category === selectedCategory;
    const matchesTier = selectedTier === 'all' || strategy.tier === selectedTier;
    const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         strategy.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesCategory && matchesTier && matchesSearch;
  }).sort((a, b) => {
    if (sortBy === 'winRate') return b.winRate - a.winRate;
    if (sortBy === 'return') return parseFloat(b.avgReturn.split('-')[1]) - parseFloat(a.avgReturn.split('-')[1]);
    if (sortBy === 'users') return b.activeUsers - a.activeUsers;
    return 0;
  });

  // Use the helper functions defined above

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Store className="h-8 w-8 text-primary" />
            Strategy Marketplace
            <Crown className="h-6 w-6 text-yellow-500" />
          </h1>
          <p className="text-muted-foreground">
            Professional trading strategies with institutional-grade performance
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Advanced Filters
          </Button>
          <Button className="gap-2">
            <Sparkles className="h-4 w-4" />
            Create Strategy
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search strategies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            {categories.map(category => (
              <SelectItem key={category.id} value={category.id}>
                {category.name} ({category.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={selectedTier} onValueChange={setSelectedTier}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Tier" />
          </SelectTrigger>
          <SelectContent>
            {tiers.map(tier => (
              <SelectItem key={tier.id} value={tier.id}>
                {tier.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="winRate">Win Rate</SelectItem>
            <SelectItem value="return">Return</SelectItem>
            <SelectItem value="users">Users</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Strategy Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredStrategies.map((strategy, index) => (
          <motion.div
            key={strategy.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="relative overflow-hidden hover:shadow-lg transition-shadow cursor-pointer" 
                  onClick={() => setSelectedStrategy(strategy.id)}>
              <div 
                className="absolute top-0 left-0 w-full h-1" 
                style={{ backgroundColor: strategy.color.match(/text-(\w+)-500/)?.[0]?.replace('text-', '') }}
              />
              
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded ${strategy.color}`}>
                      <strategy.icon className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{strategy.name}</CardTitle>
                      <CardDescription className="capitalize">{strategy.category}</CardDescription>
                    </div>
                  </div>
                  {getTierBadge(strategy.tier)}
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {strategy.description}
                </p>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Win Rate</div>
                    <div className="font-medium text-green-500">{strategy.winRate}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Avg Return</div>
                    <div className="font-medium">{strategy.avgReturn}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Risk Level</div>
                    <div className={`font-medium ${getRiskColor(strategy.riskLevel)}`}>
                      {strategy.riskLevel}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Users</div>
                    <div className="font-medium">{formatNumber(strategy.activeUsers)}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Performance</span>
                    <span className="text-green-500">+{strategy.performance[strategy.performance.length - 1].return}%</span>
                  </div>
                  <Progress value={strategy.winRate} className="h-2" />
                </div>

                <div className="flex flex-wrap gap-1">
                  {strategy.features.slice(0, 2).map((feature, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {feature}
                    </Badge>
                  ))}
                  {strategy.features.length > 2 && (
                    <Badge variant="secondary" className="text-xs">
                      +{strategy.features.length - 2} more
                    </Badge>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    className="flex-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Check if user owns this strategy or needs to purchase
                      const creditCost = 25; // Would come from API
                      if (balance.available_credits >= creditCost) {
                        setStrategyToExecute(strategy);
                        setShowExecutionModal(true);
                      } else {
                        // Show purchase modal
                        setStrategyToExecute({
                          ...strategy,
                          credit_cost: creditCost
                        });
                        setShowPurchaseModal(true);
                      }
                    }}
                    disabled={executing}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    {balance.available_credits >= 25 ? 'Execute' : 'Purchase'}
                  </Button>
                  <Button size="sm" variant="outline">
                    <Eye className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {filteredStrategies.length === 0 && (
        <div className="text-center py-12">
          <Store className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium">No strategies found</h3>
          <p className="text-muted-foreground">Try adjusting your filters or search terms</p>
        </div>
      )}

      {/* Strategy Execution Modal */}
      {showExecutionModal && strategyToExecute && (
        <StrategyExecutionModal
          isOpen={showExecutionModal}
          onClose={() => {
            setShowExecutionModal(false);
            setStrategyToExecute(null);
          }}
          strategy={strategyToExecute}
          executing={executing}
        />
      )}

      {/* Strategy Purchase Modal */}
      {showPurchaseModal && strategyToExecute && (
        <StrategyPurchaseModal
          isOpen={showPurchaseModal}
          onClose={() => {
            setShowPurchaseModal(false);
            setStrategyToExecute(null);
          }}
          strategy={strategyToExecute}
        />
      )}

      {/* Strategy Detail Modal */}
      <AnimatePresence>
        {selectedStrategy && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setSelectedStrategy(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-background rounded-lg max-w-6xl w-full max-h-[90vh] overflow-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <StrategyDetailContent 
                strategy={tradingStrategies.find(s => s.id === selectedStrategy)} 
                onClose={() => setSelectedStrategy(null)}
                onExecute={(strategy) => {
                  setSelectedStrategy(null);
                  setStrategyToExecute(strategy);
                  setShowExecutionModal(true);
                }}
                onPurchase={(strategy) => {
                  setSelectedStrategy(null);
                  setStrategyToExecute(strategy);
                  setShowPurchaseModal(true);
                }}
                userCredits={balance.available_credits}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Helper functions moved outside component
const getRiskColor = (risk: string) => {
  switch (risk) {
    case 'Low': return 'text-green-500';
    case 'Medium': return 'text-yellow-500';
    case 'High': return 'text-red-500';
    default: return 'text-gray-500';
  }
};

const getTierBadge = (tier: string) => {
  const tierConfig = tiers.find(t => t.id === tier);
  if (!tierConfig) return null;
  
  return (
    <Badge className={`${tierConfig.color} text-white`}>
      {tierConfig.name}
    </Badge>
  );
};

// Strategy Detail Content Component
interface StrategyDetailContentProps {
  strategy: any;
  onClose: () => void;
  onExecute: (strategy: any) => void;
  onPurchase: (strategy: any) => void;
  userCredits: number;
}

const StrategyDetailContent: React.FC<StrategyDetailContentProps> = ({
  strategy,
  onClose,
  onExecute,
  onPurchase,
  userCredits
}) => {
  if (!strategy) return null;

  const canAfford = userCredits >= 25; // Mock credit cost
  const hasStrategy = Math.random() > 0.5; // Mock ownership

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-lg ${strategy.color}`}>
            <strategy.icon className="h-8 w-8" />
          </div>
          <div>
            <h2 className="text-3xl font-bold">{strategy.name}</h2>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="secondary" className="capitalize">
                {strategy.category} Trading
              </Badge>
              {getTierBadge(strategy.tier)}
              <Badge variant="outline" className={getRiskColor(strategy.riskLevel)}>
                {strategy.riskLevel} Risk
              </Badge>
            </div>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-6 w-6" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Performance Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="h-5 w-5" />
                Performance History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsLineChart data={strategy.performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip 
                      formatter={(value) => [`${value}%`, 'Return']}
                      labelFormatter={(label) => `Month: ${label}`}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="return" 
                      stroke="#22c55e" 
                      strokeWidth={2}
                      dot={{ fill: '#22c55e', strokeWidth: 2 }}
                    />
                  </RechartsLineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Strategy Description */}
          <Card>
            <CardHeader>
              <CardTitle>Strategy Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                {strategy.description} This advanced trading algorithm leverages cutting-edge 
                market analysis techniques combined with risk management protocols to maximize 
                returns while protecting capital.
              </p>
              
              <div className="space-y-3">
                <h4 className="font-semibold">Key Features:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {strategy.features.map((feature: string, index: number) => (
                    <div key={index} className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t">
                <h4 className="font-semibold mb-3">Trading Specifications:</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Timeframe</div>
                    <div className="font-medium">{strategy.timeframe}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Min Capital</div>
                    <div className="font-medium">{formatCurrency(strategy.minCapital)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Max Leverage</div>
                    <div className="font-medium">{strategy.maxLeverage}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Category</div>
                    <div className="font-medium capitalize">{strategy.category}</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Risk Analysis */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Risk Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold text-red-500">
                    {strategy.riskLevel === 'High' ? '8.5' : strategy.riskLevel === 'Medium' ? '5.2' : '2.8'}
                  </div>
                  <div className="text-sm text-muted-foreground">Risk Score</div>
                  <div className="text-xs mt-1">(1-10 scale)</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-500">
                    {strategy.riskLevel === 'High' ? '15.2%' : strategy.riskLevel === 'Medium' ? '8.7%' : '4.1%'}
                  </div>
                  <div className="text-sm text-muted-foreground">Max Drawdown</div>
                  <div className="text-xs mt-1">Historical</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold text-green-500">
                    {(strategy.winRate / 20).toFixed(1)}
                  </div>
                  <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
                  <div className="text-xs mt-1">Risk-adjusted</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Key Metrics */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Win Rate</span>
                  <span className="font-bold text-green-500">{strategy.winRate}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Return</span>
                  <span className="font-bold">{strategy.avgReturn}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Active Users</span>
                  <span className="font-bold">{formatNumber(strategy.activeUsers)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Risk Level</span>
                  <span className={`font-bold ${getRiskColor(strategy.riskLevel)}`}>
                    {strategy.riskLevel}
                  </span>
                </div>
              </div>

              <div className="pt-4 border-t">
                <div className="text-sm text-muted-foreground mb-2">Performance Trend</div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium text-green-500">
                    +{strategy.performance[strategy.performance.length - 1].return}% Last Month
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* User Reviews */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5" />
                User Reviews
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[1,2,3,4,5].map((star) => (
                      <Star key={star} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  <span className="text-sm text-muted-foreground">4.8 (127 reviews)</span>
                </div>
                
                <div className="space-y-3">
                  <div className="border-l-2 border-green-500 pl-3">
                    <div className="text-sm font-medium">CryptoTrader_Pro</div>
                    <div className="text-xs text-muted-foreground">2 days ago</div>
                    <div className="text-sm mt-1">
                      "Excellent strategy! Made 15% profit in just one week."
                    </div>
                  </div>
                  
                  <div className="border-l-2 border-blue-500 pl-3">
                    <div className="text-sm font-medium">InvestorAlpha</div>
                    <div className="text-xs text-muted-foreground">1 week ago</div>
                    <div className="text-sm mt-1">
                      "Consistent returns with good risk management."
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {hasStrategy ? (
                  <Button 
                    className="w-full" 
                    onClick={() => onExecute(strategy)}
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Execute Strategy
                  </Button>
                ) : canAfford ? (
                  <Button 
                    className="w-full" 
                    onClick={() => onPurchase({...strategy, credit_cost: 25})}
                  >
                    <ShoppingCart className="h-4 w-4 mr-2" />
                    Purchase for 25 Credits
                  </Button>
                ) : (
                  <Button className="w-full" disabled>
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    Insufficient Credits
                  </Button>
                )}
                
                <Button variant="outline" className="w-full">
                  <Users className="h-4 w-4 mr-2" />
                  Join Community
                </Button>
              </div>
              
              <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                <div className="text-xs text-muted-foreground text-center">
                  💡 Pro Tip: Start with paper trading to test the strategy risk-free
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default StrategyMarketplace;
