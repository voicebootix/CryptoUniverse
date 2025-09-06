import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";
import { useToast } from "@/components/ui/use-toast";

export interface TelegramConnection {
  connected: boolean;
  connection_id?: string;
  telegram_username?: string;
  is_active: boolean;
  trading_enabled: boolean;
  notifications_enabled: boolean;
  voice_commands_enabled: boolean;
  is_authenticated: boolean;
  total_messages: number;
  total_commands: number;
  last_active?: string;
}

export interface TelegramConfig {
  telegram_username?: string;
  enable_notifications: boolean;
  enable_trading: boolean;
  enable_voice_commands: boolean;
  daily_trade_limit: number;
  max_trade_amount: number;
}

export const useTelegram = () => {
  const [connection, setConnection] = useState<TelegramConnection>({
    connected: false,
    is_active: false,
    trading_enabled: false,
    notifications_enabled: false,
    voice_commands_enabled: false,
    is_authenticated: false,
    total_messages: 0,
    total_commands: 0,
  });
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  // Fetch Telegram connection status
  const fetchConnection = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get("/telegram/connection");
      setConnection(response.data);
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || "Failed to fetch Telegram connection";
      setError(errorMsg);

      // Don't show toast for "not connected" errors - check status code instead of string
      const isNotConnectedError = err?.response?.status === 404 || 
                                  err?.status === 404 ||
                                  err?.code === 'TELEGRAM_NOT_CONNECTED';
      
      if (!isNotConnectedError) {
        toast({
          title: "Error",
          description: "Failed to load Telegram connection status",
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Connect Telegram account
  const connectTelegram = async (config: TelegramConfig) => {
    try {
      setConnecting(true);
      setError(null);

      const response = await apiClient.post("/telegram/connect", config);
      if (response.data.connection_id) {
        // Connection created, but not yet authenticated
        setConnection((prev) => ({
          ...prev,
          connected: true,
          connection_id: response.data.connection_id,
          telegram_username: config.telegram_username,
          trading_enabled: config.enable_trading,
          notifications_enabled: config.enable_notifications,
          voice_commands_enabled: config.enable_voice_commands,
          is_authenticated: false,
        }));

        return response.data; // Return auth token and instructions
      } else {
        throw new Error("Connection creation failed");
      }
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || "Failed to connect Telegram";
      setError(errorMsg);

      toast({
        title: "Connection Failed",
        description: errorMsg,
        variant: "destructive",
      });

      throw err;
    } finally {
      setConnecting(false);
    }
  };

  // Disconnect Telegram account
  const disconnectTelegram = async () => {
    try {
      await apiClient.delete("/telegram/disconnect");

      setConnection({
        connected: false,
        is_active: false,
        trading_enabled: false,
        notifications_enabled: false,
        voice_commands_enabled: false,
        is_authenticated: false,
        total_messages: 0,
        total_commands: 0,
      });

      toast({
        title: "Telegram Disconnected",
        description: "Your Telegram account has been disconnected",
        variant: "default",
      });
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || "Failed to disconnect Telegram";
      toast({
        title: "Error",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Send message to Telegram
  const sendMessage = async (message: string) => {
    try {
      const response = await apiClient.post("/telegram/send-message", {
        message: message,
        message_type: "text",
      });

      if (response.data.success) {
        toast({
          title: "Message Sent",
          description: "Message sent to your Telegram",
          variant: "default",
        });

        // Update message count
        setConnection((prev) => ({
          ...prev,
          total_messages: prev.total_messages + 1,
        }));
      }

      return response.data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to send message";
      toast({
        title: "Send Failed",
        description: errorMsg,
        variant: "destructive",
      });
      throw err;
    }
  };

  // Test Telegram connection
  const testConnection = async () => {
    try {
      const testMessage = `🧪 **Connection Test**\n\nTime: ${new Date().toLocaleString()}\nStatus: Connected and working!`;

      await sendMessage(testMessage);

      toast({
        title: "Test Successful",
        description: "Check your Telegram for the test message",
        variant: "default",
      });
    } catch (err: any) {
      toast({
        title: "Test Failed",
        description: "Connection test failed - check your Telegram setup",
        variant: "destructive",
      });
    }
  };

  // Load connection on mount
  useEffect(() => {
    fetchConnection();
  }, []);

  return {
    connection,
    loading,
    connecting,
    error,
    actions: {
      connectTelegram,
      disconnectTelegram,
      sendMessage,
      testConnection,
      fetchConnection,
    },
  };
};
