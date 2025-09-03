import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Settings,
  Shield,
  Clock,
  Zap,
  Eye,
  Bell,
  Key,
  FileText,
  X,
  Save,
  RotateCcw,
} from "lucide-react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Slider } from "./ui/slider";
import { useToast } from "./ui/use-toast";

interface ExchangeSettings {
  // Connection Parameters
  timeout_seconds: number;
  rate_limit_per_minute: number;
  max_retries: number;
  connection_pool_size: number;

  // Arbitrage Automation
  auto_execute_arbitrage: boolean;
  min_profit_threshold: number;
  max_position_size: number;
  risk_level: "conservative" | "moderate" | "aggressive";

  // Trading Preferences
  default_order_type: "market" | "limit";
  max_slippage_percent: number;
  order_routing_priority: "speed" | "cost" | "balanced";
  enable_smart_routing: boolean;

  // Data Refresh
  price_update_interval: number;
  balance_update_interval: number;
  orderbook_depth: number;
  enable_real_time: boolean;

  // UI/UX Preferences
  default_view: "grid" | "table" | "chart";
  show_advanced_metrics: boolean;
  enable_sound_notifications: boolean;
  theme_mode: "dark" | "light" | "auto";

  // Security Settings
  show_api_keys: boolean;
  enable_audit_logging: boolean;
  require_2fa_for_trades: boolean;
  session_timeout_minutes: number;
}

interface ExchangeHubSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (settings: ExchangeSettings) => void;
  initialSettings: ExchangeSettings;
}

