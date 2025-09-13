import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  DollarSign,
  Target,
  Zap,
  Wallet,
  ArrowUpRight,
  ArrowLeft,
  Coins,
  Activity,
  Receipt,
  CheckCircle,
  Clock,
  RefreshCw,
  Calculator,
  CreditCard,
  Bitcoin,
  Banknote,
  AlertTriangle,
  Copy,
  ExternalLink,
  Gem,
  Sparkles,
  BarChart3,
  Calendar,
  TrendingDown
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
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
  AreaChart,
  Area
} from 'recharts';

interface ProfitSharingData {
  // Current Period
  total_profit_earned: number;
  platform_fee_owed: number;
  user_profit_after_fee: number;
  credits_to_be_earned: number;
  platform_fee_percentage: number;
  
  // Historical Data
  total_profit_lifetime: number;
  total_fees_paid_lifetime: number;
  total_credits_earned_lifetime: number;
  
  // Status
  has_pending_payment: boolean;
  last_payment_date?: string;
  next_payment_due_date?: string;
  payment_frequency: 'monthly' | 'weekly' | 'realtime';
  
  // Breakdown by Strategy
  strategy_contributions: Array<{
    strategy_id: string;
    strategy_name: string;
    profit_contribution: number;
    percentage_of_total: number;
  }>;
  
  // Historical Chart Data
  profit_history: Array<{
    date: string;
    total_profit: number;
    platform_fee: number;
    user_profit: number;
    credits_earned: number;
  }>;
}

interface PaymentDetails {
  payment_id: string;
  amount_usd: number;
  currency: string;
  payment_address: string;
  payment_url?: string;
  qr_code_url?: string;
  expires_at: string;
  status: 'pending' | 'confirmed' | 'expired' | 'failed';
  transaction_hash?: string;
}

