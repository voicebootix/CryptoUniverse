import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  MessageSquare,
  Zap,
  TrendingUp,
  Shield,
  Target,
  BarChart3,
  DollarSign,
  RefreshCw,
  Maximize2,
  Minimize2,
  Activity,
  Users,
  Clock
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ChatInterface from '@/components/chat/ChatInterface';
import ConversationalTradingInterface from '@/components/chat/ConversationalTradingInterface';
import PhaseProgressVisualizer, { ExecutionPhase } from '@/components/trading/PhaseProgressVisualizer';
import PaperTradingToggle from '@/components/trading/PaperTradingToggle';
import { formatCurrency, formatPercentage } from '@/lib/utils';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

const AIChatPage: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedTab, setSelectedTab] = useState('conversational');
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  
  // Fetch real chat statistics
  const { data: chatStats, isLoading: statsLoading } = useQuery({
    queryKey: ['chat-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/chat/stats');
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
  
  // Fetch recent AI actions
  const { data: recentActions, isLoading: actionsLoading } = useQuery({
    queryKey: ['recent-actions'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/chat/recent-actions');
      return response.data.actions || [];
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'trade_execution':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'portfolio_rebalance':
        return <BarChart3 className="h-4 w-4 text-blue-500" />;
      case 'risk_assessment':
        return <Shield className="h-4 w-4 text-yellow-500" />;
      case 'opportunity_discovery':
        return <Target className="h-4 w-4 text-purple-500" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'pending':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'failed':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            AI Money Manager Chat
          </h1>
          <p className="text-muted-foreground">
            Comprehensive cryptocurrency portfolio management through natural language conversation
          </p>
        </div>

        <div className="flex items-center gap-3">
          <PaperTradingToggle 
            isCompact 
            onModeChange={setIsPaperTrading}
          />
          {chatStats && (
            <>
              <Badge variant="secondary" className="gap-1">
                <Activity className="h-3 w-3" />
                {chatStats.todayConversations || 0} conversations today
              </Badge>
              <Badge variant="secondary" className="gap-1">
                <Zap className="h-3 w-3" />
                {chatStats.avgResponseTime || 0}s avg response
              </Badge>
            </>
          )}
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Conversations</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : (chatStats?.totalConversations || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              +{chatStats?.todayConversations || 0} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Accuracy</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {statsLoading ? '-' : `${chatStats?.aiAccuracy || 0}%`}
            </div>
            <p className="text-xs text-muted-foreground">
              Prediction accuracy
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI-Generated Profit</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {statsLoading ? '-' : formatCurrency(chatStats?.totalProfit || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              From AI recommendations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : `${chatStats?.avgResponseTime || 0}s`}
            </div>
            <p className="text-xs text-muted-foreground">
              Average AI response
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Phase Progress Visualizer */}
      {currentPhase !== ExecutionPhase.IDLE && (
        <PhaseProgressVisualizer
          currentPhase={currentPhase}
          phaseHistory={[]}
          isCompact
          showMetrics={false}
        />
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Interface with Tabs */}
        <div className={`${isExpanded ? 'lg:col-span-3' : 'lg:col-span-2'} transition-all duration-300`}>
          <Tabs value={selectedTab} onValueChange={setSelectedTab}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="conversational">Conversational Trading</TabsTrigger>
              <TabsTrigger value="basic">Basic Chat</TabsTrigger>
            </TabsList>
            <TabsContent value="conversational" className="mt-4">
              <div className={`${isExpanded ? 'h-[80vh]' : 'h-[600px]'}`}>
                <ConversationalTradingInterface
                  isExpanded={isExpanded}
                  onToggleExpand={() => setIsExpanded(!isExpanded)}
                  isPaperTrading={isPaperTrading}
                  className="h-full"
                />
              </div>
            </TabsContent>
            <TabsContent value="basic" className="mt-4">
              <div className={`${isExpanded ? 'h-[80vh]' : 'h-[600px]'}`}>
                <ChatInterface
                  isExpanded={isExpanded}
                  onToggleExpand={() => setIsExpanded(!isExpanded)}
                  className="h-full"
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Side Panel */}
        {!isExpanded && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* AI Capabilities */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  AI Capabilities
                </CardTitle>
                <CardDescription>
                  What your AI money manager can do
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/10">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <div>
                    <div className="font-medium text-sm">Trade Execution</div>
                    <div className="text-xs text-muted-foreground">Buy/sell with AI analysis</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/10">
                  <BarChart3 className="h-4 w-4 text-blue-500" />
                  <div>
                    <div className="font-medium text-sm">Portfolio Analysis</div>
                    <div className="text-xs text-muted-foreground">Performance & optimization</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-yellow-500/5 border border-yellow-500/10">
                  <Shield className="h-4 w-4 text-yellow-500" />
                  <div>
                    <div className="font-medium text-sm">Risk Management</div>
                    <div className="text-xs text-muted-foreground">Assessment & mitigation</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/10">
                  <Target className="h-4 w-4 text-purple-500" />
                  <div>
                    <div className="font-medium text-sm">Opportunity Discovery</div>
                    <div className="text-xs text-muted-foreground">Find new investments</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent AI Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Recent AI Actions
                </CardTitle>
                <CardDescription>
                  Latest AI-driven portfolio activities
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {actionsLoading ? (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    Loading recent actions...
                  </div>
                ) : recentActions && recentActions.length > 0 ? (
                  recentActions.map((action: any) => (
                  <div key={action.id} className="flex items-start gap-3 p-3 rounded-lg border">
                    <div className="flex-shrink-0">
                      {getActionIcon(action.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{action.action}</div>
                      <div className="text-xs text-muted-foreground">{action.amount}</div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">{action.timestamp}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={`text-xs ${getStatusColor(action.status)}`}>
                            {action.status}
                          </Badge>
                          {action.profit && (
                            <span className={`text-xs font-medium ${
                              action.profit.startsWith('+') ? 'text-green-500' : 'text-blue-500'
                            }`}>
                              {action.profit}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No recent actions
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">AI Performance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Successful Trades</span>
                  <span className="font-medium">{chatStats?.successfulTrades || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Portfolio Optimizations</span>
                  <span className="font-medium">{chatStats?.portfolioOptimizations || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Risk Assessments</span>
                  <span className="font-medium">{chatStats?.riskAssessments || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">AI Accuracy</span>
                  <span className="font-medium text-green-500">{chatStats?.aiAccuracy || 0}%</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>

      {/* Help Section */}
      {!isExpanded && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">How to Use AI Money Manager Chat</CardTitle>
            <CardDescription>
              Natural language examples for managing your cryptocurrency portfolio
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <h4 className="font-semibold text-sm">📊 Portfolio Management</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>"Show me my portfolio performance"</div>
                  <div>"How is my Bitcoin position doing?"</div>
                  <div>"What's my total profit this month?"</div>
                  <div>"Analyze my portfolio allocation"</div>
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="font-semibold text-sm">💹 Trading Commands</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>"Buy $1000 of Ethereum"</div>
                  <div>"Sell half of my SOL position"</div>
                  <div>"Execute a limit order for BTC at $50k"</div>
                  <div>"What's the best entry point for ADA?"</div>
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="font-semibold text-sm">⚖️ Risk & Rebalancing</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>"Analyze the risk in my portfolio"</div>
                  <div>"Should I rebalance my allocation?"</div>
                  <div>"Set stop losses for high-risk positions"</div>
                  <div>"How can I reduce portfolio volatility?"</div>
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="font-semibold text-sm">🔍 Market Opportunities</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>"Find me the best opportunities"</div>
                  <div>"What altcoins look promising?"</div>
                  <div>"Analyze the DeFi market trends"</div>
                  <div>"Should I invest in Layer 2 tokens?"</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AIChatPage;