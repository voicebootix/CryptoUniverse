import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CreditCard,
  DollarSign,
  TrendingUp,
  Package,
  Gift,
  Zap,
  Crown,
  Shield,
  Star,
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Download,
  Upload,
  RefreshCw,
  Settings,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Minus,
  ChevronRight,
  ChevronDown,
  Filter,
  Search,
  BarChart3,
  PieChart,
  Activity,
  Award,
  Target,
  Gem,
  Sparkles,
  Coins,
  Receipt,
  FileText,
  Mail,
  Bell,
  User,
  Users,
  Lock,
  Unlock,
  Key
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Tabs } from '@/components/ui/tabs';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell } from 'recharts';

// Subscription Plans
const subscriptionPlans = [
  {
    id: 'starter',
    name: 'Starter',
    price: 0,
    credits: 100,
    features: [
      '100 Monthly Credits',
      'Basic Trading Strategies',
      '1 Exchange Connection',
      'Community Support',
      'Basic Analytics'
    ],
    icon: <Zap className="w-6 h-6" />,
    color: 'from-gray-400 to-gray-600',
    popular: false
  },
  {
    id: 'pro',
    name: 'Professional',
    price: 49,
    credits: 1000,
    features: [
      '1,000 Monthly Credits',
      'Advanced Trading Strategies',
      '5 Exchange Connections',
      'Priority Support',
      'Advanced Analytics',
      'AI Trading Assistant',
      'Custom Alerts'
    ],
    icon: <Star className="w-6 h-6" />,
    color: 'from-blue-500 to-purple-600',
    popular: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 199,
    credits: 5000,
    features: [
      '5,000 Monthly Credits',
      'All Trading Strategies',
      'Unlimited Exchanges',
      'Dedicated Support',
      'Custom Analytics',
      'AI Consensus System',
      'API Access',
      'White Label Options',
      'Custom Strategies'
    ],
    icon: <Crown className="w-6 h-6" />,
    color: 'from-purple-500 to-pink-600',
    popular: false
  },
  {
    id: 'ultimate',
    name: 'Ultimate',
    price: 499,
    credits: 'Unlimited',
    features: [
      'Unlimited Credits',
      'Everything in Enterprise',
      'Dedicated Account Manager',
      'Custom Development',
      'SLA Guarantee',
      'Advanced AI Models',
      'Institutional Features',
      'Direct Market Access'
    ],
    icon: <Gem className="w-6 h-6" />,
    color: 'from-yellow-500 to-orange-600',
    popular: false
  }
];

// Credit Packs
const creditPacks = [
  { id: 1, credits: 100, price: 9.99, savings: 0, bonus: 0 },
  { id: 2, credits: 500, price: 44.99, savings: 10, bonus: 50 },
  { id: 3, credits: 1000, price: 79.99, savings: 20, bonus: 150 },
  { id: 4, credits: 2500, price: 174.99, savings: 30, bonus: 500 },
  { id: 5, credits: 5000, price: 299.99, savings: 40, bonus: 1500 },
  { id: 6, credits: 10000, price: 499.99, savings: 50, bonus: 5000 }
];

// Current subscription data
const currentSubscription = {
  plan: 'Professional',
  status: 'active',
  creditsRemaining: 687,
  creditsTotal: 1000,
  renewalDate: '2024-02-15',
  price: 49,
  autoRenew: true
};

// Billing history
const billingHistory = [
  { id: 1, date: '2024-01-15', description: 'Monthly Subscription - Professional', amount: 49.00, status: 'paid', invoice: 'INV-2024-001' },
  { id: 2, date: '2024-01-10', description: 'Credit Pack - 500 Credits', amount: 44.99, status: 'paid', invoice: 'INV-2024-002' },
  { id: 3, date: '2023-12-15', description: 'Monthly Subscription - Professional', amount: 49.00, status: 'paid', invoice: 'INV-2023-012' },
  { id: 4, date: '2023-12-01', description: 'Credit Pack - 1000 Credits', amount: 79.99, status: 'paid', invoice: 'INV-2023-011' },
  { id: 5, date: '2023-11-15', description: 'Monthly Subscription - Professional', amount: 49.00, status: 'paid', invoice: 'INV-2023-010' }
];

