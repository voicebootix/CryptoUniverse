"""
Enterprise System Monitoring Service

Comprehensive monitoring and metrics collection for the CryptoUniverse platform.
Provides real-time system health, performance metrics, and alerting capabilities.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import deque
import math
import statistics

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = None


@dataclass
class SystemAlert:
    """System alert definition."""
    id: str
    severity: str  # "info", "warning", "critical"
    message: str
    timestamp: datetime
    resolved: bool = False


class MetricsCollector:
    """Enterprise metrics collection and aggregation."""
    
    def __init__(self, max_points: int = 100):  # PRODUCTION: Reduced from 1000 for memory efficiency
        self.metrics = {}
        self.max_points = max_points
        
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric point."""
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.max_points)
        
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            tags=tags or {}
        )
        self.metrics[name].append(point)
    
    def get_metric_summary(self, name: str, duration_minutes: int = 15) -> Dict[str, Any]:
        """Get metric summary for the last N minutes."""
        if name not in self.metrics:
            return {"error": f"Metric {name} not found"}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        recent_points = [
            point for point in self.metrics[name] 
            if point.timestamp >= cutoff_time
        ]
        
        if not recent_points:
            return {"error": f"No recent data for {name}"}
        
        values = [point.value for point in recent_points]
        sorted_values = sorted(values)
        first_value = values[0]
        last_value = values[-1]
        avg_value = sum(values) / len(values)
        p95_index = max(0, math.ceil(0.95 * len(sorted_values)) - 1)
        p95_value = sorted_values[p95_index]
        median_value = statistics.median(sorted_values)

        change_pct: Optional[float]
        if first_value:
            change_pct = ((last_value - first_value) / first_value) * 100
        elif last_value:
            change_pct = float("inf")
        else:
            change_pct = 0.0

        trend = "stable"
        if isinstance(change_pct, (int, float)):
            if change_pct > 10:
                trend = "increasing"
            elif change_pct < -10:
                trend = "decreasing"

        return {
            "metric": name,
            "duration_minutes": duration_minutes,
            "points_count": len(values),
            "current": last_value,
            "average": avg_value,
            "median": median_value,
            "p95": p95_value,
            "min": min(sorted_values),
            "max": max(sorted_values),
            "trend": trend,
            "change_pct": None if change_pct in {float("inf"), float("-inf")} else change_pct,
        }
    
    def get_all_metrics_summary(self, duration_minutes: int = 15) -> Dict[str, Any]:
        """Get summary of all metrics."""
        return {
            name: self.get_metric_summary(name, duration_minutes)
            for name in self.metrics.keys()
        }


