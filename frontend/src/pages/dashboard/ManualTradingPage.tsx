import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
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
  ChartSpline,
  Equal,
  Compass,
  HelpCircle,
  Lightbulb
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useUser } from '@/store/authStore';
import { useExchanges } from '@/hooks/useExchanges';
import { useStrategies } from '@/hooks/useStrategies';
import { usePortfolioStore } from '@/hooks/usePortfolio';
import { useAIConsensus } from '@/hooks/useAIConsensus';
import { useCredits } from '@/hooks/useCredits';
import { useChatStore, ChatMode } from '@/store/chatStore';
import PhaseProgressVisualizer, { ExecutionPhase } from '@/components/trading/PhaseProgressVisualizer';
import { PHASE_CONFIG, PhaseData, AIPersonality, PERSONALITY_CONFIG } from '@/constants/trading';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { apiClient } from '@/lib/api/client';

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

const PERSONA_STORAGE_KEY = 'manual-trading-persona-selection';
const TOUR_STORAGE_KEY = 'manual-trading-tour-v1';

type TourStepId = 'hero' | 'persona' | 'trade' | 'workflow' | 'summary' | 'insights';

interface PersonaPreset {
  trade: Partial<ManualTradeRequest>;
  workflow: Partial<WorkflowConfig>;
  headline: string;
  subline: string;
}

const PERSONA_PRESETS: Record<AIPersonality, PersonaPreset> = {
  [AIPersonality.CONSERVATIVE]: {
    trade: {
      orderType: 'limit',
      leverage: 1,
      stopLoss: 2,
      takeProfit: 3,
      amount: 750
    },
    workflow: {
      confidence: 90,
      timeframe: '4h',
      includeRiskMetrics: true,
      aiModels: 'cost_optimized',
      rebalanceThreshold: 2
    },
    headline: 'Protect capital first with tight guardrails.',
    subline: 'High-confidence entries, conservative sizing, and full risk telemetry.'
  },
  [AIPersonality.BALANCED]: {
    trade: {
      orderType: 'market',
      leverage: 2,
      stopLoss: 3,
      takeProfit: 6,
      amount: 1000
    },
    workflow: {
      confidence: 80,
      timeframe: '1h',
      includeRiskMetrics: true,
      aiModels: 'all',
      rebalanceThreshold: 4
    },
    headline: 'Blend growth and safety for daily compounding.',
    subline: 'Balanced AI mix with protective stops and dynamic rebalancing.'
  },
  [AIPersonality.AGGRESSIVE]: {
    trade: {
      orderType: 'market',
      leverage: 3,
      stopLoss: 4,
      takeProfit: 9,
      amount: 1500
    },
    workflow: {
      confidence: 72,
      timeframe: '30m',
      includeRiskMetrics: false,
      aiModels: 'gpt4_claude',
      rebalanceThreshold: 6
    },
    headline: 'Chase momentum with rapid-fire consensus.',
    subline: 'Favors quicker timeframes and looser guardrails for stronger signals.'
  },
  [AIPersonality.DEGEN]: {
    trade: {
      orderType: 'market',
      leverage: 5,
      stopLoss: 6,
      takeProfit: 15,
      amount: 2000
    },
    workflow: {
      confidence: 65,
      timeframe: '15m',
      includeRiskMetrics: false,
      aiModels: 'gpt4_claude',
      rebalanceThreshold: 8
    },
    headline: 'Speculative bursts with high tolerance for volatility.',
    subline: 'Maximizes leverage and keeps safeguards minimal—use with caution.'
  }
};

const ONBOARDING_STEPS: Array<{ title: string; description: string }> = [
  {
    title: '1. Sync with AI consensus',
    description: 'Start with the Live AI Workflow to gather recommendations and surface any portfolio alerts.'
  },
  {
    title: '2. Review suggested actions',
    description: 'Use the AI Recommendation Summary and Insights feed to validate strategy alignment and risk checks.'
  },
  {
    title: '3. Execute with guardrails',
    description: 'Populate the trade form with AI guidance, then add optional risk controls before sending the order.'
  }
];

