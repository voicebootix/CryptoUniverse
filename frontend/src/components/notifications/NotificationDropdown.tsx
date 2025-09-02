import React from "react";
import { Bell, Check, X, AlertTriangle, Info, AlertCircle } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { ScrollArea } from "../ui/scroll-area";
import { useNotifications, Notification } from "../../hooks/useNotifications";

const NotificationIcon: React.FC<{
  severity: Notification["severity"];
  className?: string;
}> = ({ severity, className = "h-4 w-4" }) => {
  switch (severity) {
    case "critical":
      return <AlertCircle className={`${className} text-red-500`} />;
    case "warning":
      return <AlertTriangle className={`${className} text-yellow-500`} />;
    case "info":
    default:
      return <Info className={`${className} text-blue-500`} />;
  }
};

const NotificationItem: React.FC<{
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onClear: (id: string) => void;
  formatTimestamp: (timestamp: string) => string;
}> = ({ notification, onMarkAsRead, onClear, formatTimestamp }) => {
  return (
    <div
      className={`p-3 border-b border-border hover:bg-muted/50 transition-colors ${
        !notification.resolved ? "bg-blue-50/30 dark:bg-blue-950/20" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <NotificationIcon
            severity={notification.severity}
            className="h-4 w-4 mt-0.5 flex-shrink-0"
          />
          <div className="flex-1 min-w-0">
            <p
              className={`text-sm ${
                !notification.resolved ? "font-medium" : "text-muted-foreground"
              }`}
            >
              {notification.message}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {formatTimestamp(notification.timestamp)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {!notification.resolved && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onMarkAsRead(notification.id)}
              className="h-6 w-6 p-0 hover:bg-green-100 dark:hover:bg-green-900/20"
              title="Mark as read"
            >
              <Check className="h-3 w-3 text-green-600" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onClear(notification.id)}
            className="h-6 w-6 p-0 hover:bg-red-100 dark:hover:bg-red-900/20"
            title="Clear notification"
          >
            <X className="h-3 w-3 text-red-600" />
          </Button>
        </div>
      </div>
    </div>
  );
};

const NotificationDropdown: React.FC = () => {
  const {
    notifications,
    unreadCount,
    isLoading,
    error,
    markAsRead,
    markAllAsRead,
    clearNotification,
    formatTimestamp,
    fetchNotifications,
  } = useNotifications();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-96 p-0" align="end">
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <span className="font-semibold">Notifications</span>
              {unreadCount > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {unreadCount} new
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchNotifications}
                disabled={isLoading}
                className="h-7 px-2 text-xs"
              >
                Refresh
              </Button>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="h-7 px-2 text-xs"
                >
                  Mark all read
                </Button>
              )}
            </div>
          </div>
        </div>

        <ScrollArea className="max-h-96">
          {isLoading && notifications.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2"></div>
              Loading notifications...
            </div>
          ) : error ? (
            <div className="p-4 text-center text-red-500">
              <AlertCircle className="h-6 w-6 mx-auto mb-2" />
              {error}
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchNotifications}
                className="mt-2 h-7 px-2 text-xs"
              >
                Retry
              </Button>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No notifications</p>
              <p className="text-xs mt-1">You're all caught up!</p>
            </div>
          ) : (
            <div>
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={markAsRead}
                  onClear={clearNotification}
                  formatTimestamp={formatTimestamp}
                />
              ))}
            </div>
          )}
        </ScrollArea>

        {notifications.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <div className="p-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-8 text-xs"
                onClick={() => {
                  // In a real app, this would navigate to a full notifications page
                  console.log("View all notifications");
                }}
              >
                View all notifications
              </Button>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationDropdown;
