import React, { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';
import { adminService } from '@/services/adminService';
import { toast } from 'sonner';
import { Loader2, RefreshCw, Save, RotateCcw } from 'lucide-react';

interface StrategyScanningPolicy {
  strategy_key: string;
  max_symbols: number | null;
  chunk_size: number | null;
  priority: number | null;
  enabled: boolean;
  source: 'default' | 'config' | 'database';
  id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

interface PolicyResponse {
  success: boolean;
  policies: StrategyScanningPolicy[];
  count: number;
}

const formatSourceLabel = (source: StrategyScanningPolicy['source']) => {
  switch (source) {
    case 'database':
      return { label: 'Override', variant: 'default' as const };
    case 'config':
      return { label: 'Config', variant: 'secondary' as const };
    default:
      return { label: 'Default', variant: 'outline' as const };
  }
};

const StrategyScanningPolicyManager: React.FC = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, isFetching, isError, refetch } = useQuery<PolicyResponse>({
    queryKey: ['admin-opportunity-policies'],
    queryFn: async () => {
      const response = await adminService.getOpportunityPolicies();
      return response as PolicyResponse;
    },
    refetchInterval: 60_000,
  });

  const [drafts, setDrafts] = useState<Record<string, StrategyScanningPolicy>>({});

  useEffect(() => {
    if (!data?.policies) return;
    const nextDrafts: Record<string, StrategyScanningPolicy> = {};
    data.policies.forEach((policy) => {
      nextDrafts[policy.strategy_key] = { ...policy };
    });
    setDrafts(nextDrafts);
  }, [data?.policies]);

  const updateMutation = useMutation({
    mutationFn: async ({
      strategyKey,
      payload,
    }: {
      strategyKey: string;
      payload: {
        max_symbols: number | null;
        chunk_size: number | null;
        priority: number | null;
        enabled: boolean;
      };
    }) => {
      const response = await adminService.updateOpportunityPolicy(strategyKey, payload);
      return response as { policy: StrategyScanningPolicy };
    },
    onSuccess: (response, variables) => {
      toast.success(`Policy updated for ${variables.strategyKey}`);
      queryClient.invalidateQueries({ queryKey: ['admin-opportunity-policies'] });
    },
    onError: (error: any, variables) => {
      toast.error(
        `Failed to update ${variables.strategyKey}: ${error.response?.data?.detail || error.message}`,
      );
    },
  });

  const resetMutation = useMutation({
    mutationFn: async (strategyKey: string) => {
      const response = await adminService.resetOpportunityPolicy(strategyKey);
      return response as { policy: StrategyScanningPolicy };
    },
    onSuccess: (response, strategyKey) => {
      toast.success(`Policy reset for ${strategyKey}`);
      queryClient.invalidateQueries({ queryKey: ['admin-opportunity-policies'] });
    },
    onError: (error: any, strategyKey) => {
      toast.error(
        `Failed to reset ${strategyKey}: ${error.response?.data?.detail || error.message}`,
      );
    },
  });

  const originalPolicies = useMemo(() => {
    const map: Record<string, StrategyScanningPolicy> = {};
    data?.policies?.forEach((policy) => {
      map[policy.strategy_key] = policy;
    });
    return map;
  }, [data?.policies]);

  const handleNumericChange = (
    strategyKey: string,
    field: 'max_symbols' | 'chunk_size' | 'priority',
    value: string,
  ) => {
    setDrafts((prev) => {
      const next = { ...prev };
      const current = next[strategyKey];
      if (!current) return prev;

      let parsed: number | null = null;
      if (value.trim() !== '') {
        const numeric = Number.parseInt(value, 10);
        parsed = Number.isNaN(numeric) || numeric < 1 ? null : numeric;
      }

      next[strategyKey] = {
        ...current,
        [field]: parsed,
      } as StrategyScanningPolicy;
      return next;
    });
  };

  const handleToggleEnabled = (strategyKey: string, enabled: boolean) => {
    setDrafts((prev) => {
      const next = { ...prev };
      const current = next[strategyKey];
      if (!current) return prev;
      next[strategyKey] = { ...current, enabled };
      return next;
    });
  };

  const handleSave = (policy: StrategyScanningPolicy) => {
    updateMutation.mutate({
      strategyKey: policy.strategy_key,
      payload: {
        max_symbols: policy.max_symbols ?? null,
        chunk_size: policy.chunk_size ?? null,
        priority: policy.priority ?? null,
        enabled: policy.enabled,
      },
    });
  };

  const handleReset = (strategyKey: string) => {
    resetMutation.mutate(strategyKey);
  };

  const hasChanges = (policy: StrategyScanningPolicy) => {
    const original = originalPolicies[policy.strategy_key];
    if (!original) return true;
    return (
      (original.max_symbols ?? null) !== (policy.max_symbols ?? null) ||
      (original.chunk_size ?? null) !== (policy.chunk_size ?? null) ||
      (original.priority ?? null) !== (policy.priority ?? null) ||
      original.enabled !== policy.enabled
    );
  };

  const sortedPolicies = useMemo(() => {
    if (!data?.policies) return [] as StrategyScanningPolicy[];
    return [...data.policies].sort((a, b) => {
      const priorityDiff = (b.priority ?? 0) - (a.priority ?? 0);
      if (priorityDiff !== 0) return priorityDiff;
      return a.strategy_key.localeCompare(b.strategy_key);
    });
  }, [data?.policies]);

  return (
    <Card className="trading-card">
      <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <CardTitle>Opportunity Scanning Policies</CardTitle>
          <CardDescription>
            Control per-strategy symbol coverage and batching without redeploying the backend.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Separator className="mb-4" />
        {isLoading ? (
          <div className="flex items-center gap-3 py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading policies...
          </div>
        ) : isError ? (
          <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            Failed to load policies. Please try again.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">Strategy</TableHead>
                <TableHead>Max Symbols</TableHead>
                <TableHead>Chunk Size</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Enabled</TableHead>
                <TableHead className="w-[180px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPolicies.map((policy) => {
                const draft = drafts[policy.strategy_key] ?? policy;
                const dirty = hasChanges(draft);
                const saving =
                  updateMutation.isPending && updateMutation.variables?.strategyKey === policy.strategy_key;
                const resetting = resetMutation.isPending && resetMutation.variables === policy.strategy_key;
                const sourceBadge = formatSourceLabel(policy.source);

                return (
                  <TableRow key={policy.strategy_key}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <div className="font-medium capitalize">
                          {policy.strategy_key.replace(/_/g, ' ')}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant={sourceBadge.variant}>{sourceBadge.label}</Badge>
                          {policy.updated_at ? (
                            <span>
                              Updated {new Date(policy.updated_at).toLocaleString()}
                            </span>
                          ) : (
                            <span>Preset</span>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={1}
                        placeholder="Unlimited"
                        value={draft.max_symbols ?? ''}
                        onChange={(event) =>
                          handleNumericChange(policy.strategy_key, 'max_symbols', event.target.value)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={1}
                        placeholder="Auto"
                        value={draft.chunk_size ?? ''}
                        onChange={(event) =>
                          handleNumericChange(policy.strategy_key, 'chunk_size', event.target.value)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        placeholder="100"
                        value={draft.priority ?? ''}
                        onChange={(event) =>
                          handleNumericChange(policy.strategy_key, 'priority', event.target.value)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={draft.enabled}
                          onCheckedChange={(checked) => handleToggleEnabled(policy.strategy_key, checked)}
                          disabled={saving || resetting}
                        />
                        <span className="text-xs text-muted-foreground">
                          {draft.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="default"
                          disabled={!dirty || saving}
                          onClick={() => handleSave(draft)}
                        >
                          <Save className={`mr-2 h-4 w-4 ${saving ? 'animate-spin' : ''}`} />
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={resetting}
                          onClick={() => handleReset(policy.strategy_key)}
                        >
                          <RotateCcw className={`mr-2 h-4 w-4 ${resetting ? 'animate-spin' : ''}`} />
                          Reset
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

export default StrategyScanningPolicyManager;
