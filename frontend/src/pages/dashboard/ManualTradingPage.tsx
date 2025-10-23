import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import type { ComponentProps } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  BarChart3,
  Activity,
  Brain,
  Shield,
  RefreshCw,
  Play,
  Settings,
  Eye,
  AlertTriangle,
  CheckCircle,
  Zap,
  Clock,
  Sparkles,
  ListTree,
  Radio,
  LineChart,
  Equal
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { useUser } from '@/store/authStore';
import { useExchanges } from '@/hooks/useExchanges';
import { useStrategies } from '@/hooks/useStrategies';
import { usePortfolioStore } from '@/hooks/usePortfolio';
import { useAIConsensus } from '@/hooks/useAIConsensus';
import { useCredits } from '@/hooks/useCredits';
import { useChatStore, ChatMode } from '@/store/chatStore';
import PhaseProgressVisualizer, { ExecutionPhase } from '@/components/trading/PhaseProgressVisualizer';
import { PHASE_CONFIG } from '@/constants/trading';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { apiClient } from '@/lib/api/client';
import { AIConsensusCard } from '@/components/trading/AIConsensusCard';
import { MarketContextCard } from '@/components/trading/MarketContextCard';
import { AIUsageStats } from '@/components/trading/AIUsageStats';
import { OpportunitiesDrawer } from '@/components/trading/opportunities';
import type { OpportunitiesDrawerState, Opportunity } from '@/components/trading/opportunities';
import type { ConsensusData, MarketContext, AIPricingConfig } from './types';

type ManualWorkflowType =
  | 'trade_validation'
  | 'portfolio_rebalance'
  | 'opportunity_scan'
  | 'market_analysis'
  | 'portfolio_review';

interface ManualTradeRequest {
  symbol: string;
  action: 'buy' | 'sell';
  amount: number;
  orderType: 'market' | 'limit' | 'stop';
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
  exchange?: string;
  leverage?: number;
}

interface WorkflowConfig {
  type: ManualWorkflowType;
  timeframe: string;
  confidence: number;
  includeRiskMetrics: boolean;
  aiModels: string;
  targetSymbolsText: string;
  rebalanceThreshold: number;
  strategyId: string;
  customNotes: string;
}

type WorkflowLogLevel = 'info' | 'success' | 'warning' | 'error';

interface WorkflowLogEntry {
  id: string;
  time: string;
  level: WorkflowLogLevel;
  message: string;
}

interface ManualWorkflowSummary {
  content: string;
  confidence?: number;
  intent?: string;
  requiresApproval?: boolean;
  decisionId?: string;
  actionData?: Record<string, any>;
  aiAnalysis?: any;
}

const DEFAULT_WORKFLOW: WorkflowConfig = {
  type: 'trade_validation',
  timeframe: '1h',
  confidence: 80,
  includeRiskMetrics: true,
  aiModels: 'all',
  targetSymbolsText: 'BTC/USDT,ETH/USDT',
  rebalanceThreshold: 5,
  strategyId: 'manual',
  customNotes: ''
};