class SystemMonitoringService:
    """Enterprise-grade system monitoring service."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.active_alerts = []
        self.alert_history = deque(maxlen=100)
        self.monitoring_active = False
        self._monitoring_task = None
        
        # Monitoring thresholds
        self.thresholds = {
            "cpu_usage_pct": {"warning": 80.0, "critical": 95.0},
            "memory_usage_pct": {"warning": 85.0, "critical": 95.0},
            "disk_usage_pct": {"warning": 80.0, "critical": 90.0},
            "response_time_ms": {"warning": 2000.0, "critical": 5000.0},
            "error_rate_pct": {"warning": 5.0, "critical": 10.0},
            # Signal-specific thresholds
            "signal_generation_empty": {"warning": 3.0, "critical": 10.0},  # Count in 15 min
            "signal_delivery_failed_all": {"warning": 2.0, "critical": 5.0},  # Count in 15 min
            "signal_delivery_telegram_failed": {"warning": 5.0, "critical": 15.0},  # Count in 15 min
            "signal_delivery_webhook_failed": {"warning": 5.0, "critical": 15.0},  # Count in 15 min
        }
    
    async def start_monitoring(self, interval_seconds: int = 120):  # PRODUCTION: 2 minutes instead of 30s
        """Start continuous monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info("System monitoring started", interval_seconds=interval_seconds)
    
    async def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._check_alert_conditions()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e))
                await asyncio.sleep(interval_seconds)

    def get_performance_trends(self) -> Dict[str, Any]:
        """Expose smoothed performance metrics for dashboards and alerts."""
        metric_windows = {
            "http_request_duration_ms": 15,
            "db_query_duration_ms": 15,
            "redis_response_time_ms": 15,
            "db_slow_query_count": 60,
        }

        trends: Dict[str, Any] = {}
        for metric, window in metric_windows.items():
            summary = self.metrics_collector.get_metric_summary(metric, window)
            if "error" not in summary:
                trends[metric] = summary
        return trends
    
    async def _collect_system_metrics(self):
        """Collect comprehensive system metrics."""
        try:
            # System Resource Metrics
            try:
                import psutil
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.metrics_collector.record_metric("cpu_usage_pct", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.metrics_collector.record_metric("memory_usage_pct", memory.percent)
                self.metrics_collector.record_metric("memory_available_gb", memory.available / (1024**3))
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.metrics_collector.record_metric("disk_usage_pct", disk_percent)
                self.metrics_collector.record_metric("disk_free_gb", disk.free / (1024**3))
                
                # Network metrics
                network = psutil.net_io_counters()
                self.metrics_collector.record_metric("network_bytes_sent", network.bytes_sent)
                self.metrics_collector.record_metric("network_bytes_recv", network.bytes_recv)
                
            except ImportError:
                logger.debug("psutil not available for system metrics")
            
            # Application-specific metrics
            await self._collect_application_metrics()
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
    
    async def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        try:
            # Redis connection metrics
            try:
                from app.core.redis import redis_manager
                start_time = time.time()
                redis_ping = await redis_manager.ping()
                redis_response_time = (time.time() - start_time) * 1000
                
                self.metrics_collector.record_metric(
                    "redis_response_time_ms", 
                    redis_response_time,
                    {"status": "healthy" if redis_ping else "unhealthy"}
                )
                self.metrics_collector.record_metric(
                    "redis_availability", 
                    1.0 if redis_ping else 0.0
                )
            except Exception as e:
                logger.debug("Redis metrics collection failed", error=str(e))
                self.metrics_collector.record_metric("redis_availability", 0.0)
            
            # Database connection metrics
            try:
                from app.core.database import AsyncSessionLocal
                start_time = time.time()
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import text
                    await db.execute(text("SELECT 1"))
                db_response_time = (time.time() - start_time) * 1000
                
                self.metrics_collector.record_metric("database_response_time_ms", db_response_time)
                self.metrics_collector.record_metric("database_availability", 1.0)
            except Exception as e:
                logger.debug("Database metrics collection failed", error=str(e))
                self.metrics_collector.record_metric("database_availability", 0.0)
            
            # Market data service metrics
            try:
                from app.services.market_data_feeds import market_data_feeds
                start_time = time.time()
                btc_price = await market_data_feeds.get_real_time_price("BTC")
                market_response_time = (time.time() - start_time) * 1000
                
                self.metrics_collector.record_metric("market_data_response_time_ms", market_response_time)
                self.metrics_collector.record_metric(
                    "market_data_availability", 
                    1.0 if btc_price.get("success") else 0.0
                )
            except Exception as e:
                logger.debug("Market data metrics collection failed", error=str(e))
                self.metrics_collector.record_metric("market_data_availability", 0.0)
            
        except Exception as e:
            logger.error("Failed to collect application metrics", error=str(e))
    
    async def _check_alert_conditions(self):
        """Check for alert conditions and generate alerts."""
        try:
            current_time = datetime.utcnow()

            for metric_name, thresholds in self.thresholds.items():
                summary = self.metrics_collector.get_metric_summary(metric_name, duration_minutes=15)

                if "error" in summary:
                    continue

                # For count-based metrics (like signal failures), use points_count
                # For percentage-based metrics (like CPU), use current value
                if metric_name.startswith("signal_"):
                    # Count-based metric - check total occurrences in time window
                    check_value = summary.get("points_count", 0)
                else:
                    # Percentage/value-based metric - check current value
                    check_value = summary.get("current", 0)

                # Check critical threshold
                if check_value >= thresholds["critical"]:
                    alert_id = f"{metric_name}_critical_{int(time.time())}"

                    # Build appropriate message based on metric type
                    if metric_name.startswith("signal_"):
                        message = f"{metric_name}: {check_value} failures in 15 min >= {thresholds['critical']} (CRITICAL)"
                    else:
                        message = f"{metric_name}: {check_value:.2f} >= {thresholds['critical']} (CRITICAL)"

                    alert = SystemAlert(
                        id=alert_id,
                        severity="critical",
                        message=message,
                        timestamp=current_time
                    )
                    await self._add_alert(alert)

                    # ENTERPRISE: Trigger cleanup for disk usage issues
                    if metric_name == "disk_usage_pct" and check_value >= 80:
                        await self._trigger_disk_cleanup()

                # Check warning threshold
                elif check_value >= thresholds["warning"]:
                    alert_id = f"{metric_name}_warning_{int(time.time())}"

                    # Build appropriate message based on metric type
                    if metric_name.startswith("signal_"):
                        message = f"{metric_name}: {check_value} failures in 15 min >= {thresholds['warning']} (WARNING)"
                    else:
                        message = f"{metric_name}: {check_value:.2f} >= {thresholds['warning']} (WARNING)"

                    alert = SystemAlert(
                        id=alert_id,
                        severity="warning",
                        message=message,
                        timestamp=current_time
                    )
                    await self._add_alert(alert)

        except Exception as e:
            logger.error("Failed to check alert conditions", error=str(e))
    
    async def _trigger_disk_cleanup(self):
        """ENTERPRISE: Aggressive disk cleanup when usage is critical."""
        try:
            import os
            import tempfile
            import subprocess
            import shutil
            
            logger.warning("High disk usage detected - triggering AGGRESSIVE cleanup")
            files_cleaned = 0
            space_freed_mb = 0
            
            # Get initial disk usage
            try:
                initial_usage = shutil.disk_usage('/')
                initial_free = initial_usage.free
            except Exception:
                initial_free = 0
            
            # 1. Clean up temp files (more aggressive - 6 hours instead of 1 day)
            temp_dir = tempfile.gettempdir()
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.getmtime(file_path) < time.time() - 21600:  # 6 hours
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                files_cleaned += 1
                                space_freed_mb += file_size / 1024 / 1024
                        except Exception:
                            pass
            
            # 2. Clean up Docker build cache (if available)
            try:
                result = subprocess.run(['docker', 'system', 'prune', '-f'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("Docker cache cleanup completed", output=result.stdout)
            except Exception:
                pass  # Docker might not be available
            
            # 3. Clean up package manager cache
            cache_dirs = [
                "/root/.cache",
                "/tmp/.cache", 
                "/app/.cache",
                "/var/cache",
                "/home/appuser/.cache"
            ]
            
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    try:
                        for root, dirs, files in os.walk(cache_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.getmtime(file_path) < time.time() - 3600:  # 1 hour
                                        file_size = os.path.getsize(file_path)
                                        os.remove(file_path)
                                        files_cleaned += 1
                                        space_freed_mb += file_size / 1024 / 1024
                                except Exception:
                                    pass
                    except Exception:
                        pass
            
            # 4. Clean up old log files (more aggressive)
            log_dirs = ["/var/log", "/tmp", "./logs", "/app/logs"]
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            try:
                                if (file.endswith('.log') or file.endswith('.log.gz') or 
                                    file.endswith('.out') or file.endswith('.err')):
                                    file_path = os.path.join(root, file)
                                    if os.path.getmtime(file_path) < time.time() - 86400:  # 1 day instead of 1 week
                                        file_size = os.path.getsize(file_path)
                                        os.remove(file_path)
                                        files_cleaned += 1
                                        space_freed_mb += file_size / 1024 / 1024
                            except Exception:
                                pass
            
            # 5. Clean up Python cache files
            python_cache_dirs = ["/app/__pycache__", "/tmp/__pycache__"]
            for cache_dir in python_cache_dirs:
                if os.path.exists(cache_dir):
                    try:
                        shutil.rmtree(cache_dir)
                        logger.info(f"Removed Python cache directory: {cache_dir}")
                    except Exception:
                        pass
            
            # Get final disk usage
            try:
                final_usage = shutil.disk_usage('/')
                final_free = final_usage.free
                actual_freed_mb = (final_free - initial_free) / 1024 / 1024
            except Exception:
                actual_freed_mb = space_freed_mb
            
            logger.info("AGGRESSIVE disk cleanup completed", 
                       files_cleaned=files_cleaned, 
                       space_freed_mb=round(actual_freed_mb, 2))
            
        except Exception as e:
            logger.error("Disk cleanup failed", error=str(e))
    
    async def _add_alert(self, alert: SystemAlert):
        """Add alert if not already active."""
        # Check if similar alert already exists
        existing = [a for a in self.active_alerts if a.message == alert.message and not a.resolved]
        if not existing:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            logger.warning("System alert generated", alert=alert.message, severity=alert.severity)
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            "monitoring_active": self.monitoring_active,
            "metrics_count": len(self.metrics_collector.metrics),
            "active_alerts_count": len([a for a in self.active_alerts if not a.resolved]),
            "total_alerts_count": len(self.alert_history),
            "last_collection": datetime.utcnow().isoformat(),
            "thresholds": self.thresholds
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [
            {
                "id": alert.id,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            }
            for alert in self.active_alerts if not alert.resolved
        ]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                logger.info("Alert resolved", alert_id=alert_id)
                return True
        return False
    
    def get_metrics_dashboard(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive metrics dashboard."""
        return {
            "system_overview": {
                "monitoring_active": self.monitoring_active,
                "duration_minutes": duration_minutes,
                "timestamp": datetime.utcnow().isoformat()
            },
            "metrics": self.metrics_collector.get_all_metrics_summary(duration_minutes),
            "active_alerts": self.get_active_alerts(),
            "alert_summary": {
                "active": len([a for a in self.active_alerts if not a.resolved]),
                "total": len(self.alert_history),
                "critical": len([a for a in self.active_alerts if a.severity == "critical" and not a.resolved]),
                "warnings": len([a for a in self.active_alerts if a.severity == "warning" and not a.resolved])
            }
        }


# Global monitoring service instance
system_monitoring_service = SystemMonitoringService()
