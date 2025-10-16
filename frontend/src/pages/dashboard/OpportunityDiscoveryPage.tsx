import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Target,
  TrendingUp,
  DollarSign,
  Clock,
  Shield,
  BarChart3,
  RefreshCw,
  Filter,
  Download,
  Eye,
  AlertCircle,
  CheckCircle,
  Loader2,
  Sparkles,
  Zap,
  Brain,
  Activity,
  ArrowRight,
  Star,
  TrendingDown,
  AlertTriangle,
  Info,
  Play,
  Pause,
  RotateCcw,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useOpportunityDiscovery } from '@/hooks/useOpportunityDiscovery';
import { Opportunity } from '@/lib/api/opportunityApi';

const OpportunityDiscoveryPage: React.FC = () => {
  const [filters, setFilters] = useState({
    riskLevel: 'all',
    minProfit: 0,
    maxCapital: 100000,
    timeframes: [] as string[],
    opportunityTypes: [] as string[],
  });
  const [sortBy, setSortBy] = useState<'profit' | 'confidence' | 'risk' | 'timeframe'>('profit');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const {
    userStatus,
    scanStatus,
    scanResults,
    opportunities,
    totalOpportunities,
    isDiscovering,
    isScanning,
    isOnboarded,
    needsOnboarding,
    hasActiveScan,
    scanProgress,
    discoverOpportunities,
    triggerOnboarding,
    clearScan,
    refreshAll,
  } = useOpportunityDiscovery({
    autoRefresh: true,
    refreshInterval: 30000,
  });

  // Filter and sort opportunities
  const filteredOpportunities = useMemo(() => {
    let filtered = opportunities;

    // Apply filters
    if (filters.riskLevel !== 'all') {
      filtered = filtered.filter(opp => opp.risk_level === filters.riskLevel);
    }

    if (filters.minProfit > 0) {
      filtered = filtered.filter(opp => opp.profit_potential_usd >= filters.minProfit);
    }

    if (filters.maxCapital < 100000) {
      filtered = filtered.filter(opp => opp.required_capital_usd <= filters.maxCapital);
    }

    if (filters.timeframes.length > 0) {
      filtered = filtered.filter(opp => filters.timeframes.includes(opp.estimated_timeframe));
    }

    if (filters.opportunityTypes.length > 0) {
      filtered = filtered.filter(opp => filters.opportunityTypes.includes(opp.opportunity_type));
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'profit':
          return b.profit_potential_usd - a.profit_potential_usd;
        case 'confidence':
          return b.confidence_score - a.confidence_score;
        case 'risk':
          const riskOrder = { low: 1, medium: 2, high: 3, very_high: 4 };
          return riskOrder[a.risk_level as keyof typeof riskOrder] - riskOrder[b.risk_level as keyof typeof riskOrder];
        case 'timeframe':
          return a.estimated_timeframe.localeCompare(b.estimated_timeframe);
        default:
          return 0;
      }
    });

    return filtered;
  }, [opportunities, filters, sortBy]);

  // Risk level colors
  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low':
        return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'medium':
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'high':
        return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
      case 'very_high':
        return 'text-red-500 bg-red-500/10 border-red-500/20';
      default:
        return 'text-gray-500 bg-gray-500/10 border-gray-500/20';
    }
  };

  // Confidence score color
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-500';
    if (score >= 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  // Opportunity card component
  const OpportunityCard: React.FC<{ opportunity: Opportunity; index: number }> = ({ opportunity, index }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card className="hover:shadow-lg transition-all duration-200 border-l-4 border-l-primary/20">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                {opportunity.strategy_name}
              </CardTitle>
              <CardDescription className="flex items-center gap-2">
                <span className="font-medium">{opportunity.symbol}</span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground">{opportunity.exchange}</span>
              </CardDescription>
            </div>
            <Badge className={getRiskColor(opportunity.risk_level)}>
              {opportunity.risk_level.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Profit Potential */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Profit Potential</span>
            </div>
            <span className="text-lg font-bold text-green-500">
              {formatCurrency(opportunity.profit_potential_usd)}
            </span>
          </div>

          {/* Required Capital */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-500" />
              <span className="text-sm font-medium">Required Capital</span>
            </div>
            <span className="text-sm font-medium">
              {formatCurrency(opportunity.required_capital_usd)}
            </span>
          </div>

          {/* Confidence Score */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-purple-500" />
              <span className="text-sm font-medium">Confidence</span>
            </div>
            <span className={`text-sm font-medium ${getConfidenceColor(opportunity.confidence_score)}`}>
              {formatPercentage(opportunity.confidence_score)}
            </span>
          </div>

          {/* Timeframe */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-orange-500" />
              <span className="text-sm font-medium">Timeframe</span>
            </div>
            <span className="text-sm font-medium">{opportunity.estimated_timeframe}</span>
          </div>

          {/* Entry/Exit Prices */}
          {(opportunity.entry_price || opportunity.exit_price) && (
            <div className="space-y-2 pt-2 border-t">
              {opportunity.entry_price && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Entry Price</span>
                  <span className="font-medium">{formatCurrency(opportunity.entry_price)}</span>
                </div>
              )}
              {opportunity.exit_price && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Exit Price</span>
                  <span className="font-medium">{formatCurrency(opportunity.exit_price)}</span>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            <Button size="sm" className="flex-1">
              <Eye className="h-4 w-4 mr-1" />
              View Details
            </Button>
            <Button size="sm" variant="outline">
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );

  // Onboarding required state
  if (needsOnboarding) {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
            <Target className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Opportunity Discovery</h1>
            <p className="text-muted-foreground mt-2">
              Discover the best trading opportunities tailored to your portfolio
            </p>
          </div>
        </div>

        <Card className="max-w-md mx-auto">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              Onboarding Required
            </CardTitle>
            <CardDescription>
              Complete your onboarding to access opportunity discovery features
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="font-medium">What you'll get:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• 3 free trading strategies</li>
                <li>• Credit account setup</li>
                <li>• Personalized opportunity discovery</li>
                <li>• Real-time market analysis</li>
              </ul>
            </div>
            <Button 
              onClick={() => triggerOnboarding()} 
              className="w-full"
              disabled={isDiscovering}
            >
              {isDiscovering ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 mr-2" />
              )}
              Start Onboarding
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Target className="h-8 w-8 text-primary" />
            Opportunity Discovery
          </h1>
          <p className="text-muted-foreground">
            Discover the best trading opportunities tailored to your portfolio and risk profile
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={refreshAll}
            variant="outline"
            size="sm"
            disabled={isDiscovering}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isDiscovering ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => discoverOpportunities({ force_refresh: true })}
            disabled={isDiscovering || isScanning}
            className="bg-primary hover:bg-primary/90"
          >
            {isDiscovering || isScanning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            {isScanning ? 'Scanning...' : 'Find Opportunities'}
          </Button>
        </div>
      </div>

      {/* Scan Status */}
      {hasActiveScan && scanProgress && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-primary animate-pulse" />
                  <span className="font-medium">Scanning Opportunities</span>
                </div>
                <Badge variant="outline">
                  {scanProgress.percentage}% Complete
                </Badge>
              </div>
              <Progress value={scanProgress.percentage} className="w-full" />
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  {scanProgress.strategies_completed} of {scanProgress.total_strategies} strategies completed
                </span>
                <span>
                  {scanProgress.opportunities_found_so_far} opportunities found so far
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Target className="h-4 w-4 text-primary" />
              <div>
                <p className="text-sm font-medium">Total Opportunities</p>
                <p className="text-2xl font-bold">{totalOpportunities}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-sm font-medium">Avg. Profit Potential</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(
                    opportunities.reduce((sum, opp) => sum + opp.profit_potential_usd, 0) / 
                    Math.max(opportunities.length, 1)
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Shield className="h-4 w-4 text-blue-500" />
              <div>
                <p className="text-sm font-medium">Avg. Confidence</p>
                <p className="text-2xl font-bold">
                  {formatPercentage(
                    opportunities.reduce((sum, opp) => sum + opp.confidence_score, 0) / 
                    Math.max(opportunities.length, 1)
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4 text-orange-500" />
              <div>
                <p className="text-sm font-medium">Last Updated</p>
                <p className="text-sm font-medium">
                  {scanResults?.last_updated 
                    ? new Date(scanResults.last_updated).toLocaleTimeString()
                    : 'Never'
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters & Controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Risk Level Filter */}
            <div className="space-y-2">
              <Label>Risk Level</Label>
              <Select
                value={filters.riskLevel}
                onValueChange={(value) => setFilters(prev => ({ ...prev, riskLevel: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Risk Levels</SelectItem>
                  <SelectItem value="low">Low Risk</SelectItem>
                  <SelectItem value="medium">Medium Risk</SelectItem>
                  <SelectItem value="high">High Risk</SelectItem>
                  <SelectItem value="very_high">Very High Risk</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Min Profit Filter */}
            <div className="space-y-2">
              <Label>Min Profit Potential (USD)</Label>
              <Input
                type="number"
                value={filters.minProfit}
                onChange={(e) => setFilters(prev => ({ ...prev, minProfit: Number(e.target.value) }))}
                placeholder="0"
              />
            </div>

            {/* Max Capital Filter */}
            <div className="space-y-2">
              <Label>Max Required Capital (USD)</Label>
              <Input
                type="number"
                value={filters.maxCapital}
                onChange={(e) => setFilters(prev => ({ ...prev, maxCapital: Number(e.target.value) }))}
                placeholder="100000"
              />
            </div>

            {/* Sort By */}
            <div className="space-y-2">
              <Label>Sort By</Label>
              <Select
                value={sortBy}
                onValueChange={(value: any) => setSortBy(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="profit">Profit Potential</SelectItem>
                  <SelectItem value="confidence">Confidence Score</SelectItem>
                  <SelectItem value="risk">Risk Level</SelectItem>
                  <SelectItem value="timeframe">Timeframe</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Opportunities Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">
            Opportunities ({filteredOpportunities.length})
          </h2>
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('grid')}
            >
              Grid
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              List
            </Button>
          </div>
        </div>

        {filteredOpportunities.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <div className="mx-auto w-16 h-16 bg-muted rounded-full flex items-center justify-center">
                  <Search className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">No Opportunities Found</h3>
                  <p className="text-muted-foreground">
                    Try adjusting your filters or run a new discovery scan
                  </p>
                </div>
                <Button onClick={() => discoverOpportunities()}>
                  <Search className="h-4 w-4 mr-2" />
                  Find Opportunities
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className={
            viewMode === 'grid' 
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
              : 'space-y-4'
          }>
            <AnimatePresence>
              {filteredOpportunities.map((opportunity, index) => (
                <OpportunityCard
                  key={`${opportunity.strategy_id}-${opportunity.symbol}`}
                  opportunity={opportunity}
                  index={index}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

export default OpportunityDiscoveryPage;