import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Target,
  Award,
  Zap,
  Clock,
  Calendar,
  Filter,
  Download,
  Settings,
  RefreshCw,
  Eye,
  EyeOff,
  ArrowUpRight,
  ArrowDownRight,
  PieChart,
  LineChart,
  AreaChart,
  Layers,
  Database,
  Server,
  Globe,
  Users,
  Shield,
  AlertTriangle,
  CheckCircle,
  Info,
  Maximize2,
  Minimize2,
  Grid,
  List,
  Search,
  Share2,
  Bookmark,
  Bell,
  Mail,
  FileText,
  Printer,
  Monitor,
  Smartphone,
  Tablet,
  Wifi,
  WifiOff,
  Battery,
  Signal,
  Volume2,
  VolumeX,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Repeat,
  Shuffle,
  Heart,
  Star,
  Flag,
  Tag,
  Hash,
  AtSign,
  Phone,
  MessageSquare,
  Video,
  Camera,
  Mic,
  MicOff,
  Image,
  Paperclip,
  Link2,
  ExternalLink,
  Copy,
  Scissors,
  Edit,
  Trash2,
  Archive,
  Folder,
  FolderOpen,
  File,
  FileText as FileIcon,
  Plus,
  Minus,
  X,
  Check,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsUp,
  ChevronsDown,
  ChevronsLeft,
  ChevronsRight,
  MoreVertical,
  MoreHorizontal,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { formatCurrency, formatPercentage, formatNumber } from "@/lib/utils";
import {
  LineChart as RechartsLineChart,
  Line,
  AreaChart as RechartsAreaChart,
  Area,
  BarChart as RechartsBarChart,
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
  ComposedChart,
  Scatter,
  ScatterChart,
  ZAxis,
  Treemap,
  Sankey,
  FunnelChart,
  Funnel,
  LabelList,
} from "recharts";

// Advanced Analytics Data
const portfolioMetrics = {
  totalValue: 2847593.45,
  totalPnL: 847593.45,
  totalPnLPct: 42.3,
  sharpeRatio: 2.87,
  maxDrawdown: -8.4,
  winRate: 73.2,
  profitFactor: 2.34,
  avgWinSize: 2450.67,
  avgLossSize: -1245.89,
  volatility: 12.4,
  beta: 0.87,
  alpha: 15.6,
  informationRatio: 1.45,
  sortinoRatio: 3.21,
  calmarRatio: 4.12,
};

// Performance over time
const performanceData = [
  {
    date: "2024-01",
    portfolio: 2000000,
    benchmark: 2000000,
    drawdown: 0,
    volume: 1200000,
  },
  {
    date: "2024-02",
    portfolio: 2150000,
    benchmark: 2080000,
    drawdown: -2.1,
    volume: 1350000,
  },
  {
    date: "2024-03",
    portfolio: 2280000,
    benchmark: 2120000,
    drawdown: -1.8,
    volume: 1480000,
  },
  {
    date: "2024-04",
    portfolio: 2420000,
    benchmark: 2200000,
    drawdown: -3.2,
    volume: 1620000,
  },
  {
    date: "2024-05",
    portfolio: 2680000,
    benchmark: 2350000,
    drawdown: -1.5,
    volume: 1850000,
  },
  {
    date: "2024-06",
    portfolio: 2847593,
    benchmark: 2480000,
    drawdown: -0.8,
    volume: 2100000,
  },
];

// Asset allocation
const assetAllocation = [
  { name: "Bitcoin", value: 35, amount: 996658.21, color: "#f7931a" },
  { name: "Ethereum", value: 25, amount: 711898.36, color: "#627eea" },
  { name: "DeFi Tokens", value: 20, amount: 569518.69, color: "#ff6b6b" },
  { name: "Layer 1s", value: 12, amount: 341711.21, color: "#4ecdc4" },
  { name: "Stablecoins", value: 5, amount: 142379.67, color: "#45b7d1" },
  { name: "Others", value: 3, amount: 85427.31, color: "#96ceb4" },
];

