import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  Send,
  Bot,
  User,
  Loader,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Brain,
  Zap,
  RefreshCw,
  Maximize2,
  Minimize2,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Clock,
  DollarSign,
  BarChart3,
  Shield,
  Target
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { formatCurrency } from '@/lib/utils';
import { apiClient } from '@/lib/api/client';
import type { AxiosError } from 'axios';

interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant' | 'system' | 'trade_notification' | 'portfolio_update' | 'market_alert';
  timestamp: string;
  intent?: string;
  confidence?: number;
  metadata?: any;
}

interface ChatInterfaceProps {
  className?: string;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

interface StreamProgressEvent {
  stage: string;
  message: string;
  percent?: number;
  timestamp?: string;
}

interface OpportunitySummaryOpportunity {
  title: string;
  symbol?: string;
  risk_level?: string;
  timeframe?: string;
  confidence?: number;
  profit_potential?: number | null;
  required_capital?: number | null;
  entry_price?: number | null;
  exit_price?: number | null;
  entry_range?: string | null;
  target_range?: string | null;
  stop_range?: string | null;
  action_items?: string[];
  notes?: string[];
  discovered_at?: string;
}

interface OpportunitySummaryStrategy {
  name: string;
  opportunity_count: number;
  opportunities: OpportunitySummaryOpportunity[];
}

interface OpportunitySummary {
  scan_state?: string;
  message?: string;
  total_opportunities?: number;
  generated_at?: string;
  filtered_out?: number;
  strategies?: OpportunitySummaryStrategy[];
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  className = '',
  isExpanded = false,
  onToggleExpand
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Memoized sorted messages to prevent state mutation during render
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      // Primary: Compare timestamps
      const aTime = new Date(a.timestamp).getTime();
      const bTime = new Date(b.timestamp).getTime();
      if (aTime !== bTime) return aTime - bTime;

      // Tie-breaker 1: User messages come before others
      if (a.type === 'user' && b.type !== 'user') return -1;
      if (b.type === 'user' && a.type !== 'user') return 1;