// Credit usage data
const creditUsageData = [
  { date: 'Jan 1', used: 23, remaining: 977 },
  { date: 'Jan 5', used: 87, remaining: 890 },
  { date: 'Jan 10', used: 145, remaining: 745 },
  { date: 'Jan 15', used: 234, remaining: 766 },
  { date: 'Jan 20', used: 189, remaining: 577 },
  { date: 'Jan 25', used: 90, remaining: 487 },
  { date: 'Today', used: 313, remaining: 687 }
];

// Credit usage breakdown
const creditBreakdown = [
  { name: 'Trading Execution', value: 45, color: '#3b82f6' },
  { name: 'AI Analysis', value: 30, color: '#8b5cf6' },
  { name: 'Strategy Backtesting', value: 15, color: '#ec4899' },
  { name: 'Market Data', value: 10, color: '#f59e0b' }
];

// Rewards and achievements
const rewards = [
  { id: 1, name: 'Early Adopter', description: 'Joined in the first month', credits: 100, claimed: true, icon: <Award className="w-6 h-6" /> },
  { id: 2, name: 'Trading Master', description: 'Complete 1000 trades', credits: 500, claimed: false, progress: 78, icon: <Target className="w-6 h-6" /> },
  { id: 3, name: 'Profit King', description: 'Achieve $10,000 in profits', credits: 1000, claimed: false, progress: 62, icon: <TrendingUp className="w-6 h-6" /> },
  { id: 4, name: 'Referral Champion', description: 'Refer 5 friends', credits: 250, claimed: false, progress: 40, icon: <Users className="w-6 h-6" /> }
];

const CreditBillingCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [selectedPlan, setSelectedPlan] = useState<string>(currentSubscription.plan.toLowerCase());
  const [showUpgradeModal, setShowUpgradeModal] = useState<boolean>(false);

  const creditUsagePercentage = ((currentSubscription.creditsTotal - currentSubscription.creditsRemaining) / currentSubscription.creditsTotal) * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Credit & Billing Center
          </h1>
          <p className="text-gray-500 mt-1">Manage your subscription, credits, and billing</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Download Invoices
          </Button>
          <Button className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
            <CreditCard className="w-4 h-4 mr-2" />
            Buy Credits
          </Button>
        </div>
      </div>

      {/* Current Plan Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 md:col-span-2 bg-gradient-to-br from-purple-50 to-pink-50 border-purple-200">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-semibold flex items-center gap-2">
                {currentSubscription.plan} Plan
                <Badge variant="success">Active</Badge>
              </h2>
              <p className="text-gray-600 mt-1">Renews on {currentSubscription.renewalDate}</p>
            </div>
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Manage
            </Button>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Credits Used</span>
                <span className="font-medium">
                  {currentSubscription.creditsTotal - currentSubscription.creditsRemaining} / {currentSubscription.creditsTotal}
                </span>
              </div>
              <Progress value={creditUsagePercentage} className="h-3" />
              <p className="text-xs text-gray-500 mt-1">
                {currentSubscription.creditsRemaining} credits remaining
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm text-gray-600">Monthly Cost</p>
                <p className="text-2xl font-bold">{formatCurrency(currentSubscription.price)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Auto-Renewal</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={currentSubscription.autoRenew ? 'success' : 'secondary'}>
                    {currentSubscription.autoRenew ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
          <h3 className="font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Button className="w-full justify-start" variant="outline">
              <Plus className="w-4 h-4 mr-2" />
              Buy Credit Pack
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <ArrowUpRight className="w-4 h-4 mr-2" />
              Upgrade Plan
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <Gift className="w-4 h-4 mr-2" />
              Refer & Earn
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <Receipt className="w-4 h-4 mr-2" />
              View Invoices
            </Button>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="overview">Overview</Tabs.Tab>
          <Tabs.Tab value="plans">Subscription Plans</Tabs.Tab>
          <Tabs.Tab value="credits">Credit Packs</Tabs.Tab>
          <Tabs.Tab value="usage">Usage Analytics</Tabs.Tab>
          <Tabs.Tab value="billing">Billing History</Tabs.Tab>
          <Tabs.Tab value="rewards">Rewards</Tabs.Tab>
        </Tabs.List>

        <Tabs.Content value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Credit Usage Chart */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Credit Usage Trend</h3>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={creditUsageData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="used" stackId="1" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
                  <Area type="monotone" dataKey="remaining" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            {/* Credit Breakdown */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Credit Usage Breakdown</h3>
              <ResponsiveContainer width="100%" height={250}>
                <RechartsPieChart>
                  <Pie
                    data={creditBreakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {creditBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {creditBreakdown.map((item) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded" style={{ backgroundColor: item.color }} />
                    <span className="text-sm">{item.name}: {item.value}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </Tabs.Content>

        <Tabs.Content value="plans">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {subscriptionPlans.map((plan) => (
              <motion.div
                key={plan.id}
                whileHover={{ scale: 1.02 }}
                className={`relative ${plan.popular ? 'scale-105' : ''}`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10">
                    <Badge className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
                      Most Popular
                    </Badge>
                  </div>
                )}
                <Card className={`p-6 h-full ${plan.popular ? 'border-purple-500 border-2' : ''}`}>
                  <div className={`inline-flex p-3 rounded-lg bg-gradient-to-r ${plan.color} text-white mb-4`}>
                    {plan.icon}
                  </div>
                  <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                  <div className="mb-4">
                    <span className="text-3xl font-bold">${plan.price}</span>
                    <span className="text-gray-500">/month</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">
                    {typeof plan.credits === 'number' ? formatNumber(plan.credits) : plan.credits} Credits
                  </p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={`w-full ${
                      plan.id === selectedPlan
                        ? 'bg-gray-200 text-gray-500'
                        : `bg-gradient-to-r ${plan.color} text-white`
                    }`}
                    disabled={plan.id === selectedPlan}
                  >
                    {plan.id === selectedPlan ? 'Current Plan' : 'Select Plan'}
                  </Button>
                </Card>
              </motion.div>
            ))}
          </div>
        </Tabs.Content>

        <Tabs.Content value="credits">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {creditPacks.map((pack) => (
              <Card key={pack.id} className="p-6 hover:shadow-lg transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-2xl font-bold">{formatNumber(pack.credits)}</h3>
                    <p className="text-gray-500">Credits</p>
                  </div>
                  {pack.bonus > 0 && (
                    <Badge variant="success">
                      +{formatNumber(pack.bonus)} Bonus
                    </Badge>
                  )}
                </div>
                <div className="mb-4">
                  <p className="text-3xl font-bold">${pack.price}</p>
                  {pack.savings > 0 && (
                    <p className="text-sm text-green-600">Save {pack.savings}%</p>
                  )}
                </div>
                <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                  <Coins className="w-4 h-4 mr-2" />
                  Purchase
                </Button>
              </Card>
            ))}
          </div>
        </Tabs.Content>

        <Tabs.Content value="usage">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Detailed Usage Analytics</h3>
            <p className="text-gray-500">Advanced usage analytics coming soon...</p>
          </Card>
        </Tabs.Content>

        <Tabs.Content value="billing">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Billing History</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Date</th>
                    <th className="text-left py-2">Description</th>
                    <th className="text-left py-2">Amount</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-left py-2">Invoice</th>
                  </tr>
                </thead>
                <tbody>
                  {billingHistory.map((item) => (
                    <tr key={item.id} className="border-b hover:bg-gray-50">
                      <td className="py-3">{item.date}</td>
                      <td className="py-3">{item.description}</td>
                      <td className="py-3">{formatCurrency(item.amount)}</td>
                      <td className="py-3">
                        <Badge variant="success">{item.status}</Badge>
                      </td>
                      <td className="py-3">
                        <Button variant="outline" size="sm">
                          <Download className="w-4 h-4 mr-2" />
                          {item.invoice}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </Tabs.Content>

        <Tabs.Content value="rewards">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {rewards.map((reward) => (
              <Card key={reward.id} className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-3 rounded-lg bg-gradient-to-r from-purple-100 to-pink-100">
                      {reward.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold">{reward.name}</h3>
                      <p className="text-sm text-gray-500">{reward.description}</p>
                    </div>
                  </div>
                  <Badge variant={reward.claimed ? 'success' : 'secondary'}>
                    {reward.claimed ? 'Claimed' : `${reward.progress}%`}
                  </Badge>
                </div>
                {!reward.claimed && (
                  <div className="space-y-2">
                    <Progress value={reward.progress} className="h-2" />
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">Progress</span>
                      <span className="text-sm font-medium">+{formatNumber(reward.credits)} credits</span>
                    </div>
                  </div>
                )}
                {reward.claimed && (
                  <div className="bg-green-50 rounded-lg p-3">
                    <p className="text-sm text-green-600 font-medium">
                      ✓ {formatNumber(reward.credits)} credits earned
                    </p>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </Tabs.Content>
      </Tabs>
    </div>
  );
};

export default CreditBillingCenter;