// Risk metrics over time
const riskData = [
  { date: "2024-01", var: 2.1, cvar: 3.2, volatility: 15.4, beta: 0.95 },
  { date: "2024-02", var: 1.8, cvar: 2.9, volatility: 14.2, beta: 0.92 },
  { date: "2024-03", var: 2.3, cvar: 3.5, volatility: 16.1, beta: 0.88 },
  { date: "2024-04", var: 1.9, cvar: 3.1, volatility: 13.8, beta: 0.85 },
  { date: "2024-05", var: 1.6, cvar: 2.7, volatility: 12.9, beta: 0.89 },
  { date: "2024-06", var: 1.4, cvar: 2.4, volatility: 12.4, beta: 0.87 },
];

// Trading activity heatmap
const tradingHeatmap = [
  { hour: "00", mon: 12, tue: 15, wed: 8, thu: 22, fri: 18, sat: 5, sun: 3 },
  { hour: "04", mon: 8, tue: 12, wed: 6, thu: 18, fri: 14, sat: 3, sun: 2 },
  { hour: "08", mon: 45, tue: 52, wed: 38, thu: 48, fri: 42, sat: 15, sun: 8 },
  { hour: "12", mon: 38, tue: 42, wed: 35, thu: 45, fri: 40, sat: 25, sun: 18 },
  { hour: "16", mon: 52, tue: 58, wed: 48, thu: 55, fri: 50, sat: 35, sun: 22 },
  { hour: "20", mon: 35, tue: 38, wed: 32, thu: 42, fri: 38, sat: 28, sun: 15 },
];

// Strategy performance
const strategyPerformance = [
  {
    name: "AI Momentum",
    return: 48.5,
    sharpe: 2.9,
    maxDD: -5.2,
    trades: 245,
    winRate: 78.4,
    allocation: 25,
  },
  {
    name: "Arbitrage Scanner",
    return: 32.1,
    sharpe: 3.4,
    maxDD: -2.8,
    trades: 892,
    winRate: 85.2,
    allocation: 20,
  },
  {
    name: "DeFi Yield",
    return: 67.8,
    sharpe: 2.1,
    maxDD: -12.4,
    trades: 156,
    winRate: 71.8,
    allocation: 18,
  },
  {
    name: "Mean Reversion",
    return: 28.9,
    sharpe: 2.6,
    maxDD: -6.1,
    trades: 324,
    winRate: 68.5,
    allocation: 15,
  },
  {
    name: "Breakout Hunter",
    return: 41.2,
    sharpe: 2.3,
    maxDD: -8.7,
    trades: 198,
    winRate: 72.1,
    allocation: 12,
  },
  {
    name: "Grid Trading",
    return: 24.6,
    sharpe: 3.1,
    maxDD: -4.3,
    trades: 567,
    winRate: 82.3,
    allocation: 10,
  },
];

// Market correlation matrix
const correlationData = [
  {
    asset: "BTC",
    BTC: 1.0,
    ETH: 0.85,
    SOL: 0.72,
    ADA: 0.68,
    DOT: 0.71,
    LINK: 0.65,
  },
  {
    asset: "ETH",
    BTC: 0.85,
    ETH: 1.0,
    SOL: 0.78,
    ADA: 0.73,
    DOT: 0.76,
    LINK: 0.69,
  },
  {
    asset: "SOL",
    BTC: 0.72,
    ETH: 0.78,
    SOL: 1.0,
    ADA: 0.65,
    DOT: 0.68,
    LINK: 0.62,
  },
  {
    asset: "ADA",
    BTC: 0.68,
    ETH: 0.73,
    SOL: 0.65,
    ADA: 1.0,
    DOT: 0.71,
    LINK: 0.58,
  },
  {
    asset: "DOT",
    BTC: 0.71,
    ETH: 0.76,
    SOL: 0.68,
    ADA: 0.71,
    DOT: 1.0,
    LINK: 0.63,
  },
  {
    asset: "LINK",
    BTC: 0.65,
    ETH: 0.69,
    SOL: 0.62,
    ADA: 0.58,
    DOT: 0.63,
    LINK: 1.0,
  },
];

// Advanced metrics
const advancedMetrics = {
  valueAtRisk: {
    daily95: -42567.89,
    daily99: -68234.12,
    weekly95: -156789.45,
    weekly99: -234567.89,
  },
  expectedShortfall: {
    daily95: -58923.45,
    daily99: -89456.78,
    weekly95: -198765.43,
    weekly99: -298765.43,
  },
  stressTest: {
    march2020: -15.6,
    may2022: -12.3,
    ftxCollapse: -8.9,
    customScenario: -18.7,
  },
};

const AdvancedAnalytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [timeframe, setTimeframe] = useState<string>("6M");
  const [benchmark, setBenchmark] = useState<string>("BTC");
  const [showDrawdown, setShowDrawdown] = useState<boolean>(true);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    "return",
    "sharpe",
    "maxdd",
  ]);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Real-time data simulation
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      // Simulate real-time updates
    }, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getCorrelationColor = (value: number) => {
    if (value >= 0.8) return "bg-red-500";
    if (value >= 0.6) return "bg-orange-500";
    if (value >= 0.4) return "bg-yellow-500";
    if (value >= 0.2) return "bg-green-500";
    return "bg-blue-500";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Advanced Analytics
          </h1>
          <p className="text-gray-500 mt-1">
            Institutional-grade portfolio analytics and risk management
          </p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2">
            <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
            <span className="text-sm">Auto-refresh</span>
          </div>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="w-4 h-4 mr-2" />
            Configure
          </Button>
          <Button className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
            <Share2 className="w-4 h-4 mr-2" />
            Share Dashboard
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-indigo-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-indigo-400">
                  Total Portfolio Value
                </p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {formatCurrency(portfolioMetrics.totalValue)}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <ArrowUpRight className="w-4 h-4 text-green-400" />
                  <p className="text-sm font-medium text-green-400">
                    +{formatPercentage(portfolioMetrics.totalPnLPct)}
                  </p>
                </div>
              </div>
              <div className="p-3 bg-indigo-500/10 rounded-xl">
                <TrendingUp className="w-6 h-6 text-indigo-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-green-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-emerald-400">
                  Sharpe Ratio
                </p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {portfolioMetrics.sharpeRatio}
                </p>
                <p className="text-sm font-medium text-gray-400 mt-2">
                  Risk-adjusted return
                </p>
              </div>
              <div className="p-3 bg-emerald-500/10 rounded-xl">
                <Target className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-red-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-orange-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-red-400">Max Drawdown</p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {portfolioMetrics.maxDrawdown}%
                </p>
                <p className="text-sm font-medium text-gray-400 mt-2">
                  Peak to trough
                </p>
              </div>
              <div className="p-3 bg-red-500/10 rounded-xl">
                <TrendingDown className="w-6 h-6 text-red-400" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-cyan-500/10"></div>
          <div className="relative p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-blue-400">Win Rate</p>
                <p className="text-2xl font-bold mt-2 text-white">
                  {formatPercentage(portfolioMetrics.winRate)}
                </p>
                <p className="text-sm font-medium text-gray-400 mt-2">
                  Profitable trades
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Award className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Controls */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Timeframe:</span>
            <Select value={timeframe} onValueChange={setTimeframe}>
              <option value="1M">1 Month</option>
              <option value="3M">3 Months</option>
              <option value="6M">6 Months</option>
              <option value="1Y">1 Year</option>
              <option value="2Y">2 Years</option>
              <option value="ALL">All Time</option>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Benchmark:</span>
            <Select value={benchmark} onValueChange={setBenchmark}>
              <option value="BTC">Bitcoin</option>
              <option value="ETH">Ethereum</option>
              <option value="SPY">S&P 500</option>
              <option value="GOLD">Gold</option>
              <option value="CUSTOM">Custom Index</option>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={showDrawdown} onCheckedChange={setShowDrawdown} />
            <span className="text-sm">Show Drawdown</span>
          </div>
          <Button variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Data
          </Button>
        </div>
      </Card>

      {/* Main Analytics */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Portfolio Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance Analysis</TabsTrigger>
          <TabsTrigger value="risk">Risk Management</TabsTrigger>
          <TabsTrigger value="allocation">Asset Allocation</TabsTrigger>
          <TabsTrigger value="strategies">Strategy Analysis</TabsTrigger>
          <TabsTrigger value="correlation">Market Correlation</TabsTrigger>
          <TabsTrigger value="stress">Stress Testing</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Chart */}
            <Card className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                  Portfolio Performance vs Benchmark
                </h3>
                <div className="flex gap-2">
                  <Badge variant="default">Portfolio</Badge>
                  <Badge variant="secondary">{benchmark}</Badge>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="portfolio"
                    fill="#8b5cf6"
                    fillOpacity={0.3}
                    stroke="#8b5cf6"
                    strokeWidth={3}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="benchmark"
                    stroke="#64748b"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                  {showDrawdown && (
                    <Bar
                      yAxisId="right"
                      dataKey="drawdown"
                      fill="#ef4444"
                      fillOpacity={0.6}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </Card>

            {/* Key Metrics */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                Advanced Risk Metrics
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-emerald-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-green-400 font-medium">Alpha</p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.alpha}%
                    </p>
                  </div>
                </div>
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-indigo-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-blue-400 font-medium">Beta</p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.beta}
                    </p>
                  </div>
                </div>
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-purple-400 font-medium">
                      Sortino Ratio
                    </p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.sortinoRatio}
                    </p>
                  </div>
                </div>
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-amber-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-orange-400 font-medium">
                      Calmar Ratio
                    </p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.calmarRatio}
                    </p>
                  </div>
                </div>
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-teal-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-cyan-400 font-medium">
                      Information Ratio
                    </p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.informationRatio}
                    </p>
                  </div>
                </div>
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-3">
                  <div className="absolute inset-0 bg-gradient-to-br from-rose-500/10 to-red-500/10"></div>
                  <div className="relative">
                    <p className="text-xs text-rose-400 font-medium">
                      Profit Factor
                    </p>
                    <p className="text-lg font-semibold text-white mt-1">
                      {portfolioMetrics.profitFactor}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Volume Analysis */}
            <Card className="p-6 lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">
                Trading Volume & Performance
              </h3>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Bar
                    yAxisId="right"
                    dataKey="volume"
                    fill="#3b82f6"
                    fillOpacity={0.6}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="portfolio"
                    stroke="#8b5cf6"
                    strokeWidth={3}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </Card>

            {/* Performance Summary */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                Performance Summary
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Total Return</span>
                    <span className="font-medium text-green-600">
                      +{formatPercentage(portfolioMetrics.totalPnLPct)}
                    </span>
                  </div>
                  <Progress
                    value={portfolioMetrics.totalPnLPct}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Volatility</span>
                    <span className="font-medium">
                      {portfolioMetrics.volatility}%
                    </span>
                  </div>
                  <Progress
                    value={portfolioMetrics.volatility}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Win Rate</span>
                    <span className="font-medium text-green-600">
                      {formatPercentage(portfolioMetrics.winRate)}
                    </span>
                  </div>
                  <Progress value={portfolioMetrics.winRate} className="h-2" />
                </div>
                <div className="pt-4 border-t">
                  <p className="text-xs text-gray-500 mb-2">
                    Average Trade Size
                  </p>
                  <div className="flex justify-between">
                    <div>
                      <p className="text-sm text-green-600">
                        Win: {formatCurrency(portfolioMetrics.avgWinSize)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-red-600">
                        Loss: {formatCurrency(portfolioMetrics.avgLossSize)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="risk">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Risk Metrics Over Time */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Risk Metrics Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <RechartsLineChart data={riskData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="var"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="VaR (95%)"
                  />
                  <Line
                    type="monotone"
                    dataKey="cvar"
                    stroke="#f97316"
                    strokeWidth={2}
                    name="CVaR (95%)"
                  />
                  <Line
                    type="monotone"
                    dataKey="volatility"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    name="Volatility"
                  />
                </RechartsLineChart>
              </ResponsiveContainer>
            </Card>

            {/* Value at Risk */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                Value at Risk Analysis
              </h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-red-500/5 transition-all duration-300">
                    <div className="absolute inset-0 bg-gradient-to-br from-red-500/5 to-red-900/5"></div>
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                        <p className="text-xs font-medium text-gray-400">
                          Daily VaR (95%)
                        </p>
                      </div>
                      <p className="text-xl font-bold text-red-400">
                        {formatCurrency(advancedMetrics.valueAtRisk.daily95)}
                      </p>
                    </div>
                  </div>

                  <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-red-500/5 transition-all duration-300">
                    <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-red-900/10"></div>
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-red-600"></div>
                        <p className="text-xs font-medium text-gray-400">
                          Daily VaR (99%)
                        </p>
                      </div>
                      <p className="text-xl font-bold text-red-500">
                        {formatCurrency(advancedMetrics.valueAtRisk.daily99)}
                      </p>
                    </div>
                  </div>

                  <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-orange-500/5 transition-all duration-300">
                    <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 to-orange-900/5"></div>
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                        <p className="text-xs font-medium text-gray-400">
                          Weekly VaR (95%)
                        </p>
                      </div>
                      <p className="text-xl font-bold text-orange-400">
                        {formatCurrency(advancedMetrics.valueAtRisk.weekly95)}
                      </p>
                    </div>
                  </div>

                  <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-orange-500/5 transition-all duration-300">
                    <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-orange-900/10"></div>
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-orange-600"></div>
                        <p className="text-xs font-medium text-gray-400">
                          Weekly VaR (99%)
                        </p>
                      </div>
                      <p className="text-xl font-bold text-orange-500">
                        {formatCurrency(advancedMetrics.valueAtRisk.weekly99)}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <h4 className="font-medium mb-3">
                    Expected Shortfall (CVaR)
                  </h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Daily (95%):</span>
                      <span className="font-medium text-red-600">
                        {formatCurrency(
                          advancedMetrics.expectedShortfall.daily95
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Daily (99%):</span>
                      <span className="font-medium text-red-600">
                        {formatCurrency(
                          advancedMetrics.expectedShortfall.daily99
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Weekly (95%):</span>
                      <span className="font-medium text-red-600">
                        {formatCurrency(
                          advancedMetrics.expectedShortfall.weekly95
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="allocation">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Asset Allocation Pie Chart */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                Current Asset Allocation
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <RechartsPieChart>
                  <Pie
                    data={assetAllocation}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={120}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {assetAllocation.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {assetAllocation.map((item) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm">
                      {item.name}: {item.value}%
                    </span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Allocation Details */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Allocation Details</h3>
              <div className="space-y-3">
                {assetAllocation.map((asset) => (
                  <div
                    key={asset.name}
                    className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg transition-all duration-300"
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-gray-500/5 to-gray-900/5"></div>
                    <div className="relative flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: asset.color }}
                          />
                          <p className="text-sm font-medium text-gray-200">
                            {asset.name}
                          </p>
                        </div>
                        <div className="px-2 py-1 rounded-full bg-gray-800/50">
                          <p className="text-xs font-medium text-gray-400">
                            {asset.value}% allocation
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-white">
                          {formatCurrency(asset.amount)}
                        </p>
                        <p className="text-xs text-gray-500">Current value</p>
                      </div>
                    </div>
                    <div className="mt-2 w-full bg-gray-800/50 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full"
                        style={{
                          width: `${asset.value}%`,
                          backgroundColor: asset.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="strategies">
          <Card className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold">
                Strategy Performance Analysis
              </h3>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Filter className="w-4 h-4 mr-2" />
                  Filter Strategies
                </Button>
                <Button variant="outline" size="sm">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Compare
                </Button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Strategy</th>
                    <th className="text-left py-2">Return</th>
                    <th className="text-left py-2">Sharpe</th>
                    <th className="text-left py-2">Max DD</th>
                    <th className="text-left py-2">Trades</th>
                    <th className="text-left py-2">Win Rate</th>
                    <th className="text-left py-2">Allocation</th>
                    <th className="text-left py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {strategyPerformance.map((strategy) => (
                    <tr
                      key={strategy.name}
                      className="border-b hover:bg-gray-50"
                    >
                      <td className="py-3 font-medium">{strategy.name}</td>
                      <td className="py-3">
                        <span
                          className={`font-semibold ${
                            strategy.return >= 0
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {strategy.return >= 0 ? "+" : ""}
                          {formatPercentage(strategy.return)}
                        </span>
                      </td>
                      <td className="py-3">{strategy.sharpe}</td>
                      <td className="py-3 text-red-600">{strategy.maxDD}%</td>
                      <td className="py-3">{strategy.trades}</td>
                      <td className="py-3">
                        {formatPercentage(strategy.winRate)}
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${strategy.allocation * 4}%` }}
                            />
                          </div>
                          <span className="text-sm">
                            {strategy.allocation}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3">
                        <Badge variant="default">Active</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="correlation">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6">
              Asset Correlation Matrix
            </h3>
            <div className="overflow-x-auto">
              <div className="grid grid-cols-7 gap-1 min-w-[500px]">
                <div className="p-2 font-medium text-center"></div>
                {["BTC", "ETH", "SOL", "ADA", "DOT", "LINK"].map((asset) => (
                  <div
                    key={asset}
                    className="p-2 font-medium text-center text-sm"
                  >
                    {asset}
                  </div>
                ))}
                {correlationData.map((row) => (
                  <React.Fragment key={row.asset}>
                    <div className="p-2 font-medium text-center text-sm">
                      {row.asset}
                    </div>
                    {["BTC", "ETH", "SOL", "ADA", "DOT", "LINK"].map(
                      (asset) => (
                        <div
                          key={asset}
                          className={`p-2 text-center text-xs font-medium text-white rounded ${getCorrelationColor(
                            typeof row[asset as keyof typeof row] === 'number' ? row[asset as keyof typeof row] as number : 0
                          )}`}
                        >
                          {typeof row[asset as keyof typeof row] === 'number' 
                            ? (row[asset as keyof typeof row] as number).toFixed(2)
                            : '-'
                          }
                        </div>
                      )
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded" />
                <span>Low (0.0-0.2)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded" />
                <span>Moderate (0.2-0.4)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded" />
                <span>Medium (0.4-0.6)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-orange-500 rounded" />
                <span>High (0.6-0.8)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded" />
                <span>Very High (0.8+)</span>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="stress">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                Historical Stress Test Results
              </h3>
              <div className="space-y-4">
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-red-500/5 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-red-900/10"></div>
                  <div className="relative flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/10">
                        <AlertTriangle className="h-4 w-4 text-red-400" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-200">
                          COVID-19 market crash scenario
                        </p>
                        <p className="text-sm text-gray-500">
                          March 2020 Crash
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-3 py-1 rounded-full bg-red-500/10">
                        <p className="text-sm font-bold text-red-400">
                          {advancedMetrics.stressTest.march2020}%
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-orange-500/5 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-orange-900/10"></div>
                  <div className="relative flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500/10">
                        <AlertTriangle className="h-4 w-4 text-orange-400" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-200">
                          LUNA/UST collapse scenario
                        </p>
                        <p className="text-sm text-gray-500">
                          May 2022 Terra Luna
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-3 py-1 rounded-full bg-orange-500/10">
                        <p className="text-sm font-bold text-orange-400">
                          {advancedMetrics.stressTest.may2022}%
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-yellow-500/5 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/10 to-yellow-900/10"></div>
                  <div className="relative flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500/10">
                        <AlertTriangle className="h-4 w-4 text-yellow-400" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-200">
                          November 2022 FTX bankruptcy
                        </p>
                        <p className="text-sm text-gray-500">FTX Collapse</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-3 py-1 rounded-full bg-yellow-500/10">
                        <p className="text-sm font-bold text-yellow-400">
                          {advancedMetrics.stressTest.ftxCollapse}%
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-4 hover:shadow-lg hover:shadow-violet-500/5 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-violet-500/10 to-violet-900/10"></div>
                  <div className="relative flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-500/10">
                        <AlertTriangle className="h-4 w-4 text-violet-400" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-200">
                          50% market drop + liquidity crisis
                        </p>
                        <p className="text-sm text-gray-500">Custom Scenario</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-3 py-1 rounded-full bg-violet-500/10">
                        <p className="text-sm font-bold text-violet-400">
                          {advancedMetrics.stressTest.customScenario}%
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Scenario Analysis</h3>
              <div className="space-y-4">
                <div>
                  <p className="font-medium mb-2">Portfolio Resilience Score</p>
                  <div className="flex items-center gap-3">
                    <Progress value={75} className="flex-1 h-3" />
                    <span className="font-bold text-green-600">75/100</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Based on historical stress test performance
                  </p>
                </div>
                <div className="pt-4 border-t">
                  <p className="font-medium mb-3">Risk Factors</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Market Risk:</span>
                      <span className="font-medium text-orange-600">High</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Liquidity Risk:</span>
                      <span className="font-medium text-yellow-600">
                        Medium
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Concentration Risk:</span>
                      <span className="font-medium text-green-600">Low</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Counterparty Risk:</span>
                      <span className="font-medium text-yellow-600">
                        Medium
                      </span>
                    </div>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <Button className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
                    <Play className="w-4 h-4 mr-2" />
                    Run Custom Stress Test
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdvancedAnalytics;
