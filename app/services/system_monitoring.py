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
    
    def __init__(self, max_points: int = 1000):
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
        return {
            "metric": name,
            "duration_minutes": duration_minutes,
            "points_count": len(values),
            "current": values[-1] if values else 0,
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "trend": "increasing" if len(values) >= 2 and values[-1] > values[0] else "stable"
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
            "error_rate_pct": {"warning": 5.0, "critical": 10.0}
        }
    
    async def start_monitoring(self, interval_seconds: int = 30):
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
                    await db.execute("SELECT 1")
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
                summary = self.metrics_collector.get_metric_summary(metric_name, duration_minutes=5)
                
                if "error" in summary:
                    continue
                
                current_value = summary.get("current", 0)
                
                # Check critical threshold
                if current_value >= thresholds["critical"]:
                    alert_id = f"{metric_name}_critical_{int(time.time())}"
                    alert = SystemAlert(
                        id=alert_id,
                        severity="critical",
                        message=f"{metric_name}: {current_value:.2f} >= {thresholds['critical']} (CRITICAL)",
                        timestamp=current_time
                    )
                    await self._add_alert(alert)
                
                # Check warning threshold
                elif current_value >= thresholds["warning"]:
                    alert_id = f"{metric_name}_warning_{int(time.time())}"
                    alert = SystemAlert(
                        id=alert_id,
                        severity="warning", 
                        message=f"{metric_name}: {current_value:.2f} >= {thresholds['warning']} (WARNING)",
                        timestamp=current_time
                    )
                    await self._add_alert(alert)
        
        except Exception as e:
            logger.error("Failed to check alert conditions", error=str(e))
    
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
