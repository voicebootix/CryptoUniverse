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
      // Prevent double connections
      if (websocketRef.current && (
        websocketRef.current.readyState === WebSocket.CONNECTING ||
        websocketRef.current.readyState === WebSocket.OPEN
      )) {
        return;
      }

      // Clean up existing connection if present
      if (websocketRef.current) {
        // Set flag on existing socket to skip reconnection logic when it closes
        (websocketRef.current as any)._skipReconnect = true;
        websocketRef.current.close();
      }

      // Construct WebSocket URL with robust URL constructor
      let wsUrl: string;
      
      try {
        if (import.meta.env.VITE_WS_URL) {
          // Use environment-specified WebSocket URL with URL constructor
          const baseWsUrl = new URL(import.meta.env.VITE_WS_URL);
          baseWsUrl.pathname = url;
          wsUrl = baseWsUrl.toString();
        } else {
          // Build from current location using URL constructor
          const currentUrl = new URL(window.location.href);
          currentUrl.protocol = currentUrl.protocol === 'https:' ? 'wss:' : 'ws:';
          currentUrl.pathname = url;
          wsUrl = currentUrl.toString();
        }
      } catch (error) {
        // Fallback to string concatenation if URL constructor fails
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host;
        wsUrl = `${wsProtocol}//${wsHost}${url}`;
      }
      
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
          // Failed to parse WebSocket message - using raw data as fallback
          setLastMessage(event.data);
          onMessage?.(event.data);
        }
      };

      websocketRef.current.onclose = (event) => {
        // Clear any pending reconnection timeouts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        
        setConnectionStatus('Closed');
        onClose?.();

        // Check if this socket was flagged to skip reconnection
        const shouldSkipReconnect = (event.target as any)?._skipReconnect;
        
        // Attempt to reconnect unless we asked to skip (manual reconnect or flagged socket)
        if (!skipNextReconnectRef.current && !shouldSkipReconnect && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          // WebSocket reconnection attempt ${reconnectCountRef.current}/${reconnectAttempts}
          
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
        // WebSocket connection error - handled by state
        onError?.(error);
      };

    } catch (error) {
      // Failed to create WebSocket connection - connection state updated
      setConnectionStatus('Closed');
    }
  }, [url, tokens, onMessage, onOpen, onClose, onError, reconnectAttempts, reconnectInterval]);

  const sendMessage = useCallback((message: any) => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      const messageString = typeof message === 'string' ? message : JSON.stringify(message);
      websocketRef.current.send(messageString);
    } else {
      // WebSocket not open - message not sent
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