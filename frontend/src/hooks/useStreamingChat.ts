/**
 * React Hook for Streaming Chat Messages
 * 
 * Provides streaming chat functionality with progress updates
 * and automatic fallback to regular API on connection issues.
 */

import { useState, useCallback, useRef } from 'react';
import { streamChatMessage, sendChatMessage, type ChatMessage } from '@/services/chatService';

export interface StreamProgress {
  stage: string;
  message: string;
  percent?: number;
}

export interface UseStreamingChatOptions {
  sessionId: string;
  conversationMode?: string;
  enableStreaming?: boolean;
  onMessage?: (message: ChatMessage) => void;
  onError?: (error: string) => void;
}

export interface UseStreamingChatReturn {
  sendMessage: (message: string) => Promise<void>;
  isStreaming: boolean;
  streamProgress: StreamProgress | null;
  currentStreamContent: string;
  cancelStream: () => void;
}

/**
 * Hook for streaming chat messages with SSE
 */
export function useStreamingChat({
  sessionId,
  conversationMode = 'live_trading',
  enableStreaming = true,
  onMessage,
  onError
}: UseStreamingChatOptions): UseStreamingChatReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamProgress, setStreamProgress] = useState<StreamProgress | null>(null);
  const [currentStreamContent, setCurrentStreamContent] = useState('');
  
  const abortStreamRef = useRef<(() => void) | null>(null);
  const streamTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const cancelStream = useCallback(() => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
    }
    
    if (streamTimeoutRef.current) {
      clearTimeout(streamTimeoutRef.current);
      streamTimeoutRef.current = null;
    }
    
    setIsStreaming(false);
    setStreamProgress(null);
    setCurrentStreamContent('');
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (isStreaming) {
      console.warn('Already streaming a message');
      return;
    }

    setIsStreaming(true);
    setStreamProgress({ stage: 'initializing', message: 'Connecting...' });
    setCurrentStreamContent('');

    // If streaming is disabled or not supported, use regular API
    if (!enableStreaming || typeof EventSource === 'undefined') {
      try {
        const response = await sendChatMessage(message, sessionId, conversationMode);
        
        if (response.success) {
          const assistantMessage: ChatMessage = {
            id: response.message_id,
            content: response.content,
            type: 'assistant',
            timestamp: response.timestamp,
            intent: response.intent,
            confidence: response.confidence,
            metadata: response.metadata
          };
          
          if (onMessage) {
            onMessage(assistantMessage);
          }
        }
      } catch (error: any) {
        const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to send message';
        if (onError) {
          onError(errorMessage);
        }
      } finally {
        setIsStreaming(false);
        setStreamProgress(null);
      }
      return;
    }

    // Use streaming with timeout fallback
    let streamCompleted = false;
    let fullContent = '';

    // Set timeout to fallback to regular API if streaming takes too long
    streamTimeoutRef.current = setTimeout(async () => {
      if (streamCompleted) return;
      
      console.warn('Streaming timeout, falling back to regular API');
      cancelStream();
      
      try {
        const response = await sendChatMessage(message, sessionId, conversationMode);
        
        if (response.success) {
          const assistantMessage: ChatMessage = {
            id: response.message_id,
            content: response.content,
            type: 'assistant',
            timestamp: response.timestamp,
            intent: response.intent,
            confidence: response.confidence,
            metadata: response.metadata
          };
          
          if (onMessage) {
            onMessage(assistantMessage);
          }
        }
      } catch (error: any) {
        const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to send message';
        if (onError) {
          onError(errorMessage);
        }
      }
    }, 120000); // 120 second timeout

    try {
      abortStreamRef.current = streamChatMessage(
        message,
        sessionId,
        conversationMode,
        // onChunk
        (chunk: string) => {
          fullContent += chunk;
          setCurrentStreamContent(fullContent);
        },
        // onProgress
        (progress: StreamProgress) => {
          setStreamProgress(progress);
        },
        // onComplete
        (finalContent: string) => {
          streamCompleted = true;
          
          if (streamTimeoutRef.current) {
            clearTimeout(streamTimeoutRef.current);
            streamTimeoutRef.current = null;
          }
          
          const assistantMessage: ChatMessage = {
            id: `stream-${Date.now()}`,
            content: finalContent,
            type: 'assistant',
            timestamp: new Date().toISOString(),
            metadata: { streamed: true }
          };
          
          if (onMessage) {
            onMessage(assistantMessage);
          }
          
          setIsStreaming(false);
          setStreamProgress(null);
          setCurrentStreamContent('');
          abortStreamRef.current = null;
        },
        // onError
        (error: string) => {
          streamCompleted = true;
          
          if (streamTimeoutRef.current) {
            clearTimeout(streamTimeoutRef.current);
            streamTimeoutRef.current = null;
          }
          
          if (onError) {
            onError(error);
          }
          
          setIsStreaming(false);
          setStreamProgress(null);
          setCurrentStreamContent('');
          abortStreamRef.current = null;
        }
      );
    } catch (error: any) {
      streamCompleted = true;
      
      if (streamTimeoutRef.current) {
        clearTimeout(streamTimeoutRef.current);
        streamTimeoutRef.current = null;
      }
      
      const errorMessage = error?.message || 'Failed to start streaming';
      if (onError) {
        onError(errorMessage);
      }
      
      setIsStreaming(false);
      setStreamProgress(null);
      setCurrentStreamContent('');
    }
  }, [isStreaming, sessionId, conversationMode, enableStreaming, onMessage, onError, cancelStream]);

  return {
    sendMessage,
    isStreaming,
    streamProgress,
    currentStreamContent,
    cancelStream
  };
}
