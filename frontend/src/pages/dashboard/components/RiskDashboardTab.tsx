import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ShieldAlert, Activity, TrendingDown, TrendingUp, LineChart, Loader2, CheckCircle2 } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import { formatCurrency, formatNumber, formatPercentage } from '@/lib/utils';
import {
  useRiskDashboard,
  PositionSizingPayload,
  EmergencyPolicyUpdatePayload,
  EmergencyPolicy,
} from '@/hooks/useRiskDashboard';

const DEFAULT_THRESHOLDS = {
  warning: 7,
  critical: 15,
  emergency: 25,
};

const RiskDashboardTab: React.FC = () => {
  const {
    loading,
    error,
    metrics,
    guidelines,
    riskAlerts,
    portfolioValue,
    lastUpdated,
    positionSizing,
    positionSizingLoading,
    emergencyPolicies,
    policiesUpdating,
    fetchDashboard,
    computePositionSizing,
    fetchEmergencyPolicies,
    updateEmergencyPolicies,
    clearError,
  } = useRiskDashboard();

  const [sizingForm, setSizingForm] = useState<PositionSizingPayload>({
    symbol: '',
    expectedReturn: 6,
    confidence: 60,
    mode: 'balanced',
    stopLossPct: 2,
    takeProfitPct: 6,
  });

  const [optIn, setOptIn] = useState<boolean>(false);
  const [thresholds, setThresholds] = useState({ ...DEFAULT_THRESHOLDS });

  useEffect(() => {
    fetchDashboard();
    fetchEmergencyPolicies();
  }, [fetchDashboard, fetchEmergencyPolicies]);

  useEffect(() => {
    if (emergencyPolicies) {
      setOptIn(Boolean(emergencyPolicies.opt_in));

      const policyThresholds = emergencyPolicies.policies.reduce((acc, policy) => {
        const key = policy.level as keyof typeof DEFAULT_THRESHOLDS;
        if (key in DEFAULT_THRESHOLDS) {
          acc[key] = Number(policy.loss_threshold_pct ?? DEFAULT_THRESHOLDS[key]);
        }
        return acc;
      }, { ...DEFAULT_THRESHOLDS });

      setThresholds(policyThresholds);
    }
  }, [emergencyPolicies]);

  const onSizingSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    computePositionSizing({
      symbol: sizingForm.symbol,
      expectedReturn: Number(sizingForm.expectedReturn),
      confidence: Number(sizingForm.confidence),
      mode: sizingForm.mode,
      stopLossPct: sizingForm.stopLossPct ? Number(sizingForm.stopLossPct) : undefined,
      takeProfitPct: sizingForm.takeProfitPct ? Number(sizingForm.takeProfitPct) : undefined,
    });
  };

  const onEmergencySubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const payload: EmergencyPolicyUpdatePayload = {
      optIn,
      thresholds: {
        warning: Number(thresholds.warning),
        critical: Number(thresholds.critical),
        emergency: Number(thresholds.emergency),
      },
    };

    updateEmergencyPolicies(payload);
  };

  const policyDisplay = useMemo<EmergencyPolicy[]>(() => {
    if (!emergencyPolicies?.policies) {
      return [];
    }
    return emergencyPolicies.policies;
  }, [emergencyPolicies]);

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Risk system warning</AlertTitle>
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>{error}</span>
            <Button size="sm" variant="outline" onClick={() => clearError()}>
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Portfolio risk snapshot</CardTitle>
            <CardDescription>
              Institutional-grade VaR, expected shortfall and drawdown analytics powered by the risk engine.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading && !metrics ? (
              <div className="space-y-3">
                <div className="h-4 rounded bg-muted animate-pulse" />
                <div className="h-4 rounded bg-muted animate-pulse w-3/4" />
                <div className="h-4 rounded bg-muted animate-pulse w-2/3" />
              </div>
            ) : metrics ? (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>VaR (95%)</span>
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    </div>
                    <p className="text-2xl font-semibold text-red-500">
                      {formatPercentage(metrics.var95Percent, 2)}
                    </p>
                    <p className="text-xs text-muted-foreground">Daily loss not exceeded 95% of the time</p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>VaR (99%)</span>
                      <TrendingDown className="h-4 w-4 text-rose-500" />
                    </div>
                    <p className="text-2xl font-semibold text-rose-500">
                      {formatPercentage(metrics.var99Percent, 2)}
                    </p>
                    <p className="text-xs text-muted-foreground">Severe tail risk at the 99% confidence level</p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Expected shortfall</span>
                      <ShieldAlert className="h-4 w-4 text-orange-500" />
                    </div>
                    <p className="text-2xl font-semibold text-orange-500">
                      {formatPercentage(metrics.expectedShortfallPercent, 2)}
                    </p>
                    <p className="text-xs text-muted-foreground">Average loss when VaR levels are breached</p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Annual volatility</span>
                      <Activity className="h-4 w-4 text-violet-500" />
                    </div>
                    <p className="text-2xl font-semibold text-violet-500">
                      {formatPercentage(metrics.volatilityPercent, 2)}
                    </p>
                    <Progress value={Math.min(metrics.volatilityPercent, 100)} className="mt-3" />
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Sharpe / Sortino</span>
                      <LineChart className="h-4 w-4 text-emerald-500" />
                    </div>
                    <p className="text-2xl font-semibold">
                      {formatNumber(metrics.sharpeRatio, 2)}{' '}
                      <span className="text-sm text-muted-foreground">Sharpe</span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Sortino {formatNumber(metrics.sortinoRatio, 2)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Beta vs BTC</span>
                      <TrendingUp className="h-4 w-4 text-sky-500" />
                    </div>
                    <p className="text-2xl font-semibold text-sky-500">{formatNumber(metrics.beta, 2)}</p>
                    <p className="text-xs text-muted-foreground">Correlation {formatNumber(metrics.correlationToMarket, 2)}</p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <p className="text-sm text-muted-foreground">Maximum drawdown</p>
                    <p className="text-3xl font-semibold text-red-500">
                      {formatPercentage(metrics.maximumDrawdownPercent, 2)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Largest peak-to-trough decline across the analysed window
                    </p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card/40">
                    <p className="text-sm text-muted-foreground">Portfolio value assessed</p>
                    <p className="text-3xl font-semibold">{formatCurrency(portfolioValue)}</p>
                    {lastUpdated && (
                      <p className="text-xs text-muted-foreground">Updated {new Date(lastUpdated).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No active positions detected yet. Add positions to analyse risk.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk guidelines</CardTitle>
            <CardDescription>Actionable policies enforced alongside quantitative metrics.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {guidelines.map((guideline) => (
              <div key={guideline} className="flex items-start gap-3 rounded-lg border border-dashed border-border p-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5" />
                <p className="text-sm text-muted-foreground">{guideline}</p>
              </div>
            ))}

            {riskAlerts.length > 0 && (
              <div className="space-y-2">
                <Separator />
                <p className="text-sm font-medium">Active alerts</p>
                <div className="space-y-2">
                  {riskAlerts.map((alert, index) => (
                    <div key={index} className="rounded-md border border-warning/30 bg-warning/10 p-3">
                      <p className="text-xs uppercase tracking-wide text-warning mb-1">{alert?.severity || 'Warning'}</p>
                      <p className="text-sm text-warning-foreground">{alert?.message || 'Risk condition triggered.'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Kelly-backed position sizing</CardTitle>
            <CardDescription>Let the risk engine enforce the 10% capital allocation ceiling and stop rules.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={onSizingSubmit} className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                <Input
                  id="symbol"
                  placeholder="e.g. BTC"
                  value={sizingForm.symbol}
                  onChange={(event) => setSizingForm((prev) => ({ ...prev, symbol: event.target.value.toUpperCase() }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mode">Trading mode</Label>
                <Select value={sizingForm.mode} onValueChange={(value) => setSizingForm((prev) => ({ ...prev, mode: value }))}>
                  <SelectTrigger id="mode">
                    <SelectValue placeholder="Select trading mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                    <SelectItem value="beast_mode">Beast Mode</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="expectedReturn">Expected return %</Label>
                <Input
                  id="expectedReturn"
                  type="number"
                  step="0.1"
                  value={sizingForm.expectedReturn}
                  onChange={(event) => setSizingForm((prev) => ({ ...prev, expectedReturn: Number(event.target.value) }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confidence">Confidence %</Label>
                <Input
                  id="confidence"
                  type="number"
                  min={0}
                  max={100}
                  step="1"
                  value={sizingForm.confidence}
                  onChange={(event) => setSizingForm((prev) => ({ ...prev, confidence: Number(event.target.value) }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="stopLoss">Stop-loss %</Label>
                <Input
                  id="stopLoss"
                  type="number"
                  step="0.1"
                  value={sizingForm.stopLossPct}
                  onChange={(event) => setSizingForm((prev) => ({ ...prev, stopLossPct: Number(event.target.value) }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="takeProfit">Take-profit %</Label>
                <Input
                  id="takeProfit"
                  type="number"
                  step="0.1"
                  value={sizingForm.takeProfitPct}
                  onChange={(event) => setSizingForm((prev) => ({ ...prev, takeProfitPct: Number(event.target.value) }))}
                />
              </div>
              <div className="md:col-span-2">
                <Button type="submit" disabled={positionSizingLoading || !sizingForm.symbol}>
                  {positionSizingLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Calculate recommended size
                </Button>
              </div>
            </form>

            {positionSizing.result && (
              <div className="space-y-3 rounded-lg border border-border bg-card/40 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Recommended allocation</p>
                    <p className="text-2xl font-semibold">
                      {formatPercentage(Number(positionSizing.result.risk_adjusted_size ?? 0) * 100, 2)} of capital
                    </p>
                  </div>
                  <Badge variant="outline" className="uppercase">
                    {positionSizing.result.trading_mode || sizingForm.mode}
                  </Badge>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Position size (USD)</p>
                    <p className="text-lg font-semibold">
                      {formatCurrency(Number(positionSizing.result.position_value_usd ?? 0))}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Kelly baseline</p>
                    <p className="text-lg font-semibold">
                      {formatPercentage(Number(positionSizing.result.kelly_size ?? 0) * 100, 2)}
                    </p>
                  </div>
                </div>

                {positionSizing.riskControls && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-md border border-border/70 p-3">
                      <p className="text-xs text-muted-foreground">Stop-loss (max)</p>
                      <p className="text-sm font-semibold">
                        {formatCurrency(Number(positionSizing.riskControls.stop_loss_usd ?? 0))}
                      </p>
                    </div>
                    <div className="rounded-md border border-border/70 p-3">
                      <p className="text-xs text-muted-foreground">Take-profit (target)</p>
                      <p className="text-sm font-semibold">
                        {formatCurrency(Number(positionSizing.riskControls.take_profit_usd ?? 0))}
                      </p>
                    </div>
                  </div>
                )}

                {positionSizing.guidelines.length > 0 && (
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">
                    {positionSizing.guidelines.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Emergency circuit-breakers</CardTitle>
            <CardDescription>
              Automated liquidation controls at 7%, 15% and 25% drawdowns with optional custom thresholds.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={onEmergencySubmit} className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="font-medium">Opt-in to automatic emergency controls</p>
                  <p className="text-xs text-muted-foreground">
                    When enabled, the emergency manager can reduce, halt or liquidate positions once thresholds are hit.
                  </p>
                </div>
                <Switch checked={optIn} onCheckedChange={(checked) => setOptIn(checked)} />
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {(['warning', 'critical', 'emergency'] as Array<keyof typeof DEFAULT_THRESHOLDS>).map((level) => (
                  <div key={level} className="space-y-2 rounded-md border border-border p-3">
                    <Label className="capitalize">{level} threshold %</Label>
                    <Input
                      type="number"
                      step="0.5"
                      min={1}
                      value={thresholds[level]}
                      onChange={(event) =>
                        setThresholds((prev) => ({ ...prev, [level]: Number(event.target.value) }))
                      }
                      disabled={!optIn}
                    />
                    <p className="text-xs text-muted-foreground">
                      Default {DEFAULT_THRESHOLDS[level]}%
                    </p>
                  </div>
                ))}
              </div>

              <Button type="submit" disabled={policiesUpdating}>
                {policiesUpdating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save emergency preferences
              </Button>
            </form>

            <div className="space-y-3">
              {policyDisplay.map((policy) => (
                <div key={policy.level} className="rounded-lg border border-dashed border-border p-3 bg-card/40">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="capitalize">
                        {policy.level}
                      </Badge>
                      <span className="text-sm font-semibold">{policy.loss_threshold_pct}% loss</span>
                    </div>
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">{policy.action.replace('_', ' ')}</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{policy.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RiskDashboardTab;
