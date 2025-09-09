import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  User,
  Shield,
  Bell,
  CreditCard,
  Globe,
  Palette,
  Key,
  Smartphone,
  Mail,
  Eye,
  EyeOff,
  Save,
  AlertTriangle
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useToast } from '@/components/ui/use-toast';
import { useAuthStore } from '@/store/authStore';
import { usePaperModeStore } from '@/store/paperModeStore';
import { apiClient } from '@/lib/api/client';

interface UserSettings {
  profile: {
    firstName: string;
    lastName: string;
    email: string;
    avatar: string;
    timezone: string;
    language: string;
  };
  security: {
    twoFactorEnabled: boolean;
    emailNotifications: boolean;
    smsNotifications: boolean;
    loginAlerts: boolean;
  };
  trading: {
    defaultPaperMode: boolean;
    riskLevel: 'conservative' | 'moderate' | 'aggressive';
    maxPositionSize: number;
    stopLossDefault: number;
    takeProfitDefault: number;
  };
  notifications: {
    tradeExecutions: boolean;
    priceAlerts: boolean;
    marketNews: boolean;
    systemUpdates: boolean;
    emailDigest: boolean;
    pushNotifications: boolean;
  };
  appearance: {
    theme: 'light' | 'dark' | 'system';
    currency: string;
    numberFormat: 'us' | 'eu';
    chartType: 'candlestick' | 'line' | 'area';
  };
}

