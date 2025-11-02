#!/usr/bin/env python3
"""
Render Logs Analysis Script

Analyzes Render application logs to:
1. Validate race condition fix for opportunity scan status endpoint
2. Identify performance bottlenecks and errors
3. Generate metrics and recommendations
"""

import re
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse


class RenderLogAnalyzer:
    """Analyzes Render application logs for performance and reliability issues."""
    
    def __init__(self):
        self.scan_initiations = []
        self.status_checks = []
        self.db_queries = []
        self.api_errors = defaultdict(list)
        self.strategy_timeouts = []
        self.performance_alerts = []
        self.kraken_errors = []
        self.coingecko_rate_limits = []
        self.coincap_errors = []
        self.database_timeouts = []
        
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse a single log line and extract relevant information."""
        result = {}
        
        # HTTP requests
        http_match = re.search(r'(GET|POST|PUT|DELETE)\s+([^\s]+)\s+HTTP/1\.1"\s+(\d+)', line)
        if http_match:
            method, path, status = http_match.groups()
            result['type'] = 'http_request'
            result['method'] = method
            result['path'] = path
            result['status'] = int(status)
            
            # Check for opportunity scan endpoints
            if '/opportunities/discover' in path:
                result['endpoint'] = 'discover'
                scan_id_match = re.search(r'scan_[a-f0-9]+', line)
                if scan_id_match:
                    result['scan_id'] = scan_id_match.group()
            elif '/opportunities/status/' in path:
                result['endpoint'] = 'status'
                scan_id_match = re.search(r'scan_[a-f0-9]+', path)
                if scan_id_match:
                    result['scan_id'] = scan_id_match.group()
            
            return result
        
        # Database query performance
        db_match = re.search(r'(Slow|Very slow) database query.*duration=([\d.]+)', line)
        if db_match:
            severity, duration = db_match.groups()
            result['type'] = 'db_query'
            result['severity'] = severity.lower()
            result['duration'] = float(duration)
            return result
        
        # Kraken API errors
        if 'kraken' in line.lower() and 'error' in line.lower():
            if 'EAPI:Invalid nonce' in line:
                result['type'] = 'kraken_nonce_error'
                attempt_match = re.search(r'Attempt (\d+)', line)
                if attempt_match:
                    result['attempt'] = int(attempt_match.group(1))
                return result
        
        # CoinGecko rate limiting
        if 'coingecko' in line.lower() and 'rate limited' in line.lower():
            result['type'] = 'coingecko_rate_limit'
            api_match = re.search(r'API\s+([^\s]+)', line)
            if api_match:
                result['api'] = api_match.group(1)
            return result
        
        # CoinCap errors
        if 'coincap' in line.lower() and ('failed' in line.lower() or 'error' in line.lower()):
            result['type'] = 'coincap_error'
            error_match = re.search(r'error=([^,\s]+)', line)
            if error_match:
                result['error'] = error_match.group(1)
            return result
        
        # Strategy timeouts
        if '❌' in line and 'Strategy:' in line and 'TimeoutError' in line:
            result['type'] = 'strategy_timeout'
            strategy_match = re.search(r'Strategy:\s+([^\n]+)', line)
            if strategy_match:
                result['strategy'] = strategy_match.group(1).strip()
            elapsed_match = re.search(r'elapsed_seconds=([\d.]+)', line)
            if elapsed_match:
                result['elapsed_seconds'] = float(elapsed_match.group(1))
            return result
        
        # Performance degradation alerts
        if 'OPPORTUNITY DISCOVERY PERFORMANCE DEGRADED' in line:
            result['type'] = 'performance_alert'
            time_match = re.search(r'total_time_ms=([\d.]+)', line)
            if time_match:
                result['total_time_ms'] = float(time_match.group(1))
            threshold_match = re.search(r'alert_threshold=([\d.]+)', line)
            if threshold_match:
                result['threshold'] = float(threshold_match.group(1))
            return result
        
        # Database connection timeouts
        if ('CancelledError' in line or 'TimeoutError' in line) and ('asyncpg' in line or 'SQLAlchemy' in line):
            result['type'] = 'db_timeout'
            if 'portfolio aggregation' in line.lower():
                result['context'] = 'portfolio_aggregation'
            return result
        
        return None
    
    def analyze_logs(self, log_content: str) -> Dict:
        """Analyze log content and extract metrics."""
        lines = log_content.split('\n')
        
        for line in lines:
            parsed = self.parse_log_line(line)
            if not parsed:
                continue
            
            if parsed['type'] == 'http_request':
                if parsed.get('endpoint') == 'discover':
                    self.scan_initiations.append(parsed)
                elif parsed.get('endpoint') == 'status':
                    self.status_checks.append(parsed)
            
            elif parsed['type'] == 'db_query':
                self.db_queries.append(parsed)
            
            elif parsed['type'] == 'kraken_nonce_error':
                self.kraken_errors.append(parsed)
            
            elif parsed['type'] == 'coingecko_rate_limit':
                self.coingecko_rate_limits.append(parsed)
            
            elif parsed['type'] == 'coincap_error':
                self.coincap_errors.append(parsed)
            
            elif parsed['type'] == 'strategy_timeout':
                self.strategy_timeouts.append(parsed)
            
            elif parsed['type'] == 'performance_alert':
                self.performance_alerts.append(parsed)
            
            elif parsed['type'] == 'db_timeout':
                self.database_timeouts.append(parsed)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate analysis report."""
        report = {
            'race_condition_fix_validation': self._validate_race_condition_fix(),
            'database_performance': self._analyze_database_performance(),
            'external_api_issues': self._analyze_external_apis(),
            'strategy_execution': self._analyze_strategy_execution(),
            'overall_performance': self._analyze_overall_performance(),
            'summary': {}
        }
        
        # Generate summary
        report['summary'] = {
            'total_scans_initiated': len(self.scan_initiations),
            'total_status_checks': len(self.status_checks),
            'status_check_success_rate': self._calculate_status_success_rate(),
            'total_db_slow_queries': len(self.db_queries),
            'total_kraken_errors': len(self.kraken_errors),
            'total_strategy_timeouts': len(self.strategy_timeouts),
            'performance_alerts_count': len(self.performance_alerts),
        }
        
        return report
    
    def _validate_race_condition_fix(self) -> Dict:
        """Validate that race condition fix is working."""
        # Match scan initiations with status checks
        scan_ids = {s.get('scan_id') for s in self.scan_initiations if s.get('scan_id')}
        status_scan_ids = {s.get('scan_id') for s in self.status_checks if s.get('scan_id')}
        
        successful_status_checks = [s for s in self.status_checks if s.get('status') == 200]
        failed_status_checks = [s for s in self.status_checks if s.get('status') != 200]
        
        return {
            'fix_status': 'VALIDATED' if len(failed_status_checks) == 0 else 'NEEDS_REVIEW',
            'scans_with_status_checks': len(scan_ids & status_scan_ids),
            'successful_status_checks': len(successful_status_checks),
            'failed_status_checks': len(failed_status_checks),
            'status_check_success_rate': len(successful_status_checks) / len(self.status_checks) * 100 if self.status_checks else 0,
        }
    
    def _analyze_database_performance(self) -> Dict:
        """Analyze database query performance."""
        if not self.db_queries:
            return {'status': 'no_issues_found'}
        
        durations = [q['duration'] for q in self.db_queries]
        slow_queries = [q for q in self.db_queries if q['duration'] > 1.0]
        very_slow_queries = [q for q in self.db_queries if q['duration'] > 2.0]
        
        return {
            'status': 'CRITICAL' if len(very_slow_queries) > 0 else 'WARNING' if len(slow_queries) > 0 else 'OK',
            'total_slow_queries': len(self.db_queries),
            'queries_over_1s': len(slow_queries),
            'queries_over_2s': len(very_slow_queries),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
        }
    
    def _analyze_external_apis(self) -> Dict:
        """Analyze external API issues."""
        return {
            'kraken': {
                'status': 'CRITICAL' if len(self.kraken_errors) > 0 else 'OK',
                'error_count': len(self.kraken_errors),
                'max_attempts': max([e.get('attempt', 0) for e in self.kraken_errors]) if self.kraken_errors else 0,
            },
            'coingecko': {
                'status': 'WARNING' if len(self.coingecko_rate_limits) > 0 else 'OK',
                'rate_limit_count': len(self.coingecko_rate_limits),
                'affected_apis': list(set([e.get('api', 'unknown') for e in self.coingecko_rate_limits])),
            },
            'coincap': {
                'status': 'WARNING' if len(self.coincap_errors) > 0 else 'OK',
                'error_count': len(self.coincap_errors),
                'errors': [e.get('error', 'unknown') for e in self.coincap_errors[:5]],  # First 5
            },
        }
    
    def _analyze_strategy_execution(self) -> Dict:
        """Analyze strategy execution timeouts."""
        if not self.strategy_timeouts:
            return {'status': 'no_timeouts_found'}
        
        strategies = [s.get('strategy', 'unknown') for s in self.strategy_timeouts]
        elapsed_times = [s.get('elapsed_seconds', 0) for s in self.strategy_timeouts]
        
        strategy_counts = defaultdict(int)
        for s in strategies:
            strategy_counts[s] += 1
        
        return {
            'status': 'CRITICAL',
            'total_timeouts': len(self.strategy_timeouts),
            'unique_strategies': len(set(strategies)),
            'avg_elapsed_seconds': sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0,
            'max_elapsed_seconds': max(elapsed_times) if elapsed_times else 0,
            'strategies_by_count': dict(sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True)),
        }
    
    def _analyze_overall_performance(self) -> Dict:
        """Analyze overall performance metrics."""
        if not self.performance_alerts:
            return {'status': 'no_alerts_found'}
        
        total_times = [a.get('total_time_ms', 0) / 1000 for a in self.performance_alerts]  # Convert to seconds
        thresholds = [a.get('threshold', 10) for a in self.performance_alerts]
        
        return {
            'status': 'CRITICAL',
            'alert_count': len(self.performance_alerts),
            'avg_scan_duration_seconds': sum(total_times) / len(total_times) if total_times else 0,
            'max_scan_duration_seconds': max(total_times) if total_times else 0,
            'avg_threshold_seconds': sum(thresholds) / len(thresholds) if thresholds else 0,
            'degradation_factor': (sum(total_times) / len(total_times)) / (sum(thresholds) / len(thresholds)) if total_times and thresholds else 0,
        }
    
    def _calculate_status_success_rate(self) -> float:
        """Calculate status check success rate."""
        if not self.status_checks:
            return 0.0
        successful = len([s for s in self.status_checks if s.get('status') == 200])
        return (successful / len(self.status_checks)) * 100 if self.status_checks else 0.0


