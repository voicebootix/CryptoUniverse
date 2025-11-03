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
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/components/ui/use-toast';
import { useUser } from '@/store/authStore';
import { UserRole } from '@/types/auth';
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
import {
  opportunityApi,
  OpportunityDiscoveryResponse,
  OpportunityApiError,
  type Opportunity as DiscoveryOpportunity,
} from '@/lib/api/opportunityApi';
import { AIConsensusCard } from '@/components/trading/AIConsensusCard';
import { MarketContextCard } from '@/components/trading/MarketContextCard';
import { AIUsageStats } from '@/components/trading/AIUsageStats';
import { QuickActionBar } from '@/components/trading/QuickActionBar';
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

type OpportunityScanFilterState = {
  symbols: string[];
  assetTiers: string[];
  strategyIds: string[];
};

const ASSET_TIER_OPTIONS = [
  {
    value: 'tier_institutional',
    label: 'Institutional',
    description: '$100M+ daily volume',
  },
  {
    value: 'tier_enterprise',
    label: 'Enterprise',
    description: '$50M+ daily volume',
  },
  {
    value: 'tier_professional',
    label: 'Professional',
    description: '$10M+ daily volume',
  },
  {
    value: 'tier_retail',
    label: 'Retail',
    description: '$1M+ daily volume',
  },
  {
    value: 'tier_emerging',
    label: 'Emerging',
    description: '$100K+ daily volume',
  },
  {
    value: 'tier_micro',
    label: 'Micro',
    description: '$10K+ daily volume',
  },
];

