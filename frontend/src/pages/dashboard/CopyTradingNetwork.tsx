import React, { useState, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Copy,
  Star,
  Shield,
  Award,
  Trophy,
  Target,
  Zap,
  Crown,
  DollarSign,
  Activity,
  BarChart3,
  PieChart,
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Filter,
  Search,
  Settings,
  Bell,
  Eye,
  EyeOff,
  UserPlus,
  UserMinus,
  UserCheck,
  MessageSquare,
  Heart,
  Share2,
  Bookmark,
  TrendingUp as TrendIcon,
  ArrowUpRight,
  ArrowDownRight,
  ChevronUp,
  ChevronDown,
  MoreVertical,
  Globe,
  Lock,
  Unlock,
  Verified,
  Badge as BadgeIcon,
  Signal,
  Wifi,
  WifiOff,
  Volume2,
  VolumeX,
  Play,
  Pause,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Avatar } from "@/components/ui/avatar";
import { formatCurrency, formatPercentage, formatNumber } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";

// API Service
const apiService = {
  async getSignalProviders(params: any = {}) {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`/api/v1/copy-trading/providers?${query}`);
    if (!response.ok) throw new Error('Failed to fetch providers');
    return response.json();
  },

  async getMyCopyTradingStats() {
    const response = await fetch('/api/v1/copy-trading/my-stats');
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async getFollowing() {
    const response = await fetch('/api/v1/copy-trading/following');
    if (!response.ok) throw new Error('Failed to fetch following');
    return response.json();
  },

  async getCopiedTrades() {
    const response = await fetch('/api/v1/copy-trading/copied-trades');
    if (!response.ok) throw new Error('Failed to fetch trades');
    return response.json();
  },

  async getLeaderboard(period: string = '30d') {
    const response = await fetch(`/api/v1/copy-trading/leaderboard?period=${period}`);
    if (!response.ok) throw new Error('Failed to fetch leaderboard');
    return response.json();
  },

  async followStrategy(strategyId: string, allocation: number, maxDrawdown: number) {
    const response = await fetch(`/api/v1/copy-trading/follow/${strategyId}?allocation_percentage=${allocation}&max_drawdown=${maxDrawdown}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to follow strategy');
    return response.json();
  }
};

// Fallback mock data (kept as backup)
const mockSignalProviders = [
  {
    id: 1,
    username: "CryptoWhale",
    avatar: "🐋",
    verified: true,
    tier: "platinum",
    followers: 12453,
    winRate: 78.5,
    avgReturn: 24.3,
    totalReturn: 1245.6,
    riskScore: 3,
    monthlyFee: 99,
    signals30d: 145,
    successRate: 82,
    specialties: ["BTC", "ETH", "DeFi"],
    performance: [
      { month: "Jan", return: 18.5 },
      { month: "Feb", return: 22.3 },
      { month: "Mar", return: 31.2 },
      { month: "Apr", return: 15.8 },
      { month: "May", return: 28.4 },
      { month: "Jun", return: 24.3 },
    ],
    recentSignals: [
      {
        pair: "BTC/USDT",
        type: "LONG",
        entry: 43250,
        target: 44500,
        status: "active",
        pnl: 2.3,
      },
      {
        pair: "ETH/USDT",
        type: "SHORT",
        entry: 2280,
        target: 2150,
        status: "closed",
        pnl: 5.7,
      },
      {
        pair: "SOL/USDT",
        type: "LONG",
        entry: 98.5,
        target: 105,
        status: "active",
        pnl: 3.2,
      },
    ],
  },
  {
    id: 2,
    username: "AITraderPro",
    avatar: "🤖",
    verified: true,
    tier: "gold",
    followers: 8932,
    winRate: 72.3,
    avgReturn: 18.7,
    totalReturn: 892.4,
    riskScore: 2,
    monthlyFee: 79,
    signals30d: 98,
    successRate: 75,
    specialties: ["AI Signals", "Scalping", "Futures"],
    performance: [
      { month: "Jan", return: 15.2 },
      { month: "Feb", return: 19.8 },
      { month: "Mar", return: 22.1 },
      { month: "Apr", return: 12.4 },
      { month: "May", return: 20.3 },
      { month: "Jun", return: 18.7 },
    ],
    recentSignals: [],
  },
  {
    id: 3,
    username: "DeFiMaster",
    avatar: "💎",
    verified: true,
    tier: "platinum",
    followers: 6543,
    winRate: 81.2,
    avgReturn: 32.1,
    totalReturn: 2134.5,
    riskScore: 4,
    monthlyFee: 149,
    signals30d: 67,
    successRate: 85,
    specialties: ["DeFi", "Yield Farming", "NFTs"],
    performance: [
      { month: "Jan", return: 28.5 },
      { month: "Feb", return: 35.2 },
      { month: "Mar", return: 41.3 },
      { month: "Apr", return: 22.8 },
      { month: "May", return: 38.6 },
      { month: "Jun", return: 32.1 },
    ],
    recentSignals: [],
  },
  {
    id: 4,
    username: "SwingKing",
    avatar: "👑",
    verified: false,
    tier: "silver",
    followers: 4321,
    winRate: 68.9,
    avgReturn: 14.2,
    totalReturn: 567.8,
    riskScore: 2,
    monthlyFee: 49,
    signals30d: 45,
    successRate: 70,
    specialties: ["Swing Trading", "Altcoins"],
    performance: [],
    recentSignals: [],
  },
];

// Fallback mock stats
const mockMyStats = {
  following: 3,
  totalInvested: 25000,
  currentValue: 31250,
  totalReturn: 6250,
  returnPct: 25,
  winRate: 71.2,
  activeCopies: 12,
  monthlyProfit: 1850,
  bestProvider: "CryptoWhale",
  worstProvider: "SwingKing",
};

// Fallback mock copied trades
const mockActiveCopiedTrades = [
  {
    id: 1,
    provider: "CryptoWhale",
    pair: "BTC/USDT",
    type: "LONG",
    entry: 43250,
    current: 43680,
    pnl: 430,
    pnlPct: 0.99,
    status: "active",
    copiedAt: "2h ago",
  },
  {
    id: 2,
    provider: "AITraderPro",
    pair: "ETH/USDT",
    type: "SHORT",
    entry: 2280,
    current: 2245,
    pnl: 350,
    pnlPct: 1.54,
    status: "active",
    copiedAt: "4h ago",
  },
  {
    id: 3,
    provider: "DeFiMaster",
    pair: "UNI/USDT",
    type: "LONG",
    entry: 5.45,
    current: 5.68,
    pnl: 230,
    pnlPct: 4.22,
    status: "active",
    copiedAt: "6h ago",
  },
  {
    id: 4,
    provider: "CryptoWhale",
    pair: "SOL/USDT",
    type: "LONG",
    entry: 98.5,
    current: 101.8,
    pnl: 330,
    pnlPct: 3.35,
    status: "active",
    copiedAt: "1d ago",
  },
];

// Fallback mock leaderboard
const mockLeaderboardData = [
  {
    rank: 1,
    provider: "CryptoWhale",
    return30d: 45.6,
    return90d: 134.2,
    followers: 12453,
    tier: "platinum",
  },
  {
    rank: 2,
    provider: "DeFiMaster",
    return30d: 42.3,
    return90d: 128.7,
    followers: 6543,
    tier: "platinum",
  },
  {
    rank: 3,
    provider: "AITraderPro",
    return30d: 38.7,
    return90d: 98.4,
    followers: 8932,
    tier: "gold",
  },
  {
    rank: 4,
    provider: "QuantumTrader",
    return30d: 35.2,
    return90d: 89.3,
    followers: 5234,
    tier: "gold",
  },
  {
    rank: 5,
    provider: "SwingKing",
    return30d: 28.9,
    return90d: 72.1,
    followers: 4321,
    tier: "silver",
  },
];

const CopyTradingNetwork: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("discover");
  const [selectedProvider, setSelectedProvider] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filterTier, setFilterTier] = useState<string>("all");
  const [filterSpecialty, setFilterSpecialty] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("returns");
  const [autoCopy, setAutoCopy] = useState<boolean>(true);
  const [riskLimit, setRiskLimit] = useState<number>(3);
  const [showOnlyVerified, setShowOnlyVerified] = useState<boolean>(false);

  // Real data state
  const [signalProviders, setSignalProviders] = useState<any[]>([]);
  const [myStats, setMyStats] = useState<any>(mockMyStats);
  const [activeCopiedTrades, setActiveCopiedTrades] = useState<any[]>([]);
  const [leaderboardData, setLeaderboardData] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  // Load real data on component mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load data in parallel
      const [providersRes, statsRes, tradesRes, leaderRes] = await Promise.allSettled([
        apiService.getSignalProviders({
          verified_only: showOnlyVerified,
          tier: filterTier === 'all' ? undefined : filterTier,
          sort_by: sortBy
        }),
        apiService.getMyCopyTradingStats(),
        apiService.getCopiedTrades(),
        apiService.getLeaderboard('30d')
      ]);

      // Handle providers
      if (providersRes.status === 'fulfilled' && providersRes.value.success) {
        setSignalProviders(providersRes.value.data || []);
      } else {
        console.warn('Using fallback provider data');
        setSignalProviders(mockSignalProviders);
      }

      // Handle stats
      if (statsRes.status === 'fulfilled' && statsRes.value.success) {
        setMyStats(statsRes.value.data);
      }

      // Handle trades
      if (tradesRes.status === 'fulfilled' && tradesRes.value.success) {
        setActiveCopiedTrades(tradesRes.value.data || []);
      } else {
        setActiveCopiedTrades(mockActiveCopiedTrades);
      }

      // Handle leaderboard
      if (leaderRes.status === 'fulfilled' && leaderRes.value.success) {
        setLeaderboardData(leaderRes.value.data || []);
      } else {
        setLeaderboardData(mockLeaderboardData);
      }

    } catch (err) {
      console.error('Failed to load copy trading data:', err);
      setError('Failed to load data. Using cached data.');
      // Use fallback data
      setSignalProviders(mockSignalProviders);
      setActiveCopiedTrades(mockActiveCopiedTrades);
      setLeaderboardData(mockLeaderboardData);
    } finally {
      setLoading(false);
    }
  };

  // Reload data when filters change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (signalProviders.length > 0) { // Only reload if we have initial data
        loadData();
      }
    }, 500); // Debounce

    return () => clearTimeout(timeoutId);
  }, [showOnlyVerified, filterTier, sortBy]);

  // Filter and sort providers based on controls
  const filteredProviders = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    let data = signalProviders.filter(p => {
      const matchesSearch =
        !q ||
        p.username.toLowerCase().includes(q) ||
        p.specialties.some((s: string) => s.toLowerCase().includes(q));
      const matchesTier = filterTier === "all" || p.tier === filterTier;
      const matchesSpec =
        filterSpecialty === "all" ||
        p.specialties.some((s: string) => s.toLowerCase().includes(filterSpecialty));
      const matchesVerified = !showOnlyVerified || p.verified;
      return matchesSearch && matchesTier && matchesSpec && matchesVerified;
    });
    
    data.sort((a, b) => {
      switch (sortBy) {
        case "winrate":
          return b.winRate - a.winRate;
        case "followers":
          return b.followers - a.followers;
        case "signals":
          return b.signals30d - a.signals30d;
        case "returns":
        default:
          return b.avgReturn - a.avgReturn;
      }
    });
    
    return data;
  }, [searchQuery, filterTier, filterSpecialty, sortBy, showOnlyVerified]);

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "platinum":
        return "from-gray-400 to-gray-600";
      case "gold":
        return "from-yellow-400 to-yellow-600";
      case "silver":
        return "from-gray-300 to-gray-500";
      default:
        return "from-blue-400 to-blue-600";
    }
  };

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case "platinum":
        return <Crown className="w-4 h-4" />;
      case "gold":
        return <Trophy className="w-4 h-4" />;
      case "silver":
        return <Award className="w-4 h-4" />;
      default:
        return <Star className="w-4 h-4" />;
    }
  };

  const getRiskColor = (score: number) => {
    if (score <= 2) return "text-green-600";
    if (score <= 3) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Copy Trading Network
          </h1>
          <p className="text-gray-500 mt-1">
            Follow and copy successful traders automatically
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm">
            <Bell className="w-4 h-4 mr-2" />
            Signal Alerts
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="w-4 h-4 mr-2" />
            Copy Settings
          </Button>
          <Button className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
            <UserPlus className="w-4 h-4 mr-2" />
            Find Providers
          </Button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-indigo-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-indigo-400">
                  Total Return
                </p>
                <p className="text-2xl font-bold mt-2 text-white">
                  +{formatCurrency(myStats.totalReturn)}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <ArrowUpRight className="w-4 h-4 text-green-400" />
                  <p className="text-sm font-medium text-green-400">
                    +{formatPercentage(myStats.returnPct)}
                  </p>
                </div>
              </div>
              <div className="p-3 bg-indigo-500/10 rounded-xl">
                <TrendingUp className="w-6 h-6 text-indigo-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-cyan-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-blue-400">Following</p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {myStats.following}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <p className="text-sm font-medium text-gray-400">
                    {myStats.activeCopies} active copies
                  </p>
                </div>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-green-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-emerald-400">Win Rate</p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {formatPercentage(myStats.winRate)}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <p className="text-sm font-medium text-gray-400">
                    Last 30 days
                  </p>
                </div>
              </div>
              <div className="p-3 bg-emerald-500/10 rounded-xl">
                <Target className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-orange-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-red-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-orange-400">
                  Monthly Profit
                </p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {formatCurrency(myStats.monthlyProfit)}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <p className="text-sm font-medium text-gray-400">
                    This month
                  </p>
                </div>
              </div>
              <div className="p-3 bg-orange-500/10 rounded-xl">
                <DollarSign className="w-6 h-6 text-orange-400" />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="discover">Discover Providers</TabsTrigger>
          <TabsTrigger value="following">Following</TabsTrigger>
          <TabsTrigger value="copied">Copied Trades</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
          <TabsTrigger value="signals">Signal Feed</TabsTrigger>
          <TabsTrigger value="performance">My Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="discover">
          {/* Filters */}
          <Card className="p-4 mb-6">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    placeholder="Search providers..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Select value={filterTier} onValueChange={setFilterTier}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="platinum">Platinum</SelectItem>
                  <SelectItem value="gold">Gold</SelectItem>
                  <SelectItem value="silver">Silver</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={filterSpecialty}
                onValueChange={setFilterSpecialty}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Filter by specialty" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Specialties</SelectItem>
                  <SelectItem value="btc">BTC Trading</SelectItem>
                  <SelectItem value="defi">DeFi</SelectItem>
                  <SelectItem value="scalping">Scalping</SelectItem>
                  <SelectItem value="swing">Swing Trading</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="returns">Highest Returns</SelectItem>
                  <SelectItem value="winrate">Best Win Rate</SelectItem>
                  <SelectItem value="followers">Most Followers</SelectItem>
                  <SelectItem value="signals">Most Signals</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2">
                <Switch
                  checked={showOnlyVerified}
                  onCheckedChange={setShowOnlyVerified}
                />
                <span className="text-sm">Verified Only</span>
              </div>
            </div>
          </Card>

          {/* Loading State */}
          {loading && (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3 text-muted-foreground">Loading copy trading data...</span>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-destructive" />
                <span className="text-destructive font-medium">Warning</span>
              </div>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {/* Provider Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredProviders.map((provider) => (
              <motion.div
                key={provider.id}
                whileHover={{ scale: 1.02 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Card className="p-6 hover:shadow-lg transition-all">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="text-4xl">{provider.avatar}</div>
                        {provider.verified && (
                          <div className="absolute -bottom-1 -right-1 bg-blue-500 rounded-full p-1">
                            <CheckCircle className="w-3 h-3 text-white" />
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-lg">
                            {provider.username}
                          </h3>
                          <div
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gradient-to-r ${getTierColor(
                              provider.tier
                            )} text-white text-xs`}
                          >
                            {getTierIcon(provider.tier)}
                            <span>{provider.tier}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Users className="w-3 h-3" />
                            {formatNumber(provider.followers)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Signal className="w-3 h-3" />
                            {provider.signals30d} signals/30d
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      className="bg-gradient-to-r from-purple-600 to-pink-600 text-white"
                      onClick={async () => {
                        try {
                          await apiService.followStrategy(provider.id.toString(), 10, 20); // 10% allocation, 20% max drawdown
                          toast({
                            title: 'Success',
                            description: `Now following ${provider.username}`,
                          });
                          loadData(); // Refresh data
                        } catch (err) {
                          toast({
                            title: 'Error',
                            description: 'Failed to follow strategy',
                            variant: 'destructive'
                          });
                        }
                      }}
                      disabled={loading}
                    >
                      <UserPlus className="w-4 h-4 mr-1" />
                      {loading ? 'Following...' : 'Follow'}
                    </Button>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-gray-500">Win Rate</p>
                      <p className="text-lg font-semibold text-green-600">
                        {formatPercentage(provider.winRate)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Avg Return</p>
                      <p className="text-lg font-semibold">
                        {formatPercentage(provider.avgReturn)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Risk Score</p>
                      <p
                        className={`text-lg font-semibold ${getRiskColor(
                          provider.riskScore
                        )}`}
                      >
                        {provider.riskScore}/5
                      </p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">
                      Performance (6 months)
                    </p>
                    {provider.performance.length > 0 && (
                      <ResponsiveContainer width="100%" height={60}>
                        <AreaChart data={provider.performance}>
                          <Area
                            type="monotone"
                            dataKey="return"
                            stroke="#8b5cf6"
                            fill="#8b5cf6"
                            fillOpacity={0.3}
                            strokeWidth={2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t">
                    <div className="flex gap-2">
                      {provider.specialties.slice(0, 3).map((specialty) => (
                        <Badge key={specialty} variant="secondary">
                          {specialty}
                        </Badge>
                      ))}
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">
                        ${provider.monthlyFee}/mo
                      </p>
                      <p className="text-xs text-gray-500">Subscription</p>
                    </div>
                  </div>

                  {provider.recentSignals.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-xs text-gray-500 mb-2">
                        Recent Signals
                      </p>
                      <div className="space-y-2">
                        {provider.recentSignals
                          .slice(0, 2)
                          .map((signal, idx) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between text-sm"
                            >
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={
                                    signal.type === "LONG"
                                      ? "default"
                                      : "destructive"
                                  }
                                >
                                  {signal.type}
                                </Badge>
                                <span>{signal.pair}</span>
                              </div>
                              <span
                                className={`font-medium ${
                                  signal.pnl >= 0
                                    ? "text-green-600"
                                    : "text-red-600"
                                }`}
                              >
                                {signal.pnl >= 0 ? "+" : ""}
                                {signal.pnl}%
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="following">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">
              Providers You're Following
            </h3>
            <div className="space-y-4">
              {signalProviders.slice(0, 3).map((provider) => (
                <div
                  key={provider.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">{provider.avatar}</div>
                    <div>
                      <p className="font-semibold">{provider.username}</p>
                      <p className="text-sm text-gray-500">
                        Following since Dec 2023
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div>
                      <p className="text-sm text-gray-500">Your Return</p>
                      <p className="text-lg font-semibold text-green-600">
                        +{formatPercentage(provider.avgReturn)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch checked={true} />
                      <span className="text-sm">Auto-copy</span>
                    </div>
                    <Button variant="outline" size="sm">
                      <Settings className="w-4 h-4 mr-2" />
                      Settings
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="copied">
          <Card className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold">Active Copied Trades</h3>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch checked={autoCopy} onCheckedChange={setAutoCopy} />
                  <span className="text-sm">Auto-copy enabled</span>
                </div>
                <Badge variant="default">
                  {activeCopiedTrades.length} Active
                </Badge>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Provider</th>
                    <th className="text-left py-2">Pair</th>
                    <th className="text-left py-2">Type</th>
                    <th className="text-left py-2">Entry</th>
                    <th className="text-left py-2">Current</th>
                    <th className="text-left py-2">P&L</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-left py-2">Copied</th>
                    <th className="text-left py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {activeCopiedTrades.map((trade) => (
                    <tr key={trade.id} className="border-b hover:bg-gray-50">
                      <td className="py-3">{trade.provider}</td>
                      <td className="py-3 font-medium">{trade.pair}</td>
                      <td className="py-3">
                        <Badge
                          variant={
                            trade.type === "LONG" ? "default" : "destructive"
                          }
                        >
                          {trade.type}
                        </Badge>
                      </td>
                      <td className="py-3">${trade.entry}</td>
                      <td className="py-3">${trade.current}</td>
                      <td className="py-3">
                        <div
                          className={`font-semibold ${
                            trade.pnl >= 0 ? "text-green-600" : "text-red-600"
                          }`}
                        >
                          {trade.pnl >= 0 ? "+" : ""}
                          {formatCurrency(trade.pnl)}
                          <span className="text-xs ml-1">
                            ({trade.pnlPct}%)
                          </span>
                        </div>
                      </td>
                      <td className="py-3">
                        <Badge variant="default">Active</Badge>
                      </td>
                      <td className="py-3 text-sm text-gray-500">
                        {trade.copiedAt}
                      </td>
                      <td className="py-3">
                        <Button variant="outline" size="sm">
                          Close
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="leaderboard">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6">Top Signal Providers</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Rank</th>
                    <th className="text-left py-2">Provider</th>
                    <th className="text-left py-2">30d Return</th>
                    <th className="text-left py-2">90d Return</th>
                    <th className="text-left py-2">Followers</th>
                    <th className="text-left py-2">Tier</th>
                    <th className="text-left py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboardData.map((item) => (
                    <tr key={item.rank} className="border-b hover:bg-gray-50">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          {item.rank === 1 && (
                            <Trophy className="w-5 h-5 text-yellow-500" />
                          )}
                          {item.rank === 2 && (
                            <Trophy className="w-5 h-5 text-gray-400" />
                          )}
                          {item.rank === 3 && (
                            <Trophy className="w-5 h-5 text-orange-600" />
                          )}
                          {item.rank > 3 && (
                            <span className="ml-6">{item.rank}</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 font-semibold">{item.provider}</td>
                      <td className="py-3 text-green-600 font-medium">
                        +{formatPercentage(item.return30d)}
                      </td>
                      <td className="py-3 text-green-600 font-medium">
                        +{formatPercentage(item.return90d)}
                      </td>
                      <td className="py-3">{formatNumber(item.followers)}</td>
                      <td className="py-3">
                        <div
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gradient-to-r ${getTierColor(
                            item.tier
                          )} text-white text-xs`}
                        >
                          {getTierIcon(item.tier)}
                          <span>{item.tier}</span>
                        </div>
                      </td>
                      <td className="py-3">
                        <Button variant="outline" size="sm">
                          View Profile
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="signals">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Live Signal Feed</h3>
            <p className="text-gray-500">
              Real-time signals from providers you follow...
            </p>
          </Card>
        </TabsContent>

        <TabsContent value="performance">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">
              Your Copy Trading Performance
            </h3>
            <p className="text-gray-500">
              Detailed performance analytics coming soon...
            </p>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CopyTradingNetwork;
