import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  MessageSquare,
  TrendingUp,
  Settings,
  Users,
  Zap,
  Wallet,
  Shield,
  Activity,
  DollarSign,
  BarChart3,
  Bot,
  Play,
  Pause,
  History,
  AlertCircle,
  CheckCircle,
  Target
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';

// Import existing components
import ConversationalTradingInterface from '@/components/chat/ConversationalTradingInterface';
import PhaseProgressVisualizer, { ExecutionPhase } from '@/components/trading/PhaseProgressVisualizer';
import PaperTradingToggle from '@/components/trading/PaperTradingToggle';

// Import stores
import { useGlobalPaperModeStore, useGlobalPaperMode } from '@/store/globalPaperModeStore';
import { useAuthStore } from '@/store/authStore';

// Import API client
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage } from '@/lib/utils';

// Manual Trading Component (extracted from ManualTradingPage)
import ManualTradingPanel from './components/ManualTradingPanel';

// Autonomous Settings Component (extracted from AutonomousPage)
import AutonomousSettingsPanel from './components/AutonomousSettingsPanel';

// Opportunities Drawer
import { OpportunitiesDrawer } from '@/components/trading/opportunities';
import type { OpportunitiesDrawerState, Opportunity } from '@/components/trading/opportunities';

// AI Showcase Components
import { AIConsensusCard } from '@/components/trading/AIConsensusCard';
import { MarketContextCard } from '@/components/trading/MarketContextCard';
import { AIUsageStats } from '@/components/trading/AIUsageStats';
import { QuickActionBar } from '@/components/trading/QuickActionBar';
import { PortfolioImpactPreview } from '@/components/trading/PortfolioImpactPreview';

interface TradeExecution {
  id: string;
  phase: ExecutionPhase;
  details: {
    symbol?: string;
    side?: string;
    quantity?: number;
    price?: number;
  };
  timestamp: Date;
  isPaperMode: boolean;
}

