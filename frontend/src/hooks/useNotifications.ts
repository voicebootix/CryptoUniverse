import { useState, useEffect, useCallback } from "react";
import { apiClient as api } from "../lib/api/client";

export interface Notification {
  id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  timestamp: string;
  resolved?: boolean;
  type?: string;
  metadata?: Record<string, any>;
}

export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
}

export const useNotifications = () => {
  const [state, setState] = useState<NotificationState>({
    notifications: [],
    unreadCount: 0,
    isLoading: false,
    error: null,
  });

  const fetchNotifications = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await api.get("/monitoring/alerts");

      if (response.data.active_alerts) {
        const notifications: Notification[] = response.data.active_alerts.map(
          (alert: any) => ({
            id: alert.id,
            severity: alert.severity || "info",
            message: alert.message,
            timestamp: alert.timestamp,
            resolved: alert.resolved || false,
            type: "system_alert",
            metadata: alert,
          })
        );

        // Add some mock notifications for demo purposes
        const mockNotifications: Notification[] = [
          {
            id: "trade_001",
            severity: "info",
            message: "BTC/USDT trade executed successfully: +$234.56",
            timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            type: "trade_execution",
          },
          {
            id: "portfolio_001",
            severity: "warning",
            message: "Portfolio risk level increased to 7.2/10",
            timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
            type: "risk_alert",
          },
          {
            id: "market_001",
            severity: "info",
            message: "ETH price alert: $3,245 target reached",
            timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            type: "price_alert",
          },
        ];

        const allNotifications = [...notifications, ...mockNotifications];
        const unreadCount = allNotifications.filter((n) => !n.resolved).length;

        setState((prev) => ({
          ...prev,
          notifications: allNotifications,
          unreadCount,
          isLoading: false,
        }));
      } else {
        setState((prev) => ({
          ...prev,
          notifications: [],
          unreadCount: 0,
          isLoading: false,
        }));
      }
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
      setState((prev) => ({
        ...prev,
        error: "Failed to load notifications",
        isLoading: false,
      }));
    }
  }, []);

  const markAsRead = useCallback(
    async (notificationId: string) => {
      try {
        // For system alerts, call the resolve endpoint
        const notification = state.notifications.find(
          (n) => n.id === notificationId
        );
        if (notification?.type === "system_alert") {
          await api.post(`/monitoring/alerts/${notificationId}/resolve`);
        }

        setState((prev) => ({
          ...prev,
          notifications: prev.notifications.map((n) =>
            n.id === notificationId ? { ...n, resolved: true } : n
          ),
          unreadCount: Math.max(0, prev.unreadCount - 1),
        }));
      } catch (error) {
        console.error("Failed to mark notification as read:", error);
      }
    },
    [state.notifications]
  );

  const markAllAsRead = useCallback(async () => {
    try {
      // Mark all system alerts as resolved
      const systemAlerts = state.notifications.filter(
        (n) => n.type === "system_alert" && !n.resolved
      );
      await Promise.all(
        systemAlerts.map((alert) =>
          api.post(`/monitoring/alerts/${alert.id}/resolve`)
        )
      );

      setState((prev) => ({
        ...prev,
        notifications: prev.notifications.map((n) => ({
          ...n,
          resolved: true,
        })),
        unreadCount: 0,
      }));
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }, [state.notifications]);

  const clearNotification = useCallback((notificationId: string) => {
    setState((prev) => ({
      ...prev,
      notifications: prev.notifications.filter((n) => n.id !== notificationId),
      unreadCount: prev.notifications.find(
        (n) => n.id === notificationId && !n.resolved
      )
        ? prev.unreadCount - 1
        : prev.unreadCount,
    }));
  }, []);

  const getSeverityColor = (severity: Notification["severity"]) => {
    switch (severity) {
      case "critical":
        return "text-red-500";
      case "warning":
        return "text-yellow-500";
      case "info":
      default:
        return "text-blue-500";
    }
  };

  const getSeverityIcon = (severity: Notification["severity"]) => {
    switch (severity) {
      case "critical":
        return "🚨";
      case "warning":
        return "⚠️";
      case "info":
      default:
        return "ℹ️";
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  // Auto-refresh notifications every 30 seconds
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  return {
    ...state,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    clearNotification,
    getSeverityColor,
    getSeverityIcon,
    formatTimestamp,
  };
};
