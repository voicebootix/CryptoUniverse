import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  DollarSign,
  Target,
  Zap,
  Crown,
  Gift,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Coins,
  Award,
  Gem,
  Sparkles,
  BarChart3,
  PieChart,
  Activity,
  Receipt,
  CheckCircle,
  Clock,
  RefreshCw,
  Calculator,
  CreditCard,
  Bitcoin,
  Banknote,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency, formatPercentage, formatNumber } from "@/lib/utils";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
} from "recharts";

interface ProfitSharingData {
  totalProfit: number;
  platformFee: number;
  userKeeps: number;
  creditsEarned: number;
  earningPotential: number;
}

interface StrategyBudget {
  availableCredits: number;
  activeStrategies: number;
  currentMonthlyCost: number;
  remainingBudget: number;
  recommendations: any[];
}

const ProfitSharingCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState("overview");
  const [profitData, setProfitData] = useState<ProfitSharingData>({
    totalProfit: 2847.5,
    platformFee: 711.88,
    userKeeps: 2135.62,
    creditsEarned: 712,
    earningPotential: 712,
  });

  const [strategyBudget, setStrategyBudget] = useState<StrategyBudget>({
    availableCredits: 712,
    activeStrategies: 3,
    currentMonthlyCost: 80,
    remainingBudget: 632,
    recommendations: [],
  });

  const [paymentMethod, setPaymentMethod] = useState("bitcoin");

  const profitHistory = [
    { month: "Jan", profit: 1250, fee: 312.5, credits: 312 },
    { month: "Feb", profit: 1890, fee: 472.5, credits: 472 },
    { month: "Mar", profit: 2340, fee: 585, credits: 585 },
    { month: "Apr", profit: 1670, fee: 417.5, credits: 417 },
    { month: "May", profit: 2847, fee: 711.88, credits: 712 },
  ];

  const strategyPortfolio = [
    {
      name: "AI Risk Manager",
      cost: 15,
      category: "Essential",
      performance: "+12%",
    },
    { name: "AI Momentum", cost: 25, category: "Spot", performance: "+28%" },
    {
      name: "AI Portfolio Optimizer",
      cost: 20,
      category: "Portfolio",
      performance: "+15%",
    },
    {
      name: "Available Budget",
      cost: 632,
      category: "Unused",
      performance: "N/A",
    },
  ];

  const availableStrategies = [
    {
      name: "AI Arbitrage",
      cost: 30,
      performance: "+35%",
      risk: "Low",
      tier: "Basic",
    },
    {
      name: "AI Scalping",
      cost: 45,
      performance: "+67%",
      risk: "High",
      tier: "Pro",
    },
    {
      name: "AI Futures",
      cost: 60,
      performance: "+82%",
      risk: "High",
      tier: "Pro",
    },
    {
      name: "AI Options",
      cost: 75,
      performance: "+124%",
      risk: "Very High",
      tier: "Enterprise",
    },
    {
      name: "CryptoWhale Strategy",
      cost: 55,
      performance: "+78%",
      risk: "Medium",
      tier: "Community",
    },
  ];

  const COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#64748b"];

  const processPayment = async () => {
    try {
      // Process profit sharing payment
      console.log(
        `Processing ${paymentMethod} payment of $${profitData.platformFee}`
      );
    } catch (error) {
      console.error("Payment failed:", error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Profit Sharing Center
          </h1>
          <p className="text-muted-foreground">
            Revolutionary profit-based revenue model - Pay 25% of profits, earn
            credits for more strategies
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="px-3 py-1 text-green-600">
            <Coins className="w-4 h-4 mr-2" />
            {formatNumber(strategyBudget.availableCredits)} Credits
          </Badge>
          <Badge variant="outline" className="px-3 py-1 text-blue-600">
            <Target className="w-4 h-4 mr-2" />$
            {formatNumber(strategyBudget.availableCredits)} Earning Potential
          </Badge>
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-6"
      >
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Profit Overview</TabsTrigger>
          <TabsTrigger value="payment">Payment Due</TabsTrigger>
          <TabsTrigger value="strategies">Strategy Budget</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* Profit Overview */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-green-500/10"></div>
              <div className="relative p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-emerald-400">
                      Total Profit
                    </p>
                    <p className="text-2xl font-bold mt-2 text-white">
                      {formatCurrency(profitData.totalProfit)}
                    </p>
                    <div className="flex items-center gap-1 mt-2">
                      <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                      <p className="text-sm font-medium text-emerald-400">
                        Generated this month
                      </p>
                    </div>
                  </div>
                  <div className="p-3 bg-emerald-500/10 rounded-xl">
                    <TrendingUp className="w-6 h-6 text-emerald-400" />
                  </div>
                </div>
              </div>
            </Card>

            <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-cyan-500/10"></div>
              <div className="relative p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-blue-400">
                      Platform Share
                    </p>
                    <p className="text-2xl font-bold mt-2 text-white">
                      {formatCurrency(profitData.platformFee)}
                    </p>
                    <div className="flex items-center gap-1 mt-2">
                      <p className="text-sm font-medium text-gray-400">
                        25% of total profit
                      </p>
                    </div>
                  </div>
                  <div className="p-3 bg-blue-500/10 rounded-xl">
                    <Calculator className="w-6 h-6 text-blue-400" />
                  </div>
                </div>
              </div>
            </Card>

            <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-violet-500/10"></div>
              <div className="relative p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-purple-400">
                      Your Profit
                    </p>
                    <p className="text-2xl font-bold mt-2 text-white">
                      {formatCurrency(profitData.userKeeps)}
                    </p>
                    <div className="flex items-center gap-1 mt-2">
                      <p className="text-sm font-medium text-gray-400">
                        75% of total profit
                      </p>
                    </div>
                  </div>
                  <div className="p-3 bg-purple-500/10 rounded-xl">
                    <Wallet className="w-6 h-6 text-purple-400" />
                  </div>
                </div>
              </div>
            </Card>

            <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] hover:shadow-lg hover:shadow-orange-500/10 transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-amber-500/10"></div>
              <div className="relative p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-orange-400">
                      Credits Earned
                    </p>
                    <p className="text-2xl font-bold mt-2 text-white">
                      {formatNumber(profitData.creditsEarned)}
                    </p>
                    <div className="flex items-center gap-1 mt-2">
                      <p className="text-sm font-medium text-gray-400">
                        ${formatNumber(profitData.earningPotential)} potential
                      </p>
                    </div>
                  </div>
                  <div className="p-3 bg-orange-500/10 rounded-xl">
                    <Coins className="w-6 h-6 text-orange-400" />
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Profit Sharing Explanation */}
          <Card className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35]">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-violet-500/5"></div>
            <CardHeader className="relative">
              <CardTitle className="flex items-center gap-2 text-white">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Sparkles className="w-5 h-5 text-blue-400" />
                </div>
                How Profit Sharing Works
              </CardTitle>
            </CardHeader>
            <CardContent className="relative space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-6 hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-green-500/10"></div>
                  <div className="relative text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500/10 mx-auto mb-4">
                      <TrendingUp className="h-7 w-7 text-emerald-400" />
                    </div>
                    <h4 className="text-lg font-semibold text-emerald-400 mb-2">
                      1. You Earn Profits
                    </h4>
                    <p className="text-sm text-gray-400">
                      AI strategies generate real profits from trading
                    </p>
                  </div>
                </div>

                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-6 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-cyan-500/10"></div>
                  <div className="relative text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-500/10 mx-auto mb-4">
                      <Calculator className="h-7 w-7 text-blue-400" />
                    </div>
                    <h4 className="text-lg font-semibold text-blue-400 mb-2">
                      2. Share 25% with Platform
                    </h4>
                    <p className="text-sm text-gray-400">
                      Pay only when you make money - no upfront fees
                    </p>
                  </div>
                </div>

                <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-6 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-violet-500/10"></div>
                  <div className="relative text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-purple-500/10 mx-auto mb-4">
                      <Coins className="h-7 w-7 text-purple-400" />
                    </div>
                    <h4 className="text-lg font-semibold text-purple-400 mb-2">
                      3. Get Credits to Earn More
                    </h4>
                    <p className="text-sm text-gray-400">
                      Use credits to buy better strategies and earn more
                    </p>
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden bg-[#1a1c23] border-[#2a2d35] rounded-lg p-6 hover:shadow-lg hover:shadow-amber-500/10 transition-all duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-yellow-500/5"></div>
                <div className="relative flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/10">
                    <Zap className="h-6 w-6 text-amber-400" />
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-amber-400 mb-2">
                      Revolutionary Model
                    </h4>
                    <p className="text-sm text-gray-400">
                      Unlike traditional subscriptions, you only pay when you
                      make money. The more you earn, the more credits you get to
                      unlock better strategies and earn even more!
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payment Due */}
        <TabsContent value="payment" className="space-y-6">
          <Card className="border border-[#2a2d35] bg-[#1a1c23] relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5"></div>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-blue-600" />
                Payment Due: {formatCurrency(profitData.platformFee)}
              </CardTitle>
              <CardDescription>
                Pay your profit share to unlock {profitData.creditsEarned}{" "}
                credits
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Payment Breakdown */}
              <div className="grid gap-4 md:grid-cols-3">
                <div className="p-4 bg-emerald-50/80 rounded-lg border border-emerald-200 hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                    <span className="font-medium text-emerald-900">
                      Your Profits
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-emerald-600">
                    {formatCurrency(profitData.totalProfit)}
                  </div>
                </div>

                <div className="p-4 bg-blue-50/80 rounded-lg border border-blue-200 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                  <div className="flex items-center gap-2 mb-2">
                    <Calculator className="w-4 h-4 text-blue-600" />
                    <span className="font-medium text-blue-900">
                      Platform Share (25%)
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-blue-600">
                    {formatCurrency(profitData.platformFee)}
                  </div>
                </div>

                <div className="p-4 bg-purple-50/80 rounded-lg border border-purple-200 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300">
                  <div className="flex items-center gap-2 mb-2">
                    <Coins className="w-4 h-4 text-purple-600" />
                    <span className="font-medium text-purple-900">
                      Credits Earned
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-purple-600">
                    {formatNumber(profitData.creditsEarned)}
                  </div>
                </div>
              </div>

              {/* Crypto Payment Options */}
              <div className="space-y-4">
                <h4 className="font-medium">Pay with Cryptocurrency</h4>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                  {[
                    {
                      id: "bitcoin",
                      name: "Bitcoin",
                      icon: Bitcoin,
                      color: "text-orange-500",
                    },
                    {
                      id: "ethereum",
                      name: "Ethereum",
                      icon: Gem,
                      color: "text-blue-500",
                    },
                    {
                      id: "usdc",
                      name: "USDC",
                      icon: DollarSign,
                      color: "text-green-500",
                    },
                    {
                      id: "usdt",
                      name: "USDT",
                      icon: Banknote,
                      color: "text-green-600",
                    },
                  ].map((crypto) => (
                    <motion.div
                      key={crypto.id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={`p-4 rounded-lg cursor-pointer transition-all ${
                        paymentMethod === crypto.id
                          ? "bg-[#1e2128] border-[1px] border-blue-500/50 shadow-lg shadow-blue-500/10"
                          : "bg-[#1a1c23] border-[1px] border-[#2a2d35] hover:bg-[#1e2128] hover:border-[#3a3d45]"
                      }`}
                      onClick={() => setPaymentMethod(crypto.id)}
                    >
                      <div className="flex items-center gap-3">
                        <crypto.icon className={`w-6 h-6 ${crypto.color}`} />
                        <div>
                          <div className="font-medium">{crypto.name}</div>
                          <div className="text-xs text-muted-foreground">
                            ≈{" "}
                            {crypto.id === "bitcoin"
                              ? "0.0025 BTC"
                              : crypto.id === "ethereum"
                              ? "0.21 ETH"
                              : "$711.88"}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              <Button
                onClick={processPayment}
                className="w-full bg-gradient-to-r from-emerald-600 via-blue-600 to-purple-600 text-white py-4 mt-2 rounded-lg font-medium hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
                size="lg"
              >
                <CreditCard className="w-4 h-4 mr-2" />
                Pay {formatCurrency(profitData.platformFee)} & Earn{" "}
                {profitData.creditsEarned} Credits
              </Button>

              <div className="p-4 bg-[#1e2128] border-[1px] border-[#2a2d35] rounded-lg mt-4 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      After Payment
                    </h4>
                    <p className="text-sm text-blue-700">
                      You'll have {profitData.creditsEarned} credits to purchase
                      additional strategies. Each credit represents $1 earning
                      potential, so you can earn up to $
                      {formatNumber(profitData.earningPotential)} more!
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Strategy Budget */}
        <TabsContent value="strategies" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Current Strategy Portfolio */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="w-5 h-5" />
                  Your Strategy Portfolio
                </CardTitle>
                <CardDescription>
                  {strategyBudget.activeStrategies} active strategies •{" "}
                  {strategyBudget.currentMonthlyCost} credits/month
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  {strategyPortfolio.map((strategy, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-3 h-3 rounded-full ${
                            index < 3 ? "bg-green-500" : "bg-gray-300"
                          }`}
                        />
                        <div>
                          <div className="font-medium">{strategy.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {strategy.category}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">
                          {strategy.cost} credits
                        </div>
                        <div
                          className={`text-sm ${
                            strategy.performance !== "N/A"
                              ? "text-green-600"
                              : "text-gray-500"
                          }`}
                        >
                          {strategy.performance}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Available Budget</span>
                    <span className="text-lg font-bold text-green-600">
                      {formatNumber(strategyBudget.remainingBudget)} credits
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    ${formatNumber(strategyBudget.remainingBudget)} earning
                    potential
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Available Strategies */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Available Strategies
                </CardTitle>
                <CardDescription>
                  Purchase additional strategies to increase earning potential
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {availableStrategies.map((strategy, index) => (
                  <div
                    key={index}
                    className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <div className="font-medium">{strategy.name}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {strategy.tier}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {strategy.risk} Risk
                          </Badge>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-green-600">
                          {strategy.performance}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {strategy.cost} credits
                        </div>
                      </div>
                    </div>

                    <Button
                      size="sm"
                      className="w-full"
                      disabled={strategy.cost > strategyBudget.remainingBudget}
                    >
                      {strategy.cost > strategyBudget.remainingBudget
                        ? "Insufficient Credits"
                        : `Purchase for ${strategy.cost} Credits`}
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Strategy Performance Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Strategy Portfolio Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPieChart>
                    <Pie
                      data={strategyPortfolio}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="cost"
                      nameKey="name"
                    >
                      {strategyPortfolio.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value, name) => [`${value} credits`, name]}
                    />
                  </RechartsPieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Profit History */}
        <TabsContent value="history" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Profit & Credit History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={profitHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="profit"
                      stroke="#10b981"
                      strokeWidth={3}
                      name="Profit ($)"
                    />
                    <Line
                      type="monotone"
                      dataKey="credits"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Credits Earned"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
};

export default ProfitSharingCenter;
