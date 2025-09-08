import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  X,
  CheckCircle,
  AlertCircle,
  Info,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Bot,
  Shield,
  Activity,
  Clock,
  Star,
  Zap,
  Target,
  Users,
  Settings,
  Volume2,
  VolumeX,
  Filter,
  MoreVertical,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { formatCurrency } from '@/lib/utils';

interface Notification {
  id: string;
  type: 'trade' | 'profit' | 'loss' | 'alert' | 'system' | 'strategy' | 'achievement';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  priority: 'low' | 'medium' | 'high' | 'critical';
  data?: any;
  actionable?: boolean;
}

// Mock notifications data
const generateMockNotifications = (): Notification[] => [
  {
    id: '1',
    type: 'profit',
    title: 'Trade Executed Successfully',
    message: 'BTC/USDT trade completed with +$2,450 profit',
    timestamp: new Date(Date.now() - 5 * 60000), // 5 minutes ago
    read: false,
    priority: 'high',
    data: { symbol: 'BTC/USDT', profit: 2450, percentage: 5.2 },
    actionable: true
  },
  {
    id: '2',
    type: 'alert',
    title: 'Price Alert Triggered',
    message: 'ETH has reached your target price of $2,100',
    timestamp: new Date(Date.now() - 15 * 60000), // 15 minutes ago
    read: false,
    priority: 'medium',
    data: { symbol: 'ETH/USDT', price: 2100, targetPrice: 2100 },
    actionable: true
  },
  {
    id: '3',
    type: 'strategy',
    title: 'AI Strategy Recommendation',
    message: 'Momentum strategy suggests buying SOL based on current market conditions',
    timestamp: new Date(Date.now() - 30 * 60000), // 30 minutes ago
    read: true,
    priority: 'medium',
    data: { strategy: 'Momentum', symbol: 'SOL/USDT', confidence: 85 },
    actionable: true
  },
  {
    id: '4',
    type: 'achievement',
    title: 'New Achievement Unlocked!',
    message: 'You\'ve earned the "Profitable Week" badge - 7 consecutive profitable days!',
    timestamp: new Date(Date.now() - 2 * 60 * 60000), // 2 hours ago
    read: false,
    priority: 'low',
    data: { badge: 'Profitable Week', streak: 7 }
  },
  {
    id: '5',
    type: 'loss',
    title: 'Stop Loss Triggered',
    message: 'ADA/USDT position closed at -$150 to protect capital',
    timestamp: new Date(Date.now() - 4 * 60 * 60000), // 4 hours ago
    read: true,
    priority: 'high',
    data: { symbol: 'ADA/USDT', loss: -150, percentage: -3.2 },
    actionable: false
  },
  {
    id: '6',
    type: 'system',
    title: 'Portfolio Rebalanced',
    message: 'AI has automatically rebalanced your portfolio to maintain target allocation',
    timestamp: new Date(Date.now() - 6 * 60 * 60000), // 6 hours ago
    read: true,
    priority: 'low',
    data: { action: 'rebalance', assetsAffected: 5 }
  }
];

interface GlobalNotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  onNotificationClick?: (notification: Notification) => void;
}