const SettingsPage: React.FC = () => {
  const { toast } = useToast();
  const { user, setUser } = useAuthStore();
  const { isPaperMode } = usePaperModeStore();
  
  const [activeTab, setActiveTab] = useState('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [settings, setSettings] = useState<UserSettings>({
    profile: {
      firstName: user?.full_name?.split(' ')[0] || '',
      lastName: user?.full_name?.split(' ')[1] || '',
      email: user?.email || '',
      avatar: user?.avatar_url || '',
      timezone: 'UTC',
      language: 'en'
    },
    security: {
      twoFactorEnabled: false,
      emailNotifications: true,
      smsNotifications: false,
      loginAlerts: true
    },
    trading: {
      defaultPaperMode: isPaperMode,
      riskLevel: 'moderate',
      maxPositionSize: 1000,
      stopLossDefault: 5,
      takeProfitDefault: 10
    },
    notifications: {
      tradeExecutions: true,
      priceAlerts: true,
      marketNews: false,
      systemUpdates: true,
      emailDigest: false,
      pushNotifications: true
    },
    appearance: {
      theme: 'system',
      currency: 'USD',
      numberFormat: 'us',
      chartType: 'candlestick'
    }
  });

  useEffect(() => {
    fetchUserSettings();
  }, []);

  const fetchUserSettings = async () => {
    try {
      const response = await apiClient.get('/user/settings');
      if (response.data.success) {
        setSettings(response.data.data);
      }
    } catch (error) {
      // Use default settings if fetch fails
    }
  };

  const saveSettings = async (section?: keyof UserSettings) => {
    setIsLoading(true);
    try {
      const payload = section ? { [section]: settings[section] } : settings;
      
      const response = await apiClient.put('/user/settings', payload);
      
      if (response.data.success) {
        toast({
          title: "Settings Saved",
          description: `${section ? section.charAt(0).toUpperCase() + section.slice(1) : 'All'} settings updated successfully`
        });
        
        if (section === 'profile' && user) {
          setUser({
            ...user,
            full_name: `${settings.profile.firstName} ${settings.profile.lastName}`,
            avatar_url: settings.profile.avatar
          });
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save settings. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const changePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: "Error",
        description: "New passwords do not match",
        variant: "destructive"
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: "Error", 
        description: "Password must be at least 8 characters",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post('/user/change-password', {
        currentPassword,
        newPassword
      });
      
      toast({
        title: "Password Changed",
        description: "Your password has been updated successfully"
      });
      
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to change password. Please check your current password.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Settings className="h-8 w-8 text-primary" />
            Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your account preferences and trading configurations
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Security
            </TabsTrigger>
            <TabsTrigger value="trading" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Trading
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="appearance" className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              Appearance
            </TabsTrigger>
          </TabsList>

          {/* Profile Settings */}
          <TabsContent value="profile" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>
                  Update your account details and personal information
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center gap-6">
                  <Avatar className="h-20 w-20">
                    <AvatarImage src={settings.profile.avatar} />
                    <AvatarFallback className="text-lg">
                      {settings.profile.firstName?.[0]}{settings.profile.lastName?.[0]}
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <Button variant="outline">Change Avatar</Button>
                    <p className="text-sm text-muted-foreground">
                      Upload a new profile picture
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input
                      id="firstName"
                      value={settings.profile.firstName}
                      onChange={(e) => setSettings({
                        ...settings,
                        profile: { ...settings.profile, firstName: e.target.value }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input
                      id="lastName"
                      value={settings.profile.lastName}
                      onChange={(e) => setSettings({
                        ...settings,
                        profile: { ...settings.profile, lastName: e.target.value }
                      })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={settings.profile.email}
                    onChange={(e) => setSettings({
                      ...settings,
                      profile: { ...settings.profile, email: e.target.value }
                    })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="timezone">Timezone</Label>
                    <Select
                      value={settings.profile.timezone}
                      onValueChange={(value) => setSettings({
                        ...settings,
                        profile: { ...settings.profile, timezone: value }
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UTC">UTC</SelectItem>
                        <SelectItem value="America/New_York">Eastern Time</SelectItem>
                        <SelectItem value="America/Chicago">Central Time</SelectItem>
                        <SelectItem value="America/Denver">Mountain Time</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                        <SelectItem value="Europe/London">London</SelectItem>
                        <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="language">Language</Label>
                    <Select
                      value={settings.profile.language}
                      onValueChange={(value) => setSettings({
                        ...settings,
                        profile: { ...settings.profile, language: value }
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="es">Spanish</SelectItem>
                        <SelectItem value="fr">French</SelectItem>
                        <SelectItem value="de">German</SelectItem>
                        <SelectItem value="ja">Japanese</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button onClick={() => saveSettings('profile')} disabled={isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Profile
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Settings */}
          <TabsContent value="security" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Password</CardTitle>
                <CardDescription>
                  Change your account password
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="currentPassword"
                      type={showCurrentPassword ? "text" : "password"}
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    >
                      {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <div className="relative">
                    <Input
                      id="newPassword"
                      type={showNewPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                    >
                      {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>

                <Button onClick={changePassword} disabled={isLoading}>
                  <Key className="h-4 w-4 mr-2" />
                  Change Password
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Security Preferences</CardTitle>
                <CardDescription>
                  Manage your security and notification settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Two-Factor Authentication</Label>
                    <p className="text-sm text-muted-foreground">
                      Add an extra layer of security to your account
                    </p>
                  </div>
                  <Switch
                    checked={settings.security.twoFactorEnabled}
                    onCheckedChange={(checked) => setSettings({
                      ...settings,
                      security: { ...settings.security, twoFactorEnabled: checked }
                    })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Email Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive security alerts via email
                    </p>
                  </div>
                  <Switch
                    checked={settings.security.emailNotifications}
                    onCheckedChange={(checked) => setSettings({
                      ...settings,
                      security: { ...settings.security, emailNotifications: checked }
                    })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Login Alerts</Label>
                    <p className="text-sm text-muted-foreground">
                      Get notified of new device logins
                    </p>
                  </div>
                  <Switch
                    checked={settings.security.loginAlerts}
                    onCheckedChange={(checked) => setSettings({
                      ...settings,
                      security: { ...settings.security, loginAlerts: checked }
                    })}
                  />
                </div>

                <Button onClick={() => saveSettings('security')} disabled={isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Security Settings
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trading Settings */}
          <TabsContent value="trading" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Trading Defaults</CardTitle>
                <CardDescription>
                  Configure your default trading preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Default Paper Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Start new sessions in paper trading mode
                    </p>
                  </div>
                  <Switch
                    checked={settings.trading.defaultPaperMode}
                    onCheckedChange={(checked) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, defaultPaperMode: checked }
                    })}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Risk Level</Label>
                  <Select
                    value={settings.trading.riskLevel}
                    onValueChange={(value) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, riskLevel: value as any }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="conservative">Conservative</SelectItem>
                      <SelectItem value="moderate">Moderate</SelectItem>
                      <SelectItem value="aggressive">Aggressive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Max Position Size (USDT)</Label>
                  <Input
                    type="number"
                    value={settings.trading.maxPositionSize}
                    onChange={(e) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, maxPositionSize: parseFloat(e.target.value) }
                    })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Default Stop Loss (%)</Label>
                    <Input
                      type="number"
                      value={settings.trading.stopLossDefault}
                      onChange={(e) => setSettings({
                        ...settings,
                        trading: { ...settings.trading, stopLossDefault: parseFloat(e.target.value) }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Default Take Profit (%)</Label>
                    <Input
                      type="number"
                      value={settings.trading.takeProfitDefault}
                      onChange={(e) => setSettings({
                        ...settings,
                        trading: { ...settings.trading, takeProfitDefault: parseFloat(e.target.value) }
                      })}
                    />
                  </div>
                </div>

                <Button onClick={() => saveSettings('trading')} disabled={isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Trading Settings
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications */}
          <TabsContent value="notifications" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Choose what notifications you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {Object.entries({
                  tradeExecutions: 'Trade Executions',
                  priceAlerts: 'Price Alerts',
                  marketNews: 'Market News',
                  systemUpdates: 'System Updates',
                  emailDigest: 'Daily Email Digest',
                  pushNotifications: 'Push Notifications'
                }).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>{label}</Label>
                      <p className="text-sm text-muted-foreground">
                        {key === 'tradeExecutions' && 'Get notified when trades are executed'}
                        {key === 'priceAlerts' && 'Receive alerts for price movements'}
                        {key === 'marketNews' && 'Stay updated with market news'}
                        {key === 'systemUpdates' && 'Important system announcements'}
                        {key === 'emailDigest' && 'Daily summary of your trading activity'}
                        {key === 'pushNotifications' && 'Browser push notifications'}
                      </p>
                    </div>
                    <Switch
                      checked={settings.notifications[key as keyof typeof settings.notifications]}
                      onCheckedChange={(checked) => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, [key]: checked }
                      })}
                    />
                  </div>
                ))}

                <Button onClick={() => saveSettings('notifications')} disabled={isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Notification Settings
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Appearance */}
          <TabsContent value="appearance" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Appearance & Display</CardTitle>
                <CardDescription>
                  Customize how the interface looks and feels
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Theme</Label>
                  <Select
                    value={settings.appearance.theme}
                    onValueChange={(value) => setSettings({
                      ...settings,
                      appearance: { ...settings.appearance, theme: value as any }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Currency</Label>
                  <Select
                    value={settings.appearance.currency}
                    onValueChange={(value) => setSettings({
                      ...settings,
                      appearance: { ...settings.appearance, currency: value }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">USD ($)</SelectItem>
                      <SelectItem value="EUR">EUR (€)</SelectItem>
                      <SelectItem value="GBP">GBP (£)</SelectItem>
                      <SelectItem value="JPY">JPY (¥)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Chart Type</Label>
                  <Select
                    value={settings.appearance.chartType}
                    onValueChange={(value) => setSettings({
                      ...settings,
                      appearance: { ...settings.appearance, chartType: value as any }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="candlestick">Candlestick</SelectItem>
                      <SelectItem value="line">Line</SelectItem>
                      <SelectItem value="area">Area</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button onClick={() => saveSettings('appearance')} disabled={isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Appearance Settings
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Global Save Button */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <AlertTriangle className="h-4 w-4" />
                Changes are saved immediately when you click individual save buttons
              </div>
              <Button 
                onClick={() => saveSettings()} 
                disabled={isLoading}
                size="lg"
              >
                <Save className="h-4 w-4 mr-2" />
                Save All Settings
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default SettingsPage;
