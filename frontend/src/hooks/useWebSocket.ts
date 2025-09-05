import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '@/store/authStore';

export interface WebSocketOptions {
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface WebSocketReturn {
  lastMessage: any;
  connectionStatus: 'Connecting' | 'Open' | 'Closing' | 'Closed';
  sendMessage: (message: any) => void;
  reconnect: () => void;
}

export const useWebSocket = (
  url: string,
  options: WebSocketOptions = {}
): WebSocketReturn => {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const [lastMessage, setLastMessage] = useState<any>(null);
  const [connectionStatus, setConnectionStatus] = useState<'Connecting' | 'Open' | 'Closing' | 'Closed'>('Connecting');
  
  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectCountRef = useRef(0);
  const skipNextReconnectRef = useRef(false);
  const { tokens } = useAuthStore();

  const connect = useCallback(() => {
    try {
      // Construct WebSocket URL - match current domain
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.host;
      const wsUrl = `${wsProtocol}//${wsHost}${url}`;
      
      // Use secure authentication via subprotocol instead of URL params
      const authProtocol = tokens?.access_token 
        ? [`Bearer.${tokens.access_token}`]
        : undefined;

      websocketRef.current = new WebSocket(wsUrl, authProtocol);
      
      websocketRef.current.onopen = () => {
        // Clear any pending reconnection timeouts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        setConnectionStatus('Open');
        reconnectCountRef.current = 0;
        onOpen?.();
      };

      websocketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          setLastMessage(event.data);
          onMessage?.(event.data);
        }
      };

      websocketRef.current.onclose = () => {
        // Clear any pending reconnection timeouts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        
        setConnectionStatus('Closed');
        onClose?.();

        // Attempt to reconnect unless we asked to skip (manual reconnect)
        if (!skipNextReconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          console.log(`WebSocket reconnection attempt ${reconnectCountRef.current}/${reconnectAttempts}`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setConnectionStatus('Connecting');
            connect();
          }, reconnectInterval);
        } else if (skipNextReconnectRef.current) {
          // Consume the skip flag once
          skipNextReconnectRef.current = false;
        }
      };

      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('Closed');
    }
  }, [url, tokens, onMessage, onOpen, onClose, onError, reconnectAttempts, reconnectInterval]);

  const sendMessage = useCallback((message: any) => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      const messageString = typeof message === 'string' ? message : JSON.stringify(message);
      websocketRef.current.send(messageString);
    } else {
      console.warn('WebSocket is not open. Cannot send message:', message);
    }
  }, []);

  const reconnect = useCallback(() => {
    // Set skip flag to prevent automatic reconnection when we manually close
    skipNextReconnectRef.current = true;
    reconnectCountRef.current = 0;
    
    // Clear any pending timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Close existing connection if open
    if (websocketRef.current && websocketRef.current.readyState !== WebSocket.CLOSED) {
      websocketRef.current.close();
    } else {
      // If already closed, connect immediately
      setConnectionStatus('Connecting');
      connect();
    }
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, [connect]);

  return {
    lastMessage,
    connectionStatus,
    sendMessage,
    reconnect,
  };
};