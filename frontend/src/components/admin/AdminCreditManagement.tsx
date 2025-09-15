import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Search,
  Send,
  CreditCard,
  Users,
  TrendingUp,
  DollarSign,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Settings,
  User,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  Download,
  RefreshCw
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatNumber, formatRelativeTime } from '@/lib/utils';

interface UserCreditInfo {
  user_id: string;
  email: string;
  full_name: string;
  total_credits: number;
  available_credits: number;
  used_credits: number;
  profit_potential: number;
  profit_earned: number;
  last_activity: string;
  account_status: string;
}

interface CreditTransaction {
  id: string;
  user_id: string;
  user_email: string;
  amount: number;
  transaction_type: string;
  description: string;
  created_at: string;
  created_by: string;
  status: string;
  reference_id?: string;
}

interface PlatformAnalytics {
  total_credits_issued: number;
  total_credits_used: number;
  total_revenue_usd: number;
  total_profit_shared: number;
  active_users: number;
  strategies_purchased: number;
  platform_fee_collected: number;
  daily_credit_usage: Array<{ date: string; credits_used: number; revenue: number }>;
}

const AdminCreditManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserCreditInfo | null>(null);
  const [creditAmount, setCreditAmount] = useState('');
  const [transferReason, setTransferReason] = useState('');
  const [showTransferDialog, setShowTransferDialog] = useState(false);

  // Fetch platform analytics
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['admin-credit-analytics'],
    queryFn: async () => {
      const response = await apiClient.get('/admin/credits/analytics');
      return response.data as PlatformAnalytics;
    },
    refetchInterval: 30000,
    retry: 2
  });

  // Search users
  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['admin-user-search', searchQuery],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return [];
      const response = await apiClient.get('/admin/users/search', {
        params: { q: searchQuery, include_credits: true }
      });
      return response.data.users as UserCreditInfo[];
    },
    enabled: searchQuery.length >= 2,
    retry: 2
  });

  // Fetch recent credit transactions
  const { data: recentTransactions, isLoading: transactionsLoading } = useQuery({
    queryKey: ['admin-credit-transactions'],
    queryFn: async () => {
      const response = await apiClient.get('/admin/credits/transactions', {
        params: { limit: 50, include_user_info: true }
      });
      return response.data.transactions as CreditTransaction[];
    },
    refetchInterval: 30000,
    retry: 2
  });

  // Credit transfer mutation
  const transferCreditsMutation = useMutation({
    mutationFn: async ({ userId, amount, reason }: { userId: string; amount: number; reason: string }) => {
      const response = await apiClient.post('/admin/credits/transfer', {
        to_user_id: userId,
        amount: amount,
        reason: reason,
        transaction_type: 'admin_grant'
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Successfully transferred ${data.amount} credits`);
      queryClient.invalidateQueries({ queryKey: ['admin-credit-analytics'] });
      queryClient.invalidateQueries({ queryKey: ['admin-credit-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['admin-user-search'] });
      setCreditAmount('');
      setTransferReason('');
      setShowTransferDialog(false);
    },
    onError: (error: any) => {
      toast.error(`Transfer failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Bulk operations mutation
  const bulkOperationMutation = useMutation({
    mutationFn: async ({ operation, params }: { operation: string; params: any }) => {
      const response = await apiClient.post(`/admin/credits/bulk/${operation}`, params);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Bulk operation completed: ${data.affected_users} users processed`);
      queryClient.invalidateQueries({ queryKey: ['admin-credit-analytics'] });
    },
    onError: (error: any) => {
      toast.error(`Bulk operation failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  const handleCreditTransfer = () => {
    if (!selectedUser || !creditAmount || !transferReason) {
      toast.error('Please fill in all required fields');
      return;
    }

    const amount = parseInt(creditAmount.trim(), 10);
    if (!Number.isInteger(amount) || Number.isNaN(amount) || amount < 1 || amount > 10000) {
      toast.error('Credit amount must be a valid integer between 1 and 10,000');
      return;
    }

    transferCreditsMutation.mutate({
      userId: selectedUser.user_id,
      amount: amount,
      reason: transferReason
    });
  };

  const getStatusBadge = (status: string) => {
    const config = {
      active: { variant: 'default' as const, icon: CheckCircle },
      suspended: { variant: 'destructive' as const, icon: AlertTriangle },
      pending: { variant: 'secondary' as const, icon: Clock },
    };
    
    const { variant, icon: Icon } = config[status as keyof typeof config] || config.active;
    
    return (
      <Badge variant={variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Credit Management</h2>
          <p className="text-muted-foreground">
            Manage user credits, transfers, and platform analytics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => queryClient.invalidateQueries()}
            disabled={analyticsLoading || searchLoading || transactionsLoading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh All
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Platform Overview</TabsTrigger>
          <TabsTrigger value="users">User Management</TabsTrigger>
          <TabsTrigger value="transactions">Transaction History</TabsTrigger>
          <TabsTrigger value="bulk">Bulk Operations</TabsTrigger>
        </TabsList>

        {/* Platform Overview */}
        <TabsContent value="overview" className="space-y-4">
          {analyticsLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map(i => (
                <Card key={i}>
                  <CardHeader className="pb-2">
                    <div className="h-4 bg-muted rounded animate-pulse" />
                  </CardHeader>
                  <CardContent>
                    <div className="h-8 bg-muted rounded animate-pulse" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : analytics ? (
            <>
              {/* Key Metrics */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Credits Issued</CardTitle>
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatNumber(analytics.total_credits_issued)}</div>
                    <p className="text-xs text-muted-foreground">
                      {formatNumber(analytics.total_credits_used)} used
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Platform Revenue</CardTitle>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(analytics.total_revenue_usd)}</div>
                    <p className="text-xs text-muted-foreground">
                      {formatCurrency(analytics.platform_fee_collected)} from profit sharing
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                    <Users className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatNumber(analytics.active_users)}</div>
                    <p className="text-xs text-muted-foreground">
                      {formatNumber(analytics.strategies_purchased)} strategies purchased
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Profit Shared</CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(analytics.total_profit_shared)}</div>
                    <p className="text-xs text-muted-foreground">
                      25% platform fee
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Daily Usage Chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Daily Credit Usage</CardTitle>
                  <CardDescription>Credit consumption and revenue over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    <BarChart3 className="h-8 w-8 mr-2" />
                    Chart visualization will be implemented with recharts
                  </div>
                </CardContent>
              </Card>
            </>
          ) : null}
        </TabsContent>

        {/* User Management */}
        <TabsContent value="users" className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search users by email, name, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Dialog open={showTransferDialog} onOpenChange={setShowTransferDialog}>
              <DialogTrigger asChild>
                <Button disabled={!selectedUser}>
                  <Send className="h-4 w-4 mr-2" />
                  Send Credits
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Transfer Credits</DialogTitle>
                  <DialogDescription>
                    Send credits to {selectedUser?.full_name} ({selectedUser?.email})
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="amount">Credit Amount</Label>
                    <Input
                      id="amount"
                      type="number"
                      placeholder="Enter credit amount"
                      value={creditAmount}
                      onChange={(e) => setCreditAmount(e.target.value)}
                      min="1"
                      max="10000"
                    />
                  </div>
                  <div>
                    <Label htmlFor="reason">Reason for Transfer</Label>
                    <Textarea
                      id="reason"
                      placeholder="Enter reason for credit transfer..."
                      value={transferReason}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTransferReason(e.target.value)}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setShowTransferDialog(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreditTransfer}
                      disabled={transferCreditsMutation.isPending}
                    >
                      {transferCreditsMutation.isPending ? 'Transferring...' : 'Transfer Credits'}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {/* Search Results */}
          {searchQuery && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Search Results</CardTitle>
              </CardHeader>
              <CardContent>
                {searchLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                  </div>
                ) : searchResults && searchResults.length > 0 ? (
                  <div className="space-y-2">
                    {searchResults.map((user) => (
                      <div
                        key={user.user_id}
                        className={`p-3 border rounded cursor-pointer transition-colors ${
                          selectedUser?.user_id === user.user_id
                            ? 'border-primary bg-primary/5'
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => setSelectedUser(user)}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{user.full_name}</div>
                            <div className="text-sm text-muted-foreground">{user.email}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">{formatNumber(user.available_credits)} credits</div>
                            <div className="text-sm text-muted-foreground">
                              {formatCurrency(user.profit_potential)} potential
                            </div>
                          </div>
                          {getStatusBadge(user.account_status)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : searchQuery.length >= 2 ? (
                  <div className="text-center py-4 text-muted-foreground">
                    No users found matching "{searchQuery}"
                  </div>
                ) : null}
              </CardContent>
            </Card>
          )}

          {/* Selected User Details */}
          {selectedUser && (
            <Card>
              <CardHeader>
                <CardTitle>User Credit Details</CardTitle>
                <CardDescription>{selectedUser.full_name} ({selectedUser.email})</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <div className="text-sm text-muted-foreground">Available Credits</div>
                    <div className="text-2xl font-bold text-green-500">
                      {formatNumber(selectedUser.available_credits)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Total Credits</div>
                    <div className="text-2xl font-bold">
                      {formatNumber(selectedUser.total_credits)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Used Credits</div>
                    <div className="text-2xl font-bold text-blue-500">
                      {formatNumber(selectedUser.used_credits)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Profit Potential</div>
                    <div className="text-xl font-bold text-purple-500">
                      {formatCurrency(selectedUser.profit_potential)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Profit Earned</div>
                    <div className="text-xl font-bold text-green-500">
                      {formatCurrency(selectedUser.profit_earned)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Last Activity</div>
                    <div className="text-sm">
                      {selectedUser.last_activity ? 
                        (() => {
                          const date = new Date(selectedUser.last_activity);
                          return isNaN(date.getTime()) ? 'No activity' : formatRelativeTime(date);
                        })() 
                        : 'No activity'
                      }
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Transaction History */}
        <TabsContent value="transactions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Credit Transactions</CardTitle>
              <CardDescription>Latest credit transfers and operations</CardDescription>
            </CardHeader>
            <CardContent>
              {transactionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : recentTransactions && recentTransactions.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentTransactions.map((transaction) => (
                      <TableRow key={transaction.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{transaction.user_email}</div>
                            <div className="text-sm text-muted-foreground">
                              ID: {transaction.user_id.slice(0, 8)}...
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {transaction.transaction_type.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className={`font-medium ${transaction.amount > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {transaction.amount > 0 ? '+' : ''}{formatNumber(transaction.amount)}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {transaction.description}
                        </TableCell>
                        <TableCell>
                          {new Date(transaction.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(transaction.status)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No recent transactions found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Bulk Operations */}
        <TabsContent value="bulk" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Bulk Credit Operations</CardTitle>
              <CardDescription>
                Perform bulk operations on user credits. Use with extreme caution.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="border-orange-200">
                  <CardHeader>
                    <CardTitle className="text-sm">Welcome Package Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-4">
                      Send welcome package ($100 credits) to new users who haven't received it yet.
                    </p>
                    <Button
                      onClick={() => bulkOperationMutation.mutate({
                        operation: 'welcome-package',
                        params: { dry_run: false }
                      })}
                      disabled={bulkOperationMutation.isPending}
                      className="w-full"
                    >
                      Distribute Welcome Packages
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-red-200">
                  <CardHeader>
                    <CardTitle className="text-sm">Emergency Credit Freeze</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-4">
                      Temporarily freeze all credit usage across the platform.
                    </p>
                    <Button
                      variant="destructive"
                      onClick={() => bulkOperationMutation.mutate({
                        operation: 'freeze-credits',
                        params: { reason: 'Emergency freeze activated by admin' }
                      })}
                      disabled={bulkOperationMutation.isPending}
                      className="w-full"
                    >
                      Emergency Freeze
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdminCreditManagement;