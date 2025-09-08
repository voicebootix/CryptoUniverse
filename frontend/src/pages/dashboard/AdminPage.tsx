import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Users,
  Activity,
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Server,
  Database,
  Cpu,
  HardDrive,
  Wifi,
  Zap,
  UserCheck,
  UserX,
  Ban,
  Play,
  Pause,
  RefreshCw,
  Download,
  Upload,
  Eye,
  Search,
  Filter,
  MoreVertical,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import { adminService } from '@/services/adminService';
import { toast } from 'sonner';

// State for real data
interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  is_verified?: boolean;
  created_at: string;
  last_login: string | null;
  tenant_id: string | null;
  credits?: number;
  total_trades?: number;
}

interface SystemMetrics {
  active_users?: number;
  total_trades_today?: number;
  total_volume_24h?: number;
  system_health?: string;
  autonomous_sessions?: number;
  error_rate?: number;
  response_time_avg?: number;
  uptime_percentage?: number;
  // Additional fields that may exist
  cpuUsage?: number;
  memoryUsage?: number;
  diskUsage?: number;
  networkLatency?: number;
}

const auditLogs = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    action: 'Emergency Stop',
    user: 'Admin',
    details: 'Global emergency stop activated',
    severity: 'critical',
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    action: 'User Login',
    user: 'john.smith@example.com',
    details: 'Successful login from 192.168.1.100',
    severity: 'info',
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    action: 'Configuration Change',
    user: 'Admin',
    details: 'Updated autonomous trading intervals',
    severity: 'warning',
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    action: 'Trade Execution',
    user: 'sarah.j@example.com',
    details: 'Large trade executed: 10 BTC @ $50,000',
    severity: 'info',
  },
];

const AdminPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Fetch real data from backend
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data in parallel
      const [usersData, metricsData, pendingData, logsData] = await Promise.all([
        adminService.getUsers(),
        adminService.getMetrics().catch(() => null),
        adminService.getPendingUsers().catch(() => ({ pending_users: [] })),
        adminService.getAuditLogs({ limit: 10 }).catch(() => ({ audit_logs: [] }))
      ]);

      // Update state with real data
      setUsers(usersData.users || []);
      setPendingUsers(pendingData.pending_users || []);
      setSystemMetrics(metricsData);
      setAuditLogs(logsData.audit_logs || []);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchData();
    setIsRefreshing(false);
  };

  const handleEmergencyStop = async () => {
    if (confirm('Are you sure you want to stop all trading activities?')) {
      try {
        await adminService.emergencyStopAll('Manual emergency stop by admin');
        toast.success('Emergency stop activated');
        await fetchData();
      } catch (error) {
        toast.error('Failed to activate emergency stop');
      }
    }
  };

  const handleVerifyUser = async (userId: string) => {
    try {
      const result = await adminService.verifyUser(userId);
      toast.success(`User ${result.user_email} has been verified`);
      await fetchData(); // Refresh data
    } catch (error) {
      toast.error('Failed to verify user');
    }
  };

  const handleUserAction = async (userId: string, action: string) => {
    try {
      const result = await adminService.manageUser(userId, action);
      toast.success(result.action_taken || 'Action completed');
      await fetchData(); // Refresh data
    } catch (error) {
      toast.error(`Failed to ${action} user`);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = (user.full_name || user.email).toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = selectedRole === 'all' || user.role === selectedRole;
    const matchesStatus = selectedStatus === 'all' || user.status === selectedStatus;
    
    return matchesSearch && matchesRole && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="profit">Active</Badge>;
      case 'inactive':
        return <Badge variant="outline">Inactive</Badge>;
      case 'suspended':
        return <Badge variant="destructive">Suspended</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500';
      case 'warning':
        return 'text-yellow-500';
      case 'info':
        return 'text-blue-500';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            Admin Panel
          </h1>
          <p className="text-muted-foreground">
            System administration and user management
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="destructive"
            onClick={handleEmergencyStop}
            className="gap-2"
          >
            <AlertTriangle className="h-4 w-4" />
            Emergency Stop
          </Button>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Health</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-profit" />
                <span className="text-lg font-bold capitalize">{systemMetrics?.system_health || 'Loading...'}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Uptime: {systemMetrics?.uptime_percentage ? `${systemMetrics.uptime_percentage}%` : 'Loading...'}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemMetrics?.active_users || 0}</div>
              <p className="text-xs text-muted-foreground">
                {systemMetrics?.autonomous_sessions || 0} autonomous sessions
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(systemMetrics?.total_trades_today || 0)}</div>
              <p className="text-xs text-muted-foreground">
                Last 24 hours
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-profit">
                {formatPercentage(systemMetrics?.error_rate || 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                Avg response: {systemMetrics?.response_time_avg || 0}ms
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
          <TabsTrigger value="audit">Audit Logs</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* System Resources */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  System Resources
                </CardTitle>
                <CardDescription>Real-time system performance metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">CPU Usage</span>
                    </div>
                    <span className="text-sm font-bold">{systemMetrics?.cpuUsage ?? 0}%</span>
                  </div>
                  <Progress value={systemMetrics?.cpuUsage ?? 0} className="h-2" />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Memory Usage</span>
                    </div>
                    <span className="text-sm font-bold">{systemMetrics?.memoryUsage ?? 0}%</span>
                  </div>
                  <Progress value={systemMetrics?.memoryUsage ?? 0} className="h-2" />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HardDrive className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Disk Usage</span>
                    </div>
                    <span className="text-sm font-bold">{systemMetrics?.diskUsage ?? 0}%</span>
                  </div>
                  <Progress value={systemMetrics?.diskUsage ?? 0} className="h-2" />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Wifi className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Network Latency</span>
                    </div>
                    <span className="text-sm font-bold">{systemMetrics?.networkLatency ?? 0}ms</span>
                  </div>
                  <Progress value={systemMetrics?.networkLatency ?? 0} max={200} className="h-2" />
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
                <CardDescription>Administrative controls and system management</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3">
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div>
                      <p className="font-medium">Maintenance Mode</p>
                      <p className="text-sm text-muted-foreground">
                        Disable trading for system updates
                      </p>
                    </div>
                    <Switch
                      checked={maintenanceMode}
                      onCheckedChange={setMaintenanceMode}
                    />
                  </div>

                  <Button variant="outline" className="justify-start gap-2">
                    <Download className="h-4 w-4" />
                    Export System Logs
                  </Button>

                  <Button variant="outline" className="justify-start gap-2">
                    <Upload className="h-4 w-4" />
                    Import Configuration
                  </Button>

                  <Button variant="destructive" className="justify-start gap-2">
                    <Ban className="h-4 w-4" />
                    Stop All Trading
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users" className="space-y-6">
          {/* Pending Verification Alert */}
          {pendingUsers.length > 0 && (
            <Card className="trading-card border-warning">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-warning">
                  <AlertTriangle className="h-5 w-5" />
                  Pending Verifications ({pendingUsers.length})
                </CardTitle>
                <CardDescription>These users are waiting for admin approval to access the platform</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {pendingUsers.slice(0, 5).map((user) => (
                    <div key={user.id} className="flex items-center justify-between p-3 bg-warning/10 rounded-lg">
                      <div>
                        <p className="font-medium">{user.email}</p>
                        <p className="text-sm text-muted-foreground">
                          Registered: {formatRelativeTime(new Date(user.created_at))}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => handleVerifyUser(user.id)}
                        className="gap-2"
                      >
                        <UserCheck className="h-4 w-4" />
                        Verify Now
                      </Button>
                    </div>
                  ))}
                  {pendingUsers.length > 5 && (
                    <p className="text-sm text-muted-foreground text-center">
                      And {pendingUsers.length - 5} more users pending...
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* User Filters */}
          <Card className="trading-card">
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>Manage user accounts and permissions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search users..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                
                <Select value={selectedRole} onValueChange={setSelectedRole}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Roles</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="trader">Trader</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                    <SelectItem value="suspended">Suspended</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Users Table */}
          <Card className="trading-card">
            <CardContent className="p-0">
              <div className="space-y-0">
                {filteredUsers.map((user, index) => (
                  <motion.div
                    key={user.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-center justify-between p-6 border-b border-border last:border-b-0"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="font-medium text-sm">
                          {(user.full_name || user.email).split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                        </span>
                      </div>
                      
                      <div>
                        <p className="font-medium">{user.full_name || user.email}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                        <div className="flex items-center gap-2 mt-1">
                          {getStatusBadge(user.status)}
                          <Badge variant="outline" className="text-xs capitalize">
                            {user.role}
                          </Badge>
                          {user.status === 'pending_verification' && (
                            <Badge variant="warning" className="text-xs">
                              Needs Verification
                            </Badge>
                          )}
                          {user.is_verified === false && user.status !== 'pending_verification' && (
                            <Badge variant="destructive" className="text-xs">
                              Not Verified
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="font-medium">{user.credits ? `${user.credits} credits` : 'No credits'}</p>
                      <p className="text-sm text-muted-foreground">
                        {user.total_trades || 0} trades total
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {user.last_login ? `Last login: ${formatRelativeTime(new Date(user.last_login))}` : 'Never logged in'}
                      </p>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {(user.status === 'pending_verification' || !user.is_verified) && (
                          <DropdownMenuItem onClick={() => handleVerifyUser(user.id)}>
                            <UserCheck className="mr-2 h-4 w-4 text-green-500" />
                            Verify User
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem onClick={() => handleUserAction(user.id, 'activate')}>
                          <UserCheck className="mr-2 h-4 w-4" />
                          Activate User
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUserAction(user.id, 'deactivate')}>
                          <UserX className="mr-2 h-4 w-4" />
                          Deactivate User
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUserAction(user.id, 'suspend')} className="text-destructive">
                          <Ban className="mr-2 h-4 w-4" />
                          Suspend User
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Tab */}
        <TabsContent value="system" className="space-y-6">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle>System Configuration</CardTitle>
              <CardDescription>Configure system-wide settings and parameters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <Label className="text-base font-medium">Trading Parameters</Label>
                  
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="global-stop">Global Emergency Stop</Label>
                      <Switch id="global-stop" />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <Label htmlFor="rate-limiting">Rate Limiting</Label>
                      <Switch id="rate-limiting" defaultChecked />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <Label htmlFor="auto-backup">Automatic Backups</Label>
                      <Switch id="auto-backup" defaultChecked />
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-base font-medium">Service Intervals</Label>
                  
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <Label htmlFor="health-monitor" className="text-sm">Health Monitor</Label>
                      <Input id="health-monitor" placeholder="60s" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <Label htmlFor="metrics-collector" className="text-sm">Metrics Collector</Label>
                      <Input id="metrics-collector" placeholder="300s" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <Label htmlFor="autonomous-cycles" className="text-sm">Autonomous Cycles</Label>
                      <Input id="autonomous-cycles" placeholder="900s" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button variant="outline">Reset to Defaults</Button>
                <Button>Save Configuration</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Logs Tab */}
        <TabsContent value="audit" className="space-y-6">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle>Audit Logs</CardTitle>
              <CardDescription>System activity and security events</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {auditLogs.map((log, index) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-2 h-2 rounded-full ${
                        log.severity === 'critical' ? 'bg-red-500' :
                        log.severity === 'warning' ? 'bg-yellow-500' :
                        'bg-blue-500'
                      }`} />
                      
                      <div>
                        <p className="font-medium">{log.action || log.event_type}</p>
                        <p className="text-sm text-muted-foreground">{log.details || JSON.stringify(log.event_data?.details || {})}</p>
                        <p className="text-xs text-muted-foreground">
                          by {log.user_email || log.user || 'Unknown'} • {formatRelativeTime(new Date(log.created_at || log.timestamp))}
                        </p>
                      </div>
                    </div>

                    <Badge
                      variant={
                        log.severity === 'critical' ? 'destructive' :
                        log.severity === 'warning' ? 'warning' :
                        'outline'
                      }
                      className="capitalize"
                    >
                      {log.severity}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-6">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle>Platform Settings</CardTitle>
              <CardDescription>Configure platform-wide preferences and features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">New User Registration</Label>
                    <p className="text-sm text-muted-foreground">
                      Allow new users to register accounts
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Email Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Send system alerts and updates via email
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">API Rate Limiting</Label>
                    <p className="text-sm text-muted-foreground">
                      Enforce API rate limits for external requests
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Debug Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable detailed logging for troubleshooting
                    </p>
                  </div>
                  <Switch />
                </div>
              </div>

              <div className="flex justify-end">
                <Button>Save Settings</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdminPage;
