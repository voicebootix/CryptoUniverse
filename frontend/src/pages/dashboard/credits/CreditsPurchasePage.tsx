import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  ArrowLeft,
  CreditCard,
  Zap,
  TrendingUp,
  Shield,
  Star,
  Bitcoin,
  Coins,
  DollarSign,
  CheckCircle,
  AlertTriangle,
  Copy,
  Clock,
  ExternalLink
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';
import { toast } from 'sonner';

interface PurchaseOption {
  package_name: string;
  usd_cost: number;
  credits: number;
  profit_potential: number;
  bonus_credits: number;
  strategies_included: number;
  popular: boolean;
}

interface PaymentMethod {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
}

const CreditsPurchasePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedPackage, setSelectedPackage] = useState<PurchaseOption | null>(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<string>('usdc');
  const [customAmount, setCustomAmount] = useState<string>('');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentData, setPaymentData] = useState<any>(null);
  const [paymentStatus, setPaymentStatus] = useState<'pending' | 'checking' | 'confirmed' | 'failed'>('pending');
  const [timeRemaining, setTimeRemaining] = useState<number>(0);

  const paymentMethods: PaymentMethod[] = [
    {
      id: 'bitcoin',
      name: 'Bitcoin',
      icon: <Bitcoin className="h-5 w-5" />,
      description: 'Secure, decentralized payments'
    },
    {
      id: 'ethereum',
      name: 'Ethereum',
      icon: <Coins className="h-5 w-5" />,
      description: 'Fast smart contract payments'
    },
    {
      id: 'usdc',
      name: 'USDC',
      icon: <DollarSign className="h-5 w-5" />,
      description: 'Stable USD-pegged crypto'
    },
    {
      id: 'usdt',
      name: 'USDT',
      icon: <DollarSign className="h-5 w-5" />,
      description: 'Tether stablecoin'
    }
  ];

  // Fetch purchase options
  const { data: purchaseOptions, isLoading } = useQuery({
    queryKey: ['credit-purchase-options'],
    queryFn: async () => {
      const response = await apiClient.get('/credits/purchase-options');
      return response.data.purchase_options || [];
    }
  });

  // Purchase credits mutation
  const purchaseMutation = useMutation({
    mutationFn: async ({ amount, paymentMethod }: { amount: number; paymentMethod: string }) => {
      const response = await apiClient.post('/credits/purchase', {
        amount_usd: amount,
        payment_method: paymentMethod
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Payment request generated successfully!');
      // Store payment data and show payment modal
      setPaymentData(data);
      setPaymentStatus('pending');
      
      // Calculate expiry countdown
      if (data.expires_at) {
        const expiryTime = new Date(data.expires_at).getTime();
        const now = Date.now();
        setTimeRemaining(Math.max(0, Math.floor((expiryTime - now) / 1000)));
      }
      
      // Open QR code in new tab if available
      if (data.qr_code_url) {
        window.open(data.qr_code_url, '_blank');
      }
      
      setShowPaymentModal(true);
      
      // Start polling for payment status
      startStatusPolling(data.payment_id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Purchase failed');
    }
  });
  
  // Countdown timer for payment expiry
  useEffect(() => {
    if (timeRemaining > 0) {
      const timer = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [timeRemaining]);
  
  // Status polling for payment confirmation
  const startStatusPolling = (paymentId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/credits/payment-status/${paymentId}`);
        const status = response.data.status;
        
        if (status === 'confirmed') {
          setPaymentStatus('confirmed');
          clearInterval(pollInterval);
          // Invalidate credits cache to refresh balance
          queryClient.invalidateQueries({ queryKey: ['user-credits'] });
          toast.success('Payment confirmed! Credits added to your account.');
        } else if (status === 'failed') {
          setPaymentStatus('failed');
          clearInterval(pollInterval);
          toast.error('Payment failed. Please try again.');
        }
      } catch (error) {
        // Continue polling on error
        console.error('Status check failed:', error);
      }
    }, 10000); // Poll every 10 seconds
    
    // Stop polling after 1 hour
    setTimeout(() => clearInterval(pollInterval), 3600000);
  };
  
  // Manual status check
  const checkPaymentStatus = async () => {
    if (!paymentData?.payment_id) return;
    
    setPaymentStatus('checking');
    try {
      const response = await apiClient.get(`/credits/payment-status/${paymentData.payment_id}`);
      const status = response.data.status;
      
      if (status === 'confirmed') {
        setPaymentStatus('confirmed');
        queryClient.invalidateQueries({ queryKey: ['user-credits'] });
        toast.success('Payment confirmed! Credits added to your account.');
      } else if (status === 'failed') {
        setPaymentStatus('failed');
        toast.error('Payment failed. Please try again.');
      } else {
        setPaymentStatus('pending');
        toast.info('Payment is still pending. Please wait for blockchain confirmation.');
      }
    } catch (error) {
      setPaymentStatus('pending');
      toast.error('Failed to check payment status. Please try again.');
    }
  };
  
  // Copy to clipboard helper
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };
  
  // Format time remaining
  const formatTimeRemaining = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const handlePurchase = () => {
    const amount = selectedPackage ? selectedPackage.usd_cost : parseFloat(customAmount);
    
    if (!amount || amount < 10) {
      toast.error('Minimum purchase amount is $10');
      return;
    }

    purchaseMutation.mutate({
      amount,
      paymentMethod: selectedPaymentMethod
    });
  };

  const getPackageIcon = (packageName: string) => {
    switch (packageName.toLowerCase()) {
      case 'starter': return <Zap className="h-6 w-6" />;
      case 'growth': return <TrendingUp className="h-6 w-6" />;
      case 'professional': return <Shield className="h-6 w-6" />;
      case 'enterprise': return <Star className="h-6 w-6" />;
      default: return <CreditCard className="h-6 w-6" />;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Purchase Credits</h1>
          <p className="text-muted-foreground">Fuel your trading strategies with profit potential credits</p>
        </div>
      </div>

      {/* Value Proposition */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500 rounded-full">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Revolutionary Credit System</h3>
              <p className="text-muted-foreground">
                Pay for profit potential, not subscriptions. Every credit gives you 4x profit capacity.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Package Selection */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Choose Your Package</CardTitle>
              <CardDescription>Select a pre-built package or enter a custom amount</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[1, 2, 3, 4].map(i => (
                    <div key={i} className="p-4 border rounded-lg animate-pulse">
                      <div className="h-6 bg-muted rounded mb-3" />
                      <div className="h-4 bg-muted rounded mb-2" />
                      <div className="h-4 bg-muted rounded" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {purchaseOptions?.map((pkg: PurchaseOption) => (
                    <div
                      key={pkg.package_name}
                      className={`p-4 border rounded-lg cursor-pointer transition-all ${
                        selectedPackage?.package_name === pkg.package_name
                          ? 'border-blue-500 bg-blue-50'
                          : 'hover:border-gray-300'
                      } ${pkg.popular ? 'ring-2 ring-blue-200' : ''}`}
                      onClick={() => setSelectedPackage(pkg)}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          {getPackageIcon(pkg.package_name)}
                          <h3 className="font-semibold">{pkg.package_name}</h3>
                        </div>
                        {pkg.popular && <Badge variant="default">Popular</Badge>}
                      </div>
                      
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Cost:</span>
                          <span className="font-semibold">{formatCurrency(pkg.usd_cost)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Credits:</span>
                          <span className="font-semibold text-blue-500">{pkg.credits + pkg.bonus_credits}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Profit Potential:</span>
                          <span className="font-semibold text-green-500">{formatCurrency(pkg.profit_potential)}</span>
                        </div>
                        {pkg.bonus_credits > 0 && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Bonus Credits:</span>
                            <span className="font-semibold text-orange-500">+{pkg.bonus_credits}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <Separator />

              {/* Custom Amount */}
              <div className="space-y-3">
                <Label htmlFor="custom-amount">Custom Amount (minimum $10)</Label>
                <Input
                  id="custom-amount"
                  type="number"
                  placeholder="Enter custom USD amount"
                  value={customAmount}
                  onChange={(e) => {
                    setCustomAmount(e.target.value);
                    setSelectedPackage(null);
                  }}
                  min="10"
                  max="10000"
                />
                {customAmount && parseFloat(customAmount) >= 10 && (
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span>Credits:</span>
                        <span className="font-semibold">{Math.floor(parseFloat(customAmount))}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Profit Potential:</span>
                        <span className="font-semibold text-green-500">
                          {formatCurrency(parseFloat(customAmount) * 4)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Payment Method Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Payment Method</CardTitle>
              <CardDescription>Choose your preferred cryptocurrency</CardDescription>
            </CardHeader>
            <CardContent>
              <RadioGroup value={selectedPaymentMethod} onValueChange={setSelectedPaymentMethod}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {paymentMethods.map((method) => (
                    <div key={method.id} className="flex items-center space-x-2">
                      <RadioGroupItem value={method.id} id={method.id} />
                      <Label 
                        htmlFor={method.id} 
                        className="flex items-center gap-3 cursor-pointer flex-1 p-3 border rounded-lg hover:bg-muted/50"
                      >
                        {method.icon}
                        <div>
                          <div className="font-medium">{method.name}</div>
                          <div className="text-xs text-muted-foreground">{method.description}</div>
                        </div>
                      </Label>
                    </div>
                  ))}
                </div>
              </RadioGroup>
            </CardContent>
          </Card>
        </div>

        {/* Purchase Summary */}
        <div>
          <Card className="sticky top-6">
            <CardHeader>
              <CardTitle>Purchase Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedPackage ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Package:</span>
                    <span className="font-semibold">{selectedPackage.package_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cost:</span>
                    <span className="font-semibold">{formatCurrency(selectedPackage.usd_cost)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Credits:</span>
                    <span className="font-semibold text-blue-500">
                      {selectedPackage.credits + selectedPackage.bonus_credits}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Profit Potential:</span>
                    <span className="font-semibold text-green-500">
                      {formatCurrency(selectedPackage.profit_potential)}
                    </span>
                  </div>
                </div>
              ) : customAmount && parseFloat(customAmount) >= 10 ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Custom Amount:</span>
                    <span className="font-semibold">{formatCurrency(parseFloat(customAmount))}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Credits:</span>
                    <span className="font-semibold text-blue-500">{Math.floor(parseFloat(customAmount))}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Profit Potential:</span>
                    <span className="font-semibold text-green-500">
                      {formatCurrency(parseFloat(customAmount) * 4)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-6">
                  <CreditCard className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>Select a package or enter custom amount</p>
                </div>
              )}

              {(selectedPackage || (customAmount && parseFloat(customAmount) >= 10)) && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle className="h-4 w-4" />
                      <span>Instant credit delivery</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Shield className="h-4 w-4" />
                      <span>Secure crypto payments</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <TrendingUp className="h-4 w-4" />
                      <span>4x profit potential</span>
                    </div>
                  </div>
                  
                  <Button 
                    className="w-full" 
                    onClick={handlePurchase}
                    disabled={purchaseMutation.isPending}
                  >
                    {purchaseMutation.isPending ? 'Processing...' : 'Purchase Credits'}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Payment Modal */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Complete Your Payment</DialogTitle>
            <DialogDescription>
              {paymentStatus === 'pending' && 'Send the exact amount to complete your purchase'}
              {paymentStatus === 'checking' && 'Checking payment status...'}
              {paymentStatus === 'confirmed' && 'Payment confirmed! Credits added to your account.'}
              {paymentStatus === 'failed' && 'Payment failed. Please try again.'}
            </DialogDescription>
          </DialogHeader>
          
          {paymentData && (
            <div className="space-y-4">
              {/* Payment Status */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                {paymentStatus === 'pending' && (
                  <>
                    <Clock className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">Pending — awaiting blockchain confirmation</span>
                  </>
                )}
                {paymentStatus === 'checking' && (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
                    <span className="text-sm">Checking payment status...</span>
                  </>
                )}
                {paymentStatus === 'confirmed' && (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm text-green-600">Payment confirmed!</span>
                  </>
                )}
                {paymentStatus === 'failed' && (
                  <>
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    <span className="text-sm text-red-600">Payment failed</span>
                  </>
                )}
              </div>
              
              {/* Payment Details */}
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Payment ID</Label>
                  <div className="flex items-center gap-2 p-2 bg-muted rounded text-sm font-mono">
                    <span className="flex-1 truncate">{paymentData.payment_id}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(paymentData.payment_id)}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                
                <div>
                  <Label className="text-xs text-muted-foreground">Payment Address</Label>
                  <div className="flex items-center gap-2 p-2 bg-muted rounded text-sm font-mono">
                    <span className="flex-1 truncate">{paymentData.payment_address}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(paymentData.payment_address)}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                
                <div>
                  <Label className="text-xs text-muted-foreground">Amount</Label>
                  <div className="p-2 bg-muted rounded text-sm font-semibold">
                    {paymentData.crypto_amount} {paymentData.crypto_currency}
                  </div>
                </div>
                
                {timeRemaining > 0 && (
                  <div>
                    <Label className="text-xs text-muted-foreground">Time Remaining</Label>
                    <div className="p-2 bg-orange-50 border border-orange-200 rounded text-sm font-semibold text-orange-600">
                      {formatTimeRemaining(timeRemaining)}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Action Buttons */}
              <div className="flex gap-2">
                {paymentData.qr_code_url && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(paymentData.qr_code_url, '_blank')}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View QR Code
                  </Button>
                )}
                <Button
                  size="sm"
                  onClick={checkPaymentStatus}
                  disabled={paymentStatus === 'checking' || paymentStatus === 'confirmed'}
                >
                  {paymentStatus === 'checking' ? 'Checking...' : 'I Paid — Check Status'}
                </Button>
              </div>
              
              {paymentStatus === 'confirmed' && (
                <Button
                  className="w-full"
                  onClick={() => {
                    setShowPaymentModal(false);
                    navigate('/dashboard');
                  }}
                >
                  Continue to Dashboard
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CreditsPurchasePage;