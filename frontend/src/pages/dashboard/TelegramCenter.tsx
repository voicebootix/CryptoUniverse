import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Send,
  Bot,
  Command,
  Terminal,
  Activity,
  Bell,
  Shield,
  Zap,
  TrendingUp,
  DollarSign,
  BarChart3,
  Settings,
  Link2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Clock,
  User,
  Users,
  Hash,
  AtSign,
  Phone,
  Video,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Search,
  Filter,
  Download,
  Upload,
  RefreshCw,
  Play,
  Pause,
  ChevronRight,
  ChevronDown,
  MoreVertical,
  Paperclip,
  Image,
  FileText,
  Code,
  Database,
  Server,
  Cloud,
  Wifi,
  WifiOff,
  Lock,
  Unlock,
  Key,
  Eye,
  EyeOff,
  Copy,
  Share2,
  Bookmark,
  Heart,
  ThumbsUp,
  ThumbsDown,
  Star,
  Flag,
  Trash2,
  Edit,
  Save,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { formatCurrency, formatPercentage, formatNumber } from "@/lib/utils";
import { useTelegram } from "@/hooks/useTelegram";
import TelegramConnectionModal from "@/components/TelegramConnectionModal";

// Bot Status
const botStatus = {
  connected: true,
  uptime: "7d 14h 23m",
  messagesProcessed: 12453,
  commandsExecuted: 8932,
  activeChats: 23,
  responseTime: "< 100ms",
  lastSync: "2 min ago",
};

// Available Commands
const commands = [
  {
    command: "/start",
    description: "Initialize bot and show welcome message",
    category: "basic",
  },
  {
    command: "/help",
    description: "Show all available commands",
    category: "basic",
  },
  {
    command: "/status",
    description: "Get system and trading status",
    category: "basic",
  },
  {
    command: "/balance",
    description: "Check account balance across exchanges",
    category: "account",
  },
  {
    command: "/positions",
    description: "View all open positions",
    category: "trading",
  },
  {
    command: "/trades",
    description: "Recent trade history",
    category: "trading",
  },
  {
    command: "/buy <pair> <amount>",
    description: "Execute buy order",
    category: "trading",
  },
  {
    command: "/sell <pair> <amount>",
    description: "Execute sell order",
    category: "trading",
  },
  {
    command: "/market <pair>",
    description: "Get market analysis for pair",
    category: "analysis",
  },
  {
    command: "/ai_consensus",
    description: "Get AI consensus for current market",
    category: "ai",
  },
  {
    command: "/strategy <name>",
    description: "Activate trading strategy",
    category: "strategy",
  },
  {
    command: "/stop_all",
    description: "Emergency stop all trading",
    category: "control",
  },
  {
    command: "/alerts on/off",
    description: "Toggle price alerts",
    category: "alerts",
  },
  {
    command: "/report daily/weekly",
    description: "Generate performance report",
    category: "reports",
  },
];

// Chat Messages
const chatMessages = [
  { id: 1, type: "user", message: "/status", time: "10:23 AM", user: "You" },
  {
    id: 2,
    type: "bot",
    message:
      "🟢 System Status: Online\n💰 Total Balance: $125,432.50\n📊 Active Positions: 12\n📈 24h P&L: +$3,245.67 (+2.65%)\n🤖 AI Consensus: BULLISH (78%)",
    time: "10:23 AM",
    user: "CryptoBot",
  },
  {
    id: 3,
    type: "user",
    message: "/ai_consensus BTC",
    time: "10:25 AM",
    user: "You",
  },
  {
    id: 4,
    type: "bot",
    message:
      "🤖 AI Consensus for BTC/USDT:\n\n📊 Overall Signal: STRONG BUY\n🎯 Confidence: 82%\n\n📈 Technical Analysis: Bullish\n📰 Sentiment Analysis: Positive\n🔮 ML Prediction: $45,200 (24h)\n⚡ Momentum: Increasing\n\n💡 Recommended Action: Long position with 2% allocation",
    time: "10:25 AM",
    user: "CryptoBot",
  },
  {
    id: 5,
    type: "alert",
    message: "⚠️ Price Alert: ETH crossed $2,300 resistance",
    time: "10:28 AM",
    user: "System",
  },
  {
    id: 6,
    type: "user",
    message: "/buy ETH 0.5",
    time: "10:30 AM",
    user: "You",
  },
  {
    id: 7,
    type: "bot",
    message:
      "✅ Order Executed:\n🔹 Buy 0.5 ETH @ $2,301.45\n💵 Total: $1,150.73\n📍 Exchange: Binance\n🆔 Order ID: #ORD-2024-1234",
    time: "10:30 AM",
    user: "CryptoBot",
  },
];

// Alert Settings
const alertSettings = [
  {
    id: 1,
    type: "Price Alerts",
    enabled: true,
    count: 12,
    description: "Get notified when price crosses thresholds",
  },
  {
    id: 2,
    type: "Trade Execution",
    enabled: true,
    count: 8,
    description: "Confirm when trades are executed",
  },
  {
    id: 3,
    type: "AI Signals",
    enabled: true,
    count: 5,
    description: "Receive AI-generated trading signals",
  },
  {
    id: 4,
    type: "System Status",
    enabled: false,
    count: 0,
    description: "System health and maintenance updates",
  },
  {
    id: 5,
    type: "Market Analysis",
    enabled: true,
    count: 3,
    description: "Daily market analysis and insights",
  },
  {
    id: 6,
    type: "Strategy Updates",
    enabled: true,
    count: 2,
    description: "Strategy performance notifications",
  },
];

// Connected Channels
const connectedChannels = [
  {
    id: 1,
    name: "Personal Bot",
    type: "private",
    members: 1,
    status: "active",
    messages: 453,
  },
  {
    id: 2,
    name: "Trading Signals",
    type: "channel",
    members: 1234,
    status: "active",
    messages: 89,
  },
  {
    id: 3,
    name: "VIP Group",
    type: "group",
    members: 45,
    status: "active",
    messages: 234,
  },
  {
    id: 4,
    name: "Market Updates",
    type: "channel",
    members: 5678,
    status: "inactive",
    messages: 0,
  },
];

// Quick Actions
const quickActions = [
  {
    icon: <TrendingUp className="w-4 h-4" />,
    label: "Market Status",
    command: "/market",
  },
  {
    icon: <DollarSign className="w-4 h-4" />,
    label: "Check Balance",
    command: "/balance",
  },
  {
    icon: <Bot className="w-4 h-4" />,
    label: "AI Analysis",
    command: "/ai_consensus",
  },
  {
    icon: <Shield className="w-4 h-4" />,
    label: "Stop Trading",
    command: "/stop_all",
  },
  {
    icon: <BarChart3 className="w-4 h-4" />,
    label: "View Positions",
    command: "/positions",
  },
  { icon: <Bell className="w-4 h-4" />, label: "Set Alert", command: "/alert" },
];

const TelegramCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("chat");
  const [message, setMessage] = useState<string>("");
  const [messages, setMessages] = useState<any[]>(chatMessages);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [selectedCommand, setSelectedCommand] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showConnectionModal, setShowConnectionModal] = useState(false);

  const { connection, loading, connecting, actions } = useTelegram();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = () => {
    if (!message.trim()) return;

    const newMessage = {
      id: messages.length + 1,
      type: "user",
      message: message,
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      user: "You",
    };

    setMessages([...messages, newMessage]);
    setMessage("");
    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      const botResponse = {
        id: messages.length + 2,
        type: "bot",
        message: "✅ Command received and processing...",
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        user: "CryptoBot",
      };
      setMessages((prev) => [...prev, botResponse]);
      setIsTyping(false);
    }, 1500);
  };

  const handleQuickAction = (command: string) => {
    setMessage(command);
  };

  const getMessageTypeStyles = (type: string) => {
    switch (type) {
      case "user":
        return "bg-gradient-to-r from-blue-600 to-blue-500 text-white self-end";
      case "bot":
        return "bg-[#1e2128] text-gray-200 border border-[#3a3d45] self-start";
      case "alert":
        return "bg-[#1e2128] border border-amber-500/20 text-amber-400 self-center w-full";
      default:
        return "bg-[#1e2128] text-gray-200 border border-[#3a3d45]";
    }
  };

  return (
    <div className="space-y-6 min-h-screen bg-[#0f1115] p-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
            Telegram Command Center
          </h1>
          <p className="text-gray-500 mt-1">
            Control your trading bot through Telegram
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="sm"
            className="bg-[#1a1c23] border-[#2a2d35] text-gray-300 hover:text-gray-200 hover:bg-[#1e2128] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
          >
            <Download className="w-4 h-4 mr-2" />
            Export Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="bg-[#1a1c23] border-[#2a2d35] text-gray-300 hover:text-gray-200 hover:bg-[#1e2128] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
          >
            <Settings className="w-4 h-4 mr-2" />
            Bot Settings
          </Button>
          <Button
            className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 text-white hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
            onClick={() => setShowConnectionModal(true)}
          >
            <Link2 className="w-4 h-4 mr-2" />
            Connect Channel
          </Button>
        </div>
      </div>

      {/* Bot Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-green-500/5"></div>
          <div className="relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse" />
                <span className="font-medium text-gray-200">Bot Status</span>
              </div>
              <Badge
                variant="default"
                className="bg-emerald-500/20 text-emerald-400"
              >
                Online
              </Badge>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Uptime: {botStatus.uptime}
            </p>
          </div>
        </Card>

        <Card className="p-4 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5"></div>
          <div className="relative">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Messages</span>
              <MessageSquare className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-xl font-bold text-gray-100">
              {formatNumber(botStatus.messagesProcessed)}
            </p>
            <p className="text-xs text-gray-400">Last: {botStatus.lastSync}</p>
          </div>
        </Card>

        <Card className="p-4 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-violet-500/5"></div>
          <div className="relative">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Commands</span>
              <Terminal className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-xl font-bold text-gray-100">
              {formatNumber(botStatus.commandsExecuted)}
            </p>
            <p className="text-xs text-gray-400">
              Response: {botStatus.responseTime}
            </p>
          </div>
        </Card>

        <Card className="p-4 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-orange-500/5"></div>
          <div className="relative">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Active Chats</span>
              <Users className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xl font-bold text-gray-100">
              {botStatus.activeChats}
            </p>
            <p className="text-xs text-gray-400">Private: 8, Groups: 15</p>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Interface */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col bg-[#1a1c23] border-[#2a2d35] rounded-lg">
            <div className="p-4 border-b border-[#2a2d35] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Bot className="w-8 h-8 text-blue-400" />
                  <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#1a1c23]" />
                </div>
                <div>
                  <p className="font-semibold text-gray-200">
                    CryptoUniverse Bot
                  </p>
                  <p className="text-xs text-gray-400">@CryptoUniverseBot</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-[#1e2128] border-[#2a2d35] text-gray-400 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                >
                  <Phone className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-[#1e2128] border-[#2a2d35] text-gray-400 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                >
                  <Video className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-[#1e2128] border-[#2a2d35] text-gray-400 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                >
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 messages-container">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${
                    msg.type === "user"
                      ? "justify-end"
                      : msg.type === "alert"
                      ? "justify-center"
                      : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[70%] ${
                      msg.type === "alert" ? "w-full" : ""
                    }`}
                  >
                    {msg.type !== "alert" && (
                      <p
                        className={`text-xs text-gray-400 mb-1 ${
                          msg.type === "user" ? "text-right" : ""
                        }`}
                      >
                        {msg.user} • {msg.time}
                      </p>
                    )}
                    <div
                      className={`rounded-lg p-3 ${getMessageTypeStyles(
                        msg.type
                      )} ${msg.type === "alert" ? "border text-center" : ""}`}
                    >
                      <pre className="whitespace-pre-wrap font-sans text-sm">
                        {msg.message}
                      </pre>
                    </div>
                  </div>
                </motion.div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-[#1e2128] border border-[#2a2d35] rounded-lg p-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-blue-400/50 rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-blue-400/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.1s" }}
                      />
                      <div
                        className="w-2 h-2 bg-blue-400/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Actions */}
            <div className="p-3 border-t border-b border-[#2a2d35] bg-[#1e2128]">
              <div className="flex gap-2 overflow-x-auto">
                {quickActions.map((action, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    onClick={() => handleQuickAction(action.command)}
                    className="flex-shrink-0 bg-[#1a1c23] border-[#2a2d35] text-gray-300 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                  >
                    {action.icon}
                    <span className="ml-1">{action.label}</span>
                  </Button>
                ))}
              </div>
            </div>

            {/* Input */}
            <div className="p-4 flex gap-2 bg-[#1e2128] border-t border-[#2a2d35] rounded-b-lg">
              <Button
                variant="outline"
                size="sm"
                className="bg-[#1a1c23] border-[#2a2d35] text-gray-400 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              <Input
                placeholder="Type a command or message..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                className="flex-1 bg-[#1a1c23] border-[#2a2d35] text-gray-200 placeholder:text-gray-500"
              />
              <Button
                onClick={sendMessage}
                className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 text-white hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Commands */}
          <Card className="p-4 bg-[#1a1c23] border-[#2a2d35]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-200">Commands</h3>
              <Button
                variant="outline"
                size="sm"
                className="bg-[#1e2128] border-[#2a2d35] text-gray-400 hover:text-gray-200 hover:bg-[#222429] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
              >
                <Code className="w-4 h-4" />
              </Button>
            </div>
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search commands..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 text-sm bg-[#1e2128] border-[#2a2d35] text-gray-200 placeholder:text-gray-500"
              />
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {commands
                .filter(
                  (cmd) =>
                    cmd.command.includes(searchQuery) ||
                    cmd.description
                      .toLowerCase()
                      .includes(searchQuery.toLowerCase())
                )
                .map((cmd, idx) => (
                  <div
                    key={idx}
                    className="p-2 hover:bg-[#1e2128] rounded cursor-pointer border border-[#2a2d35] hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                    onClick={() => setMessage(cmd.command)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <code className="text-sm font-medium text-blue-400">
                          {cmd.command}
                        </code>
                        <p className="text-xs text-gray-400 mt-1">
                          {cmd.description}
                        </p>
                      </div>
                      <Copy className="w-3 h-3 text-gray-400 mt-1 hover:text-gray-200" />
                    </div>
                  </div>
                ))}
            </div>
          </Card>

          {/* Alert Settings */}
          <Card className="p-4 bg-[#1a1c23] border-[#2a2d35]">
            <h3 className="font-semibold mb-4 text-gray-200">Alert Settings</h3>
            <div className="space-y-3">
              {alertSettings.slice(0, 3).map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-200">
                      {alert.type}
                    </p>
                    <p className="text-xs text-gray-400">
                      {alert.count} active
                    </p>
                  </div>
                  <Switch
                    checked={alert.enabled}
                    className="data-[state=checked]:bg-blue-600"
                  />
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="w-full bg-[#1e2128] border-[#2a2d35] text-gray-300 hover:text-gray-200"
              >
                View All Settings
              </Button>
            </div>
          </Card>

          {/* Connected Channels */}
          <Card className="p-4 bg-[#1a1c23] border-[#2a2d35]">
            <h3 className="font-semibold mb-4 text-gray-200">
              Connected Channels
            </h3>
            <div className="space-y-2">
              {connectedChannels.map((channel) => (
                <div
                  key={channel.id}
                  className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                >
                  <div className="flex items-center gap-2">
                    <Hash className="w-4 h-4 text-blue-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-200">
                        {channel.name}
                      </p>
                      <p className="text-xs text-gray-400">
                        {channel.members} members
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      channel.status === "active" ? "default" : "secondary"
                    }
                    className={
                      channel.status === "active"
                        ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                        : "bg-gray-500/20 text-gray-400"
                    }
                  >
                    {channel.status}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Telegram Connection Modal */}
      <TelegramConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onConnect={async (config) => {
          const result = await actions.connectTelegram(config);
          return (
            result || {
              auth_token: "",
              connection_id: "",
              setup_instructions: "",
            }
          );
        }}
        connecting={connecting}
      />
    </div>
  );
};

export default TelegramCenter;