const ManualTradingPage: React.FC = () => {
  const user = useUser();
  const { toast } = useToast();

  // Access control: Only TRADER and ADMIN roles can access Manual Trading
  if (!user || (user.role !== UserRole.TRADER && user.role !== UserRole.ADMIN)) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900/20">
              <Shield className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <CardTitle className="text-xl">Access Restricted</CardTitle>
            <CardDescription>
              Manual Trading is only available for traders and administrators.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center text-sm text-muted-foreground">
              <p>Your current role: <Badge variant="outline">{user?.role || 'Unknown'}</Badge></p>
              <p className="mt-2">Please contact an administrator to upgrade your account if you need access to trading features.</p>
            </div>
            <Button 
              onClick={() => window.history.back()} 
              className="w-full"
              variant="outline"
            >
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
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
  const [scanDialogOpen, setScanDialogOpen] = useState(false);
  const [scanFilters, setScanFilters] = useState<OpportunityScanFilterState>({
    symbols: [],
    assetTiers: [],
    strategyIds: [],
  });
  const [scanSymbolInput, setScanSymbolInput] = useState('');

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
  const suggestedSymbols = useMemo(() => {
    const normalized = availableSymbols.map((symbol) => symbol.replace(/\s+/g, '').toUpperCase());
    return Array.from(new Set(normalized)).slice(0, 12);
  }, [availableSymbols]);

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

  const addScanSymbol = useCallback((rawSymbol: string) => {
    const normalized = rawSymbol.replace(/\s+/g, '').toUpperCase();
    if (!normalized) {
      return;
    }
    setScanFilters((prev) => {
      if (prev.symbols.includes(normalized)) {
        return prev;
      }
      return {
        ...prev,
        symbols: [...prev.symbols, normalized],
      };
    });
  }, []);

  const removeScanSymbol = useCallback((symbol: string) => {
    setScanFilters((prev) => ({
      ...prev,
      symbols: prev.symbols.filter((value) => value !== symbol),
    }));
  }, []);

  const handleAddScanSymbol = useCallback(() => {
    if (!scanSymbolInput.trim()) {
      return;
    }
    addScanSymbol(scanSymbolInput);
    setScanSymbolInput('');
  }, [scanSymbolInput, addScanSymbol]);

  const handleSymbolInputKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        handleAddScanSymbol();
      }
    },
    [handleAddScanSymbol]
  );

  const toggleAssetTier = useCallback((tier: string, enabled: boolean) => {
    const normalized = tier.trim();
    if (!normalized) {
      return;
    }

    setScanFilters((prev) => {
      const hasTier = prev.assetTiers.includes(normalized);
      if (enabled && !hasTier) {
        return { ...prev, assetTiers: [...prev.assetTiers, normalized] };
      }
      if (!enabled && hasTier) {
        return { ...prev, assetTiers: prev.assetTiers.filter((value) => value !== normalized) };
      }
      return prev;
    });
  }, []);

  const clearAssetTiers = useCallback(() => {
    setScanFilters((prev) => ({ ...prev, assetTiers: [] }));
  }, []);

  const toggleStrategySelection = useCallback((strategyId: string, enabled: boolean) => {
    const normalized = strategyId.trim();
    if (!normalized) {
      return;
    }

    setScanFilters((prev) => {
      const hasStrategy = prev.strategyIds.includes(normalized);
      if (enabled && !hasStrategy) {
        return { ...prev, strategyIds: [...prev.strategyIds, normalized] };
      }
      if (!enabled && hasStrategy) {
        return { ...prev, strategyIds: prev.strategyIds.filter((value) => value !== normalized) };
      }
      return prev;
    });
  }, []);

  const selectAllStrategies = useCallback(() => {
    if (!strategies.length) {
      return;
    }
    setScanFilters((prev) => {
      const combined = new Set([...prev.strategyIds, ...strategies.map((strategy) => strategy.strategy_id)]);
      return { ...prev, strategyIds: Array.from(combined) };
    });
  }, [strategies]);

  const clearStrategies = useCallback(() => {
    setScanFilters((prev) => ({ ...prev, strategyIds: [] }));
  }, []);

  const normalizeFiltersForSubmission = useCallback(
    (filters: OpportunityScanFilterState): OpportunityScanFilterState => {
      const normalizeArray = (values: string[], transform?: (value: string) => string): string[] => {
        if (!values.length) {
          return [];
        }

        const next = new Set<string>();
        values.forEach((value) => {
          if (!value) {
            return;
          }
          const trimmed = value.trim();
          if (!trimmed) {
            return;
          }
          const finalValue = transform ? transform(trimmed) : trimmed;
          if (finalValue) {
            next.add(finalValue);
          }
        });
        return Array.from(next);
      };

      return {
        symbols: normalizeArray(filters.symbols, (value) => value.toUpperCase()),
        assetTiers: normalizeArray(filters.assetTiers),
        strategyIds: normalizeArray(filters.strategyIds),
      };
    },
    []
  );

  const handleOpenScanDialog = useCallback(() => {
    setScanDialogOpen(true);
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
        description: `${tradeForm.action.toUpperCase()} ${tradeForm.symbol} ? ${formatCurrency(Number(result.amount || tradeForm.amount))}`,
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
  }, [
    tradeForm,
    toast,
    selectedStrategy,
    pushWorkflowLog,
    creditActions,
    fetchPortfolio,
    fetchRecentTrades,
    scanFilters,
  ]);

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
    async (
      action: 'opportunity' | 'validation' | 'risk' | 'portfolio' | 'market' | 'decision',
      options?: { filters?: OpportunityScanFilterState }
    ) => {
      try {
        const primarySymbol = sanitizedTargetSymbols[0] || tradeForm.symbol;

        switch (action) {
          case 'opportunity': {
            const appliedFilters = options?.filters ?? scanFilters;
            if (options?.filters) {
              setScanFilters(options.filters);
            }
            let lastLoggedMessage: string | null = null;
            const logMessage = (level: WorkflowLogLevel, message: string) => {
              if (lastLoggedMessage === message) {
                return;
              }
              lastLoggedMessage = message;
              pushWorkflowLog(level, message);
            };

            const filterMessages: string[] = [];
            if (appliedFilters?.symbols?.length) {
              filterMessages.push(`symbols (${appliedFilters.symbols.join(', ')})`);
            }
            if (appliedFilters?.assetTiers?.length) {
              filterMessages.push(`asset tiers (${appliedFilters.assetTiers.join(', ')})`);
            }
            if (appliedFilters?.strategyIds?.length) {
              filterMessages.push(`strategies (${appliedFilters.strategyIds.join(', ')})`);
            }

            const filterSuffix = filterMessages.length ? ` with ${filterMessages.join('; ')}` : '';

            logMessage('info', `Scanning opportunities using your active trading strategies${filterSuffix}...`);

            // 1. Initiate the enterprise opportunity discovery scan
            const scanInitiation = await opportunityApi.discoverOpportunities({
              force_refresh: true,
              include_strategy_recommendations: true,
              symbols: appliedFilters?.symbols?.length ? appliedFilters.symbols : undefined,
              asset_tiers: appliedFilters?.assetTiers?.length ? appliedFilters.assetTiers : undefined,
              strategy_ids: appliedFilters?.strategyIds?.length ? appliedFilters.strategyIds : undefined,
            });

            if (!scanInitiation?.success) {
              throw new Error(scanInitiation?.message || 'Opportunity scan failed');
            }

            logMessage('info', `Scan initiated with ID: ${scanInitiation.scan_id}`);

            // 2. Poll for scan results using the new async pattern
            let scanResult: OpportunityDiscoveryResponse | null = null;
            let pollAttempts = 0;
            const pollIntervalMs = (scanInitiation.polling_interval_seconds ?? 3) * 1000;
            const estimatedRuntimeMs = (scanInitiation.estimated_completion_seconds ?? 120) * 1000;
            const maxWaitMs = Math.max(120_000, Math.floor(estimatedRuntimeMs * 1.5));
            const maxPollAttempts = Math.max(40, Math.ceil(maxWaitMs / Math.max(pollIntervalMs, 1000)));
            let consecutiveErrors = 0;
            let lastNotFoundLoggedAt = -1;
            let notFoundStreak = 0;
            let lastPartialResults: DiscoveryOpportunity[] = [];

            const attemptEarlyResultFetch = async (): Promise<OpportunityDiscoveryResponse | null> => {
              try {
                return await opportunityApi.getScanResults(scanInitiation.scan_id);
              } catch (error) {
                if (error instanceof OpportunityApiError) {
                  const pendingCodes = ['SCAN_IN_PROGRESS', '202', '404', 'SCAN_NOT_FOUND'];
                  if (pendingCodes.includes(error.code ?? '')) {
                    return null;
                  }
                }

                throw error;
              }
            };

            while (pollAttempts < maxPollAttempts) {
              await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
              pollAttempts++;

              try {
                const statusResponse = await opportunityApi.getScanStatus(scanInitiation.scan_id);

                // Reset error counter on successful response
                consecutiveErrors = 0;

                const normalizedStatus = (statusResponse.status || '').toLowerCase();

                switch (normalizedStatus) {
                  case 'complete': {
                    logMessage('success', 'Scan completed successfully! Fetching results...');

                    const results = await attemptEarlyResultFetch();
                    if (results) {
                      scanResult = results;
                      logMessage('success', `Retrieved ${results.total_opportunities} opportunities${filterSuffix}.`);
                      break;
                    }

                    logMessage('info', 'Results not ready yet. Waiting for backend to finalize...');
                    break;
                  }
                  case 'scanning':
                  case 'running':
                  case 'in_progress':
                  case 'processing':
                  case 'queued':
                  case 'pending':
                  case 'initiated':
                  case 'initializing': {
                    notFoundStreak = 0;
                    const progress = statusResponse.progress;
                    if (progress) {
                      logMessage(
                        'info',
                        `Scanning... ${progress.strategies_completed}/${progress.total_strategies} strategies (${progress.percentage ?? 0}%)`
                      );
                    } else {
                      logMessage('info', `Scan in progress (attempt ${pollAttempts}/${maxPollAttempts})...`);
                    }

                    if (Array.isArray(statusResponse.partial_results) && statusResponse.partial_results.length > 0) {
                      lastPartialResults = statusResponse.partial_results;
                    }

                    if (pollAttempts >= 3 && pollAttempts % 5 === 0) {
                      const results = await attemptEarlyResultFetch();
                    if (results) {
                      scanResult = results;
                      logMessage('success', `Retrieved ${results.total_opportunities} opportunities${filterSuffix}.`);
                        break;
                      }
                    }
                    break;
                  }
                  case 'not_found': {
                    notFoundStreak++;
                    // Avoid spamming the log with the same message
                    if (lastNotFoundLoggedAt !== pollAttempts) {
                      logMessage('warning', 'Scan not yet registered - waiting for backend to initialise the job...');
                      lastNotFoundLoggedAt = pollAttempts;
                    }

                    if (notFoundStreak >= 3) {
                      const results = await attemptEarlyResultFetch();
                    if (results) {
                      scanResult = results;
                      logMessage('success', `Retrieved ${results.total_opportunities} opportunities${filterSuffix}.`);
                        break;
                      }
                    }
                    break;
                  }
                  case 'failed': {
                    const failureReason = statusResponse.message || 'Scan failed';
                    logMessage('error', `Scan failed: ${failureReason}`);
                    throw new Error(failureReason);
                  }
                  default: {
                    logMessage('warning', `Unexpected scan status: ${statusResponse.status}`);
                  }
                }

                if (scanResult) {
                  break;
                }
              } catch (pollError: any) {
                consecutiveErrors++;

                if (pollError instanceof OpportunityApiError) {
                  const statusCode = pollError.code;

                  if (statusCode === '401' || statusCode === '403') {
                    logMessage('error', `Authentication error (${statusCode}): ${pollError.message}`);
                  } else if (statusCode === '404' || statusCode === 'SCAN_NOT_FOUND') {
                    logMessage('error', `Scan not found (${statusCode}) - please initiate a new scan.`);
                    throw pollError;
                  } else if (statusCode === '500') {
                    logMessage('error', `Backend service error (500): ${pollError.message}`);
                  } else {
                    logMessage('error', `Polling error (${statusCode || 'unknown'}): ${pollError.message}`);
                  }
                } else {
                  // Extract detailed error information if available from Axios
                  const statusCode = pollError?.response?.status;
                  const errorDetail = pollError?.response?.data?.detail || pollError?.response?.data?.message;
                  const errorMsg = pollError?.message || 'Unknown error';

                  if (statusCode === 500) {
                    logMessage('error', `Backend service error (500): ${errorDetail || errorMsg}`);
                    logMessage('error', 'Internal server error occurred. Check backend logs for details.');
                  } else if (statusCode === 404) {
                    logMessage('error', `Scan not found (404) - scan_id may be invalid or scan was not created`);
                  } else if (statusCode === 401 || statusCode === 403) {
                    logMessage('error', `Authentication error (${statusCode}): ${errorDetail || errorMsg}`);
                  } else if (pollError?.code === 'ECONNABORTED' || pollError?.code === 'ETIMEDOUT') {
                    logMessage('warning', `Request timeout (attempt ${pollAttempts}/${maxPollAttempts})`);
                  } else {
                    logMessage('error', `Polling error (${statusCode || 'network'}): ${errorDetail || errorMsg}`);
                  }
                }

                // If we have 3+ consecutive errors, fail fast
                if (consecutiveErrors >= 3) {
                  logMessage('error', `Aborting scan after ${consecutiveErrors} consecutive errors`);
                  const error = new Error(`Backend service unavailable - ${consecutiveErrors} consecutive errors`);
                  error.cause = pollError;
                  throw error;
                }

                logMessage('info', `Retrying... (${consecutiveErrors} consecutive errors)`);
                continue;
              }
            }

            if (!scanResult) {
              try {
                const finalResults = await attemptEarlyResultFetch();
                if (finalResults) {
                  scanResult = finalResults;
                  logMessage('success', `Retrieved ${finalResults.total_opportunities} opportunities${filterSuffix}.`);
                }
              } catch (finalError) {
                if (
                  !(finalError instanceof OpportunityApiError &&
                  (finalError.code === 'SCAN_IN_PROGRESS' || finalError.code === 'SCAN_NOT_FOUND'))
                ) {
                  throw finalError;
                }
              }
            }

            if (!scanResult) {
              if (lastPartialResults.length > 0) {
                logMessage('warning', 'Scan timed out - using latest partial results while backend continues processing.');
                scanResult = {
                  success: true,
                  scan_id: scanInitiation.scan_id,
                  user_id: user?.id || 'unknown',
                  opportunities: lastPartialResults,
                  total_opportunities: lastPartialResults.length,
                  signal_analysis: null,
                  threshold_transparency: null,
                  user_profile: {},
                  strategy_performance: {},
                  asset_discovery: {},
                  strategy_recommendations: [],
                  execution_time_ms: 0,
                  last_updated: new Date().toISOString(),
                  fallback_used: true
                };
              } else {
                logMessage('error', `Scan timeout - taking longer than ${Math.round(maxWaitMs / 1000)} seconds`);
                throw new Error('Scan timeout - taking longer than expected. The scan may still be running in the background.');
              }
            }

            // 3. Parse opportunities from scan result
            const opportunities = scanResult.opportunities || [];

            logMessage('success', `Found ${opportunities.length} opportunities from your active strategies${filterSuffix}.`);

            // 2. Map opportunities from discovery service to our Opportunity type
            // These are already pre-validated by the strategy engine
            const validated: Opportunity[] = opportunities.map((opp: any) => {
              const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString(); // 5 minutes from now

              // Normalize opportunity_type for case-insensitive comparison
              const oppType = String(opp.opportunity_type || '').toLowerCase().trim();

              // Determine side with explicit checks for long/buy and short/sell
              let side: 'buy' | 'sell';
              if (oppType.includes('long') || oppType.includes('buy')) {
                side = 'buy';
              } else if (oppType.includes('short') || oppType.includes('sell')) {
                side = 'sell';
              } else {
                // Default fallback
                side = 'sell';
              }

              return {
                id: crypto.randomUUID(),
                symbol: opp.symbol,
                side,
                strategy: opp.strategy_name || opp.strategy_id || 'Unknown',
                confidence: Number(opp.confidence_score ?? 0) * 100, // Convert 0-1 to 0-100
                entry_price: Number(opp.entry_price ?? 0),
                stop_loss: Number(opp.metadata?.stop_loss ?? 0),
                take_profit: Number(opp.metadata?.take_profit ?? 0),
                suggested_position_size: Number(opp.required_capital_usd ?? 0),
                position_size_percent: Number(opp.metadata?.position_size_percent ?? 5),
                max_risk: Number(opp.metadata?.max_risk_usd ?? 0),
                max_risk_percent: Number(opp.metadata?.max_risk_percent ?? 2),
                potential_gain: Number(opp.profit_potential_usd ?? 0),
                potential_gain_percent: Number(opp.metadata?.potential_gain_percent ?? 0),
                risk_reward_ratio: Number(opp.metadata?.risk_reward_ratio ?? 0),
                timeframe: opp.estimated_timeframe || '4h',
                reasoning: opp.metadata?.reasoning || `Opportunity detected by ${opp.strategy_name}`,
                indicators: opp.metadata?.indicators,
                timestamp: opp.discovered_at || new Date().toISOString(),
                expires_at: expiresAt,
                aiValidated: true, // Already validated by strategy engine
                validation: {
                  approved: true,
                  consensus_score: Number(opp.confidence_score ?? 0) * 100,
                  confidence: Number(opp.confidence_score ?? 0) * 100,
                  reason: `Strategy-validated opportunity: ${opp.strategy_name}`,
                  model_responses: [],
                  risk_assessment: {
                    level: (opp.risk_level?.toUpperCase() || 'MEDIUM') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                    max_loss: opp.stop_loss ? Math.abs(opp.entry_price - opp.stop_loss) * (opp.suggested_position_size || 0) : 0,
                    max_loss_percent: opp.stop_loss ? Math.abs((opp.stop_loss - opp.entry_price) / opp.entry_price) * 100 : 0
                  }
                },
                validationReason: undefined
              };
            });

            const nonValidated: Opportunity[] = []; // All opportunities from service are pre-validated

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
              title: `? ${validated.length} AI-Validated Opportunities`,
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
      selectedStrategy,
      scanFilters,
      pricingConfig,
      user,
    ]
  );

  const handleStartOpportunityScan = useCallback(() => {
    const normalized = normalizeFiltersForSubmission(scanFilters);
    setScanDialogOpen(false);
    void handleConsensusAction('opportunity', { filters: normalized });
  }, [
    handleConsensusAction,
    normalizeFiltersForSubmission,
    scanFilters,
  ]);

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

  // Removed: auto-switch to workflow tab (tabs no longer used)

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
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full flex flex-col">
      {/* Header Section */}
      <div className="flex-shrink-0 border-b p-6">
        {/* Pricing Error Alert */}
        {pricingError && (
          <div className="mb-4 rounded-lg border-red-500/50 bg-red-500/10 p-4">
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
          </div>
        )}

        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <Target className="h-8 w-8 text-primary" />
              Manual Trading
            </h1>
            <p className="text-muted-foreground mt-1">
              Professional trading interface with AI-powered intelligence
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline" className="gap-1">
              <Radio className="h-3 w-3" />
              {isConnectionOpen ? 'AI Live' : 'AI Idle'}
            </Badge>
            <Badge variant="outline" className="gap-1">
              <ListTree className="h-3 w-3" />
              {aggregatedStats.connectedCount} Exchanges
            </Badge>
            <Badge variant="outline" className="gap-1">
              <DollarSign className="h-3 w-3" />
              {formatCurrency(availableBalance)}
            </Badge>
            <Badge variant="secondary" className="gap-1">
              <Zap className="h-3 w-3" />
              {creditsLoading ? 'Loading...' : `${balance.available_credits} credits`}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 min-h-0">
        {/* LEFT COLUMN: Trading Execution (col-span-8) */}
        <div className="col-span-1 lg:col-span-8 flex flex-col gap-6 min-h-0">
          {/* Trade Execution Form */}
          <Card className="flex-1 flex flex-col overflow-hidden">
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

          {/* Streaming Logs / Phase Execution */}
          {(isStreaming || workflowLogs.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  Execution Log
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-2 text-sm font-mono">
                    {workflowLogs.map((log) => (
                      <div
                        key={log.id}
                        className={`p-2 rounded ${
                          log.level === 'error'
                            ? 'bg-red-500/10 text-red-500'
                            : log.level === 'success'
                            ? 'bg-green-500/10 text-green-500'
                            : log.level === 'warning'
                            ? 'bg-yellow-500/10 text-yellow-500'
                            : 'bg-muted'
                        }`}
                      >
                        <span className="text-muted-foreground">[{log.time}]</span> {log.message}
                      </div>
                    ))}
                    {streamingContent && (
                      <div className="p-2 rounded bg-blue-500/10 text-blue-500">
                        {streamingContent}
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </div>

        {/* RIGHT COLUMN: AI Intelligence Panel (col-span-4) */}
        <div className="col-span-1 lg:col-span-4 flex flex-col gap-4 min-h-0 overflow-hidden">
          <div className="space-y-4 overflow-y-auto flex-1 pr-2 pb-4">
            {/* Quick Action Bar */}
            <Dialog open={scanDialogOpen} onOpenChange={setScanDialogOpen}>
              <DialogContent className="max-w-3xl">
                <DialogHeader>
                  <DialogTitle>Configure opportunity scan</DialogTitle>
                  <DialogDescription>
                    Choose optional filters to focus the scan. Leave everything blank to analyze all eligible assets and strategies.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-6">
                  <div>
                    <Label className="text-sm font-semibold">Symbols</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      Provide trading pairs (e.g. BTCUSDT). Leave empty to scan the full asset universe.
                    </p>
                    <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                      <Input
                        value={scanSymbolInput}
                        onChange={(event) => setScanSymbolInput(event.target.value)}
                        onKeyDown={handleSymbolInputKeyDown}
                        placeholder="Add symbol (press Enter to add)"
                        className="sm:flex-1"
                      />
                      <div className="flex gap-2">
                        <Button type="button" variant="secondary" onClick={handleAddScanSymbol}>
                          Add
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setScanFilters((prev) => ({ ...prev, symbols: [] }))}
                          disabled={!scanFilters.symbols.length}
                        >
                          Clear
                        </Button>
                      </div>
                    </div>
                    {scanFilters.symbols.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {scanFilters.symbols.map((symbol) => (
                          <Badge key={symbol} variant="secondary" className="flex items-center gap-1">
                            {symbol}
                            <button
                              type="button"
                              onClick={() => removeScanSymbol(symbol)}
                              className="text-xs leading-none text-muted-foreground transition-colors hover:text-destructive focus:outline-none"
                              aria-label={`Remove ${symbol}`}
                            >
                              ?
                            </button>
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-muted-foreground">
                        Leave empty to include every discovered asset.
                      </p>
                    )}
                    {suggestedSymbols.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {suggestedSymbols.map((symbol) => (
                          <Button
                            key={symbol}
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => addScanSymbol(symbol)}
                            disabled={scanFilters.symbols.includes(symbol)}
                          >
                            {symbol}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-semibold">Asset tiers</Label>
                        <p className="text-sm text-muted-foreground">
                          Narrow the scan by daily volume tier. Leave all unchecked to respect your profile tier.
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={clearAssetTiers}
                        disabled={!scanFilters.assetTiers.length}
                      >
                        Use profile tiers
                      </Button>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {ASSET_TIER_OPTIONS.map((tier) => (
                        <label
                          key={tier.value}
                          className="flex items-start gap-3 rounded-md border p-3 transition-colors hover:bg-muted/60"
                        >
                          <Checkbox
                            checked={scanFilters.assetTiers.includes(tier.value)}
                            onCheckedChange={(checked) => toggleAssetTier(tier.value, checked === true)}
                          />
                          <div>
                            <div className="font-medium">{tier.label}</div>
                            <p className="text-xs text-muted-foreground">{tier.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-semibold">Strategies</Label>
                        <p className="text-sm text-muted-foreground">
                          Choose specific strategies to include. Leave empty to scan all active strategies.
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={selectAllStrategies}
                          disabled={!strategies.length}
                        >
                          Select all
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={clearStrategies}
                          disabled={!scanFilters.strategyIds.length}
                        >
                          Clear
                        </Button>
                      </div>
                    </div>
                    <ScrollArea className="max-h-48 rounded-md border">
                      <div className="space-y-2 p-3">
                        {strategies.length === 0 ? (
                          <p className="text-sm text-muted-foreground">No active strategies available.</p>
                        ) : (
                          strategies.map((strategy) => (
                            <label
                              key={strategy.strategy_id}
                              className="flex items-start gap-3 rounded-md p-2 transition-colors hover:bg-muted/60"
                            >
                              <Checkbox
                                checked={scanFilters.strategyIds.includes(strategy.strategy_id)}
                                onCheckedChange={(checked) => toggleStrategySelection(strategy.strategy_id, checked === true)}
                              />
                              <div>
                                <div className="font-medium">{strategy.name}</div>
                                <p className="text-xs text-muted-foreground capitalize">
                                  {strategy.status?.replace(/_/g, ' ') || 'active'}
                                </p>
                              </div>
                            </label>
                          ))
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setScanDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="button" onClick={handleStartOpportunityScan}>
                    Start scan
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <QuickActionBar
              onScanOpportunities={handleOpenScanDialog}
              onValidateTrade={() => handleConsensusAction('validation')}
              onAssessRisk={() => handleConsensusAction('risk')}
              onRebalancePortfolio={() => handleConsensusAction('portfolio')}
              onFinalConsensus={() => handleConsensusAction('decision')}
              availableCredits={balance.available_credits || 0}
              compact={false}
            />

            {/* Phase Progress Visualizer */}
            <PhaseProgressVisualizer
              currentPhase={currentPhase}
              phaseHistory={phaseHistory}
              isCompact={false}
              showMetrics={true}
              allowManualControl={false}
            />

            {/* AI Consensus Card */}
            {latestConsensusData && (
              <AIConsensusCard
                consensusData={latestConsensusData}
                compact={true}
                onApplyRecommendation={applyAiRecommendationToTrade}
              />
            )}

            {/* Market Context Card */}
            {/* TODO: Fix type mismatch between MarketContext and MarketContextData */}
            {/* {marketContext && (
              <MarketContextCard
                marketData={marketContext}
                compact={true}
              />
            )} */}

            {/* AI Usage Stats */}
            <AIUsageStats
              usageData={{
                remainingCredits: balance.available_credits || 0,
                totalCredits: balance.total_purchased_credits || 0,
                todayCalls: balance.total_used_credits || 0,
                todayCost: (balance.total_used_credits || 0) * (pricingConfig?.per_call_estimate || 0.05),
                profitGenerated: dailyPnL > 0 ? dailyPnL : 0,
                roi: dailyPnL > 0 && balance.total_used_credits > 0 ? dailyPnL / ((balance.total_used_credits || 1) * (pricingConfig?.per_call_estimate || 0.05)) : 0
              }}
              isLoading={creditsLoading}
              compact={true}
            />

            {/* Portfolio Snapshot */}
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

            {/* Recent Trades */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  Recent Trades
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-48">
                  <div className="space-y-2 text-sm">
                    {recentTrades.length === 0 ? (
                      <p className="text-muted-foreground text-center py-4">No recent trades</p>
                    ) : (
                      recentTrades.slice(0, 5).map((trade) => (
                        <div key={trade.id} className="rounded-md border p-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold">{trade.symbol}</span>
                            <Badge variant="outline" className="text-xs">
                              {trade.side === 'buy' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                              {trade.side.toUpperCase()}
                            </Badge>
                          </div>
                          <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                            <span>{new Date(trade.time).toLocaleTimeString()}</span>
                            <span className={trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                              {formatCurrency(trade.pnl)}
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
      </div>

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