const ExchangeHubSettingsModal: React.FC<ExchangeHubSettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialSettings,
}) => {
  const [settings, setSettings] = useState<ExchangeSettings>(initialSettings);
  const [activeTab, setActiveTab] = useState("connection");
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(settings);
      toast({
        title: "Settings Saved",
        description:
          "Your exchange hub settings have been updated successfully.",
        variant: "default",
      });
      onClose();
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Failed to save settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSettings(initialSettings);
    toast({
      title: "Settings Reset",
      description: "All settings have been reset to their previous values.",
      variant: "default",
    });
  };

  const updateSetting = (key: keyof ExchangeSettings, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <Card className="p-0 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5"></div>
          <div className="relative">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b border-[#2a2d35]">
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  <Settings className="w-6 h-6 text-blue-400" />
                  Exchange Hub Settings
                </h2>
                <p className="text-gray-400 mt-1">
                  Configure your multi-exchange trading environment
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={onClose}
                className="hover:bg-[#1e2128] text-gray-400 hover:text-gray-200"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Settings Content */}
            <div className="p-6">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-6 bg-[#1e2128] border border-[#2a2d35]">
                  <TabsTrigger value="connection" className="text-xs">
                    <Shield className="w-3 h-3 mr-1" />
                    Connection
                  </TabsTrigger>
                  <TabsTrigger value="arbitrage" className="text-xs">
                    <Zap className="w-3 h-3 mr-1" />
                    Arbitrage
                  </TabsTrigger>
                  <TabsTrigger value="trading" className="text-xs">
                    <Settings className="w-3 h-3 mr-1" />
                    Trading
                  </TabsTrigger>
                  <TabsTrigger value="data" className="text-xs">
                    <Clock className="w-3 h-3 mr-1" />
                    Data
                  </TabsTrigger>
                  <TabsTrigger value="ui" className="text-xs">
                    <Eye className="w-3 h-3 mr-1" />
                    UI/UX
                  </TabsTrigger>
                  <TabsTrigger value="security" className="text-xs">
                    <Key className="w-3 h-3 mr-1" />
                    Security
                  </TabsTrigger>
                </TabsList>

                {/* Connection Settings */}
                <TabsContent value="connection" className="mt-6 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-blue-400" />
                        Connection Parameters
                      </h3>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Connection Timeout (seconds)
                        </Label>
                        <Input
                          type="number"
                          min="5"
                          max="120"
                          value={settings.timeout_seconds}
                          onChange={(e) =>
                            updateSetting(
                              "timeout_seconds",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                        <p className="text-xs text-gray-500">
                          How long to wait for exchange responses
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Rate Limit (requests/minute)
                        </Label>
                        <Input
                          type="number"
                          min="10"
                          max="1000"
                          value={settings.rate_limit_per_minute}
                          onChange={(e) =>
                            updateSetting(
                              "rate_limit_per_minute",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                        <p className="text-xs text-gray-500">
                          Maximum API requests per minute
                        </p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label className="text-gray-300">Max Retries</Label>
                        <Input
                          type="number"
                          min="0"
                          max="10"
                          value={settings.max_retries}
                          onChange={(e) =>
                            updateSetting(
                              "max_retries",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                        <p className="text-xs text-gray-500">
                          Retry attempts for failed requests
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Connection Pool Size
                        </Label>
                        <Input
                          type="number"
                          min="1"
                          max="50"
                          value={settings.connection_pool_size}
                          onChange={(e) =>
                            updateSetting(
                              "connection_pool_size",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                        <p className="text-xs text-gray-500">
                          Concurrent connections per exchange
                        </p>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* Arbitrage Settings */}
                <TabsContent value="arbitrage" className="mt-6 space-y-6">
                  <div className="space-y-6">
                    <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-emerald-400" />
                      Arbitrage Automation
                    </h3>

                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                      <div>
                        <Label className="text-gray-300 flex items-center gap-2">
                          <Zap className="w-4 h-4" />
                          Auto-Execute Arbitrage
                        </Label>
                        <p className="text-sm text-gray-500">
                          Automatically execute profitable arbitrage
                          opportunities
                        </p>
                      </div>
                      <Switch
                        checked={settings.auto_execute_arbitrage}
                        onCheckedChange={(checked) =>
                          updateSetting("auto_execute_arbitrage", checked)
                        }
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Minimum Profit Threshold (%)
                        </Label>
                        <div className="px-3">
                          <Slider
                            value={[settings.min_profit_threshold]}
                            onValueChange={(value) =>
                              updateSetting("min_profit_threshold", value[0])
                            }
                            max={10}
                            min={0.1}
                            step={0.1}
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>0.1%</span>
                            <span className="text-blue-400">
                              {settings.min_profit_threshold}%
                            </span>
                            <span>10%</span>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Max Position Size (USD)
                        </Label>
                        <Input
                          type="number"
                          min="100"
                          max="100000"
                          value={settings.max_position_size}
                          onChange={(e) =>
                            updateSetting(
                              "max_position_size",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">Risk Level</Label>
                        <Select
                          value={settings.risk_level}
                          onValueChange={(value) =>
                            updateSetting("risk_level", value)
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="conservative">
                              Conservative
                            </SelectItem>
                            <SelectItem value="moderate">Moderate</SelectItem>
                            <SelectItem value="aggressive">
                              Aggressive
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* Trading Settings */}
                <TabsContent value="trading" className="mt-6 space-y-6">
                  <div className="space-y-6">
                    <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                      <Settings className="w-4 h-4 text-purple-400" />
                      Trading Preferences
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Default Order Type
                        </Label>
                        <Select
                          value={settings.default_order_type}
                          onValueChange={(value) =>
                            updateSetting("default_order_type", value)
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="market">Market Order</SelectItem>
                            <SelectItem value="limit">Limit Order</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Max Slippage (%)
                        </Label>
                        <div className="px-3">
                          <Slider
                            value={[settings.max_slippage_percent]}
                            onValueChange={(value) =>
                              updateSetting("max_slippage_percent", value[0])
                            }
                            max={5}
                            min={0.1}
                            step={0.1}
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>0.1%</span>
                            <span className="text-purple-400">
                              {settings.max_slippage_percent}%
                            </span>
                            <span>5%</span>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Order Routing Priority
                        </Label>
                        <Select
                          value={settings.order_routing_priority}
                          onValueChange={(value) =>
                            updateSetting("order_routing_priority", value)
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="speed">Speed First</SelectItem>
                            <SelectItem value="cost">Lowest Cost</SelectItem>
                            <SelectItem value="balanced">Balanced</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                      <div>
                        <Label className="text-gray-300">
                          Enable Smart Routing
                        </Label>
                        <p className="text-sm text-gray-500">
                          Automatically route orders to best exchange
                        </p>
                      </div>
                      <Switch
                        checked={settings.enable_smart_routing}
                        onCheckedChange={(checked) =>
                          updateSetting("enable_smart_routing", checked)
                        }
                      />
                    </div>
                  </div>
                </TabsContent>

                {/* Data Settings */}
                <TabsContent value="data" className="mt-6 space-y-6">
                  <div className="space-y-6">
                    <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-amber-400" />
                      Data Refresh Settings
                    </h3>

                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                      <div>
                        <Label className="text-gray-300">
                          Enable Real-Time Data
                        </Label>
                        <p className="text-sm text-gray-500">
                          Use WebSocket connections for live updates
                        </p>
                      </div>
                      <Switch
                        checked={settings.enable_real_time}
                        onCheckedChange={(checked) =>
                          updateSetting("enable_real_time", checked)
                        }
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Price Update Interval (seconds)
                        </Label>
                        <Input
                          type="number"
                          min="1"
                          max="60"
                          value={settings.price_update_interval}
                          onChange={(e) =>
                            updateSetting(
                              "price_update_interval",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                          disabled={settings.enable_real_time}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Balance Update Interval (seconds)
                        </Label>
                        <Input
                          type="number"
                          min="5"
                          max="300"
                          value={settings.balance_update_interval}
                          onChange={(e) =>
                            updateSetting(
                              "balance_update_interval",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Order Book Depth
                        </Label>
                        <Select
                          value={settings.orderbook_depth.toString()}
                          onValueChange={(value) =>
                            updateSetting("orderbook_depth", parseInt(value))
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="5">5 levels</SelectItem>
                            <SelectItem value="10">10 levels</SelectItem>
                            <SelectItem value="20">20 levels</SelectItem>
                            <SelectItem value="50">50 levels</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* UI/UX Settings */}
                <TabsContent value="ui" className="mt-6 space-y-6">
                  <div className="space-y-6">
                    <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                      <Eye className="w-4 h-4 text-cyan-400" />
                      UI/UX Preferences
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label className="text-gray-300">Default View</Label>
                        <Select
                          value={settings.default_view}
                          onValueChange={(value) =>
                            updateSetting("default_view", value)
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="grid">Grid View</SelectItem>
                            <SelectItem value="table">Table View</SelectItem>
                            <SelectItem value="chart">Chart View</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">Theme Mode</Label>
                        <Select
                          value={settings.theme_mode}
                          onValueChange={(value) =>
                            updateSetting("theme_mode", value)
                          }
                        >
                          <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                            <SelectItem value="dark">Dark</SelectItem>
                            <SelectItem value="light">Light</SelectItem>
                            <SelectItem value="auto">Auto</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                        <div>
                          <Label className="text-gray-300">
                            Show Advanced Metrics
                          </Label>
                          <p className="text-sm text-gray-500">
                            Display technical indicators and advanced data
                          </p>
                        </div>
                        <Switch
                          checked={settings.show_advanced_metrics}
                          onCheckedChange={(checked) =>
                            updateSetting("show_advanced_metrics", checked)
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                        <div>
                          <Label className="text-gray-300 flex items-center gap-2">
                            <Bell className="w-4 h-4" />
                            Sound Notifications
                          </Label>
                          <p className="text-sm text-gray-500">
                            Play sounds for alerts and updates
                          </p>
                        </div>
                        <Switch
                          checked={settings.enable_sound_notifications}
                          onCheckedChange={(checked) =>
                            updateSetting("enable_sound_notifications", checked)
                          }
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* Security Settings */}
                <TabsContent value="security" className="mt-6 space-y-6">
                  <div className="space-y-6">
                    <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                      <Key className="w-4 h-4 text-red-400" />
                      Security Settings
                    </h3>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                        <div>
                          <Label className="text-gray-300 flex items-center gap-2">
                            <Eye className="w-4 h-4" />
                            Show API Keys
                          </Label>
                          <p className="text-sm text-gray-500">
                            Display API keys in connection status
                          </p>
                        </div>
                        <Switch
                          checked={settings.show_api_keys}
                          onCheckedChange={(checked) =>
                            updateSetting("show_api_keys", checked)
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                        <div>
                          <Label className="text-gray-300 flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            Enable Audit Logging
                          </Label>
                          <p className="text-sm text-gray-500">
                            Log all trading activities for compliance
                          </p>
                        </div>
                        <Switch
                          checked={settings.enable_audit_logging}
                          onCheckedChange={(checked) =>
                            updateSetting("enable_audit_logging", checked)
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                        <div>
                          <Label className="text-gray-300 flex items-center gap-2">
                            <Shield className="w-4 h-4" />
                            Require 2FA for Trades
                          </Label>
                          <p className="text-sm text-gray-500">
                            Additional verification for trading operations
                          </p>
                        </div>
                        <Switch
                          checked={settings.require_2fa_for_trades}
                          onCheckedChange={(checked) =>
                            updateSetting("require_2fa_for_trades", checked)
                          }
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-gray-300">
                          Session Timeout (minutes)
                        </Label>
                        <Input
                          type="number"
                          min="5"
                          max="480"
                          value={settings.session_timeout_minutes}
                          onChange={(e) =>
                            updateSetting(
                              "session_timeout_minutes",
                              parseInt(e.target.value)
                            )
                          }
                          className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                        />
                        <p className="text-xs text-gray-500">
                          Automatic logout after inactivity
                        </p>
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </div>

            {/* Footer Actions */}
            <div className="flex justify-between items-center p-6 border-t border-[#2a2d35]">
              <Button
                variant="outline"
                onClick={handleReset}
                className="bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset to Defaults
              </Button>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={onClose}
                  className="bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700"
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Save Settings
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default ExchangeHubSettingsModal;
