import React from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Filter } from 'lucide-react';
import type { OpportunityFilter, OpportunitySort } from './types';

interface OpportunityFiltersProps {
  activeFilter: OpportunityFilter;
  onFilterChange: (filter: OpportunityFilter) => void;
  sortBy: OpportunitySort;
  onSortChange: (sort: OpportunitySort) => void;
  validatedCount: number;
  totalCount: number;
}

export const OpportunityFilters: React.FC<OpportunityFiltersProps> = ({
  activeFilter,
  onFilterChange,
  sortBy,
  onSortChange,
  validatedCount,
  totalCount
}) => {
  return (
    <div className="space-y-4">
      {/* Filter Tabs */}
      <Tabs value={activeFilter} onValueChange={(v) => onFilterChange(v as OpportunityFilter)}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="validated" className="gap-1">
            <Sparkles className="h-3 w-3" />
            Validated
            <Badge variant="secondary" className="ml-1">{validatedCount}</Badge>
          </TabsTrigger>
          <TabsTrigger value="all" className="gap-1">
            All
            <Badge variant="secondary" className="ml-1">{totalCount}</Badge>
          </TabsTrigger>
          <TabsTrigger value="high">
            High ({'>'}80%)
          </TabsTrigger>
          <TabsTrigger value="medium">
            Medium (60-80%)
          </TabsTrigger>
          <TabsTrigger value="low">
            Low ({'<'}60%)
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Sort Dropdown */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Sort by:</span>
        <Select value={sortBy} onValueChange={(v) => onSortChange(v as OpportunitySort)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="confidence">Confidence (High to Low)</SelectItem>
            <SelectItem value="potential_gain">Potential Gain (High to Low)</SelectItem>
            <SelectItem value="risk_reward">Risk/Reward Ratio</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
};

export default OpportunityFilters;
