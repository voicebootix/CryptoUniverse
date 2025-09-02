import React, { useState } from 'react';
import { motion } from 'framer-motion';
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
  Info
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';

interface TelegramConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (config: TelegramConfig) => Promise<void>;
  connecting: boolean;
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
  connecting
}) => {
  const [config, setConfig] = useState<TelegramConfig>({
    telegram_username: '',
    enable_notifications: true,
    enable_trading: false,
    enable_voice_commands: false,
    daily_trade_limit: 10,
    max_trade_amount: 1000
  });
  const [authToken, setAuthToken] = useState<string>('');
  const [step, setStep] = useState<'configure' | 'authenticate'>('configure');
  const { toast } = useToast();

  const handleConnect = async () => {
    try {
      const response = await fetch('/api/v1/telegram/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      const result = await response.json();
      
      if (result.connection_id) {
        setAuthToken(result.auth_token);
        setStep('authenticate');
        
        toast({
          title: "Connection Created",
          description: "Follow the authentication steps to complete setup",
          variant: "default",
        });
      } else {
        throw new Error(result.detail || 'Connection failed');
      }
      
    } catch (error: any) {
      toast({
        title: "Connection Failed",
        description: error.message || 'Failed to create Telegram connection',
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
    window.open('https://t.me/CryptoUniverseBot', '_blank');
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
        <Card className="p-6 bg-white">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <MessageSquare className="w-6 h-6 text-blue-500" />
                Connect Telegram
              </h2>
              <p className="text-gray-500 mt-1">
                {step === 'configure' 
                  ? 'Configure your Telegram integration settings'
                  : 'Complete authentication in Telegram'
                }
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:bg-gray-100"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          {step === 'configure' && (
            <div className="space-y-6">
              {/* Configuration Form */}
              <div className="space-y-4">
                <div>
                  <Label htmlFor="username">Telegram Username (Optional)</Label>
                  <Input
                    id="username"
                    placeholder="@yourusername"
                    value={config.telegram_username}
                    onChange={(e) => setConfig(prev => ({ ...prev, telegram_username: e.target.value }))}
                  />
                  <p className="text-sm text-gray-600 mt-1">
                    Optional: Your Telegram username for identification
                  </p>
                </div>

                {/* Feature Toggles */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div>
                      <Label className="flex items-center gap-2">
                        <Bell className="w-4 h-4" />
                        Enable Notifications
                      </Label>
                      <p className="text-sm text-gray-600">
                        Receive trade alerts, portfolio updates, and system notifications
                      </p>
                    </div>
                    <Switch
                      checked={config.enable_notifications}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, enable_notifications: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div>
                      <Label className="flex items-center gap-2">
                        <Zap className="w-4 h-4" />
                        Enable Trading Commands
                      </Label>
                      <p className="text-sm text-gray-600">
                        Execute trades directly from Telegram chat
                      </p>
                    </div>
                    <Switch
                      checked={config.enable_trading}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, enable_trading: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                    <div>
                      <Label className="flex items-center gap-2">
                        <Bot className="w-4 h-4" />
                        Enable Voice Commands
                      </Label>
                      <p className="text-sm text-gray-600">
                        Use voice messages for natural language trading
                      </p>
                    </div>
                    <Switch
                      checked={config.enable_voice_commands}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, enable_voice_commands: checked }))}
                    />
                  </div>
                </div>

                {/* Trading Limits */}
                {config.enable_trading && (
                  <div className="space-y-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <h4 className="font-medium text-amber-900">Trading Safety Limits</h4>
                    
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Daily Trade Limit</Label>
                        <Input
                          type="number"
                          min="1"
                          max="100"
                          value={config.daily_trade_limit}
                          onChange={(e) => setConfig(prev => ({ 
                            ...prev, 
                            daily_trade_limit: parseInt(e.target.value) || 10 
                          }))}
                        />
                        <p className="text-xs text-amber-700">Maximum trades per day via Telegram</p>
                      </div>

                      <div>
                        <Label>Max Trade Amount (USD)</Label>
                        <Input
                          type="number"
                          min="100"
                          max="50000"
                          value={config.max_trade_amount}
                          onChange={(e) => setConfig(prev => ({ 
                            ...prev, 
                            max_trade_amount: parseInt(e.target.value) || 1000 
                          }))}
                        />
                        <p className="text-xs text-amber-700">Maximum amount per trade</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Security Notice */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900 mb-1">Security & Privacy</h4>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li>• Your Telegram is linked securely to your CryptoUniverse account</li>
                      <li>• Trading commands require additional confirmation</li>
                      <li>• All messages are encrypted and logged for security</li>
                      <li>• You can disconnect anytime from the dashboard</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleConnect}
                  disabled={connecting}
                  className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white"
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

          {step === 'authenticate' && (
            <div className="space-y-6">
              {/* Authentication Steps */}
              <div className="space-y-4">
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <h4 className="font-medium text-green-900">Connection Created Successfully</h4>
                  </div>
                  <p className="text-sm text-green-700">
                    Now complete the authentication in Telegram to start using the bot.
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium">Step 1: Open CryptoUniverse Bot</h4>
                  <Button
                    variant="outline"
                    onClick={openTelegram}
                    className="w-full"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Open @CryptoUniverseBot in Telegram
                  </Button>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium">Step 2: Send Authentication Command</h4>
                  <div className="p-3 bg-gray-100 rounded-lg font-mono text-sm">
                    /auth {authToken}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={copyAuthToken}
                    className="w-full"
                  >
                    <Copy className="w-4 h-4 mr-2" />
                    Copy Authentication Command
                  </Button>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium">Step 3: Start Trading</h4>
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-700">
                      Once authenticated, you can use commands like:
                    </p>
                    <ul className="text-sm text-blue-700 mt-2 space-y-1">
                      <li>• <code>/status</code> - Check account status</li>
                      <li>• <code>/balance</code> - View portfolio balance</li>
                      <li>• <code>/buy BTC 100</code> - Buy $100 worth of BTC</li>
                      <li>• <code>/autonomous start</code> - Start AI trading</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button variant="outline" onClick={() => setStep('configure')}>
                  Back to Settings
                </Button>
                <Button onClick={onClose} className="px-8">
                  Done
                </Button>
              </div>
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
};

export default TelegramConnectionModal;