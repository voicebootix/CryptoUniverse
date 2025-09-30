import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface InvestorProfileFormValues {
  riskTolerance: string;
  investmentAmount: string;
  timeHorizon: string;
  objectives: string[];
  additionalObjective?: string;
  constraints: string[];
  additionalConstraint?: string;
  notes?: string;
}

interface InvestorProfilePromptProps {
  missingFields: string[];
  onSubmit: (values: InvestorProfileFormValues) => Promise<void> | void;
  onSkip?: () => void;
  isSubmitting?: boolean;
}

const RISK_OPTIONS = [
  { value: 'conservative', label: 'Conservative', description: 'Capital preservation, lower volatility' },
  { value: 'balanced', label: 'Balanced', description: 'Even mix of growth and stability' },
  { value: 'aggressive', label: 'Aggressive', description: 'Higher risk tolerance for stronger growth' },
  { value: 'beast_mode', label: 'Beast Mode', description: 'Maximum risk appetite and velocity' }
];

const HORIZON_OPTIONS = [
  { value: '0-12 months', label: '0-12 months' },
  { value: '1-3 years', label: '1-3 years' },
  { value: '3-5 years', label: '3-5 years' },
  { value: '5+ years', label: '5+ years' }
];

const OBJECTIVE_OPTIONS = [
  'Capital preservation',
  'Steady income',
  'Balanced growth',
  'Aggressive growth',
  'Speculative opportunities'
];

const CONSTRAINT_OPTIONS = [
  'None',
  'Limited liquidity',
  'Tax sensitive',
  'No leverage',
  'ESG or sustainability focus'
];

const isFieldRequired = (field: string, missingFields: string[]) => missingFields.includes(field);

const InvestorProfilePrompt: React.FC<InvestorProfilePromptProps> = ({
  missingFields,
  onSubmit,
  onSkip,
  isSubmitting = false
}) => {
  const [riskTolerance, setRiskTolerance] = useState('');
  const [investmentAmount, setInvestmentAmount] = useState('');
  const [timeHorizon, setTimeHorizon] = useState('');
  const [objectives, setObjectives] = useState<string[]>([]);
  const [additionalObjective, setAdditionalObjective] = useState('');
  const [constraints, setConstraints] = useState<string[]>([]);
  const [additionalConstraint, setAdditionalConstraint] = useState('');
  const [notes, setNotes] = useState('');

  const objectiveSelections = useMemo(() => {
    if (!additionalObjective.trim()) {
      return objectives;
    }
    return [...objectives, additionalObjective.trim()];
  }, [objectives, additionalObjective]);

  const constraintSelections = useMemo(() => {
    const base = constraints.includes('None') ? ['None'] : constraints;
    if (!additionalConstraint.trim()) {
      return base;
    }
    return [...base.filter(option => option !== 'None'), additionalConstraint.trim()];
  }, [constraints, additionalConstraint]);

  const toggleObjective = (value: string) => {
    setObjectives((prev) =>
      prev.includes(value) ? prev.filter((option) => option !== value) : [...prev, value]
    );
  };

  const toggleConstraint = (value: string) => {
    setConstraints((prev) => {
      if (value === 'None') {
        return prev.includes('None') ? [] : ['None'];
      }

      const withoutNone = prev.filter((option) => option !== 'None');
      return withoutNone.includes(value)
        ? withoutNone.filter((option) => option !== value)
        : [...withoutNone, value];
    });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    await onSubmit({
      riskTolerance,
      investmentAmount,
      timeHorizon,
      objectives: objectiveSelections,
      additionalObjective: additionalObjective.trim() || undefined,
      constraints: constraintSelections,
      additionalConstraint: additionalConstraint.trim() || undefined,
      notes: notes.trim() || undefined
    });
  };

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-primary">
          Investor Profile Update Required
        </CardTitle>
        <CardDescription>
          Share a few quick details so the AI can align opportunities and rebalancing with your goals.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>
                Risk tolerance
                {isFieldRequired('risk_tolerance', missingFields) && (
                  <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                )}
              </Label>
              <Select value={riskTolerance} onValueChange={setRiskTolerance}>
                <SelectTrigger className={cn(isFieldRequired('risk_tolerance', missingFields) && !riskTolerance && 'border-primary')}>
                  <SelectValue placeholder="Select your risk profile" />
                </SelectTrigger>
                <SelectContent>
                  {RISK_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex flex-col">
                        <span className="font-medium">{option.label}</span>
                        <span className="text-xs text-muted-foreground">{option.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>
                Investment amount (USD)
                {isFieldRequired('investment_amount', missingFields) && (
                  <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                )}
              </Label>
              <Input
                type="number"
                min="0"
                step="100"
                placeholder="e.g. 10000"
                value={investmentAmount}
                onChange={(event) => setInvestmentAmount(event.target.value)}
                className={cn(isFieldRequired('investment_amount', missingFields) && !investmentAmount && 'border-primary')}
              />
            </div>

            <div className="space-y-2">
              <Label>
                Time horizon
                {isFieldRequired('time_horizon', missingFields) && (
                  <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                )}
              </Label>
              <Select value={timeHorizon} onValueChange={setTimeHorizon}>
                <SelectTrigger className={cn(isFieldRequired('time_horizon', missingFields) && !timeHorizon && 'border-primary')}>
                  <SelectValue placeholder="How long can you stay invested?" />
                </SelectTrigger>
                <SelectContent>
                  {HORIZON_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>
                Objectives
                {isFieldRequired('investment_objectives', missingFields) && (
                  <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                )}
              </Label>
              <div className="grid grid-cols-1 gap-2">
                {OBJECTIVE_OPTIONS.map((option) => (
                  <label key={option} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={objectives.includes(option)}
                      onCheckedChange={() => toggleObjective(option)}
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
              <Input
                placeholder="Other objective"
                value={additionalObjective}
                onChange={(event) => setAdditionalObjective(event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>
                Constraints
                {isFieldRequired('constraints', missingFields) && (
                  <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                )}
              </Label>
              <div className="grid grid-cols-1 gap-2">
                {CONSTRAINT_OPTIONS.map((option) => (
                  <label key={option} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={constraints.includes(option)}
                      onCheckedChange={() => toggleConstraint(option)}
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
              <Input
                placeholder="Other constraint"
                value={additionalConstraint}
                onChange={(event) => setAdditionalConstraint(event.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Anything else the AI should consider?</Label>
            <Textarea
              placeholder="Liquidity needs, preferred assets, exclusions, etc."
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </div>

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            {onSkip && (
              <Button
                type="button"
                variant="ghost"
                onClick={onSkip}
                disabled={isSubmitting}
                className="justify-start text-muted-foreground"
              >
                I'll provide this later
              </Button>
            )}

            <Button type="submit" disabled={isSubmitting} className="gap-2">
              {isSubmitting ? 'Submitting...' : 'Save investor profile'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default InvestorProfilePrompt;