const ProfitSharingCenter: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('usdc');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState<PaymentDetails | null>(null);
  const [timeRemaining, setTimeRemaining] = useState(0);

  // Fetch profit sharing data
  const { data: profitData, isLoading: profitLoading, error: profitError } = useQuery({
    queryKey: ['profit-sharing-data'],
    queryFn: async () => {
      const response = await apiClient.get('/profit-sharing/user-summary');
      return response.data as ProfitSharingData;
    },
    refetchInterval: 30000,
    retry: 2,
    staleTime: 15000
  });

  // Fetch user credits for context
  const { data: userCredits } = useQuery({
    queryKey: ['user-credits'],
    queryFn: async () => {
      const response = await apiClient.get('/credits/balance');
      return response.data;
    },
    refetchInterval: 30000,
    retry: 2
  });

  // Process profit sharing payment
  const processPaymentMutation = useMutation({
    mutationFn: async (paymentMethod: string) => {
      const response = await apiClient.post('/profit-sharing/process-payment', {
        payment_method: paymentMethod,
        amount_usd: profitData?.platform_fee_owed || 0
      });
      return response.data as PaymentDetails;
    },
    onSuccess: (data) => {
      toast.success('Payment request created successfully');
      setPaymentDetails(data);
      setShowPaymentModal(true);
      
      // Calculate payment expiry countdown
      if (data.expires_at) {
        const expiryTime = new Date(data.expires_at).getTime();
        const now = Date.now();
        setTimeRemaining(Math.max(0, Math.floor((expiryTime - now) / 1000)));
      }
      
      // Open payment URL if available
      if (data.qr_code_url) {
        window.open(data.qr_code_url, '_blank');
      }
    },
    onError: (error: any) => {
      toast.error(`Payment failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Check payment status
  const checkPaymentStatus = async (paymentId: string) => {
    try {
      const response = await apiClient.get(`/profit-sharing/payment-status/${paymentId}`);
      const status = response.data.status;
      
      if (status === 'confirmed') {
        toast.success('Payment confirmed! Credits have been added to your account.');
        queryClient.invalidateQueries({ queryKey: ['profit-sharing-data'] });
        queryClient.invalidateQueries({ queryKey: ['user-credits'] });
        setShowPaymentModal(false);
      } else if (status === 'failed') {
        toast.error('Payment failed. Please try again.');
        setPaymentDetails(prev => prev ? { ...prev, status: 'failed' } : null);
      }
    } catch (error) {
      console.error('Failed to check payment status:', error);
    }
  };

  // Countdown timer for payment expiry
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (timeRemaining > 0) {
      timer = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [timeRemaining]);

  const paymentMethods = [
    {
      id: 'bitcoin',
      name: 'Bitcoin',
      icon: Bitcoin,
      description: 'BTC payments'
    },
    {
      id: 'ethereum',
      name: 'Ethereum',
      icon: Gem,
      description: 'ETH payments'
    },
    {
      id: 'usdc',
      name: 'USDC',
      icon: DollarSign,
      description: 'USD Coin'
    },
    {
      id: 'usdt',
      name: 'USDT',
      icon: Banknote,
      description: 'Tether'
    }
  ];

  const formatTimeRemaining = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (profitError) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to Load Profit Data</h3>
          <p className="text-muted-foreground mb-4">
            {profitError instanceof Error ? profitError.message : 'Unable to fetch profit sharing data'}
          </p>
          <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['profit-sharing-data'] })}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Profit Sharing Center
            </h1>
            <p className="text-muted-foreground">
              Revolutionary profit-based revenue model - Pay {profitData?.platform_fee_percentage || 25}% of profits, earn credits for more strategies
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {userCredits && (
            <Badge variant="outline" className="px-3 py-1 text-green-600">
              <Coins className="w-4 h-4 mr-2" />
              {formatNumber(userCredits.available_credits)} Credits
            </Badge>
          )}
          {profitData && (
            <Badge variant="outline" className="px-3 py-1 text-blue-600">
              <Target className="w-4 h-4 mr-2" />
              ${formatNumber(userCredits?.profit_potential || 0)} Earning Potential
            </Badge>
          )}
        </div>
      </div>

      {profitLoading ? (
        <div className="space-y-6">
          {/* Loading skeleton */}
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map(i => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded animate-pulse" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : profitData ? (
        <>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Profit Overview</TabsTrigger>
              <TabsTrigger value="payment">Payment Due</TabsTrigger>
              <TabsTrigger value="strategies">Strategy Breakdown</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            {/* Profit Overview */}
            <TabsContent value="overview" className="space-y-6">
              {/* Key Metrics */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card className="relative overflow-hidden bg-gradient-to-br from-emerald-50 to-green-50 border-emerald-200">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium text-emerald-600">Total Profit Earned</p>
                        <p className="text-2xl font-bold mt-2 text-emerald-700">
                          {formatCurrency(profitData.total_profit_earned)}
                        </p>
                        <div className="flex items-center gap-1 mt-2">
                          <ArrowUpRight className="w-4 h-4 text-emerald-500" />
                          <p className="text-sm font-medium text-emerald-600">Current Period</p>
                        </div>
                      </div>
                      <div className="p-3 bg-emerald-100 rounded-xl">
                        <TrendingUp className="w-6 h-6 text-emerald-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="relative overflow-hidden bg-gradient-to-br from-blue-50 to-cyan-50 border-blue-200">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium text-blue-600">Platform Fee Owed</p>
                        <p className="text-2xl font-bold mt-2 text-blue-700">
                          {formatCurrency(profitData.platform_fee_owed)}
                        </p>
                        <div className="flex items-center gap-1 mt-2">
                          <p className="text-sm font-medium text-blue-500">
                            {profitData.platform_fee_percentage}% of profit
                          </p>
                        </div>
                      </div>
                      <div className="p-3 bg-blue-100 rounded-xl">
                        <Calculator className="w-6 h-6 text-blue-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="relative overflow-hidden bg-gradient-to-br from-purple-50 to-violet-50 border-purple-200">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium text-purple-600">Your Profit (After Fee)</p>
                        <p className="text-2xl font-bold mt-2 text-purple-700">
                          {formatCurrency(profitData.user_profit_after_fee)}
                        </p>
                        <div className="flex items-center gap-1 mt-2">
                          <p className="text-sm font-medium text-purple-500">
                            {100 - profitData.platform_fee_percentage}% kept
                          </p>
                        </div>
                      </div>
                      <div className="p-3 bg-purple-100 rounded-xl">
                        <Wallet className="w-6 h-6 text-purple-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="relative overflow-hidden bg-gradient-to-br from-orange-50 to-amber-50 border-orange-200">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium text-orange-600">Credits to Earn</p>
                        <p className="text-2xl font-bold mt-2 text-orange-700">
                          {formatNumber(profitData.credits_to_be_earned)}
                        </p>
                        <div className="flex items-center gap-1 mt-2">
                          <p className="text-sm font-medium text-orange-500">
                            From fee payment
                          </p>
                        </div>
                      </div>
                      <div className="p-3 bg-orange-100 rounded-xl">
                        <Coins className="w-6 h-6 text-orange-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Profit Sharing Explanation */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-blue-500" />
                    How Profit Sharing Works
                  </CardTitle>
                  <CardDescription>
                    Our revolutionary model aligns platform success with your profitability
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-6 md:grid-cols-3">
                    <div className="text-center p-6 bg-emerald-50 rounded-lg border border-emerald-200">
                      <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <TrendingUp className="w-6 h-6 text-emerald-600" />
                      </div>
                      <h4 className="font-semibold text-emerald-700 mb-2">1. You Earn Profits</h4>
                      <p className="text-sm text-emerald-600">
                        AI strategies generate real profits from your trading activities
                      </p>
                    </div>

                    <div className="text-center p-6 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Calculator className="w-6 h-6 text-blue-600" />
                      </div>
                      <h4 className="font-semibold text-blue-700 mb-2">2. Share {profitData.platform_fee_percentage}% with Platform</h4>
                      <p className="text-sm text-blue-600">
                        Pay only when you make money - no upfront fees ever
                      </p>
                    </div>

                    <div className="text-center p-6 bg-purple-50 rounded-lg border border-purple-200">
                      <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Coins className="w-6 h-6 text-purple-600" />
                      </div>
                      <h4 className="font-semibold text-purple-700 mb-2">3. Get Credits to Earn More</h4>
                      <p className="text-sm text-purple-600">
                        Fee payments become credits to buy better strategies
                      </p>
                    </div>
                  </div>

                  {profitData.has_pending_payment && (
                    <div className="mt-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <Clock className="w-5 h-5 text-orange-600 mt-0.5" />
                        <div>
                          <h4 className="font-medium text-orange-700">Payment Due</h4>
                          <p className="text-sm text-orange-600 mt-1">
                            You have ${formatCurrency(profitData.platform_fee_owed)} in profit sharing fees due.
                            Pay now to earn {profitData.credits_to_be_earned} credits and continue using premium strategies.
                          </p>
                          <Button 
                            className="mt-3" 
                            size="sm"
                            onClick={() => setActiveTab('payment')}
                          >
                            Pay Now
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Lifetime Statistics */}
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {formatCurrency(profitData.total_profit_lifetime)}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Total Lifetime Profits</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {formatCurrency(profitData.total_fees_paid_lifetime)}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Total Fees Paid</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {formatNumber(profitData.total_credits_earned_lifetime)}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Total Credits Earned</div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Payment Due Tab */}
            <TabsContent value="payment" className="space-y-6">
              {profitData.has_pending_payment ? (
                <Card className="border-2 border-orange-200 bg-orange-50">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-orange-700">
                      <Receipt className="w-5 h-5" />
                      Payment Due: {formatCurrency(profitData.platform_fee_owed)}
                    </CardTitle>
                    <CardDescription className="text-orange-600">
                      Pay your profit share to unlock {profitData.credits_to_be_earned} credits
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Payment Breakdown */}
                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2 mb-2">
                          <TrendingUp className="w-4 h-4 text-green-600" />
                          <span className="font-medium text-green-700">Your Profits</span>
                        </div>
                        <div className="text-2xl font-bold text-green-600">
                          {formatCurrency(profitData.total_profit_earned)}
                        </div>
                      </div>

                      <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-center gap-2 mb-2">
                          <Calculator className="w-4 h-4 text-blue-600" />
                          <span className="font-medium text-blue-700">Platform Share ({profitData.platform_fee_percentage}%)</span>
                        </div>
                        <div className="text-2xl font-bold text-blue-600">
                          {formatCurrency(profitData.platform_fee_owed)}
                        </div>
                      </div>

                      <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                        <div className="flex items-center gap-2 mb-2">
                          <Coins className="w-4 h-4 text-purple-600" />
                          <span className="font-medium text-purple-700">Credits Earned</span>
                        </div>
                        <div className="text-2xl font-bold text-purple-600">
                          {formatNumber(profitData.credits_to_be_earned)}
                        </div>
                      </div>
                    </div>

                    {/* Payment Method Selection */}
                    <div className="space-y-4">
                      <h4 className="font-medium">Choose Payment Method</h4>
                      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                        {paymentMethods.map((method) => (
                          <motion.div
                            key={method.id}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                              selectedPaymentMethod === method.id
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => setSelectedPaymentMethod(method.id)}
                          >
                            <div className="flex items-center gap-3">
                              <method.icon className="w-6 h-6 text-blue-500" />
                              <div>
                                <div className="font-medium">{method.name}</div>
                                <div className="text-xs text-muted-foreground">{method.description}</div>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>

                    <Button
                      onClick={() => processPaymentMutation.mutate(selectedPaymentMethod)}
                      disabled={processPaymentMutation.isPending}
                      className="w-full bg-gradient-to-r from-green-600 to-blue-600 text-white py-3"
                      size="lg"
                    >
                      <CreditCard className="w-4 h-4 mr-2" />
                      {processPaymentMutation.isPending 
                        ? 'Generating Payment...' 
                        : `Pay ${formatCurrency(profitData.platform_fee_owed)} & Earn ${profitData.credits_to_be_earned} Credits`
                      }
                    </Button>

                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                        <div>
                          <h4 className="font-medium text-blue-900">After Payment</h4>
                          <p className="text-sm text-blue-700 mt-1">
                            You'll receive {profitData.credits_to_be_earned} credits instantly after payment confirmation.
                            Each credit represents $4 earning potential, giving you ${formatNumber(profitData.credits_to_be_earned * 4)} in new profit capacity!
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-12 text-center">
                    <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold mb-2">No Payment Due</h3>
                    <p className="text-muted-foreground">
                      You're all caught up! Continue trading to generate more profits.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Strategy Breakdown */}
            <TabsContent value="strategies" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Strategy Profit Contributions</CardTitle>
                  <CardDescription>How each strategy contributed to your total profits</CardDescription>
                </CardHeader>
                <CardContent>
                  {profitData.strategy_contributions && profitData.strategy_contributions.length > 0 ? (
                    <div className="space-y-4">
                      {profitData.strategy_contributions.map((strategy, index) => (
                        <div key={strategy.strategy_id} className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                              {index + 1}
                            </div>
                            <div>
                              <div className="font-medium">{strategy.strategy_name}</div>
                              <div className="text-sm text-muted-foreground">
                                {formatPercentage(strategy.percentage_of_total)} of total profit
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold text-green-500">
                              {formatCurrency(strategy.profit_contribution)}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Fee: {formatCurrency(strategy.profit_contribution * profitData.platform_fee_percentage / 100)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                      <p>No strategy breakdown available yet</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* History */}
            <TabsContent value="history" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Profit & Payment History</CardTitle>
                  <CardDescription>Track your earnings and fee payments over time</CardDescription>
                </CardHeader>
                <CardContent>
                  {profitData.profit_history && profitData.profit_history.length > 0 ? (
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={profitData.profit_history}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip />
                          <Area 
                            type="monotone" 
                            dataKey="user_profit" 
                            stackId="1" 
                            stroke="#22c55e" 
                            fill="#22c55e" 
                            fillOpacity={0.6}
                            name="Your Profit"
                          />
                          <Area 
                            type="monotone" 
                            dataKey="platform_fee" 
                            stackId="1" 
                            stroke="#3b82f6" 
                            fill="#3b82f6" 
                            fillOpacity={0.6}
                            name="Platform Fee"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-muted-foreground">
                      <div className="text-center">
                        <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                        <p>Start trading to see your profit history</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Payment Modal */}
          <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Complete Payment</DialogTitle>
                <DialogDescription>
                  Send the exact amount to the address below
                </DialogDescription>
              </DialogHeader>
              
              {paymentDetails && (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-muted">
                    <div className="flex items-center gap-2">
                      {paymentDetails.status === 'pending' && <Clock className="h-4 w-4 text-orange-500" />}
                      {paymentDetails.status === 'confirmed' && <CheckCircle className="h-4 w-4 text-green-500" />}
                      <span className="text-sm font-medium">
                        {paymentDetails.status === 'pending' && 'Awaiting Payment'}
                        {paymentDetails.status === 'confirmed' && 'Payment Confirmed'}
                        {paymentDetails.status === 'failed' && 'Payment Failed'}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-muted-foreground">Payment Address</label>
                      <div className="flex items-center gap-2 p-2 bg-muted rounded font-mono text-sm">
                        <span className="flex-1 truncate">{paymentDetails.payment_address}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(paymentDetails.payment_address)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-muted-foreground">Amount</label>
                      <div className="p-2 bg-muted rounded text-sm font-semibold">
                        {formatCurrency(paymentDetails.amount_usd)} ({paymentDetails.currency})
                      </div>
                    </div>

                    {timeRemaining > 0 && (
                      <div>
                        <label className="text-xs text-muted-foreground">Time Remaining</label>
                        <div className="p-2 bg-orange-50 border border-orange-200 rounded text-sm font-semibold text-orange-600">
                          {formatTimeRemaining(timeRemaining)}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    {paymentDetails.qr_code_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(paymentDetails.qr_code_url, '_blank')}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        QR Code
                      </Button>
                    )}
                    <Button
                      size="sm"
                      onClick={() => checkPaymentStatus(paymentDetails.payment_id)}
                      disabled={paymentDetails.status === 'confirmed'}
                    >
                      {paymentDetails.status === 'confirmed' ? 'Confirmed' : 'Check Status'}
                    </Button>
                  </div>
                </div>
              )}
            </DialogContent>
          </Dialog>
        </>
      ) : null}
    </div>
  );
};

export default ProfitSharingCenter;