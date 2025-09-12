import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  X,
  MessageSquare,
  Bot,
  Shield,
  CheckCircle,
  Copy,
  ExternalLink,
  Settings,
  Bell,
  Zap,
  AlertTriangle,
  Info,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";

interface TelegramConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (config: TelegramConfig) => Promise<{
    auth_token: string;
    connection_id: string;
    setup_instructions: string;
  }>;
  connecting: boolean;
  onConnectionSuccess?: () => void;
}

interface TelegramConfig {
  telegram_username?: string;
  enable_notifications: boolean;
  enable_trading: boolean;
  enable_voice_commands: boolean;
  daily_trade_limit: number;
  max_trade_amount: number;
}

const TelegramConnectionModal: React.FC<TelegramConnectionModalProps> = ({
  isOpen,
  onClose,
  onConnect,
  connecting,
  onConnectionSuccess,
}) => {
  const [config, setConfig] = useState<TelegramConfig>({
    telegram_username: "",
    enable_notifications: true,
    enable_trading: false,
    enable_voice_commands: false,
    daily_trade_limit: 10,
    max_trade_amount: 1000,
  });
  const [authToken, setAuthToken] = useState<string>("");
  const [step, setStep] = useState<"configure" | "authenticate">("configure");
  const { toast } = useToast();

  const handleConnect = async () => {
    try {
      const result = await onConnect(config);

      setAuthToken(result.auth_token);
      setStep("authenticate");

      // Call success callback to refresh connection status
      if (onConnectionSuccess) {
        onConnectionSuccess();
      }

      toast({
        title: "Connection Created",
        description: "Follow the authentication steps to complete setup",
        variant: "default",
      });
    } catch (error: any) {
      console.error("Telegram connection error:", error);
      
      // Show more specific error messages
      let errorMessage = "Failed to create Telegram connection";
      if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || "Connection already exists or invalid configuration";
      } else if (error.response?.status === 500) {
        errorMessage = "Server error - please try again later";
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast({
        title: "Connection Failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const copyAuthToken = () => {
    navigator.clipboard.writeText(`/auth ${authToken}`);
    toast({
      title: "Copied",
      description: "Authentication command copied to clipboard",
      variant: "default",
    });
  };

  const openTelegram = () => {
    // Create deep link with start parameter containing auth token
    const deepLink = `https://t.me/CryptoUniverseBot?start=auth_${authToken.replace(/[^a-zA-Z0-9]/g, '_')}`;
    window.open(deepLink, "_blank");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <Card className="p-6 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5"></div>
          <div className="relative">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  <MessageSquare className="w-6 h-6 text-blue-400" />
                  Connect Telegram
                </h2>
                <p className="text-gray-400 mt-1">
                  {step === "configure"
                    ? "Configure your Telegram integration settings"
                    : "Complete authentication in Telegram"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="hover:bg-[#1e2128] text-gray-400 hover:text-gray-200"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {step === "configure" && (
              <div className="space-y-6">
                {/* Configuration Form */}
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="username" className="text-gray-300">
                      Telegram Username (Optional)
                    </Label>
                    <Input
                      id="username"
                      placeholder="@yourusername"
                      value={config.telegram_username}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          telegram_username: e.target.value,
                        }))
                      }
                      className="bg-[#1a1c23] border-[#2a2d35] text-gray-200 placeholder:text-gray-500"
                    />
                    <p className="text-sm text-gray-400 mt-1">
                      Optional: Your Telegram username for identification
                    </p>
                  </div>

                  {/* Feature Toggles */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                      <div>
                        <Label className="flex items-center gap-2 text-blue-400">
                          <Bell className="w-4 h-4" />
                          Enable Notifications
                        </Label>
                        <p className="text-sm text-gray-400">
                          Receive trade alerts, portfolio updates, and system
                          notifications
                        </p>
                      </div>
                      <Switch
                        checked={config.enable_notifications}
                        onCheckedChange={(checked) =>
                          setConfig((prev) => ({
                            ...prev,
                            enable_notifications: checked,
                          }))
                        }
                        className="data-[state=checked]:bg-blue-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
                      <div>
                        <Label className="flex items-center gap-2 text-emerald-400">
                          <Zap className="w-4 h-4" />
                          Enable Trading Commands
                        </Label>
                        <p className="text-sm text-gray-400">
                          Execute trades directly from Telegram chat
                        </p>
                      </div>
                      <Switch
                        checked={config.enable_trading}
                        onCheckedChange={(checked) =>
                          setConfig((prev) => ({
                            ...prev,
                            enable_trading: checked,
                          }))
                        }
                        className="data-[state=checked]:bg-emerald-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300">
                      <div>
                        <Label className="flex items-center gap-2 text-purple-400">
                          <Bot className="w-4 h-4" />
                          Enable Voice Commands
                        </Label>
                        <p className="text-sm text-gray-400">
                          Use voice messages for natural language trading
                        </p>
                      </div>
                      <Switch
                        checked={config.enable_voice_commands}
                        onCheckedChange={(checked) =>
                          setConfig((prev) => ({
                            ...prev,
                            enable_voice_commands: checked,
                          }))
                        }
                        className="data-[state=checked]:bg-purple-600"
                      />
                    </div>
                  </div>

                  {/* Trading Limits */}
                  {config.enable_trading && (
                    <div className="space-y-4 p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-amber-500/10 transition-all duration-300">
                      <h4 className="font-medium text-amber-400 flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        Trading Safety Limits
                      </h4>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <Label className="text-gray-300">
                            Daily Trade Limit
                          </Label>
                          <Input
                            type="number"
                            min="1"
                            max="100"
                            value={config.daily_trade_limit}
                            onChange={(e) =>
                              setConfig((prev) => ({
                                ...prev,
                                daily_trade_limit:
                                  parseInt(e.target.value) || 10,
                              }))
                            }
                            className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                          />
                          <p className="text-xs text-amber-400/80">
                            Maximum trades per day via Telegram
                          </p>
                        </div>

                        <div>
                          <Label className="text-gray-300">
                            Max Trade Amount (USD)
                          </Label>
                          <Input
                            type="number"
                            min="100"
                            max="50000"
                            value={config.max_trade_amount}
                            onChange={(e) =>
                              setConfig((prev) => ({
                                ...prev,
                                max_trade_amount:
                                  parseInt(e.target.value) || 1000,
                              }))
                            }
                            className="bg-[#1a1c23] border-[#2a2d35] text-gray-200"
                          />
                          <p className="text-xs text-amber-400/80">
                            Maximum amount per trade
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Security Notice */}
                <div className="p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-400 mb-2">
                        Security & Privacy
                      </h4>
                      <ul className="text-sm text-gray-400 space-y-2">
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          Your Telegram is linked securely to your
                          CryptoUniverse account
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          Trading commands require additional confirmation
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          All messages are encrypted and logged for security
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          You can disconnect anytime from the dashboard
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-[#2a2d35]">
                  <Button
                    variant="outline"
                    onClick={onClose}
                    className="bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleConnect}
                    disabled={connecting}
                    className="px-8 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 text-white hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
                  >
                    {connecting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <MessageSquare className="w-4 h-4 mr-2" />
                        Create Connection
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {step === "authenticate" && (
              <div className="space-y-6">
                {/* Authentication Steps */}
                <div className="space-y-4">
                  <div className="p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-300">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                      <h4 className="font-medium text-emerald-400">
                        Connection Created Successfully
                      </h4>
                    </div>
                    <p className="text-sm text-gray-400">
                      Now complete the authentication in Telegram to start using
                      the bot.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-300">
                      Step 1: Open CryptoUniverse Bot
                    </h4>
                    <div className="space-y-2">
                      <Button
                        variant="outline"
                        onClick={openTelegram}
                        className="w-full bg-gradient-to-r from-blue-600/10 to-purple-600/10 text-blue-400 border-blue-500/30 hover:bg-blue-600/20 hover:text-blue-300"
                      >
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Open @CryptoUniverseBot (Recommended)
                      </Button>
                      <p className="text-xs text-gray-400 text-center">
                        This will automatically start the authentication process
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-300">
                      Step 2: Send Authentication Command
                    </h4>
                    <div className="space-y-3">
                      <div className="p-3 bg-[#1a1c23] border border-[#2a2d35] rounded-lg">
                        <p className="text-xs text-gray-400 mb-2">If the bot doesn't start automatically, send:</p>
                        <div className="font-mono text-sm text-blue-400 bg-[#0f1115] p-2 rounded border">
                          /auth {authToken}
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={copyAuthToken}
                        className="w-full bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy Authentication Command
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-300">
                      Step 3: Start Trading
                    </h4>
                    <div className="p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                      <p className="text-sm text-blue-400">
                        Once authenticated, you can use commands like:
                      </p>
                      <ul className="text-sm text-gray-400 mt-3 space-y-2">
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          <code className="text-blue-400">/status</code> - Check
                          account status
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          <code className="text-blue-400">/balance</code> - View
                          portfolio balance
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          <code className="text-blue-400">/buy BTC 100</code> -
                          Buy $100 worth of BTC
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400/50"></div>
                          <code className="text-blue-400">
                            /autonomous start
                          </code>{" "}
                          - Start AI trading
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-[#2a2d35]">
                  <Button
                    variant="outline"
                    onClick={() => setStep("configure")}
                    className="bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
                  >
                    Back to Settings
                  </Button>
                  <Button
                    onClick={onClose}
                    className="px-8 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 text-white hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
                  >
                    Done
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default TelegramConnectionModal;
