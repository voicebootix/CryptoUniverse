/**
 * Chat Service with Server-Sent Events (SSE) Streaming Support
 * 
 * Provides both regular and streaming chat message functionality.
 * Streaming provides real-time progress updates for long-running operations.
 */

import { apiClient } from '@/lib/api/client';

export interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant' | 'system' | 'error';
  timestamp: string;
  intent?: string;
  confidence?: number;
  metadata?: any;
}

export interface ChatResponse {
  success: boolean;
  session_id: string;
  message_id: string;
  content: string;
  intent: string;
  confidence: number;
  requires_approval?: boolean;
  requires_action?: boolean;
  decision_id?: string;
  action_data?: any;
  metadata?: any;
  timestamp: string;
}

export interface StreamChunk {
  type: 'chunk' | 'response' | 'processing' | 'complete' | 'error' | 'progress';
  content?: string;
  progress?: {
    stage: string;
    message: string;
    percent?: number;
  };
  error?: string;
  timestamp?: string;
  personality?: string;
}

/**
 * Send a chat message using regular POST endpoint
 */
export async function sendChatMessage(
  message: string,
  sessionId: string,
  conversationMode: string = 'live_trading'
): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/unified-chat/message', {
    message,
    session_id: sessionId,
    conversation_mode: conversationMode,
    stream: false
  });

  return response.data;
}

/**
 * Send a chat message using Server-Sent Events (SSE) for streaming response
 * 
 * @param message - The user's message
 * @param sessionId - The chat session ID
 * @param conversationMode - The conversation mode (default: 'live_trading')
 * @param onChunk - Callback for each chunk received
 * @param onProgress - Callback for progress updates
 * @param onComplete - Callback when streaming completes
 * @param onError - Callback for errors
 * @returns A function to abort the stream
 */
export function streamChatMessage(
  message: string,
  sessionId: string,
  conversationMode: string = 'live_trading',
  onChunk: (chunk: string) => void,
  onProgress?: (progress: { stage: string; message: string; percent?: number }) => void,
  onComplete?: (fullContent: string) => void,
  onError?: (error: string) => void
): () => void {
  const token = localStorage.getItem('token');
  const baseURL = apiClient.defaults.baseURL || '';
  
  // Build SSE URL with query parameters
  const params = new URLSearchParams({
    message,
    session_id: sessionId,
    conversation_mode: conversationMode
  });
  
  const url = `${baseURL}/unified-chat/stream?${params.toString()}`;
  
  // Create EventSource for SSE
  const eventSource = new EventSource(url, {
    withCredentials: false
  });
  
  // Note: EventSource doesn't support custom headers directly
  // The backend should accept token via query param or cookie for SSE
  // For now, we'll rely on cookie-based auth or modify backend to accept token in query
  
  let fullContent = '';
  let aborted = false;
  
  eventSource.onmessage = (event) => {
    if (aborted) return;
    
    try {
      const data: StreamChunk = JSON.parse(event.data);
      
      switch (data.type) {
        case 'response':
          // Backend sends 'response' type for AI response chunks
          if (data.content) {
            fullContent += data.content;
            onChunk(data.content);
          }
          break;
          
        case 'chunk':
          // Legacy support for 'chunk' type (if backend ever sends it)
          if (data.content) {
            fullContent += data.content;
            onChunk(data.content);
          }
          break;
          
        case 'processing':
          // Backend sends 'processing' type for initial processing message
          if (onProgress) {
            onProgress({
              stage: 'processing',
              message: data.content || 'Processing your request...',
              percent: 10
            });
          }
          break;
          
        case 'progress':
          // Backend sends 'progress' type for detailed progress updates
          if (data.progress && onProgress) {
            onProgress(data.progress);
          }
          break;
          
        case 'complete':
          eventSource.close();
          if (onComplete) {
            onComplete(fullContent);
          }
          break;
          
        case 'error':
          eventSource.close();
          if (onError && data.error) {
            onError(data.error);
          }
          break;
      }
    } catch (error) {
      console.error('Failed to parse SSE data:', error);
    }
  };
  
  eventSource.onerror = (error) => {
    if (aborted) return;
    
    console.error('SSE connection error:', error);
    eventSource.close();
    
    if (onError) {
      onError('Connection to server lost. Please try again.');
    }
  };
  
  // Return abort function
  return () => {
    aborted = true;
    eventSource.close();
  };
}

/**
 * Create a new chat session
 */
export async function createChatSession(): Promise<{ session_id: string }> {
  const response = await apiClient.post<{ session_id: string }>('/unified-chat/session/new');
  return response.data;
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(
  sessionId: string,
  limit: number = 50
): Promise<ChatMessage[]> {
  const response = await apiClient.get<{ messages: ChatMessage[] }>(
    `/unified-chat/history/${sessionId}`,
    { params: { limit } }
  );
  return response.data.messages;
}

/**
 * Get all active chat sessions for the user
 */
export async function getChatSessions(): Promise<string[]> {
  const response = await apiClient.get<{ sessions: string[] }>('/unified-chat/sessions');
  return response.data.sessions;
}