const ManualTradingPage: React.FC = () => {
  const user = useUser();
  const { toast } = useToast();
  const { exchanges, aggregatedStats } = useExchanges();
  const { strategies, availableStrategies, actions: strategyActions, executing: strategyExecuting } = useStrategies();
  const {
    totalValue,
    availableBalance,
    totalPnL,
    totalPnLPercent,
    dailyPnL,
    dailyPnLPercent,
    positions,
    marketData,
    recentTrades,
    fetchPortfolio,
    fetchStatus,
    fetchMarketData,
    fetchRecentTrades,
    connectWebSocket
  } = usePortfolioStore((state) => ({
    totalValue: state.totalValue,
    availableBalance: state.availableBalance,
    totalPnL: state.totalPnL,
    totalPnLPercent: state.totalPnLPercent,
    dailyPnL: state.dailyPnL,
    dailyPnLPercent: state.dailyPnLPercent,
    positions: state.positions,
    marketData: state.marketData,
    recentTrades: state.recentTrades,
    fetchPortfolio: state.fetchPortfolio,
    fetchStatus: state.fetchStatus,
    fetchMarketData: state.fetchMarketData,
    fetchRecentTrades: state.fetchRecentTrades,
    connectWebSocket: state.connectWebSocket
  }));

  const {
    aiStatus,
    consensusHistory,
    connectionStatus,
    analyzeOpportunity,
    validateTrade,
    assessRisk,
    reviewPortfolio,
    analyzeMarket,
    makeConsensusDecision,
    isAnalyzing
  } = useAIConsensus();

  const { balance, actions: creditActions, loading: creditsLoading } = useCredits();

  const sessionId = useChatStore((state) => state.sessionId);
  const initializeSession = useChatStore((state) => state.initializeSession);
  const setCurrentMode = useChatStore((state) => state.setCurrentMode);

  const [tradeForm, setTradeForm] = useState<ManualTradeRequest>({
    symbol: 'BTC/USDT',
    action: 'buy',
    amount: 1000,
    orderType: 'market',
    exchange: 'auto'
  });

  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig>(DEFAULT_WORKFLOW);
  const [workflowLogs, setWorkflowLogs] = useState<WorkflowLogEntry[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [aiSummary, setAiSummary] = useState<ManualWorkflowSummary | null>(null);
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  type PhaseHistoryEntry = ComponentProps<typeof PhaseProgressVisualizer>['phaseHistory'][number];
  const [phaseHistory, setPhaseHistory] = useState<PhaseHistoryEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTab, setActiveTab] = useState('trade');
  const [aiInsights, setAiInsights] = useState<Array<{ id: string; title: string; payload: any; function: string; timestamp: string }>>([]);
  const [latestConsensusData, setLatestConsensusData] = useState<ConsensusData | null>(null);
  const [marketContext, setMarketContext] = useState<MarketContext | null>(null);
  const [pricingConfig, setPricingConfig] = useState<AIPricingConfig | null>(null);
  const [pricingError, setPricingError] = useState<string | null>(null);
  const [opportunitiesDrawer, setOpportunitiesDrawer] = useState<OpportunitiesDrawerState>({
    open: false,
    data: null,
    executing: new Set(),
    validating: new Set()
  });

  const streamingControllerRef = useRef<AbortController | null>(null);
  const manualSessionRef = useRef<string | null>(null);
  const initializingSessionPromiseRef = useRef<Promise<void> | null>(null);

  const availableSymbols = useMemo(() => {
    const symbols = new Set<string>();
    positions.forEach((position) => symbols.add(position.symbol));
    marketData.forEach((item) => symbols.add(item.symbol));
    if (symbols.size === 0 && tradeForm.symbol) {
      symbols.add(tradeForm.symbol);
    }
    return Array.from(symbols).sort();
  }, [positions, marketData, tradeForm.symbol]);

  const selectedStrategy = useMemo(() => {
    if (!workflowConfig.strategyId || workflowConfig.strategyId === 'manual') {
      return undefined;
    }
    return availableStrategies[workflowConfig.strategyId];
  }, [workflowConfig.strategyId, availableStrategies]);

  const sanitizedTargetSymbols = useMemo(() => {
    return workflowConfig.targetSymbolsText
      .split(',')
      .map((symbol) => symbol.trim())
      .filter((symbol) => symbol.length > 0);
  }, [workflowConfig.targetSymbolsText]);

  const ensureSessionId = useCallback(async () => {
    if (manualSessionRef.current) {
      return manualSessionRef.current;
    }

    let existingSession = sessionId || useChatStore.getState().sessionId;

    if (!existingSession) {
      if (!initializingSessionPromiseRef.current) {
        initializingSessionPromiseRef.current = initializeSession();
      }

      try {
        await initializingSessionPromiseRef.current;
      } catch (error) {
        manualSessionRef.current = null;
        throw error;
      } finally {
        initializingSessionPromiseRef.current = null;
      }

      existingSession = useChatStore.getState().sessionId;
    }

    manualSessionRef.current = existingSession || null;
    return manualSessionRef.current;
  }, [sessionId, initializeSession]);

  const pushWorkflowLog = useCallback((level: WorkflowLogLevel, message: string) => {
    setWorkflowLogs((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        time: new Date().toLocaleTimeString(),
        level,
        message
      }
    ]);
  }, []);

  const appendPhase = useCallback((phase: ExecutionPhase, detail?: string) => {
    setPhaseHistory((prev) => {
      const { icon: PhaseIcon, details: configDetails = [], progress: _progress, ...phaseConfig } = PHASE_CONFIG[phase];
      const baseDetails = Array.isArray(configDetails) ? configDetails : [];
      const newDetails = detail ? [detail] : [];

      const existingIndex = prev.findIndex((item) => item.phase === phase);
      if (existingIndex >= 0) {
        const updated = [...prev];
        const existingDetails = updated[existingIndex].details ?? baseDetails;
        const mergedDetails = newDetails.length
          ? Array.from(new Set([...(existingDetails || []), ...newDetails]))
          : existingDetails;

        updated[existingIndex] = {
          ...updated[existingIndex],
          ...phaseConfig,
          icon: <PhaseIcon className="h-4 w-4" />,
          details: mergedDetails
        };
        return updated;
      }

      return [
        ...prev,
        {
          ...phaseConfig,
          icon: <PhaseIcon className="h-4 w-4" />,
          details: newDetails.length ? [...baseDetails, ...newDetails] : baseDetails
        }
      ];
    });
  }, []);

  const mapPhaseFromString = useCallback((phase?: string | null): ExecutionPhase | null => {
    if (!phase) return null;
    const normalized = phase.toLowerCase();
    if (normalized.includes('analysis')) return ExecutionPhase.ANALYSIS;
    if (normalized.includes('consensus')) return ExecutionPhase.CONSENSUS;
    if (normalized.includes('validation') || normalized.includes('risk')) return ExecutionPhase.VALIDATION;
    if (normalized.includes('execution')) return ExecutionPhase.EXECUTION;
    if (normalized.includes('monitor')) return ExecutionPhase.MONITORING;
    if (normalized.includes('complete')) return ExecutionPhase.COMPLETED;
    return null;
  }, []);

  const handlePhaseUpdate = useCallback(
    (phase?: string | null, detail?: string) => {
      const mapped = mapPhaseFromString(phase);
      if (!mapped) return;

      if (mapped === ExecutionPhase.COMPLETED) {
        appendPhase(mapped, detail);
        setCurrentPhase(mapped);
        return;
      }

      setCurrentPhase(mapped);
      appendPhase(mapped, detail);
    },
    [appendPhase, mapPhaseFromString]
  );

  const resetWorkflowState = useCallback(() => {
    setWorkflowLogs([]);
    setStreamingContent('');
    setAiSummary(null);
    setPhaseHistory([]);
    setCurrentPhase(ExecutionPhase.IDLE);
  }, []);

  const buildWorkflowMessage = useCallback(() => {
    const contextPayload = {
      workflow: workflowConfig.type,
      strategy: selectedStrategy
        ? {
            id: workflowConfig.strategyId,
            name: selectedStrategy.name,
            category: selectedStrategy.category,
            risk_level: selectedStrategy.risk_level
          }
        : null,
      trade_parameters: {
        symbol: tradeForm.symbol,
        action: tradeForm.action,
        amount: tradeForm.amount,
        order_type: tradeForm.orderType,
        stop_loss: tradeForm.stopLoss,
        take_profit: tradeForm.takeProfit,
        exchange: tradeForm.exchange,
        leverage: tradeForm.leverage
      },
      portfolio_snapshot: {
        total_value: totalValue,
        available_balance: availableBalance,
        total_pnl: totalPnL,
        positions,
        exchanges: aggregatedStats.exchanges
      },
      ai_preferences: {
        timeframe: workflowConfig.timeframe,
        confidence_target: workflowConfig.confidence,
        include_risk_metrics: workflowConfig.includeRiskMetrics,
        ai_models: workflowConfig.aiModels,
        target_symbols: sanitizedTargetSymbols,
        rebalance_threshold: workflowConfig.rebalanceThreshold
      },
      custom_notes: workflowConfig.customNotes || undefined,
      interface_origin: 'manual_dashboard'
    };

    const readableName = {
      trade_validation: 'trade validation',
      portfolio_rebalance: 'portfolio rebalancing',
      opportunity_scan: 'opportunity scanning',
      market_analysis: 'market analysis',
      portfolio_review: 'portfolio review'
    }[workflowConfig.type];

    return [
      `Run the full 5-phase institutional workflow for ${readableName}.`,
      'Stream updates for every phase as they occur and explicitly tag phase names in the updates.',
      'Use the live data provided to make decisions and finish with a concise execution checklist and recommendation.',
      'Context:',
      JSON.stringify(contextPayload, null, 2)
    ].join('\n');
  }, [
    workflowConfig,
    selectedStrategy,
    tradeForm,
    totalValue,
    availableBalance,
    totalPnL,
    positions,
    aggregatedStats.exchanges,
    sanitizedTargetSymbols
  ]);

  const runLiveWorkflow = useCallback(async () => {
    if (isStreaming) {
      streamingControllerRef.current?.abort();
    }

    const token = localStorage.getItem('auth_token');
    if (!token) {
      toast({
        title: 'Authentication Required',
        description: 'Please log in to start an AI workflow.',
        variant: 'destructive'
      });
      return;
    }

    const baseURL = apiClient.defaults.baseURL;
    if (!baseURL) {
      toast({
        title: 'Configuration Error',
        description: 'API base URL is not configured. Please refresh the page.',
        variant: 'destructive'
      });
      return;
    }

    resetWorkflowState();
    pushWorkflowLog('info', 'Initializing AI workflow...');

    try {
      const activeSession = await ensureSessionId();
      const message = buildWorkflowMessage();
      const params = new URLSearchParams({
        message,
        session_id: activeSession || '',
        conversation_mode: 'live_trading'
      });

      const url = `${baseURL}/unified-chat/stream?${params.toString()}`;
      const { fetchEventSource } = await import('@microsoft/fetch-event-source');

      const controller = new AbortController();
      streamingControllerRef.current = controller;
      setIsStreaming(true);
      setCurrentPhase(ExecutionPhase.ANALYSIS);

      let fullContent = '';
      let streamMetadata: Record<string, any> = {};

      await fetchEventSource(url, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'text/event-stream'
        },
        signal: controller.signal,
        onopen: async (response) => {
          if (!response.ok) {
            pushWorkflowLog('error', `Failed to start workflow: HTTP ${response.status}`);
            throw new Error(`HTTP ${response.status}`);
          }

          pushWorkflowLog('info', 'AI workflow connection established.');
        },
        onmessage: (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.metadata) {
              streamMetadata = { ...streamMetadata, ...data.metadata };
            }

            if (data.type === 'progress' || data.type === 'processing') {
              const detail = data.progress?.message || data.content || 'Processing update received.';
              pushWorkflowLog('info', detail);
              handlePhaseUpdate(data.progress?.phase || data.metadata?.phase || data.phase, detail);
            }

            if (data.ai_analysis?.current_phase) {
              handlePhaseUpdate(data.ai_analysis.current_phase, data.ai_analysis.summary);
            }

            if (data.type === 'chunk' || data.type === 'response' || data.type === 'persona_enriched') {
              if (data.content) {
                fullContent += data.content;
                setStreamingContent(fullContent);
              }

              handlePhaseUpdate(data.metadata?.phase, data.metadata?.update);
            }

            if (data.type === 'complete') {
              setIsStreaming(false);
              streamingControllerRef.current = null;
              handlePhaseUpdate(data.metadata?.phase || 'completed', data.content || 'Workflow completed.');
              setCurrentPhase(ExecutionPhase.COMPLETED);

              const summary: ManualWorkflowSummary = {
                content: fullContent,
                confidence: data.confidence ?? streamMetadata.confidence,
                intent: data.intent ?? streamMetadata.intent,
                requiresApproval: data.requires_approval ?? streamMetadata.requires_approval,
                decisionId: data.decision_id ?? streamMetadata.decision_id,
                actionData: data.action_data ?? streamMetadata.action_data,
                aiAnalysis: data.ai_analysis ?? streamMetadata.ai_analysis
              };

              setAiSummary(summary);
              pushWorkflowLog('success', 'Workflow completed with AI recommendation ready.');

              creditActions.fetchBalance();
              fetchPortfolio();
              fetchRecentTrades();
            }

            if (data.type === 'error') {
              setIsStreaming(false);
              streamingControllerRef.current = null;
              pushWorkflowLog('error', data.error || 'AI workflow encountered an error.');
            }
          } catch (error) {
            console.error('Failed to parse SSE data', error);
            pushWorkflowLog('warning', 'Received unrecognized streaming data.');
          }
        },
        onerror: (error) => {
          setIsStreaming(false);
          streamingControllerRef.current = null;
          pushWorkflowLog('error', `Streaming error: ${error.message}`);
          controller.abort();
          throw error;
        },
        onclose: () => {
          setIsStreaming(false);
          streamingControllerRef.current = null;
          pushWorkflowLog('info', 'AI workflow connection closed.');
        }
      });
      } catch (error: any) {
        setIsStreaming(false);
        streamingControllerRef.current?.abort();
        streamingControllerRef.current = null;
        pushWorkflowLog('error', error?.message || 'AI workflow failed to start.');
      }
    }, [
    isStreaming,
    toast,
    resetWorkflowState,
    pushWorkflowLog,
    ensureSessionId,
    buildWorkflowMessage,
    handlePhaseUpdate,
    creditActions,
    fetchPortfolio,
    fetchRecentTrades
  ]);

  const handleTradeSubmit = useCallback(async () => {
    if (!tradeForm.symbol || !tradeForm.amount) {
      toast({
        title: 'Missing Information',
        description: 'Please provide at least a symbol and trade amount.',
        variant: 'destructive'
      });
      return;
    }

    try {
      pushWorkflowLog('info', `Submitting ${tradeForm.action.toUpperCase()} order for ${tradeForm.symbol}.`);
      const response = await apiClient.post('/trading/execute', {
        symbol: tradeForm.symbol,
        action: tradeForm.action,
        amount: tradeForm.amount,
        order_type: tradeForm.orderType,
        price: tradeForm.price,
        stop_loss: tradeForm.stopLoss,
        take_profit: tradeForm.takeProfit,
        exchange: tradeForm.exchange === 'auto' ? undefined : tradeForm.exchange,
        leverage: tradeForm.leverage,
        strategy_type: selectedStrategy?.name
      });

      const result = response.data;

      pushWorkflowLog('success', `Trade executed successfully on ${result.exchange || 'selected exchange'}.`);
      toast({
        title: 'Trade Executed',
        description: `${tradeForm.action.toUpperCase()} ${tradeForm.symbol} · ${formatCurrency(Number(result.amount || tradeForm.amount))}`,
        variant: 'default'
      });

      creditActions.fetchBalance();
      fetchPortfolio();
      fetchRecentTrades();
    } catch (error: any) {
      console.error('Trade execution failed', error);
      pushWorkflowLog('error', error?.response?.data?.detail || error?.message || 'Trade execution failed.');
      toast({
        title: 'Trade Execution Failed',
        description: error?.response?.data?.detail || error?.message || 'Unable to execute trade.',
        variant: 'destructive'
      });
    }
  }, [tradeForm, toast, selectedStrategy, pushWorkflowLog, creditActions, fetchPortfolio, fetchRecentTrades]);

  const recordInsight = useCallback((title: string, fn: string, payload: any) => {
    setAiInsights((prev) => [
      {
        id: crypto.randomUUID(),
        title,
        function: fn,
        payload,
        timestamp: new Date().toISOString()
      },
      ...prev
    ]);
  }, []);

  const handleConsensusAction = useCallback(
    async (action: 'opportunity' | 'validation' | 'risk' | 'portfolio' | 'market' | 'decision') => {
      try {
        const primarySymbol = sanitizedTargetSymbols[0] || tradeForm.symbol;

        switch (action) {
          case 'opportunity': {
            pushWorkflowLog('info', `Scanning opportunities across ${sanitizedTargetSymbols.length || 1} symbols...`);

            // 1. Scan for opportunities
            const scanResult = await analyzeOpportunity({
              symbol: primarySymbol,
              analysis_type: workflowConfig.type === 'opportunity_scan' ? 'opportunity' : 'technical',
              timeframe: workflowConfig.timeframe,
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              include_risk_metrics: workflowConfig.includeRiskMetrics
            });

            // Parse the API response structure: data.result.opportunity_analysis or data.opportunities
            const opportunityData = scanResult?.result?.opportunity_analysis || scanResult?.result || scanResult;
            const opportunities = opportunityData?.opportunities || opportunityData?.detected_opportunities || [];

            pushWorkflowLog('info', `Found ${opportunities.length} opportunities. Validating with AI consensus...`);

            // 2. Batch validate all opportunities
            const validationResults = await Promise.allSettled(
              opportunities.map((opp: any) =>
                validateTrade({
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
                  confidence_threshold: workflowConfig.confidence,
                  ai_models: workflowConfig.aiModels,
                  execution_urgency: 'normal'
                })
              )
            );

            // 3. Split into validated vs non-validated
            const validated: Opportunity[] = [];
            const nonValidated: Opportunity[] = [];

            opportunities.forEach((opp: any, idx: number) => {
              const validation = validationResults[idx];
              const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString(); // 5 minutes from now

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
                timeframe: opp.timeframe || workflowConfig.timeframe,
                reasoning: opp.reasoning,
                indicators: opp.indicators,
                timestamp: new Date().toISOString(),
                expires_at: expiresAt,
                aiValidated: false,
                validation: undefined,
                validationReason: undefined
              };

              if (validation.status === 'fulfilled' && validation.value.approved) {
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
                  ? validation.value.reason
                  : 'Validation failed';
                nonValidated.push(opportunity);
              }
            });

            // 4. Calculate costs from backend pricing config (use defaults if not loaded)
            const config = pricingConfig || {
              opportunity_scan_cost: 1,
              validation_cost: 2,
              execution_cost: 2,
              per_call_estimate: 0.05
            };
            const scanCost = opportunities.length * config.opportunity_scan_cost;
            const validationCost = opportunities.length * config.validation_cost;
            const totalScanCost = scanCost + validationCost;

            // 5. Show drawer with tiered results
            setOpportunitiesDrawer({
              open: true,
              data: {
                validated,
                nonValidated,
                totalCount: opportunities.length,
                validatedCount: validated.length,
                scanCost: totalScanCost,
                executionCostPerTrade: config.execution_cost
              },
              executing: new Set(),
              validating: new Set()
            });

            // 6. Update consensus card with best validated opportunity (sort by consensus_score)
            if (validated.length > 0) {
              // Clone and sort to avoid mutation
              const sortedValidated = [...validated].sort((a, b) => {
                const scoreA = a.validation?.consensus_score ?? 0;
                const scoreB = b.validation?.consensus_score ?? 0;
                return scoreB - scoreA; // Descending
              });
              const best = sortedValidated[0];
              setLatestConsensusData({
                consensus_score: best.validation?.consensus_score || 0,
                recommendation: best.side === 'buy' ? 'BUY' : 'SELL',
                confidence_threshold_met: true,
                model_responses: (best.validation?.model_responses || []).map(mr => ({
                  ...mr,
                  score: mr.confidence || 0  // Add missing score property
                })),
                cost_summary: { total_cost: totalScanCost },
                reasoning: best.reasoning || `Top opportunity from ${validated.length} validated`,
                timestamp: new Date().toISOString()
              });
            }

            // 7. Show toast
            toast({
              title: `✨ ${validated.length} AI-Validated Opportunities`,
              description: `${opportunities.length} total found | ${validated.length} ready to execute`,
            });

            recordInsight('Opportunity Scan', 'analyze_opportunity', { validated: validated.length, total: opportunities.length });
            pushWorkflowLog('success', `Found ${validated.length} validated, ${nonValidated.length} other opportunities`);
            break;
          }
          case 'validation': {
            pushWorkflowLog('info', 'Running AI trade validation.');
            const result = await validateTrade({
              trade_data: {
                symbol: tradeForm.symbol,
                action: tradeForm.action,
                amount: tradeForm.amount,
                order_type: tradeForm.orderType,
                stop_loss: tradeForm.stopLoss,
                take_profit: tradeForm.takeProfit,
                leverage: tradeForm.leverage,
                exchange: tradeForm.exchange,
                strategy: selectedStrategy?.name
              },
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              execution_urgency: 'normal'
            });
            recordInsight('Trade Validation', 'validate_trade', result);
            pushWorkflowLog('success', 'Trade validation completed.');
            break;
          }
          case 'risk': {
            pushWorkflowLog('info', 'Running portfolio risk assessment.');
            const result = await assessRisk({
              portfolio_data: {
                total_value: totalValue,
                available_balance: availableBalance,
                positions,
                daily_pnl: dailyPnL,
                exchanges: aggregatedStats.exchanges
              },
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              risk_type: 'comprehensive',
              stress_test: workflowConfig.includeRiskMetrics
            });
            recordInsight('Risk Assessment', 'risk_assessment', result);
            pushWorkflowLog('success', 'Risk assessment completed.');
            break;
          }
          case 'portfolio': {
            pushWorkflowLog('info', 'Reviewing portfolio with AI consensus.');
            const result = await reviewPortfolio({
              portfolio_data: {
                total_value: totalValue,
                available_balance: availableBalance,
                positions,
                target_symbols: sanitizedTargetSymbols
              },
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              review_type: 'comprehensive',
              benchmark: 'BTC'
            });
            recordInsight('Portfolio Review', 'portfolio_review', result);
            pushWorkflowLog('success', 'Portfolio review completed.');
            break;
          }
          case 'market': {
            pushWorkflowLog('info', `Running market analysis for ${sanitizedTargetSymbols.join(', ') || primarySymbol}.`);
            const result = await analyzeMarket({
              symbols: sanitizedTargetSymbols.length ? sanitizedTargetSymbols : [primarySymbol],
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              analysis_depth: workflowConfig.includeRiskMetrics ? 'deep' : 'standard',
              include_sentiment: workflowConfig.includeRiskMetrics
            });
            recordInsight('Market Analysis', 'market_analysis', result);
            pushWorkflowLog('success', 'Market analysis completed.');
            break;
          }
          case 'decision': {
            pushWorkflowLog('info', 'Requesting final consensus decision from AI.');
            const result = await makeConsensusDecision({
              decision_context: {
                workflow: workflowConfig.type,
                trade: {
                  symbol: tradeForm.symbol,
                  action: tradeForm.action,
                  amount: tradeForm.amount,
                  order_type: tradeForm.orderType
                },
                portfolio: {
                  total_value: totalValue,
                  positions
                },
                strategy: selectedStrategy?.name,
                custom_notes: workflowConfig.customNotes
              },
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              decision_type: workflowConfig.type === 'portfolio_rebalance' ? 'portfolio_rebalance' : 'trade_execution',
              execution_timeline: workflowConfig.type === 'portfolio_rebalance' ? 'same_day' : 'immediate'
            });
            recordInsight('Consensus Decision', 'consensus_decision', result);
            pushWorkflowLog('success', 'Consensus decision ready.');
            break;
          }
        }

        creditActions.fetchBalance();
        fetchPortfolio();
      } catch (error: any) {
        console.error('AI consensus action failed', error);
        pushWorkflowLog('error', error?.response?.data?.detail || error?.message || 'AI consensus request failed.');
        toast({
          title: 'AI Request Failed',
          description: error?.response?.data?.detail || error?.message || 'Unable to complete AI request.',
          variant: 'destructive'
        });
      }
    },
    [
      sanitizedTargetSymbols,
      tradeForm,
      analyzeOpportunity,
      workflowConfig,
      validateTrade,
      recordInsight,
      pushWorkflowLog,
      assessRisk,
      totalValue,
      availableBalance,
      positions,
      dailyPnL,
      aggregatedStats.exchanges,
      reviewPortfolio,
      analyzeMarket,
      makeConsensusDecision,
      creditActions,
      fetchPortfolio,
      toast,
      selectedStrategy
    ]
  );

  const applyAiRecommendationToTrade = useCallback(() => {
    if (!aiSummary?.actionData) {
      toast({
        title: 'No Action Available',
        description: 'Run an AI workflow to generate actionable trade parameters.',
        variant: 'destructive'
      });
      return;
    }

    const proposal = aiSummary.actionData;
    const validActions: ManualTradeRequest['action'][] = ['buy', 'sell'];
    const validOrderTypes: ManualTradeRequest['orderType'][] = ['market', 'limit', 'stop'];

    const normalizeString = (value: unknown) => {
      if (typeof value !== 'string') {
        return undefined;
      }

      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : undefined;
    };

    const normalizeEnum = <T extends string>(value: unknown, allowed: readonly T[]): T | undefined => {
      if (typeof value !== 'string') {
        return undefined;
      }

      const normalized = value.trim().toLowerCase();
      return allowed.includes(normalized as T) ? (normalized as T) : undefined;
    };

    const parsePositiveNumber = (value: unknown): number | undefined => {
      if (typeof value === 'number') {
        return Number.isFinite(value) && value > 0 ? value : undefined;
      }

      if (typeof value === 'string') {
        const trimmed = value.trim();

        if (!trimmed) {
          return undefined;
        }

        const parsed = Number(trimmed);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
      }

      return undefined;
    };

    const proposedAction = normalizeEnum<ManualTradeRequest['action']>(proposal.action, validActions);
    const proposedOrderType = normalizeEnum<ManualTradeRequest['orderType']>(proposal.order_type, validOrderTypes);

    if (proposal.action && !proposedAction) {
      toast({
        title: 'Invalid AI Recommendation',
        description: `AI returned invalid action: ${proposal.action}`,
        variant: 'destructive'
      });
      return;
    }

    if (proposal.order_type && !proposedOrderType) {
      toast({
        title: 'Invalid AI Recommendation',
        description: `AI returned invalid order type: ${proposal.order_type}`,
        variant: 'destructive'
      });
      return;
    }

    const amount = parsePositiveNumber(proposal.amount);
    const price = parsePositiveNumber(proposal.price);
    const stopLoss = parsePositiveNumber(proposal.stop_loss);
    const takeProfit = parsePositiveNumber(proposal.take_profit);
    const leverage = parsePositiveNumber(proposal.leverage);

    setTradeForm((prev) => ({
      ...prev,
      symbol: normalizeString(proposal.symbol) || prev.symbol,
      action: proposedAction || prev.action || 'buy',
      amount: amount ?? prev.amount,
      orderType: proposedOrderType || prev.orderType || 'market',
      price: price ?? prev.price,
      stopLoss: stopLoss ?? prev.stopLoss,
      takeProfit: takeProfit ?? prev.takeProfit,
      leverage: leverage ?? prev.leverage
    }));

    toast({
      title: 'Recommendation Applied',
      description: 'The AI recommendation has been applied to the trade form.',
      variant: 'default'
    });
  }, [aiSummary, toast]);

  const handleStrategyExecution = useCallback(
    async (strategyId: string) => {
      try {
        pushWorkflowLog('info', `Executing strategy ${strategyId}.`);
        const result = await strategyActions.executeStrategy({
          function: strategyId,
          symbol: tradeForm.symbol,
          parameters: {
            timeframe: workflowConfig.timeframe,
            confidence: workflowConfig.confidence,
            include_risk_metrics: workflowConfig.includeRiskMetrics
          },
          simulation_mode: false
        });
        recordInsight('Strategy Execution', strategyId, result);
        pushWorkflowLog('success', `${strategyId} executed successfully.`);
        creditActions.fetchBalance();
      } catch (error: any) {
        console.error('Strategy execution failed', error);
        pushWorkflowLog('error', error?.response?.data?.detail || error?.message || 'Strategy execution failed.');
      }
    },
    [strategyActions, tradeForm.symbol, workflowConfig, recordInsight, pushWorkflowLog, creditActions]
  );

  // Opportunities Drawer Handlers
  const handleExecuteOpportunity = useCallback(
    async (opportunityId: string, positionSize: number) => {
      try {
        // Add to executing set
        setOpportunitiesDrawer(prev => ({
          ...prev,
          executing: new Set([...prev.executing, opportunityId])
        }));

        // Find the opportunity
        const opportunity = [
          ...(opportunitiesDrawer.data?.validated || []),
          ...(opportunitiesDrawer.data?.nonValidated || [])
        ].find(opp => opp.id === opportunityId);

        if (!opportunity) {
          throw new Error('Opportunity not found');
        }

        pushWorkflowLog('info', `Executing trade for ${opportunity.symbol}...`);

        // Execute the trade
        const response = await apiClient.post('/trading/execute', {
          symbol: opportunity.symbol,
          action: opportunity.side,
          amount: positionSize,
          order_type: 'market',
          price: opportunity.entry_price,
          stop_loss: opportunity.stop_loss,
          take_profit: opportunity.take_profit,
          leverage: 1,
          strategy_type: opportunity.strategy,
          source: 'ai_opportunity'
        });

        pushWorkflowLog('success', `Trade executed: ${opportunity.side.toUpperCase()} ${opportunity.symbol}`);

        toast({
          title: 'Trade Executed',
          description: `${opportunity.side.toUpperCase()} ${formatCurrency(positionSize)} of ${opportunity.symbol}`,
          variant: 'default'
        });

        // Refresh data
        creditActions.fetchBalance();
        fetchPortfolio();
        fetchRecentTrades();

        // Remove from executing set
        setOpportunitiesDrawer(prev => {
          const newExecuting = new Set(prev.executing);
          newExecuting.delete(opportunityId);
          return { ...prev, executing: newExecuting };
        });
      } catch (error: any) {
        console.error('Trade execution failed', error);
        pushWorkflowLog('error', error?.response?.data?.detail || error?.message || 'Trade execution failed.');
        toast({
          title: 'Trade Execution Failed',
          description: error?.response?.data?.detail || error?.message || 'Unable to execute trade.',
          variant: 'destructive'
        });

        // Remove from executing set
        setOpportunitiesDrawer(prev => {
          const newExecuting = new Set(prev.executing);
          newExecuting.delete(opportunityId);
          return { ...prev, executing: newExecuting };
        });
      }
    },
    [opportunitiesDrawer.data, pushWorkflowLog, toast, creditActions, fetchPortfolio, fetchRecentTrades]
  );

  const handleBatchExecuteOpportunities = useCallback(
    async (opportunityIds: string[]) => {
      try {
        // Add all to executing set
        setOpportunitiesDrawer(prev => ({
          ...prev,
          executing: new Set([...prev.executing, ...opportunityIds])
        }));

        pushWorkflowLog('info', `Executing batch of ${opportunityIds.length} trades...`);

        // Execute all trades in parallel
        const results = await Promise.allSettled(
          opportunityIds.map(async (id) => {
            const opportunity = [
              ...(opportunitiesDrawer.data?.validated || []),
            ].find(opp => opp.id === id);

            if (!opportunity) {
              throw new Error(`Opportunity ${id} not found`);
            }

            return apiClient.post('/trading/execute', {
              symbol: opportunity.symbol,
              action: opportunity.side,
              amount: opportunity.suggested_position_size,
              order_type: 'market',
              price: opportunity.entry_price,
              stop_loss: opportunity.stop_loss,
              take_profit: opportunity.take_profit,
              leverage: 1,
              strategy_type: opportunity.strategy,
              source: 'ai_opportunity_batch'
            });
          })
        );

        // Count successes
        const successCount = results.filter(r => r.status === 'fulfilled').length;
        const failCount = results.length - successCount;

        pushWorkflowLog('success', `Batch execution complete: ${successCount} successful, ${failCount} failed`);

        toast({
          title: 'Batch Execution Complete',
          description: `${successCount} trades executed successfully${failCount > 0 ? `, ${failCount} failed` : ''}`,
          variant: successCount > 0 ? 'default' : 'destructive'
        });

        // Refresh data
        creditActions.fetchBalance();
        fetchPortfolio();
        fetchRecentTrades();

        // Clear executing set
        setOpportunitiesDrawer(prev => ({
          ...prev,
          executing: new Set()
        }));
      } catch (error: any) {
        console.error('Batch execution failed', error);
        pushWorkflowLog('error', error?.message || 'Batch execution failed.');
        toast({
          title: 'Batch Execution Failed',
          description: error?.message || 'Unable to execute batch trades.',
          variant: 'destructive'
        });

        // Clear executing set
        setOpportunitiesDrawer(prev => ({
          ...prev,
          executing: new Set()
        }));
      }
    },
    [opportunitiesDrawer.data, pushWorkflowLog, toast, creditActions, fetchPortfolio, fetchRecentTrades]
  );

  const handleValidateOpportunity = useCallback(
    async (opportunityId: string) => {
      try {
        // Add to validating set
        setOpportunitiesDrawer(prev => ({
          ...prev,
          validating: new Set([...prev.validating, opportunityId])
        }));

        // Find the opportunity
        const opportunity = opportunitiesDrawer.data?.nonValidated.find(opp => opp.id === opportunityId);

        if (!opportunity) {
          throw new Error('Opportunity not found');
        }

        pushWorkflowLog('info', `Validating ${opportunity.symbol} with AI consensus...`);

        // Validate the trade - calculate percentages based on side
        const stopLossPercent = opportunity.side === 'buy'
          ? ((opportunity.entry_price - opportunity.stop_loss) / opportunity.entry_price) * 100
          : ((opportunity.stop_loss - opportunity.entry_price) / opportunity.entry_price) * 100;

        const takeProfitPercent = opportunity.side === 'buy'
          ? ((opportunity.take_profit - opportunity.entry_price) / opportunity.entry_price) * 100
          : ((opportunity.entry_price - opportunity.take_profit) / opportunity.entry_price) * 100;

        const result = await validateTrade({
          trade_data: {
            symbol: opportunity.symbol,
            action: opportunity.side,
            amount: opportunity.suggested_position_size,
            order_type: 'market',
            stop_loss: stopLossPercent,
            take_profit: takeProfitPercent,
            leverage: 1,
            strategy: opportunity.strategy
          },
          confidence_threshold: workflowConfig.confidence,
          ai_models: workflowConfig.aiModels,
          execution_urgency: 'normal'
        });

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
              },
              validationReason: undefined
            };

            return {
              ...prev,
              data: {
                ...prev.data,
                validated: [...prev.data.validated, updatedOpportunity],
                nonValidated: prev.data.nonValidated.filter(opp => opp.id !== opportunityId),
                validatedCount: prev.data.validatedCount + 1
              },
              validating: new Set([...prev.validating].filter(id => id !== opportunityId))
            };
          });

          pushWorkflowLog('success', `${opportunity.symbol} validated successfully!`);
          toast({
            title: 'Opportunity Validated',
            description: `${opportunity.symbol} passed AI consensus validation`,
            variant: 'default'
          });
        } else {
          pushWorkflowLog('warning', `${opportunity.symbol} did not pass validation`);
          toast({
            title: 'Validation Failed',
            description: result.reason || 'Did not meet consensus threshold',
            variant: 'destructive'
          });

          // Remove from validating set
          setOpportunitiesDrawer(prev => {
            const newValidating = new Set(prev.validating);
            newValidating.delete(opportunityId);
            return { ...prev, validating: newValidating };
          });
        }

        creditActions.fetchBalance();
      } catch (error: any) {
        console.error('Validation failed', error);
        pushWorkflowLog('error', error?.message || 'Validation failed.');
        toast({
          title: 'Validation Error',
          description: error?.message || 'Unable to validate opportunity.',
          variant: 'destructive'
        });

        // Remove from validating set
        setOpportunitiesDrawer(prev => {
          const newValidating = new Set(prev.validating);
          newValidating.delete(opportunityId);
          return { ...prev, validating: newValidating };
        });
      }
    },
    [opportunitiesDrawer.data, validateTrade, workflowConfig, pushWorkflowLog, toast, creditActions]
  );

  const handleApplyOpportunityToForm = useCallback(
    (opportunity: Opportunity) => {
      // Calculate percentages based on side
      const stopLossPercent = opportunity.side === 'buy'
        ? ((opportunity.entry_price - opportunity.stop_loss) / opportunity.entry_price) * 100
        : ((opportunity.stop_loss - opportunity.entry_price) / opportunity.entry_price) * 100;

      const takeProfitPercent = opportunity.side === 'buy'
        ? ((opportunity.take_profit - opportunity.entry_price) / opportunity.entry_price) * 100
        : ((opportunity.entry_price - opportunity.take_profit) / opportunity.entry_price) * 100;

      setTradeForm({
        symbol: opportunity.symbol,
        action: opportunity.side,
        amount: opportunity.suggested_position_size,
        orderType: 'market',
        price: opportunity.entry_price,
        stopLoss: stopLossPercent,
        takeProfit: takeProfitPercent,
        leverage: 1
      });

      // Switch to Execute Trade tab
      setActiveTab('trade');

      toast({
        title: 'Applied to Form',
        description: `${opportunity.symbol} parameters loaded into trade form`,
        variant: 'default'
      });
    },
    [toast]
  );

  // Fetch pricing configuration from backend
  useEffect(() => {
    const fetchPricing = async () => {
      try {
        const response = await apiClient.get('/ai/pricing');
        setPricingConfig({
          opportunity_scan_cost: response.data.opportunity_scan_cost || 1,
          validation_cost: response.data.validation_cost || 2,
          execution_cost: response.data.execution_cost || 2,
          per_call_estimate: response.data.per_call_estimate || 0.05
        });
        setPricingError(null);
      } catch (error: any) {
        console.error('Failed to fetch pricing config, using defaults', error);
        // Use default pricing config as fallback
        setPricingConfig({
          opportunity_scan_cost: 1,
          validation_cost: 2,
          execution_cost: 2,
          per_call_estimate: 0.05
        });
        // Don't show error to user for missing pricing endpoint, just use defaults
        setPricingError(null);
      }
    };

    fetchPricing();
  }, []);

  useEffect(() => {
    setCurrentMode(ChatMode.TRADING);
    if (!sessionId) {
      initializeSession();
    }
  }, [sessionId, initializeSession, setCurrentMode]);

  useEffect(() => {
    fetchPortfolio();
    fetchStatus();
    fetchMarketData();
    fetchRecentTrades();
    connectWebSocket();

    return () => {
      streamingControllerRef.current?.abort();
    };
  }, [fetchPortfolio, fetchStatus, fetchMarketData, fetchRecentTrades, connectWebSocket]);

  const workflowDisabled = isStreaming || isAnalyzing;
  const isConnectionOpen = connectionStatus?.toLowerCase() === 'open';

  useEffect(() => {
    if (!connectionStatus) {
      return;
    }

    const normalizedStatus = connectionStatus.toLowerCase();
    const message = isConnectionOpen
      ? 'AI consensus channel connected.'
      : `AI consensus connection ${normalizedStatus}.`;

    pushWorkflowLog('info', message);
  }, [connectionStatus, isConnectionOpen, pushWorkflowLog]);

  useEffect(() => {
    if (isStreaming && activeTab !== 'workflow') {
      setActiveTab('workflow');
    }
  }, [isStreaming, activeTab]);

  // Update latestConsensusData when AI summary completes
  useEffect(() => {
    if (aiSummary?.aiAnalysis) {
      const analysis = aiSummary.aiAnalysis;

      // Try to extract consensus data from the AI analysis
      if (analysis.consensus_score !== undefined && analysis.recommendation) {
        setLatestConsensusData({
          consensus_score: analysis.consensus_score || 0,
          recommendation: analysis.recommendation || 'HOLD',
          confidence_threshold_met: analysis.confidence_threshold_met || false,
          model_responses: analysis.model_responses || [],
          cost_summary: analysis.cost_summary,
          reasoning: analysis.reasoning || aiSummary.content,
          timestamp: new Date().toISOString()
        });
      }
    }
  }, [aiSummary]);

  // Update marketContext when market data updates
  useEffect(() => {
    if (marketData && marketData.length > 0) {
      // Derive market context from marketData
      const symbols = marketData.map(item => item.symbol);
      const avgChange = marketData.reduce((sum, item) => sum + (item.change || 0), 0) / marketData.length;

      // Determine trend based on average change
      let trend: 'bullish' | 'bearish' | 'neutral' = 'neutral';
      if (avgChange > 2) trend = 'bullish';
      else if (avgChange < -2) trend = 'bearish';

      // Determine sentiment (simplified)
      let sentiment: 'positive' | 'negative' | 'neutral' = 'neutral';
      if (avgChange > 1) sentiment = 'positive';
      else if (avgChange < -1) sentiment = 'negative';

      setMarketContext({
        symbols,
        trend,
        sentiment,
        avgChange,
        topGainers: marketData
          .filter(item => (item.change || 0) > 0)
          .sort((a, b) => (b.change || 0) - (a.change || 0))
          .slice(0, 3),
        topLosers: marketData
          .filter(item => (item.change || 0) < 0)
          .sort((a, b) => (a.change || 0) - (b.change || 0))
          .slice(0, 3)
      });
    }
  }, [marketData]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      {/* Pricing Error Alert */}
      {pricingError && (
        <Card className="border-red-500/50 bg-red-500/10">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-500">Pricing Configuration Error</h3>
                <p className="text-sm text-muted-foreground mt-1">{pricingError}</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.location.reload()}
                  className="mt-3"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh Page
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Manual Trading Control Center</h1>
          <p className="text-muted-foreground">
            Execute trades, rebalancing, and AI-driven actions with full transparency into every phase.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className="gap-1">
            <Radio className="h-3 w-3" />
            {isConnectionOpen ? 'AI live' : 'AI idle'}
          </Badge>
          <Badge variant="outline" className="gap-1">
            <ListTree className="h-3 w-3" />
            {aggregatedStats.connectedCount} Exchanges
          </Badge>
          <Badge variant="outline" className="gap-1">
            <DollarSign className="h-3 w-3" />
            {formatCurrency(availableBalance)} Available
          </Badge>
          <Badge variant="secondary" className="gap-1">
            <Zap className="h-3 w-3" />
            {creditsLoading ? 'Loading credits…' : `${balance.available_credits} credits`}
          </Badge>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trade">Execute Trade</TabsTrigger>
          <TabsTrigger value="workflow">AI Workflow</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="risk">Live Intelligence</TabsTrigger>
        </TabsList>

        <TabsContent value="trade" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Manual Trade Execution
                </CardTitle>
                <CardDescription>
                  Execute trades directly with optional AI-generated parameters and risk controls.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Trading Pair</Label>
                    {availableSymbols.length ? (
                      <Select
                        value={tradeForm.symbol}
                        onValueChange={(value) => setTradeForm((prev) => ({ ...prev, symbol: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select trading pair" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableSymbols.map((symbol) => (
                            <SelectItem key={symbol} value={symbol}>
                              {symbol}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={tradeForm.symbol}
                        onChange={(event) => setTradeForm((prev) => ({ ...prev, symbol: event.target.value }))}
                        placeholder="Enter symbol (e.g. BTC/USDT)"
                      />
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Action</Label>
                    <Select
                      value={tradeForm.action}
                      onValueChange={(value) => setTradeForm((prev) => ({ ...prev, action: value as 'buy' | 'sell' }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="buy">Buy / Long</SelectItem>
                        <SelectItem value="sell">Sell / Short</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Order Type</Label>
                    <Select
                      value={tradeForm.orderType}
                      onValueChange={(value) => setTradeForm((prev) => ({ ...prev, orderType: value as ManualTradeRequest['orderType'] }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="market">Market</SelectItem>
                        <SelectItem value="limit">Limit</SelectItem>
                        <SelectItem value="stop">Stop</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Exchange Routing</Label>
                    <Select
                      value={tradeForm.exchange}
                      onValueChange={(value) => setTradeForm((prev) => ({ ...prev, exchange: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto-select best venue</SelectItem>
                        {exchanges
                          .filter((exchange) => exchange.is_active)
                          .map((exchange) => (
                            <SelectItem key={exchange.id} value={exchange.exchange}>
                              {exchange.nickname || exchange.exchange.toUpperCase()}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Amount (USD)</Label>
                    <Input
                      type="number"
                      value={tradeForm.amount}
                      onChange={(event) =>
                        setTradeForm((prev) => ({ ...prev, amount: Number(event.target.value) || 0 }))
                      }
                      placeholder="Enter notional amount"
                    />
                  </div>

                  {tradeForm.orderType !== 'market' && (
                    <div className="space-y-2">
                      <Label>Limit / Stop Price</Label>
                      <Input
                        type="number"
                        value={tradeForm.price ?? ''}
                        onChange={(event) =>
                          setTradeForm((prev) => ({
                            ...prev,
                            price: event.target.value ? Number(event.target.value) : undefined
                          }))
                        }
                        placeholder="Enter price"
                      />
                    </div>
                  )}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Stop Loss (%)</Label>
                    <Input
                      type="number"
                      value={tradeForm.stopLoss ?? ''}
                      onChange={(event) =>
                        setTradeForm((prev) => ({
                          ...prev,
                          stopLoss: event.target.value ? Number(event.target.value) : undefined
                        }))
                      }
                      placeholder="Optional stop loss"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Take Profit (%)</Label>
                    <Input
                      type="number"
                      value={tradeForm.takeProfit ?? ''}
                      onChange={(event) =>
                        setTradeForm((prev) => ({
                          ...prev,
                          takeProfit: event.target.value ? Number(event.target.value) : undefined
                        }))
                      }
                      placeholder="Optional take profit"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Sparkles className="h-4 w-4" />
                    {aiSummary?.confidence
                      ? `Latest AI confidence: ${aiSummary.confidence.toFixed(1)}%`
                      : 'Run an AI workflow to generate guidance.'}
                  </div>
                  <div className="flex items-center gap-3">
                    <Button variant="outline" onClick={applyAiRecommendationToTrade} disabled={!aiSummary?.actionData}>
                      <Settings className="mr-2 h-4 w-4" />
                      Apply AI Parameters
                    </Button>
                    <Button onClick={handleTradeSubmit} className="bg-green-600 hover:bg-green-700">
                      <Play className="mr-2 h-4 w-4" />
                      Execute {tradeForm.action.toUpperCase()}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-6">
              {/* AI Consensus Card */}
              {latestConsensusData && (
                <AIConsensusCard
                  consensusData={latestConsensusData}
                  compact
                  onApplyRecommendation={applyAiRecommendationToTrade}
                />
              )}

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BarChart3 className="h-4 w-4" />
                    Portfolio Snapshot
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Total Value</span>
                    <span className="font-semibold">{formatCurrency(totalValue)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Available Balance</span>
                    <span className="font-semibold">{formatCurrency(availableBalance)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Daily P&amp;L</span>
                    <span className={dailyPnL >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                      {formatCurrency(dailyPnL)} ({formatPercentage(dailyPnLPercent)})
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Total P&amp;L</span>
                    <span className={totalPnL >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                      {formatCurrency(totalPnL)} ({formatPercentage(totalPnLPercent)})
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Market Context Card - TODO: Create adapter for MarketContext type */}
              {/* {marketContext && (
                <MarketContextCard
                  marketData={marketContext}
                  compact
                />
              )} */}

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Activity className="h-4 w-4" />
                    Recent Trades
                  </CardTitle>
                  <CardDescription>Live feed from all connected exchanges.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-48 pr-2">
                    <div className="space-y-3 text-sm">
                      {recentTrades.length === 0 ? (
                        <p className="text-muted-foreground">No recent trades recorded.</p>
                      ) : (
                        recentTrades.map((trade) => (
                          <div key={trade.id} className="rounded-md border p-3">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold">{trade.symbol}</span>
                              <Badge variant="outline" className="gap-1">
                                {trade.side === 'buy' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                {trade.side.toUpperCase()}
                              </Badge>
                            </div>
                            <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                              <span>{new Date(trade.time).toLocaleString()}</span>
                              <span>{formatCurrency(trade.price)}</span>
                            </div>
                            <div className="mt-2 flex items-center justify-between text-xs">
                              <span>Amount: {trade.amount}</span>
                              <span className={trade.pnl >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                                P&amp;L: {formatCurrency(trade.pnl)}
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="workflow" className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Live AI Workflow
                </CardTitle>
                <CardDescription>
                  Mirror the chat-based AI process with step-by-step transparency and actionable results.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Workflow Type</Label>
                    <Select
                      value={workflowConfig.type}
                      onValueChange={(value) => setWorkflowConfig((prev) => ({ ...prev, type: value as ManualWorkflowType }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="trade_validation">Trade Validation</SelectItem>
                        <SelectItem value="portfolio_rebalance">Portfolio Rebalancing</SelectItem>
                        <SelectItem value="opportunity_scan">Opportunity Scan</SelectItem>
                        <SelectItem value="market_analysis">Market Analysis</SelectItem>
                        <SelectItem value="portfolio_review">Portfolio Review</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Preferred Strategy</Label>
                    <Select
                      value={workflowConfig.strategyId}
                      onValueChange={(value) => setWorkflowConfig((prev) => ({ ...prev, strategyId: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select strategy" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="manual">Manual Parameters</SelectItem>
                        {Object.entries(availableStrategies).map(([key, strategy]) => (
                          <SelectItem key={key} value={key}>
                            {strategy.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedStrategy && (
                      <p className="text-xs text-muted-foreground">
                        {selectedStrategy.description}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Timeframe</Label>
                    <Input
                      value={workflowConfig.timeframe}
                      onChange={(event) => setWorkflowConfig((prev) => ({ ...prev, timeframe: event.target.value }))}
                      placeholder="e.g. 1h, 4h, 1d"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Target Confidence (%)</Label>
                    <Slider
                      value={[workflowConfig.confidence]}
                      min={55}
                      max={95}
                      step={1}
                      onValueChange={([value]) => setWorkflowConfig((prev) => ({ ...prev, confidence: value }))}
                    />
                    <div className="text-xs text-muted-foreground">{workflowConfig.confidence}% consensus target</div>
                  </div>

                  <div className="space-y-2">
                    <Label>Symbols to Monitor</Label>
                    <Input
                      value={workflowConfig.targetSymbolsText}
                      onChange={(event) => setWorkflowConfig((prev) => ({ ...prev, targetSymbolsText: event.target.value }))}
                      placeholder="Comma separated list (e.g. BTC/USDT,ETH/USDT)"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Rebalance Threshold (%)</Label>
                    <Input
                      type="number"
                      value={workflowConfig.rebalanceThreshold}
                      onChange={(event) =>
                        setWorkflowConfig((prev) => ({ ...prev, rebalanceThreshold: Number(event.target.value) || 0 }))
                      }
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-4 rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>AI Model Strategy</Label>
                      <p className="text-xs text-muted-foreground">Select the weighting of GPT-4, Claude, and Gemini.</p>
                    </div>
                    <Select
                      value={workflowConfig.aiModels}
                      onValueChange={(value) => setWorkflowConfig((prev) => ({ ...prev, aiModels: value }))}
                    >
                      <SelectTrigger className="w-[200px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Balanced (all models)</SelectItem>
                        <SelectItem value="gpt4_claude">GPT-4 + Claude</SelectItem>
                        <SelectItem value="cost_optimized">Cost Optimized</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between rounded-md border p-3">
                    <div>
                      <Label className="flex items-center gap-2 text-sm">
                        <Shield className="h-4 w-4" /> Include risk metrics
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Stress tests, drawdown analysis, and liquidity checks during the workflow.
                      </p>
                    </div>
                    <Switch
                      checked={workflowConfig.includeRiskMetrics}
                      onCheckedChange={(checked) => setWorkflowConfig((prev) => ({ ...prev, includeRiskMetrics: checked }))}
                    />
                  </div>
                  <Textarea
                    value={workflowConfig.customNotes}
                    onChange={(event) => setWorkflowConfig((prev) => ({ ...prev, customNotes: event.target.value }))}
                    placeholder="Optional notes or constraints for the AI (e.g. prefer exchanges with deep liquidity)."
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-muted-foreground">
                    Credits are automatically deducted per workflow step. Available: {balance.available_credits}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button variant="outline" onClick={() => handleConsensusAction('opportunity')} disabled={workflowDisabled}>
                      <Target className="mr-2 h-4 w-4" />
                      Scan Opportunities
                    </Button>
                    <Button variant="outline" onClick={() => handleConsensusAction('validation')} disabled={workflowDisabled}>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      Validate Trade
                    </Button>
                    <Button variant="outline" onClick={() => handleConsensusAction('risk')} disabled={workflowDisabled}>
                      <Shield className="mr-2 h-4 w-4" />
                      Assess Risk
                    </Button>
                    <Button variant="outline" onClick={() => handleConsensusAction('decision')} disabled={workflowDisabled}>
                      <Equal className="mr-2 h-4 w-4" />
                      Final Consensus
                    </Button>
                    <Button onClick={runLiveWorkflow} disabled={workflowDisabled}>
                      {isStreaming ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Streaming...
                        </>
                      ) : (
                        <>
                          <Brain className="mr-2 h-4 w-4" />
                          Run Live Workflow
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-6">
              <PhaseProgressVisualizer currentPhase={currentPhase} phaseHistory={phaseHistory} isCompact />

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Activity className="h-4 w-4" />
                    Workflow Stream
                  </CardTitle>
                  <CardDescription>Live commentary from the AI as phases progress.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-48 pr-2 text-sm">
                    {streamingContent ? (
                      <pre className="whitespace-pre-wrap text-muted-foreground">{streamingContent}</pre>
                    ) : (
                      <p className="text-muted-foreground">Start a workflow to stream analysis in real time.</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <LineChart className="h-4 w-4" />
                    AI Workflow Logs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-48 pr-2 text-sm">
                    <div className="space-y-2">
                      {workflowLogs.length === 0 ? (
                        <p className="text-muted-foreground">No workflow logs yet.</p>
                      ) : (
                        workflowLogs
                          .slice()
                          .reverse()
                          .map((log) => (
                            <div key={log.id} className="rounded-md border p-2">
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>{log.time}</span>
                                <span className="capitalize">{log.level}</span>
                              </div>
                              <p className="text-sm">{log.message}</p>
                            </div>
                          ))
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </div>

          {aiSummary && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Brain className="h-4 w-4" />
                  AI Recommendation Summary
                </CardTitle>
                <CardDescription>Final consensus from the AI workflow with actionable context.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                  {aiSummary.confidence && (
                    <Badge variant="outline">Confidence {aiSummary.confidence.toFixed(1)}%</Badge>
                  )}
                  {aiSummary.intent && <Badge variant="outline">Intent {aiSummary.intent}</Badge>}
                  {aiSummary.requiresApproval && <Badge variant="outline">Requires Approval</Badge>}
                </div>

                <ScrollArea className="h-40 rounded-md border p-4 text-sm">
                  <pre className="whitespace-pre-wrap text-muted-foreground">{aiSummary.content}</pre>
                </ScrollArea>

                {aiSummary.actionData && (
                  <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                    <h4 className="mb-2 font-semibold">Suggested Action</h4>
                    <div className="grid gap-2 md:grid-cols-2">
                      {Object.entries(aiSummary.actionData).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-muted-foreground">{key.replace(/_/g, ' ')}</span>
                          <span className="font-medium">{typeof value === 'number' ? value.toString() : String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-3">
                  <Button variant="outline" onClick={applyAiRecommendationToTrade}>
                    <Settings className="mr-2 h-4 w-4" />
                    Apply to Trade Form
                  </Button>
                  <Button onClick={() => handleConsensusAction('decision')}>
                    <Brain className="mr-2 h-4 w-4" />
                    Refresh Consensus
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {aiInsights.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-4 w-4" />
                  AI Insights Feed
                </CardTitle>
                <CardDescription>Recent consensus calls and data pulls driven by manual requests.</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-64 pr-2">
                  <div className="space-y-3 text-sm">
                    {aiInsights.map((insight) => (
                      <div key={insight.id} className="rounded-md border p-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{new Date(insight.timestamp).toLocaleTimeString()}</span>
                          <Badge variant="outline">{insight.function}</Badge>
                        </div>
                        <h4 className="mt-1 font-semibold">{insight.title}</h4>
                        <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-muted-foreground">
                          {JSON.stringify(insight.payload, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="strategies" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Strategy Controls
              </CardTitle>
              <CardDescription>
                Execute any available strategy — including your unlocked premium strategies — directly from the manual dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Object.entries(availableStrategies).map(([key, strategy]) => (
                  <Card key={key} className="flex flex-col justify-between">
                    <CardHeader>
                      <CardTitle className="text-lg">{strategy.name}</CardTitle>
                      <CardDescription className="capitalize">{strategy.category}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      <p className="text-muted-foreground">{strategy.description}</p>
                      <div className="flex items-center justify-between">
                        <span>Risk Level</span>
                        <Badge variant="outline">{strategy.risk_level}</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Minimum Capital</span>
                        <span className="font-medium">{formatCurrency(strategy.min_capital)}</span>
                      </div>
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => handleStrategyExecution(key)}
                        disabled={strategyExecuting}
                      >
                        <Play className="mr-2 h-3 w-3" />
                        Execute Strategy
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4" />
                Active Strategy Performance
              </CardTitle>
              <CardDescription>Metrics pulled live from the backend for each configured strategy.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {strategies.length === 0 ? (
                  <p className="text-muted-foreground text-sm">
                    No strategies configured yet. Use the marketplace or IDE to add strategies.
                  </p>
                ) : (
                  strategies.map((strategy) => (
                    <Card key={strategy.strategy_id} className="border-dashed">
                      <CardHeader>
                        <CardTitle className="text-lg">{strategy.name}</CardTitle>
                        <CardDescription>{strategy.status}</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span>Total Trades</span>
                          <span className="font-medium">{strategy.total_trades}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Win Rate</span>
                          <span className="font-medium">{formatPercentage(strategy.win_rate)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Total P&amp;L</span>
                          <span className={strategy.total_pnl >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                            {formatCurrency(Number(strategy.total_pnl))}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Last executed: {strategy.last_executed_at ? new Date(strategy.last_executed_at).toLocaleString() : '—'}
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="risk" className="space-y-6">
          {/* AI Usage Stats - Full width */}
          <AIUsageStats
            usageData={{
              remainingCredits: balance.available_credits || 0,
              totalCredits: balance.total_purchased_credits || 0,
              todayCalls: balance.total_used_credits || 0,
              todayCost: (balance.total_used_credits || 0) * (pricingConfig?.per_call_estimate || 0.05),
              profitGenerated: dailyPnL > 0 ? dailyPnL : 0,
              roi: dailyPnL > 0 && balance.total_used_credits > 0 ? dailyPnL / ((balance.total_used_credits || 1) * (pricingConfig?.per_call_estimate || 0.05)) : 0,
              callBreakdown: (() => {
                // Aggregate aiInsights by function/type
                if (!aiInsights || aiInsights.length === 0) {
                  return undefined;
                }

                const grouped = aiInsights.reduce((acc, insight) => {
                  const type = insight.function || 'unknown';
                  if (!acc[type]) {
                    acc[type] = { count: 0, totalCost: 0, successCount: 0 };
                  }
                  acc[type].count++;

                  // Extract cost from payload if available, otherwise use pricing config
                  const insightCost = insight.payload?.price
                    ?? insight.payload?.cost
                    ?? pricingConfig?.per_call_estimate
                    ?? 0.05;
                  acc[type].totalCost += insightCost;

                  // Check explicit success field (payload.success, payload.status === 'ok', status === 'completed')
                  const isSuccess =
                    insight.payload?.success === true ||
                    insight.payload?.status === 'ok' ||
                    insight.payload?.status === 'completed' ||
                    (insight as any).status === 'completed';

                  if (isSuccess) {
                    acc[type].successCount++;
                  }
                  return acc;
                }, {} as Record<string, { count: number; totalCost: number; successCount: number }>);

                return Object.entries(grouped).map(([type, data]) => ({
                  type,
                  count: data.count,
                  totalCost: data.totalCost,
                  successRate: data.count > 0 ? (data.successCount / data.count) * 100 : 0
                }));
              })()
            }}
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Portfolio &amp; Risk Metrics
                </CardTitle>
                <CardDescription>Live portfolio composition with AI-monitored balances.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Positions Tracked</span>
                    <Badge variant="outline">{positions.length}</Badge>
                  </div>
                  <Separator className="my-3" />
                  <ScrollArea className="h-48 pr-2">
                    {positions.length === 0 ? (
                      <p className="text-muted-foreground">No open positions detected.</p>
                    ) : (
                      <div className="space-y-3">
                        {positions.map((position) => (
                          <div key={position.symbol} className="rounded-md border p-3 text-sm">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold">{position.symbol}</span>
                              <Badge variant="outline">{position.side.toUpperCase()}</Badge>
                            </div>
                            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                              <span>Amount: {position.amount}</span>
                              <span>Value: {formatCurrency(position.value)}</span>
                            </div>
                            <div className="mt-1 flex items-center justify-between text-xs">
                              <span>Unrealized P&amp;L</span>
                              <span className={position.unrealizedPnL >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                                {formatCurrency(position.unrealizedPnL)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  AI System Health
                </CardTitle>
                <CardDescription>Model status, cost usage, and consensus telemetry in real time.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="rounded-md border p-3">
                  <h4 className="font-semibold mb-2">Model Status</h4>
                  <div className="grid gap-2">
                    {aiStatus?.ai_models_status
                      ? Object.entries(aiStatus.ai_models_status).map(([model, status]) => (
                          <div key={model} className="flex items-center justify-between">
                            <span>{model}</span>
                            <Badge variant="outline">{String(status)}</Badge>
                          </div>
                        ))
                      : <p className="text-muted-foreground">Model telemetry not available.</p>}
                  </div>
                </div>
                <div className="rounded-md border p-3">
                  <h4 className="font-semibold mb-2">Consensus Stream</h4>
                  <ScrollArea className="h-32 pr-2">
                    <div className="space-y-2">
                      {consensusHistory.length === 0 ? (
                        <p className="text-muted-foreground text-xs">No consensus events yet.</p>
                      ) : (
                        consensusHistory.slice(-20).reverse().map((item, index) => (
                          <div key={`${item.timestamp}-${index}`} className="flex items-center justify-between text-xs">
                            <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                            <span>{item.recommendation} @ {item.consensus}%</span>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4" />
                Market Data Stream
              </CardTitle>
              <CardDescription>Real-time pricing feed from the trading websocket.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-64 pr-2">
                <div className="grid gap-2 text-sm md:grid-cols-2 xl:grid-cols-3">
                  {marketData.length === 0 ? (
                    <p className="text-muted-foreground">Market data will appear as soon as subscriptions update.</p>
                  ) : (
                    marketData.map((item) => (
                      <div key={item.symbol} className="rounded-md border p-3">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{item.symbol}</span>
                          <span className={item.change >= 0 ? 'text-green-500 font-semibold' : 'text-red-500 font-semibold'}>
                            {formatPercentage(item.change)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                          <span>Price</span>
                          <span>{formatCurrency(item.price)}</span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                          <span>Volume</span>
                          <span>{item.volume}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Opportunities Drawer */}
      <OpportunitiesDrawer
        state={opportunitiesDrawer}
        onClose={() => setOpportunitiesDrawer(prev => ({ ...prev, open: false }))}
        onExecuteTrade={handleExecuteOpportunity}
        onExecuteBatch={handleBatchExecuteOpportunities}
        onValidateOpportunity={handleValidateOpportunity}
        onApplyToForm={handleApplyOpportunityToForm}
        availableCredits={balance.available_credits || 0}
        portfolioValue={totalValue}
      />
    </motion.div>
  );
};

export default ManualTradingPage;