      // Tie-breaker 2: Compare by id string
      return a.id.localeCompare(b.id);
    });
  }, [messages]);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fallbackTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingMessageRef = useRef<string | null>(null);
  const pendingRequestIdRef = useRef<string | null>(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isLoading) {
      scrollToBottom();
    }
  }, [isLoading, scrollToBottom]);

  const clearFallbackTimer = useCallback(() => {
    if (fallbackTimerRef.current) {
      clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearFallbackTimer();
    };
  }, [clearFallbackTimer]);

  const finalizePendingRequest = useCallback(() => {
    pendingMessageRef.current = null;
    pendingRequestIdRef.current = null;
    clearFallbackTimer();
    setIsLoading(false);
  }, [clearFallbackTimer]);

  const buildErrorMessage = useCallback((error: unknown): string => {
    if (typeof error === 'string') {
      return error;
    }

    if (error && typeof error === 'object') {
      const axiosError = error as AxiosError<any>;
      const detail = axiosError.response?.data?.detail;

      if (typeof detail === 'string' && detail.trim().length > 0) {
        return detail;
      }

      if (detail && typeof detail === 'object' && 'message' in detail) {
        const message = (detail as { message?: string }).message;
        if (message) {
          return message;
        }
      }

      if (axiosError.response?.data?.message) {
        return axiosError.response.data.message;
      }

      if ('message' in error && typeof (error as { message?: string }).message === 'string') {
        return (error as { message: string }).message;
      }
    }

    return 'The AI assistant could not complete that request. Please try again in a moment or contact support if the issue persists.';
  }, []);

  const pushSystemMessage = useCallback((content: string) => {
    const systemMessage: ChatMessage = {
      id: `system-${Date.now()}`,
      content,
      type: 'system',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, systemMessage]);
  }, []);

  // Initialize chat session
  useEffect(() => {
    initializeChatSession();
    // WebSocket cleanup is handled by the useWebSocket hook
  }, []);

  const initializeChatSession = async () => {
    try {
      // Create new chat session
      const response = await apiClient.post('/chat/session/new', {});

      if (response.data.success) {
        setSessionId(response.data.session_id);
        
        // Session created, WebSocket will connect automatically via hook
        
        // Add welcome message
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          content: `👋 Welcome to CryptoUniverse AI Money Manager!

I'm your comprehensive AI assistant for cryptocurrency portfolio management. I can help you with:

🔹 **Portfolio Analysis** - Review performance, allocation, and optimization
🔹 **Trade Execution** - Execute buy/sell orders with AI analysis  
🔹 **Risk Management** - Assess and mitigate portfolio risks
🔹 **Rebalancing** - Optimize your asset allocation
🔹 **Market Opportunities** - Discover new investment prospects
🔹 **Strategy Optimization** - Fine-tune your trading strategies

Just chat with me naturally! How can I help you manage your crypto investments today?`,
          type: 'assistant',
          timestamp: new Date().toISOString(),
          confidence: 1.0
        };
        
        setMessages([welcomeMessage]);
      }
    } catch (error) {
      // Failed to initialize chat session - handled by UI error state
      toast({
        title: 'Connection Error',
        description: 'Failed to initialize chat session. Please refresh the page.',
        variant: 'destructive',
      });
    }
  };

  const buildWebSocketUrl = useCallback((activeSessionId: string): string => {
    if (!activeSessionId) {
      return '';
    }

    const path = `/chat/ws/${activeSessionId}`;
    const baseURL = apiClient.defaults.baseURL;

    if (baseURL) {
      try {
        const parsed = new URL(baseURL, window.location.origin);
        const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
        const basePath = parsed.pathname.replace(/\/$/, '');
        return `${protocol}//${parsed.host}${basePath}${path}`;
      } catch (error) {
        console.error('Failed to build WebSocket URL from API base', error);
      }
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1${path}`;
  }, []);

  const websocketEndpoint = useMemo(() => (
    sessionId ? buildWebSocketUrl(sessionId) : ''
  ), [buildWebSocketUrl, sessionId]);

  // Use the shared WebSocket hook with proper authentication and reconnection
  const { lastMessage, connectionStatus, sendMessage: sendWsMessage } = useWebSocket(
    websocketEndpoint,
    {
      onOpen: () => {
        console.log('🔌 WebSocket connected for chat');
        setIsConnected(true);
      },
      onClose: () => {
        console.log('🔌 WebSocket disconnected for chat');
        setIsConnected(false);
      },
      onMessage: (data) => {
        console.log('📨 WebSocket message received:', data);
        if (data.type === 'chat_response') {
          clearFallbackTimer();

          const chunkPayload = (data && typeof data === 'object' && 'chunk' in data)
            ? (data.chunk as Record<string, any>)
            : undefined;
          const chunk = (chunkPayload && typeof chunkPayload === 'object') ? chunkPayload : data;
          const timestamp = (chunk && typeof chunk === 'object' && 'timestamp' in chunk)
            ? chunk.timestamp
            : data.timestamp;

          if (chunk && typeof chunk === 'object' && ('type' in chunk || 'content' in chunk || 'progress' in chunk)) {
            const chunkType = typeof chunk.type === 'string'
              ? chunk.type
              : (chunk.progress ? 'progress' : 'response');

            const normalizedTimestamp = typeof timestamp === 'string'
              ? timestamp
              : new Date().toISOString();

            const stagePercentDefaults: Record<string, number> = {
              thinking: 5,
              analyzing: 15,
              gathering_data: 25,
              processing: 45,
            };

            if (chunkType === 'processing' || chunkType === 'thinking' || chunkType === 'analyzing' || chunkType === 'gathering_data') {
              const message = typeof chunk.content === 'string' && chunk.content.trim().length > 0
                ? chunk.content
                : 'Processing your request...';
              const stage = typeof chunk.stage === 'string' && chunk.stage.trim().length > 0
                ? chunk.stage
                : chunkType;
              const defaultPercent = stagePercentDefaults[chunkType];
              const percentValue = typeof chunk.percent === 'number'
                ? chunk.percent
                : typeof chunk.progress?.percent === 'number'
                  ? chunk.progress.percent
                  : defaultPercent;
              handleProgressUpdate(message, percentValue, stage, normalizedTimestamp);
              return;
            }

            if (chunkType === 'progress') {
              const progressPayload = chunk.progress ?? {};
              const stage = typeof progressPayload.stage === 'string' && progressPayload.stage.trim().length > 0
                ? progressPayload.stage
                : (typeof chunk.stage === 'string' && chunk.stage.trim().length > 0
                  ? chunk.stage
                  : `stage-${Date.now()}`);
              const message = typeof progressPayload.message === 'string' && progressPayload.message.trim().length > 0
                ? progressPayload.message
                : (typeof chunk.content === 'string' && chunk.content.trim().length > 0
                  ? chunk.content
                  : 'Processing your request...');
              const percentValue = typeof progressPayload.percent === 'number'
                ? progressPayload.percent
                : undefined;
              handleProgressUpdate(message, percentValue, stage, normalizedTimestamp);
              return;
            }

            if (chunkType === 'response' || chunkType === 'chunk' || chunkType === 'persona_enriched') {
              const shouldReplaceContent = chunkType === 'persona_enriched' && Boolean(chunk.replaces_previous);
              if (typeof chunk.content === 'string') {
                if (shouldReplaceContent) {
                  streamingContentRef.current = chunk.content;
                } else {
                  streamingContentRef.current = `${streamingContentRef.current}${chunk.content}`;
                }
              }

              updateStreamingMessage(prev => ({
                ...prev,
                content: streamingContentRef.current || prev.content,
                metadata: {
                  ...(prev.metadata || {}),
                  ...(chunk.metadata || {}),
                  streaming: true,
                  personality: chunk.personality ?? prev.metadata?.personality,
                  persona_enriched: chunkType === 'persona_enriched' ? true : prev.metadata?.persona_enriched,
                },
                timestamp: normalizedTimestamp,
              }));

              setStreamProgress('Generating a detailed response...');
              setStreamProgressPercent(prev => (prev >= 70 ? prev : 70));
              return;
            }

            if (chunkType === 'action_required') {
              const content = typeof chunk.content === 'string' && chunk.content.trim().length > 0
                ? chunk.content
                : 'This action requires your confirmation. Would you like to proceed?';
              const actionMessage: ChatMessage = {
                id: chunk.decision_id ? `action-${chunk.decision_id}` : `action-${Date.now()}`,
                content,
                type: 'system',
                timestamp: normalizedTimestamp,
                metadata: {
                  ...(chunk.metadata || {}),
                  action: chunk.action,
                  decision_id: chunk.decision_id,
                },
              };
              setMessages(prev => [...prev, actionMessage]);
              setStreamProgress(content);
              setStreamProgressPercent(prev => (prev >= 85 ? prev : 85));
              return;
            }

            if (chunkType === 'error') {
              const errorMessage = typeof chunk.content === 'string' && chunk.content.trim().length > 0
                ? chunk.content
                : typeof chunk.error === 'string' && chunk.error.trim().length > 0
                  ? chunk.error
                  : 'An error occurred while processing your request. Please try again.';

              if (currentStreamingMessageId) {
                setMessages(prev => prev.filter(msg => msg.id !== currentStreamingMessageId));
              }

              finalizePendingRequest();
              setStreamProgress(null);
              setStreamProgressPercent(0);
              setCurrentStreamingMessageId(null);
              progressEventsRef.current = [];
              setProgressEvents([]);
              streamingContentRef.current = '';

              pushSystemMessage(errorMessage);
              toast({
                title: 'Message Failed',
                description: errorMessage,
                variant: 'destructive',
              });
              return;
            }

            if (chunkType === 'complete') {
              finalizeStreamingMessage(chunk, data);
              return;
            }

            // Fallback for any other chunk types with content
            if (typeof chunk.content === 'string' && chunk.content.trim().length > 0) {
              streamingContentRef.current = `${streamingContentRef.current}${chunk.content}`;
              updateStreamingMessage(prev => ({
                ...prev,
                content: streamingContentRef.current,
                metadata: {
                  ...(prev.metadata || {}),
                  streaming: true,
                },
                timestamp: normalizedTimestamp,
              }));
              setStreamProgress('Generating a detailed response...');
              setStreamProgressPercent(prev => (prev >= 70 ? prev : 70));
              return;
            }

            // If we reach here and received an unknown chunk type, log for debugging
            console.debug('Unhandled chat chunk', chunk);
            return;
          }

          // Non-chunk payloads fallback to treating as complete assistant message
          const fallbackMessage: ChatMessage = {
            id: data.message_id || `assistant-${Date.now()}`,
            content: typeof data.content === 'string' ? data.content : '',
            type: 'assistant',
            timestamp: typeof data.timestamp === 'string' ? data.timestamp : new Date().toISOString(),
            intent: data.intent,
            confidence: data.confidence,
            metadata: data.metadata,
          };

          if (currentStreamingMessageId) {
            streamingContentRef.current = fallbackMessage.content;
            updateStreamingMessage(prev => ({
              ...fallbackMessage,
              id: prev.id,
              metadata: {
                ...(fallbackMessage.metadata || {}),
                streaming: false,
                progress_updates: progressEventsRef.current,
              },
            }));
          } else {
            setMessages(prev => [...prev, fallbackMessage]);
          }

          finalizeStreamingMessage(data, data);
        } else if (data.type === 'connection_established') {
          // Chat connection established
        }
      },
      onError: () => {
        setIsConnected(false);
      },
      reconnectAttempts: 3,
      reconnectInterval: 2000
    }
  );

  // Update connection status based on WebSocket hook
  useEffect(() => {
    setIsConnected(connectionStatus === 'Open');
  }, [connectionStatus]);

  // State for streaming progress
  const [streamProgress, setStreamProgress] = useState<string | null>(null);
  const [streamProgressPercent, setStreamProgressPercent] = useState<number>(0);
  const [progressEvents, setProgressEvents] = useState<StreamProgressEvent[]>([]);
  const [currentStreamingMessageId, setCurrentStreamingMessageId] = useState<string | null>(null);
  const progressEventsRef = useRef<StreamProgressEvent[]>([]);
  const streamingContentRef = useRef<string>('');

  const mergeProgressEvents = useCallback(
    (existing: StreamProgressEvent[] = [], update: StreamProgressEvent): StreamProgressEvent[] => {
      const list = Array.isArray(existing) ? [...existing] : [];
      const index = list.findIndex((item) => item.stage === update.stage);
      if (index >= 0) {
        list[index] = { ...list[index], ...update };
        return list;
      }
      return [...list, update];
    },
    []
  );

  const pushProgressEvent = useCallback(
    (update: StreamProgressEvent) => {
      const merged = mergeProgressEvents(progressEventsRef.current, update);
      progressEventsRef.current = merged;
      setProgressEvents(merged);

      if (!currentStreamingMessageId) {
        return;
      }

      setMessages(prev => prev.map(msg => {
        if (msg.id !== currentStreamingMessageId) {
          return msg;
        }

        const existingUpdates = Array.isArray(msg.metadata?.progress_updates)
          ? (msg.metadata.progress_updates as StreamProgressEvent[])
          : [];

        return {
          ...msg,
          metadata: {
            ...(msg.metadata || {}),
            progress_updates: mergeProgressEvents(existingUpdates, update),
          },
        };
      }));
    },
    [currentStreamingMessageId, mergeProgressEvents, setMessages]
  );

  const updateStreamingMessage = useCallback(
    (updater: (prev: ChatMessage) => ChatMessage) => {
      if (!currentStreamingMessageId) {
        return;
      }
      setMessages(prev => prev.map(msg => (
        msg.id === currentStreamingMessageId ? updater(msg) : msg
      )));
    },
    [currentStreamingMessageId]
  );

  const handleProgressUpdate = useCallback(
    (
      message: string,
      percent: number | undefined,
      stage: string,
      timestamp?: string,
    ) => {
      const progressTimestamp = timestamp ?? new Date().toISOString();
      setStreamProgress(message);

      const event: StreamProgressEvent = {
        stage,
        message,
        timestamp: progressTimestamp,
      };

      if (typeof percent === 'number' && !Number.isNaN(percent)) {
        const bounded = Math.max(0, Math.min(100, Math.round(percent)));
        event.percent = bounded;
        setStreamProgressPercent(prev => (prev >= bounded ? prev : bounded));
      }

      pushProgressEvent(event);

      updateStreamingMessage(prev => ({
        ...prev,
        metadata: {
          ...(prev.metadata || {}),
          streaming: true,
        },
      }));
    },
    [pushProgressEvent, setStreamProgress, setStreamProgressPercent, updateStreamingMessage]
  );

  const finalizeStreamingMessage = useCallback(
    (finalChunk?: any, envelope?: any) => {
      const resolvedTimestamp = typeof finalChunk?.timestamp === 'string'
        ? finalChunk.timestamp
        : typeof envelope?.timestamp === 'string'
          ? envelope.timestamp
          : new Date().toISOString();

      if (currentStreamingMessageId) {
        updateStreamingMessage(prev => {
          const mergedMetadata = {
            ...(prev.metadata || {}),
            ...(finalChunk?.metadata || {}),
            streaming: false,
            progress_updates: progressEventsRef.current,
          } as Record<string, any>;

          if (finalChunk?.context) {
            mergedMetadata.context = finalChunk.context;
          }

          return {
            ...prev,
            content: streamingContentRef.current || (typeof finalChunk?.content === 'string' ? finalChunk.content : prev.content),
            intent: finalChunk?.intent ?? prev.intent,
            confidence: typeof finalChunk?.confidence === 'number' ? finalChunk.confidence : prev.confidence,
            metadata: mergedMetadata,
            timestamp: resolvedTimestamp,
          };
        });
      }

      finalizePendingRequest();
      setStreamProgress(null);
      setStreamProgressPercent(0);
      setCurrentStreamingMessageId(null);
      progressEventsRef.current = [];
      setProgressEvents([]);
      streamingContentRef.current = '';
    },
    [
      currentStreamingMessageId,
      finalizePendingRequest,
      setCurrentStreamingMessageId,
      setProgressEvents,
      setStreamProgress,
      setStreamProgressPercent,
      updateStreamingMessage,
    ]
  );

  const sendRestMessage = useCallback(async (
    messageToSend: string,
    requestId: string,
    placeholderId: string
  ) => {
    if (!sessionId) {
      return;
    }

    try {
      const response = await apiClient.post('/chat/message', {
        message: messageToSend,
        session_id: sessionId,
        mode: 'trading',
      });

      if (response.data?.success) {
        const assistantMessage: ChatMessage = {
          id: response.data.message_id,
          content: response.data.content,
          type: 'assistant',
          timestamp: response.data.timestamp || new Date().toISOString(),
          intent: response.data.intent,
          confidence: response.data.confidence,
          metadata: response.data.metadata,
        };

        setMessages(prev => {
          const hasPlaceholder = prev.some(msg => msg.id === placeholderId);
          if (hasPlaceholder) {
            return prev.map(msg =>
              msg.id === placeholderId ? { ...assistantMessage, id: msg.id } : msg
            );
          }
          return [...prev, assistantMessage];
        });
      } else {
        throw new Error(response.data?.detail || 'Chat service unavailable');
      }
    } catch (error) {
      const friendlyMessage = buildErrorMessage(error);
      setMessages(prev => prev.filter(msg => msg.id !== placeholderId));
      pushSystemMessage(friendlyMessage);
      toast({
        title: 'Message Failed',
        description: friendlyMessage,
        variant: 'destructive',
      });
    } finally {
      finalizePendingRequest();
      setStreamProgress(null);
      setStreamProgressPercent(0);
      setCurrentStreamingMessageId(null);
      progressEventsRef.current = [];
      setProgressEvents([]);
      streamingContentRef.current = '';
    }
  }, [
    buildErrorMessage,
    finalizePendingRequest,
    setMessages,
    pushSystemMessage,
    sessionId,
    toast,
  ]);

  const sendMessage = useCallback(async () => {
    const messageToSend = inputValue.trim();
    if (!messageToSend || isLoading || !sessionId) {
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: messageToSend,
      type: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setStreamProgress('Processing your request...');
    setStreamProgressPercent(10);
    progressEventsRef.current = [];
    setProgressEvents([]);

    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const placeholderId = `assistant-${requestId}`;
    const placeholderMessage: ChatMessage = {
      id: placeholderId,
      content: '🤖 The AI assistant is preparing a detailed response...',
      type: 'assistant',
      timestamp: new Date().toISOString(),
      metadata: { streaming: true },
    };

    setMessages(prev => [...prev, placeholderMessage]);
    setCurrentStreamingMessageId(placeholderId);
    pendingMessageRef.current = messageToSend;
    pendingRequestIdRef.current = requestId;
    streamingContentRef.current = '';

    const invokeRest = async () => {
      await sendRestMessage(messageToSend, requestId, placeholderId);
    };

    try {
      if (isConnected) {
        sendWsMessage({
          type: 'chat_message',
          message: messageToSend,
          session_id: sessionId,
          request_id: requestId,
        });

        fallbackTimerRef.current = setTimeout(() => {
          if (pendingRequestIdRef.current === requestId) {
            void invokeRest();
          }
        }, 8000);
      } else {
        await invokeRest();
      }
    } catch (error) {
      clearFallbackTimer();
      setMessages(prev => prev.filter(msg => msg.id !== placeholderId));
      const friendlyMessage = buildErrorMessage(error);
      pushSystemMessage(friendlyMessage);
      toast({
        title: 'Message Failed',
        description: friendlyMessage,
        variant: 'destructive',
      });
      setStreamProgress(null);
      setStreamProgressPercent(0);
      setCurrentStreamingMessageId(null);
      progressEventsRef.current = [];
      setProgressEvents([]);
      setIsLoading(false);
      pendingMessageRef.current = null;
      pendingRequestIdRef.current = null;
      streamingContentRef.current = '';
    }
  }, [
    buildErrorMessage,
    clearFallbackTimer,
    inputValue,
    isConnected,
    isLoading,
    sendRestMessage,
    sendWsMessage,
    sessionId,
    setMessages,
    toast,
  ]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getMessageIcon = (type: string, intent?: string) => {
    switch (type) {
      case 'user':
        return <User className="h-4 w-4" />;
      case 'assistant':
        switch (intent) {
          case 'trade_execution':
            return <TrendingUp className="h-4 w-4 text-green-500" />;
          case 'risk_assessment':
            return <Shield className="h-4 w-4 text-yellow-500" />;
          case 'portfolio_analysis':
            return <BarChart3 className="h-4 w-4 text-blue-500" />;
          case 'emergency_command':
            return <AlertTriangle className="h-4 w-4 text-red-500" />;
          default:
            return <Bot className="h-4 w-4 text-primary" />;
        }
      case 'trade_notification':
        return <DollarSign className="h-4 w-4 text-green-500" />;
      case 'portfolio_update':
        return <BarChart3 className="h-4 w-4 text-blue-500" />;
      case 'market_alert':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      default:
        return <Brain className="h-4 w-4" />;
    }
  };

  const getConfidenceBadge = (confidence?: number) => {
    if (!confidence) return null;
    
    const getVariant = (score: number) => {
      if (score >= 0.9) return 'default';
      if (score >= 0.7) return 'secondary';
      return 'outline';
    };

    const getColor = (score: number) => {
      if (score >= 0.9) return 'text-green-500';
      if (score >= 0.7) return 'text-yellow-500';
      return 'text-red-500';
    };

    return (
      <Badge variant={getVariant(confidence)} className={`text-xs ${getColor(confidence)}`}>
        {(confidence * 100).toFixed(0)}% confidence
      </Badge>
    );
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied',
      description: 'Message copied to clipboard',
    });
  };

  const formatMessageContent = (content: string, metadata?: any) => {
    // Handle special formatting for different message types
    if (metadata?.trade_params) {
      return (
        <div className="space-y-3">
          <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          {metadata.requires_confirmation && (
            <div className="flex gap-2 mt-4">
              <Button size="sm" className="bg-green-600 hover:bg-green-700">
                ✅ Execute Trade
              </Button>
              <Button size="sm" variant="outline">
                📋 More Details
              </Button>
              <Button size="sm" variant="outline">
                ❌ Cancel
              </Button>
            </div>
          )}
        </div>
      );
    }

    if (metadata?.emergency_mode) {
      return (
        <div className="space-y-3">
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          </div>
          {metadata.available_actions && (
            <div className="grid grid-cols-2 gap-2 mt-4">
              {metadata.available_actions.map((action: string) => (
                <Button key={action} size="sm" variant="outline" className="text-xs">
                  {action.replace('_', ' ').toUpperCase()}
                </Button>
              ))}
            </div>
          )}
        </div>
      );
    }

    const opportunitySummary = metadata?.opportunity_summary || metadata?.opportunitySummary;
    if (opportunitySummary) {
      return (
        <div className="space-y-4">
          {content && (
            <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          )}
          {renderOpportunitySummary(opportunitySummary as OpportunitySummary)}
        </div>
      );
    }

    // Default formatting with line breaks
    return <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />;
  };

  const renderOpportunitySummary = (summary: OpportunitySummary) => {
    if (!summary) return null;
    const strategies = summary.strategies || [];

    return (
      <div className="space-y-4 border border-primary/20 bg-primary/5 rounded-lg p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            <span className="font-semibold text-sm">Opportunity scan</span>
          </div>
          <Badge variant="outline" className="text-xs capitalize">
            {summary.scan_state ? summary.scan_state.replace(/_/g, ' ') : 'in progress'}
          </Badge>
        </div>
        {summary.message && (
          <p className="text-xs text-muted-foreground">{summary.message}</p>
        )}
        {typeof summary.filtered_out === 'number' && summary.filtered_out > 0 && (
          <p className="text-xs text-muted-foreground">
            Filtered out {summary.filtered_out} ideas that did not match your profile.
          </p>
        )}

        {strategies.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            No actionable opportunities were returned from this scan.
          </div>
        ) : (
          <div className="space-y-3">
            {strategies.map((strategy) => {
              const strategyOpportunities = strategy.opportunities || [];
              return (
                <div
                  key={strategy.name}
                  className="rounded-lg border border-primary/15 bg-background p-3 space-y-3"
                >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-primary" />
                    <span className="font-semibold text-sm">{strategy.name}</span>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {strategy.opportunity_count ?? strategy.opportunities.length} opportunities
                  </Badge>
                </div>

                <div className="space-y-3">
                  {strategyOpportunities.map((opportunity, index) => (
                    <div
                      key={`${strategy.name}-${index}`}
                      className="rounded-md border border-primary/10 bg-primary/5 p-3 space-y-2"
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div className="space-y-1">
                          <p className="text-sm font-medium">{opportunity.title}</p>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            {opportunity.symbol && (
                              <span className="font-semibold text-foreground">{opportunity.symbol}</span>
                            )}
                            {opportunity.risk_level && (
                              <span>• {opportunity.risk_level.toUpperCase()}</span>
                            )}
                            {opportunity.timeframe && <span>• {opportunity.timeframe}</span>}
                          </div>
                        </div>
                        {typeof opportunity.confidence === 'number' && (
                          <Badge className={opportunity.confidence >= 75 ? 'bg-green-600' : 'bg-amber-500'}>
                            {opportunity.confidence.toFixed(0)}% confidence
                          </Badge>
                        )}
                      </div>

                      <div className="grid gap-2 sm:grid-cols-2 text-xs text-muted-foreground">
                        {typeof opportunity.profit_potential === 'number' && (
                          <div className="flex items-center gap-1 text-green-600">
                            <DollarSign className="h-3 w-3" />
                            <span>Potential {formatCurrency(opportunity.profit_potential)}</span>
                          </div>
                        )}
                        {typeof opportunity.required_capital === 'number' && (
                          <div>Capital {formatCurrency(opportunity.required_capital)}</div>
                        )}
                        {opportunity.entry_range && <div>Entry range: {opportunity.entry_range}</div>}
                        {typeof opportunity.entry_price === 'number' && !opportunity.entry_range && (
                          <div>Entry price: {formatCurrency(opportunity.entry_price)}</div>
                        )}
                        {opportunity.target_range && <div>Targets: {opportunity.target_range}</div>}
                        {typeof opportunity.exit_price === 'number' && !opportunity.target_range && (
                          <div>Target price: {formatCurrency(opportunity.exit_price)}</div>
                        )}
                        {opportunity.stop_range && <div>Stops: {opportunity.stop_range}</div>}
                      </div>

                      {opportunity.action_items && opportunity.action_items.length > 0 && (
                        <div className="space-y-1 text-sm text-foreground">
                          {opportunity.action_items.map((item, actionIndex) => (
                            <div key={actionIndex} className="flex items-start gap-2">
                              <CheckCircle className="h-3 w-3 text-primary mt-0.5" />
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {opportunity.notes && opportunity.notes.length > 0 && (
                        <div className="text-xs text-muted-foreground space-y-1">
                          {opportunity.notes.map((note, noteIndex) => (
                            <p key={noteIndex}>• {note}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">AI Money Manager</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-xs text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => initializeChatSession()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          {onToggleExpand && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleExpand}
            >
              {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6">
          <div className="space-y-4 py-4">
            <AnimatePresence>
              {sortedMessages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type !== 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      {getMessageIcon(message.type, message.intent)}
                    </div>
                  )}
                  
                  <div className={`max-w-[80%] ${message.type === 'user' ? 'order-1' : 'order-2'}`}>
                    <div
                      className={`rounded-lg px-4 py-3 ${
                        message.type === 'user'
                          ? 'bg-primary text-primary-foreground ml-auto'
                          : 'bg-muted'
                      }`}
                    >
                      <div className="text-sm space-y-3">
                        {message.metadata?.admin_access && (
                          <Badge variant="secondary" className="text-[0.6rem] uppercase tracking-wide">
                            Admin strategy access
                          </Badge>
                        )}
                        {formatMessageContent(message.content, message.metadata)}
                      </div>

                      <div className="flex items-center justify-between mt-2 gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </span>
                          {message.intent && (
                            <Badge variant="outline" className="text-xs">
                              {message.intent.replace('_', ' ')}
                            </Badge>
                          )}
                          {getConfidenceBadge(message.confidence)}
                        </div>
                        
                        {message.type === 'assistant' && (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(message.content)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                            >
                              <ThumbsUp className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                            >
                              <ThumbsDown className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {message.type === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center order-2">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Loader className="h-4 w-4 animate-spin text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-3 min-w-[220px] space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {streamProgress || 'AI is thinking...'}
                    </span>
                  </div>
                  {(progressEvents.length > 0 || streamProgressPercent > 0) && (
                    <div className="space-y-2">
                      <div className="h-1.5 bg-primary/20 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${Math.max(0, Math.min(streamProgressPercent ?? 0, 100))}%` }}
                        />
                      </div>
                      <ul className="space-y-1 text-[0.7rem] text-muted-foreground">
                        {progressEvents.map((event) => (
                          <li key={event.stage} className="flex items-center justify-between gap-2">
                            <span className="truncate" title={event.message}>
                              {event.message}
                            </span>
                            {typeof event.percent === 'number' && (
                              <span className="text-foreground font-medium">{event.percent}%</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <Separator />

        {/* Input Area */}
        <div className="p-4">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me about your portfolio, trading, or market opportunities..."
                disabled={isLoading}
                className="pr-12"
              />
              {inputValue && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-8 w-8 p-0"
                  onClick={() => setInputValue('')}
                >
                  ×
                </Button>
              )}
            </div>
            
            <Button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="gap-2"
            >
              {isLoading ? (
                <>
                  <Loader className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Sending…</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span className="text-sm">Send</span>
                </>
              )}
            </Button>
          </div>
          
          {/* Quick Action Buttons */}
          <div className="flex flex-wrap gap-2 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Show me my portfolio performance')}
              disabled={isLoading}
              className="text-xs"
            >
              📊 Portfolio
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('What are the best opportunities right now?')}
              disabled={isLoading}
              className="text-xs"
            >
              🔍 Opportunities
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Analyze the risk in my current positions')}
              disabled={isLoading}
              className="text-xs"
            >
              🛡️ Risk Analysis
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Should I rebalance my portfolio?')}
              disabled={isLoading}
              className="text-xs"
            >
              ⚖️ Rebalance
            </Button>
          </div>
          
          {!isConnected && (
            <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Connection lost. Messages will be sent via API.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ChatInterface;