const AIMoneyManager: React.FC = () => {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const isPaperMode = useGlobalPaperMode();
  const { fetchPaperStats, paperStats } = useGlobalPaperModeStore();

  // State management
  const [activeTab, setActiveTab] = useState('conversation');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  const [phaseDetails, setPhaseDetails] = useState<Record<string, any>>({});
  const [isAutonomousEnabled, setIsAutonomousEnabled] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<TradeExecution | null>(null);
  const [recentExecutions, setRecentExecutions] = useState<TradeExecution[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [opportunitiesDrawer, setOpportunitiesDrawer] = useState<OpportunitiesDrawerState>({
    open: false,
    data: null,
    executing: new Set(),
    validating: new Set()
  });
  const [credits, setCredits] = useState<number>(0);
  const [portfolioValue, setPortfolioValue] = useState<number>(10000); // Default portfolio value
  const [latestConsensusData, setLatestConsensusData] = useState<any>(null);
  const [marketContext, setMarketContext] = useState<any>(null);
  const [usageData, setUsageData] = useState<any>(null);

  // WebSocket connection for real-time updates
  const [ws, setWs] = useState<WebSocket | null>(null);

  // Initialize chat session
  useEffect(() => {
    initializeChatSession();
    if (isPaperMode) {
      fetchPaperStats();
    }
  }, [isPaperMode]);

  // Setup WebSocket connection
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const initializeChatSession = async () => {
    try {
      const response = await apiClient.post('/chat/session/new', {
        session_type: 'trading',
        context: {
          isPaperMode,
          user_id: user?.id
        }
      });

      const { success, session_id: newSessionId, message } = response.data ?? {};

      if (success && newSessionId) {
        setSessionId(newSessionId);
        return;
      }

      throw new Error(message || 'Missing chat session id in response');
    } catch (error) {
      console.error('Failed to initialize chat session', error);
      toast({
        title: "Connection Error",
        description: "Failed to initialize chat session",
        variant: "destructive"
      });
    }
  };

  const connectWebSocket = () => {
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/ai-consensus/ws`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      // WebSocket connected successfully
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    websocket.onerror = () => {
      toast({
        title: "Connection Error",
        description: "WebSocket connection failed. Using fallback mode.",
        variant: "destructive"
      });
    };

    setWs(websocket);
  };

  const handleWebSocketMessage = (data: Record<string, any>) => {
    if (data.type === 'phase_update') {
      setCurrentPhase(data.phase);
      setPhaseDetails((prev: Record<string, any>) => ({
        ...prev,
        [data.phase]: data.details
      }));
    } else if (data.type === 'execution_complete') {
      handleExecutionComplete(data);
    }
  };

  const handleExecutionComplete = (data: Record<string, any>) => {
    setIsExecuting(false);
    setCurrentPhase(ExecutionPhase.COMPLETED);
    
    const execution: TradeExecution = {
      id: data.execution_id,
      phase: ExecutionPhase.COMPLETED,
      details: data.details,
      timestamp: new Date(),
      isPaperMode: data.isPaperMode
    };

    setCurrentExecution(execution);
    setRecentExecutions((prev: TradeExecution[]) => [execution, ...prev].slice(0, 10));

    toast({
      title: "Trade Executed Successfully",
      description: `${data.details.symbol} - ${data.details.side} ${data.details.quantity}`,
      // duration: 5000,
    });

    // Reset after delay
    setTimeout(() => {
      setCurrentPhase(ExecutionPhase.IDLE);
      setPhaseDetails({});
    }, 5000);
  };

  // Execute trade through 5-phase process
  const executeTradeWithPhases = async (tradeParams: Record<string, any>) => {
    setIsExecuting(true);
    
    try {
      // Phase 1: Analysis
      setCurrentPhase(ExecutionPhase.ANALYSIS);
      const analysisResponse = await apiClient.post('/ai-consensus/analyze-opportunity', {
        ...tradeParams,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: Record<string, any>) => ({
        ...prev,
        analysis: analysisResponse.data.data
      }));

      // Phase 2: Consensus
      setCurrentPhase(ExecutionPhase.CONSENSUS);
      const consensusResponse = await apiClient.post('/ai-consensus/consensus-decision', {
        analysis_id: analysisResponse.data.data.id,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: Record<string, any>) => ({
        ...prev,
        consensus: consensusResponse.data.data
      }));

      // Phase 3: Validation
      setCurrentPhase(ExecutionPhase.VALIDATION);
      const validationResponse = await apiClient.post('/ai-consensus/validate-trade', {
        consensus_id: consensusResponse.data.data.id,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: Record<string, any>) => ({
        ...prev,
        validation: validationResponse.data.data
      }));

      // Check if validation passed
      if (!validationResponse.data.data.passed) {
        throw new Error('Trade validation failed: ' + validationResponse.data.data.reason);
      }

      // Phase 4: Execution
      setCurrentPhase(ExecutionPhase.EXECUTION);
      const endpoint = isPaperMode 
        ? '/paper-trading/execute'
        : '/trading/execute';

      const executionResponse = await apiClient.post(endpoint, {
        validation_id: validationResponse.data.data.id,
        ...tradeParams
      });

      setPhaseDetails((prev: Record<string, any>) => ({
        ...prev,
        execution: executionResponse.data.data
      }));

      // Phase 5: Monitoring
      setCurrentPhase(ExecutionPhase.MONITORING);
      
      // Start monitoring via WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'start_monitoring',
          execution_id: executionResponse.data.data.id
        }));
      }

    } catch (error: any) {
      setIsExecuting(false);
      setCurrentPhase(ExecutionPhase.IDLE);
      
      toast({
        title: "Trade Execution Failed",
        description: error.message || "An error occurred during trade execution",
        variant: "destructive",
        // duration: 5000,
      });
    }
  };

  // Handle trade from chat interface
  const handleChatTrade = async (tradeData: Record<string, any>) => {
    await executeTradeWithPhases(tradeData);
  };

  // Handle manual trade
  const handleManualTrade = async (tradeData: Record<string, any>) => {
    await executeTradeWithPhases({
      ...tradeData,
      source: 'manual'
    });
  };

  // Toggle autonomous mode
  const toggleAutonomousMode = async () => {
    try {
      const newState = !isAutonomousEnabled;
      
      const response = await apiClient.post('/trading/autonomous/toggle', {
        enable: newState,
        mode: 'balanced'
      });

      if (response.data.success) {
        setIsAutonomousEnabled(newState);
        
        toast({
          title: newState ? "Autonomous Mode Enabled" : "Autonomous Mode Disabled",
          description: newState 
            ? "AI will now execute trades automatically based on your settings"
            : "Autonomous trading has been paused",
          // duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to change autonomous mode",
        variant: "destructive",
      });
    }
  };

  // Scan for opportunities
  const handleScanOpportunities = useCallback(async () => {
    try {
      setIsExecuting(true);

      toast({
        title: "Scanning Markets",
        description: "AI models are analyzing opportunities across all markets..."
      });

      // Call opportunity scan API
      const response = await apiClient.post('/ai-consensus/analyze-opportunity', {
        symbol: 'BTC/USDT', // Default symbol, could be made configurable
        analysis_type: 'opportunity',
        timeframe: '4h',
        confidence_threshold: 0.7,
        ai_models: 'all',
        include_risk_metrics: true
      });

      // Parse response
      const opportunityData = response.data?.result?.opportunity_analysis || response.data?.result || response.data;
      const opportunities = opportunityData?.opportunities || opportunityData?.detected_opportunities || [];

      if (opportunities.length === 0) {
        toast({
          title: "No Opportunities Found",
          description: "AI didn't detect any high-confidence trading opportunities at this time."
        });
        return;
      }

      // Batch validate all opportunities
      const validationResults = await Promise.allSettled(
        opportunities.map((opp: any) =>
          apiClient.post('/ai-consensus/validate-trade', {
            trade_data: {
              symbol: opp.symbol,
              action: opp.side,
              amount: opp.suggested_position_size,
              order_type: 'market',
              stop_loss: opp.stop_loss_percent,
              take_profit: opp.take_profit_percent,
              leverage: opp.leverage || 1,
              strategy: opp.strategy
            },
            confidence_threshold: 0.7,
            ai_models: 'all',
            execution_urgency: 'normal'
          }).then(res => res.data?.result || res.data)
        )
      );

      // Split into validated vs non-validated
      const validated: Opportunity[] = [];
      const nonValidated: Opportunity[] = [];

      opportunities.forEach((opp: any, idx: number) => {
        const validation = validationResults[idx];
        const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString();

        const opportunity: Opportunity = {
          id: crypto.randomUUID(),
          symbol: opp.symbol,
          side: opp.side,
          strategy: opp.strategy || 'Unknown',
          confidence: opp.confidence || 0,
          entry_price: opp.entry_price || 0,
          stop_loss: opp.stop_loss || 0,
          take_profit: opp.take_profit || 0,
          suggested_position_size: opp.suggested_position_size || 0,
          position_size_percent: opp.position_size_percent || 0,
          max_risk: opp.max_risk || 0,
          max_risk_percent: opp.max_risk_percent || 0,
          potential_gain: opp.potential_gain || 0,
          potential_gain_percent: opp.potential_gain_percent || 0,
          risk_reward_ratio: opp.risk_reward_ratio || 0,
          timeframe: opp.timeframe || '1h',
          reasoning: opp.reasoning,
          indicators: opp.indicators,
          timestamp: new Date().toISOString(),
          expires_at: expiresAt,
          aiValidated: false,
          validation: undefined,
          validationReason: undefined
        };

        if (validation.status === 'fulfilled' && validation.value?.approved) {
          opportunity.aiValidated = true;
          opportunity.validation = {
            approved: validation.value.approved,
            consensus_score: validation.value.consensus_score || 0,
            confidence: validation.value.confidence || 0,
            reason: validation.value.reason,
            model_responses: validation.value.model_responses,
            risk_assessment: validation.value.risk_assessment
          };
          validated.push(opportunity);
        } else {
          opportunity.validationReason = validation.status === 'fulfilled'
            ? validation.value?.reason
            : 'Validation failed';
          nonValidated.push(opportunity);
        }
      });

      // Sort validated by consensus score
      const sortedValidated = [...validated].sort((a, b) => {
        const scoreA = a.validation?.consensus_score ?? 0;
        const scoreB = b.validation?.consensus_score ?? 0;
        return scoreB - scoreA;
      });

      // Open drawer
      setOpportunitiesDrawer({
        open: true,
        data: {
          validated: sortedValidated,
          nonValidated,
          totalCount: opportunities.length,
          validatedCount: sortedValidated.length,
          scanCost: opportunities.length * 3, // Approximate cost
          executionCostPerTrade: 2
        },
        executing: new Set(),
        validating: new Set()
      });

      toast({
        title: "Scan Complete",
        description: `Found ${opportunities.length} opportunities (${sortedValidated.length} AI-validated)`
      });

    } catch (error: any) {
      console.error('Opportunity scan failed', error);
      toast({
        title: "Scan Failed",
        description: error?.response?.data?.detail || error?.message || "Failed to scan for opportunities",
        variant: "destructive"
      });
    } finally {
      setIsExecuting(false);
    }
  }, [toast]);

  // Execute single opportunity
  const handleExecuteOpportunity = useCallback(async (opportunityId: string, positionSize: number) => {
    try {
      setOpportunitiesDrawer(prev => ({
        ...prev,
        executing: new Set([...prev.executing, opportunityId])
      }));

      const opportunity = [...(opportunitiesDrawer.data?.validated || []), ...(opportunitiesDrawer.data?.nonValidated || [])]
        .find(opp => opp.id === opportunityId);

      if (!opportunity) {
        throw new Error('Opportunity not found');
      }

      // Execute trade
      const response = await apiClient.post('/trading/execute', {
        symbol: opportunity.symbol,
        action: opportunity.side,
        amount: positionSize,
        order_type: 'market',
        stop_loss: opportunity.stop_loss,
        take_profit: opportunity.take_profit,
        source: 'ai_opportunity'
      });

      if (response.data.success) {
        toast({
          title: "Trade Executed",
          description: `Successfully executed ${opportunity.side} ${positionSize} ${opportunity.symbol}`,
        });

        // Remove opportunity from drawer
        setOpportunitiesDrawer(prev => {
          if (!prev.data) return prev;
          return {
            ...prev,
            data: {
              ...prev.data,
              validated: prev.data.validated.filter(opp => opp.id !== opportunityId),
              nonValidated: prev.data.nonValidated.filter(opp => opp.id !== opportunityId)
            }
          };
        });
      }

    } catch (error: any) {
      console.error('Trade execution failed', error);
      toast({
        title: "Execution Failed",
        description: error?.response?.data?.detail || error?.message || "Failed to execute trade",
        variant: "destructive"
      });
    } finally {
      setOpportunitiesDrawer(prev => {
        const newExecuting = new Set(prev.executing);
        newExecuting.delete(opportunityId);
        return { ...prev, executing: newExecuting };
      });
    }
  }, [opportunitiesDrawer, toast]);

  // Batch execute opportunities
  const handleBatchExecuteOpportunities = useCallback(async (opportunityIds: string[]) => {
    try {
      setOpportunitiesDrawer(prev => ({
        ...prev,
        executing: new Set([...prev.executing, ...opportunityIds])
      }));

      const results = await Promise.allSettled(
        opportunityIds.map(id => handleExecuteOpportunity(id, 0)) // Position size should be set already
      );

      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;

      toast({
        title: "Batch Execution Complete",
        description: `${successful} successful, ${failed} failed`
      });

    } catch (error: any) {
      console.error('Batch execution failed', error);
      toast({
        title: "Batch Execution Failed",
        description: "Failed to execute batch trades",
        variant: "destructive"
      });
    } finally {
      setOpportunitiesDrawer(prev => ({
        ...prev,
        executing: new Set()
      }));
    }
  }, [handleExecuteOpportunity, toast]);

  // Validate opportunity
  const handleValidateOpportunity = useCallback(async (opportunityId: string) => {
    try {
      setOpportunitiesDrawer(prev => ({
        ...prev,
        validating: new Set([...prev.validating, opportunityId])
      }));

      const opportunity = opportunitiesDrawer.data?.nonValidated.find(opp => opp.id === opportunityId);
      if (!opportunity) {
        throw new Error('Opportunity not found');
      }

      const response = await apiClient.post('/ai-consensus/validate-trade', {
        trade_data: {
          symbol: opportunity.symbol,
          action: opportunity.side,
          amount: opportunity.suggested_position_size,
          order_type: 'market',
          stop_loss: opportunity.stop_loss,
          take_profit: opportunity.take_profit
        },
        confidence_threshold: 0.7,
        ai_models: 'all',
        execution_urgency: 'normal'
      });

      const result = response.data?.result || response.data;

      if (result.approved) {
        // Move to validated
        setOpportunitiesDrawer(prev => {
          if (!prev.data) return prev;

          const updatedOpportunity: Opportunity = {
            ...opportunity,
            aiValidated: true,
            validation: {
              approved: result.approved,
              consensus_score: result.consensus_score || 0,
              confidence: result.confidence || 0,
              reason: result.reason,
              model_responses: result.model_responses,
              risk_assessment: result.risk_assessment
            }
          };

          return {
            ...prev,
            data: {
              ...prev.data,
              validated: [...prev.data.validated, updatedOpportunity].sort((a, b) => {
                const scoreA = a.validation?.consensus_score ?? 0;
                const scoreB = b.validation?.consensus_score ?? 0;
                return scoreB - scoreA;
              }),
              nonValidated: prev.data.nonValidated.filter(opp => opp.id !== opportunityId)
            }
          };
        });

        toast({
          title: "Validation Successful",
          description: `Opportunity approved with ${result.consensus_score}% consensus`
        });
      } else {
        toast({
          title: "Validation Failed",
          description: result.reason || "AI consensus rejected this opportunity",
          variant: "destructive"
        });
      }

    } catch (error: any) {
      console.error('Validation failed', error);
      toast({
        title: "Validation Error",
        description: error?.response?.data?.detail || error?.message || "Failed to validate opportunity",
        variant: "destructive"
      });
    } finally {
      setOpportunitiesDrawer(prev => {
        const newValidating = new Set(prev.validating);
        newValidating.delete(opportunityId);
        return { ...prev, validating: newValidating };
      });
    }
  }, [opportunitiesDrawer, toast]);

  // Apply opportunity to trade form
  const handleApplyOpportunityToForm = useCallback((opportunity: Opportunity) => {
    // Update phase details with the opportunity suggestion
    setPhaseDetails(prev => ({
      ...prev,
      analysis: {
        ...prev.analysis,
        suggestions: {
          symbol: opportunity.symbol,
          side: opportunity.side,
          amount: opportunity.suggested_position_size,
          price: opportunity.entry_price,
          stopLoss: opportunity.stop_loss,
          takeProfit: opportunity.take_profit
        }
      }
    }));

    // Close drawer
    setOpportunitiesDrawer(prev => ({ ...prev, open: false }));

    // Switch to manual trading tab
    setActiveTab('manual');

    toast({
      title: "Applied to Form",
      description: "Opportunity parameters have been applied to the trading form"
    });
  }, [toast]);

  // Fetch credits and portfolio on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch credits
        const creditsResponse = await apiClient.get('/credits/balance');
        const availableCredits = creditsResponse.data.available_credits || 0;
        const totalCredits = creditsResponse.data.total_purchased_credits || 1000;
        const usedCredits = creditsResponse.data.total_used_credits || 0;
        setCredits(availableCredits);

        // Set usage data for AIUsageStats
        setUsageData({
          remainingCredits: availableCredits,
          totalCredits: totalCredits,
          todayCalls: usedCredits,
          todayCost: usedCredits * 0.05, // Estimate
          profitGenerated: 0,
          roi: 0
        });

        // Fetch portfolio value
        const portfolioResponse = await apiClient.get('/portfolio/summary');
        setPortfolioValue(portfolioResponse.data.total_value || 10000);
      } catch (error) {
        console.error('Failed to fetch data', error);
        // Set default usage data on error
        setUsageData({
          remainingCredits: credits || 675,
          totalCredits: 1000,
          todayCalls: 0,
          todayCost: 0,
          profitGenerated: 0,
          roi: 0
        });
      }
    };
    fetchData();
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Header Section */}
      <div className="flex items-center justify-between p-6 border-b">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            AI Money Manager
          </h1>
          <p className="text-muted-foreground mt-1">
            Your intelligent trading companion with {isPaperMode ? 'paper' : 'real'} funds
          </p>
        </div>

        {/* Autonomous Mode Toggle */}
        <div className="flex items-center gap-2">
          <Switch
            id="autonomous-mode"
            checked={isAutonomousEnabled}
            onCheckedChange={toggleAutonomousMode}
          />
          <Label htmlFor="autonomous-mode" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Auto Mode
          </Label>
        </div>
      </div>

      {/* Paper Mode Alert */}
      {isPaperMode && (
        <Alert className="mx-6 mt-4 border-blue-500 bg-blue-500/10">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You're in Paper Trading mode. All trades use virtual funds for practice.
            {paperStats && (
              <span className="ml-2">
                Win Rate: {formatPercentage(paperStats.winRate)} | 
                Profit: {formatCurrency(paperStats.totalProfit)}
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content - Split View as Specified */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 min-h-0">
        {/* LEFT: Conversational Interface (col-span-7) - Original size */}
        <div className="col-span-1 lg:col-span-7 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="pb-0 flex-shrink-0">
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Conversational Interface
              </CardTitle>
              <CardDescription>
                Chat with AI about market analysis and trading decisions
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              <ConversationalTradingInterface
                isPaperTrading={isPaperMode}
                className="h-full"
                onTradeExecuted={handleChatTrade}
                sessionId={sessionId || undefined}
              />
            </CardContent>
          </Card>
        </div>

        {/* RIGHT: AI Intelligence Panel (col-span-5) - Always visible */}
        <div className="col-span-1 lg:col-span-5 flex flex-col gap-4 min-h-0 overflow-hidden">
          <div className="space-y-4 overflow-y-auto flex-1 pr-2 pb-4">
            {/* 5-Phase Visualizer */}
            <PhaseProgressVisualizer
            currentPhase={currentPhase}
            phaseHistory={[]}
            isCompact={false}
            showMetrics={true}
            allowManualControl={true}
            onPhaseOverride={(phase: ExecutionPhase) => {
              setCurrentPhase(phase);
            }}
          />

          {/* Quick Action Bar - AI Features */}
          <QuickActionBar
            onScanOpportunities={handleScanOpportunities}
            onValidateTrade={() => console.log('Validate trade')}
            onAssessRisk={() => console.log('Assess risk')}
            onRebalancePortfolio={() => console.log('Rebalance')}
            onFinalConsensus={() => console.log('Final consensus')}
            availableCredits={credits}
            compact={true}
          />

          {/* AI Consensus Card */}
          {latestConsensusData && (
            <AIConsensusCard
              consensusData={latestConsensusData}
              compact={true}
            />
          )}

          {/* Market Context Card */}
          {marketContext && (
            <MarketContextCard
              marketData={marketContext}
              compact={true}
            />
          )}

          {/* AI Usage Stats */}
          <AIUsageStats
            usageData={usageData}
            isLoading={!usageData}
            compact={true}
          />

          {/* Current Execution Details */}
          {isExecuting && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 animate-pulse" />
                  Executing Trade
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {phaseDetails.analysis && (
                    <div>
                      <p className="text-sm font-medium">Analysis Results:</p>
                      <p className="text-sm text-muted-foreground">
                        Confidence: {formatPercentage(phaseDetails.analysis.confidence)}
                      </p>
                    </div>
                  )}
                  
                  {phaseDetails.consensus && (
                    <div>
                      <p className="text-sm font-medium">AI Consensus:</p>
                      <p className="text-sm text-muted-foreground">
                        {phaseDetails.consensus.decision}
                      </p>
                    </div>
                  )}

                  {phaseDetails.validation && (
                    <div>
                      <p className="text-sm font-medium">Validation:</p>
                      <div className="flex items-center gap-2">
                        {phaseDetails.validation.passed ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-sm text-muted-foreground">
                          {phaseDetails.validation.message}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Current Positions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="h-5 w-5" />
                Current Positions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentExecutions.length > 0 ? (
                <div className="space-y-2">
                  {recentExecutions.slice(0, 5).map((execution) => (
                    <div
                      key={execution.id}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                    >
                      <div className="flex items-center gap-2">
                        {execution.isPaperMode && (
                          <Badge variant="outline" className="text-xs">
                            Paper
                          </Badge>
                        )}
                        <span className="text-sm font-medium">
                          {execution.details.symbol}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {execution.details.side}
                        </span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {new Date(execution.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No active positions</p>
                  <p className="text-xs">Start a conversation to begin trading</p>
                </div>
              )}
            </CardContent>
          </Card>
          </div>
        </div>
      </div>

      {/* BOTTOM: Tabs as Specified */}
      <div className="border-t bg-muted/30">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <div className="flex items-center justify-center py-2">
            <TabsList className="grid grid-cols-4 w-auto">
              <TabsTrigger value="conversation" className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Conversation
              </TabsTrigger>
              <TabsTrigger value="manual" className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Manual Trading
              </TabsTrigger>
              <TabsTrigger value="autonomous" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Autonomous Settings
              </TabsTrigger>
              <TabsTrigger value="copy" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Copy Trading
              </TabsTrigger>
            </TabsList>
          </div>
          
          {/* Tab Content Drawers */}
          <AnimatePresence mode="wait">
            {activeTab !== 'conversation' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t"
              >
                <div className="max-h-96 overflow-y-auto">
                  <TabsContent value="manual" className="p-6 m-0">
                    <div className="space-y-4">
                      {/* Scan Opportunities Button */}
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={handleScanOpportunities}
                        disabled={isExecuting}
                      >
                        <Target className="mr-2 h-4 w-4" />
                        Scan Market Opportunities
                      </Button>

                      {/* Manual Trading Panel */}
                      <ManualTradingPanel
                        isPaperMode={isPaperMode}
                        onExecuteTrade={handleManualTrade}
                        isExecuting={isExecuting}
                        aiSuggestions={phaseDetails.analysis?.suggestions}
                      />
                    </div>
                  </TabsContent>

                  <TabsContent value="autonomous" className="p-6 m-0">
                    <AutonomousSettingsPanel
                      isPaperMode={isPaperMode}
                      isEnabled={isAutonomousEnabled}
                      onToggle={toggleAutonomousMode}
                    />
                  </TabsContent>

                  <TabsContent value="copy" className="p-6 m-0">
                    <div className="text-center space-y-4">
                      <Users className="h-12 w-12 mx-auto text-muted-foreground" />
                      <div>
                        <h3 className="font-semibold">Copy Trading</h3>
                        <p className="text-sm text-muted-foreground">
                          Follow and copy successful traders automatically
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Browse Traders
                      </Button>
                    </div>
                  </TabsContent>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Tabs>
      </div>

      {/* Opportunities Drawer */}
      <OpportunitiesDrawer
        state={opportunitiesDrawer}
        onClose={() => setOpportunitiesDrawer(prev => ({ ...prev, open: false }))}
        onExecuteTrade={handleExecuteOpportunity}
        onExecuteBatch={handleBatchExecuteOpportunities}
        onValidateOpportunity={handleValidateOpportunity}
        onApplyToForm={handleApplyOpportunityToForm}
        availableCredits={credits}
        portfolioValue={portfolioValue}
      />
    </div>
  );
};

export default AIMoneyManager;