import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  MessageSquare,
  TrendingUp,
  Settings,
  Users,
  Zap,
  Shield,
  Activity,
  DollarSign,
  BarChart3,
  Bot,
  Play,
  Pause,
  History,
  AlertCircle,
  CheckCircle
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
import { usePaperModeStore, useIsPaperMode } from '@/store/paperModeStore';
import { useAuthStore } from '@/store/authStore';

// Import API client
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage } from '@/lib/utils';

// Manual Trading Component (extracted from ManualTradingPage)
import ManualTradingPanel from './components/ManualTradingPanel';

// Autonomous Settings Component (extracted from AutonomousPage)
import AutonomousSettingsPanel from './components/AutonomousSettingsPanel';

interface TradeExecution {
  id: string;
  phase: ExecutionPhase;
  details: any;
  timestamp: Date;
  isPaperMode: boolean;
}

const AIMoneyManager: React.FC = () => {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const isPaperMode = useIsPaperMode();
  const { fetchPaperStats, paperStats } = usePaperModeStore();

  // State management
  const [activeTab, setActiveTab] = useState('conversation');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  const [phaseDetails, setPhaseDetails] = useState<any>({});
  const [isAutonomousEnabled, setIsAutonomousEnabled] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<TradeExecution | null>(null);
  const [recentExecutions, setRecentExecutions] = useState<TradeExecution[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);

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
      const response = await apiClient.post('/api/v1/chat/sessions', {
        session_type: 'trading',
        context: {
          isPaperMode,
          user_id: user?.id
        }
      });

      if (response.data.success) {
        setSessionId(response.data.data.session_id);
      }
    } catch (error) {
      console.error('Failed to initialize chat session:', error);
    }
  };

  const connectWebSocket = () => {
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/ai-consensus/ws`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected for real-time updates');
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);
  };

  const handleWebSocketMessage = (data: any) => {
    if (data.type === 'phase_update') {
      setCurrentPhase(data.phase);
      setPhaseDetails((prev: any) => ({
        ...prev,
        [data.phase]: data.details
      }));
    } else if (data.type === 'execution_complete') {
      handleExecutionComplete(data);
    }
  };

  const handleExecutionComplete = (data: any) => {
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
  const executeTradeWithPhases = async (tradeParams: any) => {
    setIsExecuting(true);
    
    try {
      // Phase 1: Analysis
      setCurrentPhase(ExecutionPhase.ANALYSIS);
      const analysisResponse = await apiClient.post('/api/v1/ai-consensus/analyze-opportunity', {
        ...tradeParams,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: any) => ({
        ...prev,
        analysis: analysisResponse.data.data
      }));

      // Phase 2: Consensus
      setCurrentPhase(ExecutionPhase.CONSENSUS);
      const consensusResponse = await apiClient.post('/api/v1/ai-consensus/consensus-decision', {
        analysis_id: analysisResponse.data.data.id,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: any) => ({
        ...prev,
        consensus: consensusResponse.data.data
      }));

      // Phase 3: Validation
      setCurrentPhase(ExecutionPhase.VALIDATION);
      const validationResponse = await apiClient.post('/api/v1/ai-consensus/validate-trade', {
        consensus_id: consensusResponse.data.data.id,
        paperMode: isPaperMode
      });

      setPhaseDetails((prev: any) => ({
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
        ? '/api/v1/paper-trading/execute'
        : '/api/v1/trading/execute';

      const executionResponse = await apiClient.post(endpoint, {
        validation_id: validationResponse.data.data.id,
        ...tradeParams
      });

      setPhaseDetails((prev: any) => ({
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
  const handleChatTrade = async (tradeData: any) => {
    await executeTradeWithPhases(tradeData);
  };

  // Handle manual trade
  const handleManualTrade = async (tradeData: any) => {
    await executeTradeWithPhases({
      ...tradeData,
      source: 'manual'
    });
  };

  // Toggle autonomous mode
  const toggleAutonomousMode = async () => {
    try {
      const newState = !isAutonomousEnabled;
      
      const response = await apiClient.post('/api/v1/autonomous/toggle', {
        enabled: newState,
        paperMode: isPaperMode
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
      console.error('Failed to toggle autonomous mode:', error);
      toast({
        title: "Error",
        description: "Failed to change autonomous mode",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            AI Money Manager
          </h1>
          <p className="text-muted-foreground mt-1">
            Your intelligent trading companion with {isPaperMode ? 'paper' : 'real'} funds
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Paper Mode Toggle */}
          <PaperTradingToggle isCompact />

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
      </div>

      {/* Paper Mode Alert */}
      {isPaperMode && (
        <Alert className="border-blue-500 bg-blue-500/10">
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

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Conversational Interface & Trading Modes */}
        <div className="col-span-7">
          <Card className="h-full">
            <CardHeader>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="conversation" className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    AI Chat
                  </TabsTrigger>
                  <TabsTrigger value="manual" className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Manual
                  </TabsTrigger>
                  <TabsTrigger value="autonomous" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Auto Settings
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>

            <CardContent className="h-[600px] overflow-hidden">
              <AnimatePresence mode="wait">
                <TabsContent value="conversation" className="h-full mt-0">
                  <ConversationalTradingInterface
                    sessionId={sessionId}
                    isPaperMode={isPaperMode}
                    onExecuteTrade={handleChatTrade}
                    currentPhase={currentPhase}
                  />
                </TabsContent>

                <TabsContent value="manual" className="h-full mt-0">
                  <ManualTradingPanel
                    isPaperMode={isPaperMode}
                    onExecuteTrade={handleManualTrade}
                    isExecuting={isExecuting}
                    aiSuggestions={phaseDetails.analysis?.suggestions}
                  />
                </TabsContent>

                <TabsContent value="autonomous" className="h-full mt-0">
                  <AutonomousSettingsPanel
                    isPaperMode={isPaperMode}
                    isEnabled={isAutonomousEnabled}
                    onToggle={toggleAutonomousMode}
                  />
                </TabsContent>
              </AnimatePresence>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - 5-Phase Progress & Execution Details */}
        <div className="col-span-5 space-y-6">
          {/* 5-Phase Progress Visualizer */}
          <PhaseProgressVisualizer
            currentPhase={currentPhase}
            phaseDetails={phaseDetails}
            isPaperMode={isPaperMode}
            onOverride={(phase: any) => {
              console.log('Phase override:', phase);
              // Handle manual phase override if needed
            }}
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

          {/* Recent Executions */}
          {recentExecutions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Recent Trades
                </CardTitle>
              </CardHeader>
              <CardContent>
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
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIMoneyManager;