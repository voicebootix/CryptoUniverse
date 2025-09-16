import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import * as monaco from 'monaco-editor';
import Editor, { OnMount, OnChange } from '@monaco-editor/react';
import {
  Play,
  Save,
  Upload,
  Download,
  FileText,
  Code2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Settings,
  Eye,
  EyeOff,
  Terminal,
  Bug,
  Lightbulb,
  BookOpen,
  Zap,
  Cpu,
  Globe,
  Clock,
  TrendingUp,
  DollarSign
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  code_template: string;
  parameters: {
    name: string;
    type: string;
    default_value: any;
    description: string;
    required: boolean;
  }[];
  expected_returns: number;
  risk_level: string;
}

interface ValidationResult {
  is_valid: boolean;
  errors: {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning' | 'info';
  }[];
  warnings: {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning' | 'info';
  }[];
  performance_hints: string[];
  security_issues: string[];
}

interface StrategyMetadata {
  id?: string;
  name: string;
  description: string;
  category: string;
  version: string;
  risk_level: 'low' | 'medium' | 'high';
  expected_return_range: [number, number];
  required_capital: number;
  max_positions: number;
  trading_pairs: string[];
  timeframes: string[];
  tags: string[];
  is_public: boolean;
  license: string;
}

interface BacktestResult {
  strategy_id: string;
  period_days: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  avg_trade_duration: number;
  profit_factor: number;
  daily_returns: Array<{
    date: string;
    return: number;
    cumulative_return: number;
  }>;
  trade_history: Array<{
    entry_time: string;
    exit_time: string;
    symbol: string;
    side: string;
    pnl: number;
    return_pct: number;
  }>;
}

const StrategyIDE: React.FC = () => {
  const [code, setCode] = useState<string>('');
  const [metadata, setMetadata] = useState<StrategyMetadata>({
    name: '',
    description: '',
    category: 'algorithmic',
    version: '1.0.0',
    risk_level: 'medium',
    expected_return_range: [0, 0],
    required_capital: 1000,
    max_positions: 5,
    trading_pairs: ['BTC/USDT'],
    timeframes: ['1h'],
    tags: [],
    is_public: false,
    license: 'MIT'
  });
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [isRunningBacktest, setIsRunningBacktest] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [showConsole, setShowConsole] = useState(false);
  const [consoleOutput, setConsoleOutput] = useState<string[]>([]);
  const [editorTheme, setEditorTheme] = useState<'vs-dark' | 'vs-light'>('vs-dark');
  const [fontSize, setFontSize] = useState(14);
  const [autoSave, setAutoSave] = useState(true);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const completionProviderRef = useRef<monaco.IDisposable | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const queryClient = useQueryClient();

  // Cleanup completion provider and timers on unmount
  useEffect(() => {
    return () => {
      if (completionProviderRef.current) {
        completionProviderRef.current.dispose();
        completionProviderRef.current = null;
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
    };
  }, []);

  // Fetch strategy templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['strategy-templates'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/templates');
      return response.data.templates as StrategyTemplate[];
    }
  });

  // Save strategy mutation
  const saveStrategyMutation = useMutation({
    mutationFn: async (data: { code: string; metadata: StrategyMetadata; is_draft: boolean }) => {
      const response = await apiClient.post('/strategies/save', {
        code: data.code,
        metadata: data.metadata,
        is_draft: data.is_draft
      });
      return response.data;
    },
    onSuccess: (data) => {
      setLastSaved(new Date());
      toast.success('Strategy saved successfully');
      if (data.strategy_id) {
        setMetadata(prev => ({ ...prev, id: data.strategy_id }));
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to save strategy');
    }
  });

  // Validate strategy mutation
  const validateStrategyMutation = useMutation({
    mutationFn: async (code: string) => {
      // Create secure hash of code for logging (no code content exposed)
      const encoder = new TextEncoder();
      const data = encoder.encode(code);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

      console.log('🔍 Starting validation request...', {
        codeLength: code.length,
        codeHash: hashHex.substring(0, 16), // First 16 chars of hash
        hasContent: code.trim().length > 0
      });
      try {
        const response = await apiClient.post('/strategies/validate', { code });
        console.log('✅ Validation response received:', response.data);
        return response.data.validation_result as ValidationResult;
      } catch (error: any) {
        console.error('❌ Validation request failed');
        // Sanitized error logging - no sensitive data
        if (error.response) {
          console.error('Response error:', {
            status: error.response.status,
            message: error.response.data?.message || 'Server error'
          });
        } else if (error.request) {
          console.error('Request failed to send');
        } else {
          console.error('Setup error:', error.message);
        }
        throw error;
      }
    },
    onSuccess: (result) => {
      console.log('✅ Validation successful:', result);
      setValidationResult(result);
      
      // Update Monaco editor markers
      if (editorRef.current) {
        const model = editorRef.current.getModel();
        if (model) {
          const markers = [...(result.errors || []), ...(result.warnings || [])].map(issue => ({
            startLineNumber: issue.line,
            startColumn: issue.column,
            endLineNumber: issue.line,
            endColumn: issue.column + 10,
            message: issue.message,
            severity: issue.severity === 'error' ? monaco.MarkerSeverity.Error :
                     issue.severity === 'warning' ? monaco.MarkerSeverity.Warning :
                     monaco.MarkerSeverity.Info
          }));
          monaco.editor.setModelMarkers(model, 'strategy-validation', markers);
        }
      }

      // Add console output for validation
      const errors = result.errors || [];
      const warnings = result.warnings || [];
      const consoleMsg = result.is_valid
        ? `✅ Code validation passed!`
        : `❌ Validation failed: ${errors.length} errors, ${warnings.length} warnings`;

      setConsoleOutput(prev => [...prev, consoleMsg]);

      if (!result.is_valid && errors.length > 0) {
        setConsoleOutput(prev => [
          ...prev,
          ...errors.slice(0, 3).map(e => `  • Line ${e.line}: ${e.message}`)
        ]);
      }
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || 'Validation failed';
      toast.error(errorMsg);
      setConsoleOutput(prev => [...prev, `❌ Validation error: ${errorMsg}`]);
    }
  });

  // Run backtest mutation
  const runBacktestMutation = useMutation({
    mutationFn: async (data: { code: string; symbol?: string; start_date?: string; end_date?: string; initial_capital?: number }) => {
      // Add authentication check before starting
      const { useAuthStore } = await import('@/store/authStore');
      const { isAuthenticated, tokens } = useAuthStore.getState();

      console.log('🔐 Backtest auth check:', { isAuthenticated, hasToken: !!tokens?.access_token });

      if (!isAuthenticated || !tokens?.access_token) {
        console.error('❌ Not authenticated for backtest');
        toast.error('Please login to use Strategy IDE');
        throw new Error('Authentication required');
      }

      console.log('🚀 Starting backtest request...');

      // Calculate date range from period_days or use defaults
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(endDate.getDate() - 90); // Default 90 days

      const requestData = {
        code: data.code,
        symbol: data.symbol || 'BTC/USDT',
        start_date: data.start_date || startDate.toISOString().split('T')[0],
        end_date: data.end_date || endDate.toISOString().split('T')[0],
        initial_capital: data.initial_capital || 10000,
        parameters: {}
      };

      console.log('📊 Backtest request payload:', requestData);

      try {
        const response = await apiClient.post('/strategies/backtest', requestData);
        console.log('✅ Backtest response received:', response.data);
        return response.data.backtest_result as BacktestResult;
      } catch (error: any) {
        console.error('❌ Backtest request failed');
        // Sanitized error logging - no sensitive data
        if (error.response) {
          console.error('Response error:', {
            status: error.response.status,
            message: error.response.data?.message || 'Server error'
          });
        } else if (error.request) {
          console.error('Request failed to send');
        } else {
          console.error('Setup error:', error.message);
        }
        throw error;
      }
    },
    onSuccess: (result) => {
      setBacktestResult(result);
      setConsoleOutput(prev => [
        ...prev,
        `✅ Backtest completed: ${result.total_return}% return, Sharpe: ${result.sharpe_ratio}`,
        `📊 Trades: ${result.total_trades}, Win Rate: ${result.win_rate}%`
      ]);
      toast.success('Backtest completed successfully!');
      setShowConsole(true);
      setIsRunningBacktest(false);
    },
    onError: (error: any) => {
      setIsRunningBacktest(false);
      const errorMsg = error.response?.data?.detail || 'Backtest failed';
      toast.error(errorMsg);
      setConsoleOutput(prev => [
        ...prev,
        `❌ Backtest failed: ${errorMsg}`
      ]);
      setShowConsole(true);
    }
  });

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Configure Python language features
    completionProviderRef.current = monaco.languages.registerCompletionItemProvider('python', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn
        };

        const suggestions = [
          {
            label: 'buy_market',
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: 'buy_market(symbol="${1:BTC/USDT}", amount=${2:0.01})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Execute a market buy order',
            range: range
          },
          {
            label: 'sell_market',
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: 'sell_market(symbol="${1:BTC/USDT}", amount=${2:0.01})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Execute a market sell order',
            range: range
          },
          {
            label: 'get_balance',
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: 'get_balance("${1:USDT}")',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Get account balance for a currency',
            range: range
          },
          {
            label: 'get_price',
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: 'get_price("${1:BTC/USDT}")',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Get current price for a trading pair',
            range: range
          },
          {
            label: 'get_ohlcv',
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: 'get_ohlcv("${1:BTC/USDT}", "${2:1h}", ${3:100})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Get OHLCV candle data',
            range: range
          }
        ];
        
        return { suggestions };
      }
    });

    // Set up auto-validation on code change
    editor.onDidChangeModelContent(() => {
      if (autoSave) {
        // Clear previous debounce timer
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
        }
        // Set new debounce timer
        debounceTimerRef.current = window.setTimeout(() => {
          validateCode();
        }, 2000);
      }
    });
  };

  const handleCodeChange: OnChange = (value) => {
    setCode(value || '');
  };

  const validateCode = async (codeToValidate?: string) => {
    const targetCode = codeToValidate || code;
    console.log('🎯 validateCode called:', { hasCode: !!targetCode.trim() });

    if (!targetCode.trim()) {
      console.warn('⚠️ No code to validate');
      return;
    }

    // Add authentication check
    const { useAuthStore } = await import('@/store/authStore');
    const { isAuthenticated, tokens } = useAuthStore.getState();

    console.log('🔐 Auth state:', { isAuthenticated, hasToken: !!tokens?.access_token });

    if (!isAuthenticated || !tokens?.access_token) {
      console.error('❌ Not authenticated');
      toast.error('Please login to use Strategy IDE');
      setConsoleOutput(prev => [...prev, '❌ Authentication required to validate code']);
      return;
    }

    setIsValidating(true);
    try {
      await validateStrategyMutation.mutateAsync(targetCode);
    } catch (error: any) {
      console.error('❌ validateCode error:', error.message || 'Unknown error');
    } finally {
      setIsValidating(false);
    }
  };

  const saveStrategy = (isDraft = true) => {
    saveStrategyMutation.mutate({ code, metadata, is_draft: isDraft });
  };

  const runBacktest = (periodDays = 90) => {
    if (!validationResult?.is_valid) {
      toast.error('Please fix validation errors before running backtest');
      return;
    }
    setIsRunningBacktest(true);

    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - periodDays);

    runBacktestMutation.mutate({
      code,
      symbol: 'BTC/USDT',
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
      initial_capital: metadata.required_capital || 10000
    });
  };

  const loadTemplate = (templateId: string) => {
    const template = templates?.find(t => t.id === templateId);
    if (template) {
      setCode(template.code_template);
      setMetadata(prev => ({
        ...prev,
        name: template.name,
        description: template.description,
        category: template.category
      }));
      validateCode(template.code_template);
    }
  };

  const exportStrategy = () => {
    const strategyData = {
      code,
      metadata,
      validation: validationResult,
      backtest: backtestResult
    };
    
    const blob = new Blob([JSON.stringify(strategyData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${metadata.name || 'strategy'}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const importStrategy = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const strategyData = JSON.parse(e.target?.result as string);
        setCode(strategyData.code || '');
        setMetadata(strategyData.metadata || metadata);
        if (strategyData.validation) {
          setValidationResult(strategyData.validation);
        }
        if (strategyData.backtest) {
          setBacktestResult(strategyData.backtest);
        }
        toast.success('Strategy imported successfully');
      } catch (error) {
        toast.error('Invalid strategy file');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Code2 className="h-6 w-6 text-blue-500" />
            <h1 className="text-xl font-bold">Strategy IDE</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <Input
              placeholder="Strategy name..."
              value={metadata.name}
              onChange={(e) => setMetadata(prev => ({ ...prev, name: e.target.value }))}
              className="w-64"
            />
            {lastSaved && (
              <div className="text-sm text-muted-foreground">
                Saved {formatRelativeTime(lastSaved)}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowConsole(!showConsole)}
          >
            <Terminal className="h-4 w-4 mr-1" />
            Console
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => validateCode()}
            disabled={isValidating}
          >
            {isValidating ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4 mr-1" />
            )}
            Validate
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => runBacktest()}
            disabled={isRunningBacktest || !validationResult?.is_valid}
          >
            {isRunningBacktest ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-1" />
            )}
            Backtest
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => saveStrategy(true)}
            disabled={saveStrategyMutation.isPending}
          >
            <Save className="h-4 w-4 mr-1" />
            Save Draft
          </Button>
          
          <Button
            size="sm"
            onClick={() => saveStrategy(false)}
            disabled={saveStrategyMutation.isPending || !validationResult?.is_valid}
          >
            <Upload className="h-4 w-4 mr-1" />
            Publish
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 border-r bg-muted/20 flex flex-col">
          <Tabs defaultValue="templates" className="flex-1">
            <div className="p-4 border-b">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="templates">Templates</TabsTrigger>
                <TabsTrigger value="metadata">Settings</TabsTrigger>
                <TabsTrigger value="tools">Tools</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="templates" className="p-4 space-y-4 flex-1 overflow-auto">
              <div>
                <Label>Strategy Templates</Label>
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a template..." />
                  </SelectTrigger>
                  <SelectContent>
                    {templates?.map((template) => (
                      <SelectItem key={template.id} value={template.id}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedTemplate && (
                  <Button
                    variant="outline"
                    className="w-full mt-2"
                    onClick={() => loadTemplate(selectedTemplate)}
                  >
                    Load Template
                  </Button>
                )}
              </div>

              {templates?.find(t => t.id === selectedTemplate) && (
                <Card>
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      <div className="font-medium">{templates.find(t => t.id === selectedTemplate)?.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {templates.find(t => t.id === selectedTemplate)?.description}
                      </div>
                      <div className="flex gap-2">
                        <Badge variant="outline">
                          {templates.find(t => t.id === selectedTemplate)?.category}
                        </Badge>
                        <Badge variant="outline">
                          {templates.find(t => t.id === selectedTemplate)?.difficulty}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="metadata" className="p-4 space-y-4 flex-1 overflow-auto">
              <div className="space-y-4">
                <div>
                  <Label>Description</Label>
                  <Textarea
                    placeholder="Describe your strategy..."
                    value={metadata.description}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                  />
                </div>

                <div>
                  <Label>Category</Label>
                  <Select
                    value={metadata.category}
                    onValueChange={(value) => setMetadata(prev => ({ ...prev, category: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="algorithmic">Algorithmic</SelectItem>
                      <SelectItem value="momentum">Momentum</SelectItem>
                      <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
                      <SelectItem value="arbitrage">Arbitrage</SelectItem>
                      <SelectItem value="scalping">Scalping</SelectItem>
                      <SelectItem value="swing">Swing Trading</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Risk Level</Label>
                  <Select
                    value={metadata.risk_level}
                    onValueChange={(value: 'low' | 'medium' | 'high') => setMetadata(prev => ({ ...prev, risk_level: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low Risk</SelectItem>
                      <SelectItem value="medium">Medium Risk</SelectItem>
                      <SelectItem value="high">High Risk</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Required Capital (USD)</Label>
                  <Input
                    type="number"
                    value={metadata.required_capital}
                    onChange={(e) => setMetadata(prev => ({ ...prev, required_capital: parseInt(e.target.value) || 0 }))}
                  />
                </div>

                <div>
                  <Label>Max Positions</Label>
                  <Input
                    type="number"
                    value={metadata.max_positions}
                    onChange={(e) => setMetadata(prev => ({ ...prev, max_positions: parseInt(e.target.value) || 1 }))}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={metadata.is_public}
                    onCheckedChange={(checked) => setMetadata(prev => ({ ...prev, is_public: checked }))}
                  />
                  <Label>Make strategy public</Label>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="tools" className="p-4 space-y-4 flex-1 overflow-auto">
              <div className="space-y-4">
                <div>
                  <Label>Editor Theme</Label>
                  <Select
                    value={editorTheme}
                    onValueChange={(value: 'vs-dark' | 'vs-light') => setEditorTheme(value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vs-dark">Dark Theme</SelectItem>
                      <SelectItem value="vs-light">Light Theme</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Font Size</Label>
                  <Input
                    type="number"
                    value={fontSize}
                    onChange={(e) => setFontSize(parseInt(e.target.value) || 14)}
                    min={10}
                    max={24}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={autoSave}
                    onCheckedChange={setAutoSave}
                  />
                  <Label>Auto-save & validate</Label>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={exportStrategy}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export Strategy
                  </Button>

                  <div>
                    <input
                      type="file"
                      accept=".json"
                      onChange={importStrategy}
                      className="hidden"
                      id="import-strategy"
                    />
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => document.getElementById('import-strategy')?.click()}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Import Strategy
                    </Button>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 relative">
            <Editor
              height="100%"
              defaultLanguage="python"
              theme={editorTheme}
              value={code}
              onChange={handleCodeChange}
              onMount={handleEditorDidMount}
              options={{
                fontSize,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                wordWrap: 'on',
                lineNumbers: 'on',
                folding: true,
                matchBrackets: 'always',
                autoIndent: 'full',
                formatOnPaste: true,
                formatOnType: true,
                suggestOnTriggerCharacters: true,
                quickSuggestions: true,
                parameterHints: { enabled: true },
                hover: { enabled: true }
              }}
            />

            {/* Validation Overlay */}
            {validationResult && (
              <div className="absolute top-4 right-4 z-10">
                <Card className={`w-80 ${validationResult.is_valid ? 'border-green-500' : 'border-red-500'}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      {validationResult.is_valid ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      <div className="font-medium">
                        {validationResult.is_valid ? 'Code Valid' : 'Validation Issues'}
                      </div>
                    </div>
                    
                    {validationResult.errors && validationResult.errors.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-sm font-medium text-red-600">Errors:</div>
                        {validationResult.errors.slice(0, 3).map((error, i) => (
                          <div key={i} className="text-xs text-red-600">
                            Line {error.line}: {error.message}
                          </div>
                        ))}
                      </div>
                    )}

                    {validationResult.warnings && validationResult.warnings.length > 0 && (
                      <div className="space-y-1 mt-2">
                        <div className="text-sm font-medium text-yellow-600">Warnings:</div>
                        {validationResult.warnings.slice(0, 2).map((warning, i) => (
                          <div key={i} className="text-xs text-yellow-600">
                            Line {warning.line}: {warning.message}
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

          {/* Console */}
          {showConsole && (
            <div className="h-48 border-t bg-black text-green-400 font-mono text-sm overflow-auto">
              <div className="p-4">
                <div className="text-gray-400 mb-2">Strategy Console Output</div>
                {consoleOutput.length === 0 ? (
                  <div className="text-gray-500">No output yet. Run validation or backtest to see results.</div>
                ) : (
                  consoleOutput.map((line, i) => (
                    <div key={i}>{line}</div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Results Panel */}
        {backtestResult && (
          <div className="w-96 border-l bg-muted/20 overflow-auto">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold">Backtest Results</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setBacktestResult(null)}
                >
                  <XCircle className="h-4 w-4" />
                </Button>
              </div>

              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Total Return</span>
                        <span className={`font-bold ${backtestResult.total_return >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatPercentage(backtestResult.total_return)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Sharpe Ratio</span>
                        <span className="font-medium">{backtestResult.sharpe_ratio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Max Drawdown</span>
                        <span className="font-medium text-red-500">
                          {formatPercentage(backtestResult.max_drawdown)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Win Rate</span>
                        <span className="font-medium text-green-500">
                          {formatPercentage(backtestResult.win_rate)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Total Trades</span>
                        <span className="font-medium">{backtestResult.total_trades}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Recent Trades</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      {backtestResult.trade_history.slice(0, 5).map((trade, i) => (
                        <div key={i} className="flex justify-between text-sm">
                          <span>{trade.symbol}</span>
                          <span className={trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                            {formatPercentage(trade.return_pct)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyIDE;