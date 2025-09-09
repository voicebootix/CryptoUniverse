/**
 * Trading API Adapter Layer
 * Maps frontend calls to existing backend endpoints
 */

import { apiClient } from './client';
import { 
  API_ENDPOINTS, 
  WS_EVENTS, 
  TIMEOUTS 
} from '@/constants/trading';
import {
  ApiResponse,
  PaperTradingStats,
  UserPreferences,
  TradeExecutionRequest,
  TradeExecutionResponse,
  AIConsensusResult,
} from '@/types/trading';
import { ConversationMemory } from '@/constants/trading';
import { mapTradeExecutionResponse } from '@/lib/utils/typeMappers';

// Paper Trading API
export const paperTradingApi = {
  async getStats(): Promise<PaperTradingStats> {
    try {
      const response = await apiClient.get<ApiResponse<PaperTradingStats>>(
        API_ENDPOINTS.PAPER_TRADING_STATS
      );
      return response.data.data || {
        totalTrades: 0,
        winRate: 0,
        totalProfit: 0,
        bestTrade: 0,
        worstTrade: 0,
        readyForLive: false
      };
    } catch (error) {
      console.error('Failed to fetch paper trading stats:', error);
      // Return default stats for new users
      return {
        totalTrades: 0,
        winRate: 0,
        totalProfit: 0,
        bestTrade: 0,
        worstTrade: 0,
        readyForLive: false
      };
    }
  },

  async getTradingMode(): Promise<{ isPaperTrading: boolean }> {
    try {
      const response = await apiClient.get<ApiResponse<UserPreferences>>(
        API_ENDPOINTS.USER_PREFERENCES
      );
      return {
        isPaperTrading: response.data.data?.paper_trading_enabled !== false
      };
    } catch (error) {
      console.error('Failed to fetch trading mode:', error);
      // Default to paper trading for safety
      return { isPaperTrading: true };
    }
  },

  async setTradingMode(isPaperTrading: boolean): Promise<UserPreferences> {
    try {
      const response = await apiClient.patch<ApiResponse<UserPreferences>>(
        API_ENDPOINTS.USER_PREFERENCES,
        { paper_trading_enabled: isPaperTrading }
      );
      if (!response.data.success) {
        throw new Error(response.data.error || 'Failed to update trading mode');
      }
      return response.data.data!;
    } catch (error) {
      console.error('Failed to update trading mode:', error);
      throw error;
    }
  }
};

// Conversational Trading API
export const conversationalTradingApi = {
  async sendMessage(
    message: string, 
    personality: string, 
    isPaperTrading: boolean, 
    memory?: ConversationMemory | null
  ) {
    try {
      const response = await apiClient.post(
        API_ENDPOINTS.CHAT_MESSAGE,
        {
          message,
          session_id: memory?.sessionId,
          metadata: {
            personality,
            isPaperTrading,
            mode: 'conversational_trading',
            context: memory?.context
          }
        },
        { timeout: TIMEOUTS.API_REQUEST }
      );
      
      // Transform response to expected format
      return {
        type: WS_EVENTS.CHAT_RESPONSE,
        content: response.data.content || response.data.message,
        metadata: response.data.metadata,
        phase: response.data.metadata?.phase,
        proposal: response.data.metadata?.trade_proposal,
        intent: response.data.intent,
        confidence: response.data.confidence
      };
    } catch (error) {
      console.error('Failed to send conversational message:', error);
      throw error;
    }
  },

  async getMemory(): Promise<{ memory: ConversationMemory | null }> {
    try {
      // Just get sessions - simpler approach
      const historyRes = await apiClient.get(API_ENDPOINTS.CHAT_SESSIONS);
      
      // Return basic memory structure for new users
      return {
        memory: {
          sessionId: '',
          context: {},
          preferences: {},
          lastActivity: new Date().toISOString(),
          trustScore: 50, // Default trust score
          totalProfit: 0
        }
      };
    } catch (error) {
      console.error('Failed to fetch conversation memory:', error);
      // Return default for new users
      return {
        memory: {
          sessionId: '',
          context: {},
          preferences: {},
          lastActivity: new Date().toISOString(),
          trustScore: 50,
          totalProfit: 0
        }
      };
    }
  },

  async executeTrade(
    proposal: TradeExecutionRequest, 
    isPaperTrading: boolean
  ): Promise<TradeExecutionResponse> {
    try {
      const endpoint = isPaperTrading 
        ? API_ENDPOINTS.PAPER_TRADING_EXECUTE
        : API_ENDPOINTS.TRADE_EXECUTE;
      
      const response = await apiClient.post<ApiResponse<TradeExecutionResponse>>(
        endpoint,
        {
          action: proposal.action,
          symbol: proposal.symbol,
          amount: proposal.amount,
          price: proposal.price,
          order_type: proposal.order_type || 'market',
          stop_loss: proposal.stop_loss,
          take_profit: proposal.take_profit,
          metadata: proposal.metadata
        },
        { timeout: TIMEOUTS.API_REQUEST }
      );
      
      if (!response.data.success) {
        throw new Error(response.data.error || 'Trade execution failed');
      }
      
      // Map DTO to frontend type if needed
      const responseData = response.data.data!;
      // Check if it's in DTO format (snake_case) vs frontend format (camelCase)
      return 'trade_id' in responseData 
        ? mapTradeExecutionResponse(responseData as any) 
        : responseData;
    } catch (error: any) {
      console.error('Trade execution failed:', error);
      return {
        success: false,
        tradeId: '',
        action: proposal.action,
        symbol: proposal.symbol,
        amount: proposal.amount,
        price: 0,
        fees: 0,
        timestamp: new Date().toISOString(),
        status: 'failed',
        error: error.response?.data?.detail || error.message || 'Trade execution failed'
      };
    }
  }
};

// WebSocket connection helper
export const getWebSocketUrl = (path: string) => {
  // Use environment variable for WebSocket URL
  const wsBase = import.meta.env.VITE_WS_URL;
  
  if (wsBase) {
    return `${wsBase}${path}`;
  }
  
  // Fallback to constructing from API URL
  const apiUrl = import.meta.env.VITE_API_URL || '';
  if (apiUrl) {
    const wsUrl = apiUrl
      .replace('https://', 'wss://')
      .replace('http://', 'ws://')
      .replace('/api/v1', '');
    return `${wsUrl}/api/v1${path}`;
  }
  
  // Last resort - use current host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/v1${path}`;
};