def main():
    parser = argparse.ArgumentParser(description='Analyze Render application logs')
    parser.add_argument('log_file', help='Path to log file (or use stdin)')
    parser.add_argument('--output', '-o', help='Output JSON file for report', default=None)
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    # Read log file
    try:
        with open(args.log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
    except FileNotFoundError:
        print(f"Error: Log file '{args.log_file}' not found.")
        return 1
    
    # Analyze logs
    analyzer = RenderLogAnalyzer()
    report = analyzer.analyze_logs(log_content)
    
    # Output results
    if args.format == 'json':
        output = json.dumps(report, indent=2)
    else:
        output = format_text_report(report)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)
    
    return 0


def format_text_report(report: Dict) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("RENDER LOGS ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Race condition fix validation
    lines.append("1. RACE CONDITION FIX VALIDATION")
    lines.append("-" * 80)
    rc = report['race_condition_fix_validation']
    lines.append(f"  Status: {rc['fix_status']}")
    lines.append(f"  Successful Status Checks: {rc['successful_status_checks']}")
    lines.append(f"  Failed Status Checks: {rc['failed_status_checks']}")
    lines.append(f"  Success Rate: {rc['status_check_success_rate']:.1f}%")
    lines.append("")
    
    # Database performance
    lines.append("2. DATABASE PERFORMANCE")
    lines.append("-" * 80)
    db = report['database_performance']
    lines.append(f"  Status: {db.get('status', 'N/A')}")
    if db.get('status') != 'no_issues_found':
        lines.append(f"  Total Slow Queries: {db.get('total_slow_queries', 0)}")
        lines.append(f"  Queries > 1s: {db.get('queries_over_1s', 0)}")
        lines.append(f"  Queries > 2s: {db.get('queries_over_2s', 0)}")
        lines.append(f"  Avg Duration: {db.get('avg_duration', 0):.3f}s")
        lines.append(f"  Max Duration: {db.get('max_duration', 0):.3f}s")
    lines.append("")
    
    # External APIs
    lines.append("3. EXTERNAL API ISSUES")
    lines.append("-" * 80)
    apis = report['external_api_issues']
    for api_name, api_data in apis.items():
        lines.append(f"  {api_name.upper()}:")
        lines.append(f"    Status: {api_data.get('status', 'N/A')}")
        if api_name == 'kraken':
            lines.append(f"    Error Count: {api_data.get('error_count', 0)}")
            lines.append(f"    Max Attempts: {api_data.get('max_attempts', 0)}")
        elif api_name == 'coingecko':
            lines.append(f"    Rate Limit Hits: {api_data.get('rate_limit_count', 0)}")
        elif api_name == 'coincap':
            lines.append(f"    Error Count: {api_data.get('error_count', 0)}")
    lines.append("")
    
    # Strategy execution
    lines.append("4. STRATEGY EXECUTION")
    lines.append("-" * 80)
    strat = report['strategy_execution']
    if strat.get('status') != 'no_timeouts_found':
        lines.append(f"  Status: {strat.get('status', 'N/A')}")
        lines.append(f"  Total Timeouts: {strat.get('total_timeouts', 0)}")
        lines.append(f"  Unique Strategies: {strat.get('unique_strategies', 0)}")
        lines.append(f"  Avg Elapsed Time: {strat.get('avg_elapsed_seconds', 0):.1f}s")
        lines.append(f"  Max Elapsed Time: {strat.get('max_elapsed_seconds', 0):.1f}s")
        lines.append("  Top Affected Strategies:")
        for strategy, count in list(strat.get('strategies_by_count', {}).items())[:5]:
            lines.append(f"    - {strategy}: {count} timeouts")
    else:
        lines.append("  Status: No timeouts found")
    lines.append("")
    
    # Overall performance
    lines.append("5. OVERALL PERFORMANCE")
    lines.append("-" * 80)
    perf = report['overall_performance']
    if perf.get('status') != 'no_alerts_found':
        lines.append(f"  Status: {perf.get('status', 'N/A')}")
        lines.append(f"  Alert Count: {perf.get('alert_count', 0)}")
        lines.append(f"  Avg Scan Duration: {perf.get('avg_scan_duration_seconds', 0):.1f}s")
        lines.append(f"  Max Scan Duration: {perf.get('max_scan_duration_seconds', 0):.1f}s")
        lines.append(f"  Degradation Factor: {perf.get('degradation_factor', 0):.1f}x")
    else:
        lines.append("  Status: No performance alerts found")
    lines.append("")
    
    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 80)
    summary = report['summary']
    for key, value in summary.items():
        lines.append(f"  {key.replace('_', ' ').title()}: {value}")
    
    return "\n".join(lines)


if __name__ == '__main__':
    exit(main())