const GlobalNotificationCenter: React.FC<GlobalNotificationCenterProps> = ({
  isOpen,
  onClose,
  onNotificationClick
}) => {
  const [notifications, setNotifications] = useState<Notification[]>(generateMockNotifications());
  const [selectedTab, setSelectedTab] = useState('all');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread' | 'high'>('all');

  const getNotificationIcon = (type: string, priority: string) => {
    const iconClass = `h-5 w-5 ${priority === 'critical' ? 'text-red-500' : 
                                  priority === 'high' ? 'text-orange-500' :
                                  priority === 'medium' ? 'text-blue-500' : 'text-gray-500'}`;
    
    switch (type) {
      case 'trade':
        return <Activity className={iconClass} />;
      case 'profit':
        return <TrendingUp className={`h-5 w-5 text-green-500`} />;
      case 'loss':
        return <TrendingDown className={`h-5 w-5 text-red-500`} />;
      case 'alert':
        return <AlertCircle className={iconClass} />;
      case 'system':
        return <Bot className={iconClass} />;
      case 'strategy':
        return <Target className={iconClass} />;
      case 'achievement':
        return <Star className={`h-5 w-5 text-yellow-500`} />;
      default:
        return <Info className={iconClass} />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'border-l-red-500 bg-red-500/5';
      case 'high': return 'border-l-orange-500 bg-orange-500/5';
      case 'medium': return 'border-l-blue-500 bg-blue-500/5';
      default: return 'border-l-gray-500 bg-gray-500/5';
    }
  };

  const getTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  const markAsRead = (notificationId: string) => {
    setNotifications(prev =>
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    );
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const deleteNotification = (notificationId: string) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId));
  };

  const filteredNotifications = notifications.filter(n => {
    if (selectedTab !== 'all' && n.type !== selectedTab) return false;
    if (filter === 'unread' && n.read) return false;
    if (filter === 'high' && !['high', 'critical'].includes(n.priority)) return false;
    return true;
  });

  const unreadCount = notifications.filter(n => !n.read).length;
  const priorityCount = notifications.filter(n => ['high', 'critical'].includes(n.priority) && !n.read).length;

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
    onNotificationClick?.(notification);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          className="bg-background rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bell className="h-6 w-6 text-primary" />
                <div>
                  <h2 className="text-2xl font-bold">Notification Center</h2>
                  <p className="text-muted-foreground">
                    {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up!'} 
                    {priorityCount > 0 && ` • ${priorityCount} high priority`}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Settings */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <Settings className="h-4 w-4" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80">
                    <div className="space-y-4">
                      <h3 className="font-medium">Notification Settings</h3>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                          <span className="text-sm">Sound Notifications</span>
                        </div>
                        <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
                      </div>
                      
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Filter</label>
                        <div className="flex gap-2">
                          <Button
                            variant={filter === 'all' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setFilter('all')}
                          >
                            All
                          </Button>
                          <Button
                            variant={filter === 'unread' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setFilter('unread')}
                          >
                            Unread
                          </Button>
                          <Button
                            variant={filter === 'high' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setFilter('high')}
                          >
                            High Priority
                          </Button>
                        </div>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Mark all read */}
                {unreadCount > 0 && (
                  <Button variant="ghost" size="sm" onClick={markAllAsRead}>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Mark all read
                  </Button>
                )}

                <Button variant="ghost" size="icon" onClick={onClose}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="p-6 pb-0">
            <Tabs value={selectedTab} onValueChange={setSelectedTab}>
              <TabsList className="w-full justify-start">
                <TabsTrigger value="all" className="flex items-center gap-2">
                  All
                  <Badge variant="secondary" className="text-xs">
                    {notifications.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="trade" className="flex items-center gap-2">
                  <Activity className="h-3 w-3" />
                  Trades
                </TabsTrigger>
                <TabsTrigger value="alert" className="flex items-center gap-2">
                  <AlertCircle className="h-3 w-3" />
                  Alerts
                </TabsTrigger>
                <TabsTrigger value="strategy" className="flex items-center gap-2">
                  <Target className="h-3 w-3" />
                  AI Strategies
                </TabsTrigger>
                <TabsTrigger value="achievement" className="flex items-center gap-2">
                  <Star className="h-3 w-3" />
                  Achievements
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Content */}
          <div className="px-6 pb-6 max-h-[60vh] overflow-y-auto">
            <div className="space-y-3 mt-4">
              {filteredNotifications.length === 0 ? (
                <div className="text-center py-12">
                  <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium">No notifications</h3>
                  <p className="text-muted-foreground">
                    {filter === 'unread' ? 'All notifications have been read' : 
                     filter === 'high' ? 'No high priority notifications' :
                     'You\'re all caught up!'}
                  </p>
                </div>
              ) : (
                filteredNotifications.map((notification) => (
                  <motion.div
                    key={notification.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`
                      relative p-4 border border-l-4 rounded-lg cursor-pointer transition-all
                      ${getPriorityColor(notification.priority)}
                      ${!notification.read ? 'shadow-md' : 'opacity-75'}
                      hover:shadow-lg hover:scale-[1.01]
                    `}
                    onClick={() => handleNotificationClick(notification)}
                  >
                    {!notification.read && (
                      <div className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full" />
                    )}
                    
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        {getNotificationIcon(notification.type, notification.priority)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className={`font-medium ${!notification.read ? 'text-foreground' : 'text-muted-foreground'}`}>
                            {notification.title}
                          </h4>
                          <span className="text-xs text-muted-foreground">
                            {getTimeAgo(notification.timestamp)}
                          </span>
                        </div>
                        
                        <p className={`text-sm ${!notification.read ? 'text-foreground' : 'text-muted-foreground'}`}>
                          {notification.message}
                        </p>
                        
                        {notification.data && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {notification.type === 'profit' && (
                              <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                                +{formatCurrency(notification.data.profit)}
                              </Badge>
                            )}
                            {notification.type === 'loss' && (
                              <Badge className="bg-red-500/10 text-red-500 border-red-500/20">
                                {formatCurrency(notification.data.loss)}
                              </Badge>
                            )}
                            {notification.type === 'strategy' && (
                              <Badge variant="secondary">
                                {notification.data.confidence}% confidence
                              </Badge>
                            )}
                          </div>
                        )}
                        
                        {notification.actionable && (
                          <div className="mt-3 flex gap-2">
                            <Button size="sm" variant="outline">
                              View Details
                            </Button>
                            {notification.type === 'strategy' && (
                              <Button size="sm">
                                Execute
                              </Button>
                            )}
                          </div>
                        )}
                      </div>

                      <Popover>
                        <PopoverTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <MoreVertical className="h-3 w-3" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-40" align="end">
                          <div className="space-y-1">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="w-full justify-start"
                              onClick={() => markAsRead(notification.id)}
                            >
                              {notification.read ? <EyeOff className="h-3 w-3 mr-2" /> : <Eye className="h-3 w-3 mr-2" />}
                              {notification.read ? 'Mark unread' : 'Mark read'}
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="w-full justify-start text-red-500 hover:text-red-600"
                              onClick={() => deleteNotification(notification.id)}
                            >
                              <Trash2 className="h-3 w-3 mr-2" />
                              Delete
                            </Button>
                          </div>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default GlobalNotificationCenter;