const TOUR_STEPS: Array<{ id: TourStepId; title: string; description: string }> = [
  {
    id: 'hero',
    title: 'Welcome to the control center',
    description: 'Track AI connectivity, exchange status, and credits at a glance before taking action.'
  },
  {
    id: 'persona',
    title: 'Pick a persona preset',
    description: 'Load trade and workflow defaults that mirror your preferred risk appetite in one click.'
  },
  {
    id: 'trade',
    title: 'Fine-tune orders',
    description: 'Use the guided trade form with optional guardrails before routing through the AI execution stack.'
  },
  {
    id: 'workflow',
    title: 'Stream the AI workflow',
    description: 'Kick off opportunity scans, validations, or rebalancing with the same phases the chat interface runs.'
  },
  {
    id: 'summary',
    title: 'Read the AI headline',
    description: 'Every workflow ends with a plain-language recommendation and confidence score ready to apply.'
  },
  {
    id: 'insights',
    title: 'Review structured insights',
    description: 'Dive into the AI logbook with parsed payloads or expand for the raw execution context.'
  }
];

interface SpotlightArea {
  top: number;
  left: number;
  width: number;
  height: number;
}

const formatPercentValue = (value: number): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—';
  }

  const normalized = Math.abs(value) <= 1 ? value * 100 : value;
  return formatPercentage(normalized);
};

const MAX_INSIGHT_PREVIEW_ENTRIES = 8;

interface InsightEntry {
  label: string;
  value: string;
}

const formatInsightValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  const stringValue = String(value);
  return stringValue.length > 64 ? `${stringValue.slice(0, 61)}…` : stringValue;
};

const extractInsightEntries = (payload: any, path: string[] = []): InsightEntry[] => {
  if (payload === null || payload === undefined) {
    return [
      {
        label: path.length ? path.join(' › ') : 'value',
        value: '—'
      }
    ];
  }

  if (Array.isArray(payload)) {
    if (payload.length === 0) {
      return [
        {
          label: path.length ? path.join(' › ') : 'value',
          value: 'Empty'
        }
      ];
    }

    return payload.flatMap((item, index) =>
      typeof item === 'object' && item !== null
        ? extractInsightEntries(item, [...path, `#${index + 1}`])
        : [
            {
              label: [...path, `#${index + 1}`].join(' › '),
              value: formatInsightValue(item)
            }
          ]
    );
  }

  if (typeof payload === 'object') {
    const entries = Object.entries(payload as Record<string, unknown>);
    if (entries.length === 0) {
      return [
        {
          label: path.length ? path.join(' › ') : 'value',
          value: 'Empty'
        }
      ];
    }

    return entries.flatMap(([key, value]) =>
      typeof value === 'object' && value !== null
        ? extractInsightEntries(value, [...path, key])
        : [
            {
              label: [...path, key].join(' › '),
              value: formatInsightValue(value)
            }
          ]
    );
  }

  return [
    {
      label: path.length ? path.join(' › ') : 'value',
      value: formatInsightValue(payload)
    }
  ];
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
  const [phaseHistory, setPhaseHistory] = useState<PhaseData[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTab, setActiveTab] = useState('trade');
  const [aiInsights, setAiInsights] = useState<Array<{ id: string; title: string; payload: any; function: string; timestamp: string }>>([]);
  const [guidedMode, setGuidedMode] = useState(true);
  const [selectedPersona, setSelectedPersona] = useState<AIPersonality | 'custom'>('custom');
  const [tourActive, setTourActive] = useState(false);
  const [tourStepIndex, setTourStepIndex] = useState(0);
  const [tourSpotlight, setTourSpotlight] = useState<SpotlightArea | null>(null);
  const [tourTooltipPosition, setTourTooltipPosition] = useState<{ top: number; left: number } | null>(null);

  const streamingControllerRef = useRef<AbortController | null>(null);
  const manualSessionRef = useRef<string | null>(null);
  const initializingSessionPromiseRef = useRef<Promise<void> | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  const personaRef = useRef<HTMLDivElement | null>(null);
  const tradeFormRef = useRef<HTMLDivElement | null>(null);
  const workflowRef = useRef<HTMLDivElement | null>(null);
  const summaryRef = useRef<HTMLDivElement | null>(null);
  const insightsRef = useRef<HTMLDivElement | null>(null);

  const stepRefs = useMemo(
    () => ({
      hero: heroRef,
      persona: personaRef,
      trade: tradeFormRef,
      workflow: workflowRef,
      summary: summaryRef,
      insights: insightsRef
    }),
    []
  ) as Record<TourStepId, React.RefObject<HTMLDivElement>>;

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

  const activePersonaLabel = useMemo(() => {
    if (selectedPersona === 'custom') {
      return 'Custom parameters';
    }
    return PERSONALITY_CONFIG[selectedPersona].name;
  }, [selectedPersona]);

  const applyPersonaPreset = useCallback(
    (personality: AIPersonality, options?: { silent?: boolean; persist?: boolean }) => {
      const preset = PERSONA_PRESETS[personality];
      if (!preset) {
        return;
      }

      setTradeForm((prev) => ({ ...prev, ...preset.trade }));
      setWorkflowConfig((prev) => ({ ...prev, ...preset.workflow }));

      if (!options?.silent) {
        const persona = PERSONALITY_CONFIG[personality];
        toast({
          title: `${persona.emoji} ${persona.name} preset loaded`,
          description: preset.subline,
          variant: 'default'
        });
      }

      if (options?.persist !== false && typeof window !== 'undefined') {
        localStorage.setItem(PERSONA_STORAGE_KEY, personality);
      }

      setSelectedPersona(personality);
    },
    [toast]
  );

  const handlePersonaReset = useCallback(() => {
    setSelectedPersona('custom');
    if (typeof window !== 'undefined') {
      localStorage.setItem(PERSONA_STORAGE_KEY, 'custom');
    }

    toast({
      title: 'Custom configuration active',
      description: 'You can now fine-tune every parameter without preset overrides.',
      variant: 'default'
    });
  }, [toast]);

  const handlePersonaSelect = useCallback(
    (personality: AIPersonality) => {
      applyPersonaPreset(personality);
    },
    [applyPersonaPreset]
  );

  const startTour = useCallback(() => {
    setTourStepIndex(0);
    setTourActive(true);
  }, []);

  const completeTour = useCallback(() => {
    setTourActive(false);
    if (typeof window !== 'undefined') {
      localStorage.setItem(TOUR_STORAGE_KEY, 'seen');
    }
  }, []);

  const skipTour = useCallback(() => {
    completeTour();
  }, [completeTour]);

  const goToNextTourStep = useCallback(() => {
    setTourStepIndex((previous) => {
      if (previous >= TOUR_STEPS.length - 1) {
        completeTour();
        return previous;
      }
      return previous + 1;
    });
  }, [completeTour]);

  const goToPreviousTourStep = useCallback(() => {
    setTourStepIndex((previous) => Math.max(0, previous - 1));
  }, []);

  const updateSpotlight = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const step = TOUR_STEPS[tourStepIndex];
    if (!step) {
      return;
    }

    const element = stepRefs[step.id]?.current;

    if (!element) {
      setTourSpotlight(null);
      setTourTooltipPosition({
        top: window.scrollY + 120,
        left: 24
      });
      return;
    }

    const rect = element.getBoundingClientRect();
    const top = rect.top + window.scrollY;
    const left = rect.left + window.scrollX;
    const width = rect.width;
    const height = rect.height;

    setTourSpotlight({ top, left, width, height });

    const tooltipWidth = 320;
    const viewportWidth = window.innerWidth;
    const tooltipLeft = Math.min(
      Math.max(left, 24),
      Math.max(24, viewportWidth - tooltipWidth - 24)
    );

    setTourTooltipPosition({
      top: top + height + 24,
      left: tooltipLeft
    });
  }, [stepRefs, tourStepIndex]);

  const getRecommendationTone = useCallback((recommendation: string) => {
    const normalized = recommendation?.toLowerCase?.() || '';

    if (normalized.includes('buy') || normalized.includes('long')) {
      return 'bg-emerald-500/70';
    }

    if (normalized.includes('sell') || normalized.includes('short')) {
      return 'bg-rose-500/70';
    }

    if (normalized.includes('rebalance') || normalized.includes('hedge')) {
      return 'bg-amber-500/70';
    }

    return 'bg-blue-500/70';
  }, []);

  const aiSummaryHeadlines = useMemo(() => {
    if (!aiSummary) {
      return [] as string[];
    }

    const statements: string[] = [];
    const actionData = aiSummary.actionData || {};
    const rawSymbol = actionData.symbol || actionData.asset || actionData.pair || actionData.ticker;
    const symbol = typeof rawSymbol === 'string' ? rawSymbol.toUpperCase() : '';
    const directionValue = actionData.action || actionData.side || aiSummary.intent;

    if (symbol && typeof directionValue === 'string') {
      const direction = directionValue.toUpperCase();
      const confidenceSuffix = typeof aiSummary.confidence === 'number'
        ? ` with ${aiSummary.confidence.toFixed(1)}% confidence`
        : '';
      statements.push(`${direction} ${symbol}${confidenceSuffix} based on AI consensus.`);
    } else if (typeof aiSummary.confidence === 'number') {
      statements.push(`AI consensus confidence at ${aiSummary.confidence.toFixed(1)}%.`);
    }

    const addPriceHeadline = (value: unknown, label: string) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        statements.push(`${label} ${formatCurrency(value)}.`);
      }
    };

    const addPercentHeadline = (value: unknown, label: string) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        statements.push(`${label} ${formatPercentValue(value)}.`);
      }
    };

    addPriceHeadline(actionData.price ?? actionData.entry_price ?? actionData.entry, 'Target entry around');
    addPriceHeadline(actionData.take_profit ?? actionData.target ?? actionData.takeProfit, 'Upside target near');
    addPriceHeadline(actionData.stop_loss ?? actionData.stopLoss, 'Protective stop near');

    addPercentHeadline(actionData.stop_loss_pct ?? actionData.stopLossPct, 'Max drawdown capped at');
    addPercentHeadline(actionData.position_size_pct ?? actionData.positionSizePct, 'Position size set to');
    addPercentHeadline(actionData.rebalance_target, 'Rebalance target at');

    const analysis = aiSummary.aiAnalysis;
    if (Array.isArray(analysis?.key_points)) {
      analysis.key_points.forEach((point: unknown) => {
        if (typeof point === 'string' && point.trim().length > 0) {
          statements.push(point.trim());
        }
      });
    } else if (typeof analysis?.summary === 'string' && analysis.summary.trim().length > 0) {
      statements.push(analysis.summary.trim());
    }

    if (statements.length === 0 && typeof aiSummary.content === 'string') {
      const sanitized = aiSummary.content.replace(/\s+/g, ' ').trim();
      if (sanitized.length > 0) {
        sanitized
          .split(/(?<=[.!?])\s+/)
          .slice(0, 2)
          .forEach((sentence) => {
            if (sentence && sentence.trim().length > 0) {
              statements.push(sentence.trim());
            }
          });
      }
    }

    return Array.from(new Set(statements.filter(Boolean)));
  }, [aiSummary]);

  const consensusTrendPoints = useMemo(() => {
    if (!Array.isArray(consensusHistory)) {
      return [] as Array<{ id: string; value: number; recommendation: string; time: string }>;
    }

    return consensusHistory.slice(-8).map((entry, index) => {
      const numericValue = Number(entry.consensus);
      const clampedValue = Number.isFinite(numericValue)
        ? Math.max(0, Math.min(100, numericValue))
        : 0;

      return {
        id: `${entry.timestamp || index}-${index}`,
        value: clampedValue,
        recommendation: entry.recommendation || 'HOLD',
        time: entry.time || ''
      };
    });
  }, [consensusHistory]);

  const latestConsensus =
    consensusTrendPoints.length > 0 ? consensusTrendPoints[consensusTrendPoints.length - 1] : null;

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const stored = localStorage.getItem(PERSONA_STORAGE_KEY) as AIPersonality | 'custom' | null;
    if (stored && stored !== 'custom') {
      applyPersonaPreset(stored, { silent: true, persist: false });
    } else if (stored === 'custom') {
      setSelectedPersona('custom');
    } else {
      applyPersonaPreset(AIPersonality.BALANCED, { silent: true, persist: false });
    }
  }, [applyPersonaPreset]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const hasSeenTour = localStorage.getItem(TOUR_STORAGE_KEY);
    if (!hasSeenTour) {
      const timer = window.setTimeout(() => {
        setTourStepIndex(0);
        setTourActive(true);
      }, 800);

      return () => window.clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    if (!tourActive) {
      setTourSpotlight(null);
      setTourTooltipPosition(null);
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    const raf = window.requestAnimationFrame(updateSpotlight);
    return () => window.cancelAnimationFrame(raf);
  }, [tourActive, tourStepIndex, updateSpotlight]);

  useEffect(() => {
    if (!tourActive || typeof window === 'undefined') {
      return;
    }

    const handleChange = () => updateSpotlight();
    window.addEventListener('resize', handleChange);
    window.addEventListener('scroll', handleChange, true);

    return () => {
      window.removeEventListener('resize', handleChange);
      window.removeEventListener('scroll', handleChange, true);
    };
  }, [tourActive, updateSpotlight]);

  useEffect(() => {
    if (!tourActive || typeof window === 'undefined') {
      return;
    }

    const step = TOUR_STEPS[tourStepIndex];
    const element = stepRefs[step.id]?.current;
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    }
  }, [tourActive, tourStepIndex, stepRefs]);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    if (!tourActive) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [tourActive]);

  useEffect(() => {
    if (!tourActive || typeof window === 'undefined') {
      return;
    }

    const timer = window.setTimeout(() => updateSpotlight(), 120);
    return () => window.clearTimeout(timer);
  }, [tourActive, guidedMode, aiSummary, aiSummaryHeadlines.length, aiInsights.length, activeTab, updateSpotlight]);

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
      const IconComponent = PHASE_CONFIG[phase].icon;
      const baseDetails = PHASE_CONFIG[phase].details || [];
      const newDetails = detail ? [detail] : [];

      const existingIndex = prev.findIndex((item) => item.phase === phase);
      if (existingIndex >= 0) {
        const updated = [...prev];
        const existingDetails = updated[existingIndex].details || baseDetails;
        const mergedDetails = newDetails.length
          ? Array.from(new Set([...(existingDetails || []), ...newDetails]))
          : existingDetails;
        updated[existingIndex] = {
          ...updated[existingIndex],
          icon: IconComponent,
          details: mergedDetails
        };
        return updated;
      }

      return [
        ...prev,
        {
          phase,
          title: PHASE_CONFIG[phase].title,
          description: PHASE_CONFIG[phase].description,
          icon: IconComponent,
          color: PHASE_CONFIG[phase].color,
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
        onopen: (response) => {
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
            pushWorkflowLog('info', `Scanning live opportunities for ${primarySymbol}.`);
            const result = await analyzeOpportunity({
              symbol: primarySymbol,
              analysis_type: workflowConfig.type === 'opportunity_scan' ? 'opportunity' : 'technical',
              timeframe: workflowConfig.timeframe,
              confidence_threshold: workflowConfig.confidence,
              ai_models: workflowConfig.aiModels,
              include_risk_metrics: workflowConfig.includeRiskMetrics
            });
            recordInsight('Opportunity Analysis', 'analyze_opportunity', result);
            pushWorkflowLog('success', 'Opportunity analysis completed.');
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
    setTradeForm((prev) => ({
      ...prev,
      symbol: proposal.symbol || prev.symbol,
      action: (proposal.action || prev.action || 'buy') as 'buy' | 'sell',
      amount: Number(proposal.amount || prev.amount),
      orderType: (proposal.order_type || prev.orderType || 'market') as ManualTradeRequest['orderType'],
      price: proposal.price ? Number(proposal.price) : prev.price,
      stopLoss: proposal.stop_loss ? Number(proposal.stop_loss) : prev.stopLoss,
      takeProfit: proposal.take_profit ? Number(proposal.take_profit) : prev.takeProfit,
      leverage: proposal.leverage ? Number(proposal.leverage) : prev.leverage
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

  useEffect(() => {
    if (!connectionStatus) {
      return;
    }

    const normalizedStatus = connectionStatus.toLowerCase();
    const message =
      connectionStatus === 'OPEN'
        ? 'AI consensus channel connected.'
        : `AI consensus connection ${normalizedStatus}.`;

    pushWorkflowLog('info', message);
  }, [connectionStatus, pushWorkflowLog]);

  useEffect(() => {
    if (isStreaming && activeTab !== 'workflow') {
      setActiveTab('workflow');
    }
  }, [isStreaming, activeTab]);

  const currentTourStep = TOUR_STEPS[tourStepIndex];

  return (
    <>
      {tourActive && currentTourStep && (
        <div className="fixed inset-0 z-[60]">
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />
          {tourSpotlight && (
            <div
              className="pointer-events-none absolute rounded-xl border-2 border-primary shadow-[0_0_0_9999px_rgba(15,23,42,0.55)] transition-all duration-200"
              style={{
                top: Math.max(12, tourSpotlight.top - 16),
                left: Math.max(12, tourSpotlight.left - 16),
                width: tourSpotlight.width + 32,
                height: tourSpotlight.height + 32
              }}
            />
          )}
          <div
            className="pointer-events-auto absolute z-[61] max-w-sm rounded-lg border bg-background p-5 shadow-xl"
            style={{
              top:
                tourTooltipPosition?.top ??
                (typeof window !== 'undefined' ? window.scrollY + 120 : 120),
              left: tourTooltipPosition?.left ?? 24
            }}
          >
            <div className="space-y-2">
              <Badge variant="outline" className="text-xs uppercase tracking-wide">
                Guided walkthrough
              </Badge>
              <h3 className="text-lg font-semibold">{currentTourStep.title}</h3>
              <p className="text-sm text-muted-foreground">{currentTourStep.description}</p>
            </div>
            <div className="mt-4 flex items-center justify-between gap-2">
              <Button variant="ghost" size="sm" onClick={skipTour}>
                Skip
              </Button>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={goToPreviousTourStep}
                  disabled={tourStepIndex === 0}
                >
                  Back
                </Button>
                <Button size="sm" onClick={goToNextTourStep}>
                  {tourStepIndex >= TOUR_STEPS.length - 1 ? 'Finish' : 'Next'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
        <div ref={heroRef} className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Manual Trading Control Center</h1>
            <p className="text-muted-foreground">
              Execute trades, rebalancing, and AI-driven actions with full transparency into every phase.
            </p>
          </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className="gap-1">
            <Radio className="h-3 w-3" />
            {connectionStatus === 'OPEN' ? 'AI live' : 'AI idle'}
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
          <div className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-2">
            <Compass className="hidden h-4 w-4 text-muted-foreground sm:block" />
            <div className="space-y-0.5">
              <Label htmlFor="guided-mode-toggle" className="text-sm font-medium leading-none">
                Guided mode
              </Label>
              <p className="text-xs text-muted-foreground">
                Surface onboarding tips for manual workflows.
              </p>
            </div>
            <Switch id="guided-mode-toggle" checked={guidedMode} onCheckedChange={setGuidedMode} />
          </div>
        </div>
        </div>

        {guidedMode && (
          <Alert variant="warning" className="border-dashed border-warning/50 bg-warning/5">
            <div className="flex items-start gap-3">
              <Lightbulb className="mt-1 h-4 w-4 text-warning" />
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <AlertTitle className="flex items-center gap-2 text-sm font-semibold">
                    <HelpCircle className="h-4 w-4" />
                    Quick start for first-time operators
                  </AlertTitle>
                </div>
                <AlertDescription>
                  <ol className="space-y-2 text-sm">
                    {ONBOARDING_STEPS.map((step) => (
                      <li key={step.title} className="flex gap-2">
                        <span className="font-semibold text-foreground">{step.title}</span>
                        <span className="text-muted-foreground">{step.description}</span>
                      </li>
                    ))}
                  </ol>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs text-muted-foreground">
                      Switch off guided mode above once you are comfortable working without the onboarding tips.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        startTour();
                      }}
                    >
                      Replay walkthrough
                    </Button>
                  </div>
                </AlertDescription>
              </div>
            </div>
          </Alert>
        )}

        <Card ref={personaRef} className="border-dashed border-primary/40 bg-primary/5">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Compass className="h-4 w-4" />
              Persona presets
            </CardTitle>
            <CardDescription>
              Load workflow and trade defaults that mirror the AI personas available in the chat experience.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {Object.entries(PERSONALITY_CONFIG).map(([key, persona]) => {
                const personaKey = key as AIPersonality;
                const preset = PERSONA_PRESETS[personaKey];
                const isActive = selectedPersona === personaKey;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handlePersonaSelect(personaKey)}
                    className={`group flex h-full flex-col justify-between rounded-lg border p-4 text-left transition ${
                      isActive
                        ? 'border-primary bg-primary/10 shadow-lg'
                        : 'border-border/70 hover:border-primary/70 hover:bg-primary/5'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-semibold">
                          {persona.emoji} {persona.name}
                        </span>
                        <Badge variant={isActive ? 'default' : 'outline'} className="text-xs">
                          {persona.riskLevel} risk
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{preset.headline}</p>
                    </div>
                    <div className="mt-4 flex items-center justify-between text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      <span>Target {formatPercentage(persona.dailyTargetPct)}</span>
                      <span>Drawdown {formatPercentage(persona.maxDrawdownPct)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
              <span>Current preset: {activePersonaLabel}</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={startTour}>
                  Show tour
                </Button>
                <Button variant="secondary" size="sm" onClick={handlePersonaReset}>
                  Custom setup
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trade">Execute Trade</TabsTrigger>
          <TabsTrigger value="workflow">AI Workflow</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="risk">Live Intelligence</TabsTrigger>
        </TabsList>

        <TabsContent value="trade" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <Card ref={tradeFormRef} className="lg:col-span-2">
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
                    {guidedMode && (
                      <p className="text-xs text-muted-foreground">
                        Match the pair to the assets you are analyzing in the AI workflow.
                      </p>
                    )}
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
                    {guidedMode && (
                      <p className="text-xs text-muted-foreground">
                        Choose whether you want the AI to express a long or short bias.
                      </p>
                    )}
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
                    {guidedMode && (
                      <p className="text-xs text-muted-foreground">
                        Market orders execute instantly; limit and stop orders require a price target.
                      </p>
                    )}
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
                    {guidedMode && (
                      <p className="text-xs text-muted-foreground">
                        Stay on auto for AI venue selection or pick a specific connected exchange.
                      </p>
                    )}
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
                    {guidedMode && (
                      <p className="text-xs text-muted-foreground">
                        Size the trade by notional value; AI validations will flag exposure limits automatically.
                      </p>
                    )}
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
                      {guidedMode && (
                        <p className="text-xs text-muted-foreground">
                          Provide the trigger price you want the order to respect.
                        </p>
                      )}
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

                <Accordion
                  key={guidedMode ? 'guided-risk' : 'expert-risk'}
                  type="single"
                  collapsible
                  defaultValue={guidedMode ? undefined : 'advanced-risk'}
                  className="rounded-md border"
                >
                  <AccordionItem value="advanced-risk">
                    <AccordionTrigger className="px-4 text-sm font-medium">
                      Advanced risk controls (optional)
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-4">
                      <div className="grid gap-4 md:grid-cols-3">
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
                        <div className="space-y-2">
                          <Label>Leverage</Label>
                          <Input
                            type="number"
                            min={1}
                            step={1}
                            value={tradeForm.leverage ?? ''}
                            onChange={(event) =>
                              setTradeForm((prev) => ({
                                ...prev,
                                leverage: event.target.value ? Number(event.target.value) : undefined
                              }))
                            }
                            placeholder="Optional leverage"
                          />
                        </div>
                      </div>
                      <p className="mt-3 text-xs text-muted-foreground">
                        These safeguards travel with your order so the execution service can mirror the same guardrails used in
                        the automated chat workflows.
                      </p>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>

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
            <Card ref={workflowRef} className="xl:col-span-2">
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
                    <ChartSpline className="h-4 w-4" />
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

          <Card ref={summaryRef}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Brain className="h-4 w-4" />
                AI Recommendation Summary
              </CardTitle>
              <CardDescription>Final consensus from the AI workflow with actionable context.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {aiSummaryHeadlines.length > 0 ? (
                <div className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-4">
                  <h4 className="flex items-center gap-2 text-sm font-semibold text-primary">
                    <Sparkles className="h-4 w-4" />
                    Key takeaways
                  </h4>
                  <ul className="space-y-2 text-sm text-foreground">
                    {aiSummaryHeadlines.map((headline) => (
                      <li key={headline} className="flex items-start gap-2">
                        <CheckCircle className="mt-0.5 h-4 w-4 text-primary" />
                        <span>{headline}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-muted-foreground/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Run the live AI workflow to produce a consensus headline and actionable checklist.
                </div>
              )}

              {consensusTrendPoints.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Consensus trend</span>
                    {latestConsensus && (
                      <Badge variant="outline">
                        {latestConsensus.recommendation} · {latestConsensus.value.toFixed(0)}%
                      </Badge>
                    )}
                  </div>
                  <div className="flex h-24 items-end gap-1 rounded-md border border-border/60 bg-muted/20 p-2">
                    {consensusTrendPoints.map((point) => (
                      <div
                        key={point.id}
                        className={`flex-1 rounded-t ${getRecommendationTone(point.recommendation)}`}
                        style={{ height: `${Math.max(6, point.value)}%` }}
                        title={`${point.recommendation} · ${point.value.toFixed(0)}%`}
                      />
                    ))}
                  </div>
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>{consensusTrendPoints[0]?.time}</span>
                    <span>{consensusTrendPoints[consensusTrendPoints.length - 1]?.time}</span>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                  {typeof aiSummary?.confidence === 'number' && (
                    <Badge variant="outline">Confidence {aiSummary.confidence.toFixed(1)}%</Badge>
                  )}
                  {aiSummary?.intent && <Badge variant="outline">Intent {aiSummary.intent}</Badge>}
                  {aiSummary?.requiresApproval && <Badge variant="outline">Requires Approval</Badge>}
                </div>
                <ScrollArea className="h-40 rounded-md border p-4 text-sm">
                  {aiSummary?.content ? (
                    <pre className="whitespace-pre-wrap text-muted-foreground">{aiSummary.content}</pre>
                  ) : (
                    <p className="text-muted-foreground">
                      No narrative summary yet. Launch a workflow or refresh consensus to populate this section.
                    </p>
                  )}
                </ScrollArea>
              </div>

              <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                {aiSummary?.actionData ? (
                  <>
                    <h4 className="mb-2 font-semibold">Suggested Action</h4>
                    <div className="grid gap-2 md:grid-cols-2">
                      {Object.entries(aiSummary.actionData).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-muted-foreground">{key.replaceAll('_', ' ')}</span>
                          <span className="font-medium">{typeof value === 'number' ? value.toString() : String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-muted-foreground">
                    When the AI produces trade instructions they will appear here with structured fields you can apply instantly.
                  </p>
                )}
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  variant="outline"
                  onClick={applyAiRecommendationToTrade}
                  disabled={!aiSummary?.actionData}
                >
                  <Settings className="mr-2 h-4 w-4" />
                  Apply to Trade Form
                </Button>
                <Button onClick={() => handleConsensusAction('decision')} disabled={workflowDisabled}>
                  <Brain className="mr-2 h-4 w-4" />
                  Refresh Consensus
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card ref={insightsRef}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4" />
                AI Insights Feed
              </CardTitle>
              <CardDescription>Recent consensus calls and data pulls driven by manual requests.</CardDescription>
            </CardHeader>
            <CardContent>
              {aiInsights.length === 0 ? (
                <div className="rounded-md border border-dashed border-muted-foreground/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No AI insights logged yet. Trigger scans, validations, or final consensus runs to populate this feed.
                </div>
              ) : (
                <ScrollArea className="max-h-64 pr-2">
                  <div className="space-y-3 text-sm">
                    {aiInsights.map((insight) => {
                      const entries = extractInsightEntries(insight.payload);
                      const previewEntries = entries.slice(0, MAX_INSIGHT_PREVIEW_ENTRIES);
                      return (
                        <div key={insight.id} className="rounded-md border p-3">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>{new Date(insight.timestamp).toLocaleTimeString()}</span>
                            <Badge variant="outline">{insight.function}</Badge>
                          </div>
                          <h4 className="mt-1 font-semibold">{insight.title}</h4>
                          <div className="mt-2 space-y-1 text-xs sm:text-sm">
                            {previewEntries.map((entry, index) => (
                              <div
                                key={`${insight.id}-${entry.label}-${index}`}
                                className="flex items-start justify-between gap-3 rounded border border-dashed border-border/60 px-2 py-1"
                              >
                                <span className="text-muted-foreground">{entry.label}</span>
                                <span className="font-medium text-right">{entry.value}</span>
                              </div>
                            ))}
                          </div>
                          {entries.length > previewEntries.length && (
                            <details className="mt-2 text-xs">
                              <summary className="cursor-pointer text-primary">View full payload</summary>
                              <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap text-muted-foreground">
                                {JSON.stringify(insight.payload, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
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
    </motion.div>
  </>
);
};

export default ManualTradingPage;
